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
  head   the flex-mounted OV3660 head + lens: located by the COLLAR, so it
         does not travel with the PCB and does not swing with it on insertion
  card   the inserted microSD card
  board  everything else — the rigid PCB assembly that the bay must hold
so play and tilt sweeps move `board`, and the head is checked where the collar
holds it.  See INSERTION FEASIBILITY for what that costs.

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
    print("puckcase v2 — fail-closed fit check (DESIGN_v2.md §6)")
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
    print("\n-- 4. board (PCB assembly, head + card excluded) vs the printed "
          "parts")
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
    ALONG = [("-0.20 (stop ribs)", -0.20), ("nominal", 0.0),
             ("+0.20", 0.20), ("+0.40 (USB wall)", 0.40)]
    ACROSS = [("-0.15", -0.15), ("0.00", 0.0), ("+0.15 (rails)", 0.15)]
    runs = 0
    for ytag, dy in ALONG:
        for xtag, dx in ACROSS:
            post = None if (dx == 0.0 and dy == 0.0) else Pos(dx, dy, 0)
            b = L.xiao_vendor(post=post, parts="board", label="board")
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
                    fail(f"board (Y {dy:+.2f} X {dx:+.2f}) x {p.label} = "
                         f"{iv:.4f} mm^3 (limit {limit})")
                if ih > limit:
                    fail(f"header (Y {dy:+.2f} X {dx:+.2f}) x {p.label} = "
                         f"{ih:.4f} mm^3 (limit {limit})")
            tv = intersect_vol(tongue, b)
            rv = intersect_vol(ribs, b)
            if tv > CONTACT_TOL:
                fail(f"tongue x board (Y {dy:+.2f} X {dx:+.2f}) = {tv:.4f}")
            if rv > 3.0:
                fail(f"rail ribs x board (Y {dy:+.2f} X {dx:+.2f}) = {rv:.4f}")
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
        print(f"  camera head (collar-located, nominal) x {p.label:12s} "
              f"{iv:.4f} mm^3")
        if iv > TOL:
            fail(f"camera head x {p.label} = {iv:.4f} mm^3")
    card = L.xiao_vendor(parts="card", label="microsd_card")
    for p in (rigid, front, back):
        iv = intersect_vol(p, card)
        print(f"  microSD card (fitted, nominal) x {p.label:12s} "
              f"{iv:.4f} mm^3")
        if iv > TOL:
            fail(f"microSD card x {p.label} = {iv:.4f} mm^3")
    note("board/header/head/card vs printed, nominal + play extremes")

    # ------------------------------------------------------------------
    # 5. tilt insertion
    # ------------------------------------------------------------------
    print("\n-- 5. tilt insertion (board rotated about its far-edge PCB-back "
          "corner line)")
    tilt_runs = 0
    for ang in (-13, -8, -4):
        b = L.xiao_vendor(pre=L.tilt_loc(ang), parts="board",
                          label=f"board_tilt_{ang}")
        row = []
        for p in (rigid, back):
            iv = intersect_vol(p, b)
            row.append(f"{p.label} {iv:.4f}")
            if iv > TOL:
                fail(f"tilt {ang} deg x {p.label} = {iv:.4f} mm^3")
        crush = intersect_vol(ribs, b)
        row.append(f"rail ribs {crush:.4f} (deliberate crush)")
        if crush > 3.0:
            fail(f"tilt {ang} deg rail crush = {crush:.4f} mm^3")
        tilt_runs += 1
        print(f"  {ang:3d} deg   " + "   ".join(row) + "   (expect 0)")
    if tilt_runs != 3:
        fail("not every tilt angle was checked")

    # the far edge in the groove at 13 deg: hook underside -> ledge face
    slot = L.bZ(L.LEDGE_BZ[1]) - L.bZ(L.HOOK_BZ[0])
    need = L.PCB_T * math.cos(math.radians(13)) + 0.80 * math.sin(math.radians(13))
    print(f"  far-edge groove at 13 deg: slot {slot:.3f} vs "
          f"1.25*cos13 + 0.80*sin13 = {need:.3f}")
    if slot < need:
        fail(f"groove {slot:.3f} < required {need:.3f}")

    # the flex-mounted head fed straight back into the collar window
    SHORT = 1.30
    win_z = L.bZ(L.COLLAR_BZ[0])             # window entry plane, Z 8.36
    z_nom = _bb(L.xiao_vendor(parts="head"))[2]
    dz_short = (win_z + SHORT) - z_nom
    hs = L.xiao_vendor(parts="head", post=Pos(0, 0, dz_short),
                       label="head_short")
    iv = intersect_vol(rigid, hs)
    print(f"  head {SHORT:.2f} short of the window (front face Z "
          f"{win_z + SHORT:.2f}, +{dz_short:.2f} back) x ring: {iv:.4f} mm^3")
    if iv > TOL:
        fail(f"head {SHORT} short of the window x ring = {iv:.4f}")
    steps = [i * 0.25 for i in range(0, 33)]
    worst = 0.0
    for dz in steps:
        worst = max(worst, intersect_vol(
            rigid, L.xiao_vendor(parts="head", post=Pos(0, 0, dz),
                                 label=f"head_{dz}")))
    print(f"  head fed straight back 0..{steps[-1]:.1f} in "
          f"{len(steps)} steps x ring: worst {worst:.4f} mm^3  (expect 0)")
    if worst > TOL:
        fail(f"head straight-in sweep hits the ring: {worst:.4f} mm^3")
    note("tilt insertion -13/-8/-4 deg + groove + head entry")

    # ------------------------------------------------------------------
    # 6. named clearances
    # ------------------------------------------------------------------
    print("\n-- 6. named clearances (DESIGN_v2 §6.3)")
    B = L.B
    head_side = (L.COLLAR_WIN - (B.CAM_HEAD[2] - B.CAM_HEAD[0])) / 2
    bore_rad = (L.COLLAR_BORE_D - B.LENS_D) / 2
    gaps = [
        # DESIGN_v2 §1 sizes the head 8.3 square; the measured vendor STEP
        # says 8.0, so the built 8.6 window gives 0.30/side, not 0.15.
        ("collar window -> head, per side", head_side, 0.15, ">="),
        ("collar bore -> lens barrel, radial", bore_rad, 0.15, ">="),
        ("collar step -> head top (Z)", L.COLLAR_STEP_BZ - B.HEAD_TOP, 0.15, ">="),
        ("collar back face -> SD card top", L.COLLAR_BZ[0] - B.SD_CARD[5],
         0.50, ">="),
        ("collar back face -> SD socket", L.COLLAR_BZ[0] - B.SD_SOCKET[5],
         0.50, ">="),
        ("collar relief -> FPC roll", L.FPC_RELIEF_BZ - B.FPC_ROLL[5], 0.50, ">="),
        ("bridge face -> USB-C shell top", L.BRIDGE_BZ[0] - B.USB[5], 0.10, "=="),
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
        ("USB-end wall -> PCB end edge", -L.USB_BX[1], 0.40, "=="),
        ("card tip -> top wall inner face (roof)", L.CARD_ROOF, 4.00, "=="),
        ("lens tip -> plate inner face (Z)", L.LENS_TIP_Z - L.PLATE_T, 1.00, "=="),
        ("eave proud of the front plate face (Z)", -L.Z_EAVE, 8.00, "=="),
    ]
    for name, got, want, op in gaps:
        print(f"  {name:46s} {got:8.3f}   (contract {op} {want:.2f})")
        if op == "==" and abs(got - want) > 0.021:
            fail(f"{name}: {got:.3f} != contract {want:.2f}")
        if op == ">=" and got < want - 1e-9:
            fail(f"{name}: {got:.3f} < contract {want:.2f}")
    note("named clearances")

    # inflated-mock proofs: every listed part 0.30 clear of every printed part
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
    # 7. the snap tongue
    # ------------------------------------------------------------------
    print("\n-- 7. snap tongue (DESIGN_v2 §6.5)")
    reach = L.LIP_BX[1]
    slit_lo = L.bX(L.TONGUE_BY[1]) - L.bX(L.WIN_BY[1])
    slit_hi = L.bX(L.WIN_BY[0]) - L.bX(L.TONGUE_BY[0])
    strain = 3.0 * L.TONGUE_T * L.TONGUE_DEFL / (2.0 * L.TONGUE_L ** 2) * 100.0
    t_rows = [("lip reach over the PCB back edge", reach, 0.40, "=="),
              ("free gap beside the tongue, -X", slit_lo, 0.80, ">="),
              ("free gap beside the tongue, +X", slit_hi, 0.80, ">="),
              ("tongue thickness", L.TONGUE_T, 0.90, "=="),
              ("tongue free length", L.TONGUE_L, 8.70, "=="),
              ("outer-fibre strain at 0.60 deflection (%)", strain, 1.50, "<=")]
    for name, got, want, op in t_rows:
        print(f"  {name:44s} {got:8.3f}   (contract {op} {want:.2f})")
        if op == "==" and abs(got - want) > 0.021:
            fail(f"{name}: {got:.3f} != {want:.2f}")
        if op == ">=" and got < want - 1e-9:
            fail(f"{name}: {got:.3f} < {want:.2f}")
        if op == "<=" and got > want + 1e-9:
            fail(f"{name}: {got:.3f} > {want:.2f}")
    note("snap tongue")

    # ------------------------------------------------------------------
    # 8. eave brow, card roof, screws
    # ------------------------------------------------------------------
    print("\n-- 8. eave brow, card roof, screws")
    brow = math.degrees(math.atan2(L.IN_Y1 - L.LENS_YC, L.LENS_TIP_Z - L.Z_EAVE))
    boss_len = L.Z_PLATE - L.BOSS_Z0
    tip_z = L.BOSS_Z0 + L.SCREW_L
    pilot_bottom = L.Z_PLATE + L.PILOT_DEPTH
    engage = tip_z - L.Z_PLATE
    rows = [("eave brow angle above the lens axis (deg)", brow, 40.0, ">="),
            ("card roof to the top wall inner face", L.CARD_ROOF, 3.50, ">="),
            ("boss bore diameter", L.BOSS_BORE, 2.20, "=="),
            ("pilot diameter", L.PILOT_D, 1.70, "=="),
            ("pilot depth", L.PILOT_DEPTH, 3.40, "=="),
            ("boss length (screw head -> back plate)", boss_len, 10.50, "=="),
            ("M2 x 12 tip short of the pilot bottom", pilot_bottom - tip_z,
             0.30, ">="),
            ("M2 x 12 thread engagement in the back plate", engage, 1.50, "==")]
    for name, got, want, op in rows:
        print(f"  {name:44s} {got:8.3f}   (contract {op} {want:.2f})")
        if op == "==" and abs(got - want) > 0.021:
            fail(f"{name}: {got:.3f} != {want:.2f}")
        if op == ">=" and got < want - 1e-9:
            fail(f"{name}: {got:.3f} < {want:.2f}")
    if engage < 2.0:
        warn(f"M2 x 12 engages only {engage:.2f} mm of the back plate "
             f"(bosses are {boss_len:.1f} long).  DESIGN_v2 §5's alternative — "
             f"counterbore Ø4.4 x 4.5 in a Ø6.5 boss and keep M2 x 8 — or "
             f"M2 x 14 would give 3.5 mm.")
    note("brow / roof / screws")

    # ------------------------------------------------------------------
    # 9. overhang audit (DESIGN_v2 §6.7)
    # ------------------------------------------------------------------
    print("\n-- 9. overhang audit: planar faces steeper than 45 deg from "
          "vertical, in each part's print orientation")
    ORIENT = {"front_plate": (False, 0.0), "ring": (True, L.Z_PLATE),
              "back_plate": (False, L.Z_PLATE)}
    for p in printed:
        flip, bed = ORIENT[p.label]
        oh = overhang_faces(p, flip, bed)
        total = sum(a for a, _, _ in oh)
        print(f"  {p.label}: {len(oh)} faces, {total:.1f} mm^2 "
              f"(bed at Z {bed:.2f}, {'+Z is down' if flip else '-Z is down'}; "
              f"first-layer faces excluded)")
        for a, nz, bb in oh[:20]:
            print(f"      {a:7.2f} mm^2  n.down={nz:.2f}  "
                  f"X {bb[0]:.2f}..{bb[3]:.2f}  Y {bb[1]:.2f}..{bb[4]:.2f}  "
                  f"Z {bb[2]:.2f}..{bb[5]:.2f}")
        if len(oh) > 20:
            print(f"      ... {len(oh) - 20} more")
    note("overhang audit")

    # ------------------------------------------------------------------
    # 10. insertion feasibility (contract-level findings)
    # ------------------------------------------------------------------
    print("\n-- 10. insertion feasibility")
    card_sweep = max(
        intersect_vol(ring, L.xiao_vendor(pre=L.tilt_loc(a), parts="card",
                                          label=f"card_{a}"))
        for a in (-13, -8, -4, -1))
    print(f"  microSD card swept through the tilt range x ring: "
          f"{card_sweep:.2f} mm^3 (the bridge band)")
    travel_needed = B.SD_CARD[2] - B.SD_SOCKET[0]
    travel_have = L.CARD_ROOF
    print(f"  in-situ card insertion: needs {travel_needed:.2f} mm of straight "
          f"travel, the roof gives {travel_have:.2f} mm")
    head_sweep = intersect_vol(
        ring, L.xiao_vendor(pre=L.tilt_loc(-4), parts="head", label="head_rigid"))
    print(f"  head swung rigidly with the PCB at -4 deg x ring: "
          f"{head_sweep:.2f} mm^3 (it is flex-mounted, so it is fed in "
          f"separately)")
    if card_sweep > TOL:
        warn("DESIGN_v2 §2's order 'SD card in; tilt the board ~13 deg' is not "
             f"buildable: the card sweeps {card_sweep:.1f} mm^3 through the "
             "bridge band at any tilt > ~1 deg, and it cannot be fitted after "
             f"the board either ({travel_needed:.2f} mm of travel needed, "
             f"{travel_have:.2f} available).  Needs a contract decision: drop "
             "the bridge (the collar step already stops the USB end), or drop "
             "the board another 1.5 for the roof.")
    if head_sweep > TOL:
        warn(f"the camera head cannot swing in with the PCB ({head_sweep:.1f} "
             "mm^3 into the collar/bridge at -4 deg); it must be fed into the "
             "collar window by hand — consistent with DESIGN_v2 §1 'held only "
             "by its flex'.")
    note("insertion feasibility")

    # ------------------------------------------------------------------
    print("\n-- checks run: " + "; ".join(ran))
    if len(ran) != 12:
        fail(f"only {len(ran)}/12 check groups ran")
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
