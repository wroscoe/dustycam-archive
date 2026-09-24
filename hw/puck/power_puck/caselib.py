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
CUP_D = 18.00                          # v2: skirt interior depth (was 13.50)
Z_FLOOR = Z_SEAM + CUP_D               # 36.40 floor top, inside
Z_BACK_OUT = Z_FLOOR + WALL            # 38.80

FRONT_LIP_Z0, FRONT_LIP_Z1 = Z_TUBE0, Z_TUBE0 + LIP_ENG    # 2.40, 9.90
BACK_LIP_Z0, BACK_LIP_Z1 = Z_SEAM - LIP_ENG, Z_SEAM         # 10.90, 18.40
# 1.00 gap between the two lip noses: BACK_LIP_Z0 - FRONT_LIP_Z1 == 1.00

# v2: solid seam ring under the lip.  The lip (LIP rect) only ever touched
# the skirt (IN rect) along a knife edge because LIP is inset 0.15 from IN;
# the ring keeps the BAY-radius bore for LEDGE_T beyond the seam, then
# chamfers out (45 deg, since BAY is IN inset by exactly LIP_WALL+LIP_GAP)
# to the full IN-radius interior for the rest of the cup depth.
LEDGE_T = 1.60
LEDGE_CHAMFER = LIP_WALL + LIP_GAP     # 1.75
LEDGE_Z0 = Z_SEAM + LEDGE_T            # 20.00  ledge bore ends / chamfer starts
CHAMFER_TOP = LEDGE_Z0 + LEDGE_CHAMFER  # 21.75  chamfer ends / IN-radius bore starts

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
# Jack (panel-mount DC barrel, through the back cup's -Y skirt wall).  v2:
# JACK_ZC moves to the middle of the window between the chamfer top and the
# floor (the charger moved up to the top of the cup, so the jack no longer
# has to share the old, shallower window with it).
# ---------------------------------------------------------------------------
JACK_HOLE_D = 7.52
JACK_REACH = 13.00
JACK_NUT_D, JACK_NUT_T = 12.00, 2.50           # assumed
JACK_BODY_D = 10.00                            # assumed
JACK_FLANGE_D, JACK_FLANGE_T = 11.00, 2.00     # assumed
JACK_XC = CX
JACK_ZC = (CHAMFER_TOP + Z_FLOOR) / 2   # 29.075
JACK_Y_END = 0.0 + JACK_REACH          # 13.00, jack reaches y = 13.0

# v2: charger moves up to the top of the cup, USB-C edge toward +Y (JST edge
# stays toward -Y).
CHG_Y1 = IN_Y1 - 2.0                   # 76.40
CHG_Y0 = CHG_Y1 - CHG_L                # 51.00 (documentation; real bbox taller)
CHG_X0 = CX - CHG_W / 2                # 7.73
CHG_X1 = CHG_X0 + CHG_W                # 39.48

Z_CHG_BARE = Z_FLOOR - CHG_BOSS_H      # 33.00, PCB bare face on the boss tops
Z_CHG_COMPS = Z_CHG_BARE - CHG_H       # 26.63, components extend to here

PLUG_W, PLUG_H, PLUG_OUT = 5.90, 4.50, 6.00
# plug 1 (LOAD) and plug 2 (BATT) x-centres, mirrored (Rot 180 about Y) from
# the local JST housing offsets: CHG_X1 - 20.32 and CHG_X1 - 11.43
PLUG_XC = [CHG_X1 - 20.32, CHG_X1 - 11.43]     # [19.16, 28.05]

# USB-C port, through the back cup's +Y skirt wall, under the charger's
# USB-C shell (vendor model local x 11.4..20.34, local z 0.57..4.77 from the
# PCB bottom).
USB_W, USB_H = 15.0, 9.5
USB_Z0 = Z_CHG_BARE - 4.77             # 28.23
USB_Z1 = Z_CHG_BARE - 0.57             # 32.43
USB_ZC = (USB_Z0 + USB_Z1) / 2         # 30.33
USB_SHELL_Y = CHG_Y1 + 1.0             # 77.40, 1.0 inside IN_Y1 (78.40)

# v2: printed cap for the USB-C port.  Plug 0.15/side inside the opening
# with two crush ribs (0.10/side net, same recipe as the lips), 2.40 deep so
# it stops flush with the inner wall face — 1.0 short of the USB-C shell.
# Head sits on the outer face; prints head-down.
CAP_GAP = LIP_GAP                       # 0.15
CAP_W, CAP_H = USB_W - 2 * CAP_GAP, USB_H - 2 * CAP_GAP    # 14.70 x 9.20
CAP_R = 2.5 - CAP_GAP                   # 2.35
CAP_DEPTH = WALL                        # 2.40, flush with the inner face
CAP_LEADIN = 0.40
CAP_RIB_H = CAP_DEPTH - CAP_LEADIN      # 2.00
CAP_HEAD_W, CAP_HEAD_H, CAP_HEAD_T, CAP_HEAD_R = USB_W + 3.0, USB_H + 3.0, 1.50, 3.5

# ---------------------------------------------------------------------------
# LOAD slot: v2 moves it from the tube to the back cup's -Y skirt wall,
# beside the jack (was in the tube's -Y wall in v1).
# ---------------------------------------------------------------------------
LOAD_SLOT_XC = CX - 12.0
LOAD_SLOT_W, LOAD_SLOT_H = 7.0, 6.0

# ---------------------------------------------------------------------------
# helpers (copied from cameras/n6cam/hardware/case/caselib.py style)
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


def chamfer_widen(x0, y0, x1, y1, r, z0, c):
    """45 deg widening chamfer (v2 ledge->bore transition): c undersize
    (inset) at z0, nominal (x0,y0,x1,y1,r) at z0 + c."""
    w, l = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return Pos(cx, cy) * loft(
        [_sk(w - 2 * c, l - 2 * c, max(r - c, 0.05), z0), _sk(w, l, r, z0 + c)]
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
    """Prints front-mouth down (Z_TUBE0 on the bed).  v2: no LOAD slot (moved
    to the back cup's -Y skirt wall)."""
    part = prism(OUT_X0, OUT_Y0, OUT_X1, OUT_Y1, R_OUT, Z_TUBE0, Z_SEAM, cb=EFOOT)
    part -= prism(IN_X0, IN_Y0, IN_X1, IN_Y1, R_IN, Z_TUBE0 - 1.0, Z_SEAM + 1.0)
    part -= flare_down(IN_X0, IN_Y0, IN_X1, IN_Y1, R_IN, Z_TUBE0, LEADIN)
    part -= flare_up(IN_X0, IN_Y0, IN_X1, IN_Y1, R_IN, Z_SEAM, LEADIN)
    part.label = "tube"
    return part


def front_plate():
    """Prints outer-face down (z = 0 on the bed).  Outer face is plain.
    v2: no lip notch (the JST plug exit moved to the back cup), 6 ribs
    (single -Y rib at CX), matching back_cup's rib layout."""
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
    part += Pos(CX, LIP_Y0, FRONT_LIP_Z0) * Rot(0, 0, 180) * rib

    part.label = "front_plate"
    return part


def back_cup():
    """Prints back-face down (Z_BACK_OUT on the bed).

    v2: the lip (LIP rect) only ever line-touched the skirt (IN rect), since
    LIP is inset 0.15 from IN.  Now the interior stays at BAY radius for
    LEDGE_T past the seam (a solid ring, OUT-to-BAY, under the full lip
    wall), then a 45 deg chamfer (BAY is exactly IN inset by LIP_WALL +
    LIP_GAP, so the chamfer is a true 45) widens it out to the full
    IN-radius bore for the rest of the depth to the floor.  Order: shell -
    void, THEN + lip - bay-bore, so the lip's wall roots fully into the
    solid ring instead of butting a knife edge.
    """
    part = prism(OUT_X0, OUT_Y0, OUT_X1, OUT_Y1, R_OUT, Z_SEAM, Z_BACK_OUT,
                 ct=EFOOT)

    void = prism(BAY_X0, BAY_Y0, BAY_X1, BAY_Y1, R_BAY, Z_SEAM - 1.0, LEDGE_Z0)
    void += chamfer_widen(IN_X0, IN_Y0, IN_X1, IN_Y1, R_IN, LEDGE_Z0, LEDGE_CHAMFER)
    void += prism(IN_X0, IN_Y0, IN_X1, IN_Y1, R_IN, CHAMFER_TOP, Z_FLOOR)
    part -= void

    part += prism(LIP_X0, LIP_Y0, LIP_X1, LIP_Y1, R_LIP,
                  BACK_LIP_Z0, BACK_LIP_Z1, cb=LEADIN)
    part -= prism(BAY_X0, BAY_Y0, BAY_X1, BAY_Y1, R_BAY,
                  BACK_LIP_Z0 - 1.0, BACK_LIP_Z1 + 0.01)

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

    # v2: LOAD slot, beside the jack in the same -Y skirt wall
    part -= slot_y(LOAD_SLOT_XC, JACK_ZC, LOAD_SLOT_W, LOAD_SLOT_H,
                   OUT_Y0 - 1.0, IN_Y0 + 1.0, r=1.5)

    # v2: USB-C port through the +Y skirt wall, under the charger's shell
    part -= slot_y(CX, USB_ZC, USB_W, USB_H, IN_Y1 - 1.0, OUT_Y1 + 1.0, r=2.5)

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
    """v2: moves WITH the cup (it now exits through the back cup's own -Y
    wall, beside the jack, instead of the tube).  Down the inside of the
    bottom-left of the cup, from plug 1 to the LOAD slot (routing box, x
    9..15 literal), then the plug shape (PLUG_W x PLUG_H) through the slot,
    centred on the slot (LOAD_SLOT_XC, not the routing box's rough x9..15 —
    a literal x9..15 there is centred at x=12.0, 0.395 off the slot's true
    centre at LOAD_SLOT_XC=11.605, and clips two corners of the slot's r=1.5
    rounding by ~0.043 mm^3 total; centring on the slot instead, as the spec
    explicitly says for this box, makes it fit with margin)."""
    part = box_at(9.0, 3.0, 26.1, 15.0 - 9.0, 47.0 - 3.0, 32.1 - 26.1)
    part += box_at(LOAD_SLOT_XC - PLUG_W / 2, -5.0, JACK_ZC - PLUG_H / 2,
                   PLUG_W, 3.0 - (-5.0), PLUG_H)
    part.label = "load_cable_mock"
    return part


def batt_cable_mock():
    """v2: static, attached to the battery — from the battery zone back
    toward plug 2 (the charger moved up to the top of the cup)."""
    part = box_at(26.0, 40.0, 13.9, 30.0 - 26.0, 47.0 - 40.0, 27.0 - 13.9)
    part.label = "batt_cable_mock"
    return part


def usb_cap():
    """v2: press-in cap for the USB-C port.  Built along local +Z (plug) with
    the head at local -Z, then rotated so local +Z -> puck -Y: head outside
    the +Y wall, plug in the opening, nose flush with the inner face.
    Prints head-down (outer face on the bed).  No supports."""
    plug = prism(-CAP_W / 2, -CAP_H / 2, CAP_W / 2, CAP_H / 2, CAP_R,
                 0.0, CAP_DEPTH, ct=CAP_LEADIN)
    head = prism(-CAP_HEAD_W / 2, -CAP_HEAD_H / 2, CAP_HEAD_W / 2, CAP_HEAD_H / 2,
                 CAP_HEAD_R, -CAP_HEAD_T, 0.0, cb=EFOOT)
    part = plug + head
    rib = fits.edge_crush_rib(CAP_RIB_H, length=6.0, proud=LIP_RIB_PROUD)
    part += Pos(0, CAP_H / 2, 0) * rib                      # local +Y face
    part += Pos(0, -CAP_H / 2, 0) * Rot(0, 0, 180) * rib    # local -Y face
    part = Pos(CX, OUT_Y1, USB_ZC) * Rot(90, 0, 0) * part
    part.label = "usb_cap"
    return part


def usb_plug_mock():
    """v2: USB-C plug overmold at the charger's +Y edge, through the back
    cup's +Y skirt wall.  Static reference; excluded from the sweep."""
    part = box_at(CX - 6.0, USB_SHELL_Y, USB_ZC - 3.5, 12.0, 95.0 - USB_SHELL_Y, 7.0)
    part.label = "usb_plug_mock"
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
