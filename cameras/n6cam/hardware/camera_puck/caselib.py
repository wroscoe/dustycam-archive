"""OpenMV Cam N6 camera puck — camera-only enclosure, 4-part printed
enclosure (geometry library).

v1 (2026-09-12): the N6 case rev D architecture (front_cup / cam_plate /
back cup) with the power puck's 80.80 face height, a plain friction-fit
BACK PLATE instead of rev D's back cup (no battery bay — the coupling plate
that will replace it is future work), a LOAD-lead slot through the front
cup's bottom wall for the JST-PH power lead coming from the puck, and the
puck's press-in USB cap (deeper here: the port passes through the outer
wall + the internal shoulder, WALL + SHOULDER = 3.60).  No charger, no jack,
no battery — this puck only frames and cools the camera.

Four printed parts:

  front_cup   outer shell over the lens/component side of the N6.  Straight
              bore for the board, an internal shoulder that the cam plate
              bears against, then a deeper socket that receives the back
              plate's lip.  Lens barrel stands proud through the face.
              LOAD-lead slot and two vents through its bottom (-Y) wall.
  cam_plate   flat plate the N6 bolts to with 2 x M2.5 through its Ø2.80
              mounting holes.  Sandwiched between the front cup shoulder
              and the back plate lip.  No battery, no charger: no notch,
              no pilots, no wire slot.
  back_plate  lip plugs into the front cup socket (0.15/side + crush ribs),
              pushes the plate up against the shoulder.  Back face is
              plain — a future coupling plate replaces this part.
  usb_cap     press-in plug for the USB-C port, puck recipe, deeper plug
              (3.60) for this enclosure's wall + shoulder stack-up.

Coordinate frame — identical to ref/openmv-n6.py and ../case/caselib.py:
  origin at the N6 PCB bottom-left corner, on the PCB *bottom* face.
  +X 35.56 board width, +Y toward the lens end, +Z optical axis toward the
  lens.  The camera's bottom is the -Y wall.  (Mapping to the power puck's
  own frame, for the README only: x' = x + 4.302, y' = y + 13.60,
  z' = 25.90 - z.)

Fit values come from the project-local fits.py (copy of ../case/fits.py).
"""

import itertools

from build123d import *  # noqa: F403

import fits

# ---------------------------------------------------------------------------
# N6 board envelope (measured — see ref/DIMENSIONS.md)
# ---------------------------------------------------------------------------
BOARD_X0, BOARD_X1 = -0.102, 35.712   # incl. camera daughter-board arm overhang
BOARD_Y0, BOARD_Y1 = 0.000, 45.080    # incl. side-actuated button overhang
Z_TAIL = -3.000                       # header tails below the PCB (assumed 3.0)
Z_LOCKRING_TOP = 22.850               # M12 lock-ring top, above PCB bottom
Z_LENS_TIP = 31.250
LENS_AXIS = (17.810, 36.255)
LENS_BARREL_D = 14.000
MOUNT_HOLES = [(3.048, 41.402), (32.512, 41.402)]   # Ø2.80, 29.464 apart

# ---------------------------------------------------------------------------
# Fits and print rules (mywarehouse tolerances.md / printing.md)
# ---------------------------------------------------------------------------
WALL = 2.40                 # enclosure structure wall = 6 perimeters
LIP_WALL = 1.60
LIP_GAP = fits.LIP_GAP      # 0.15/side, press-fit lip into mouth
LIP_RIB_PROUD = fits.LIP_RIB_PROUD   # 0.25 crush ribs -> 0.10/side net
PLATE_GAP = fits.PLATE_SLIDE_GAP     # 0.20/side, plate in socket
EFOOT = fits.ELEPHANT_FOOT  # 0.40 x 45 deg on bed-contact perimeters
LEADIN = 0.60               # 45 deg lead-in on friction entries
LIP_ENG = 7.50              # puck recipe: lip engagement depth
LIP_RIB_H = 6.40            # rib height (rev E recipe: fixed, not derived)

BOARD_CLR = 0.60            # board -> front cup bore, per side
CARD_CH = 3.60              # +X bore side runs this wide instead (microSD card
                            # channel — see the note above SD_YC below)
SHOULDER = 1.20             # ledge width the cam plate bears on
WIRE_CH = 10.00             # lead channel at the USB/LOAD (-Y) end

# ---------------------------------------------------------------------------
# Z stack (all relative to the PCB bottom face)
# ---------------------------------------------------------------------------
Z_CEIL = Z_LOCKRING_TOP + 0.65               # 23.50, front cup inner ceiling
Z_FRONT_OUT = Z_CEIL + WALL                  # 25.90, case front face
Z_SHOULDER = -3.50                           # cam plate front face
PLATE_T = 3.00                               # rev D thickness (no charger pilots)
Z_PLATE_BOT = Z_SHOULDER - PLATE_T           # -6.50, back plate lip nose pushes here
Z_SEAM = Z_PLATE_BOT - LIP_ENG               # -14.00, front cup rim / back plate inner face
Z_BACK_OUT = Z_SEAM - WALL                   # -16.40, case back face

# Rev B (../case): +2.00 not +1.00 — print 1 of the RT1062 case (same M12
# lens family) bound on the knurled focus ring, ~Ø15.5 actual vs Ø14.0 in
# OpenMV's GLB.  Ø16.00 clears the knurl 0.25/side and still keeps the
# Ø16.20 lock ring captive.
LENS_HOLE_D = LENS_BARREL_D + 2.00          # 16.00, barrel stands proud

# ---------------------------------------------------------------------------
# XY rectangles, built outward from the board envelope — X exactly as
# ../case (unchanged board); Y re-derived for the puck's 80.80 face height.
# ---------------------------------------------------------------------------
CAV_X0, CAV_X1 = BOARD_X0 - BOARD_CLR, BOARD_X1 + CARD_CH        # -0.702, 39.312
SOCK_X0, SOCK_X1 = CAV_X0 - SHOULDER, CAV_X1 + SHOULDER          # -1.902, 40.512
OUT_X0, OUT_X1 = SOCK_X0 - WALL, SOCK_X1 + WALL                  # -4.302, 42.912

OUT_H = 80.80                              # matches the power puck face
CAV_Y0 = BOARD_Y0 - WIRE_CH                # -10.00
SOCK_Y0 = CAV_Y0 - SHOULDER                # -11.20
OUT_Y0 = SOCK_Y0 - WALL                    # -13.60
OUT_Y1 = OUT_Y0 + OUT_H                    # 67.20
SOCK_Y1 = OUT_Y1 - WALL                    # 64.80
CAV_Y1 = SOCK_Y1 - SHOULDER                # 63.60
TOP_CH = CAV_Y1 - BOARD_Y1                 # 18.52 headroom above the board (derived)

PLATE_X0, PLATE_X1 = SOCK_X0 + PLATE_GAP, SOCK_X1 - PLATE_GAP
PLATE_Y0, PLATE_Y1 = SOCK_Y0 + PLATE_GAP, SOCK_Y1 - PLATE_GAP

LIP_X0, LIP_X1 = SOCK_X0 + LIP_GAP, SOCK_X1 - LIP_GAP
LIP_Y0, LIP_Y1 = SOCK_Y0 + LIP_GAP, SOCK_Y1 - LIP_GAP

BAY_X0, BAY_X1 = LIP_X0 + LIP_WALL, LIP_X1 - LIP_WALL
BAY_Y0, BAY_Y1 = LIP_Y0 + LIP_WALL, LIP_Y1 - LIP_WALL

R_OUT = 6.00
R_SOCK = R_OUT - WALL                # 3.60
R_CAV = 1.20
R_LIP = R_SOCK - LIP_GAP             # 3.45
R_BAY = R_LIP - LIP_WALL             # 1.85
R_PLATE = R_SOCK + 0.40              # 4.00 > socket radius: corners never bind

CX = (OUT_X0 + OUT_X1) / 2           # 19.305
CY = (OUT_Y0 + OUT_Y1) / 2           # 26.80

# ---------------------------------------------------------------------------
# M2.5 board screws into thread-forming bosses
# ---------------------------------------------------------------------------
BOSS_D = 5.50
BOSS_PILOT_D = 2.10
BOSS_PILOT_DEPTH = 5.30              # 1.20 floor, 4.70 engagement for M2.5 x 6

PAD = [(5.4, 0.5, 7.4, 3.0), (28.7, 0.5, 30.7, 3.0)]   # anti-bow pads, USB end
PAD_TOP_Z = -0.30                    # 0.3 below the PCB: catches bow, no preload

# ---------------------------------------------------------------------------
# microSD card channel — see ../case/caselib.py for the derivation; unchanged
# (same board, same +X cavity side).
# ---------------------------------------------------------------------------
SD_YC = 27.125                       # card centreline (socket centre), for mock

# ---------------------------------------------------------------------------
# USB-C port — through the -Y wall.  Receptacle x 18.88..28.46, z 0.45..4.61;
# opening passes a plug overmold up to 15.0 x 9.5.
# ---------------------------------------------------------------------------
USB_XC, USB_ZC = 23.67, 2.53
USB_W, USB_H = 15.00, 9.50

# ---------------------------------------------------------------------------
# LOAD-lead slot through the -Y wall, directly under the N6's side-entry
# LiPo JST-PH (housing x 7.00..13.00, z 1.30..6.26, mouth at the -Y board
# edge).  The lead comes from the power puck behind the camera.
# ---------------------------------------------------------------------------
LOAD_XC, LOAD_ZC = 10.00, 3.78
LOAD_W, LOAD_H = 7.0, 6.0

# ---------------------------------------------------------------------------
# Vents — bottom (-Y) wall of the front cup, moved clear of the LOAD slot
# and the USB port.
# ---------------------------------------------------------------------------
VENT_W, VENT_H = 2.40, 12.00
VENT_ZC = 8.00
VENT_XC = [2.9, 35.5]

# ---------------------------------------------------------------------------
# Opening non-overlap contract: the vents, the LOAD slot and the USB port
# all cut the same -Y wall.  Assert none of their X x Z footprints overlap.
# ---------------------------------------------------------------------------
def _rect(xc, zc, w, h):
    return (xc - w / 2, xc + w / 2, zc - h / 2, zc + h / 2)


def opening_gap(a, b):
    """Signed clearance between two (x0,x1,z0,z1) rects in the wall plane.
    >= 0 means separated on at least one axis (no overlap); < 0 overlaps."""
    ax0, ax1, az0, az1 = a
    bx0, bx1, bz0, bz1 = b
    gap_x = max(ax0 - bx1, bx0 - ax1)
    gap_z = max(az0 - bz1, bz0 - az1)
    return max(gap_x, gap_z)


OPENING_RECTS = {
    "usb_port": _rect(USB_XC, USB_ZC, USB_W, USB_H),
    "load_slot": _rect(LOAD_XC, LOAD_ZC, LOAD_W, LOAD_H),
    "vent_0": _rect(VENT_XC[0], VENT_ZC, VENT_W, VENT_H),
    "vent_1": _rect(VENT_XC[1], VENT_ZC, VENT_W, VENT_H),
}
for _na, _nb in itertools.combinations(OPENING_RECTS, 2):
    assert opening_gap(OPENING_RECTS[_na], OPENING_RECTS[_nb]) >= 0, (
        f"{_na} overlaps {_nb} in the -Y wall plane"
    )

# ---------------------------------------------------------------------------
# USB cap — same geometry as hardware/power_puck/caselib.py usb_cap(), but
# the plug is the full wall + shoulder deep here (the port passes through
# both the outer wall and the internal shoulder region: CAV_Y0 - OUT_Y0 =
# WALL + SHOULDER = 3.60, not just WALL as in the power puck).
# ---------------------------------------------------------------------------
CAP_GAP = LIP_GAP                       # 0.15
CAP_W, CAP_H = USB_W - 2 * CAP_GAP, USB_H - 2 * CAP_GAP    # 14.70 x 9.20
CAP_R = 2.5 - CAP_GAP                   # 2.35
CAP_DEPTH = WALL + SHOULDER             # 3.60
CAP_LEADIN = 0.40
CAP_RIB_H = CAP_DEPTH - CAP_LEADIN      # 3.20
CAP_HEAD_W, CAP_HEAD_H, CAP_HEAD_T, CAP_HEAD_R = 18.0, 12.5, 1.50, 3.5


# ---------------------------------------------------------------------------
# helpers (../case/caselib.py style)
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


def slot_y(xc, zc, w, h, y0, y1, r=None):
    """Rounded slot through a -Y/+Y wall, w along X, h along Z (stadium default)."""
    sk = RectangleRounded(w, h, min(w, h) / 2 - 0.001 if r is None else r)
    return Pos(xc, y0, zc) * Rot(-90, 0, 0) * extrude(sk, amount=y1 - y0)


def slot_x(yc, zc, w, h, x0, x1):
    """Stadium slot through a -X/+X wall, w along Y, h along Z."""
    sk = RectangleRounded(h, w, min(w, h) / 2 - 0.001)
    return Pos(x0, yc, zc) * Rot(0, 90, 0) * extrude(sk, amount=x1 - x0)


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
def front_cup():
    """Prints face-down (Z_FRONT_OUT on the bed).  No supports."""
    part = prism(OUT_X0, OUT_Y0, OUT_X1, OUT_Y1, R_OUT, Z_SEAM, Z_FRONT_OUT,
                 ct=EFOOT)

    # board cavity, then the deeper socket; the step between them is the
    # 1.20 shoulder the cam plate is clamped against
    part -= prism(CAV_X0, CAV_Y0, CAV_X1, CAV_Y1, R_CAV, Z_SHOULDER, Z_CEIL)
    part -= prism(SOCK_X0, SOCK_Y0, SOCK_X1, SOCK_Y1, R_SOCK,
                  Z_SEAM - 1.0, Z_SHOULDER)
    part -= flare_down(SOCK_X0, SOCK_Y0, SOCK_X1, SOCK_Y1, R_SOCK,
                       Z_SEAM, LEADIN)

    # lens aperture: barrel stands proud, lock ring stays captive inside
    part -= cyl_at(*LENS_AXIS, Z_CEIL - 1.0, LENS_HOLE_D, WALL + 2.0)
    part -= Pos(*LENS_AXIS, Z_FRONT_OUT - EFOOT) * Cone(
        bottom_radius=LENS_HOLE_D / 2,
        top_radius=LENS_HOLE_D / 2 + EFOOT,
        height=EFOOT,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )

    for xc in VENT_XC:
        part -= slot_y(xc, VENT_ZC, VENT_W, VENT_H, OUT_Y0 - 1.0, CAV_Y0 + 1.0)

    # USB-C port through the -Y wall (r=2.5 keeps the corners open for a
    # square-shouldered plug overmold)
    part -= slot_y(USB_XC, USB_ZC, USB_W, USB_H, OUT_Y0 - 1.0, CAV_Y0 + 1.0,
                   r=2.5)

    # LOAD-lead slot through the -Y wall, under the N6's LiPo JST-PH
    part -= slot_y(LOAD_XC, LOAD_ZC, LOAD_W, LOAD_H, OUT_Y0 - 1.0, CAV_Y0 + 1.0,
                   r=1.5)

    part.label = "front_cup"
    return part


def cam_plate():
    """Prints flat, bosses up (Z_PLATE_BOT on the bed).  No supports.  No
    battery/charger here, so no notch, no pilots, no wire slot."""
    part = prism(PLATE_X0, PLATE_Y0, PLATE_X1, PLATE_Y1, R_PLATE,
                 Z_PLATE_BOT, Z_SHOULDER, cb=EFOOT)

    for cx, cy in MOUNT_HOLES:                      # M2.5 bosses up to the PCB
        part += cyl_at(cx, cy, Z_SHOULDER, BOSS_D, -Z_SHOULDER)
    for x0, y0, x1, y1 in PAD:                      # anti-bow pads at the USB end
        part += box_at(x0, y0, Z_SHOULDER, x1 - x0, y1 - y0,
                       PAD_TOP_Z - Z_SHOULDER)
    for cx, cy in MOUNT_HOLES:
        part -= cyl_at(cx, cy, -BOSS_PILOT_DEPTH, BOSS_PILOT_D,
                       BOSS_PILOT_DEPTH + 1.0)

    part.label = "cam_plate"
    return part


def back_plate():
    """Prints back-face-down (Z_BACK_OUT on the bed).  No supports.

    Plain friction-fit plate: the puck's front_plate recipe, but its lip
    goes into the front cup's SOCKET instead of a tube mouth.  Must be ONE
    solid — the lip roots into the 2.4 plate over its full 1.6 wall (the
    prism()+prism() union, not a separate ledge, keeps this a single body).
    Back face is plain; a future coupling plate replaces this part.
    """
    part = prism(OUT_X0, OUT_Y0, OUT_X1, OUT_Y1, R_OUT, Z_BACK_OUT, Z_SEAM,
                 cb=EFOOT)
    part += prism(LIP_X0, LIP_Y0, LIP_X1, LIP_Y1, R_LIP, Z_SEAM, Z_PLATE_BOT,
                  ct=LEADIN)
    part -= prism(BAY_X0, BAY_Y0, BAY_X1, BAY_Y1, R_BAY, Z_SEAM,
                  Z_PLATE_BOT + 1.0)

    # crush ribs carry the interference; bulk lip surfaces keep 0.15 clearance.
    # Ribs run +Z from the plate toward the nose, rotations as ../case
    # back_cup() uses them; positions per spec: X-wall ribs at yc = CY +/-
    # 20, Y-wall ribs at x = CX (6 ribs total).
    rib = fits.edge_crush_rib(LIP_RIB_H, length=6.0, proud=LIP_RIB_PROUD)
    for yc in (CY - 20.0, CY + 20.0):
        part += Pos(LIP_X0, yc, Z_SEAM) * Rot(0, 0, 90) * rib
        part += Pos(LIP_X1, yc, Z_SEAM) * Rot(0, 0, -90) * rib
    part += Pos(CX, LIP_Y0, Z_SEAM) * Rot(0, 0, 180) * rib
    part += Pos(CX, LIP_Y1, Z_SEAM) * rib

    part.label = "back_plate"
    return part


def usb_cap():
    """Same geometry as hardware/power_puck/caselib.py usb_cap(), but the
    plug is WALL + SHOULDER (3.60) deep instead of WALL (2.40) — the port
    here passes through the outer wall and the internal shoulder region.
    Built along local +Z (plug, into the wall) with the head at local -Z
    (outside), then rotated so local +Z -> +Y: plug in the wall
    y OUT_Y0..CAV_Y0 (-13.60..-10.00), head outside y OUT_Y0-CAP_HEAD_T..
    OUT_Y0 (-15.10..-13.60).  Prints head-down (outer face on the bed).  No
    supports."""
    plug = prism(-CAP_W / 2, -CAP_H / 2, CAP_W / 2, CAP_H / 2, CAP_R,
                 0.0, CAP_DEPTH, ct=CAP_LEADIN)
    head = prism(-CAP_HEAD_W / 2, -CAP_HEAD_H / 2, CAP_HEAD_W / 2, CAP_HEAD_H / 2,
                 CAP_HEAD_R, -CAP_HEAD_T, 0.0, cb=EFOOT)
    part = plug + head
    rib = fits.edge_crush_rib(CAP_RIB_H, length=6.0, proud=LIP_RIB_PROUD)
    part += Pos(0, CAP_H / 2, 0) * rib
    part += Pos(0, -CAP_H / 2, 0) * Rot(0, 0, 180) * rib
    part = Pos(USB_XC, OUT_Y0, USB_ZC) * Rot(-90, 0, 0) * part
    part.label = "usb_cap"
    return part


# ---------------------------------------------------------------------------
# mocks (reference occurrences, labelled)
# ---------------------------------------------------------------------------
def sd_card_mock():
    """microSD seated in the socket: 11 x 15 x 1.0, tail proud of the PCB edge."""
    part = box_at(38.62 - 15.0, SD_YC - 5.5, -1.36, 15.0, 11.0, 1.0)
    part.label = "microsd_card_mock"
    return part


def usb_plug_mock():
    """Seated USB-C plug: shell at the receptacle mouth + 12 x 7 overmold
    running out through the port.  Reference for clearance checks only."""
    part = box_at(USB_XC - 4.47, -1.0, USB_ZC - 1.6, 8.94, 7.5, 3.2)
    part += box_at(USB_XC - 6.0, OUT_Y0 - 12.0, USB_ZC - 3.5,
                   12.0, (-1.5) - (OUT_Y0 - 12.0), 7.0)
    part.label = "usb_plug_mock"
    return part


def load_jst_plug_mock():
    """JST-PH plug seated in the N6's LiPo connector, only the part standing
    proud in front of the board edge (the connector body itself is the N6
    model's lipo_battery_connector solid, y >= 0.20)."""
    part = box_at(7.05, -6.0, 1.53, 12.95 - 7.05, 0.0 - (-6.0), 6.03 - 1.53)
    part.label = "load_jst_plug_mock"
    return part


def load_cable_mock():
    """LOAD lead: 3 x 3 box from the front cup's LOAD slot (outside) to just
    short of the plug, overlapping it by 1.0 (declared MATED)."""
    y0, y1 = OUT_Y0 - 15.0, -5.0
    part = box_at(8.5, y0, 2.28, 11.5 - 8.5, y1 - y0, 5.28 - 2.28)
    part.label = "load_cable_mock"
    return part
