"""Power puck v1 — bq25185 solar charger + 1S LiPo + panel-mount DC jack,
3-part printed enclosure (geometry library).

Three printed parts, stacked along Z (a straight rounded-rect sleeve capped
at each end):

  tube          straight rectangular sleeve, WALL thick, spanning the middle
                of the stack.  Carries the LOAD-lead slot in its -Y wall.
  front_plate   flat outer cap (z=0 outer face) with a lip that presses into
                the tube's front mouth (z 2.40..9.90).  Notched on the -Y lip
                wall so a JST-PH plug passes.
  back_cup      deep cup: outer shell + a lip that presses into the tube's
                back mouth (z 10.90..18.40), enclosing the charger + battery
                bay.  Carries the charger mounting bosses/pilots and the DC
                jack hole through its -Y skirt wall.

Coordinate frame (puck-local, per the spec):
  X: 0 at the outer -X face .. 47.21.
  Y: 0 at the outer BOTTOM face .. OUT_H (up).
  Z: 0 at the outer FRONT face .. Z_BACK_OUT (toward the back).

Cross-sections are rounded rectangles (RectangleRounded), nested by wall
thickness — R_OUT/R_IN/R_LIP/R_BAY are corner-fillet radii, not a radial
tube dimension.  Fit values come from the project-local fits.py.
"""

from build123d import *  # noqa: F403
import fits

# ---------------------------------------------------------------------------
# Parameters (exact values from the spec — do not change)
# ---------------------------------------------------------------------------
WALL = 2.40
LIP_WALL = 1.60
LIP_GAP = fits.LIP_GAP                 # 0.15/side, press-fit lip into mouth
LIP_RIB_PROUD = fits.LIP_RIB_PROUD     # 0.25 crush ribs -> 0.10/side net
EFOOT = fits.ELEPHANT_FOOT             # 0.40 x 45 deg on bed-contact perimeters
LEADIN = 0.60                          # 45 deg lead-in on friction entries
LIP_ENG = 7.50                         # lip engagement depth (front + back)
LIP_RIB_H = 6.40
R_OUT = 6.00

OUT_W = 47.21
IN_H = 76.00
OUT_H = IN_H + 2 * WALL                # 80.80

# ---------------------------------------------------------------------------
# XY rectangles, nested outward->inward by wall thickness
# ---------------------------------------------------------------------------
OUT_X0, OUT_X1 = 0.0, OUT_W
OUT_Y0, OUT_Y1 = 0.0, OUT_H

R_IN = R_OUT - WALL                    # 3.60
IN_X0, IN_X1 = OUT_X0 + WALL, OUT_X1 - WALL
IN_Y0, IN_Y1 = OUT_Y0 + WALL, OUT_Y1 - WALL

R_LIP = R_IN - LIP_GAP                 # 3.45
LIP_X0, LIP_X1 = IN_X0 + LIP_GAP, IN_X1 - LIP_GAP
LIP_Y0, LIP_Y1 = IN_Y0 + LIP_GAP, IN_Y1 - LIP_GAP

R_BAY = R_LIP - LIP_WALL               # 1.85
BAY_X0, BAY_X1 = LIP_X0 + LIP_WALL, LIP_X1 - LIP_WALL
BAY_Y0, BAY_Y1 = LIP_Y0 + LIP_WALL, LIP_Y1 - LIP_WALL

CX = (OUT_X0 + OUT_X1) / 2             # 23.605
CY = OUT_H / 2                         # 40.40

# ---------------------------------------------------------------------------
# Z stack
# ---------------------------------------------------------------------------
Z_FRONT_OUT = 0.0
Z_TUBE0 = WALL                         # 2.40  tube front mouth / plate inner face
TUBE_D = 16.00
Z_SEAM = Z_TUBE0 + TUBE_D              # 18.40 tube back mouth
CUP_D = 13.50                          # skirt interior depth (back_cup)
Z_FLOOR = Z_SEAM + CUP_D               # 31.90 floor top, inside
Z_BACK_OUT = Z_FLOOR + WALL            # 34.30

FRONT_LIP_Z0, FRONT_LIP_Z1 = Z_TUBE0, Z_TUBE0 + LIP_ENG    # 2.40, 9.90
BACK_LIP_Z0, BACK_LIP_Z1 = Z_SEAM - LIP_ENG, Z_SEAM         # 10.90, 18.40
# 1.00 gap between the two lip noses: BACK_LIP_Z0 - FRONT_LIP_Z1 == 1.00

# ---------------------------------------------------------------------------
# Charger (Adafruit 6091 bq25185).  Vendor STEP frame: PCB plan bottom-left,
# z = 0 PCB bottom, components +z.  CHG_L is the spec's documented PCB length
# (25.40); the real vendor STEP is 26.386 long (see ref/bq25185-part.yaml) —
# CHG_L is not used to build geometry, only CHG_W/holes/JST offsets are.
# ---------------------------------------------------------------------------
CHG_W, CHG_L = 31.75, 25.40
CHG_PCB_T = 1.57
CHG_H = 6.37
CHG_HOLES = [(2.54, 2.54), (29.21, 2.54), (2.54, 22.86), (29.21, 22.86)]  # Ø2.50
CHG_JST_XC_LOCAL = [11.43, 20.32]      # side-entry housing centres, -y edge

BOSS_D = 5.50
CHG_BOSS_H = 3.40
BOSS_PILOT_D = 2.10
CHG_PILOT_DEPTH = 4.60                 # from the boss top; leaves a 1.20 floor

# ---------------------------------------------------------------------------
# Jack (panel-mount DC barrel, through the back cup's -Y skirt wall)
# ---------------------------------------------------------------------------
JACK_HOLE_D = 7.52
JACK_REACH = 13.00
JACK_NUT_D, JACK_NUT_T = 12.00, 2.50           # assumed
JACK_BODY_D = 10.00                            # assumed
JACK_FLANGE_D, JACK_FLANGE_T = 11.00, 2.00     # assumed
JACK_XC = CX
JACK_ZC = Z_SEAM + CUP_D / 2           # 25.15
JACK_Y_END = 0.0 + JACK_REACH          # 13.00, jack reaches y = 13.0

CHG_Y0 = JACK_Y_END + 8.00             # 21.00
CHG_Y1 = CHG_Y0 + CHG_L                # 46.40 (documentation; real bbox taller)
CHG_X0 = CX - CHG_W / 2                # 7.73
CHG_X1 = CHG_X0 + CHG_W                # 39.48

Z_CHG_BARE = Z_FLOOR - CHG_BOSS_H      # 28.50, PCB bare face on the boss tops
Z_CHG_COMPS = Z_CHG_BARE - CHG_H       # 22.13, components extend to here

PLUG_W, PLUG_H, PLUG_OUT = 5.90, 4.50, 6.00
# plug 1 (LOAD) and plug 2 (BATT) x-centres, mirrored (Rot 180 about Y) from
# the local JST housing offsets: CHG_X1 - 20.32 and CHG_X1 - 11.43
PLUG_XC = [CHG_X1 - 20.32, CHG_X1 - 11.43]     # [19.16, 28.05]

# ---------------------------------------------------------------------------
# LOAD slot (tube's -Y wall) and front-plate lip notch
# ---------------------------------------------------------------------------
LOAD_SLOT_W, LOAD_SLOT_H = 7.0, 6.0
LOAD_SLOT_ZC = 6.40

NOTCH_X_HALF = 4.5

# ---------------------------------------------------------------------------
# helpers (copied from cameras/openmv_n6/hardware/case/caselib.py style)
# ---------------------------------------------------------------------------
def _sk(w, l, r, z):
    """Rounded-rectangle sketch on a plane at height z, centred on the origin."""
    return Plane.XY.offset(z) * RectangleRounded(w, l, r)


def prism(x0, y0, x1, y1, r, z0, z1, cb=0.0, ct=0.0):
    """Rounded-rect prism spanning z0..z1, optional 45 deg chamfer each end."""
    w, l = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    zb, zt = z0 + cb, z1 - ct
    solid = Pos(cx, cy) * extrude(_sk(w, l, r, zb), amount=zt - zb)
    if cb:
        solid += Pos(cx, cy) * loft(
            [_sk(w - 2 * cb, l - 2 * cb, max(r - cb, 0.05), z0), _sk(w, l, r, zb)]
        )
    if ct:
        solid += Pos(cx, cy) * loft(
            [_sk(w, l, r, zt), _sk(w - 2 * ct, l - 2 * ct, max(r - ct, 0.05), z1)]
        )
    return solid


def flare_down(x0, y0, x1, y1, r, z0, c):
    """45 deg lead-in cone for a bore: c oversize at z0, nominal at z0 + c."""
    w, l = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return Pos(cx, cy) * loft(
        [_sk(w + 2 * c, l + 2 * c, r + c, z0), _sk(w, l, r, z0 + c)]
    )


def flare_up(x0, y0, x1, y1, r, z1, c):
    """Mirror of flare_down: c oversize at z1, nominal at z1 - c."""
    w, l = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return Pos(cx, cy) * loft(
        [_sk(w, l, r, z1 - c), _sk(w + 2 * c, l + 2 * c, r + c, z1)]
    )


def slot_y(xc, zc, w, h, y0, y1, r=None):
    """Rounded slot through a -Y/+Y wall, w along X, h along Z (stadium default)."""
    sk = RectangleRounded(w, h, min(w, h) / 2 - 0.001 if r is None else r)
    return Pos(xc, y0, zc) * Rot(-90, 0, 0) * extrude(sk, amount=y1 - y0)


def cyl_y(xc, zc, d, y0, y1):
    """Cylinder along +Y through a -Y/+Y wall, spanning y0..y1."""
    return Pos(xc, y0, zc) * Rot(-90, 0, 0) * extrude(Circle(d / 2), amount=y1 - y0)


def box_at(x0, y0, z0, dx, dy, dz):
    return Pos(x0, y0, z0) * Box(dx, dy, dz, align=(Align.MIN,) * 3)


def cyl_at(cx, cy, z0, d, h):
    return Pos(cx, cy, z0) * Cylinder(
        d / 2, h, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )


# ---------------------------------------------------------------------------
# parts
# ---------------------------------------------------------------------------
def tube():
    """Prints front-mouth down (Z_TUBE0 on the bed)."""
    part = prism(OUT_X0, OUT_Y0, OUT_X1, OUT_Y1, R_OUT, Z_TUBE0, Z_SEAM, cb=EFOOT)
    part -= prism(IN_X0, IN_Y0, IN_X1, IN_Y1, R_IN, Z_TUBE0 - 1.0, Z_SEAM + 1.0)
    part -= flare_down(IN_X0, IN_Y0, IN_X1, IN_Y1, R_IN, Z_TUBE0, LEADIN)
    part -= flare_up(IN_X0, IN_Y0, IN_X1, IN_Y1, R_IN, Z_SEAM, LEADIN)
    # r=1.5 (not a full stadium): a JST-PH plug is nearly square-cornered
    part -= slot_y(CX, LOAD_SLOT_ZC, LOAD_SLOT_W, LOAD_SLOT_H,
                   OUT_Y0 - 1.0, IN_Y0 + 1.0, r=1.5)
    part.label = "tube"
    return part


def front_plate():
    """Prints outer-face down (z = 0 on the bed).  Outer face is plain."""
    part = prism(OUT_X0, OUT_Y0, OUT_X1, OUT_Y1, R_OUT, Z_FRONT_OUT, Z_TUBE0,
                 cb=EFOOT)
    part += prism(LIP_X0, LIP_Y0, LIP_X1, LIP_Y1, R_LIP,
                  FRONT_LIP_Z0, FRONT_LIP_Z1, ct=LEADIN)
    part -= prism(BAY_X0, BAY_Y0, BAY_X1, BAY_Y1, R_BAY,
                  FRONT_LIP_Z0, FRONT_LIP_Z1 + 1.0)

    rib = fits.edge_crush_rib(LIP_RIB_H, length=6.0, proud=LIP_RIB_PROUD)
    for yc in (CY - 15.0, CY + 15.0):
        part += Pos(LIP_X0, yc, FRONT_LIP_Z0) * Rot(0, 0, 90) * rib
        part += Pos(LIP_X1, yc, FRONT_LIP_Z0) * Rot(0, 0, -90) * rib
    part += Pos(CX, LIP_Y1, FRONT_LIP_Z0) * rib
    for xc in (CX - 12.0, CX + 12.0):
        part += Pos(xc, LIP_Y0, FRONT_LIP_Z0) * Rot(0, 0, 180) * rib

    # JST-PH plug notch through the lip's -Y wall (not the outer plate)
    part -= box_at(CX - NOTCH_X_HALF, LIP_Y0 - 1.0, Z_TUBE0 - 1.0,
                   2 * NOTCH_X_HALF, (BAY_Y0 + 0.5) - (LIP_Y0 - 1.0),
                   (FRONT_LIP_Z1 + 1.0) - (Z_TUBE0 - 1.0))

    part.label = "front_plate"
    return part


def back_cup():
    """Prints back-face down (Z_BACK_OUT on the bed)."""
    part = prism(OUT_X0, OUT_Y0, OUT_X1, OUT_Y1, R_OUT, Z_SEAM, Z_BACK_OUT,
                 ct=EFOOT)
    part -= prism(IN_X0, IN_Y0, IN_X1, IN_Y1, R_IN, Z_SEAM - 1.0, Z_FLOOR)
    part += prism(LIP_X0, LIP_Y0, LIP_X1, LIP_Y1, R_LIP,
                  BACK_LIP_Z0, BACK_LIP_Z1, cb=LEADIN)
    part -= prism(BAY_X0, BAY_Y0, BAY_X1, BAY_Y1, R_BAY,
                  BACK_LIP_Z0 - 1.0, BACK_LIP_Z1)

    rib = fits.edge_crush_rib(LIP_RIB_H, length=6.0, proud=LIP_RIB_PROUD)
    rib_z = Z_SEAM - LIP_RIB_H             # 12.0
    for yc in (CY - 15.0, CY + 15.0):
        part += Pos(LIP_X0, yc, rib_z) * Rot(0, 0, 90) * rib
        part += Pos(LIP_X1, yc, rib_z) * Rot(0, 0, -90) * rib
    part += Pos(CX, LIP_Y0, rib_z) * Rot(0, 0, 180) * rib
    part += Pos(CX, LIP_Y1, rib_z) * rib

    for hx, hy in CHG_HOLES:                          # charger mounting bosses
        part += cyl_at(CHG_X0 + hx, CHG_Y0 + hy, Z_CHG_BARE, BOSS_D, CHG_BOSS_H)
    for hx, hy in CHG_HOLES:                          # blind thread-forming pilots
        part -= cyl_at(CHG_X0 + hx, CHG_Y0 + hy, Z_CHG_BARE - 1.0,
                       BOSS_PILOT_D, 1.0 + CHG_PILOT_DEPTH)

    part -= cyl_y(JACK_XC, JACK_ZC, JACK_HOLE_D, OUT_Y0 - 1.0, IN_Y0 + 1.0)

    part.label = "back_cup"
    return part


# ---------------------------------------------------------------------------
# mocks
# ---------------------------------------------------------------------------
def battery_mock():
    part = box_at(CX - 18.0, 8.0, Z_TUBE0, 36.0, 67.0, 11.0)
    part.label = "battery_11x36x67_mock"
    return part


def charger_plug_mocks():
    parts = []
    for i, xc in enumerate(PLUG_XC):
        p = box_at(xc - PLUG_W / 2, CHG_Y0 - PLUG_OUT, Z_CHG_COMPS + 0.2,
                   PLUG_W, PLUG_OUT, PLUG_H)
        p.label = f"charger_jst_plug_{i + 1}_mock"
        parts.append(p)
    return parts


def load_cable_mock():
    # A1: out of the plug, forward past the seam (stays above the jack in Y)
    part = box_at(16.0, 14.0, 13.9, 22.0 - 16.0, 21.0 - 14.0, 22.3 - 13.9)
    # A2: down toward the bottom wall, in the tube zone (z < seam), clear of the jack
    part += box_at(16.0, 5.0, 13.9, 22.0 - 16.0, 14.0 - 5.0, 18.0 - 13.9)
    part += box_at(19.5, 4.65, 4.0, 24.0 - 19.5, 7.5 - 4.65, 18.0 - 4.0)         # B
    # D + C: the JST-PH plug itself (5.9 x 4.5) dropping to the wall and out
    # through the slot, centred on the slot
    part += box_at(CX - PLUG_W / 2, 2.9, LOAD_SLOT_ZC - PLUG_H / 2, PLUG_W, 7.5 - 2.9, PLUG_H)   # D
    part += box_at(CX - PLUG_W / 2, -5.0, LOAD_SLOT_ZC - PLUG_H / 2, PLUG_W, 3.0 - (-5.0), PLUG_H)  # C
    part.label = "load_cable_mock"
    return part


def batt_cable_mock():
    part = box_at(26.0, 14.0, 13.9, 30.0 - 26.0, 21.0 - 14.0, 22.3 - 13.9)
    part += box_at(26.0, 8.5, 13.9, 30.0 - 26.0, 14.0 - 8.5, 18.0 - 13.9)
    part.label = "batt_cable_mock"
    return part


def jack_mock():
    """flange y -2..0 Ø11; bushing y 0..2.40 Ø7.40; nut y 2.40..4.90 Ø12;
    body y 4.90..13.0 Ø10."""
    part = cyl_y(JACK_XC, JACK_ZC, JACK_FLANGE_D, -2.0, 0.0)
    part += cyl_y(JACK_XC, JACK_ZC, JACK_HOLE_D - 0.12, 0.0, 2.40)
    part += cyl_y(JACK_XC, JACK_ZC, JACK_NUT_D, 2.40, 4.90)
    part += cyl_y(JACK_XC, JACK_ZC, JACK_BODY_D, 4.90, JACK_Y_END)
    part.label = "dc_jack_mock"
    return part


_HERE = __import__("pathlib").Path(__file__).resolve().parent
_CHG_STEP = _HERE / "ref" / "adafruit-6091-adafruit-bq25185-usb-dc-solar-lithium-ion-poly.step"


@__import__("functools").lru_cache(maxsize=None)
def _charger_step():
    return import_step(str(_CHG_STEP))


def charger_mock():
    """Adafruit 6091 bq25185, vendor STEP, bare side against Z_CHG_BARE,
    components toward -Z, JST edge toward -Y.  Rot 180 about Y is a proper
    rotation (x mirrored, z flipped).

    NOTE: the vendor STEP is a 56-solid Compound.  In this build123d,
    Shape.intersect() against a Compound ignores any Location applied via
    Pos()/Rot()/.moved() *after* the Compound was built (bounding_box() and
    center() correctly reflect the transform; intersect() silently uses the
    untransformed geometry instead — verified directly against a minimal
    two-box Compound).  The fix is to bake the transform into each solid
    individually before compounding, which behaves correctly.
    """
    loc = Pos(CHG_X1, CHG_Y0, Z_CHG_BARE) * Rot(0, 180, 0)
    solids = [loc * s for s in _charger_step().solids()]
    part = Compound(children=solids)
    part.label = "charger_bq25185"
    return part
