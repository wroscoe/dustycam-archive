"""Fail-closed geometry verification for universal_tripod_pad.py.

Run from this directory: ``python verify.py``.  Any missing geometry,
exception, non-finite value, or failed dimensional check returns exit status 1.
"""

import importlib.util
import math
import sys
from pathlib import Path

from build123d import Align, Cylinder, Pos


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "universal_tripod_pad.py"
spec = importlib.util.spec_from_file_location("universal_tripod_pad", SOURCE)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

TOL = 1e-5
PUCK_FACE_WIDTH = 47.21
PUCK_FACE_HEIGHT = 80.80
failures = []


def fail(message):
    failures.append(message)
    print(f"FAIL: {message}")


def finite(name, value):
    if value is None or not math.isfinite(value):
        fail(f"{name} is not finite: {value}")
        return False
    return True


def close(name, actual, expected, tolerance=TOL, unit="mm"):
    if not finite(name, actual):
        return
    if abs(actual - expected) > tolerance:
        fail(f"{name}: expected {expected:.6f}, got {actual:.6f}")
    else:
        print(f"PASS: {name} = {actual:.6f} {unit}")


def intersection_volume(a, b, name):
    try:
        result = a.intersect(b)
    except Exception as exc:  # fail closed: no failed geometry query is a pass
        fail(f"{name}: intersection failed: {exc}")
        return None
    if result is None:
        volume = 0.0
    elif hasattr(result, "volume"):
        volume = result.volume
    else:
        try:
            volumes = [shape.volume for shape in result]
        except Exception as exc:  # noqa: BLE001
            fail(f"{name}: could not enumerate intersection result: {exc}")
            return None
        if not all(finite(f"{name} item", value) for value in volumes):
            return None
        volume = sum(volumes)
    finite(name, volume)
    return volume


def main():
    try:
        part = module.gen_step()
    except Exception as exc:  # noqa: BLE001
        fail(f"generator raised {exc}")
        return 1

    # Source parameters must remain mutually consistent before testing BREP.
    named = {
        "pad_width": module.PAD_WIDTH,
        "pad_depth": module.PAD_DEPTH,
        "pad_thickness": module.PAD_THICKNESS,
        "corner_radius": module.PAD_CORNER_RADIUS,
        "boss_diameter": module.BOSS_DIAMETER,
        "boss_height": module.BOSS_HEIGHT,
        "pocket_diameter": module.INSERT_POCKET_DIAMETER,
        "pocket_depth": module.INSERT_POCKET_DEPTH,
        "insert_floor": module.INSERT_FLOOR,
    }
    required = {
        "pad_width": 40.0, "pad_depth": 32.0, "pad_thickness": 3.0,
        "corner_radius": 4.0, "boss_diameter": 16.0, "boss_height": 11.5,
        "pocket_diameter": 8.0, "pocket_depth": 13.5, "insert_floor": 1.0,
    }
    for name, expected in required.items():
        close(f"named {name}", named[name], expected)
    close("pocket top equals boss top", named["insert_floor"] + named["pocket_depth"],
          named["pad_thickness"] + named["boss_height"])

    try:
        solids = part.solids()
        valid = part.is_valid
        volume = part.volume
        bbox = part.bounding_box()
    except Exception as exc:  # noqa: BLE001
        fail(f"topology query failed: {exc}")
        return 1

    print(f"part label={part.label!r} solids={len(solids)} valid={valid} volume={volume:.3f} mm^3")
    if part.label != "universal_glue_on_tripod_pad":
        fail(f"unexpected part label {part.label!r}")
    if len(solids) != 1:
        fail(f"expected one solid, got {len(solids)}")
    if not valid:
        fail("part is invalid")
    finite("part volume", volume)

    close("overall width", bbox.size.X, module.PAD_WIDTH)
    close("overall depth", bbox.size.Y, module.PAD_DEPTH)
    close("overall height", bbox.size.Z, module.PAD_THICKNESS + module.BOSS_HEIGHT)
    close("glue face z", bbox.min.Z, 0.0)
    close("tripod-side top z", bbox.max.Z, module.PAD_THICKNESS + module.BOSS_HEIGHT)
    close("center x", (bbox.min.X + bbox.max.X) / 2, 0.0)
    close("center y", (bbox.min.Y + bbox.max.Y) / 2, 0.0)

    # The pocket must be clear from z=1 through its blind top, while solid
    # material beneath it proves the specified 1 mm glue-side floor remains.
    probe_align = (Align.CENTER, Align.CENTER, Align.MIN)
    clearance_probe = Pos(0, 0, module.INSERT_FLOOR) * Cylinder(
        module.INSERT_POCKET_DIAMETER / 2 - 0.05,
        module.INSERT_POCKET_DEPTH - 0.01,
        align=probe_align,
    )
    clearance_volume = intersection_volume(part, clearance_probe, "pocket clearance")
    if clearance_volume is not None:
        if clearance_volume > TOL:
            fail(f"pocket is obstructed: intersection {clearance_volume:.6f} mm^3")
        else:
            print("PASS: blind pocket is clear through specified depth")

    floor_probe = Cylinder(
        module.INSERT_POCKET_DIAMETER / 2 - 0.05,
        module.INSERT_FLOOR, align=probe_align
    )
    floor_volume = intersection_volume(part, floor_probe, "pocket floor")
    expected_floor_volume = math.pi * (module.INSERT_POCKET_DIAMETER / 2 - 0.05) ** 2 * module.INSERT_FLOOR
    if floor_volume is not None:
        close(
            "blind pocket floor material volume",
            floor_volume,
            expected_floor_volume,
            1e-3,
            "mm^3",
        )

    # The centered 40 x 32 pad must fit the stated 47.21 x 80.80 plain puck
    # face with positive edge margins; this is a face-envelope check, not a
    # claim about adhesive strength or puck geometry beyond those dimensions.
    margin_x = (PUCK_FACE_WIDTH - module.PAD_WIDTH) / 2
    margin_y = (PUCK_FACE_HEIGHT - module.PAD_DEPTH) / 2
    close("puck face x margin", margin_x, 3.605)
    close("puck face y margin", margin_y, 24.4)
    if margin_x <= 0 or margin_y <= 0:
        fail(f"pad exceeds puck face: margins x={margin_x:.3f}, y={margin_y:.3f}")
    else:
        print(f"PASS: centered puck-face margins x={margin_x:.3f} mm, y={margin_y:.3f} mm")

    if failures:
        print(f"\n{len(failures)} verification failure(s)")
        return 1
    print("\nAll universal tripod pad checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
