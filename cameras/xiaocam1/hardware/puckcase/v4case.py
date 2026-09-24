"""puckcase v4 — Wade's simplification of 2026-09-15 (DESIGN_v3.md §16).

From his markups of the v3 case sections (review_v31/case_1_X_lens_rev2.png,
case_2_Y_lens_rev1.png, v4k-...-202416_rev1.png):
  * "The front plate and the cup should be merged so there is only a front
    cup. Remove the drip lip so it can be printed with the front face on the
    plate."  -> FRONT CUP: one part, prints face down, no eave, no drip.
  * "This is the part of the camera holder that should slide into the angle
    slot at the top of the front cup" / "angle to attach to front cup"
    -> a DOVETAIL RAIL on the holder's top end slides (from the back mouth,
    along Z) into a dovetail SLOT in the cup's top wall.  The holder's face
    lands flat on the cup's inner front face: no lens gap, no ears, no
    internal walls ("This fork on the back plate can be removed").
  * "The back cup should just slide onto the front cup" -> no screws: the
    cup's back rim has a 1.2 x 4.5 REBATE and the BACK PLATE drops into it
    flush, held by 6 crush ribs on its edge (a lip on both faces of the
    plate would not print flat).  The holder is held in the dovetail by two
    crush ribs per flank — friction, as Wade asked.
  * "The plate for the camera. This is also the face that the holder will be
    printed from" -> holder prints face down.
The board is retained by the holder's channel crush ribs alone — Wade had
the cup's two board-stop posts removed (front_cup.glb comments 1 and 2,
2026-09-15), so the cup's inner front face is clear.

Case frame as before.  Board -> case: x^ -> +Y, y^ -> +X, z^ -> -Z.
"""

import sys
from pathlib import Path

from build123d import Compound, Plane, Pos, Circle, loft  # noqa: F401

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import puckcase_lib as P2      # noqa: E402  outline, lip/rib geometry, puck coupling
import fits                    # noqa: E402
import v3lib as H              # noqa: E402  holder + board mocks (board frame)

prism, box_at, cyl_at, slot_y, prism_x = P2.prism, P2.box_at, P2.cyl_at, P2.slot_y, P2.prism_x

HOLDER_KW = dict(ears=False, rail=True, print_face="face")

# ---------------------------------------------------------------------------
# Z stack
# ---------------------------------------------------------------------------
FACE_T = P2.PLATE_T                        # 2.40 front face of the cup
LENS_TIP_IN = 0.49                         # lens tip this far behind the cup's outer surface
# The camera module is GLUED to the holder's plate and sits in FRONT of it
# (v3lib.camera_on_plate), so the lens now reaches H.LENS_G_Z1 = 17.81 above
# the board, not 13.96: the board sits that much deeper in the cup.
Z_B0 = LENS_TIP_IN + H.LENS_G_Z1           # 18.30 board z=0 plane
LENS_TIP_Z = Z_B0 - H.LENS_G_Z1            # 0.49
HOLDER_FACE_Z = Z_B0 - H.FACE_Z1           # 6.25: plate's outer (glue) face
HEAD_Z0C, HEAD_Z1C = Z_B0 - H.HEAD_G_Z1, HOLDER_FACE_Z          # 4.15 .. 6.25 glued head
HOLDER_Z1 = Z_B0 - H.lip_z("header")[0]    # 22.15 holder back (lips)
PIN_Z1 = Z_B0 - H.HDR_PIN_Z0               # 26.80 header pin tails (if fitted)
REB_D = 4.50                               # rebate depth at the cup's back mouth = back plate thickness
REB_T = 1.20                               # cup wall left outside the rebate
Z_REB0 = PIN_Z1 + 0.55                     # 27.35 back plate front face (pin tails 0.55 clear)
Z_MOUTH = Z_REB0 + REB_D                   # 31.85 cup back rim = plate back face = puck tube mouth
Z_BACK = Z_MOUTH
PUCK_LIP_Z0, PUCK_LIP_Z1 = Z_BACK, Z_BACK + P2.LIP_ENG          # 28.00 .. 35.50
PLATE_GAP = fits.LIP_GAP                   # 0.15 plate edge to rebate wall
PLATE_INSET = REB_T + PLATE_GAP            # 1.35 plate outline inset from OUT

# ---------------------------------------------------------------------------
# board placement
# ---------------------------------------------------------------------------
X_B0 = P2.CX - H.CAM_Y                     # 15.355 lens on CX
TOP_WALL_T = 2.40
SLOT_BOSS_T = 2.00                         # extra wall under the top wall carrying the slot
Y_TOP_IN = P2.OUT_H - TOP_WALL_T - SLOT_BOSS_T                  # 76.00 slot mouth (boss inner face)
RAIL_CLR = 0.15
Y_B0 = Y_TOP_IN - RAIL_CLR - H.X1          # 52.80: holder end wall 0.15 below the boss face
BOARD_LOC = Plane(origin=(X_B0, Y_B0, Z_B0), x_dir=(0, 1, 0), z_dir=(0, 0, -1)).location


def b2c(x=0.0, y=0.0, z=0.0):
    return (X_B0 + y, Y_B0 + x, Z_B0 - z)


def place(shape):
    return BOARD_LOC * shape


LENS_XC, LENS_YC = b2c(H.CAM_X, H.CAM_Y)[:2]          # 23.605, 56.33
HOLDER_X0, HOLDER_X1 = X_B0 + H.OUT_Y0, X_B0 + H.OUT_Y1          # 13.205 .. 35.285
HOLDER_Y0, HOLDER_Y1 = Y_B0 + H.PLATE_X0, Y_B0 + H.X1            # 51.55 .. 75.85
RAIL_XC = X_B0 + (H.CH_Y0 + H.CH_Y1) / 2                          # 24.245
RAIL_Z0, RAIL_Z1 = HOLDER_FACE_Z, Z_B0 - H.RAIL_Z0                # 6.25 .. 19.65

# dovetail slot in the boss: mouth at Y_TOP_IN, 0.15 wider than the rail per side
# the rail root sits RAIL_CLR below the mouth, so at the mouth the rail is already
# RAIL_W0/2 + RAIL_CLR wide; add the 0.15 normal gap (x 0.212 in X) and keep the
# flanks at 45 deg so the gap is constant along the flank.
FLANK_GAP = 0.15                           # normal to the flank; the slot ribs crush 0.10 of it
SLOT_W0 = H.RAIL_W0 + 2 * (RAIL_CLR + FLANK_GAP * 2 ** 0.5)     # 6.72 at the mouth
SLOT_D = H.RAIL_H + 0.35                   # 2.65 deep (0.35 over the rail top)
SLOT_W1 = SLOT_W0 + 2 * SLOT_D             # 12.02 at the bottom (45 deg, parallel to the rail)
SLOT_Z0 = HOLDER_FACE_Z                    # 6.25: closed end — the rail butts here, setting lens depth
SLOT_Z1 = Z_REB0 - 0.5                     # 26.85: boss runs to just short of the rebate
SLOT_RIB_Z = ((9.0, 4.0), (15.5, 4.0))     # (z0, height) of the two crush ribs per flank

BOSS_X0, BOSS_X1 = RAIL_XC - 12.0, RAIL_XC + 12.0
RIB_PROUD = fits.LIP_RIB_PROUD             # 0.25 -> 0.10 crush on the rail flank

# cord slot through the cup's bottom wall, just in front of the rebate
CORD_W, CORD_H, CORD_XC = P2.CORD_SLOT_W, P2.CORD_SLOT_H, P2.CORD_SLOT_XC   # 4.5 x 3.0 at X 13
CORD_Z1 = Z_REB0 - 0.5
CORD_Z0 = CORD_Z1 - CORD_H


# ---------------------------------------------------------------------------
# parts
# ---------------------------------------------------------------------------
def front_cup():
    """Outline shell, closed front face, open back mouth.  Prints face down."""
    part = prism(P2.OUT_X0, P2.OUT_Y0, P2.OUT_X1, P2.OUT_Y1, P2.R_OUT, 0.0, Z_MOUTH, cb=P2.EFOOT)
    part -= prism(P2.IN_X0, P2.IN_Y0, P2.IN_X1, P2.IN_Y1, P2.R_IN, FACE_T, Z_MOUTH + 1.0)
    part -= P2.flare_up(P2.IN_X0, P2.IN_Y0, P2.IN_X1, P2.IN_Y1, P2.R_IN, Z_MOUTH, P2.LEADIN)
    # lens hole + outer chamfer
    part -= cyl_at(LENS_XC, LENS_YC, -1.0, P2.LENS_HOLE_D, FACE_T + 2.0)
    part -= Pos(LENS_XC, LENS_YC) * loft([
        Plane.XY.offset(0.0) * Circle(P2.LENS_HOLE_D / 2 + P2.LENS_CHAMFER),
        Plane.XY.offset(P2.LENS_CHAMFER) * Circle(P2.LENS_HOLE_D / 2),
    ])
    # slot boss under the top wall, with the dovetail slot (open to the back mouth) + crush ribs on its flanks
    part += box_at(BOSS_X0, Y_TOP_IN, FACE_T - 0.01, BOSS_X1 - BOSS_X0, P2.IN_Y1 - Y_TOP_IN + 0.01, SLOT_Z1 - FACE_T + 0.01)
    part -= _slot()
    part += _slot_ribs()
    # rebate at the back mouth for the back plate
    part -= prism(P2.OUT_X0 + REB_T, P2.OUT_Y0 + REB_T, P2.OUT_X1 - REB_T, P2.OUT_Y1 - REB_T, P2.R_OUT - REB_T, Z_REB0, Z_MOUTH + 1.0)
    # cord slot through the bottom wall (a stadium, prints as a vertical slot)
    part -= slot_y(CORD_XC, (CORD_Z0 + CORD_Z1) / 2, CORD_W, CORD_H, P2.OUT_Y0 - 1.0, P2.IN_Y0 + 1.0, r=P2.CORD_SLOT_R)
    part.label = "front_cup"
    return part


def _slot_ribs():
    """Two crush ribs on each 45 deg flank of the slot, protruding into it."""
    from build123d import Rot
    out = None
    mid_h = SLOT_D / 2
    for sign in (+1.0, -1.0):
        xm = RAIL_XC + sign * (SLOT_W0 / 2 + mid_h)     # flank midpoint
        ym = Y_TOP_IN + mid_h
        for z0, h in SLOT_RIB_Z:
            rib = fits.edge_crush_rib(h, length=3.0, proud=RIB_PROUD)
            s = Pos(xm, ym, z0) * Rot(0, 0, sign * 45.0) * rib
            out = s if out is None else out + s
    return out


def _slot():
    """Dovetail slot volume: mouth at Y_TOP_IN (narrow), bottom at Y_TOP_IN + SLOT_D (wide)."""
    # start 0.5 below the mouth ALONG the 45 deg flank so the flank plane is exact (the ribs sit on it)
    pts = [(RAIL_XC - SLOT_W0 / 2 + 0.5, Y_TOP_IN - 0.5), (RAIL_XC + SLOT_W0 / 2 - 0.5, Y_TOP_IN - 0.5),
           (RAIL_XC + SLOT_W1 / 2, Y_TOP_IN + SLOT_D), (RAIL_XC - SLOT_W1 / 2, Y_TOP_IN + SLOT_D)]
    from build123d import Vector, Wire, make_face, extrude
    face = make_face(Wire.make_polygon([Vector(x, y, SLOT_Z0) for x, y in pts], close=True))
    return extrude(face, amount=Z_MOUTH + 1.0 - SLOT_Z0, dir=Vector(0, 0, 1))


PLATE_X0, PLATE_Y0 = P2.OUT_X0 + PLATE_INSET, P2.OUT_Y0 + PLATE_INSET
PLATE_X1, PLATE_Y1 = P2.OUT_X1 - PLATE_INSET, P2.OUT_Y1 - PLATE_INSET
PLATE_R = P2.R_OUT - PLATE_INSET


def _plate_edge_ribs():
    """6 crush ribs on the plate's outer edge (the puck's rib layout), vertical
    in the plate's print orientation (front face down)."""
    rib = fits.edge_crush_rib(REB_D - P2.LEADIN, length=6.0, proud=RIB_PROUD)
    out = None
    for yc in (P2.CY - 15.0, P2.CY + 15.0):
        for x, rz in ((PLATE_X0, 90), (PLATE_X1, -90)):
            s = Pos(x, yc, Z_REB0) * __import__("build123d").Rot(0, 0, rz) * rib
            out = s if out is None else out + s
    out += Pos(P2.CX, PLATE_Y1, Z_REB0) * rib
    out += Pos(P2.CX, PLATE_Y0, Z_REB0) * __import__("build123d").Rot(0, 0, 180) * rib
    return out


def back_plate():
    """Drops into the cup's back rebate, flush with the rim: REB_D thick,
    outline inset 1.35 from the cup's, 6 crush ribs on its edge, the puck's
    press-fit lip on its back.  Prints front face down, lip up (as v2.4)."""
    part = prism(PLATE_X0, PLATE_Y0, PLATE_X1, PLATE_Y1, PLATE_R, Z_REB0, Z_MOUTH, cb=P2.EFOOT, ct=P2.LEADIN)
    part += _plate_edge_ribs()
    part += prism(P2.LIP_X0, P2.LIP_Y0, P2.LIP_X1, P2.LIP_Y1, P2.R_LIP, PUCK_LIP_Z0, PUCK_LIP_Z1, ct=P2.LEADIN)
    part -= prism(P2.BAY_X0, P2.BAY_Y0, P2.BAY_X1, P2.BAY_Y1, P2.R_BAY, PUCK_LIP_Z0, PUCK_LIP_Z1 + 1.0)
    part += P2._front_ribs(PUCK_LIP_Z0, P2.LIP_RIB_H)
    part.label = "back_plate"
    return part


# ---------------------------------------------------------------------------
# assemblies
# ---------------------------------------------------------------------------
def holder_in_case(**kw):
    h = place(H.holder(**{**HOLDER_KW, **kw}))
    h.label = "holder"
    return h


def camera_in_case():
    """The module glued to the holder's plate — it rides with the holder."""
    out = []
    for k, s in H.camera_on_plate().items():
        p = place(s)
        p.label = k
        out.append(p)
    return out


def board_in_case(headers=True):
    out = []
    for k, s in H.board_mocks(headers=headers, head=False).items():
        p = place(s)
        p.label = k
        out.append(p)
    return out


def assembly(explode=0.0, headers=True):
    """explode > 0: holder + board pulled back by half, back plate back by full."""
    parts = [front_cup(), Pos(0, 0, explode) * back_plate(), Pos(0, 0, explode * 0.5) * holder_in_case()]
    parts[1].label = "back_plate"
    parts[2].label = "holder"
    for b in board_in_case(headers) + camera_in_case():
        m = Pos(0, 0, explode * 0.5) * b
        m.label = b.label
        parts.append(m)
    return Compound(children=parts, label="case_v4")
