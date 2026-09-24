"""puckcase v3 — the CASE around the v3.1 holder (DESIGN_v3.md §3, §6, §14).

Case frame (as v2.4): X 0..47.21, Y 0..80.80 (up), Z 0 = outer front face,
+Z toward the puck.  The holder and the board are modelled in the BOARD
frame (v3lib.py) and placed here with BOARD_LOC:  x^ -> +Y (USB end DOWN),
y^ -> +X, z^ -> -Z (lens forward).

What is reused from v2.4 unchanged (puckcase_lib.py, imported as P2): the
outline, front-mouth lead-in, eave + drip groove, the 4 screw bosses + M2 x 12,
cord slot, tie post, the whole back plate, the front plate's lip and ribs.
What replaces the v2.4 bay: two plain internal walls, each with a NOTCH at
its front end that the holder's ears drop into (floor at Z 10.30 = the
holder's Z datum), and a LEDGE under each bottom corner of the PCB as the
board's positive stop against sliding back out of the holder.  Z_PLATE stays
26.36 so a header board's pin tails (to Z 25.86) still fit.
"""

import sys
from pathlib import Path

from build123d import Compound, Location, Plane, Pos, Circle, loft  # noqa: F401

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import puckcase_lib as P2      # noqa: E402  v2.4 case library (shell, eave, bosses, back plate)
import v3lib as H              # noqa: E402  the holder + board mocks, board frame

prism, flare_down, flare_up = P2.prism, P2.flare_down, P2.flare_up
box_at, cyl_at, slot_y, prism_x = P2.box_at, P2.cyl_at, P2.slot_y, P2.prism_x   # box_at(x0,y0,z0,dx,dy,dz)

# ---------------------------------------------------------------------------
# board placement (DESIGN_v3 §3)
# ---------------------------------------------------------------------------
X_B0 = P2.CX - H.CAM_Y                 # 15.355  lens axis on CX
Y_B0 = 53.45                           # holder top end at Y 76.50, inside the plate's lip prism
Z_B0 = P2.Z_B0                         # 17.36   PCB back; 1.0 lens gap behind the plate
BOARD_LOC = Plane(origin=(X_B0, Y_B0, Z_B0), x_dir=(0, 1, 0), z_dir=(0, 0, -1)).location


def b2c(x=0.0, y=0.0, z=0.0):
    """Board-frame point -> case frame."""
    return (X_B0 + y, Y_B0 + x, Z_B0 - z)


def place(shape):
    return BOARD_LOC * shape


LENS_XC, LENS_YC = b2c(H.CAM_X, H.CAM_Y)[:2]          # 23.605, 56.98
Z_PLATE = P2.Z_PLATE                                    # 26.36

# holder envelope in the case frame
HOLDER_X0, HOLDER_X1 = X_B0 + H.OUT_Y0, X_B0 + H.OUT_Y1      # 13.205 .. 35.285
HOLDER_Y0, HOLDER_Y1 = Y_B0 + H.X_FACE0, Y_B0 + H.X1         # 52.45 .. 76.50
EAR_X0, EAR_X1 = X_B0 + H.OUT_Y0 - H.EAR_OUT, X_B0 + H.OUT_Y1 + H.EAR_OUT   # 11.105 .. 37.385
EAR_Y0, EAR_Y1 = Y_B0 + H.EAR_X0, Y_B0 + H.EAR_X1 + H.EAR_OUT              # 53.95 .. 62.05
EAR_SEAT_Z = Z_B0 - H.EAR_Z0                                  # 10.30
EAR_TOP_Z = Z_B0 - H.EAR_Z1                                   # 2.50

# ---------------------------------------------------------------------------
# ring v3: internal walls with notches, ledges
# ---------------------------------------------------------------------------
WALL_T = 1.60
WALL_CLR = 0.15                          # wall inner face to the holder legs
WALL_XA = (HOLDER_X0 - WALL_CLR - WALL_T, HOLDER_X0 - WALL_CLR)   # 11.455 .. 13.055
WALL_XB = (HOLDER_X1 + WALL_CLR, HOLDER_X1 + WALL_CLR + WALL_T)   # 35.435 .. 37.035
WALL_Y0, WALL_Y1 = 50.00, P2.IN_Y1       # tied to the top wall
WALL_Z0 = P2.SIDE_BACK_Z0                # 8.70, 0.30 behind the plate lip nose

NOTCH_CLR = 0.10
NOTCH_Y = (EAR_Y0 - NOTCH_CLR, EAR_Y1 + NOTCH_CLR)    # 53.85 .. 62.15
NOTCH_Z1 = EAR_SEAT_Z                                 # floor at 10.30

LEDGE_BY = (0.0, 2.0)                    # board y span of each ledge (mirror), outside the USB plug
LEDGE_BX = (-1.2, -0.2)                  # 0.20 below the PCB end edge
LEDGE_BZ = (0.15, 1.25)                  # in front of a flush header body, on the PCB's end face


def _walls_notches_ledges():
    parts = []
    for xa, xb in (WALL_XA, WALL_XB):
        w = box_at(xa, WALL_Y0, WALL_Z0, xb - xa, WALL_Y1 - WALL_Y0, Z_PLATE - WALL_Z0)
        w -= box_at(xa - 1, NOTCH_Y[0], WALL_Z0 - 1, (xb - xa) + 2, NOTCH_Y[1] - NOTCH_Y[0], (NOTCH_Z1 - WALL_Z0) + 1)
        parts.append(w)
    # ledges: from each wall inward under the PCB's bottom corners
    for by0, by1 in (LEDGE_BY, (H.PCB_W - LEDGE_BY[1], H.PCB_W - LEDGE_BY[0])):
        x0, x1 = sorted((X_B0 + by0, X_B0 + by1))
        wall_x = WALL_XA[1] if x0 < P2.CX else WALL_XB[0]
        lx0, lx1 = sorted((wall_x, x1 if x0 < P2.CX else x0))
        y0, y1 = Y_B0 + LEDGE_BX[0], Y_B0 + LEDGE_BX[1]
        z0, z1 = Z_B0 - LEDGE_BZ[1], Z_B0 - LEDGE_BZ[0]
        parts.append(box_at(lx0, y0, z0, lx1 - lx0, y1 - y0, z1 - z0))
    return parts


def ring():
    """v2.4 ring body without its bay, plus the v3 walls / notches / ledges."""
    part = prism(P2.OUT_X0, P2.OUT_Y0, P2.OUT_X1, P2.OUT_Y1, P2.R_OUT, P2.PLATE_T, Z_PLATE, ct=P2.EFOOT)
    part -= prism(P2.IN_X0, P2.IN_Y0, P2.IN_X1, P2.IN_Y1, P2.R_IN, P2.PLATE_T - 1.0, Z_PLATE + 1.0)
    lead_in = flare_down(P2.IN_X0, P2.IN_Y0, P2.IN_X1, P2.IN_Y1, P2.R_IN, P2.PLATE_T, P2.LEADIN)
    lead_in &= box_at(P2.OUT_X0 - 5.0, P2.OUT_Y0 - 5.0, P2.PLATE_T - 1.0,
                      P2.OUT_W + 10.0, P2.Y_SHOULDER + 5.0, P2.LEADIN + 2.0)
    part -= lead_in
    part -= flare_up(P2.IN_X0, P2.IN_Y0, P2.IN_X1, P2.IN_Y1, P2.R_IN, Z_PLATE, P2.LEADIN)
    eave = prism(P2.OUT_X0, P2.OUT_Y0, P2.OUT_X1, P2.OUT_Y1, P2.R_OUT, P2.Z_EAVE, P2.PLATE_T)
    eave &= box_at(-5.0, P2.Y_SHOULDER, P2.Z_EAVE - 1.0, P2.OUT_W + 10.0, P2.OUT_H + 10.0, P2.EAVE + P2.PLATE_T + 2.0)
    eave -= prism(P2.IN_X0, P2.IN_Y0, P2.IN_X1, P2.IN_Y1, P2.R_IN, P2.Z_EAVE - 1.0, P2.PLATE_T + 1.0)
    part += eave
    part -= prism_x([(P2.IN_Y1, P2.DRIP_Z0), (P2.IN_Y1, P2.DRIP_Z1), (P2.IN_Y1 + P2.DRIP_D, P2.DRIP_Z1)],
                    P2.IN_X0 + P2.R_IN, P2.IN_X1 - P2.R_IN)
    for p in _walls_notches_ledges():
        part += p
    for bx, by in P2.BOSS_XY:
        part += cyl_at(bx, by, P2.BOSS_Z0, P2.BOSS_D, Z_PLATE - P2.BOSS_Z0)
        fx0, fx1 = sorted((bx, P2.IN_X0 if bx < P2.CX else P2.IN_X1))
        fy0, fy1 = sorted((by, P2.IN_Y0 if by < P2.OUT_H / 2 else P2.IN_Y1))
        part += box_at(fx0, fy0, P2.BOSS_Z0, fx1 - fx0, fy1 - fy0, Z_PLATE - P2.BOSS_Z0)
    part += cyl_at(P2.TIE_POST_XC, P2.TIE_POST_YC, P2.TIE_POST_Z0, P2.TIE_POST_D, Z_PLATE - P2.TIE_POST_Z0)
    part += box_at(P2.TIE_POST_XC - P2.TIE_WEB_W / 2, P2.IN_Y0, P2.TIE_POST_Z0,
                   P2.TIE_WEB_W, P2.TIE_POST_YC - P2.IN_Y0, Z_PLATE - P2.TIE_POST_Z0)
    for bx, by in P2.BOSS_XY:
        part -= cyl_at(bx, by, P2.BOSS_Z0 - 1.0, P2.BOSS_BORE, (Z_PLATE - P2.BOSS_Z0) + 2.0)
    part -= slot_y(P2.CORD_SLOT_XC, P2.CORD_SLOT_ZC, P2.CORD_SLOT_W, P2.CORD_SLOT_H,
                   P2.OUT_Y0 - 1.0, P2.IN_Y0 + 1.0, r=P2.CORD_SLOT_R)
    part.label = "ring"
    return part


def front_plate():
    """v2.4 plate without the head window boss; lens hole at the v3 LENS_YC."""
    keep = box_at(-5.0, -5.0, -5.0, P2.OUT_W + 10.0, P2.Y_SHOULDER + 5.0, 20.0)
    keep += prism(P2.LIP_X0, P2.LIP_Y0, P2.LIP_X1, P2.LIP_Y1, P2.R_LIP, -5.0, P2.FRONT_LIP_Z1 + 1.0)
    part = prism(P2.OUT_X0, P2.OUT_Y0, P2.OUT_X1, P2.OUT_Y1, P2.R_OUT, 0.0, P2.PLATE_T, cb=P2.EFOOT)
    part = part & keep
    part += prism(P2.LIP_X0, P2.LIP_Y0, P2.LIP_X1, P2.LIP_Y1, P2.R_LIP, P2.FRONT_LIP_Z0, P2.FRONT_LIP_Z1, ct=P2.LEADIN)
    part -= prism(P2.BAY_X0, P2.BAY_Y0, P2.BAY_X1, P2.BAY_Y1, P2.R_BAY, P2.FRONT_LIP_Z0, P2.FRONT_LIP_Z1 + 1.0)
    part += P2._front_ribs(P2.FRONT_LIP_Z0, P2.FRONT_RIB_H)
    part -= cyl_at(LENS_XC, LENS_YC, -1.0, P2.LENS_HOLE_D, P2.PLATE_T + 2.0)
    part -= Pos(LENS_XC, LENS_YC) * loft([
        Plane.XY.offset(0.0) * Circle(P2.LENS_HOLE_D / 2 + P2.LENS_CHAMFER),
        Plane.XY.offset(P2.LENS_CHAMFER) * Circle(P2.LENS_HOLE_D / 2),
    ])
    part.label = "front_plate"
    return part


def back_plate():
    return P2.back_plate()


# ---------------------------------------------------------------------------
# assemblies
# ---------------------------------------------------------------------------
def holder_in_case(**kw):
    h = place(H.holder(**kw))
    h.label = "holder"
    return h


def board_in_case(headers=True):
    out = []
    for k, s in H.board_mocks(headers=headers).items():
        p = place(s)
        p.label = k
        out.append(p)
    return out


def assembly(explode=0.0, headers=True):
    """Every part in place; explode > 0 pulls the front plate forward, the
    holder (with the board) forward by half, and the back plate backward."""
    fp = Pos(0, 0, -explode) * front_plate()
    fp.label = "front_plate"
    hz = -explode * 0.5
    parts = [fp, ring(), Pos(0, 0, explode * 0.6) * back_plate(), Pos(0, 0, hz) * holder_in_case()]
    parts[2].label = "back_plate"
    parts[3].label = "holder"
    for b in board_in_case(headers):
        m = Pos(0, 0, hz) * b
        m.label = b.label
        parts.append(m)
    return Compound(children=parts, label="case_v3")
