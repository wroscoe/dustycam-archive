"""puckcase v2 — XIAO ESP32S3 Sense camera case that plugs into the power puck.

Geometry library for the three printed parts (front_plate, ring, back_plate)
plus the reference occurrences used by check.py / fitcheck.step.py.

v2 (DESIGN_v2.md) redesigns the board bay after the v1 coupon print:
  * the base PCB carries pin HEADERS (body on the back, pins ~6 proud), so
    nothing may bear on the back face along the long edges and nothing may sit
    within 1.0 outside them -> v1's LEDGE / BLOCK / POST features are gone and
    BACK_GAP grows from 3.0 to 9.0.
  * the board is held by its two header-free ends (hooks + centre ledge at the
    far end, bridge + snap tongue at the USB end), by the expansion PCB's long
    edges (side rails with crush ribs) and by the camera head (collar).
  * the board drops 3.5 (BOARD_DROP) so the SD card gets a 4.0 roof.

Frame (case-local, per DESIGN.md):
  X  0 at the -X outer face .. 47.21
  Y  0 at the bottom outer face .. 80.80 (up)
  Z  0 at the outer FRONT face, +Z toward the puck.

Print orientation matters for every bay feature: the ring stands on its BACK
MOUTH (Z_PLATE on the bed), so increasing case Z is DOWN and any face whose
normal points +Z is an overhang.

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
    Align, Box, Circle, Compound, Cylinder, Location, Plane, Pos, Rectangle,
    Rot, RectangleRounded, Vector, Wire, extrude, import_step, loft, make_face,
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
# Z stack  (DESIGN_v2 §3 "Placement and depth")
# ---------------------------------------------------------------------------
PLATE_T = 2.40                             # front plate, Z 0..2.40
LENS_GAP = 1.00
Z_B0 = PLATE_T + LENS_GAP + B.STACK_TOP    # 17.36  PCB bottom (board z = 0)
BACK_GAP = 9.00                            # was WIRE_GAP 3.00; header body 2.5
#                                            + 6.0 pin tails + 0.5 to the plate
Z_PLATE = Z_B0 + BACK_GAP                  # 26.36  ring back mouth / plate front
BACK_T = 4.00
Z_BACK = Z_PLATE + BACK_T                  # 30.36  puck tube front mouth face
PUCK_LIP_Z0, PUCK_LIP_Z1 = Z_BACK, Z_BACK + LIP_ENG          # 30.36 .. 37.86

EAVE = 8.00
Z_EAVE = -EAVE                             # -8.00  eave front edge
DRIP_W, DRIP_D, DRIP_BACK = 1.00, 0.80, 1.50
DRIP_Z0 = Z_EAVE + DRIP_BACK               # -6.50
DRIP_Z1 = DRIP_Z0 + DRIP_W                 # -5.50

FRONT_LIP = 6.00
FRONT_LIP_Z0, FRONT_LIP_Z1 = PLATE_T, PLATE_T + FRONT_LIP    # 2.40 .. 8.40
FRONT_RIB_H = 4.90

Z_TUBE_SHIFT = Z_BACK - P.Z_TUBE0          # 27.96  puck frame -> case frame

# ---------------------------------------------------------------------------
# Board placement (board -> case)
# ---------------------------------------------------------------------------
# DESIGN.md writes the mapping as  board x -> case -Y, board y -> case +X,
# board z -> case -Z.  That triple is IMPROPER (determinant -1): it is a
# mirror, not a rigid placement, so it cannot be built.  With "USB end up"
# (x -> -Y) and "lens forward" (z -> -Z) fixed, handedness forces
# board y -> case -X.  The lens axis is kept on CX; the consequence is that
# the board bay is mirrored about CX relative to the literal DESIGN numbers.
# The bay itself is symmetric about board y = 8.89 (every bay feature is
# given "(mirror 17.78)"), so only its case-X position changes.
X_B0 = CX + B.CAM_C[1]                     # 31.855  case X of board y = 0
BOARD_DROP = 3.50                          # v2: card roof 0.5 -> 4.0
Y_B0 = OUT_H - WALL - 3.61 - BOARD_DROP    # 71.29   case Y of board x = 0

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


def bX(by):
    """board y -> case X."""
    return X_B0 - by


def bY(bx):
    """board x -> case Y."""
    return Y_B0 - bx


def bZ(bz):
    """board z -> case Z."""
    return Z_B0 - bz


# derived board landmarks, in the case frame
PCB_X0, PCB_X1 = X_B0 - PCB_W, X_B0                       # 14.075 .. 31.855
PCB_Y0, PCB_Y1 = Y_B0 - PCB_L, Y_B0                       # 50.34 .. 71.29
PCB_Z_TOP = Z_B0 - PCB_T                                  # 16.11 (toward front)
LENS_XC, LENS_YC = board_to_case(B.CAM_C[0], B.CAM_C[1])[:2]   # 23.605, 67.76
LENS_TIP_Z = Z_B0 - B.STACK_TOP                           # 3.40
CARD_TIP_Y = bY(B.SD_CARD[0])                             # 74.40
CARD_ROOF = IN_Y1 - CARD_TIP_Y                            # 4.00

# ---------------------------------------------------------------------------
# Bay geometry — DESIGN_v2 §3.  Board coordinates unless the name says case.
# ---------------------------------------------------------------------------
SIDE_CLR = 1.50            # wall inner face from the PCB long edge
BAY_T = 1.60               # bay wall thickness
BAY_BX0, BAY_BX1 = -7.11, 23.20         # board-x run of the side walls
SIDE_BY = (-SIDE_CLR - BAY_T, -SIDE_CLR)               # -3.10 .. -1.50
SIDE_BZ = (-9.00, 11.80)                # to the collar's front face
BAY_IN_X = (X_B0 - (BOARD_MIRROR_Y - SIDE_BY[0]), X_B0 - SIDE_BY[1])   # 12.575, 33.355

# the front plate's top lip band (case Y LIP_Y1-LIP_WALL .. LIP_Y1, Z .. 8.40)
# runs right through the side walls' forward extension -> clip it.
# DEVIATION (v2): DESIGN_v2 gives the side walls one Z range (5.56..26.36) over
# the whole run Y 48.09..78.40.  At Y > 76.65 that is inside the front plate's
# lip band (Z 2.40..8.40), a hard interference DESIGN_v2 does not mention.  The
# walls keep the full forward reach only where the collar needs it (Y <= 76.35,
# 0.30 clear of the lip band) and start at Z 8.70 (0.30 clear of the lip nose)
# for the last 2.05 up to the top wall.
SIDE_LIP_CLR = 0.30
SIDE_FWD_Y1 = (LIP_Y1 - LIP_WALL) - SIDE_LIP_CLR       # 76.35
SIDE_BACK_Z0 = FRONT_LIP_Z1 + SIDE_LIP_CLR             # 8.70

# DEVIATION (v2): DESIGN_v2 §3 calls the far-end wall "low ... so the antenna
# cable can cross it", but low in BOARD z means case Z 11.36..26.36 — a full
# barrier from the board's front face to the back mouth.  With side walls, a
# far-end wall and a USB-end wall the bay is a closed box: neither the LOAD
# lead (off the header pins) nor the U.FL coax can reach the cavity below.
# A 4.5 x 4.5 wire notch is cut through the +X side wall behind the rails,
# opening onto the back mouth so it prints as a bridged slot.
WIRE_NOTCH_Y = (52.30, 56.80)
WIRE_NOTCH_Z0 = 21.86

FAR_BX = (21.60, 23.20)                 # far-end wall
FAR_BZ = (-9.00, 6.00)                  # low: nothing in front of z 6

STOP_BX = (21.15, 21.60)                # far-end stop ribs
STOP_BY = (-0.50, 3.50)
STOP_BZ = (-9.00, 3.60)

HOOK_BX = (20.00, 21.60)
HOOK_BY = (-0.50, 1.60)
HOOK_BZ = (1.40, 3.60)                  # underside 0.15 over the PCB top
HOOK_CHAMFER = 0.50                     # entry chamfer, back-inner edge

LEDGE_BX = (19.70, 21.60)               # centre ledge, behind the PCB
LEDGE_BY = (5.00, 13.00)                # between the header rows
LEDGE_BZ = (-9.00, -0.10)               # 0.10 under the PCB back face
# DEVIATION (v2): DESIGN_v2 gives the ledge a flat face 0.10 behind the PCB
# over its whole 1.25 reach plus a 0.50 entry chamfer.  Rotating the board to
# the 13 deg insertion tilt lifts its back face by reach*sin13 -> a flat face
# may only reach 0.10/sin13 = 0.444 before the tilted PCB bites it (measured:
# 0.25 mm^3 at 1.25 reach).  The flat bearing keeps the contract's 0.10 gap
# over LEDGE_FLAT (0.30 under the PCB, 2.4 mm^2 of bearing) and the rest of
# the reach becomes a 45 deg entry ramp — a bigger version of the 0.5 entry
# chamfer the contract asks for, in the same place.
LEDGE_FLAT = 0.30                       # flat bearing reach under the PCB
LEDGE_RAMP_DEG = 45.0

# v2.2 amendment: the USB-end wall is gone entirely above the lip.  What is
# left is the root strip at board z -9.0..-8.8 (it runs wall to wall and ties
# the side walls together at the bed) and TWO snap tongues grown from it, one
# at each end of the PCB's end edge.  A single central tongue could not
# survive insertion: the USB-C shell stands 1.53 proud of the PCB's end edge
# and 4.2 tall, so once the USB end is lifted ~2 mm its rear corner sweeps
# through anything behind the PCB plane inside board y 4.41..13.35.  The two
# tongues sit outside that span (>= 0.5 clear) and reach 1.7 into the opening
# so their lips land on the STRAIGHT part of the PCB's end edge — the R1.906
# corners leave straight edge only for board y 1.906..15.874.
# Consequence: there is no rigid +Y stop any more.  The tongues' faces at
# board x -0.2 are a soft stop, so the board's Y play is 0.20 to the far-end
# stop ribs and 0.20 to the tongue faces.
USB_STRIP_BX = (-1.60, -0.20)           # root strip, board x
USB_STRIP_BZ = (-9.00, -8.80)
USB_OPEN_BZ = (-0.10, 9.00)             # fully open from the lip to the collar

TONGUE_BYS = ((-0.50, 3.90), (13.88, 18.28))   # the two tongues, board y
TONGUE_BX = (-1.10, -0.20)              # 0.9 thick
TONGUE_BZ = (-8.80, -0.10)              # root at the strip, free end at the PCB
LIP_BX = (-0.20, 0.40)                  # lip: 0.40 over the PCB back edge
LIP_BZ = (-0.60, -0.10)
LIP_RAMP = 0.60                         # 45 deg ramp on the lip's back side
TONGUE_T = TONGUE_BX[1] - TONGUE_BX[0]                 # 0.90
TONGUE_L = TONGUE_BZ[1] - TONGUE_BZ[0]                 # 8.70
TONGUE_DEFL = 0.60                      # deflection at the lip on insertion
E_PETG = 2000.0                         # MPa, for the snap force estimate
PCB_STRAIGHT_BY = (PCB_R, PCB_W - PCB_R)               # 1.906 .. 15.874

RAIL_BX = (8.00, 17.00)                 # side rails on the expansion edges
RAIL_BY = 0.35                          # rail face (mirror 17.43)
RAIL_BZ = (4.20, 5.60)
RAIL_UNDER_BZ = 2.35                    # 45 deg underside back to the wall
RIB_PROUD = 0.25                        # -> 0.10 nominal crush per side
RIB_H = 1.40
RIB_BX = ((8.50, 12.50), (13.00, 17.00))

COLLAR_BX = (-1.60, 9.80)               # collar plate
COLLAR_FRONT_BX1 = -2.30                # front part reaches further
COLLAR_BZ = (9.00, 11.80)
COLLAR_STEP_BZ = 10.50                  # window/bore step = head top + 0.2
COLLAR_WIN = 8.60                       # square window around the head
COLLAR_WIN_CHAMFER = 0.60
COLLAR_BORE_D = 8.25                    # barrel 7.84 + 0.4
FPC_RELIEF_BX = (7.83, 9.80)
FPC_RELIEF_BZ = 9.50

LENS_HOLE_D = 7.50
LENS_CHAMFER = 0.60

# v2.1 amendment 2: the bosses shorten so an M2 x 12 actually holds.  With a
# 10.5 boss it engaged the back plate by only 1.5.  DEVIATION: the amendment
# asks for 8.3 (engagement 3.7), but the pilot is 3.4 deep, so a 3.7 engagement
# bottoms the screw out 0.30 PAST the pilot.  Boss length must satisfy both
# "engagement >= 3.0" (L <= 9.0) and "tip >= 0.3 short of the 3.4 pilot"
# (L >= 8.9); 9.0 is the value that meets both with the most engagement.
BOSS_LEN = 9.00
BOSS_D, BOSS_Z0, BOSS_BORE = 5.50, Z_PLATE - BOSS_LEN, 2.20    # 17.36
BOSS_INSET = 6.50
BOSS_XY = [(BOSS_INSET, BOSS_INSET), (OUT_W - BOSS_INSET, BOSS_INSET),
           (BOSS_INSET, OUT_H - BOSS_INSET), (OUT_W - BOSS_INSET, OUT_H - BOSS_INSET)]
PILOT_D, PILOT_DEPTH = 1.70, 3.40

CORD_SLOT_W, CORD_SLOT_H = 4.50, 3.00
CORD_SLOT_R = 1.499        # r1.5 stadium; 1.5 exactly is rejected by RectangleRounded
CORD_SLOT_XC = 13.00
CORD_SLOT_Z0, CORD_SLOT_Z1 = Z_PLATE - 3.50, Z_PLATE - 0.50    # 22.86 .. 25.86
CORD_SLOT_ZC = (CORD_SLOT_Z0 + CORD_SLOT_Z1) / 2               # 24.36

# DEVIATION (v1, kept): DESIGN.md puts the tie post at (13.0, 9.0) — directly
# over the cord slot (X 10.75..15.25), which leaves no path for the lead to
# both wrap it and exit, and leaves the post as a second, unattached solid.
# Moved +5.0 in X ("tie post beside it") and webbed to the bottom wall.
TIE_POST_D = 4.00
TIE_POST_XC, TIE_POST_YC = 18.00, 9.00
TIE_POST_Z0 = Z_PLATE - 6.00                                   # 20.36
TIE_WEB_W = 2.00

SCREW_D, SCREW_L = 2.00, 12.00          # v2: M2 x 12 (bosses are 10.5 long)
SCREW_HEAD_D, SCREW_HEAD_T = 4.00, 1.50

# lead + antenna envelopes (estimates, per DESIGN.md "Purchased parts")
LEAD_W, LEAD_T = 3.40, 1.70
ANT_L, ANT_W, ANT_T = 25.00, 12.00, 1.50

# header mock (DESIGN_v2 §1; not in the vendor STEP)
HDR_BODY_W = 2.54                       # across the pin row
HDR_BODY_L = 17.78                      # along the row
HDR_BODY_H = 2.50                       # on the PCB back, board z -2.5..0
HDR_BY = (-1.00, 1.54)                  # body span, mirror 16.24..18.78
HDR_BX = (1.585, 19.365)
HDR_PIN = 0.64
HDR_PIN_Z = -8.50                       # pin tails, board z 0 .. -8.5
HDR_PIN_BY = 0.27                       # pin row centre (mirror 17.51)
HDR_PIN_BX = B.CASTELL_X                # 2.855 + 2.54 i, i = 0..6

VENDOR_STEP = _REF / "xiao" / "amz-xiao-esp32s3-sense.step"


# ---------------------------------------------------------------------------
# small geometry helpers
# ---------------------------------------------------------------------------
def prism_x(pts_yz, x0, x1):
    """A polygon given as case (Y, Z) points, swept from case X x0 to x1."""
    faces = [make_face(Wire.make_polygon([Vector(x, y, z) for y, z in pts_yz],
                                         close=True)) for x in (x0, x1)]
    return loft(faces)


def prism_y(pts_xz, y0, y1):
    """A polygon given as case (X, Z) points, swept from case Y y0 to y1."""
    faces = [make_face(Wire.make_polygon([Vector(x, y, z) for x, z in pts_xz],
                                         close=True)) for y in (y0, y1)]
    return loft(faces)


def bay_box(bx0, bx1, by0, by1, cz0, cz1):
    """Board-x / board-y extents with an explicit case-Z range."""
    x0, y0, _, dx, dy, _ = bspan(bx0, bx1, by0, by1, 0, 0)
    return box_at(x0, y0, cz0, dx, dy, cz1 - cz0)


def _sq_at(cx, cy, side, z):
    return Plane.XY.offset(z) * Pos(cx, cy) * Rectangle(side, side)


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
    """Weather face.  Prints outer-face down (Z = 0 on the bed), lip up.

    v2: the posts are gone (the bay holds the board), so the plate is outline
    + lip + ribs + the chamfered lens hole at the new LENS_YC.
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

    # lens hole + outer-face chamfer
    part -= cyl_at(LENS_XC, LENS_YC, -1.0, LENS_HOLE_D, PLATE_T + 2.0)
    part -= Pos(LENS_XC, LENS_YC) * loft([
        Plane.XY.offset(0.0) * Circle(LENS_HOLE_D / 2 + LENS_CHAMFER),
        Plane.XY.offset(LENS_CHAMFER) * Circle(LENS_HOLE_D / 2),
    ])
    part.label = "front_plate"
    return part


# --- ring sub-assemblies ---------------------------------------------------
def _side_walls():
    """The two long walls, SIDE_CLR clear of the PCB's long edges, hanging
    from the ring's top wall.  Two Z bands so the forward reach clears the
    front plate's lip band (see SIDE_FWD_Y1)."""
    out = None
    for by0, by1 in (SIDE_BY, bmirror(*SIDE_BY)):
        x0, _, _, dx, _, _ = bspan(0, 0, by0, by1, 0, 0)
        back = box_at(x0, bY(BAY_BX1), SIDE_BACK_Z0, dx,
                      IN_Y1 - bY(BAY_BX1), Z_PLATE - SIDE_BACK_Z0)
        fwd = box_at(x0, bY(BAY_BX1), bZ(SIDE_BZ[1]), dx,
                     SIDE_FWD_Y1 - bY(BAY_BX1), SIDE_BACK_Z0 - bZ(SIDE_BZ[1]))
        s = back + fwd
        out = s if out is None else out + s
    return out


def _far_end():
    """Far-end wall + stop ribs + hooks + centre ledge, with the two 0.5
    entry chamfers that guide the tilted board's far edge into the groove."""
    part = bay_box(FAR_BX[0], FAR_BX[1], SIDE_BY[1], bmirror(*SIDE_BY)[0],
                   bZ(FAR_BZ[1]), bZ(FAR_BZ[0]))

    for by0, by1 in (STOP_BY, bmirror(*STOP_BY)):
        part += bay_box(STOP_BX[0], STOP_BX[1], by0, by1,
                        bZ(STOP_BZ[1]), bZ(STOP_BZ[0]))

    for by0, by1 in (HOOK_BY, bmirror(*HOOK_BY)):
        hook = bay_box(HOOK_BX[0], HOOK_BX[1], by0, by1,
                       bZ(HOOK_BZ[1]), bZ(HOOK_BZ[0]))
        # entry chamfer on the hook's back-inner edge (case +Y / +Z corner)
        ye, ze = bY(HOOK_BX[0]), bZ(HOOK_BZ[0])
        c = HOOK_CHAMFER
        x0, _, _, dx, _, _ = bspan(0, 0, by0, by1, 0, 0)
        hook -= prism_x([(ye, ze), (ye - c, ze), (ye, ze - c)],
                        x0 - 0.5, x0 + dx + 0.5)
        part += hook

    # centre ledge: flat bearing at the PCB's far edge, 45 deg entry ramp
    y_out, y_in = bY(LEDGE_BX[1]), bY(LEDGE_BX[0])          # 49.69 .. 51.59
    y_flat = bY(PCB_L - LEDGE_FLAT)                          # 50.64
    z_face, z_back = bZ(LEDGE_BZ[1]), bZ(LEDGE_BZ[0])        # 17.46 .. 26.36
    z_ramp = z_face + (y_in - y_flat)                        # 45 deg
    lx0, _, _, ldx, _, _ = bspan(0, 0, LEDGE_BY[0], LEDGE_BY[1], 0, 0)
    part += prism_x([(y_out, z_face), (y_flat, z_face), (y_in, z_ramp),
                     (y_in, z_back), (y_out, z_back)], lx0, lx0 + ldx)
    return part


def _rails(ribs=True):
    """Side rails bearing on the expansion PCB's long edges, with a 45 deg
    printable underside and two crush ribs each."""
    out = None
    for sign, rail_by in ((+1, RAIL_BY), (-1, bmirror(RAIL_BY, RAIL_BY)[0])):
        face_x = bX(rail_by)                       # 31.505 / 14.425
        wall_x = bX(SIDE_BY[1]) if sign > 0 else bX(bmirror(*SIDE_BY)[0])
        z_tip0, z_tip1 = bZ(RAIL_BZ[1]), bZ(RAIL_BZ[0])      # 11.76 .. 13.16
        z_root = bZ(RAIL_UNDER_BZ)                            # 15.01
        pts = [(face_x, z_tip0), (wall_x, z_tip0), (wall_x, z_root),
               (face_x, z_tip1)]
        rail = prism_y(pts, bY(RAIL_BX[1]), bY(RAIL_BX[0]))
        for rbx0, rbx1 in (RIB_BX if ribs else ()):
            ribl = rbx1 - rbx0
            rib = fits.edge_crush_rib(RIB_H, length=ribl, proud=RIB_PROUD)
            # canonical rib: base on y = 0, protrudes +Y, runs z 0..height,
            # centred on x = 0.  Put its base on the rail face, protruding
            # toward the board (case -X for the +y rail), running along case Y.
            yc = (bY(rbx0) + bY(rbx1)) / 2
            rz = 90 if sign > 0 else -90
            rail += Pos(face_x, yc, z_tip0) * Rot(0, 0, rz) * rib
        out = rail if out is None else out + rail
    return out


def _collar():
    """Lens collar: the sheet that captures the camera head (8.6 window +
    0.6 back chamfer), steps at the head top and bores Ø8.25 for the barrel."""
    x0, x1 = BAY_IN_X                                       # 12.575 .. 33.355
    y0, y1 = bY(COLLAR_BX[1]), bY(COLLAR_BX[0])             # 61.49 .. 72.89
    z0, z1 = bZ(COLLAR_BZ[1]), bZ(COLLAR_BZ[0])             # 5.56 .. 8.36
    z_step = bZ(COLLAR_STEP_BZ)                             # 6.86
    part = box_at(x0, y0, z0, x1 - x0, y1 - y0, z1 - z0)
    part += box_at(x0, y1, z0, x1 - x0, bY(COLLAR_FRONT_BX1) - y1, z_step - z0)

    # FPC roll relief: back face raised to board z 9.5 over board x 7.83..9.8
    ry0, ry1 = bY(FPC_RELIEF_BX[1]), bY(FPC_RELIEF_BX[0])   # 61.49 .. 63.46
    part -= box_at(LENS_XC - COLLAR_WIN / 2, ry0, bZ(FPC_RELIEF_BZ),
                   COLLAR_WIN, ry1 - ry0, z1 - bZ(FPC_RELIEF_BZ) + 0.01)

    # square window around the head, with the 45 deg entry chamfer at the back
    w, c = COLLAR_WIN, COLLAR_WIN_CHAMFER
    part -= box_at(LENS_XC - w / 2, LENS_YC - w / 2, z_step, w, w, z1 - z_step)
    part -= loft([_sq_at(LENS_XC, LENS_YC, w, z1 - c),
                  _sq_at(LENS_XC, LENS_YC, w + 2 * c, z1)])

    # barrel bore through the front part
    part -= cyl_at(LENS_XC, LENS_YC, z0 - 1.0, COLLAR_BORE_D,
                   (z_step - z0) + 1.0)
    return part


def _usb_end_wall():
    """v2.2: the USB end is open from the lip level (board z -0.1) up to the
    collar's back face.  All that is left is the root strip at the bed and the
    two snap tongues grown from it.  Returns (strip, tongues)."""
    x0, x1 = BAY_IN_X
    sy0, sy1 = bY(USB_STRIP_BX[1]), bY(USB_STRIP_BX[0])     # 71.49 .. 72.89
    strip = box_at(x0, sy0, bZ(USB_STRIP_BZ[1]), x1 - x0, sy1 - sy0,
                   bZ(USB_STRIP_BZ[0]) - bZ(USB_STRIP_BZ[1]))

    ty0, ty1 = bY(TONGUE_BX[1]), bY(TONGUE_BX[0])           # 71.49 .. 72.39
    ly0, ly1 = bY(LIP_BX[1]), bY(LIP_BX[0])                 # 70.89 .. 71.49
    lz0, lz1 = bZ(LIP_BZ[1]), bZ(LIP_BZ[0])                 # 17.46 .. 17.96
    tongues = None
    for by0, by1 in TONGUE_BYS:
        tx0, tdx = bX(by1), by1 - by0
        t = box_at(tx0, ty0, bZ(TONGUE_BZ[1]), tdx, ty1 - ty0,
                   Z_PLATE - bZ(TONGUE_BZ[1]))
        t += prism_x([(ly1, lz0), (ly0, lz0), (ly0, lz1),
                      (ly1, lz1 + LIP_RAMP)], tx0, tx0 + tdx)
        tongues = t if tongues is None else tongues + t
    return strip, tongues


def ring(ribs=True, tongue=True):
    """Body + eave + board bay + screw bosses.  Prints standing on its back
    mouth (Z = Z_PLATE on the bed), eave up.

    `ribs=False` / `tongue=False` build the RIGID ring only — the rail crush
    ribs and the snap tongue are the only features designed to interfere with
    the board, so check.py measures them separately against a rigid ring.
    """
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

    # --- board bay
    part += _side_walls()
    part += _far_end()
    strip, tongue_solid = _usb_end_wall()
    part += strip
    part += _collar()
    part += _rails(ribs=ribs)

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
    part -= box_at(BAY_IN_X[1] - 0.5, WIRE_NOTCH_Y[0], WIRE_NOTCH_Z0,
                   (BAY_IN_X[1] + BAY_T + 0.5) - (BAY_IN_X[1] - 0.5),
                   WIRE_NOTCH_Y[1] - WIRE_NOTCH_Y[0],
                   (Z_PLATE + 0.5) - WIRE_NOTCH_Z0)
    for bx, by in BOSS_XY:
        part -= cyl_at(bx, by, BOSS_Z0 - 1.0, BOSS_BORE, (Z_PLATE - BOSS_Z0) + 2.0)
    part -= slot_y(CORD_SLOT_XC, CORD_SLOT_ZC, CORD_SLOT_W, CORD_SLOT_H,
                   OUT_Y0 - 1.0, IN_Y0 + 1.0, r=CORD_SLOT_R)

    if tongue:
        part += tongue_solid

    part.label = "ring"
    return part


def rail_ribs():
    """The four rail crush ribs alone (the designed 0.10/side interference)."""
    part = _rails(ribs=True) - _rails(ribs=False)
    part.label = "rail_crush_ribs"
    return part


def tongue_only():
    """The two snap tongues alone (the compliant retention features)."""
    _, tongues = _usb_end_wall()
    tongues.label = "snap_tongues"
    return tongues


def tongue_cam_zone():
    """The volume a tongue's lip + 45 deg ramp occupies — the region the board
    is DESIGNED to cam through on insertion.  Everything outside it must be
    clear of the swept board."""
    ly0 = bY(LIP_BX[1]) - 0.05
    ly1 = bY(TONGUE_BX[1]) + 0.05
    lz0 = bZ(LIP_BZ[1]) - 0.05
    lz1 = bZ(LIP_BZ[0]) + LIP_RAMP + 0.05
    out = None
    for by0, by1 in TONGUE_BYS:
        z = box_at(bX(by1) - 0.05, ly0, lz0, (by1 - by0) + 0.10,
                   ly1 - ly0, lz1 - lz0)
        out = z if out is None else out + z
    return out


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


def _is_head(solid):
    """The flex-mounted OV3660 head + lens: the only vendor solids that reach
    above board z 9.0.  DESIGN_v2 §1: the head is held ONLY by its flex, so it
    travels with the collar, not with the PCB."""
    return solid.bounding_box().max.Z > 9.0


def _is_card(solid):
    """True for a vendor solid that lies (in board coords) inside the inserted
    microSD card's box — used to model 'card not fitted'."""
    b = solid.bounding_box()
    x0, y0, z0 = B.SD_CARD[0], B.SD_CARD[1], B.SD_CARD[4]
    x1, y1, z1 = B.SD_CARD[2], B.SD_CARD[3], B.SD_CARD[5]
    return (b.min.X >= x0 - 0.3 and b.max.X <= x1 + 0.3 and
            b.min.Y >= y0 - 0.3 and b.max.Y <= y1 + 0.3 and
            b.min.Z >= z0 - 0.3 and b.max.Z <= z1 + 0.3)


VENDOR_PARTS = ("all", "board", "pcb", "head", "card")


def xiao_vendor(pre=None, post=None, label="xiao_vendor", parts="all"):
    """The vendor XIAO STEP placed in the case frame.

    `pre` is an extra Location applied in the BOARD frame (tilt insertion),
    `post` one applied in the CASE frame (pocket-extreme shifts).  The full
    transform is baked into EVERY solid: a Location applied to a multi-solid
    Compound is silently ignored by Shape.intersect() in this build123d.

    `parts` selects which vendor solids to place:
      all    everything (the board as delivered, card inserted)
      board  everything except the flex-mounted head and the microSD card
      pcb    everything except the head (card fitted)
      head   the flex-mounted camera head + lens only
      card   the inserted microSD card only
    """
    if parts not in VENDOR_PARTS:
        raise ValueError(f"parts={parts!r} not in {VENDOR_PARTS}")
    loc = BOARD_LOC if pre is None else BOARD_LOC * pre
    if post is not None:
        loc = post * loc
    sel = {
        "all": lambda s: True,
        "board": lambda s: not _is_head(s) and not _is_card(s),
        "pcb": lambda s: not _is_head(s),
        "head": _is_head,
        "card": _is_card,
    }[parts]
    solids = [s for s in _vendor_solids() if sel(s)]
    if not solids:
        raise ValueError(f"no vendor solids selected for parts={parts!r}")
    part = Compound(children=[loc * s for s in solids])
    part.label = label
    return part


def xiao_envelope(pre=None, post=None, skip=(), label="xiao_envelope"):
    """The measured feature boxes from ref/tripodcase/xiao_board_ref.py,
    placed in the case frame, one labelled solid per feature.  Far lighter
    than the 103-solid vendor STEP, so review models use it.

    `pre` / `post` as in xiao_vendor(); `skip` drops features by label
    substring (e.g. ("camera_head", "lens", "microsd_card_inserted"))."""
    loc = BOARD_LOC if pre is None else BOARD_LOC * pre
    if post is not None:
        loc = post * loc
    src = B.gen_step()
    out = []
    for child in src.children:
        if any(k in child.label for k in skip):
            continue
        for s in child.solids():
            p = loc * s
            p.label = f"env_{child.label}"
            p.color = getattr(child, "color", None)
            out.append(p)
    part = Compound(children=out)
    part.label = label
    return part


def header_mock(inflate=0.0, label="header_mock"):
    """The pin headers DESIGN_v2 §1 assumes: two 2.54 x 17.78 x 2.5 bodies on
    the PCB back (board z -2.5..0) plus 2 x 7 pins 0.64 square down to
    z -8.5.  Every solid is baked (see xiao_vendor)."""
    g = inflate
    out = []
    for by0, by1 in (HDR_BY, bmirror(*HDR_BY)):
        s = bbox_case(HDR_BX[0] - g, HDR_BX[1] + g, by0 - g, by1 + g,
                      -HDR_BODY_H - g, 0.0 + g)
        s.label = "hdr_body"
        out.append(s)
    for pin_y in (HDR_PIN_BY, BOARD_MIRROR_Y - HDR_PIN_BY):
        for i, px in enumerate(HDR_PIN_BX):
            s = bbox_case(px - HDR_PIN / 2 - g, px + HDR_PIN / 2 + g,
                          pin_y - HDR_PIN / 2 - g, pin_y + HDR_PIN / 2 + g,
                          HDR_PIN_Z - g, 0.0 + g)
            s.label = f"hdr_pin_{i}"
            out.append(s)
    part = Compound(children=out)
    part.label = label
    return part


def puck_tube():
    """power_puck/caselib.tube(), shifted so its front mouth face (Z_TUBE0)
    lands on Z_BACK."""
    t = P.tube()
    part = Compound(children=[Pos(0, 0, Z_TUBE_SHIFT) * s for s in t.solids()])
    part.label = "puck_tube"
    return part


# --- LOAD lead route: soldered to 5V/GND at the far end of the -y header
#     row -> out through the side-wall wire notch -> down the +X corridor ->
#     across below the tie post -> out the cord slot.
LEAD_PINS = (6, 7)                  # 1-based in the row: 5V / GND, far end
LEAD_ZC = CORD_SLOT_ZC              # centred on the cord slot
LEAD_Z0 = LEAD_ZC - LEAD_T / 2      # 23.51
LEAD_CORRIDOR_X = 35.30             # outside the bay's +X side wall (34.955)
LEAD_TURN_Y = 11.40                 # clear of the tie post (Y 7..11)
LEAD_EXIT_XC = CORD_SLOT_XC
LEAD_NOTCH_YC = sum(WIRE_NOTCH_Y) / 2


def lead_mock():
    """LOAD lead: soldered to the last two pins of the -y header row, out
    through the side-wall wire notch, down the +X corridor, across below the
    tie post and out the cord slot."""
    z, t, w = LEAD_Z0, LEAD_T, LEAD_W
    x_pad = bX(HDR_PIN_BY)
    y_pins = sorted(bY(HDR_PIN_BX[i - 1]) for i in LEAD_PINS)
    x_far = LEAD_CORRIDOR_X + w
    part = box_at(x_pad - w / 2, y_pins[0] - HDR_PIN, z, w,
                  (y_pins[1] + HDR_PIN) - (y_pins[0] - HDR_PIN), t)
    part += box_at(x_pad - w / 2, LEAD_NOTCH_YC - w / 2, z,
                   x_far - (x_pad - w / 2), w, t)
    part += box_at(LEAD_CORRIDOR_X, LEAD_TURN_Y, z, w,
                   (LEAD_NOTCH_YC + w / 2) - LEAD_TURN_Y, t)
    part += box_at(LEAD_EXIT_XC - w / 2, LEAD_TURN_Y, z,
                   x_far - (LEAD_EXIT_XC - w / 2), w, t)
    part += box_at(LEAD_EXIT_XC - w / 2, -5.0, z, w, LEAD_TURN_Y + w + 5.0, t)
    part.label = "load_lead_mock"
    return part


ANT_Y0, ANT_Y1 = 15.00, 40.00       # DESIGN_v2 §3: below the bay


def antenna_mock():
    """25 x 12 x 1.5 flex flag, stuck to the back plate's front face below
    the bay (DESIGN_v2 §3 'Antenna')."""
    part = box_at(CX - ANT_W / 2, ANT_Y0, Z_PLATE - 0.06 - ANT_T,
                  ANT_W, ANT_Y1 - ANT_Y0, ANT_T)
    part.label = "antenna_mock"
    return part


UFL_PLUG_Z = 1.30                   # plug adds 1.3 above the jack
CABLE_D = 1.20
CABLE_BX = (17.00, 20.00)           # board-x run over the -y edge
CABLE_BZ = (6.00, 7.20)             # clear of the expansion edge and the rail


def ufl_plug_mock(inflate=0.0):
    """The mating U.FL plug that clips onto the jack — the 1.3 it adds on top
    of the vendor jack (the jack itself is already in the vendor STEP)."""
    g = inflate
    x0, y0, x1, y1, _, z1 = B.UFL
    part = bbox_case(x0 - g, x1 + g, y0 - g, y1 + g, z1 - g, z1 + UFL_PLUG_Z + g)
    part.label = "ufl_plug_mock"
    return part


def cable_mock(inflate=0.0):
    """Ø1.2 coax leaving the U.FL plug over the board's -y edge, rising clear
    of the expansion edge before it crosses the low far-end wall."""
    g = inflate
    part = bbox_case(CABLE_BX[0] - g, CABLE_BX[1] + g,
                     -CABLE_D / 2 - g, CABLE_D / 2 + g,
                     CABLE_BZ[0] - g, CABLE_BZ[1] + g)
    part.label = "ufl_cable_mock"
    return part


def button_mocks(inflate=0.0):
    g = inflate
    out = []
    for k, t in B.BUTTONS.items():
        x0, y0, x1, y1, z0, z1 = t
        s = bbox_case(x0 - g, x1 + g, y0 - g, y1 + g, z0 - g, z1 + g)
        s.label = f"button_{k.lower()}"
        out.append(s)
    return out


def screw_mocks():
    """4 x M2 x 12 pan head, driven from the boss tops into the back plate."""
    out = []
    for i, (bx, by) in enumerate(BOSS_XY):
        s = cyl_at(bx, by, BOSS_Z0, SCREW_D, SCREW_L)
        s += cyl_at(bx, by, BOSS_Z0 - SCREW_HEAD_T, SCREW_HEAD_D, SCREW_HEAD_T)
        s.label = f"screw_m2x12_{i + 1}"
        out.append(s)
    return out


# DEVIATION (v2): v1 pivoted the insertion tilt about the PCB-TOP far corner.
# That drives the PCB's back-far corner 0.28 further in at 13 deg and bites
# the stop ribs (0.06 mm^3) for a motion the board cannot make — the far edge
# is already against them.  v2 pivots about the corner that actually beds in
# the groove, the PCB's BACK far corner (board x = PCB_L, z = 0).
TILT_PIVOT_Z = 0.0


def tilt_loc(deg, pivot_z=TILT_PIVOT_Z):
    """Insertion tilt: rotate the board about the line through its far-edge
    PCB-back corners (board x = PCB_L, z = pivot_z, along board y), raising
    the USB end out of the bay while the far edge stays in the groove."""
    return Pos(PCB_L, 0, pivot_z) * Rot(0, deg, 0) * Pos(-PCB_L, 0, -pivot_z)
