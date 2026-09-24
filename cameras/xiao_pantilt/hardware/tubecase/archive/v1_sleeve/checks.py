"""tubecase fail-closed check script (DESIGN.md "Files to produce" > checks.py).

Runs:
  1. pairwise interference of every pair in build_parts() (skipping the
     battery_1578 <-> battery_swell_envelope pair, which is deliberately
     coincident -- the envelope is a checks-only label, not a printed part).
     This includes jack_envelope (the DC barrel jack's estimated envelope,
     also checks-only) against every other part.
  2. static numeric checks (table, PASS/FAIL).
  3. bayonet install path: rotate {deck, charger} about Z, then also drop them
     straight down, checking for zero intersection with the sleeve throughout;
     then the door (with its anti-rotation pins), translated straight up from
     z -25 to 0, against the sleeve/deck/charger (it goes on last).
  4. camera insertion / lip-trap check.

Exits 1 on any failing check, any exception, or any NaN. Writes checks.md.
"""
from __future__ import annotations

import itertools
import math
import sys
from pathlib import Path

import tubecase_lib as L
from build123d import Axis, Pos
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
    cradle_bb = L.cradle_zero().bounding_box()
    camera_bb = parts["camera_xiao"].bounding_box()
    deck_bb = parts["deck"].bounding_box()

    def add(name, value, unit, ok):
        rows_static.append((name, value, unit, ok))
        if not ok:
            FAILS.append(f"static {name}: {value} {unit}")

    # charger long edge to rib face >= 1.0
    charger_edge_r = max(abs(charger_bb.min.Y), abs(charger_bb.max.Y))
    clearance = L.rib_r0 - charger_edge_r
    add("charger long edge to rib face", round(clearance, 3), "mm (>= 1.0)", clearance >= 1.0)

    # charger components bottom vs battery swell top >= 2.0
    swell_top = L.door_t + L.battery_envelope_h
    clearance = charger_bb.min.Z - swell_top
    add("charger components bottom vs battery swell top", round(clearance, 3), "mm (>= 2.0)", clearance >= 2.0)

    # cradle max radius (no board) <= neck_id/2 - 0.5
    rmax = 0.0
    for v in L.cradle_zero().vertices():
        rmax = max(rmax, math.hypot(v.X, v.Y))
    threshold = L.neck_id / 2 - 0.5
    add("cradle max radius (no board)", round(rmax, 3), f"mm (<= neck_id/2 - 0.5 = {threshold:.3f})", rmax <= threshold)

    # lens tip x vs tube inner wall >= lens_to_tube - 0.01
    clearance = L.tube_id / 2 - camera_bb.max.X
    add("lens tip x vs tube inner wall", round(clearance, 3), "mm (>= %.2f)" % (L.lens_to_tube - 0.01), clearance >= L.lens_to_tube - 0.01)

    # cradle top and SD-card top vs cap plug underside >= 2.0
    plug_underside = L.Z_TUBE1 - L.cap_plug_h
    cradle_clear = plug_underside - cradle_bb.max.Z
    add("cradle top vs cap plug underside", round(cradle_clear, 3), "mm (>= 2.0)", cradle_clear >= 2.0)
    sd_clear = plug_underside - camera_bb.max.Z
    add("SD-card top vs cap plug underside", round(sd_clear, 3), "mm (>= 2.0)", sd_clear >= 2.0)

    # anti-rotation pin engagement into the deck's blind hole == pin_engage
    door_bb = parts["door"].bounding_box()
    pin_top_over_deck0 = door_bb.max.Z - L.Z_DECK0
    add("pin engagement into deck", round(pin_top_over_deck0, 3), f"mm (== pin_engage = {L.pin_engage})", abs(pin_top_over_deck0 - L.pin_engage) < 1e-6)

    # pin-to-charger and pin-to-battery-envelope minimum XY clearance >= 1.0, from parameters
    def _circle_to_box_clearance(cx, cy, r, bb):
        """Surface-to-surface XY clearance between a circle (pin) and an axis-aligned
        box (bounding box of a placed part), by the standard clamped-point distance."""
        dx = max(bb.min.X - cx, 0.0, cx - bb.max.X)
        dy = max(bb.min.Y - cy, 0.0, cy - bb.max.Y)
        return math.hypot(dx, dy) - r

    envelope_bb = parts["battery_swell_envelope"].bounding_box()
    pin_charger_clear = min(_circle_to_box_clearance(px, py, L.pin_d / 2, charger_bb) for px, py in L.pin_xy)
    add("pin to charger min XY clearance", round(pin_charger_clear, 3), "mm (>= 1.0)", pin_charger_clear >= 1.0)
    pin_batt_clear = min(_circle_to_box_clearance(px, py, L.pin_d / 2, envelope_bb) for px, py in L.pin_xy)
    add("pin to battery envelope min XY clearance", round(pin_batt_clear, 3), "mm (>= 1.0)", pin_batt_clear >= 1.0)

    # rib pilot inner wall: screw_r - m2_pilot/2 - rib_r0 >= 1.5
    pilot_inner_wall = L.screw_r - L.m2_pilot / 2 - L.rib_r0
    add("rib pilot inner wall", round(pilot_inner_wall, 3), "mm (>= 1.5)", pilot_inner_wall >= 1.5)

    # deck rim vs cone: deck DISC top z == Z_DECK1 (the cradle/pedestal ride well
    # above this; only the disc rim needs to meet the cone) and deck r <= sleeve_id/2 - 0.15
    disc_top_z = L._cyl_z(0, 0, L.Z_DECK0, L.Z_DECK1, L.deck_d).bounding_box().max.Z
    add("deck disc top z", round(disc_top_z, 3), f"mm (== Z_DECK1 = {L.Z_DECK1:.3f})", abs(disc_top_z - L.Z_DECK1) < 1e-3)
    add("deck max radius vs cone", round(L.deck_d / 2, 3), f"mm (<= sleeve_id/2 - 0.15 = {L.sleeve_id/2 - 0.15:.3f})", L.deck_d / 2 <= L.sleeve_id / 2 - 0.15)

    # door ribs vs sleeve ribs >= 0.4
    clearance = L.rib_r0 - 16.5
    add("door ribs vs sleeve ribs", round(clearance, 3), "mm (>= 0.4)", clearance >= 0.4)

    # lens height above seat == lens_above_seat
    add("lens height above seat", round(L.Z_LENS - L.Z_SEAT, 3), f"mm (== {L.lens_above_seat})", abs((L.Z_LENS - L.Z_SEAT) - L.lens_above_seat) < 1e-6)

    # overall height and diameter (informational); reach now includes the jack
    # housing instead of the old mounting tab (removed)
    add("overall height (Z_CAP1)", round(L.Z_CAP1, 3), "mm", True)
    add("overall body diameter (sleeve_od)", round(L.sleeve_od, 3), "mm", True)
    add("overall reach incl. jack flange (-X)", round(-L.jack_envelope_zero().bounding_box().min.X, 3), "mm", True)
    add("overall reach incl. jack brow (-X)", round(-(L.jack_x_outer - L.brow_proj), 3), "mm", True)

    # DC jack: cavity clearance around the (estimated) body >= 1.0 in y and z
    cav_y_clear = (L.jack_cavity_w - L.jack_body_d) / 2
    add("jack cavity clearance (y)", round(cav_y_clear, 3), "mm (>= 1.0)", cav_y_clear >= 1.0)
    cav_z_clear = (L.jack_cavity_h - L.jack_body_d) / 2
    add("jack cavity clearance (z)", round(cav_z_clear, 3), "mm (>= 1.0)", cav_z_clear >= 1.0)

    # DC jack: wire room from the lug ends (jack_envelope's inner/barrel+body end,
    # x -29.5) to the sleeve inner bore (x -25.5) >= 3.0
    lug_end_x = L.jack_envelope_zero().bounding_box().max.X   # -29.5
    bore_wall_x = -L.sleeve_id / 2                            # -25.5
    wire_room = bore_wall_x - lug_end_x
    add("wire room, lug ends to sleeve bore", round(wire_room, 3), "mm (>= 3.0)", wire_room >= 3.0)

    # DC jack: min X gap from the lug ends to the charger's JST plugs (x -12.7..-21) >= 5.0
    plug_gap = -21.0 - lug_end_x
    add("jack lug ends to charger plugs", round(plug_gap, 3), "mm (>= 5.0)", plug_gap >= 5.0)

    # rib bearing: deck material over the rib footprint after the twist, >= 90% of the test box
    box = L._box(-2.5, 2.5, 17.0, 25.3, L.Z_DECK0, L.Z_DECK0 + 0.5)
    box_vol = 5.0 * (25.3 - 17.0) * 0.5
    inter = _intersection(parts["deck"].wrapped, box.wrapped)
    fill = abs(_solid_volume(inter)) if inter is not None else 0.0
    frac = fill / box_vol
    add("rib bearing fill fraction", round(frac * 100, 2), "% (>= 90%)", frac >= 0.90)

    return rows_static


# --------------------------------------------------------------- 3. bayonet
def check_bayonet_path():
    print("## 3. Bayonet install path")
    sleeve = L.sleeve_zero()
    deck = L.deck_zero()
    charger = L.charger_zero()
    rows = []
    all_ok = True
    for t in range(0, 22, 2):
        d = deck.rotate(Axis.Z, -t)
        c = charger.rotate(Axis.Z, -t)
        vd = _volume(d, sleeve)
        vc = _volume(c, sleeve)
        ok = vd <= TOL and vc <= TOL and not (math.isnan(vd) or math.isnan(vc))
        rows.append((t, None, vd, vc, ok))
        print(f"  t={t:2d}  deck x sleeve={vd:.4f}  charger x sleeve={vc:.4f}  {'ok' if ok else 'FAIL'}")
        all_ok = all_ok and ok
    if not all_ok:
        FAILS.append("bayonet rotation sweep: nonzero intersection with sleeve")

    d20 = deck.rotate(Axis.Z, -20)
    c20 = charger.rotate(Axis.Z, -20)
    all_ok_dz = True
    for dz in range(0, 26, 2):
        d = Pos(0, 0, -dz) * d20
        c = Pos(0, 0, -dz) * c20
        vd = _volume(d, sleeve)
        vc = _volume(c, sleeve)
        ok = vd <= TOL and vc <= TOL and not (math.isnan(vd) or math.isnan(vc))
        rows.append((20, dz, vd, vc, ok))
        print(f"  t=20 dz={dz:2d}  deck x sleeve={vd:.4f}  charger x sleeve={vc:.4f}  {'ok' if ok else 'FAIL'}")
        all_ok_dz = all_ok_dz and ok
    if not all_ok_dz:
        FAILS.append("bayonet drop-in sweep (t=20, dz 0..24): nonzero intersection with sleeve")

    # door (with its anti-rotation pins) goes on last, straight up: z -25 .. 0 in 5 mm steps,
    # against the sleeve, deck, and charger (all already in their final positions).
    door = L.door_zero()
    door_rows = []
    all_ok_door = True
    for z in range(-25, 5, 5):
        d = Pos(0, 0, z) * door
        v_sleeve = _volume(d, sleeve)
        v_deck = _volume(d, deck)
        v_charger = _volume(d, charger)
        ok = all(not math.isnan(v) and v <= TOL for v in (v_sleeve, v_deck, v_charger))
        door_rows.append((z, v_sleeve, v_deck, v_charger, ok))
        print(f"  door z={z:4d}  x sleeve={v_sleeve:.4f}  x deck={v_deck:.4f}  x charger={v_charger:.4f}  {'ok' if ok else 'FAIL'}")
        all_ok_door = all_ok_door and ok
    if not all_ok_door:
        FAILS.append("door insertion sweep (z -25..0): nonzero intersection with sleeve/deck/charger")
    return rows, door_rows


# --------------------------------------------------------------- 4. camera insertion
def check_camera_insertion():
    print("## 4. Camera insertion (lip-trap check)")
    deck = L.deck_zero()
    camera = L.xiao_zero()
    rows = []
    ok_all = True
    for dz in (5, 25):
        cam = Pos(0, 0, dz) * camera
        v = _volume(cam, deck)
        ok = v <= TOL and not math.isnan(v)
        rows.append((dz, v, ok))
        print(f"  +{dz:2d} mm: camera x deck = {v:.4f}  {'ok' if ok else 'FAIL'}")
        ok_all = ok_all and ok
    if not ok_all:
        FAILS.append("camera insertion sweep: lips trap the board")
    return rows


# --------------------------------------------------------------- report
def write_checks_md(pairwise_bad, static_rows, bayonet_rows, door_rows, insertion_rows):
    lines = ["# tubecase checks\n"]
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

    lines.append("## 3. Bayonet install path\n\n")
    lines.append("Rotation sweep (deck+charger about Z by -t, intersect with sleeve):\n\n")
    lines.append("| t deg | dz mm | deck x sleeve | charger x sleeve | ok |\n|---|---|---|---|---|\n")
    for t, dz, vd, vc, ok in bayonet_rows:
        lines.append(f"| {t} | {dz if dz is not None else '-'} | {vd:.4f} | {vc:.4f} | {'ok' if ok else 'FAIL'} |\n")
    lines.append("\n")

    lines.append("Door insertion sweep (door + pins, straight up, z -25..0):\n\n")
    lines.append("| door z mm | x sleeve | x deck | x charger | ok |\n|---|---|---|---|---|\n")
    for z, vs, vd, vc, ok in door_rows:
        lines.append(f"| {z} | {vs:.4f} | {vd:.4f} | {vc:.4f} | {'ok' if ok else 'FAIL'} |\n")
    lines.append("\n")

    lines.append("## 4. Camera insertion\n\n| lift mm | camera x deck mm^3 | ok |\n|---|---|---|\n")
    for dz, v, ok in insertion_rows:
        lines.append(f"| {dz} | {v:.4f} | {'ok' if ok else 'FAIL'} |\n")
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
        bayonet_rows, door_rows = check_bayonet_path()
        insertion_rows = check_camera_insertion()
    except Exception as exc:  # noqa: BLE001 - fail closed on any exception
        print(f"EXCEPTION: {exc!r}", file=sys.stderr)
        Path("checks.md").write_text(f"# tubecase checks\n\nOverall: **FAIL** (exception)\n\n```\n{exc!r}\n```\n")
        raise

    write_checks_md(pairwise_bad, static_rows, bayonet_rows, door_rows, insertion_rows)
    print(f"\n{'PASS' if not FAILS else 'FAIL'}: {len(FAILS)} failing check(s). See checks.md.")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
