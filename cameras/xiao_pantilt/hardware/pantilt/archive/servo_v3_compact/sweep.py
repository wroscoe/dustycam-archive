"""Interference sweep for xiao_pantilt.

Runs pantilt_lib.build_parts() over a pan x tilt grid and boolean-intersects
every cross-group pair (base <-> yoke, base <-> tilt, yoke <-> tilt). Same-group
pairs are rigid and are covered by `inspect interfere` at the zero pose.

  PANTILT_BACKLASH=0 python sweep.py --corners     # gear check at zero backlash
  python sweep.py                                   # full grid -> clash_table.md
"""
from __future__ import annotations

import argparse
import itertools
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pantilt_lib as L  # noqa: E402
from cadgen.interference import _intersection, _shape_bbox, _boxes_overlap, _solid_volume  # noqa: E402

GEAR_PAIRS = {("pan_pinion", "pan_gear"), ("tilt_pinion", "tilt_sector")}
GEAR_TOL, STRUCT_TOL = 0.5, 1.0


def flatten(groups):
    return {g: {n: s.wrapped for n, s in parts.items()} for g, parts in groups.items()}


def pair_volume(a, b):
    if not _boxes_overlap(_shape_bbox(a), _shape_bbox(b)):
        return 0.0
    inter = _intersection(a, b)
    return _solid_volume(inter) if inter is not None else float("nan")


def check_pose(pan, tilt, groups_to_test):
    rows = []
    g = flatten(L.build_parts(pan, tilt))
    for ga, gb in groups_to_test:
        for (na, sa), (nb, sb) in itertools.product(g[ga].items(), g[gb].items()):
            v = pair_volume(sa, sb)
            if v > 1e-6:
                key = (na, nb) if (na, nb) in GEAR_PAIRS else (nb, na)
                tol = GEAR_TOL if key in GEAR_PAIRS else STRUCT_TOL
                rows.append((pan, tilt, na, nb, v, "gear" if key in GEAR_PAIRS else "struct", v <= tol))
    return rows


def static_checks():
    import math
    out = []
    g = L.build_parts(0, 0)
    cam = g["tilt_group"]["camera"]
    lens = max(cam.solids(), key=lambda s: s.bounding_box().max.X)
    bb = lens.bounding_box()
    dz = (bb.min.Z + bb.max.Z) / 2 - L.Z_TILT
    out.append(("lens barrel Z vs tilt axis (design: -6.95)", round(dz, 2), "mm", abs(dz + (L.board_center_bx - L.lens_bx)) < 0.3))
    pcd = L._pitch_r(L.pan_pinion_teeth) + L._pitch_r(L.pan_gear_teeth) + L.gear_backlash_mm
    tcd = L._pitch_r(L.tilt_pinion_teeth) + L._pitch_r(L.tilt_gear_teeth) + L.gear_backlash_mm
    out.append(("pan centre distance", round(L.pan_center_dist, 3), "mm", abs(L.pan_center_dist - pcd) < 1e-9))
    out.append(("tilt centre distance", round(L.tilt_center_dist, 3), "mm", abs(L.tilt_center_dist - tcd) < 1e-9))
    # moving envelope over the tilt range (pan-invariant): max radius and height
    rmax = 0.0; zmax = 0.0; rz = []
    for t in range(int(L.tilt_min_deg), int(L.tilt_max_deg) + 1, 10):
        gt = L.build_parts(0, t)
        for grp in ("yoke_group", "tilt_group"):
            for n, s in gt[grp].items():
                for v in s.vertices():
                    r = math.hypot(v.X, v.Y); rz.append((r, v.Z))
                    rmax = max(rmax, r); zmax = max(zmax, v.Z)
    out.append(("moving envelope max radius", round(rmax, 1), "mm", rmax < L.ring_r_in - 0.5))
    out.append(("moving envelope top above cover seat", round(zmax - L.Z_SEAT, 1), "mm", True))
    cov = g["base_group"].get("clear_cover")
    if cov is not None:
        cb = cov.bounding_box()
        if L.cover_kind == "dome4":
            r_in = L.dome4_id / 2; zc = L.Z_SEAT + L.dome4_skirt
            worst = min((math.sqrt(max(r_in**2 - r**2, 0)) + zc - z) if r < r_in else -1 for r, z in rz if z > L.Z_SEAT)
            out.append(("dome4 ceiling clearance (min over envelope)", round(worst, 1), "mm", worst >= 1.0))
        else:
            worst_r = L.jar_id / 2 - rmax
            worst_z = L.Z_SEAT + L.jar_inner_h - zmax
            out.append(("jar wall clearance", round(worst_r, 1), "mm", worst_r >= 1.0))
            out.append(("jar ceiling clearance", round(worst_z, 1), "mm", worst_z >= 1.0))
    ts = g["yoke_group"]["tilt_servo"].bounding_box()
    out.append(("tilt servo front face vs cradle sweep radius", round(-ts.max.X - L.sweep_r, 2), "mm", -ts.max.X - L.sweep_r >= 1.0))
    out.append(("tilt servo bottom ear vs plate top (notch)", round(ts.min.Z - (L.Z_PLATE_TOP - L.plate_notch), 2), "mm", ts.min.Z >= L.Z_PLATE_TOP - L.plate_notch))
    pp = g["base_group"]["pan_pinion"].bounding_box()
    out.append(("pan pinion top vs ring underside", round(L.Z_RIM - pp.max.Z, 2), "mm", L.Z_RIM - pp.max.Z >= 1.0))
    out.append(("pan pinion tip vs well wall", round(L.well_r - math.hypot(pp.min.X, 0), 2), "mm", L.well_r + pp.min.X >= 1.0))
    pan_servo_travel = (L.pan_max_deg - L.pan_min_deg) * L.pan_gear_teeth / L.pan_pinion_teeth
    tilt_servo_travel = (L.tilt_max_deg - L.tilt_min_deg) * L.tilt_gear_teeth / L.tilt_pinion_teeth
    out.append(("pan servo travel", round(pan_servo_travel, 1), "deg (<= 170)", pan_servo_travel <= 170))
    out.append(("tilt servo travel", round(tilt_servo_travel, 1), "deg (<= 170)", tilt_servo_travel <= 170))
    out.append(("cable bore", L.journal_bore, "mm", L.journal_bore >= 7.0))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corners", action="store_true", help="only the 4 range corners + zero")
    ap.add_argument("--out", default="clash_table.md")
    a = ap.parse_args()
    t0 = time.time()
    pans = [-90 + 15 * i for i in range(13)]
    tilts = [-30 + 10 * i for i in range(10)]
    if a.corners:
        poses = [(0, 0), (-90, -30), (-90, 60), (90, -30), (90, 60)]
    else:
        poses = [(p, t) for t in tilts for p in pans]
    print(f"backlash={L.gear_backlash_mm} poses={len(poses)}", flush=True)
    stat = static_checks()
    for row in stat:
        print("  static", row, flush=True)
    rows = []
    tilt_only_done = set()
    for i, (pan, tilt) in enumerate(poses):
        groups = [("base_group", "yoke_group"), ("base_group", "tilt_group")]
        if tilt not in tilt_only_done or a.corners:
            groups.append(("yoke_group", "tilt_group"))   # pan-invariant: once per tilt
            tilt_only_done.add(tilt)
        r = check_pose(pan, tilt, groups)
        rows.extend(r)
        bad = [x for x in r if not x[6]]
        print(f"[{i+1}/{len(poses)}] pan={pan:4} tilt={tilt:4} overlaps={len(r)} FAIL={len(bad)} t={time.time()-t0:.0f}s", flush=True)
        for x in bad:
            print("     FAIL", x[2], "x", x[3], round(x[4], 3), flush=True)
    fails = [x for x in rows if not x[6]]
    with open(a.out, "w") as f:
        f.write(f"# xiao_pantilt interference sweep (cover: {L.cover_kind})\n\nbacklash {L.gear_backlash_mm} mm, {len(poses)} poses, "
                f"struct tolerance {STRUCT_TOL} mm^3, gear tolerance {GEAR_TOL} mm^3, {time.time()-t0:.0f} s\n\n")
        f.write("## Static checks\n\n| check | value | unit | ok |\n|---|---|---|---|\n")
        for n, v, u, ok in stat:
            f.write(f"| {n} | {v} | {u} | {'PASS' if ok else 'FAIL'} |\n")
        f.write(f"\n## Result: {'PASS' if not fails else 'FAIL'} ({len(fails)} failing pair-poses, {len(rows)} nonzero overlaps)\n\n")
        f.write("| pan | tilt | a | b | volume mm^3 | kind | ok |\n|---|---|---|---|---|---|---|\n")
        for pan, tilt, na, nb, v, k, ok in sorted(rows, key=lambda x: -x[4]):
            f.write(f"| {pan} | {tilt} | {na} | {nb} | {v:.3f} | {k} | {'ok' if ok else 'FAIL'} |\n")
        if not rows:
            f.write("| - | - | - | - | 0 | - | ok |\n")
    print("wrote", a.out, "fails", len(fails), flush=True)


if __name__ == "__main__":
    main()
