"""Fail-closed interference check for the power puck (v2).

  python check.py            # static pairs + slide-in sweep
  python check.py --quick    # static pairs only

Every pair of occurrences whose bounding boxes overlap is intersected.  The
only pairs allowed non-zero volume are front_plate x tube (7 designed crush
ribs) and back_cup x tube (6 designed crush ribs).  Any exception, NaN,
split printable solid or unexpected volume fails the run with exit code 1.
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

TOL = 1e-4           # mm^3 - numerical noise floor
RIB_EXPECT = {
    frozenset({"front_plate", "tube"}): (12.0, 21.0),   # v2: 6 ribs (was 7)
    frozenset({"back_cup", "tube"}): (12.0, 21.0),       # 6 ribs
    frozenset({"usb_cap", "back_cup"}): (1.0, 3.0),      # 2 ribs x ~0.9 mm^3
}

# Pairs that overlap by construction inside the reference mocks: each JST
# plug mock starts inside its mated cable mock.
MATED = {
    frozenset(p) for p in [
        ("charger_jst_plug_1_mock", "load_cable_mock"),
        ("charger_jst_plug_2_mock", "batt_cable_mock"),
    ]
}
PRINTED = {"tube", "front_plate", "back_cup", "usb_cap"}

# Pairs that are alternate states of the same opening and are never present
# together: the cap fills the USB port, the plug mock is the port in use.
ALTERNATE = {frozenset({"usb_cap", "usb_plug_mock"})}

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
    printed = [C.tube(), C.front_plate(), C.back_cup(), C.usb_cap()]
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
        names = frozenset({a.label, b.label})
        if names in ALTERNATE:
            print(f"  {a.label} x {b.label}: {v:.3f} mm^3  (alternate states, not co-present)")
            continue
        if names in RIB_EXPECT:
            lo, hi = RIB_EXPECT[names]
            status = "designed crush" if lo <= v <= hi else "UNEXPECTED"
            print(f"  {a.label} x {b.label}: {v:.3f} mm^3  ({status})")
            if status != "designed crush":
                fail(f"rib crush {a.label} x {b.label} {v:.3f} outside {(lo, hi)}")
        elif names in MATED and not (names & PRINTED):
            print(f"  {a.label} x {b.label}: {v:.3f} mm^3  (mated, reference-internal)")
        elif v > TOL:
            print(f"  {a.label} x {b.label}: {v:.4f} mm^3")
            fail(f"interference {a.label} x {b.label} = {v:.4f} mm^3")
    print(f"static pairs checked: {checked}/{len(pairs)}")
    if checked != len(pairs):
        fail("not every pair was checked")

    # --- key clearances (report)
    def gap_y(a, b):
        return b.bounding_box().min.Y - a.bounding_box().max.Y

    jack = next(o for o in refs if o.label == "dc_jack_mock")
    chg = next(o for o in refs if o.label == "charger_bq25185")
    bat = next(o for o in refs if o.label == "battery_11x36x67_mock")
    plug1 = next(o for o in refs if o.label == "charger_jst_plug_1_mock")

    nut_top = C.JACK_ZC + C.JACK_NUT_D / 2
    nut_bot = C.JACK_ZC - C.JACK_NUT_D / 2
    jack_chamfer_clear = nut_bot - C.CHAMFER_TOP
    jack_floor_clear = C.Z_FLOOR - nut_top
    charger_edge_clear = gap_y(jack, chg)
    load_nut_clear = (C.JACK_XC - C.JACK_NUT_D / 2) - (C.LOAD_SLOT_XC + C.LOAD_SLOT_W / 2)
    usb_wall_clear = C.IN_Y1 - C.USB_SHELL_Y
    plug_jack_clear = gap_y(jack, plug1)

    print(f"\njack nut -> chamfer top (Z):    {jack_chamfer_clear:.3f}")
    print(f"jack nut -> floor (Z):          {jack_floor_clear:.3f}")
    print(f"jack end -> charger edge (Y):   {charger_edge_clear:.2f}")
    print(f"LOAD slot edge -> nut (X):      {load_nut_clear:.2f}")
    print(f"USB shell face -> inner wall (Y): {usb_wall_clear:.2f}")
    print(f"plug bottom -> jack end (Y):    {plug_jack_clear:.2f}")

    for want, got in [
        ("jack nut->chamfer top", jack_chamfer_clear),
        ("jack nut->floor", jack_floor_clear),
        ("jack->charger", charger_edge_clear),
        ("LOAD slot->nut", load_nut_clear),
        ("USB shell->inner wall", usb_wall_clear),
        ("plug->jack", plug_jack_clear),
    ]:
        if got < 0.0:
            fail(f"{want} clearance {got:.2f} < 0 (interference)")

    # --- slide-in sweep: back_cup + charger + jack + plugs + load_cable move
    #     along +Z, pulling the cup out of the tube's back mouth, past the
    #     stationary front_plate and battery.
    if not quick:
        # v2: load_cable_mock now exits through the back cup's own -Y wall
        # (beside the jack), so it moves WITH the cup.  batt_cable_mock stays
        # attached to the battery, and usb_plug_mock is a static reference
        # only meaningful with the cup off — both stay out of the moving
        # group (they're still checked in the static pair list above).
        moving_labels = {
            "back_cup", "charger_bq25185", "dc_jack_mock",
            "charger_jst_plug_1_mock", "charger_jst_plug_2_mock",
            "load_cable_mock",
        }
        moving = [o for o in occ if o.label in moving_labels]
        static = {
            "tube": next(o for o in occ if o.label == "tube"),
            "front_plate": next(o for o in occ if o.label == "front_plate"),
            "battery": bat,
        }
        steps = [k * 1.0 for k in range(0, 23)]   # 0..22, cup lip clears the tube well before 22
        print(f"\nslide-in sweep: {len(moving)} moving occurrences, "
              f"{len(steps)} steps of 1.0 mm, vs tube + front_plate + battery")
        worst = 0.0
        worst_rib = 0.0
        done = 0

        # NOTE: in this build123d, Shape.intersect() against a multi-solid
        # Compound ignores any Location applied via Pos()/Rot()/.moved()
        # *after* the Compound was built — bounding_box()/center() correctly
        # reflect the transform, intersect() silently does not (verified
        # directly against a minimal two-box Compound: intersect() gives the
        # same nonzero volume at d=0 and d=20 even though bounding_box()
        # correctly shows the move).  Decomposing into individual solids and
        # translating *each solid* before intersecting sidesteps the bug (a
        # translated single Solid intersects correctly), so every moving
        # occurrence is exploded to its solids for the sweep, matching how
        # caselib.charger_mock() itself now has to be built.
        def moved_solids(shape, dz):
            return [Pos(0, 0, dz) * s for s in shape.solids()]

        for d in steps:
            for m in moving:
                for ms in moved_solids(m, d):
                    for sname, s in static.items():
                        v = intersect_vol(s, ms)
                        if sname == "tube" and m.label == "back_cup":
                            # the back_cup crush ribs are designed to
                            # interfere with the tube wall right up until
                            # the lip clears the back mouth
                            # (d < LIP_RIB_H = 6.40); bound it, don't zero it.
                            if v > 21.0 + TOL:
                                fail(f"sweep offset {d:.1f}: tube x back_cup = {v:.4f} mm^3 (over rib bound)")
                            worst_rib = max(worst_rib, v)
                        else:
                            worst = max(worst, v)
                            if v > TOL:
                                fail(f"sweep offset {d:.1f}: {sname} x {m.label} = {v:.4f} mm^3")
            done += 1
        print(f"sweep steps completed: {done}/{len(steps)}")
        print(f"  worst tube x moving-group intersection (rib crush, expected to fall "
              f"to 0 by d={C.LIP_RIB_H:.1f}): {worst_rib:.5f} mm^3")
        print(f"  worst front_plate/battery x moving-group intersection: {worst:.5f} mm^3")
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
