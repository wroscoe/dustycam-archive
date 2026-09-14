"""Fail-closed interference / fit check for puckcase v2 (DESIGN_v2.md §6).

  ~/.claude/skills/cad/.venv/bin/python check.py

Every pair of occurrences whose bounding boxes overlap is intersected, solid
by solid (a Location applied to a multi-solid Compound is honoured by
bounding_box() but IGNORED by Shape.intersect() in this build123d, so nothing
is ever intersected as a compound).  The only pairs allowed a non-zero volume
are the designed crushes (two lip-rib sets, the rail crush ribs), the screws
mated into their own bosses/pilots and the LOAD lead soldered onto two header
pins — each with an explicit expected range.

v2 occurrence model (DESIGN_v2 §1 "the camera head is only held by its flex"):
the vendor STEP is split into
  head   the flex-mounted OV3660 head + lens: located by the FRONT PLATE's
         head window boss (v2.4; it was the ring's collar), so it does not
         travel with the PCB
  card   the inserted microSD card
  pcb    everything except the head — the rigid assembly the bay must hold,
         WITH the card fitted (v2.1: the card goes in before the board does)
so play and tilt sweeps move `pcb`, and the head is checked where the plate's
boss holds it.  v2.4 assembly order: board into the RING, then the plate is
pressed on and its head window drops over the head — group 5 sweeps the plate
along that path.  See INSERTION FEASIBILITY.

Any exception, NaN, split printable solid, unexpected volume or unrun check
fails the run with exit code 1.  An exception is never mapped to 0.
"""

import importlib.util
import math
import sys
from pathlib import Path

from build123d import Pos

import puckcase_lib as L        # sets up sys.path for the power_puck library
import caselib as PUCK          # noqa: E402  power_puck/caselib.py

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("fitcheck_step", HERE / "fitcheck.step.py")
_fc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fc)

TOL = 1e-4                      # mm^3, numerical noise floor
# At a play extreme the board is BY DEFINITION flat against a stop face, so a
# coplanar-contact sliver is expected there and only there.  Anything above
# this is a real bite.  The nominal position still has to be < TOL.
CONTACT_TOL = 0.050
CLEAR = 0.30                    # DESIGN_v2 §6.3 "-anything 0.3"
PRINTED = {"front_plate", "ring", "back_plate"}

failures = []
warnings = []
ran = []


def fail(msg):
    failures.append(msg)
    print("FAIL", msg)


def warn(msg):
    warnings.append(msg)
    print("WARN", msg)


def note(name):
    ran.append(name)


def vol(shape):
    v = shape.volume
    if v is None or math.isnan(v) or math.isinf(v):
        raise ValueError(f"bad volume {v}")
    return v


def _bb(s):
    b = s.bounding_box()
    return (b.min.X, b.min.Y, b.min.Z, b.max.X, b.max.Y, b.max.Z)


def _overlap(a, b, pad=0.0):
    return (a[0] <= b[3] + pad and b[0] <= a[3] + pad and
            a[1] <= b[4] + pad and b[1] <= a[4] + pad and
            a[2] <= b[5] + pad and b[2] <= a[5] + pad)


def bbox_overlap(a, b, pad=0.0):
    return _overlap(_bb(a), _bb(b), pad)


def solid_bbs(shape):
    """[(solid, bbox)] — every operand is exploded so no boolean ever runs
    against a located Compound."""
    return [(s, _bb(s)) for s in shape.solids()]


def intersect_vol(a, b):
    """Interference volume between two shapes, summed solid by solid."""
    try:
        total = 0.0
        for s1, b1 in solid_bbs(a):
            for s2, b2 in solid_bbs(b):
                if not _overlap(b1, b2):
                    continue
                common = s1.intersect(s2)
                if common is None:
                    continue
                if isinstance(common, (list, tuple)):
                    total += sum(vol(c) for c in common)
                else:
                    total += vol(common)
        return total
    except Exception as e:                                        # noqa: BLE001
        raise RuntimeError(
            f"intersect failed {getattr(a, 'label', a)} x {getattr(b, 'label', b)}: {e}"
        ) from e


def overhang_faces(part, up_is_minus_z, bed_z):
    """Planar faces whose downward tilt exceeds 45 deg in the part's print
    orientation, EXCLUDING the faces that lie on the bed (those are the first
    layer, not overhangs).  Returns [(area, normal_z, bbox)] worst first."""
    down = 1.0 if up_is_minus_z else -1.0     # the bed direction, in +Z terms
    out = []
    for f in part.faces():
        try:
            n = f.normal_at(f.center())
        except Exception:                                        # noqa: BLE001
            continue
        nz = n.Z * down
        if nz <= math.cos(math.radians(45.0)) + 1e-6:
            continue
        bb = _bb(f)
        if abs(bb[2] - bed_z) < 0.01 and abs(bb[5] - bed_z) < 0.01:
            continue                          # first layer, on the bed
        a = f.area
        if a > 0.05:
            out.append((a, nz, bb))
    out.sort(key=lambda t: -t[0])
    return out


def main():
    print("=" * 78)
    print("puckcase v2.4 — fail-closed fit check (DESIGN_v2.md §6 + §9 + §10)")
    print("=" * 78)

    # ------------------------------------------------------------------
    # 1. printable parts: exactly one valid solid each, expected bounds
    # ------------------------------------------------------------------
    printed = _fc.printed_parts()
    EXPECT_BB = {
        "front_plate": (0.0, 0.0, 0.0, L.OUT_W, L.LIP_Y1 + L.LIP_RIB_PROUD,
                        L.FRONT_LIP_Z1),
        "ring":        (0.0, 0.0, L.Z_EAVE, L.OUT_W, L.OUT_H, L.Z_PLATE),
        "back_plate":  (0.0, 0.0, L.Z_PLATE, L.OUT_W, L.OUT_H, L.PUCK_LIP_Z1),
    }
    print("\n-- 1. printable solids")
    for p in printed:
        n = len(p.solids())
        ok = p.is_valid
        bb = _bb(p)
        print(f"{p.label:12s} solids={n} valid={ok} volume={vol(p):9.2f} mm^3")
        print(f"{'':12s} bbox=({bb[0]:.3f}, {bb[1]:.3f}, {bb[2]:.3f}) .. "
              f"({bb[3]:.3f}, {bb[4]:.3f}, {bb[5]:.3f})")
        if n != 1 or not ok:
            fail(f"{p.label}: solids={n} valid={ok}")
        exp = EXPECT_BB[p.label]
        if max(abs(g - e) for g, e in zip(bb, exp)) > 0.02:
            fail(f"{p.label}: bbox {bb} != expected {exp}")
    note("printable solids + bounds")

    # ------------------------------------------------------------------
    # 2. designed crush references
    # ------------------------------------------------------------------
    print("\n-- 2. designed crush references")
    puck_crush = intersect_vol(PUCK.front_plate(), PUCK.tube())
    print(f"power_puck front_plate x tube (6 ribs, {PUCK.LIP_RIB_H} tall): "
          f"{puck_crush:.4f} mm^3")
    front_expect = puck_crush * L.FRONT_RIB_H / PUCK.LIP_RIB_H
    print(f"front_plate x ring expected (same 6 ribs, {L.FRONT_RIB_H} tall): "
          f"{front_expect:.4f} mm^3 +/- 10 %")
    print(f"back_plate x puck_tube expected: {puck_crush:.4f} mm^3 +/- 2 %")
    rib_crush = intersect_vol(L.rail_ribs(), L.xiao_vendor(parts="board"))
    print(f"4 rail crush ribs x expansion PCB edges: {rib_crush:.4f} mm^3 "
          f"(0.10/side nominal)")
    if not 0.5 <= rib_crush <= 3.0:
        fail(f"rail crush {rib_crush:.4f} outside (0.5, 3.0) mm^3")
    lead_joint = intersect_vol(L.lead_mock(), L.header_mock())
    print(f"LOAD lead x header pins (soldered joint, 2 pins): "
          f"{lead_joint:.4f} mm^3")
    note("crush references")

    RIB_EXPECT = {
        frozenset({"front_plate", "ring"}): (front_expect * 0.90, front_expect * 1.10),
        frozenset({"back_plate", "puck_tube"}): (puck_crush * 0.98, puck_crush * 1.02),
        frozenset({"ring", "xiao_vendor"}): (rib_crush * 0.98, rib_crush * 1.02),
        frozenset({"load_lead_mock", "header_mock"}): (lead_joint * 0.98,
                                                       lead_joint * 1.02),
    }

    # ------------------------------------------------------------------
    # 3. every bound-overlapping pair
    # ------------------------------------------------------------------
    refs = _fc.reference_parts()
    occ = printed + refs
    labels = [o.label for o in occ]
    if len(set(labels)) != len(labels):
        fail(f"duplicate labels: {labels}")
    SCREWS = {o.label for o in occ if o.label.startswith("screw_")}

    pairs = [(occ[i], occ[j])
             for i in range(len(occ)) for j in range(i + 1, len(occ))
             if bbox_overlap(occ[i], occ[j])]
    print(f"\n-- 3. {len(occ)} occurrences, {len(pairs)} bound-overlapping pairs")
    checked = 0
    screw_mated = 0.0
    for a, b in pairs:
        names = frozenset({a.label, b.label})
        v = intersect_vol(a, b)
        checked += 1
        if names in RIB_EXPECT:
            lo, hi = RIB_EXPECT[names]
            ok = lo <= v <= hi
            print(f"  {a.label:16s} x {b.label:16s} {v:9.4f} mm^3  "
                  f"({'designed contact' if ok else 'UNEXPECTED'})")
            if not ok:
                fail(f"designed contact {a.label} x {b.label} {v:.4f} outside "
                     f"({lo:.4f}, {hi:.4f})")
        elif (names & SCREWS) and (names & PRINTED):
            screw_mated += v
            print(f"  {a.label:16s} x {b.label:16s} {v:9.4f} mm^3  "
                  f"(MATED: screw in its own boss/pilot, excluded)")
        elif v > TOL:
            print(f"  {a.label:16s} x {b.label:16s} {v:9.4f} mm^3")
            fail(f"interference {a.label} x {b.label} = {v:.4f} mm^3")
        else:
            print(f"  {a.label:16s} x {b.label:16s} {v:9.4f} mm^3  (clear)")
    print(f"static pairs checked: {checked}/{len(pairs)}   "
          f"screw mated volume total: {screw_mated:.3f} mm^3")
    if checked != len(pairs):
        fail("not every bound-overlapping pair was checked")
    note("static pair sweep")

    ring = next(o for o in printed if o.label == "ring")
    back = next(o for o in printed if o.label == "back_plate")
    front = next(o for o in printed if o.label == "front_plate")
    v = intersect_vol(ring, back)
    print(f"\nring x back_plate: {v:.5f} mm^3 (expect 0 — screws are the only "
          f"contact)")
    if v > TOL:
        fail(f"ring x back_plate = {v:.5f} mm^3")
    note("ring x back_plate")

    # ------------------------------------------------------------------
    # 4. board vs the printed parts, nominal + play extremes
    # ------------------------------------------------------------------
    print("\n-- 4. board (PCB assembly + fitted microSD card, head excluded) "
          "vs the printed parts")
    print("   rigid ring = ring without the rail crush ribs and without the "
          "snap tongue")
    rigid = L.ring(ribs=False, tongue=False)
    rigid.label = "ring_rigid"
    ribs = L.rail_ribs()
    tongue = L.tongue_only()
    # DEVIATION: DESIGN_v2 §6.2 asks for +/- 0.3 along.  The bay's own stop
    # faces (§2/§3) are 0.20 to the far-end stop ribs and 0.40 to the USB-end
    # wall — 0.6 of travel, but asymmetric about nominal, so -0.30 is a
    # position the board cannot reach (it is 0.10 inside the stop ribs).  The
    # sweep uses the true stop faces instead, which is a superset of the
    # reachable set.
    # v2.2: there is no rigid +Y stop.  Y travel is 0.20 to the far-end stop
    # ribs and 0.20 to the two tongue faces (a soft stop).
    ALONG = [("-0.20 (stop ribs)", -0.20), ("nominal", 0.0),
             ("+0.20 (tongue faces, soft)", 0.20)]
    ACROSS = [("-0.15", -0.15), ("0.00", 0.0), ("+0.15 (rails)", 0.15)]
    runs = 0
    for ytag, dy in ALONG:
        for xtag, dx in ACROSS:
            post = None if (dx == 0.0 and dy == 0.0) else Pos(dx, dy, 0)
            b = L.xiao_vendor(post=post, parts="pcb", label="pcb")
            h = L.header_mock()
            if post is not None:
                h = L.header_mock()
                h = type(h)(children=[post * s for s in h.solids()])
                h.label = "header"
            limit = TOL if (dx == 0.0 and dy == 0.0) else CONTACT_TOL
            cells = []
            for p in (rigid, front, back):
                iv = intersect_vol(p, b)
                ih = intersect_vol(p, h)
                cells.append(f"{p.label} {iv:.4f}/{ih:.4f}")
                if iv > limit:
                    fail(f"pcb (Y {dy:+.2f} X {dx:+.2f}) x {p.label} = "
                         f"{iv:.4f} mm^3 (limit {limit})")
                if ih > limit:
                    fail(f"header (Y {dy:+.2f} X {dx:+.2f}) x {p.label} = "
                         f"{ih:.4f} mm^3 (limit {limit})")
            tv = intersect_vol(tongue, b)
            rv = intersect_vol(ribs, b)
            if tv > CONTACT_TOL:
                fail(f"tongue x pcb (Y {dy:+.2f} X {dx:+.2f}) = {tv:.4f}")
            if rv > 3.0:
                fail(f"rail ribs x pcb (Y {dy:+.2f} X {dx:+.2f}) = {rv:.4f}")
            runs += 1
            print(f"  Y {ytag:18s} X {xtag:14s} " + "  ".join(cells)
                  + f"  tongue {tv:.4f}  ribs {rv:.4f}")
    print(f"board positions checked: {runs}/{len(ALONG) * len(ACROSS)}   "
          f"(cells are board/header interference, expect 0)")
    if runs != len(ALONG) * len(ACROSS):
        fail("not every board position was checked")

    head = L.xiao_vendor(parts="head", label="camera_head")
    for p in (rigid, front, back):
        iv = intersect_vol(p, head)
        print(f"  camera head (head-window-located, nominal) x {p.label:12s} "
              f"{iv:.4f} mm^3")
        if iv > TOL:
            fail(f"camera head x {p.label} = {iv:.4f} mm^3")
    note("pcb/header/head vs printed, nominal + play extremes")

    # ------------------------------------------------------------------
    # 5. plate fitting sweep (v2.4): the plate, WITH its head window boss,
    #    pressed onto a fully populated ring
    # ------------------------------------------------------------------
    print("\n-- 5. plate fitting sweep (v2.4): the front plate stepped onto "
          "its seat")
    print("   the plate approaches from OUTSIDE the case (-Z) and travels +Z "
          "to seat;")
    print("   'short' is how far the plate still is from its seated position.")
    B0 = L.B
    fpc_roll = L.bbox_case(B0.FPC_ROLL[0], B0.FPC_ROLL[2],
                           B0.FPC_ROLL[1], B0.FPC_ROLL[3],
                           B0.FPC_ROLL[4], B0.FPC_ROLL[5])
    fpc_roll.label = "fpc_roll"
    SHORT = (8.0, 6.0, 4.0, 2.0, 1.0, 0.5, 0.0)
    # the chamfer mouth aperture the head must be inside of when the plate
    # arrives, so the 45 deg lead-in can only guide it in, never miss it
    APERTURE = L.COLLAR_WIN + 2 * L.COLLAR_WIN_CHAMFER          # 9.80
    HEAD_W = B0.CAM_HEAD[2] - B0.CAM_HEAD[0]                    # 8.00
    HEAD_H = B0.CAM_HEAD[3] - B0.CAM_HEAD[1]                    # 8.00
    plate_runs = 0
    guided = []
    for ytag, dy in ALONG:
        for xtag, dx in ACROSS:
            nominal = (dx == 0.0 and dy == 0.0)
            post = None if nominal else Pos(dx, dy, 0)
            mocks = [("pcb", L.xiao_vendor(post=post, parts="pcb",
                                           label="pcb")),
                     ("head", L.xiao_vendor(post=post, parts="head",
                                            label="head")),
                     ("card", L.xiao_vendor(post=post, parts="card",
                                            label="card"))]
            h = L.header_mock()
            r = fpc_roll
            if post is not None:
                h = type(h)(children=[post * s for s in h.solids()])
                h.label = "header"
                r = post * fpc_roll
                r.label = "fpc_roll"
            mocks += [("fpc_roll", r), ("header", h)]
            # the head's footprint must sit inside the chamfer mouth
            mx = (abs(dx) + HEAD_W / 2)
            my = (abs(dy) + HEAD_H / 2)
            margin = APERTURE / 2 - max(mx, my)
            if margin < 0.0:
                fail(f"head footprint outside the chamfer mouth at "
                     f"Y {dy:+.2f} X {dx:+.2f} (margin {margin:.3f})")
            worst = 0.0
            head_boss = 0.0
            for short in SHORT:
                # bake the offset into the SOLID (a Location on a Compound is
                # ignored by intersect(); the plate is one solid, so this is
                # the honest way to move it)
                pl = Pos(0, 0, -short) * front.solids()[0]
                pl.label = "front_plate"
                for name, mk in mocks:
                    v = intersect_vol(pl, mk) if bbox_overlap(pl, mk) else 0.0
                    if name == "head":
                        head_boss = max(head_boss, v)
                        if nominal and v > TOL:
                            fail(f"head x plate at {short:.1f} short "
                                 f"(nominal) = {v:.4f} mm^3")
                        continue
                    worst = max(worst, v)
                    limit = TOL if nominal else CONTACT_TOL
                    if v > limit:
                        fail(f"{name} x plate at {short:.1f} short "
                             f"(Y {dy:+.2f} X {dx:+.2f}) = {v:.4f} mm^3 "
                             f"(limit {limit})")
                plate_runs += 1
            if not nominal and head_boss > TOL:
                guided.append((dy, dx, head_boss))
            print(f"  Y {ytag:18s} X {xtag:14s} worst pcb/card/roll/header "
                  f"{worst:.4f}   head x boss {head_boss:.4f}   "
                  f"chamfer-mouth margin {margin:.3f}")
    print(f"  plate positions checked: {plate_runs}/"
          f"{len(SHORT) * len(ALONG) * len(ACROSS)}  "
          f"(7 approach steps x 9 board play positions)")
    if plate_runs != len(SHORT) * len(ALONG) * len(ACROSS):
        fail("not every plate approach step was checked")
    win_side = (L.COLLAR_WIN - HEAD_W) / 2
    bore_rad0 = (L.COLLAR_BORE_D - B0.LENS_D) / 2
    worst_shift = max(math.hypot(dx, dy) for _, dy in ALONG for _, dx in ACROSS)
    print(f"     8.60 window vs the 8.00 head: {win_side:.3f} per side "
          f"(>= the 0.20 / 0.15 play), so the square head never touches;")
    print(f"     Ø8.25 bore vs the Ø7.84 barrel: {bore_rad0:.3f} radial vs a "
          f"worst play-extreme radial shift of {worst_shift:.3f} — a barrel "
          f"contact, not a head-in-window one.")
    if guided:
        for dy, dx, v in guided:
            print(f"     guided by the chamfer: head x boss "
                  f"{v:.4f} mm^3 at Y {dy:+.2f} X {dx:+.2f}  (the head is "
                  f"carried rigidly with the PCB here, which it is not: "
                  f"DESIGN_v2 §9 C.9 — it hangs on its flex, the 45 deg "
                  f"lead-in and the bore recentre it and the flex takes up "
                  f"the difference)")
    else:
        print("     no head x boss contact at any play extreme")
    note("plate fitting sweep")

    # ------------------------------------------------------------------
    # 6. tilt insertion
    # ------------------------------------------------------------------
    print("\n-- 6. tilt insertion (board rotated about its far-edge PCB-back "
          "corner line)")
    print("   v2.1: the microSD card is FITTED and rides with the PCB")
    tilt_runs = 0
    for ang in (0, -2, -4, -8, -13):
        pre = None if ang == 0 else L.tilt_loc(ang)
        b = L.xiao_vendor(pre=pre, parts="pcb", label=f"pcb_tilt_{ang}")
        c = L.xiao_vendor(pre=pre, parts="card", label=f"card_tilt_{ang}")
        row = []
        for p in (rigid, back):
            iv = intersect_vol(p, b)
            row.append(f"{p.label} {iv:.4f}")
            if iv > TOL:
                fail(f"tilt {ang} deg pcb+card x {p.label} = {iv:.4f} mm^3")
        cv = intersect_vol(rigid, c)
        row.append(f"card alone {cv:.4f}")
        if cv > TOL:
            fail(f"tilt {ang} deg card x ring = {cv:.4f} mm^3")
        crush = intersect_vol(ribs, b)
        row.append(f"rail ribs {crush:.4f} (deliberate crush)")
        if crush > 3.0:
            fail(f"tilt {ang} deg rail crush = {crush:.4f} mm^3")
        tilt_runs += 1
        print(f"  {ang:3d} deg   " + "   ".join(row))
    if tilt_runs != 5:
        fail("not every tilt angle was checked")

    # the far edge in the groove at 13 deg: hook underside -> ledge face
    slot = L.bZ(L.LEDGE_BZ[1]) - L.bZ(L.HOOK_BZ[0])
    need = L.PCB_T * math.cos(math.radians(13)) + 0.80 * math.sin(math.radians(13))
    print(f"  far-edge groove at 13 deg: slot {slot:.3f} vs "
          f"1.25*cos13 + 0.80*sin13 = {need:.3f}")
    if slot < need:
        fail(f"groove {slot:.3f} < required {need:.3f}")

    # the two snap tongues during the swing: their cam ramps are designed to
    # be pushed, every other part of them must be clear of the swept board
    print("\n   snap tongues during the swing (cam ramp = designed contact, "
          "tongue BODY = must be 0):")
    body = tongue - L.tongue_cam_zone()
    body.label = "tongue_bodies"
    cam_runs = 0
    for ang in (0, -2, -4, -8, -13):
        pre = None if ang == 0 else L.tilt_loc(ang)
        b = L.xiao_vendor(pre=pre, parts="pcb", label=f"pcb_{ang}")
        bv = intersect_vol(body, b)
        cv = intersect_vol(tongue, b) - bv
        cam_runs += 1
        print(f"     {ang:3d} deg   cam ramps {cv:7.4f}   tongue bodies "
              f"{bv:7.4f}")
        if bv > TOL:
            fail(f"tongue body x swept board at {ang} deg = {bv:.4f} mm^3")
        if cv > 4.0:
            fail(f"tongue cam at {ang} deg = {cv:.4f} mm^3 (expect < 4)")
    if cam_runs != 5:
        fail("tongue swing not checked at every angle")

    # v2.4: with the collar gone there is nothing on the ring for the head to
    # be fed into, so the head may simply swing in RIGIDLY with the PCB and
    # must be clear of the ring at every angle.  (Up to v2.3 this was 1.89 mm^3
    # into the collar at -4 deg and the head had to be fed in separately.)
    print("\n   camera head swung RIGIDLY with the PCB x ring "
          "(v2.4: must be 0 at every angle — there is no collar to feed it "
          "into; the plate's head window drops over it afterwards):")
    head_runs = 0
    for ang in (0, -2, -4, -8, -13):
        pre = None if ang == 0 else L.tilt_loc(ang)
        hv = intersect_vol(rigid, L.xiao_vendor(pre=pre, parts="head",
                                                label=f"head_{ang}"))
        head_runs += 1
        print(f"     {ang:3d} deg   head x ring {hv:7.4f}")
        if hv > TOL:
            fail(f"head swung with the PCB at {ang} deg x ring = "
                 f"{hv:.4f} mm^3")
    if head_runs != 5:
        fail("rigid head swing not checked at every angle")

    note("tilt insertion 0/-2/-4/-8/-13 deg + groove + tongue swing + "
         "rigid head swing")

    # ------------------------------------------------------------------
    # 7. named clearances
    # ------------------------------------------------------------------
    print("\n-- 7. named clearances (DESIGN_v2 §6.3, §10)")
    print("   v2.4: the first eleven are features of the FRONT PLATE's head "
          "window boss")
    B = L.B
    head_side = (L.COLLAR_WIN - (B.CAM_HEAD[2] - B.CAM_HEAD[0])) / 2
    bore_rad = (L.COLLAR_BORE_D - B.LENS_D) / 2
    boss_ow = L.COLLAR_WIN + 2 * L.HEADWIN_WALL                 # 11.80 square
    gaps = [
        # v2.4: every one of these is now a feature of the FRONT PLATE's head
        # window boss, at the plate's seated position.  DESIGN_v2 §1 sizes the
        # head 8.3 square; the measured vendor STEP says 8.0, so the built 8.6
        # window gives 0.30/side, not 0.15.
        ("head window -> head, per side", head_side, 0.15, ">="),
        ("head window bore -> lens barrel, radial", bore_rad, 0.15, ">="),
        ("head window step -> head top (Z)",
         L.COLLAR_STEP_BZ - B.HEAD_TOP, 0.15, ">="),
        ("boss mouth -> SD card top", L.COLLAR_BZ[0] - B.SD_CARD[5],
         0.50, ">="),
        ("boss mouth -> SD socket", L.COLLAR_BZ[0] - B.SD_SOCKET[5],
         0.50, ">="),
        ("boss FPC relief -> FPC roll",
         L.FPC_RELIEF_BZ - B.FPC_ROLL[5], 0.50, ">="),
        # v2.4 siting of the boss: it stands free between the plate and the
        # board, inside the lip band's inner prism and well clear of the ring
        ("head window wall thickness", L.HEADWIN_WALL, 1.60, "=="),
        ("boss -> ring side wall inner face (X)",
         min((L.LENS_XC - boss_ow / 2) - L.BAY_IN_X[0],
             L.BAY_IN_X[1] - (L.LENS_XC + boss_ow / 2)), 0.30, ">="),
        ("boss -> ring far-end wall (Y)",
         (L.LENS_YC - boss_ow / 2) - L.bY(L.FAR_BX[1]), 0.30, ">="),
        ("boss -> plate lip band inner prism (BAY_Y1)",
         L.BAY_Y1 - (L.LENS_YC + boss_ow / 2), 0.30, ">="),
        # v2.1: the bridge is gone; the USB end's forward stop is the window
        # step, acting through head -> SD socket -> expansion PCB -> B2B -> PCB
        # (v2.4: it only exists once the plate is fitted)
        ("window step -> head top = USB-end stop (plate on)",
         L.COLLAR_STEP_BZ - B.HEAD_TOP, 0.20, "=="),
        ("hook underside -> PCB top", L.PCB_Z_TOP - L.bZ(L.HOOK_BZ[0]), 0.15, "=="),
        ("ledge face -> PCB back", L.bZ(L.LEDGE_BZ[1]) - L.Z_B0, 0.10, "=="),
        ("tongue lip -> PCB back", L.bZ(L.LIP_BZ[1]) - L.Z_B0, 0.10, "=="),
        ("rail face -> expansion PCB edge", B.EXP[1] - L.RAIL_BY, 0.15, "=="),
        ("rail rib crest into the expansion edge (crush)",
         (L.RAIL_BY + L.RIB_PROUD) - B.EXP[1], 0.10, "=="),
        ("rib crest -> FPC socket (board y)",
         B.FPC_CONN[1] - (L.RAIL_BY + L.RIB_PROUD), 0.22, "=="),
        ("far-end wall -> expansion PCB overhang", L.FAR_BX[0] - B.EXP[2],
         0.35, "=="),
        ("stop rib -> PCB far edge", L.STOP_BX[0] - L.PCB_L, 0.20, "=="),
        # v2.2: the wall is gone; the tongue faces are a soft +Y stop
        ("tongue face -> PCB end edge (soft +Y stop)", -L.TONGUE_BX[1],
         0.20, "=="),
        ("card tip -> top wall inner face (roof)", L.CARD_ROOF, 4.00, "=="),
        ("lens tip -> plate inner face (Z)", L.LENS_TIP_Z - L.PLATE_T, 1.00, "=="),
        ("eave proud of the front plate face (Z)", -L.Z_EAVE, 8.00, "=="),
    ]
    for name, got, want, op in gaps:
        print(f"  {name:50s} {got:8.3f}   (contract {op} {want:.2f})")
        if op == "==" and abs(got - want) > 0.021:
            fail(f"{name}: {got:.3f} != contract {want:.2f}")
        if op == ">=" and got < want - 1e-9:
            fail(f"{name}: {got:.3f} < contract {want:.2f}")
    note("named clearances")

    # inflated-mock proofs: every listed part 0.30 clear of every printed part
    # v2.1 check (b): forward travel of the whole board (head rigid) before a
    # stop catches it.  v2.4: WITH THE PLATE FITTED — the two stops are the
    # ring's far-end hooks and the plate boss's window step.
    step = 0.005
    travel = None
    caught_by = None
    allb = None
    for i in range(1, 201):
        dz = i * step
        allb = L.xiao_vendor(post=Pos(0, 0, -dz), parts="all",
                             label=f"all_fwd_{dz}")
        vr = intersect_vol(rigid, allb)
        vf = intersect_vol(front, allb)
        if vr > TOL or vf > TOL:
            travel = dz
            caught_by = "ring (far-end hooks)" if vr > TOL else \
                        "front plate (window step)"
            break
    print(f"\n   forward travel of the board (head rigid on the PCB, PLATE "
          f"FITTED) before a stop catches it: {travel:.3f} mm  "
          f"(contract <= 0.35)")
    print(f"      first contact: {caught_by}")
    print(f"      hooks (ring) at "
          f"{L.PCB_Z_TOP - L.bZ(L.HOOK_BZ[0]):.3f}, plate boss step at "
          f"{L.COLLAR_STEP_BZ - B.HEAD_TOP:.3f} — both stops, hooks first, "
          f"with the plate fitted")
    if travel is None:
        fail("forward travel sweep never contacted a stop")
    elif travel > 0.35 + 1e-9:
        fail(f"forward travel {travel:.3f} > 0.35")

    print(f"\n   0.30-clearance proofs (mock inflated by {CLEAR}, expect 0 "
          f"interference)")
    inflated = [("header body + pins", L.header_mock(inflate=CLEAR)),
                ("U.FL plug (+1.3 z)", L.ufl_plug_mock(inflate=CLEAR)),
                ("U.FL cable path Ø1.2", L.cable_mock(inflate=CLEAR))]
    inflated += [(m.label, m) for m in L.button_mocks(inflate=CLEAR)]
    n_inf = 0
    for name, m in inflated:
        tot = sum(intersect_vol(p, m) for p in printed)
        n_inf += 1
        print(f"     {name:24s} x all printed: {tot:.4f} mm^3")
        if tot > TOL:
            fail(f"{name} is closer than {CLEAR} to a printed part "
                 f"({tot:.4f} mm^3 when inflated)")
    if n_inf != 5:
        fail(f"only {n_inf}/5 inflated mocks checked")
    note("0.30 clearance proofs")

    # ------------------------------------------------------------------
    # 8. the snap tongue
    # ------------------------------------------------------------------
    print("\n-- 8. snap tongues (DESIGN_v2 §6.5, two pillar tongues, v2.3 root)")
    pcb_solid = next(sld for sld in L.xiao_envelope().children
                     if sld.label == "env_base_pcb")
    reach = L.LIP_BX[1]
    strain = 3.0 * L.TONGUE_T * L.TONGUE_DEFL / (2.0 * L.TONGUE_L ** 2) * 100.0
    inertia_per_mm = L.TONGUE_T ** 3 / 12.0
    total_force = 0.0
    n_tongue = 0
    edges = [_bb(t) for t in tongue.solids()]
    for i, (by0, by1) in enumerate(L.TONGUE_BYS):
        col = L.box_at(L.bX(by1), L.bY(reach), L.Z_B0 - 5.0,
                       by1 - by0, reach, 10.0)
        area = intersect_vol(col, pcb_solid) / L.PCB_T
        eff = area / reach
        lo = max(by0, L.PCB_STRAIGHT_BY[0])
        hi = min(by1, L.PCB_STRAIGHT_BY[1])
        straight = max(0.0, hi - lo)
        width = by1 - by0
        force = (3.0 * L.E_PETG * width * inertia_per_mm * L.TONGUE_DEFL
                 / L.TONGUE_L ** 3)
        total_force += force
        n_tongue += 1
        print(f"  tongue {i + 1} (board y {by0:+.2f}..{by1:+.2f}, "
              f"case X {L.bX(by1):.3f}..{L.bX(by0):.3f}, {width:.2f} wide)")
        print(f"     lip bearing on the PCB back      {area:7.4f} mm^2 "
              f"({eff:.3f} effective length)")
        print(f"     on the STRAIGHT end edge         {straight:7.3f} mm   "
              f"(require >= 1.90; PCB corners are R{L.PCB_R})")
        print(f"     snap force at {L.TONGUE_DEFL} deflection    "
              f"{force:7.2f} N     (E = {L.E_PETG:.0f} MPa, PETG)")
        if straight < 1.90 - 1e-9:
            fail(f"tongue {i + 1} straight-edge overlap {straight:.3f} < 1.90")
        if area < 1.0:
            fail(f"tongue {i + 1} lip bearing {area:.4f} mm^2 < 1.0")
    if n_tongue != 2:
        fail(f"only {n_tongue}/2 tongues checked")
    gap_lo = min(e[0] for e in edges) - L.BAY_IN_X[0]
    gap_hi = L.BAY_IN_X[1] - max(e[3] for e in edges)
    t_rows = [("lip reach over the PCB back edge", reach, 0.40, "=="),
              ("free gap, tongue 2 -> -X side wall", gap_lo, 0.80, ">="),
              ("free gap, tongue 1 -> +X side wall", gap_hi, 0.80, ">="),
              ("tongue thickness", L.TONGUE_T, 0.80, "=="),
              ("tongue free length", L.TONGUE_L, 7.40, "=="),
              ("root strip height", L.STRIP_H, 1.50, "=="),
              ("root strip thickness", L.STRIP_T, 1.40, "=="),
              ("clear of the USB-C shell, tongue 1 (board y)",
               B.USB[1] - L.TONGUE_BYS[0][1], 0.50, ">="),
              ("clear of the USB-C shell, tongue 2 (board y)",
               L.TONGUE_BYS[1][0] - B.USB[3], 0.50, ">="),
              ("outer-fibre strain at 0.60 deflection (%)", strain, 1.50, "<="),
              ("total snap force, both tongues (N)", total_force, 0.0, ">=")]
    for name, got, want, op in t_rows:
        print(f"  {name:44s} {got:8.3f}   (contract {op} {want:.2f})")
        if op == "==" and abs(got - want) > 0.021:
            fail(f"{name}: {got:.3f} != {want:.2f}")
        if op == ">=" and got < want - 1e-9:
            fail(f"{name}: {got:.3f} < {want:.2f}")
        if op == "<=" and got > want + 1e-9:
            fail(f"{name}: {got:.3f} > {want:.2f}")
    # v2.3: the root strip must not be the hinge.  Report both compliance
    # modes of the strip that carries both tongue roots.
    force1 = total_force / 2.0
    moment = force1 * L.TONGUE_L
    span = L.BAY_IN_X[1] - L.BAY_IN_X[0]
    xc = (L.bX(L.TONGUE_BYS[0][1]) + L.bX(L.TONGUE_BYS[0][0])) / 2.0
    a = min(L.BAY_IN_X[1] - xc, xc - L.BAY_IN_X[0])
    b = span - a
    i_strip = L.STRIP_H * L.STRIP_T ** 3 / 12.0
    d_bend = force1 * a ** 3 * b ** 3 / (3.0 * L.E_PETG * i_strip * span ** 3)
    big, small = max(L.STRIP_T, L.STRIP_H), min(L.STRIP_T, L.STRIP_H)
    ratio = big / small
    beta = 0.1406 + (0.1661 - 0.1406) * min(1.0, (ratio - 1.0) / 0.2)
    j_strip = beta * big * small ** 3
    g_mod = L.E_PETG / (2.0 * (1.0 + L.NU_PETG))
    k_tors = g_mod * j_strip * (1.0 / a + 1.0 / b)
    d_tors = (moment / k_tors) * L.TONGUE_L
    k_t = force1 / L.TONGUE_DEFL
    k_s = force1 / (d_bend + d_tors)
    k_series = 1.0 / (1.0 / k_t + 1.0 / k_s)
    f_series = k_series * L.TONGUE_DEFL
    print(f"\n  root strip: {L.STRIP_T:.2f} thick x {L.STRIP_H:.2f} tall, "
          f"wall to wall over {span:.2f}, carrying both tongue roots")
    print(f"     strip BENDING under the root shear {force1:.2f} N "
          f"(fixed-fixed, load at a = {a:.2f}): {d_bend:.4f} mm at the lip"
          f"   (contract < 0.05)")
    print(f"     strip TORSION under the root moment {moment:.2f} N.mm "
          f"(J = {j_strip:.3f}, G = {g_mod:.0f}): {d_tors:.4f} mm at the lip")
    print(f"     -> tongue alone {k_t:.2f} N/mm, strip {k_s:.2f} N/mm, "
          f"series {k_series:.2f} N/mm; snap force at 0.6 of total travel "
          f"{f_series:.2f} N per tongue")
    if d_bend > 0.05:
        fail(f"strip bending compliance {d_bend:.4f} >= 0.05 mm")
    if L.STRIP_H < 1.40:
        fail(f"root strip only {L.STRIP_H:.2f} tall — it would be the hinge")
    print("  removal: press BOTH tongues outward through the back mouth")
    note("snap tongue")

    # ------------------------------------------------------------------
    # 9. eave brow, card roof, screws
    # ------------------------------------------------------------------
    print("\n-- 9. eave brow, card roof, screws")
    brow = math.degrees(math.atan2(L.IN_Y1 - L.LENS_YC, L.LENS_TIP_Z - L.Z_EAVE))
    boss_len = L.Z_PLATE - L.BOSS_Z0
    tip_z = L.BOSS_Z0 + L.SCREW_L
    pilot_bottom = L.Z_PLATE + L.PILOT_DEPTH
    engage = tip_z - L.Z_PLATE
    rows = [("eave brow angle above the lens axis (deg)", brow, 40.0, ">="),
            ("card roof to the top wall inner face", L.CARD_ROOF, 3.50, ">="),
            ("boss bore diameter", L.BOSS_BORE, 2.20, "=="),
            ("boss diameter", L.BOSS_D, 5.50, "=="),
            ("pilot diameter", L.PILOT_D, 1.70, "=="),
            ("pilot depth", L.PILOT_DEPTH, 3.40, "=="),
            ("boss length (screw head -> back plate)", boss_len, 9.00, "=="),
            ("M2 x 12 thread engagement in the back plate", engage, 3.00, ">="),
            ("M2 x 12 tip short of the pilot bottom", pilot_bottom - tip_z,
             0.30, ">="),
            ("screw head -> front lip nose (driver reach)",
             (L.BOSS_Z0 - L.SCREW_HEAD_T) - L.FRONT_LIP_Z1, 0.0, ">=")]
    for name, got, want, op in rows:
        print(f"  {name:44s} {got:8.3f}   (contract {op} {want:.2f})")
        if op == "==" and abs(got - want) > 0.021:
            fail(f"{name}: {got:.3f} != {want:.2f}")
        if op == ">=" and got < want - 1e-9:
            fail(f"{name}: {got:.3f} < {want:.2f}")

    # driver access: nothing crosses a boss axis between the front mouth and
    # the boss top
    print("   driver access down each boss axis (Ø5.5 column, "
          f"Z {L.PLATE_T:.2f}..{L.BOSS_Z0:.2f}):")
    access = 0
    for i, (bx, by) in enumerate(L.BOSS_XY):
        col = L.cyl_at(bx, by, L.PLATE_T, L.BOSS_D, L.BOSS_Z0 - L.PLATE_T)
        v = intersect_vol(ring, col)
        access += 1
        print(f"     boss {i + 1} at ({bx:.2f}, {by:.2f}): {v:.4f} mm^3 "
              f"(expect 0)")
        if v > TOL:
            fail(f"boss {i + 1} driver access blocked by {v:.4f} mm^3")
    if access != 4:
        fail("driver access not checked on all 4 bosses")
    note("brow / roof / screws")

    # ------------------------------------------------------------------
    # 10. overhang audit (DESIGN_v2 §6.7, §10)
    # ------------------------------------------------------------------
    print("\n-- 10. overhang audit: planar faces steeper than 45 deg from "
          "vertical, in each part's print orientation")
    ORIENT = {"front_plate": (False, 0.0), "ring": (True, L.Z_PLATE),
              "back_plate": (False, L.Z_PLATE)}
    # v2.3, from the committed checks.md — the baseline v2.4 has to beat
    BEFORE = {"front_plate": 1.3, "ring": 253.4, "back_plate": 9.1}
    # v2.4 budget: the ring keeps only the hook undersides (1.37 + 1.36), the
    # four rail rib crests (0.75 each) and the cord slot's 1.5 mm flat (3.60);
    # the head window boss must add NOTHING to the plate.
    AFTER_MAX = {"front_plate": BEFORE["front_plate"] + 0.05,
                 "ring": 12.0, "back_plate": BEFORE["back_plate"] + 0.05}
    for p in printed:
        flip, bed = ORIENT[p.label]
        oh = overhang_faces(p, flip, bed)
        total = sum(a for a, _, _ in oh)
        print(f"  {p.label}: {len(oh)} faces, {total:.1f} mm^2 "
              f"(v2.3 was {BEFORE[p.label]:.1f}; budget "
              f"<= {AFTER_MAX[p.label]:.1f}) "
              f"(bed at Z {bed:.2f}, {'+Z is down' if flip else '-Z is down'}; "
              f"first-layer faces excluded)")
        for a, nz, bb in oh[:20]:
            print(f"      {a:7.2f} mm^2  n.down={nz:.2f}  "
                  f"X {bb[0]:.2f}..{bb[3]:.2f}  Y {bb[1]:.2f}..{bb[4]:.2f}  "
                  f"Z {bb[2]:.2f}..{bb[5]:.2f}")
        if len(oh) > 20:
            print(f"      ... {len(oh) - 20} more")
        if total > AFTER_MAX[p.label] + 1e-9:
            fail(f"{p.label} overhang {total:.1f} mm^2 > budget "
                 f"{AFTER_MAX[p.label]:.1f}")
    print("  accepted (no change asked, each is a sub-4 mm^2 tab or a short "
          "bridge anchored at both ends): far-end hook undersides 2.1 x 0.65 "
          "each, the four rail rib crests 0.25 x 4.0 each, the cord slot's "
          "1.5 mm flat roof, and the back plate's four Ø1.7 pilot bottoms.")
    note("overhang audit")

    # ------------------------------------------------------------------
    # 11. insertion feasibility (contract-level findings)
    # ------------------------------------------------------------------
    print("\n-- 11. insertion feasibility")
    card_sweep = max(
        intersect_vol(rigid, L.xiao_vendor(pre=L.tilt_loc(a), parts="card",
                                           label=f"card_{a}"))
        for a in (-13, -8, -4, -1))
    print(f"  microSD card fitted, swept through the tilt range x ring: "
          f"{card_sweep:.4f} mm^3  (v2.1: the bridge band is gone)")
    if card_sweep > TOL:
        fail(f"the fitted card still fouls the ring: {card_sweep:.4f} mm^3")
    head_sweep = max(
        intersect_vol(rigid, L.xiao_vendor(pre=L.tilt_loc(a), parts="head",
                                           label=f"head_rigid_{a}"))
        for a in (-13, -8, -4, -2))
    print(f"  head swung rigidly with the PCB, worst of -2/-4/-8/-13 deg "
          f"x ring: {head_sweep:.4f} mm^3")
    print(f"     v2.4: the collar is gone, so the head needs no separate "
          f"straight-in feed — it rides in with the board and the front "
          f"plate's head window drops over it (group 5).  Hard-checked in "
          f"group 6.")
    if head_sweep > TOL:
        fail(f"head swung with the PCB fouls the ring: {head_sweep:.4f} mm^3")
    note("insertion feasibility")

    # ------------------------------------------------------------------
    print("\n-- checks run: " + "; ".join(ran))
    if len(ran) != 13:
        fail(f"only {len(ran)}/13 check groups ran")
    print()
    if warnings:
        print(f"{len(warnings)} WARNING(S) — contract-level, not geometry:")
        for w in warnings:
            print(" *", w)
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
    except SystemExit:
        raise
    except Exception as e:                                        # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("CHECK FAILED (exception):", repr(e))
        sys.exit(1)
