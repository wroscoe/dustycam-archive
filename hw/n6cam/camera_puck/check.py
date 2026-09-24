"""Fail-closed interference check for the camera puck (v1).

  python check.py            # static pairs + slide-in sweep
  python check.py --quick    # static pairs only

Every pair of occurrences whose bounding boxes overlap is intersected.  The
only pairs allowed non-zero volume are back_plate x front_cup (6 designed
crush ribs) and usb_cap x front_cup (2 designed crush ribs).  Any exception,
NaN, split printable solid or unexpected volume fails the run with exit
code 1.
"""

import importlib.util
import math
import sys
from pathlib import Path

from build123d import Compound, Pos, import_step

import caselib as C

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("fitcheck_step", HERE / "fitcheck.step.py")
_fc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fc)

_asm_spec = importlib.util.spec_from_file_location("camera_puck_step", HERE / "camera-puck.step.py")
_asm = importlib.util.module_from_spec(_asm_spec)
_asm_spec.loader.exec_module(_asm)

TOL = 1e-4           # mm^3 — numerical noise floor
RIB_EXPECT = {
    frozenset({"back_plate", "front_cup"}): (12.0, 21.0),   # 6 ribs
    frozenset({"usb_cap", "front_cup"}): (2.0, 4.5),         # 2 ribs x 3.2 tall
}

# Pairs that overlap by construction inside the reference models/mocks: the
# N6 model's mid-mount USB-C and press-in spacers share volume with its PCB,
# the microSD card sits in its socket, and the LOAD plug mock starts inside
# the LOAD cable mock (they are declared MATED, not an interference).
MATED = {
    frozenset(p) for p in [
        ("pcb_main", "usb_c_receptacle"),
        ("pcb_main", "camera_standoffs"),
        ("pcb_main", "usb_plug_mock"),
        ("usb_c_receptacle", "usb_plug_mock"),
        ("microsd_socket_bottom", "microsd_card_mock"),
        ("load_jst_plug_mock", "load_cable_mock"),
    ]
}
PRINTED = {"front_cup", "cam_plate", "back_plate", "usb_cap"}

# Alternate states of the same opening, never present together: the cap
# fills the USB port, the plug mock is the port in use.
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
    printed = [C.front_cup(), C.cam_plate(), C.back_plate(), C.usb_cap()]
    front_cup, plate, back_plate, cap = printed
    refs = _fc.reference_parts()

    # --- printable solids: exactly one valid solid each
    for p in printed:
        n = len(p.solids())
        ok = p.is_valid
        print(f"{p.label:12s} solids={n} valid={ok} volume={vol(p):.2f} mm^3 bbox={p.bounding_box()}")
        if n != 1 or not ok:
            fail(f"{p.label}: solids={n} valid={ok}")

    print(f"\nusb_cap bounding box: {cap.bounding_box()}")

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

    # --- explicit clearance prints/asserts ---------------------------------
    v_plate_cup = intersect_vol(plate, front_cup)
    v_plate_back = intersect_vol(plate, back_plate)
    print(f"\nplate x front_cup: {v_plate_cup:.4f} mm^3")
    print(f"plate x back_plate: {v_plate_back:.4f} mm^3")
    if v_plate_cup > TOL:
        fail(f"plate x front_cup interference {v_plate_cup:.4f} mm^3")
    if v_plate_back > TOL:
        fail(f"plate x back_plate interference {v_plate_back:.4f} mm^3")

    lens_clear = (C.LENS_HOLE_D - C.LENS_BARREL_D) / 2
    print(f"lens barrel -> aperture radial clearance: {lens_clear:.2f} mm")
    if lens_clear <= 0:
        fail(f"lens barrel/aperture radial clearance {lens_clear:.2f} <= 0")

    usb_c = next(o for o in refs if o.label == "usb_c_receptacle")
    ubb = usb_c.bounding_box()
    usb_margin_x = min(ubb.min.X - (C.USB_XC - C.USB_W / 2), (C.USB_XC + C.USB_W / 2) - ubb.max.X)
    usb_margin_z = min(ubb.min.Z - (C.USB_ZC - C.USB_H / 2), (C.USB_ZC + C.USB_H / 2) - ubb.max.Z)
    print(f"USB shell -> port margin: x={usb_margin_x:.2f} z={usb_margin_z:.2f}")
    if usb_margin_x < 0 or usb_margin_z < 0:
        fail(f"USB shell vs port margin negative: x={usb_margin_x:.2f} z={usb_margin_z:.2f}")

    print("opening non-overlap (vents / LOAD slot / USB port):")
    for na, nb in __import__("itertools").combinations(C.OPENING_RECTS, 2):
        g = C.opening_gap(C.OPENING_RECTS[na], C.OPENING_RECTS[nb])
        print(f"  {na} <-> {nb}: gap {g:.2f} mm")
        if g < 0:
            fail(f"{na} overlaps {nb}: gap {g:.2f} mm")

    print(f"TOP_CH (headroom above the board): {C.TOP_CH:.2f} mm")
    if C.TOP_CH < 0.6:
        fail(f"TOP_CH {C.TOP_CH:.2f} < 0.6")

    # --- slide-in sweep: cam_plate + the 17 N6 solids + sd_card move along
    #     -Z out of the front cup; the LOAD plug/cable are already threaded
    #     through the slot and stay put.
    if not quick:
        moving_labels = {o.label for o in refs} - {
            "load_jst_plug_mock", "load_cable_mock", "usb_plug_mock",
        }
        moving = [plate] + [o for o in refs if o.label in moving_labels]
        # Flatten to solids: intersect() ignores a Location applied to a
        # Compound, so every solid is moved individually per step.
        moving_solids = []
        for o in moving:
            moving_solids.extend(o.solids())
        static = [front_cup]
        steps = [k * 1.0 for k in range(0, 31)]
        print(f"\nslide-in sweep: {len(moving)} moving occurrences ({len(moving_solids)} solids), {len(steps)} steps of 1.0 mm, vs front_cup")
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

    # --- re-import the exported STEP and confirm it matches the source -----
    step_path = HERE / "camera-puck.step"
    if not step_path.exists():
        fail(f"{step_path.name} not found; run gen before check.py")
    else:
        src_asm = _asm.gen_step()
        src_bbox = src_asm.bounding_box()
        reimported = import_step(str(step_path))
        n = len(reimported.solids())
        print(f"\ncamera-puck.step reimport: solids={n}")
        if n != 4:
            fail(f"camera-puck.step reimport: solids={n} (expected 4)")
        re_bbox = reimported.bounding_box()
        deltas = [
            abs(src_bbox.min.X - re_bbox.min.X), abs(src_bbox.max.X - re_bbox.max.X),
            abs(src_bbox.min.Y - re_bbox.min.Y), abs(src_bbox.max.Y - re_bbox.max.Y),
            abs(src_bbox.min.Z - re_bbox.min.Z), abs(src_bbox.max.Z - re_bbox.max.Z),
        ]
        worst_delta = max(deltas)
        print(f"source bbox:     {src_bbox}")
        print(f"reimported bbox: {re_bbox}")
        print(f"worst bbox delta: {worst_delta:.5f} mm")
        if worst_delta > 0.01:
            fail(f"camera-puck.step bounding box drifted {worst_delta:.5f} mm on reimport")

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
