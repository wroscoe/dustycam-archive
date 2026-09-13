"""puckcase v1 — XIAO ESP32S3 Sense camera case that plugs into the power puck.

Geometry library for the three printed parts (front_plate, ring, back_plate)
plus the reference occurrences used by check.py / fitcheck.step.py.

Frame (case-local, per DESIGN.md):
  X  0 at the -X outer face .. 47.21
  Y  0 at the bottom outer face .. 80.80 (up)
  Z  0 at the outer FRONT face, +Z toward the puck.

The puck's own frame is ours shifted by Z_BACK - caselib.Z_TUBE0, so the puck
tube's front mouth face lands on Z_BACK.  Everything the case shares with the
puck (OUT/IN/LIP/BAY rectangles, radii, LIP_ENG, rib layout, crush ribs) is
IMPORTED from hardware/power_puck/caselib.py + fits.py, never copied.

Board frame (vendor STEP): origin base-PCB plan bottom-left, +x along the long
edge from the USB-C end, z = 0 PCB bottom, lens +z.  See BOARD_* below for how
it maps into the case frame (and DEVIATIONS for why board y -> case -X).
"""

import functools
import sys
from pathlib import Path

from build123d import (  # noqa: F401
    Align, Box, Circle, Compound, Cylinder, Location, Plane, Pos, Rot,
    RectangleRounded, extrude, import_step, loft,
)

HERE = Path(__file__).resolve().parent
_ROOT = HERE.parents[3]                       # .../dustycam
_PUCK = _ROOT / "hardware" / "power_puck"
_REF = _ROOT / "cameras" / "xiao_pantilt" / "ref"
for _p in (str(_PUCK), str(_REF / "tripodcase")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import caselib as P            # noqa: E402  the power puck's geometry library
import fits                    # noqa: E402  shared fit constants / crush rib
import xiao_board_ref as B     # noqa: E402  measured XIAO feature boxes

prism = P.prism
flare_down = P.flare_down
flare_up = P.flare_up
slot_y = P.slot_y
cyl_at = P.cyl_at
box_at = P.box_at

# ---------------------------------------------------------------------------
# Shell — the puck's own outline, imported wholesale
# ---------------------------------------------------------------------------
OUT_W, OUT_H = P.OUT_W, P.OUT_H            # 47.21 x 80.80
WALL, R_OUT = P.WALL, P.R_OUT              # 2.40, 6.00
CX = P.CX                                  # 23.605
CY = P.CY                                  # 40.40  (puck rib layout reference)
LIP_WALL, LIP_GAP = P.LIP_WALL, P.LIP_GAP  # 1.60, 0.15
LIP_ENG, LIP_RIB_H = P.LIP_ENG, P.LIP_RIB_H
LIP_RIB_PROUD = P.LIP_RIB_PROUD
LEADIN = P.LEADIN                          # 0.60
EFOOT = fits.ELEPHANT_FOOT                 # 0.40

OUT_X0, OUT_Y0, OUT_X1, OUT_Y1 = P.OUT_X0, P.OUT_Y0, P.OUT_X1, P.OUT_Y1
IN_X0, IN_Y0, IN_X1, IN_Y1, R_IN = P.IN_X0, P.IN_Y0, P.IN_X1, P.IN_Y1, P.R_IN
LIP_X0, LIP_Y0, LIP_X1, LIP_Y1, R_LIP = P.LIP_X0, P.LIP_Y0, P.LIP_X1, P.LIP_Y1, P.R_LIP
BAY_X0, BAY_Y0, BAY_X1, BAY_Y1, R_BAY = P.BAY_X0, P.BAY_Y0, P.BAY_X1, P.BAY_Y1, P.R_BAY

Y_SHOULDER = OUT_H - R_OUT                 # 74.80  outline break / eave root

# ---------------------------------------------------------------------------
# Z stack
# ---------------------------------------------------------------------------
PLATE_T = 2.40                             # front plate, Z 0..2.40
LENS_GAP = 1.00
Z_B0 = PLATE_T + LENS_GAP + B.STACK_TOP    # 17.36  PCB bottom (board z = 0)
WIRE_GAP = 3.00                            # PCB underside -> back plate face
Z_PLATE = Z_B0 + WIRE_GAP                  # 20.36  ring back mouth / plate front
BACK_T = 4.00
Z_BACK = Z_PLATE + BACK_T                  # 24.36  puck tube front mouth face
PUCK_LIP_Z0, PUCK_LIP_Z1 = Z_BACK, Z_BACK + LIP_ENG          # 24.36 .. 31.86

EAVE = 8.00
Z_EAVE = -EAVE                             # -8.00  eave front edge
DRIP_W, DRIP_D, DRIP_BACK = 1.00, 0.80, 1.50
DRIP_Z0 = Z_EAVE + DRIP_BACK               # -6.50
DRIP_Z1 = DRIP_Z0 + DRIP_W                 # -5.50

FRONT_LIP = 6.00
FRONT_LIP_Z0, FRONT_LIP_Z1 = PLATE_T, PLATE_T + FRONT_LIP    # 2.40 .. 8.40
FRONT_RIB_H = 4.90

Z_TUBE_SHIFT = Z_BACK - P.Z_TUBE0          # 21.96  puck frame -> case frame

# ---------------------------------------------------------------------------
# Board placement (board -> case)
# ---------------------------------------------------------------------------
# DESIGN.md writes the mapping as  board x -> case -Y, board y -> case +X,
# board z -> case -Z.  That triple is IMPROPER (determinant -1): it is a
# mirror, not a rigid placement, so it cannot be built.  With "USB end up"
# (x -> -Y) and "lens forward" (z -> -Z) fixed, handedness forces
# board y -> case -X.  The lens axis is kept on CX (the contract's
# LENS_HOLE centre and X_B0 = CX - 8.25 intent); the consequence is that the
# board bay is mirrored about CX relative to the literal DESIGN.md numbers.
# The bay itself is symmetric about board y = 8.89 (every bay feature is
# given "(mirror 17.78)"), so only its case-X position changes.
X_B0 = CX + B.CAM_C[1]                     # 31.855  case X of board y = 0
Y_B0 = OUT_H - WALL - 3.61                 # 74.79   case Y of board x = 0
POCKET_GAP = 0.50

PCB_L, PCB_W, PCB_T = B.PCB_L, B.PCB_W, B.PCB_T          # 20.95, 17.78, 1.25
PCB_R = B.PCB_R
BOARD_MIRROR_Y = PCB_W                     # bay features mirror about y = 8.89

# board unit vectors -> case:  x^ -> (0,-1,0), y^ -> (-1,0,0), z^ -> (0,0,-1)
BOARD_LOC = Pos(X_B0, Y_B0, Z_B0) * Rot(0, 180, 0) * Rot(0, 0, -90)


def board_to_case(bx=0.0, by=0.0, bz=0.0):
    """A board-frame point as a case-frame (x, y, z) tuple."""
    return (X_B0 - by, Y_B0 - bx, Z_B0 - bz)


def bspan(x0, x1, y0, y1, z0, z1):
    """A board-frame axis-aligned box -> case-frame (X0, Y0, Z0, dX, dY, dZ)."""
    cx0, cx1 = sorted((X_B0 - y0, X_B0 - y1))
    cy0, cy1 = sorted((Y_B0 - x0, Y_B0 - x1))
    cz0, cz1 = sorted((Z_B0 - z0, Z_B0 - z1))
    return cx0, cy0, cz0, cx1 - cx0, cy1 - cy0, cz1 - cz0


def bbox_case(x0, x1, y0, y1, z0, z1):
    """A board-frame box as a case-frame solid."""
    return box_at(*bspan(x0, x1, y0, y1, z0, z1))


def bmirror(y0, y1):
    """Mirror a board-y span about the PCB centre line (y = 8.89)."""
    return BOARD_MIRROR_Y - y1, BOARD_MIRROR_Y - y0


# derived board landmarks, in the case frame
PCB_X0, PCB_X1 = X_B0 - PCB_W, X_B0                       # 14.075 .. 31.855
PCB_Y0, PCB_Y1 = Y_B0 - PCB_L, Y_B0                       # 53.84 .. 74.79
PCB_Z_TOP = Z_B0 - PCB_T                                  # 16.11 (toward front)
LENS_XC, LENS_YC = board_to_case(B.CAM_C[0], B.CAM_C[1])[:2]   # 23.605, 71.26
LENS_TIP_Z = Z_B0 - B.STACK_TOP                           # 3.40

# ---------------------------------------------------------------------------
# Ring bay (all in board coordinates; DESIGN.md "Parameters")
# ---------------------------------------------------------------------------
BAY_T, BAY_Z0 = 1.60, 9.00
BAY_FACE_Y = (-POCKET_GAP, PCB_W + POCKET_GAP)            # -0.50, 18.28
BAY_BX0, BAY_BX1 = -3.61, 22.50                           # board-x run of the bay
LEDGE_REACH = 1.45
LEDGE_BX0, LEDGE_BX1 = -0.40, 21.30
BLOCK_BX = (-3.61, -0.40)
BLOCK_BY = (-0.50, 1.90)
BLOCK_Z0 = 12.00
STOP_BX = (21.30, 22.50)
STOP_BY = (-0.50, 3.50)
STOP_Z0 = 13.73
HOOK_BX = (20.00, 22.50)
# DEVIATION: DESIGN.md gives HOOK y -0.50..2.00; mirrored that starts at
# board y 15.78 and clips the B2B connector (y to 15.34) by 0.06 at the
# board-y pocket extreme.  Pulled back to 1.60 -> 0.34 clear at the extreme.
HOOK_BY = (-0.50, 1.60)
HOOK_Z0, HOOK_Z1 = STOP_Z0, 15.91                         # 0.20 over the PCB top
POST_BX = (-0.10, 2.50)
# DEVIATION: DESIGN.md gives POST y -0.20..1.80; at the board-y pocket
# extreme that overlaps the RST/BOOT buttons (y 2.16 / 15.61) by 0.14.
# Pulled back to 1.36 -> 0.30 clear at the extreme (DESIGN's "buttons to the
# blocks/posts >= 0.3").  Landing area on the PCB stays well over 1 mm^2.
POST_BY = (-0.20, 1.36)
POST_Z1 = 16.01                                           # 0.10 over the PCB top

LENS_HOLE_D = 7.50
LENS_CHAMFER = 0.60

BOSS_D, BOSS_Z0, BOSS_BORE = 5.50, 15.86, 2.20
BOSS_INSET = 6.50
BOSS_XY = [(BOSS_INSET, BOSS_INSET), (OUT_W - BOSS_INSET, BOSS_INSET),
           (BOSS_INSET, OUT_H - BOSS_INSET), (OUT_W - BOSS_INSET, OUT_H - BOSS_INSET)]
PILOT_D, PILOT_DEPTH = 1.70, 3.40

CORD_SLOT_W, CORD_SLOT_H = 4.50, 3.00
CORD_SLOT_R = 1.499        # r1.5 stadium; 1.5 exactly is rejected by RectangleRounded
CORD_SLOT_XC = 13.00
CORD_SLOT_Z0, CORD_SLOT_Z1 = 16.86, 19.86
CORD_SLOT_ZC = (CORD_SLOT_Z0 + CORD_SLOT_Z1) / 2          # 18.36

# DEVIATION: DESIGN.md puts the tie post at (13.0, 9.0) — directly over the
# cord slot (X 10.75..15.25), which leaves no path for the lead to both wrap
# it and exit, and leaves the post as a second, unattached solid.  Moved
# +5.0 in X ("tie post beside it") and webbed to the bottom wall.
TIE_POST_D = 4.00
TIE_POST_XC, TIE_POST_YC = 18.00, 9.00
TIE_POST_Z0 = 14.36
TIE_WEB_W = 2.00

SCREW_D, SCREW_L = 2.00, 8.00
SCREW_HEAD_D, SCREW_HEAD_T = 4.00, 1.50

# lead + antenna envelopes (estimates, per DESIGN.md "Purchased parts")
LEAD_W, LEAD_T = 3.40, 1.70
ANT_L, ANT_W, ANT_T = 25.00, 12.00, 1.50

VENDOR_STEP = _REF / "xiao" / "amz-xiao-esp32s3-sense.step"


# ---------------------------------------------------------------------------
# printed parts
# ---------------------------------------------------------------------------
def _front_ribs(z0, height):
    """The puck's 6-rib layout (yc = CY +/- 15 on the +/-X faces, CX on the
    +/-Y faces), on the LIP rectangle."""
    rib = fits.edge_crush_rib(height, length=6.0, proud=LIP_RIB_PROUD)
    out = None
    for yc in (CY - 15.0, CY + 15.0):
        for x, rz in ((LIP_X0, 90), (LIP_X1, -90)):
            s = Pos(x, yc, z0) * Rot(0, 0, rz) * rib
            out = s if out is None else out + s
    out += Pos(CX, LIP_Y1, z0) * rib
    out += Pos(CX, LIP_Y0, z0) * Rot(0, 0, 180) * rib
    return out


def front_plate():
    """Weather face.  Prints outer-face down (Z = 0 on the bed), posts + lip up.

    Outline: the full OUT rounded rect for Y <= Y_SHOULDER; above that it is
    the LIP rect (IN inset by LIP_GAP) so the plate's top plugs in under the
    ring's eave.  The 6.0 lip merges with that top plug region.
    """
    keep = box_at(-5.0, -5.0, -5.0, OUT_W + 10.0, Y_SHOULDER + 5.0, 20.0)
    keep += prism(LIP_X0, LIP_Y0, LIP_X1, LIP_Y1, R_LIP, -5.0, FRONT_LIP_Z1 + 1.0)

    part = prism(OUT_X0, OUT_Y0, OUT_X1, OUT_Y1, R_OUT, 0.0, PLATE_T, cb=EFOOT)
    part = part & keep

    # lip into the ring's front mouth
    part += prism(LIP_X0, LIP_Y0, LIP_X1, LIP_Y1, R_LIP,
                  FRONT_LIP_Z0, FRONT_LIP_Z1, ct=LEADIN)
    part -= prism(BAY_X0, BAY_Y0, BAY_X1, BAY_Y1, R_BAY,
                  FRONT_LIP_Z0, FRONT_LIP_Z1 + 1.0)
    part += _front_ribs(FRONT_LIP_Z0, FRONT_RIB_H)

    # two posts onto the PCB's USB-end corners
    for by0, by1 in (POST_BY, bmirror(*POST_BY)):
        part += bbox_case(POST_BX[0], POST_BX[1], by0, by1,
                          Z_B0 - POST_Z1, Z_B0 - PLATE_T)

    # lens hole + outer-face chamfer
    part -= cyl_at(LENS_XC, LENS_YC, -1.0, LENS_HOLE_D, PLATE_T + 2.0)
    part -= Pos(LENS_XC, LENS_YC) * loft([
        Plane.XY.offset(0.0) * Circle(LENS_HOLE_D / 2 + LENS_CHAMFER),
        Plane.XY.offset(LENS_CHAMFER) * Circle(LENS_HOLE_D / 2),
    ])
    part.label = "front_plate"
    return part


def bay_box(bx0, bx1, by0, by1, cz0, cz1):
    """Board-x / board-y extents with an explicit case-Z range."""
    x0, y0, _, dx, dy, _ = bspan(bx0, bx1, by0, by1, 0, 0)
    return box_at(x0, y0, cz0, dx, dy, cz1 - cz0)


def ring():
    """Body + eave + board bay + screw bosses.  Prints standing on its back
    mouth (Z = Z_PLATE on the bed), eave up."""
    part = prism(OUT_X0, OUT_Y0, OUT_X1, OUT_Y1, R_OUT, PLATE_T, Z_PLATE, ct=EFOOT)
    part -= prism(IN_X0, IN_Y0, IN_X1, IN_Y1, R_IN, PLATE_T - 1.0, Z_PLATE + 1.0)
    part -= flare_down(IN_X0, IN_Y0, IN_X1, IN_Y1, R_IN, PLATE_T, LEADIN)
    part -= flare_up(IN_X0, IN_Y0, IN_X1, IN_Y1, R_IN, Z_PLATE, LEADIN)

    # --- eave: the top wall run 8.0 forward of the front mouth
    eave = prism(OUT_X0, OUT_Y0, OUT_X1, OUT_Y1, R_OUT, Z_EAVE, PLATE_T)
    eave &= box_at(-5.0, Y_SHOULDER, Z_EAVE - 1.0,
                   OUT_W + 10.0, OUT_H + 10.0, EAVE + PLATE_T + 2.0)
    eave -= prism(IN_X0, IN_Y0, IN_X1, IN_Y1, R_IN, Z_EAVE - 1.0, PLATE_T + 1.0)
    part += eave
    # drip groove along X on the eave's underside (the Y = IN_Y1 face)
    part -= box_at(IN_X0 + R_IN, IN_Y1, DRIP_Z0,
                   (IN_X1 - R_IN) - (IN_X0 + R_IN), DRIP_D, DRIP_W)

    # --- board bay, hanging from the top wall
    for face_y, inward in ((BAY_FACE_Y[0], -1), (BAY_FACE_Y[1], +1)):
        wy0, wy1 = sorted((face_y, face_y + inward * BAY_T))
        part += bay_box(BAY_BX0, BAY_BX1, wy0, wy1, BAY_Z0, Z_PLATE)
        ly0, ly1 = sorted((face_y, face_y - inward * LEDGE_REACH))
        part += bay_box(LEDGE_BX0, LEDGE_BX1, ly0, ly1, Z_B0, Z_PLATE)

    for by0, by1 in (BLOCK_BY, bmirror(*BLOCK_BY)):
        part += bay_box(BLOCK_BX[0], BLOCK_BX[1], by0, by1, BLOCK_Z0, Z_PLATE)
    for by0, by1 in (STOP_BY, bmirror(*STOP_BY)):
        part += bay_box(STOP_BX[0], STOP_BX[1], by0, by1, STOP_Z0, Z_PLATE)
    for by0, by1 in (HOOK_BY, bmirror(*HOOK_BY)):
        part += bay_box(HOOK_BX[0], HOOK_BX[1], by0, by1, HOOK_Z0, HOOK_Z1)

    # --- screw bosses, each fused to its corner by a square fill
    for bx, by in BOSS_XY:
        part += cyl_at(bx, by, BOSS_Z0, BOSS_D, Z_PLATE - BOSS_Z0)
        fx0, fx1 = sorted((bx, IN_X0 if bx < CX else IN_X1))
        fy0, fy1 = sorted((by, IN_Y0 if by < OUT_H / 2 else IN_Y1))
        part += box_at(fx0, fy0, BOSS_Z0, fx1 - fx0, fy1 - fy0, Z_PLATE - BOSS_Z0)

    # --- tie post (webbed to the bottom wall) beside the cord slot
    part += cyl_at(TIE_POST_XC, TIE_POST_YC, TIE_POST_Z0, TIE_POST_D,
                   Z_PLATE - TIE_POST_Z0)
    part += box_at(TIE_POST_XC - TIE_WEB_W / 2, IN_Y0, TIE_POST_Z0,
                   TIE_WEB_W, TIE_POST_YC - IN_Y0, Z_PLATE - TIE_POST_Z0)

    # --- cuts
    for bx, by in BOSS_XY:
        part -= cyl_at(bx, by, BOSS_Z0 - 1.0, BOSS_BORE, (Z_PLATE - BOSS_Z0) + 2.0)
    part -= slot_y(CORD_SLOT_XC, CORD_SLOT_ZC, CORD_SLOT_W, CORD_SLOT_H,
                   OUT_Y0 - 1.0, IN_Y0 + 1.0, r=CORD_SLOT_R)

    part.label = "ring"
    return part


def back_plate():
    """Coupling plate: 4.0 flat plate + the power puck's own front-plate lip
    on its back.  Prints front-face down (Z = Z_PLATE on the bed), lip up."""
    part = prism(OUT_X0, OUT_Y0, OUT_X1, OUT_Y1, R_OUT, Z_PLATE, Z_BACK, cb=EFOOT)
    part += prism(LIP_X0, LIP_Y0, LIP_X1, LIP_Y1, R_LIP,
                  PUCK_LIP_Z0, PUCK_LIP_Z1, ct=LEADIN)
    part -= prism(BAY_X0, BAY_Y0, BAY_X1, BAY_Y1, R_BAY,
                  PUCK_LIP_Z0, PUCK_LIP_Z1 + 1.0)
    part += _front_ribs(PUCK_LIP_Z0, LIP_RIB_H)

    for bx, by in BOSS_XY:                      # blind thread-forming pilots
        part -= cyl_at(bx, by, Z_PLATE - 1.0, PILOT_D, 1.0 + PILOT_DEPTH)

    part.label = "back_plate"
    return part


# ---------------------------------------------------------------------------
# reference occurrences (never printed)
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=None)
def _vendor_solids():
    return tuple(import_step(str(VENDOR_STEP)).solids())


def xiao_vendor(pre=None, post=None, label="xiao_vendor"):
    """The vendor XIAO STEP placed in the case frame.

    `pre` is an extra Location applied in the BOARD frame (tilt insertion),
    `post` one applied in the CASE frame (pocket-extreme shifts).  The full
    transform is baked into EVERY solid: a Location applied to a multi-solid
    Compound is silently ignored by Shape.intersect() in this build123d.
    """
    loc = BOARD_LOC if pre is None else BOARD_LOC * pre
    if post is not None:
        loc = post * loc
    part = Compound(children=[loc * s for s in _vendor_solids()])
    part.label = label
    return part


def xiao_envelope():
    """The measured feature boxes from ref/tripodcase/xiao_board_ref.py,
    placed in the case frame, one labelled solid per feature."""
    src = B.gen_step()
    out = []
    for child in src.children:
        for s in child.solids():
            p = BOARD_LOC * s
            p.label = f"env_{child.label}"
            p.color = getattr(child, "color", None)
            out.append(p)
    part = Compound(children=out)
    part.label = "xiao_envelope"
    return part


def puck_tube():
    """power_puck/caselib.tube(), shifted so its front mouth face (Z_TUBE0)
    lands on Z_BACK."""
    t = P.tube()
    part = Compound(children=[Pos(0, 0, Z_TUBE_SHIFT) * s for s in t.solids()])
    part.label = "puck_tube"
    return part


# --- LOAD lead route: BAT pads under the PCB -> down the plate face ->
#     beside the tie post -> out the cord slot.
LEAD_Z0 = 17.66
LEAD_RUN_XC = CX
LEAD_TURN_Y = 45.00
LEAD_EXIT_XC = CORD_SLOT_XC


def lead_mock():
    z, t, w = LEAD_Z0, LEAD_T, LEAD_W
    part = box_at(LEAD_RUN_XC - w / 2, LEAD_TURN_Y, z, w, PCB_Y1 - 0.79 - LEAD_TURN_Y, t)
    part += box_at(LEAD_EXIT_XC - w / 2, LEAD_TURN_Y, z,
                   (LEAD_RUN_XC + w / 2) - (LEAD_EXIT_XC - w / 2), w, t)
    part += box_at(LEAD_EXIT_XC - w / 2, -5.0, z, w, LEAD_TURN_Y + w + 5.0, t)
    part.label = "load_lead_mock"
    return part


def antenna_mock():
    """25 x 12 x 1.5 flex flag, stuck to the back plate's front face below
    the bay."""
    part = box_at(16.0, 20.0, Z_PLATE - 0.06 - ANT_T, ANT_L, ANT_W, ANT_T)
    part.label = "antenna_mock"
    return part


def screw_mocks():
    """4 x M2 x 8 pan head, driven from the boss tops into the back plate."""
    out = []
    for i, (bx, by) in enumerate(BOSS_XY):
        s = cyl_at(bx, by, BOSS_Z0, SCREW_D, SCREW_L)
        s += cyl_at(bx, by, BOSS_Z0 - SCREW_HEAD_T, SCREW_HEAD_D, SCREW_HEAD_T)
        s.label = f"screw_m2x8_{i + 1}"
        out.append(s)
    return out


def tilt_loc(deg):
    """Insertion tilt: rotate the board about the line through its far-edge
    PCB-top corners (board x = PCB_L, z = PCB_T, along board y), raising the
    USB end out of the bay while the far edge stays under the hooks."""
    return Pos(PCB_L, 0, PCB_T) * Rot(0, deg, 0) * Pos(-PCB_L, 0, -PCB_T)
