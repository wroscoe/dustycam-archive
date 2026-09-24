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
    out = []
    g = L.build_parts(0, 0)
    cam = g["tilt_group"]["camera"]
    lens = max(cam.solids(), key=lambda s: s.bounding_box().max.X)
    bb = lens.bounding_box()
    dz = (bb.min.Z + bb.max.Z) / 2 - L.Z_TILT
    out.append(("lens barrel Z centre vs Z_TILT", round(dz, 3), "mm", abs(dz) < 0.2))
    out.append(("lens barrel X range", (round(bb.min.X, 2), round(bb.max.X, 2)), "axis X=0 inside", bb.min.X <= 0 <= bb.max.X))
    pcd = L._pitch_r(L.pan_pinion_teeth) + L._pitch_r(L.pan_gear_teeth) + L.gear_backlash_mm
    tcd = L._pitch_r(L.tilt_pinion_teeth) + L._pitch_r(L.tilt_gear_teeth) + L.gear_backlash_mm
    out.append(("pan centre distance", round(L.pan_center_dist, 3), "mm", abs(L.pan_center_dist - pcd) < 1e-9))
    out.append(("tilt centre distance", round(L.tilt_center_dist, 3), "mm", abs(L.tilt_center_dist - tcd) < 1e-9))
    sec = g["tilt_group"]["tilt_sector"].bounding_box()
    out.append(("sector inner face vs arm outer face", round(-sec.max.Y - L.arm_y1, 2), "mm gap (outside the arm)", -sec.max.Y >= L.arm_y1))
    cov = g["yoke_group"]["gear_cover"].bounding_box()
    out.append(("sector tip vs cover inner wall", round(L.tilt_gear_tip_r, 1), f"mm r vs cavity x {-cov.min.X - L.cover_wall:.1f}", L.tilt_gear_tip_r + 0.5 <= -cov.min.X - L.cover_wall))
    pp = g["base_group"]["pan_pinion"].bounding_box()
    out.append(("cover bottom vs pan pinion top", round(cov.min.Z - pp.max.Z, 2), "mm", cov.min.Z - pp.max.Z >= 1.0))
    g60 = L.build_parts(0, L.tilt_max_deg)
    cr = g60["tilt_group"]["cradle"].bounding_box()
    ts = g["yoke_group"]["tilt_servo"].bounding_box()
    out.append(("cradle lowest at tilt max vs tilt servo top", round(cr.min.Z - ts.max.Z, 2), "mm", cr.min.Z - ts.max.Z >= 1.0))
    out.append(("tilt servo bottom vs plate top", round(ts.min.Z - L.Z_PLATE_TOP, 2), "mm", ts.min.Z - L.Z_PLATE_TOP >= 1.0))
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
        f.write(f"# xiao_pantilt interference sweep\n\nbacklash {L.gear_backlash_mm} mm, {len(poses)} poses, "
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
