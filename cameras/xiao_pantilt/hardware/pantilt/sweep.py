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
    g = L.build_parts(0)
    rmax = 0.0; zmax = 0.0
    for n, s in g["yoke_group"].items():
        for v in s.vertices():
            rmax = max(rmax, math.hypot(v.X, v.Y)); zmax = max(zmax, v.Z)
    out.append(("pod max radius", round(rmax, 2), f"mm vs tube ID/2 {L.tube_id/2}", rmax <= L.tube_id / 2 - 1.0))
    out.append(("pod top vs cap plug underside", round(L.Z_TUBE1 - L.cap_plug_depth - zmax, 2), "mm", L.Z_TUBE1 - L.cap_plug_depth - zmax >= 1.0))
    out.append(("pod top above cover seat", round(zmax - L.Z_SEAT, 1), "mm", True))
    out.append(("foot bottom vs base top plate", round(L.Z_FOOT0 - L.Z_TOP, 2), "mm", L.Z_FOOT0 - L.Z_TOP >= 1.0))
    out.append(("USB plug space under the board (rail bottom to foot)", round(L.Z_BOARD0 + L.rail_x0 - L.Z_FOOT1, 1), "mm (>= 8 right-angle plug)", L.Z_BOARD0 + L.rail_x0 - L.Z_FOOT1 >= 8))
    out.append(("lip gap over PCB", L.lip_gap, "mm (case used 0.2)", L.lip_gap >= 0.2))
    out.append(("pocket side clearance", L.pocket_side, "mm (case used 0.4)", L.pocket_side >= 0.4))
    sv = g["base_group"]["pan_servo"].bounding_box()
    out.append(("servo ear reach vs hollow radius", round(L.hollow_r - max(abs(sv.min.Y), abs(sv.max.Y), abs(sv.min.X), abs(sv.max.X)), 2), "mm", L.hollow_r - max(abs(sv.min.Y), abs(sv.max.Y)) >= 1.0))
    out.append(("servo bottom above bench", round(sv.min.Z, 2), "mm", sv.min.Z >= 0.5))
    ch = math.hypot(*L.cable_hole_xy)
    out.append(("cable hole vs groove inner radius", round(L.groove_r0 - (ch + L.cable_hole_d / 2), 2), "mm", L.groove_r0 - (ch + L.cable_hole_d / 2) >= 1.0))
    out.append(("cable hole vs servo body (Y)", round(L.cable_hole_xy[1] - L.cable_hole_d / 2 - sv.max.Y, 2), "mm", L.cable_hole_xy[1] - L.cable_hole_d / 2 - sv.max.Y >= 1.0))
    out.append(("pan servo travel", L.pan_max_deg - L.pan_min_deg, "deg (direct)", True))
    bb = g["base_group"]["battery_503035"].bounding_box()
    out.append(("battery top vs servo bottom", round(sv.min.Z - bb.max.Z, 2), "mm", sv.min.Z - bb.max.Z >= 1.0))
    lb = g["base_group"]["base_lid"].bounding_box()
    lidr = max(abs(lb.min.X), abs(lb.max.X), abs(lb.min.Y), abs(lb.max.Y))
    out.append(("lid + frame max radius vs hollow", round(L.hollow_r - lidr, 2), "mm", L.hollow_r - lidr >= 0.15))
    out.append(("base height", round(L.Z_TOP, 1), "mm", True))
    return out


def board_fit_check():
    """Holder/camera interference at the in-pocket extremes (like the tripod case)."""
    import importlib, os
    results = []
    for dx, dy in [(0, 0), (-L.pocket_side, 0), (0, -L.pocket_side), (0, L.pocket_side), (-L.pocket_side, -L.pocket_side), (-L.pocket_side, L.pocket_side)]:
        os.environ["PANTILT_BOARD_DX"] = str(dx); os.environ["PANTILT_BOARD_DY"] = str(dy)
        importlib.reload(L)
        g = L.build_parts(0)
        cam = g["yoke_group"]["camera"].wrapped
        vols = {}
        for n in ("holder", "pod_base", "servo_horn"):
            vols[n] = pair_volume(g["yoke_group"][n].wrapped, cam)
        results.append(((dx, dy), vols))
        print(f"  boardfit dx={dx:+.1f} dy={dy:+.1f} " + " ".join(f"{k}={v:.3f}" for k, v in vols.items()), flush=True)
    os.environ.pop("PANTILT_BOARD_DX", None); os.environ.pop("PANTILT_BOARD_DY", None)
    importlib.reload(L)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corners", action="store_true", help="only the 4 range corners + zero")
    ap.add_argument("--out", default="clash_table.md")
    ap.add_argument("--boardfit", action="store_true", help="holder vs vendor board at pocket extremes")
    a = ap.parse_args()
    if a.boardfit:
        res = board_fit_check()
        bad = [(o, v) for o, v in res if any(x > 0.01 for x in v.values())]   # 0.01 mm^3 = touching, like the case notes
        print("boardfit", "PASS" if not bad else f"FAIL {bad}")
        return
    t0 = time.time()
    pans = [-90 + 15 * i for i in range(13)]
    tilts = [-30 + 10 * i for i in range(10)] if getattr(L, "HAS_TILT", True) else [0]
    if a.corners:
        poses = [(0, 0), (-90, -30), (-90, 60), (90, -30), (90, 60)] if getattr(L, "HAS_TILT", True) else [(0, 0), (-90, 0), (90, 0), (45, 0)]
    else:
        poses = [(p, t) for t in tilts for p in pans]
    print(f"backlash={L.gear_backlash_mm} poses={len(poses)}", flush=True)
    stat = static_checks()
    for row in stat:
        print("  static", row, flush=True)
    rows = []
    tilt_only_done = set()
    for i, (pan, tilt) in enumerate(poses):
        groups = [("base_group", "yoke_group")]
        if "tilt_group" in L.build_parts(0, 0):
            groups.append(("base_group", "tilt_group"))
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
        f.write(f"# xiao_pantilt interference sweep (v7 split pod, slot holder)\n\nbacklash {L.gear_backlash_mm} mm, {len(poses)} poses, "
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
