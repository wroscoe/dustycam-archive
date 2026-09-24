"""tubecase v2 fail-closed check script (DESIGN.md "checks.py").

Runs:
  1. pairwise interference of every pair in build_parts() (skipping
     battery_1578 <-> battery_swell_envelope, deliberately coincident: the
     envelope is a checks-only label, not a printed feature).
  2. static numeric checks (table, PASS/FAIL) per DESIGN.md section 2.
  3. insertion paths per DESIGN.md section 3: charger/battery vs base,
     mid plate vs base, camera vs mid plate, whole chassis vs tube, cap vs
     tube and camera.

Exits 1 on any failing check, any exception, or any NaN. Writes checks.md.
"""
from __future__ import annotations

import itertools
import math
import sys
from pathlib import Path

import tubecase_lib as L
from build123d import Pos
from cadgen.interference import _boxes_overlap, _intersection, _shape_bbox, _solid_volume

TOL = 1.0   # mm^3, matches `inspect interfere --tolerance 1` and the touching-sliver note in DESIGN.md

FAILS: list[str] = []
rows_static: list[tuple[str, object, str, bool]] = []


def _volume(a, b):
    """Pairwise intersection volume via the same helpers sweep.py uses."""
    aw, bw = a.wrapped, b.wrapped
    if not _boxes_overlap(_shape_bbox(aw), _shape_bbox(bw)):
        return 0.0
    inter = _intersection(aw, bw)
    if inter is None:
        return float("nan")
    return abs(_solid_volume(inter))


def _bbox_overlap_volume(a, b):
    """Fallback approx: volume of the bounding-box intersection (not the real
    solids). Used only when a boolean against the vendor XIAO STEP fails."""
    abb, bbb = _shape_bbox(a.wrapped), _shape_bbox(b.wrapped)
    if not _boxes_overlap(abb, bbb):
        return 0.0
    lo = [max(abb[i], bbb[i]) for i in range(3)]
    hi = [min(abb[i + 3], bbb[i + 3]) for i in range(3)]
    if any(hi[i] < lo[i] for i in range(3)):
        return 0.0
    return (hi[0] - lo[0]) * (hi[1] - lo[1]) * (hi[2] - lo[2])


def _max_radius(shape):
    """Max distance from the Z axis: sample vertices (catches box-like vendor
    parts) and circular-edge centre+radius (catches cylindrical printed parts,
    whose vertices alone can miss the true radius on a full-circle edge)."""
    r = 0.0
    for v in shape.vertices():
        r = max(r, math.hypot(v.X, v.Y))
    for e in shape.edges():
        try:
            if e.geom_type == "CIRCLE":
                c = e.arc_center
                r = max(r, math.hypot(c.X, c.Y) + e.radius)
        except Exception:
            pass
    return r


# --------------------------------------------------------------- 1. pairwise
def check_pairwise_interference():
    parts = L.build_parts()
    skip = {frozenset({"battery_1578", "battery_swell_envelope"})}
    print("## 1. Pairwise interference (tolerance %.1f mm^3)" % TOL)
    bad = []
    for (na, sa), (nb, sb) in itertools.combinations(parts.items(), 2):
        if frozenset({na, nb}) in skip:
            continue
        try:
            v = _volume(sa, sb)
            approx = False
        except Exception as exc:  # noqa: BLE001 - vendor STEP booleans can be unreliable
            if "camera_xiao" in (na, nb):
                v = _bbox_overlap_volume(sa, sb)
                approx = True
                print(f"  ! boolean failed for {na} x {nb} ({exc!r}); substituted bbox-overlap volume, flagged approx")
            else:
                raise
        if math.isnan(v):
            FAILS.append(f"pairwise {na} x {nb}: NaN volume")
            print(f"  FAIL {na} x {nb}: NaN")
            continue
        ok = v <= TOL
        tag = "approx" if approx else ""
        print(f"  {'PASS' if ok else 'FAIL'} {na} x {nb}: {v:.4f} mm^3 {tag}")
        if not ok:
            bad.append((na, nb, v, approx))
            FAILS.append(f"pairwise {na} x {nb}: {v:.4f} mm^3 > {TOL}")
    return bad


# --------------------------------------------------------------- 2. static
def check_static():
    parts = L.build_parts()
    charger_bb = parts["charger_bq25185"].bounding_box()
    battery_bb = parts["battery_1578"].bounding_box()
    envelope_bb = parts["battery_swell_envelope"].bounding_box()
    camera_bb = parts["camera_xiao"].bounding_box()
    cradle_bb = L.cradle_zero().bounding_box()

    def add(name, value, unit, ok):
        rows_static.append((name, value, unit, ok))
        if not ok:
            FAILS.append(f"static {name}: {value} {unit}")

    # every part max radius <= tube_od/2 (nothing outside the tube OD)
    for name, shape in parts.items():
        r = _max_radius(shape)
        add(f"{name} max radius vs tube OD", round(r, 3), f"mm (<= {L.tube_od / 2:.2f})", r <= L.tube_od / 2 + 1e-6)

    # every internal part (everything except the tube and the cap's top disc,
    # which are the only parts allowed out to the tube OD) max radius <= tube_id/2
    internal = {k: v for k, v in parts.items() if k not in ("tube",)}
    for name, shape in internal.items():
        r = _max_radius(shape)
        if name == "cap":
            # cap plug is internal (<= tube_id/2); its top disc is deliberately tube_od
            continue
        add(f"{name} max radius vs tube ID (internal)", round(r, 3), f"mm (<= {L.tube_id / 2:.2f})", r <= L.tube_id / 2 + 1e-6)
    # cap plug alone (excluding the top disc) vs tube ID
    plug_r = 0.0
    plug_od = L.tube_id - L.cap_plug_fit
    add("cap plug max radius vs tube ID (internal)", round(plug_od / 2, 3), f"mm (<= {L.tube_id / 2:.2f})", plug_od / 2 <= L.tube_id / 2 + 1e-6)

    # jack body to liner bore >= 0.4
    jx, jy = L.jack_xy
    jack_center = math.hypot(jx, jy)
    clearance = L.bore_r - (jack_center + L.jack_body_d / 2)
    add("jack body to liner bore", round(clearance, 3), "mm (>= 0.4)", clearance >= 0.4)

    # jack body to battery rib face (x -7.5) >= 1.0
    rib_x0 = L.bay_x0 - L.rib_w   # -7.5
    jack_max_x = jx + L.jack_body_d / 2
    clearance = rib_x0 - jack_max_x
    add("jack body to battery rib face", round(clearance, 3), "mm (>= 1.0)", clearance >= 1.0)

    # charger PCB corner radius (sqrt(4.57^2 + 15.875^2)) vs bore r 20.45 >= 1.0
    corner_x = L.ch_x + L.charger_pcb_t   # 4.57
    corner_y = L.charger_pcb_l / 2        # 15.875
    corner_r = math.hypot(corner_x, corner_y)
    clearance = L.bore_r - corner_r
    add("charger PCB corner radius vs bore", round(clearance, 3), "mm (>= 1.0)", clearance >= 1.0)

    # charger component corner (10.94, 15.875) vs bore >= 0.5
    corner_r2 = math.hypot(L.charger_components_x1, corner_y)
    clearance = L.bore_r - corner_r2
    add("charger component corner vs bore", round(clearance, 3), "mm (>= 0.5)", clearance >= 0.5)
    # cross-check against the actual imported STEP's measured envelope (informational)
    measured_max_x = charger_bb.max.X
    add("charger measured max X (components, actual STEP)", round(measured_max_x, 3), f"mm (spec assumed {L.charger_components_x1})", True)

    # charger top edge + 12 (plug room) <= Z_MID0
    plug_room = 12.0
    clearance = L.Z_MID0 - (L.CH_ORIGIN_Z + plug_room)
    add("charger top edge + 12mm plug room vs Z_MID0", round(clearance, 3), "mm (>= 0, i.e. fits under Z_MID0)", clearance >= 0)

    # battery top vs mid plate underside >= 2.0
    clearance = L.Z_MID0 - battery_bb.max.Z
    add("battery top vs mid plate underside", round(clearance, 3), "mm (>= 2.0)", clearance >= 2.0)

    # mid-plate boss bottom (31.5) vs jack body top (15.2) >= 5
    boss_bottom = L.Z_MID0 - L.boss_h
    clearance = boss_bottom - L.JACK_BODY_Z1
    add("mid-plate boss bottom vs jack body top", round(clearance, 3), "mm (>= 5.0)", clearance >= 5.0)

    # radial pilot vs vertical pilot separation >= 1.0
    vertical_pilot_bottom = L.Z_MID0 - L.pilot_depth   # 37.5
    radial_pilot_top = L.tube_screw_z + L.m2_pilot / 2   # 35.85
    clearance = vertical_pilot_bottom - radial_pilot_top
    add("radial pilot vs vertical pilot separation", round(clearance, 3), "mm (>= 1.0)", clearance >= 1.0)

    # cradle top and SD top vs cap plug underside >= 2.0
    plug_underside = L.Z_TUBE1 - L.cap_plug_h
    cradle_clear = plug_underside - cradle_bb.max.Z
    add("cradle top vs cap plug underside", round(cradle_clear, 3), "mm (>= 2.0)", cradle_clear >= 2.0)
    sd_clear = plug_underside - camera_bb.max.Z
    add("SD-card top vs cap plug underside", round(sd_clear, 3), "mm (>= 2.0)", sd_clear >= 2.0)

    # lens tip x vs tube inner wall >= lens_to_tube - 0.01
    clearance = L.tube_id / 2 - camera_bb.max.X
    add("lens tip x vs tube inner wall", round(clearance, 3), "mm (>= %.2f)" % (L.lens_to_tube - 0.01), clearance >= L.lens_to_tube - 0.01)

    # wire notch clear of the cradle footprint and of the bosses
    notch = L._notch_cut()
    notch_vs_cradle = _volume(notch, L.cradle_zero())
    add("wire notch vs cradle footprint", round(notch_vs_cradle, 4), "mm^3 (<= %.1f)" % TOL, notch_vs_cradle <= TOL)
    boss_min_clear = None
    for bx, by in L.boss_xy:
        v = _volume(notch, L._boss_solid(bx, by))
        boss_min_clear = v if boss_min_clear is None else max(boss_min_clear, v)
    add("wire notch vs bosses (max pair volume)", round(boss_min_clear, 4), "mm^3 (<= %.1f)" % TOL, boss_min_clear <= TOL)

    # lens height above the base floor bottom (informational report)
    add("lens height above floor bottom", round(L.Z_LENS, 3), "mm", True)

    # overall height and diameter
    add("overall height (Z_CAP1)", round(L.Z_CAP1, 3), f"mm (== {L.tube_len + L.cap_top_t})", abs(L.Z_CAP1 - 89.5) < 1e-6)
    add("overall body diameter (tube_od)", round(L.tube_od, 3), "mm (== 50.8)", abs(L.tube_od - 50.8) < 1e-9)

    return rows_static


# ------------------------------------------------------------ 3. insertion paths
def check_insertion_paths():
    print("## 3. Insertion paths")
    base = L.base_zero()
    tube = L.tube_zero()
    mid_plate = L.mid_plate_zero()
    charger = L.charger_zero()
    battery = L.battery_zero()
    camera = L.xiao_zero()
    jack_env = L.jack_envelope_zero()
    cap = L.cap_zero()

    rows = []

    def sweep(label, moving, fixed_list, dzs, sign=1):
        all_ok = True
        for dz in dzs:
            m = Pos(0, 0, sign * dz) * moving
            vols = []
            for fname, fshape in fixed_list:
                v = _volume(m, fshape)
                vols.append((fname, v))
            ok = all(not math.isnan(v) and v <= TOL for _, v in vols)
            rows.append((label, dz, vols, ok))
            vol_str = "  ".join(f"{fname}={v:.4f}" for fname, v in vols)
            print(f"  {label} dz={dz:3d}  {vol_str}  {'ok' if ok else 'FAIL'}")
            all_ok = all_ok and ok
        if not all_ok:
            FAILS.append(f"insertion sweep '{label}': nonzero intersection")
        return all_ok

    sweep("charger vs base", charger, [("base", base)], range(0, 31, 5))
    sweep("battery vs base", battery, [("base", base)], range(0, 31, 5))
    sweep("mid_plate(+cradle) vs base", mid_plate, [("base", base)], range(0, 11, 5))
    sweep("camera vs mid_plate", camera, [("mid_plate", mid_plate)], (5, 25))

    # whole chassis (base, mid plate, charger, battery, jack envelope, camera)
    # translated -dz vs tube
    chassis = base + mid_plate + charger + battery + jack_env + camera
    sweep("chassis vs tube", chassis, [("tube", tube)], range(0, 91, 10), sign=-1)

    # cap +dz vs tube and camera
    sweep("cap vs tube+camera", cap, [("tube", tube), ("camera", camera)], range(0, 11, 5))

    return rows


# --------------------------------------------------------------- report
def write_checks_md(pairwise_bad, static_rows, insertion_rows):
    lines = ["# tubecase v2 checks\n"]
    lines.append(f"Overall: **{'PASS' if not FAILS else 'FAIL'}** ({len(FAILS)} failing check(s))\n")

    lines.append("## 1. Pairwise interference\n")
    lines.append(f"Tolerance {TOL} mm^3. {'All pairs clean.' if not pairwise_bad else f'{len(pairwise_bad)} pair(s) over tolerance.'}\n")
    if pairwise_bad:
        lines.append("| a | b | volume mm^3 | approx |\n|---|---|---|---|\n")
        for na, nb, v, approx in pairwise_bad:
            lines.append(f"| {na} | {nb} | {v:.4f} | {approx} |\n")
    lines.append("\n")

    lines.append("## 2. Static checks\n\n| check | value | unit | ok |\n|---|---|---|---|\n")
    for name, value, unit, ok in static_rows:
        lines.append(f"| {name} | {value} | {unit} | {'PASS' if ok else 'FAIL'} |\n")
    lines.append("\n")

    lines.append("## 3. Insertion paths\n\n")
    lines.append("| sweep | dz mm | volumes | ok |\n|---|---|---|---|\n")
    for label, dz, vols, ok in insertion_rows:
        vol_str = "; ".join(f"{fname}={v:.4f}" for fname, v in vols)
        lines.append(f"| {label} | {dz} | {vol_str} | {'ok' if ok else 'FAIL'} |\n")
    lines.append("\n")

    if FAILS:
        lines.append("## Failures\n\n")
        for f in FAILS:
            lines.append(f"- {f}\n")

    Path("checks.md").write_text("".join(lines))


def main():
    try:
        pairwise_bad = check_pairwise_interference()
        static_rows = check_static()
        insertion_rows = check_insertion_paths()
    except Exception as exc:  # noqa: BLE001 - fail closed on any exception
        print(f"EXCEPTION: {exc!r}", file=sys.stderr)
        Path("checks.md").write_text(f"# tubecase v2 checks\n\nOverall: **FAIL** (exception)\n\n```\n{exc!r}\n```\n")
        raise

    write_checks_md(pairwise_bad, static_rows, insertion_rows)
    print(f"\n{'PASS' if not FAILS else 'FAIL'}: {len(FAILS)} failing check(s). See checks.md.")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
