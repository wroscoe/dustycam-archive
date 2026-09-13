"""Fail-closed interference / fit check for puckcase v1.

  ~/.claude/skills/cad/.venv/bin/python check.py

Every pair of occurrences whose bounding boxes overlap is intersected, solid
by solid (a Location applied to a multi-solid Compound is honoured by
bounding_box() but IGNORED by Shape.intersect() in this build123d, so nothing
is ever intersected as a compound).  The only pairs allowed a non-zero volume
are the two designed rib crushes and the four screws, which are mated into
their own bosses and pilots.

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
# At a pocket extreme the PCB is BY DEFINITION flat against a stop face
# (0.40 to the corner blocks, 0.35 to the stop ribs, 0.50 to the bay walls),
# so a coplanar-contact sliver is expected there and only there.  Anything
# above this is a real bite.  The nominal position still has to be < TOL.
CONTACT_TOL = 0.010
PRINTED = {"front_plate", "ring", "back_plate"}

failures = []
ran = []


def fail(msg):
    failures.append(msg)
    print("FAIL", msg)


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
        sa, sb = solid_bbs(a), solid_bbs(b)
        for s1, b1 in sa:
            for s2, b2 in sb:
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


def main():
    print("=" * 78)
    print("puckcase v1 — fail-closed fit check")
    print("=" * 78)

    # ------------------------------------------------------------------
    # 1. printable parts: exactly one valid solid each, expected bounds
    # ------------------------------------------------------------------
    printed = _fc.printed_parts()
    EXPECT_BB = {
        "front_plate": (0.0, 0.0, 0.0, L.OUT_W, L.LIP_Y1 + L.LIP_RIB_PROUD, L.POST_Z1),
        "ring":        (0.0, 0.0, L.Z_EAVE, L.OUT_W, L.OUT_H, L.Z_PLATE),
        "back_plate":  (0.0, 0.0, L.Z_PLATE, L.OUT_W, L.OUT_H, L.PUCK_LIP_Z1),
    }
    print("\n-- printable solids")
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
    # 2. designed crush reference, taken from the puck itself
    # ------------------------------------------------------------------
    print("\n-- designed crush reference (power_puck front_plate x tube)")
    puck_crush = intersect_vol(PUCK.front_plate(), PUCK.tube())
    print(f"power_puck front_plate x tube (6 ribs, {PUCK.LIP_RIB_H} tall): "
          f"{puck_crush:.4f} mm^3")
    front_expect = puck_crush * L.FRONT_RIB_H / PUCK.LIP_RIB_H
    print(f"front_plate x ring expected (same 6 ribs, {L.FRONT_RIB_H} tall): "
          f"{front_expect:.4f} mm^3 +/- 10 %")
    print(f"back_plate x puck_tube expected: {puck_crush:.4f} mm^3 +/- 2 % "
          f"(same lip, same tube)")
    note("crush reference")

    RIB_EXPECT = {
        frozenset({"front_plate", "ring"}): (front_expect * 0.90, front_expect * 1.10),
        frozenset({"back_plate", "puck_tube"}): (puck_crush * 0.98, puck_crush * 1.02),
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
    print(f"\n-- {len(occ)} occurrences, {len(pairs)} bound-overlapping pairs")
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
                  f"({'designed crush' if ok else 'UNEXPECTED'})")
            if not ok:
                fail(f"rib crush {a.label} x {b.label} {v:.4f} outside "
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

    # ring x back_plate is the joint the 4 screws make; assert it explicitly
    ring = next(o for o in printed if o.label == "ring")
    back = next(o for o in printed if o.label == "back_plate")
    v = intersect_vol(ring, back)
    print(f"\nring x back_plate: {v:.5f} mm^3 (expect 0 — screws are the only contact)")
    if v > TOL:
        fail(f"ring x back_plate = {v:.5f} mm^3")
    note("ring x back_plate")

    # ------------------------------------------------------------------
    # 4. vendor XIAO vs every printed part, nominal + pocket extremes
    # ------------------------------------------------------------------
    print("\n-- vendor XIAO STEP vs the printed parts (per-solid, transform baked)")
    SHIFTS = [("nominal", 0.0, 0.0)]
    for dx in (+0.50, -0.50):
        SHIFTS.append((f"case X {dx:+.2f}", dx, 0.0))
    for dy in (+0.40, -0.35):
        SHIFTS.append((f"case Y {dy:+.2f}", 0.0, dy))
    for dx in (+0.50, -0.50):
        for dy in (+0.40, -0.35):
            SHIFTS.append((f"case X {dx:+.2f} Y {dy:+.2f}", dx, dy))
    board_runs = 0
    for tag, dx, dy in SHIFTS:
        post = None if (dx == 0.0 and dy == 0.0) else Pos(dx, dy, 0)
        v = L.xiao_vendor(post=post, label=f"xiao_{tag}")
        limit = TOL if tag == "nominal" else CONTACT_TOL
        row = []
        for p in printed:
            iv = intersect_vol(p, v)
            row.append(f"{p.label} {iv:.4f}"
                       + ("*" if TOL < iv <= CONTACT_TOL else ""))
            if iv > limit:
                fail(f"XIAO ({tag}) x {p.label} = {iv:.4f} mm^3 (limit {limit})")
        board_runs += 1
        print(f"  {tag:22s} " + "   ".join(row) + "   (expect 0)")
    print(f"board positions checked: {board_runs}/{len(SHIFTS)}"
          f"   (* = stop-face contact sliver, <= {CONTACT_TOL} mm^3)")
    if board_runs != len(SHIFTS):
        fail("not every board position was checked")
    note("XIAO vs printed, nominal + extremes")

    # ------------------------------------------------------------------
    # 5. tilt insertion
    # ------------------------------------------------------------------
    print("\n-- tilt insertion (board rotated about its far-edge PCB-top corner line)")
    tilt_runs = 0
    for ang in (6, 8, 10):
        v = L.xiao_vendor(pre=L.tilt_loc(ang), label=f"xiao_tilt_{ang}")
        row = []
        for p in (ring, back):
            iv = intersect_vol(p, v)
            row.append(f"{p.label} {iv:.4f}")
            if iv > TOL:
                fail(f"tilt {ang} deg x {p.label} = {iv:.4f} mm^3")
        tilt_runs += 1
        print(f"  {ang:2d} deg   " + "   ".join(row) + "   (expect 0)")
    if tilt_runs != 3:
        fail("not every tilt angle was checked")
    note("tilt insertion 6/8/10 deg")

    # ------------------------------------------------------------------
    # 6. numeric gaps
    # ------------------------------------------------------------------
    print("\n-- numeric gaps")
    vend = L.xiao_vendor()
    vbb = _bb(vend)
    hook_gap = L.PCB_Z_TOP - L.HOOK_Z1
    post_gap = L.PCB_Z_TOP - L.POST_Z1
    ledge_overlap = L.LEDGE_REACH - L.POCKET_GAP
    x_play = (L.STOP_BX[0] - L.PCB_L) + (0.0 - L.BLOCK_BX[1])
    y_play = (L.BAY_FACE_Y[1] - L.PCB_W) + (0.0 - L.BAY_FACE_Y[0])
    lens_gap = vbb[2] - L.PLATE_T
    card_gap = L.IN_Y1 - vbb[4]
    head_to_nose = (L.BOSS_Z0 - L.SCREW_HEAD_T) - L.FRONT_LIP_Z1
    brow = math.degrees(math.atan2(L.IN_Y1 - L.LENS_YC, L.LENS_TIP_Z - L.Z_EAVE))
    lens_lateral = (L.LENS_HOLE_D - B_LENS_TIP_D) / 2
    btn_gap = min(L.B.BUTTONS["RST"][1] - L.POST_BY[1],
                  L.bmirror(*L.POST_BY)[0] - L.B.BUTTONS["BOOT"][3]) - L.POCKET_GAP
    exp_gap = L.STOP_Z0 - (L.Z_B0 - L.B.EXP[4])

    gaps = [
        ("hook underside -> PCB top (Z)", hook_gap, 0.20),
        ("front post -> PCB top (Z)", post_gap, 0.10),
        ("ledge overlap under the PCB", ledge_overlap, 0.95),
        ("board play along the case Y (board x)", x_play, 0.75),
        ("board play along the case X (board y)", y_play, 1.00),
        ("lens tip -> plate inner face (Z)", lens_gap, 1.00),
        ("card tip -> top wall inner face (Y)", card_gap, 0.50),
        ("screw head -> front lip nose (Z)", head_to_nose, None),
        ("lens tip radial -> hole wall, nominal", lens_lateral, None),
        ("eave brow half-angle from the lens tip (deg)", brow, None),
        ("RST/BOOT button -> front post (board y, extreme)", btn_gap, None),
        ("expansion board -> stop rib front face (Z)", exp_gap, None),
        ("eave proud of the front plate face (Z)", -L.Z_EAVE, 8.00),
    ]
    for name, got, want in gaps:
        tail = "" if want is None else f"   (contract {want:.2f})"
        print(f"  {name:46s} {got:8.3f}{tail}")
        if want is not None and abs(got - want) > 0.02:
            fail(f"{name}: {got:.3f} != contract {want:.2f}")
        if got < 0.0:
            fail(f"{name}: {got:.3f} < 0 (interference)")
    note("numeric gaps")

    # ------------------------------------------------------------------
    # 7. front-plate post landing area on the PCB
    # ------------------------------------------------------------------
    print("\n-- front-plate post landing area on the PCB")
    pcb = next(s for s in L.xiao_envelope().children if s.label == "env_base_pcb")
    areas = []
    for i, (by0, by1) in enumerate((L.POST_BY, L.bmirror(*L.POST_BY))):
        x0, y0, _, dx, dy, _ = L.bspan(L.POST_BX[0], L.POST_BX[1], by0, by1, 0, 0)
        column = L.box_at(x0, y0, L.Z_B0 - 5.0, dx, dy, 10.0)
        area = intersect_vol(column, pcb) / L.PCB_T
        areas.append(area)
        print(f"  post {i + 1}: {area:.3f} mm^2 on the PCB   (require >= 1.00)")
        if area < 1.0:
            fail(f"post {i + 1} landing area {area:.3f} mm^2 < 1.0")
    if len(areas) != 2:
        fail("post landing area not computed for both posts")
    note("post landing area")

    # ------------------------------------------------------------------
    print("\n-- checks run: " + "; ".join(ran))
    if len(ran) != 8:
        fail(f"only {len(ran)}/8 check groups ran")
    print()
    if failures:
        print(f"CHECK FAILED ({len(failures)} problems)")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("CHECK PASSED")


B_LENS_TIP_D = L.B.LENS_TOP_D

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
