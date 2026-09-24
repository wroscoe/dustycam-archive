"""puckcase v3 — the camera HOLDER (DESIGN_v3.md §13/§14).

BOARD frame (xiao_board_ref.py): origin at the base PCB's plan bottom-left,
+x along the long edge from the USB-C end, z = 0 the PCB back, lens +z.
The holder is a plain C-channel the board slides into along +x from its open
bottom end (x < 0) until the expansion PCB meets the end wall.

v3.1 (Wade's markup of the v3.0 sections, 2026-09-15, review_v3/*_rev1.png):
  * "just a C shaped unclosed ring" — face, two straight legs snug on the
    board, a small lip at the bottom of each leg.  No backing block, no
    deep legs, no stepped rear zone.
  * "the friction fit with ribs is going to be fine" — two crush ribs per
    leg on the PCB edge are the grip.
  * "the outside of the header lines up with the outside of the board" —
    header body y 0..2.54 (was overhanging 1.0), pins at y 1.27.
The lip reaches 0.75 under the header body's outer strip (pins start at
y 0.95) and sits 0.15 below the body (z -2.65), so the same holder takes a
board with or without headers; a bare board has 2.65 of z play against the
ribs' grip.  holder(lip_under="pcb") is the snug variant for a board that
will never get headers (lip 0.15 under the PCB back).

Lens datum: the face bears on the 8.3 sq sensor plate (largest round part of
the lens is D 6.95, no shoulder); a 7.35 keyhole lets the barrel slide in.

Print: standing on the END WALL (x = X1 on the bed), open end up — every fin
is vertical and the keyhole opens at the top.
"""

import sys
from pathlib import Path

from build123d import (  # noqa: F401
    Align, Box, Compound, Cylinder, Pos, Rot, Vector, Wire, chamfer, extrude, make_face,
)

HERE = Path(__file__).resolve().parent
_ROOT = HERE.parents[3]                       # .../dustycam
for _p in (str(_ROOT / "hardware" / "power_puck"),
           str(_ROOT / "cameras" / "xiao_pantilt" / "ref" / "tripodcase")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import fits                    # noqa: E402  shared fit constants
import xiao_board_ref as B     # noqa: E402  measured XIAO feature boxes

# ---------------------------------------------------------------------------
# Board (vendor STEP unless noted)
# ---------------------------------------------------------------------------
PCB_L, PCB_W, PCB_T = B.PCB_L, B.PCB_W, B.PCB_T      # 20.95, 17.78, 1.25
EXP_X1 = B.EXP[2]                                    # 21.25 expansion PCB far end
CAM_X, CAM_Y = B.CAM_C                               # 3.53, 8.25 lens axis
HEAD_SQ = 8.30                  # MEASURED 2026-09-13 (vendor 8.0), centred on the lens
HEAD_Z0, HEAD_Z1 = 8.20, 10.30  # vendor; 2.1 tall matches the measurement
LENS_D = 6.95                   # MEASURED 2026-09-15: largest round part of the lens
LENS_Z1 = B.STACK_TOP           # 13.96 vendor lens top
PCB_MID_Y = PCB_W / 2           # 8.89

# pin headers (optional).  Wade 2026-09-15: body outer face flush with the
# PCB edge.  2.54 body, 7 pins on the castellation pitch, tails to z -8.5.
HDR_BY = (0.00, 2.54)           # body across the row, mirror 15.24..17.78
HDR_BX = (1.585, 19.365)        # body along the row (7 x 2.54)
HDR_BZ = (-2.50, 0.00)          # body on the PCB back
HDR_PIN = 0.64
HDR_PIN_Z0 = -8.50              # pin tails
HDR_PIN_BY = 1.27               # pin row centre, mirror 16.51
HDR_PIN_BX = B.CASTELL_X        # 2.855 + 2.54 i, i = 0..6

# ---------------------------------------------------------------------------
# Fits
# ---------------------------------------------------------------------------
SIDE_CLR = fits.LIP_GAP         # 0.15 leg to PCB edge / header body face
RIB_PROUD = fits.LIP_RIB_PROUD  # 0.25 -> 0.10 net crush per side
HEAD_SLIDE_CLR = 0.15           # face to the sensor plate while the board slides in
LENS_CLR = 0.20                 # radial, barrel in the keyhole
END_CLR = 0.20                  # end wall to the expansion PCB
LIP_CLR = 0.15                  # lip to the header body bottom (or the PCB back)
PIN_CLR = 0.20                  # lip tip to the pin tails
EFOOT = fits.ELEPHANT_FOOT      # 0.40

# ---------------------------------------------------------------------------
# Holder
# ---------------------------------------------------------------------------
FACE_T = 1.60
LEG_T = 2.00
END_T = 1.60
LIP_T = 1.20

X_FACE0 = -1.00                 # front face runs 0.53 past the head's overhang
X_LEG0 = 0.00                   # legs start at the PCB end so a ring ledge can pass under
X_END0 = EXP_X1 + END_CLR       # 21.45 end wall inner face
X1 = X_END0 + END_T             # 23.05 end wall outer face = the bed

FACE_Z0 = HEAD_Z1 + HEAD_SLIDE_CLR   # 10.45 face inner (bears on the sensor plate)
FACE_Z1 = FACE_Z0 + FACE_T           # 12.05 face outer
KEY_W = LENS_D + 2 * LENS_CLR        # 7.35 keyhole width / bore (v3.1 face only)

# v4 CAMERA PLATE (Wade 2026-09-15, review_v31/v4k-...-202416_rev1.png):
# the module is a flying head on its flex, so its flat BACK is GLUED to the
# plate's outer face and the whole head sits in FRONT of the holder.  The
# plate is solid — no keyhole, no lens slot — and covers the head's footprint
# only; the rest of the holder's top is open so the flex can drop through to
# the FPC socket.  The plate is also the print bed face.
PLATE_X0 = -1.25                     # head runs x -0.47..7.53: >= 0.6 margin all round
PLATE_X1 = 8.50
GLUE_Z = FACE_Z1                     # 12.05 outer face of the plate = glue face
HEAD_T = HEAD_Z1 - HEAD_Z0           # 2.10 head body
HEAD_G_Z0, HEAD_G_Z1 = GLUE_Z, GLUE_Z + HEAD_T                  # 12.05 .. 14.15
LENS_G_Z1 = GLUE_Z + (LENS_Z1 - HEAD_Z0)                        # 17.81 lens tip, glued

CH_Y0, CH_Y1 = -SIDE_CLR, PCB_W + SIDE_CLR       # -0.15 .. 17.93 channel (snug, no step)
OUT_Y0, OUT_Y1 = CH_Y0 - LEG_T, CH_Y1 + LEG_T    # -2.15 .. 19.93

LIP_IN = HDR_PIN_BY - HDR_PIN / 2 - PIN_CLR      # 0.75: lip tip, 0.20 off the pin tails
LIP_Z1_HDR = HDR_BZ[0] - LIP_CLR                 # -2.65 under the header body
LIP_Z1_PCB = -LIP_CLR                            # -0.15 under a bare PCB (snug variant)

# grip ribs on the leg inner faces, over the PCB thickness only; start 0.20
# above the PCB back so a header body (top flush with the back) clears them
RIB_Z = (0.20, PCB_T + 0.05)
RIB_X = (5.00, 17.00)            # rib centres (default: 2 per leg)
RIB_LEN = 1.50                   # along x, incl. 45 deg ramps on both ends

# rib variants (Wade 2026-09-15).  The base PCB's straight edge runs
# x 1.91..19.04 (corner r 1.906), so every centre stays inside that.
#   "fine": more, very small ribs   -> 4 per leg, 0.05 crush per side
#   "firm": slightly larger ribs    -> 2 per leg, 0.17 crush per side
RIB_SETS = {
    "std":  dict(rib_x=RIB_X, rib_proud=RIB_PROUD, rib_len=RIB_LEN),
    "fine": dict(rib_x=(4.00, 8.50, 13.00, 17.50), rib_proud=0.20, rib_len=1.20),
    "firm": dict(rib_x=RIB_X, rib_proud=0.32, rib_len=RIB_LEN),
}

# ears: hang the holder in the ring's wall notches.  Seat at board z 7.06
# (= case Z 10.30 with Z_B0 17.36); top at z 14.86 (= case Z 2.50, 0.10
# under the front plate).  +x end gabled 45 deg so it prints standing.
EAR_X0, EAR_X1 = 0.50, 6.50
EAR_OUT = 2.10
EAR_Z0, EAR_Z1 = 7.06, 14.86

# coax window through the -y leg for the U.FL plug + cable (jack x 17.73..20.73,
# cable exits -y at z ~1.25..3.8).  Gabled roof so it prints standing.
COAX_X = (17.20, 21.30)
COAX_Z = (1.00, 4.50)

# v4 (DESIGN_v3 §16): DOVETAIL RAIL on the end wall's outer face (x = X1),
# centred on the channel, running along z from the face outer back to
# RAIL_Z0.  It slides into the matching slot in the front cup's top wall.
# 45 deg flanks; the slot is 0.15 wider per side.  Print: face down, the
# rail is a vertical fin.
RAIL_W0 = 6.00                   # width at the root (on the end wall)
RAIL_H = 2.30                    # height off the end wall
RAIL_W1 = RAIL_W0 + 2 * RAIL_H   # 10.60 at the top (45 deg dovetail)
RAIL_Z0 = -1.35                  # back end of the rail (case Z 15.80, 0.2 before the back plate's lip band)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def box_at(x0, y0, z0, x1, y1, z1):
    return Pos(x0, y0, z0) * Box(x1 - x0, y1 - y0, z1 - z0, align=(Align.MIN,) * 3)


def _poly_xy(pts, z0, z1):
    face = make_face(Wire.make_polygon([Vector(x, y, z0) for x, y in pts], close=True))
    return extrude(face, amount=z1 - z0, dir=Vector(0, 0, 1))


def _poly_xz(pts, y0, y1):
    face = make_face(Wire.make_polygon([Vector(x, y0, z) for x, z in pts], close=True))
    return extrude(face, amount=y1 - y0, dir=Vector(0, 1, 0))


def _mirror_y(y):
    return PCB_W - y


def lip_z(lip_under):
    z1 = {"header": LIP_Z1_HDR, "pcb": LIP_Z1_PCB}[lip_under]
    return z1 - LIP_T, z1


# ---------------------------------------------------------------------------
# holder pieces
# ---------------------------------------------------------------------------
def _front_face(plate=False):
    """plate=True (v4): a SOLID band over the camera's footprint only — the
    module's back is glued to its outer face.  plate=False (v3.1): the
    full-length face with the lens keyhole the head used to poke through."""
    if plate:
        return box_at(PLATE_X0, OUT_Y0, FACE_Z0, PLATE_X1, OUT_Y1, FACE_Z1)
    face = box_at(X_FACE0, OUT_Y0, FACE_Z0, X1, OUT_Y1, FACE_Z1)
    bore = Pos(CAM_X, CAM_Y, FACE_Z0 - 1) * Cylinder(
        KEY_W / 2, FACE_T + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    slot = box_at(X_FACE0 - 1, CAM_Y - KEY_W / 2, FACE_Z0 - 1, CAM_X, CAM_Y + KEY_W / 2, FACE_Z1 + 1)
    return face - bore - slot


def _leg(y_out, y_ch, z0, ribs=True, rib_x=RIB_X, rib_proud=RIB_PROUD, rib_len=RIB_LEN,
         z_top=FACE_Z0 + 0.01):
    ya, yb = sorted((y_out, y_ch))
    leg = box_at(X_LEG0, ya, z0, X1, yb, z_top)
    if ribs:
        d = 1.0 if y_ch < PCB_MID_Y else -1.0        # rib protrudes toward the PCB
        for xc in rib_x:
            x0, x1 = xc - rib_len / 2, xc + rib_len / 2
            pts = [(x0, y_ch), (x0 + rib_proud, y_ch + d * rib_proud),
                   (x1 - rib_proud, y_ch + d * rib_proud), (x1, y_ch)]
            leg = leg + _poly_xy(pts, RIB_Z[0], RIB_Z[1])
    return leg


def _lips(z0, z1, chamfer_under=False):
    """Rear lips.  chamfer_under=True gives the PCB-facing side a 45 deg
    slope (0.30 flat at the tip) so the lip prints face-down without an
    overhang; the flat tip still catches the header body / PCB back."""
    if not chamfer_under:
        return [box_at(X_LEG0, CH_Y0, z0, X_END0, LIP_IN, z1),
                box_at(X_LEG0, _mirror_y(LIP_IN), z0, X_END0, CH_Y1, z1)]
    reach = LIP_IN - CH_Y0                            # 0.90
    out = []
    for y_leg, d in ((CH_Y0, 1.0), (CH_Y1, -1.0)):
        tip = y_leg + d * reach
        pts = [(y_leg, z1), (y_leg, z0), (tip, z0), (tip, z0 + 0.30), (y_leg + d * max(0.0, reach - (z1 - z0 - 0.30)), z1)]
        face = make_face(Wire.make_polygon([Vector(X_LEG0, y, z) for y, z in pts], close=True))
        out.append(extrude(face, amount=X_END0 - X_LEG0, dir=Vector(1, 0, 0)))
    return out


def _end_wall(z0):
    return box_at(X_END0, OUT_Y0, z0, X1, OUT_Y1, FACE_Z1)


def _ears():
    out = []
    for y_face, d in ((OUT_Y0, -1.0), (OUT_Y1, 1.0)):
        pts = [(EAR_X0, y_face), (EAR_X1 + EAR_OUT, y_face),
               (EAR_X1, y_face + d * EAR_OUT), (EAR_X0, y_face + d * EAR_OUT)]
        out.append(_poly_xy(pts, EAR_Z0, EAR_Z1))
    return out


def _coax_window(print_face="end"):
    (x0, x1), (z0, z1) = COAX_X, COAX_Z
    if print_face == "end":                          # standing on the end wall: roof is the -x side
        ridge_x = x0 - (z1 - z0) / 2
        pts = [(x1 + 1, z0), (x1 + 1, z1), (x0, z1), (ridge_x, (z0 + z1) / 2), (x0, z0)]
    else:                                            # face down: roof is the low-z side
        ridge_z = z0 - (x1 - x0) / 2
        pts = [(x0, z1), (x1, z1), (x1, z0), ((x0 + x1) / 2, ridge_z), (x0, z0)]
    return _poly_xz(pts, OUT_Y0 - 1, CH_Y0 + 0.5)


def _rail():
    """Dovetail rail on the end wall's outer face, centred on the channel."""
    yc = (CH_Y0 + CH_Y1) / 2
    pts = [(X1, yc - RAIL_W0 / 2), (X1, yc + RAIL_W0 / 2),
           (X1 + RAIL_H, yc + RAIL_W1 / 2), (X1 + RAIL_H, yc - RAIL_W1 / 2)]
    return _poly_xy(pts, RAIL_Z0, FACE_Z1)


def holder(lip_under="header", ribs="std", label="holder", ears=True, rail=False, print_face="end"):
    """The C-channel.  lip_under: "header" (universal, lip 0.15 under the
    header body) or "pcb" (snug variant for a board without headers).
    ribs: a RIB_SETS key ("std", "fine", "firm") or False for none.
    v3.1: ears=True, rail=False, print_face="end" (stands on the end wall).
    v4:   ears=False, rail=True, print_face="face" (prints on its face; the
          dovetail rail hangs it from the front cup's top wall)."""
    lz0, lz1 = lip_z(lip_under)
    rk = RIB_SETS[ribs if isinstance(ribs, str) else "std"] if ribs else {}
    # v4: the face is a plate at the camera end only, so the legs must reach the
    # bed face themselves — otherwise they print as islands over the open middle.
    zt = FACE_Z1 if rail else FACE_Z0 + 0.01
    part = _front_face(plate=rail) + _end_wall(lz0)
    part = part + _leg(OUT_Y0, CH_Y0, lz0, bool(ribs), z_top=zt, **rk)
    part = part + _leg(OUT_Y1, CH_Y1, lz0, bool(ribs), z_top=zt, **rk)
    for b in _lips(lz0, lz1, chamfer_under=(print_face == "face")):
        part = part + b
    if ears:
        for e in _ears():
            part = part + e
    if rail:
        part = part + _rail()
    part = part - _coax_window(print_face)
    if print_face == "end":
        bed_edges = part.edges().filter_by(lambda e: abs(e.center().X - X1) < 1e-6 and e.length > 3.0)
    else:
        bed_edges = part.edges().filter_by(lambda e: abs(e.center().Z - FACE_Z1) < 1e-6 and e.length > 3.0)
    part = chamfer(bed_edges, EFOOT)
    part.label = label
    return part


# ---------------------------------------------------------------------------
# board mocks (envelope boxes, board frame) — the measured lens/head override
# the vendor head
# ---------------------------------------------------------------------------
def _b(t, g=0.0):
    x0, y0, x1, y1, z0, z1 = t
    return box_at(x0 - g, y0 - g, z0 - g, x1 + g, y1 + g, z1 + g)


def camera_on_plate(g=0.0):
    """The module GLUED to the v4 camera plate: 8.30 head on the plate's outer
    face, lens barrel above it.  Board frame, so it places with the board."""
    head = box_at(CAM_X - HEAD_SQ / 2 - g, CAM_Y - HEAD_SQ / 2 - g, HEAD_G_Z0 - g,
                  CAM_X + HEAD_SQ / 2 + g, CAM_Y + HEAD_SQ / 2 + g, HEAD_G_Z1 + g)
    head.label = "sensor_plate"
    barrel = Pos(CAM_X, CAM_Y, HEAD_G_Z1 - g) * Cylinder(
        LENS_D / 2 + g, LENS_G_Z1 - HEAD_G_Z1 + 2 * g, align=(Align.CENTER, Align.CENTER, Align.MIN))
    barrel.label = "lens_barrel"
    return {"sensor_plate": head, "lens_barrel": barrel}


def board_mocks(headers=False, inflate=0.0, card=True, head=True):
    """{label: solid}.  inflate grows every box by that much on every side.
    head=False drops the camera head/lens: on v4 the module is glued to the
    holder's plate, not folded onto the board (see camera_on_plate)."""
    g = inflate
    m = {
        "base_pcb": box_at(-g, -g, -g, PCB_L + g, PCB_W + g, PCB_T + g),
        "expansion_pcb": _b(B.EXP, g),
        "usb_c_shell": _b(B.USB, g),
        "esp32s3_can": _b(B.SHIELD, g),
        "b2b_connector": _b(B.B2B, g),
        "ufl_jack": _b(B.UFL, g),
        "microsd_socket": _b(B.SD_SOCKET, g),
        "camera_fpc_socket": _b(B.FPC_CONN, g),
        "camera_fpc_roll": _b(B.FPC_ROLL, g),
        "button_rst": _b(B.BUTTONS["RST"], g),
        "button_boot": _b(B.BUTTONS["BOOT"], g),
    }
    if head:
        m["sensor_plate"] = box_at(CAM_X - HEAD_SQ / 2 - g, CAM_Y - HEAD_SQ / 2 - g, HEAD_Z0 - g,
                                   CAM_X + HEAD_SQ / 2 + g, CAM_Y + HEAD_SQ / 2 + g, HEAD_Z1 + g)
        m["lens_barrel"] = Pos(CAM_X, CAM_Y, HEAD_Z1 - g) * Cylinder(
            LENS_D / 2 + g, LENS_Z1 - HEAD_Z1 + 2 * g, align=(Align.CENTER, Align.CENTER, Align.MIN))
    if card:
        m["microsd_card"] = _b(B.SD_CARD, g)
    if headers:
        for i, (y0, y1) in enumerate((HDR_BY, (_mirror_y(HDR_BY[1]), _mirror_y(HDR_BY[0])))):
            m[f"header_body_{i}"] = box_at(HDR_BX[0] - g, y0 - g, HDR_BZ[0] - g,
                                           HDR_BX[1] + g, y1 + g, HDR_BZ[1] + g)
            yc = HDR_PIN_BY if i == 0 else _mirror_y(HDR_PIN_BY)
            for j, px in enumerate(HDR_PIN_BX):
                m[f"header_pin_{i}_{j}"] = box_at(px - HDR_PIN / 2 - g, yc - HDR_PIN / 2 - g, HDR_PIN_Z0 - g,
                                                  px + HDR_PIN / 2 + g, yc + HDR_PIN / 2 + g, 0.0 + g)
    for k, s in m.items():
        s.label = k
    return m


def usb_plug_mock(width=12.5, height=6.5, length=20.0, g=0.0):
    """Assumed USB-C plug overmold, plugged in: nose at x -1.6, centred on the shell."""
    yc, zc = B.USB_YC, B.USB_ZC
    return box_at(-1.6 - length - g, yc - width / 2 - g, zc - height / 2 - g,
                  -1.6 + g, yc + width / 2 + g, zc + height / 2 + g)


# ---------------------------------------------------------------------------
# print orientation
# ---------------------------------------------------------------------------
def holder_print_oriented(part=None, **kw):
    """v3.1: end wall (x = X1) on the bed, open end up: bed z = X1 - x.
    v4 (print_face="face"): face outer (z = FACE_Z1) on the bed: bed z = FACE_Z1 - z."""
    face_down = kw.get("print_face", "end") == "face"
    part = holder(**kw) if part is None else part
    if face_down:
        return Pos(0, 0, FACE_Z1) * Rot(180, 0, 0) * part
    return Pos(0, 0, X1) * Rot(0, 90, 0) * part
