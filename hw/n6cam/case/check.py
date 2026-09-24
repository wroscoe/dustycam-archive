"""Fail-closed interference check for the N6 case (rev E).

  python check.py            # static pairs + slide-in sweep
  python check.py --quick    # static pairs only

Every pair of occurrences whose bounding boxes overlap is intersected.  The
only pair allowed a non-zero volume is front_cup x back_cup (the designed
crush-rib interference).  Any exception, NaN, split printable solid or
unexpected volume fails the run with exit code 1.
"""

import importlib.util
import math
import sys
from pathlib import Path

from build123d import Compound, Pos

import caselib as C

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("fitcheck_step", HERE / "fitcheck.step.py")
_fc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fc)

TOL = 1e-4           # mm^3 — numerical noise floor
RIB_EXPECT = (15.0, 22.0)   # 7 ribs x ~2.6 mm^3 designed crush (rev D: 6 ribs = 15.44)

# Pairs that overlap by construction inside the reference models/mocks: the
# N6 model's mid-mount USB-C and press-in spacers share volume with its PCB,
# and every plug/card/cable mock starts inside the part it mates with.  They
# are listed explicitly so a new overlap can't hide behind a blanket ignore.
MATED = {
    frozenset(p) for p in [
        ("pcb_main", "usb_c_receptacle"),
        ("pcb_main", "camera_standoffs"),
        ("pcb_main", "usb_plug_mock"),
        ("usb_c_receptacle", "usb_plug_mock"),
        ("microsd_socket_bottom", "microsd_card_mock"),
        ("charger_jst_plug_1_mock", "load_cable_mock"),
        ("charger_jst_plug_2_mock", "batt_cable_mock"),
    ]
}
PRINTED = {"front_cup", "cam_plate", "back_cup"}

failures = []


def fail(msg):
    failures.append(msg)
    print("FAIL", msg)


def vol(shape):
    v = shape.volume
    if v is None or math.isnan(v) or math.isinf(v):
        raise ValueError(f"bad volume {v}")
    return v


def bbox_overlap(a, b, pad=0.0):
    ba, bb = a.bounding_box(), b.bounding_box()
    return (ba.min.X <= bb.max.X + pad and bb.min.X <= ba.max.X + pad and
            ba.min.Y <= bb.max.Y + pad and bb.min.Y <= ba.max.Y + pad and
            ba.min.Z <= bb.max.Z + pad and bb.min.Z <= ba.max.Z + pad)


def intersect_vol(a, b):
    try:
        common = a.intersect(b)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"intersect failed {a.label} x {b.label}: {e}") from e
    if common is None:
        return 0.0
    if isinstance(common, (list, tuple)):          # ShapeList from a compound operand
        return sum(vol(c) for c in common)
    return vol(common)


def main():
    quick = "--quick" in sys.argv
    printed = [C.front_cup(), C.cam_plate(), C.back_cup()]
    refs = _fc.reference_parts()

    # --- printable solids: exactly one valid solid each
    for p in printed:
        n = len(p.solids())
        ok = p.is_valid
        print(f"{p.label:12s} solids={n} valid={ok} volume={vol(p):.2f} mm^3 bbox={p.bounding_box()}")
        if n != 1 or not ok:
            fail(f"{p.label}: solids={n} valid={ok}")

    occ = printed + refs
    labels = [o.label for o in occ]
    if len(set(labels)) != len(labels):
        fail(f"duplicate labels: {labels}")

    # --- static pair list from overlapping bounds
    pairs = []
    for i in range(len(occ)):
        for j in range(i + 1, len(occ)):
            if bbox_overlap(occ[i], occ[j]):
                pairs.append((occ[i], occ[j]))
    print(f"\n{len(occ)} occurrences, {len(pairs)} bound-overlapping pairs")
    checked = 0
    for a, b in pairs:
        v = intersect_vol(a, b)
        checked += 1
        names = {a.label, b.label}
        if names == {"front_cup", "back_cup"}:
            status = "designed crush" if RIB_EXPECT[0] <= v <= RIB_EXPECT[1] else "UNEXPECTED"
            print(f"  {a.label} x {b.label}: {v:.3f} mm^3  ({status})")
            if status != "designed crush":
                fail(f"rib crush {v:.3f} outside {RIB_EXPECT}")
        elif names in MATED and not (names & PRINTED):
            print(f"  {a.label} x {b.label}: {v:.3f} mm^3  (mated, reference-internal)")
        elif v > TOL:
            print(f"  {a.label} x {b.label}: {v:.4f} mm^3")
            fail(f"interference {a.label} x {b.label} = {v:.4f} mm^3")
    print(f"static pairs checked: {checked}/{len(pairs)}")
    if checked != len(pairs):
        fail("not every pair was checked")

    # --- key clearances (report; assert the ones the design relies on)
    def gap_y(a, b):
        return b.bounding_box().min.Y - a.bounding_box().max.Y

    jack = next(o for o in refs if o.label == "dc_jack_mock")
    chg = next(o for o in refs if o.label == "charger_bq25185")
    bat = next(o for o in refs if o.label == "battery_30x40x6_mock")
    plate = printed[1]
    print(f"\njack end -> charger edge (Y): {gap_y(jack, chg):.2f}")
    print(f"jack end -> battery (Y):      {gap_y(jack, bat):.2f}")
    print(f"jack nut top -> plate back (Z): {plate.bounding_box().min.Z - (C.JACK_ZC + C.JACK_NUT_D/2):.2f}")
    print(f"jack nut bottom -> bay floor (Z): {(C.JACK_ZC - C.JACK_NUT_D/2) - C.Z_SEAM:.2f}")
    print(f"charger comps -> battery (Z): {bat.bounding_box().max.Z - chg.bounding_box().min.Z:.2f} (negative = clear)")
    for want, got in [("jack->charger", gap_y(jack, chg)), ("jack->battery", gap_y(jack, bat))]:
        if got < 1.0:
            fail(f"{want} clearance {got:.2f} < 1.0")

    # --- slide-in sweep: plate + N6 + charger + plugs + cables + card move
    #     along -Z out of the front cup; the jack is already installed.
    if not quick:
        moving_labels = {o.label for o in refs} - {"dc_jack_mock", "battery_30x40x6_mock", "usb_plug_mock"}
        moving = [plate] + [o for o in refs if o.label in moving_labels]
        # Flatten to solids: intersect() ignores a Location applied to a
        # Compound, so every solid is moved individually per step.
        moving_solids = []
        for o in moving:
            moving_solids.extend(o.solids())
        static = [printed[0], jack]
        steps = [k * 1.0 for k in range(0, 31)]
        print(f"\nslide-in sweep: {len(moving)} moving occurrences ({len(moving_solids)} solids), {len(steps)} steps of 1.0 mm, vs front_cup + jack")
        worst = 0.0
        done = 0
        for d in steps:
            g = Compound(children=[Pos(0, 0, -d) * s for s in moving_solids])
            for s in static:
                v = intersect_vol(s, g)
                worst = max(worst, v)
                if v > TOL:
                    fail(f"sweep offset {d:.1f}: {s.label} x moving group = {v:.4f} mm^3")
            done += 1
        print(f"sweep steps completed: {done}/{len(steps)}, worst intersection {worst:.5f} mm^3")
        if done != len(steps):
            fail("sweep did not finish")

    print()
    if failures:
        print(f"CHECK FAILED ({len(failures)} problems)")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("CHECK PASSED")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print("CHECK FAILED (exception):", repr(e))
        sys.exit(1)
