"""N20 worm-drive pan head, v8.

World datum: the stationary base is centred at XY=0 and sits on Z=0.  +Z is
up, +X is the camera look direction at pan=0, and positive pan is CCW viewed
from above.  The motor shaft/worm axis is +X.  This file intentionally keeps
all purchased hardware as labeled clearance/envelope occurrences; every
structural and drive component returned by the print generators is printed.

The worm is a single-start, right-hand (+) trapezoidal helical prototype.  The
24T wheel currently uses radial trapezoidal tooth gaps rather than a fully
hobbed conjugate surface.  It is suitable for an initial printed mesh coupon,
not a claim of production backlash or load rating.  The sign convention is
kept explicit: positive worm rotation produces negative platform pan.
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

from build123d import (Align, Axis, Box, Cylinder, Helix, Location, Plane, Polygon,
                       Pos, Transition, Vector, extrude, import_step, sweep)

HERE = Path(__file__).resolve().parent
REF = HERE.parent.parent / "ref"
N20_STEP = REF / "n20" / "amz-n20-gearmotor.step"
XIAO_STEP = REF / "xiao" / "amz-xiao-esp32s3-sense.step"

# -------------------------- named design contract (millimetres unless noted)
BASE_OD = 98.0                              # ~96 mm target; 1 mm/radial N20-can allowance
BASE_R = BASE_OD / 2
BASE_H = 38.0
WALL = 3.0
LID_T = 2.5
DECK_T = 2.3
DECK_Z0 = BASE_H - DECK_T
DECK_INNER_R = 21.65                       # 0.45 mm radial rotor sweep clearance
CABLE_BORE_D = 8.5                         # requirement: >= 7 mm clear bore
CENTER_COLUMN_OD = 16.0
ROTOR_BORE_D = CENTER_COLUMN_OD + 0.45
WHEEL_SLEEVE_CLEAR_R = 9.75

TUBE_OD = 50.8
TUBE_ID = 44.5
TUBE_LEN = 55.0
TUBE_FIT = 0.25
TUBE_LOCATOR_R = TUBE_OD / 2 + TUBE_FIT / 2
TUBE_Z0 = BASE_H                            # tube bears on top face of the upper deck
TUBE_Z1 = TUBE_Z0 + TUBE_LEN
CAP_PLUG_D = TUBE_ID - TUBE_FIT
CAP_PLUG_H = 3.0
CAP_TOP_T = 2.0

# Acxico/GA12-N20 envelope: reference model is used in the assembly.
N20_BODY_L = 34.0
N20_FACE_W = 12.0
N20_FACE_H = 10.0
N20_SHAFT_D = 3.0
N20_SHAFT_FLAT = 2.5
N20_SHAFT_L = 10.0
N20_POCKET_CLEAR = 0.35
WORM_AXIS_Y = -20.0
WORM_AXIS_Z = 30.0
N20_FACE_X = 17.0                           # shaft 7..17; printed worm extension clears gearbox from wheel

# Adafruit 3297 DRV8833: official PCB nominal 25.4 x 17.78 mm; rounded envelope.
DRV_PCB_X = 26.0
DRV_PCB_Y = 18.0
DRV_PCB_T = 3.0
DRV_HEADER_CLEAR = 6.0
DRV_BARE_EDGE_STRIP = 1.5                  # assumed unpopulated PCB perimeter used for retention tabs
DRV_X0, DRV_X1 = -14.0, 14.0
DRV_Y0, DRV_Y1 = 16.0, 36.0
DRV_Z0 = 3.0

# Worm pair: Astra-reviewed starting geometry.
AXIAL_MODULE = 1.25
WORM_STARTS = 1
WORM_PITCH_D = 10.0
WORM_OD = 12.5
WORM_ROOT_D = 6.875
WORM_LEAD = math.pi * AXIAL_MODULE          # 3.927 mm, one start
WORM_LENGTH = 10.0
WORM_THREAD_X0, WORM_THREAD_X1 = -5.0, 5.0
WORM_DRIVE_X0, WORM_DRIVE_X1 = 7.0, 17.0    # D socket directly over the N20 shaft
WORM_NOSE_X0, WORM_NOSE_X1 = -10.0, -5.0  # 3 mm running engagement in the outboard journal
WORM_HAND = +1                              # + means theta increases with +X
WORM_CREST_MIN_MM = 1.10                   # true swept trapezoid: 1.10 mm printable crest
WHEEL_TEETH = 24
WHEEL_PITCH_D = 30.0
WHEEL_FACE = 8.0
WHEEL_ROOT_R = WHEEL_PITCH_D / 2 - 1.25 * AXIAL_MODULE
WHEEL_OUTER_R = WHEEL_PITCH_D / 2 + AXIAL_MODULE
WHEEL_Z0 = WORM_AXIS_Z - WHEEL_FACE / 2
WHEEL_Z1 = WORM_AXIS_Z + WHEEL_FACE / 2
CENTER_DISTANCE = 20.0
WHEEL_RATIO = WHEEL_TEETH / WORM_STARTS
PAN_PER_WORM_REV_DEG = -360.0 / WHEEL_RATIO # exact declared sign convention
MESH_STATUS = "PROTOTYPE: radial trapezoid wheel; run printed mesh_coupon before use"

# Rotor / camera interface frozen from v7 intent.
ROTOR_PLATFORM_Z0 = WHEEL_Z1 + 2.3           # clears fixed motor rails/nose bracket
ROTOR_PLATFORM_Z1 = BASE_H + 1.0
ROTOR_R = 21.20                              # clears the N20 can at x=17/y=-14 and the 44.5 ID tube
PAN_MIN_DEG, PAN_MAX_DEG = -90.0, 90.0
STOP_R = 37.0
STOP_W = 5.0
STOP_T = 3.0
STOP_PHYSICAL_DEG = 95.0                    # physical margin outside usable sweep
STOP_BLOCK_CENTER_DEG = 102.5               # block width puts contact face at ~95°
STOP_Z0 = 18.0                         # below motor/gear deck
STOP_ARM_HUB_R = 13.0
STOP_ARM_SLEEVE_CLEAR_R = 9.65
STOP_ARM_SLEEVE_R = 9.50              # entirely within the Ø19.5 wheel bore
STOP_ARM_KEY_X0, STOP_ARM_KEY_X1 = 1.0, 4.0
STOP_ARM_KEY_Y0 = 8.05                # above Ø16 journal, within sleeve annulus
STOP_ARM_KEY_CLEAR = 0.15
STOP_ARM_RETAINER_Z0 = 13.75
STOP_ARM_RETAINER_Z1 = 14.85
# The arm installs from below and seats against the sleeve's lower face at
# 18.15 mm.  Its separate lower band leaves the rotor insertion path clear.
STOP_ARM_Z0 = STOP_Z0 - 2.55
STOP_ARM_Z1 = STOP_Z0 + 0.15
STOP_ARM_MOUTH_W = 19.6                  # Ø19 sleeve + 0.30 mm printed lateral-slide clearance
STOP_FINGER_MOUNT_X0, STOP_FINGER_MOUNT_X1 = 13.20, 17.00
STOP_FINGER_MOUNT_HALF_Y = 4.50
STOP_FINGER_KEY_X0, STOP_FINGER_KEY_X1 = 13.40, 16.40
STOP_FINGER_KEY_HALF_Y = 1.25
STOP_FINGER_BOLT_X, STOP_FINGER_BOLT_Y = 15.00, 3.10
STOP_FINGER_BOSS_Z1 = STOP_ARM_Z1 + 2.70
HOLDER_BOARD_L, HOLDER_BOARD_W, HOLDER_PCB_T = 20.95, 17.78, 1.25
HOLDER_POCKET = 0.40
HOLDER_WALL = 2.0
HOLDER_BACK = 2.0
HOLDER_LIP_OVER = 0.95
HOLDER_LIP_GAP = 0.20
HOLDER_LIP_H = 2.0
USB_OPEN_W = 13.3
USB_CENTER_BZ = 2.36
TONGUE_W, TONGUE_T, TONGUE_LEN = 8.0, 2.0, 10.0
TONGUE_CLEAR = 0.15
HOLDER_BOSS_T = 4.0
M2_PILOT_D = 1.7
M2_CLEAR_D = 2.2
HOLDER_BOSS_X0, HOLDER_BOSS_X1 = 4.0, 16.0
HOLDER_BOSS_YC = HOLDER_BOARD_W / 2
Z_BOARD0 = BASE_H + 4.0
PCB_X = -USB_CENTER_BZ
BOARD_PLANE = Plane(origin=(PCB_X, HOLDER_BOARD_W / 2, Z_BOARD0),
                    x_dir=(0, 0, 1), z_dir=(1, 0, 0))
MAST_X = (PCB_X - HOLDER_BACK - HOLDER_BOSS_T + TONGUE_CLEAR
          + (HOLDER_BOSS_T - TONGUE_T) / 2)
PAN_AXIS = Axis((0, 0, 0), (0, 0, 1))

# Service interfaces (all use common M2 screws, omitted as purchased hardware).
LID_SCREW_POINTS = tuple((42.0 * math.cos(math.radians(a)), 42.0 * math.sin(math.radians(a)))
                         for a in (0.0, 120.0, 240.0))
MOTOR_RETAINER_POINTS = ((42.0, -24.5), (42.0, -15.5))
DRV_RETAINER_POINTS = ((-15.2, 13.0), (15.2, 13.0))
COUPON_AXIS_Z = 11.0
COUPON_WHEEL_SHOULDER_R = 10.15             # exceeds Ø19.5 wheel bore and carries wheel lower face
COUPON_WHEEL_PILOT_R = 9.50                 # Ø19 pilot clears Ø19.5 wheel bore by 0.25 mm radial
COUPON_WORM_JOURNAL_R = WORM_ROOT_D / 2 + 0.10
LATCH_SCREW_X = 23.0


def _box(x0, x1, y0, y1, z0, z1):
    return Pos(x0, y0, z0) * Box(x1-x0, y1-y0, z1-z0,
                                 align=(Align.MIN, Align.MIN, Align.MIN))


def _cyl_z(r, z0, z1):
    return Cylinder(r, z1-z0, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location((0, 0, z0)))


def _cyl_x(r, x0, x1):
    return (Cylinder(r, x1-x0, align=(Align.CENTER, Align.CENTER, Align.MIN))
            .rotate(Axis.Y, 90).moved(Location((x0, 0, 0))))


def _polar(r, angle_deg):
    a = math.radians(angle_deg)
    return r * math.cos(a), r * math.sin(a)


def on_print_bed(shape):
    """Center a printable body in XY and place its lowest point at Z=0."""
    bb = shape.bounding_box()
    return Pos(-(bb.min.X+bb.max.X)/2,
               -(bb.min.Y+bb.max.Y)/2,
               -bb.min.Z) * shape


@lru_cache(maxsize=None)
def n20_zero():
    """Purchased N20 reference; local shaft face coordinate is preserved."""
    return import_step(str(N20_STEP))


@lru_cache(maxsize=None)
def xiao_zero():
    return import_step(str(XIAO_STEP))


def n20_world():
    # Reference shaft axis at local y=6, z=5; set face/axis to declared worm datum.
    return n20_zero().moved(Location((N20_FACE_X, WORM_AXIS_Y-6.0, WORM_AXIS_Z-5.0)))


def drv8833_envelope():
    """PCB plus central populated/header keepout; 1.5 mm bare perimeter is retained by tabs."""
    pcb = _box(DRV_X0, DRV_X1, DRV_Y0, DRV_Y1, DRV_Z0, DRV_Z0 + DRV_PCB_T)
    header = _box(DRV_X0+DRV_BARE_EDGE_STRIP, DRV_X1-DRV_BARE_EDGE_STRIP,
                  DRV_Y0+DRV_BARE_EDGE_STRIP, DRV_Y1-DRV_BARE_EDGE_STRIP,
                  DRV_Z0+DRV_PCB_T, DRV_Z0+DRV_PCB_T+DRV_HEADER_CLEAR)
    return pcb + header


@lru_cache(maxsize=None)
def worm_zero():
    """Printed true-swept, single-start trapezoidal helix bored for the N20 D shaft."""
    # Long printed shaft: thread is at the wheel, D socket is outboard of it,
    # so the N20 gearbox does not occupy the wheel envelope.
    root = _cyl_x(WORM_ROOT_D / 2, WORM_NOSE_X0, WORM_DRIVE_X1)
    pitch_r = WORM_PITCH_D / 2
    root_r, tip_r = WORM_ROOT_D / 2, WORM_OD / 2
    overrun = WORM_LEAD
    path = Helix(WORM_LEAD, (WORM_THREAD_X1-WORM_THREAD_X0)+2*overrun, pitch_r,
                 center=(WORM_THREAD_X0-overrun, 0, 0), direction=(WORM_HAND, 0, 0))
    p = path.position_at(0)
    tangent = path.tangent_at(0)
    section_plane = Plane(origin=p, x_dir=Vector(0, 0, 1), z_dir=tangent)
    section = section_plane * Polygon((root_r-pitch_r-0.30, -1.20),
                                      (root_r-pitch_r-0.30, 1.20),
                                      (tip_r-pitch_r, 0.55),
                                      (tip_r-pitch_r, -0.55), align=None)
    thread = sweep(section, path=path, is_frenet=True, transition=Transition.ROUND)
    # Preserve the former zero-pose mesh phase: wheel gap is centred at -Y.
    phase_offset_deg = 360.0 * (WORM_THREAD_X0-overrun) / WORM_LEAD - 90.0
    thread = thread.rotate(Axis.X, phase_offset_deg)
    clip = Box(WORM_THREAD_X1-WORM_THREAD_X0, 14.5, 14.5,
               align=(Align.MIN, Align.CENTER, Align.CENTER)).moved(Location((WORM_THREAD_X0, 0, 0)))
    thread = (thread & clip).clean()
    # D bore: 3.15 round with a 0.5 mm flat relief; light press/ream fit prototype.
    shaft_bore_d = N20_SHAFT_D + 0.15
    bore = _cyl_x(shaft_bore_d / 2, WORM_DRIVE_X0-0.05, WORM_DRIVE_X1+0.15)
    # True D cutter = circular bore intersected with the retained half-space.
    # The flat-to-opposite extreme gets the same 0.15 mm diametral clearance as
    # the round portion: +R - y_flat = 2.50 + 0.15 mm.
    shaft_flat_clearance = 0.15
    d_flat_y = shaft_bore_d / 2 - (N20_SHAFT_FLAT + shaft_flat_clearance)
    d_bore = bore & _box(WORM_DRIVE_X0-1, WORM_DRIVE_X1+1, d_flat_y, 3, -3, 3)
    # Compact Ø8 shoulders clear the wheel while remaining larger than the
    # Ø7.325 nose-journal bore for axial location.
    left_thrust = _cyl_x(4.0, -6.6, -5.25)
    right_thrust = _cyl_x(4.0, 5.25, 6.6)
    return (thread + root + left_thrust + right_thrust - d_bore).clean()


@lru_cache(maxsize=None)
def wheel_zero():
    """Printed 24T prototype wheel.  Gaps are radial trapezoids, not a hobbed flank."""
    wheel = _cyl_z(WHEEL_OUTER_R, WHEEL_Z0, WHEEL_Z1)
    # Prototype flank clearance is deliberately generous until a hobbed wheel
    # replaces these radial gaps; it avoids BREP penetration of the true worm.
    gap_half_root = math.radians(5.2)
    gap_half_outer = math.radians(8.2)
    for tooth in range(WHEEL_TEETH):
        c = 360.0 * tooth / WHEEL_TEETH
        pts = [
            _polar(WHEEL_ROOT_R - 0.3, c-math.degrees(gap_half_root)),
            _polar(WHEEL_OUTER_R + 0.8, c-math.degrees(gap_half_outer)),
            _polar(WHEEL_OUTER_R + 0.8, c+math.degrees(gap_half_outer)),
            _polar(WHEEL_ROOT_R - 0.3, c+math.degrees(gap_half_root)),
        ]
        wheel = wheel - extrude(Plane.XY.offset(WHEEL_Z0-1) * Polygon(*pts, align=None), amount=WHEEL_FACE+2)
    wheel = wheel - _cyl_z(WHEEL_SLEEVE_CLEAR_R, WHEEL_Z0-1, WHEEL_Z1+1)
    # Rotor's annular receiver occupies this upper counterbore with 0.20 mm radial clearance.
    wheel = wheel - _cyl_z(WHEEL_ROOT_R+0.35, WHEEL_Z1-1.5, WHEEL_Z1+1)
    # Three printed torque-key sockets, away from the central cable journal.
    for a in (0.0, 120.0, 240.0):
        x, y = _polar(10.5, a)
        wheel = wheel - Pos(x, y, WHEEL_Z0-1) * Cylinder(1.7, WHEEL_FACE+2,
                                                           align=(Align.CENTER, Align.CENTER, Align.MIN))
    return wheel


@lru_cache(maxsize=None)
def base_zero():
    """Printed stationary lower case: tube groove, motor/board pockets, central cable tube and stops."""
    shell = _cyl_z(BASE_R, 0, BASE_H)
    shell = shell - _cyl_z(BASE_R-WALL, -1, BASE_H+1)  # genuinely open bottom; separate lid fits inside
    # Central printed journal carries the rotor while retaining a continuous cable bore.
    journal_top = ROTOR_PLATFORM_Z1 + 2.2
    journal = _cyl_z(CENTER_COLUMN_OD/2, 0, journal_top)
    # Neck under the upper C-clip; rotor bore remains Ø16.45 around the Ø16 column.
    journal = journal - (_cyl_z(8.2, ROTOR_PLATFORM_Z1-0.05, journal_top+0.1)
                         - _cyl_z(7.45, ROTOR_PLATFORM_Z1-0.15, journal_top+0.2))
    # Positive head above the C-clip groove: the clip cannot walk up the neck.
    journal = journal + _cyl_z(CENTER_COLUMN_OD/2, ROTOR_PLATFORM_Z1+1.35, journal_top)
    journal = journal - _cyl_z(CABLE_BORE_D/2, -1, journal_top+1)
    body = shell + journal
    # A real upper deck covers the drive compartment.  The tube bears on its
    # annular floor while the outer lip provides positive radial location.
    deck = _cyl_z(BASE_R-WALL+0.8, DECK_Z0, BASE_H) - _cyl_z(DECK_INNER_R, DECK_Z0-1, BASE_H+1)
    tube_lip = _cyl_z(TUBE_LOCATOR_R+0.9, BASE_H, BASE_H+1.6) - _cyl_z(TUBE_LOCATOR_R, BASE_H-0.1, BASE_H+1.7)
    body = body + deck + tube_lip
    # N20 and controller are loaded from below; pockets include prototype print clearance.
    body = body - _box(N20_FACE_X-1.0, N20_FACE_X+25.0, WORM_AXIS_Y-6-N20_POCKET_CLEAR, WORM_AXIS_Y+6+N20_POCKET_CLEAR,
                       WORM_AXIS_Z-5-N20_POCKET_CLEAR, WORM_AXIS_Z+5+N20_POCKET_CLEAR)
    body = body - _box(DRV_X0-0.4, DRV_X1+0.4, DRV_Y0-0.4, DRV_Y1+0.4,
                       DRV_Z0-0.4, DRV_Z0+DRV_PCB_T+DRV_HEADER_CLEAR+0.4)
    # Positive, wall-tied printed supports; pockets alone would leave the parts floating.
    # Motor rests 0.35 mm below its nominal envelope and has broad lower/side retainers to the rear wall.
    motor_saddle = _box(N20_FACE_X-1.0, N20_FACE_X+25.0, -47.0, WORM_AXIS_Y+6+N20_POCKET_CLEAR+0.15,
                        WORM_AXIS_Z-5-N20_POCKET_CLEAR-2.0, WORM_AXIS_Z-5-N20_POCKET_CLEAR)
    motor_rail_l = _box(N20_FACE_X-1.0, N20_FACE_X+25.0, WORM_AXIS_Y-6-N20_POCKET_CLEAR-0.8,
                        WORM_AXIS_Y-6-N20_POCKET_CLEAR, WORM_AXIS_Z-5-N20_POCKET_CLEAR,
                        WORM_AXIS_Z+5+N20_POCKET_CLEAR)
    motor_rail_r = _box(N20_FACE_X-1.0, N20_FACE_X+25.0, WORM_AXIS_Y+6+N20_POCKET_CLEAR,
                        WORM_AXIS_Y+6+N20_POCKET_CLEAR+0.8, WORM_AXIS_Z-5-N20_POCKET_CLEAR,
                        WORM_AXIS_Z+5+N20_POCKET_CLEAR)
    # DRV board rests on a 0.4 mm shelf and has a wall-tied cable-side rail.
    drv_shelf = _box(DRV_X0-0.4, DRV_X1+0.4, DRV_Y0-0.4, 47.0, DRV_Z0-0.5, DRV_Z0-0.1)
    drv_rail = _box(DRV_X0-0.4, DRV_X1+0.4, DRV_Y1+0.4, 47.0,
                    DRV_Z0-0.5, DRV_Z0+DRV_PCB_T+DRV_HEADER_CLEAR+0.4)
    body = body + motor_saddle + motor_rail_l + motor_rail_r + drv_shelf + drv_rail
    # Wall-tied outboard worm nose bracket and its lower web; this takes radial load and thrust shoulders.
    nose = _box(-11.5, -7.0, WORM_AXIS_Y-4.5, WORM_AXIS_Y+4.5, 24.0, 36.0)
    nose = nose - _cyl_x((WORM_ROOT_D+0.45)/2, -12.0, -6.5).moved(Location((0, WORM_AXIS_Y, WORM_AXIS_Z)))
    nose_web = _box(-11.5, -7.0, -47.0, WORM_AXIS_Y-4.3, 22.0, 25.8)
    body = body + nose + nose_web
    # Four ribs make the hollow cable journal a structural part of the fixed case.
    ribs = _box(CENTER_COLUMN_OD/2-0.2, BASE_R-WALL+1, -1.5, 1.5, 22.0, 25.8)
    ribs = ribs + _box(-1.5, 1.5, CENTER_COLUMN_OD/2-0.2, BASE_R-WALL+1, 22.0, 25.8)
    ribs = ribs + _box(-BASE_R+WALL-1, -CENTER_COLUMN_OD/2+0.2, -1.5, 1.5, 22.0, 25.8)
    ribs = ribs + _box(-1.5, 1.5, -BASE_R+WALL-1, -CENTER_COLUMN_OD/2+0.2, 22.0, 25.8)
    body = body + ribs
    # Clear the threaded section and both thrust collars from shelves/ribs;
    # the dedicated outboard nose bore remains the only printed worm journal.
    worm_running_clearance = _cyl_x(WORM_OD/2+0.30, -7.0, 7.0).moved(
        Location((0, WORM_AXIS_Y, WORM_AXIS_Z)))
    body = body - worm_running_clearance
    # Let the rotor's lower stop sleeve pass through the fixed journal ribs.
    sleeve_clearance = (_cyl_z(STOP_ARM_HUB_R+0.7, STOP_Z0-0.5, WHEEL_Z1-0.5)
                        - _cyl_z(CENTER_COLUMN_OD/2+0.05,
                                 STOP_Z0-1.0, WHEEL_Z1))
    body = body - sleeve_clearance
    # Two low spokes remain below the moving stop sleeve and permanently tie
    # the journal to the case wall without crossing the DRV pocket.
    lower_spokes = _box(CENTER_COLUMN_OD/2-0.2, BASE_R-WALL+1,
                        -2.0, 2.0, 3.0, 6.0)
    lower_spokes = lower_spokes + _box(-BASE_R+WALL-1,
                                       -CENTER_COLUMN_OD/2+0.2,
                                       -2.0, 2.0, 3.0, 6.0)
    body = body + lower_spokes
    # Three M2 lid bosses are webbed to the sidewall; the removable lid carries
    # matching clearance holes.  This is positive, serviceable retention.
    for (x, y) in LID_SCREW_POINTS:
        boss = Pos(x, y, 0) * Cylinder(2.8, 8.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
        angle = math.degrees(math.atan2(y, x))
        web = _box(42.0, BASE_R-WALL+1.0, -1.25, 1.25, 0.0, 8.0).rotate(Axis.Z, angle)
        pilot = Pos(x, y, -1) * Cylinder(M2_PILOT_D/2, 10.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
        body = body + boss + web - pilot
    # Two deck-accessed M2 screws pass freely through the deck and self-tap
    # into the retainer ears below, drawing the removable plate upward.
    for (x, y) in MOTOR_RETAINER_POINTS:
        body = body - Pos(x, y, DECK_Z0-1) * Cylinder(M2_CLEAR_D/2, DECK_T+2,
                                                        align=(Align.CENTER, Align.CENTER, Align.MIN))
    # Driver retainer posts sit just outside the PCB envelope and accept two M2 screws.
    for (x, y) in DRV_RETAINER_POINTS:
        post = Pos(x, y, DRV_Z0-0.5) * Cylinder(2.5, DRV_HEADER_CLEAR+DRV_PCB_T+1.0,
                                                  align=(Align.CENTER, Align.CENTER, Align.MIN))
        pilot = Pos(x, y, DRV_Z0-1) * Cylinder(M2_PILOT_D/2, DRV_HEADER_CLEAR+DRV_PCB_T+2,
                                                align=(Align.CENTER, Align.CENTER, Align.MIN))
        body = body + post - pilot
    # Robust outside-board webs fuse the two driver-retainer posts into the
    # shelf/rail without entering the 26 x 18 mm PCB envelope.
    drv_post_web_l = _box(-17.7, -14.0, 13.0, 16.0, DRV_Z0-0.5,
                           DRV_Z0+DRV_PCB_T+DRV_HEADER_CLEAR+0.5)
    drv_post_web_r = _box(14.0, 17.7, 13.0, 16.0, DRV_Z0-0.5,
                           DRV_Z0+DRV_PCB_T+DRV_HEADER_CLEAR+0.5)
    body = body + drv_post_web_l + drv_post_web_r
    # Clearance pocket accepts the removable motor end-stop plate; its ears
    # touch the deck from below, but neither plate nor ears share volume.
    body = body - _box(40.45, 42.85, -26.5, -13.5, 24.4, 35.80)
    # Fixed blocks are intentionally ±95°, leaving a usable checked ±90° range.
    for a in (-STOP_BLOCK_CENTER_DEG, STOP_BLOCK_CENTER_DEG):
        x, y = _polar(STOP_R, a)
        stop = Pos(x, y, STOP_ARM_Z0) * Box(STOP_W, STOP_W, STOP_ARM_Z1-STOP_ARM_Z0,
                                        align=(Align.CENTER, Align.CENTER, Align.MIN))
        wall_y = math.copysign(BASE_R - WALL + 0.5, y)
        stop_web = _box(x-STOP_W/2, x+STOP_W/2,
                        min(y, wall_y), max(y, wall_y),
                        STOP_ARM_Z0, STOP_ARM_Z1)
        body = body + stop + stop_web
    # cable exits through lid below; controller wire window joins service volume.
    body = body - _box(-6, 6, BASE_R-WALL-1, BASE_R+1, 4, 13)
    # Never allow support webs to leak outside the nominal Ø98 case envelope.
    return body & _cyl_z(BASE_R, 0, ROTOR_PLATFORM_Z1+2.3)


@lru_cache(maxsize=None)
def lid_zero():
    # World lid occupies the bottom opening; print generator places it on bed.
    lid = _cyl_z(BASE_R-WALL-0.25, -LID_T, 0)
    # The lid surrounds (but does not clamp) the fixed Ø16 hollow journal.
    lid = lid - _cyl_z((CENTER_COLUMN_OD+0.50)/2, -LID_T-1, 1)
    for (x, y) in LID_SCREW_POINTS:
        lid = lid - Pos(x, y, -LID_T-1) * Cylinder(M2_CLEAR_D/2, LID_T+2,
                                              align=(Align.CENTER, Align.CENTER, Align.MIN))
    return lid


@lru_cache(maxsize=None)
def rotor_platform_zero():
    """Printed rotating platform and camera mast.  Wheel is a separately printable keyed part."""
    disk = _cyl_z(ROTOR_R, ROTOR_PLATFORM_Z0, ROTOR_PLATFORM_Z1)
    disk = disk - _cyl_z(ROTOR_BORE_D/2, ROTOR_PLATFORM_Z0-1, ROTOR_PLATFORM_Z1+1)
    # Stationary worm crest rises above the wheel mid-plane; retain an overhead relief.
    disk = disk - _box(WORM_NOSE_X0-0.5, WORM_DRIVE_X0+0.5, WORM_AXIS_Y-WORM_OD/2-0.6,
                       WORM_AXIS_Y+WORM_OD/2+0.6, ROTOR_PLATFORM_Z0-1, ROTOR_PLATFORM_Z1+1)
    # underside annular receiver keeps the wheel coaxial without a purchased bearing.
    receiver = (_cyl_z(WHEEL_ROOT_R+0.15, WHEEL_Z1-1.5, ROTOR_PLATFORM_Z0+0.1)
                - _cyl_z(ROTOR_BORE_D/2, WHEEL_Z1-2, ROTOR_PLATFORM_Z0+1))
    # This sleeve is deliberately entirely inside the wheel's Ø19.5 bore so
    # the wheel can be installed first. Its internal key pocket registers the
    # later side-installed stop arm; no post or key projects outside that bore.
    sleeve_lower = _cyl_z(STOP_ARM_SLEEVE_R, STOP_ARM_RETAINER_Z0-0.45, STOP_ARM_Z0)
    sleeve_keyed = _cyl_z(STOP_ARM_SLEEVE_R, STOP_ARM_Z0, WHEEL_Z0-0.40)
    key_pocket = _box(STOP_ARM_KEY_X0-STOP_ARM_KEY_CLEAR,
                      STOP_ARM_KEY_X1+STOP_ARM_KEY_CLEAR,
                      STOP_ARM_KEY_Y0-STOP_ARM_KEY_CLEAR, 10.0,
                      STOP_ARM_Z0-0.1, STOP_ARM_Z1+0.1)
    sleeve_keyed = sleeve_keyed - key_pocket
    sleeve_upper = _cyl_z(STOP_ARM_SLEEVE_R, WHEEL_Z0-0.40, WHEEL_Z1-1.0)
    lower_stop_sleeve = sleeve_lower + sleeve_keyed + sleeve_upper
    lower_stop_sleeve = lower_stop_sleeve - _cyl_z(ROTOR_BORE_D/2, STOP_ARM_RETAINER_Z0-1, WHEEL_Z1)
    # Lower groove accepts the separate C-clip after the stop arm is slid on.
    lower_stop_sleeve = lower_stop_sleeve - (_cyl_z(9.70, STOP_ARM_RETAINER_Z0, STOP_ARM_RETAINER_Z1)
                                             - _cyl_z(8.95, STOP_ARM_RETAINER_Z0-0.1, STOP_ARM_RETAINER_Z1+0.1))
    # A reduced OD groove accepts the separate C-clip that catches the wheel's
    # lower bore; the upper receiver/keys locate the other axial direction.
    lower_stop_sleeve = lower_stop_sleeve - (_cyl_z(9.7, WHEEL_Z0-1.0, WHEEL_Z0+0.15)
                                             - _cyl_z(8.95, WHEEL_Z0-1.1, WHEEL_Z0+0.25))
    # Mate the wheel's three sockets: 3 keyed pegs carry torque rather than relying on a friction annulus.
    keys = None
    for a in (0.0, 120.0, 240.0):
        x, y = _polar(10.5, a)
        peg = Pos(x, y, WHEEL_Z1-3.0) * Cylinder(1.5, 3.10, align=(Align.CENTER, Align.CENTER, Align.MIN))
        keys = peg if keys is None else keys + peg
    # v7-style replaceable holder joint: a 2 mm tongue rises into the holder's
    # 4 mm back boss and is retained by one transverse M2 self-tapping screw.
    z_boss0 = Z_BOARD0 + HOLDER_BOSS_X0
    # Bypass the raised fixed journal with two outboard legs, then bridge above
    # its C-clip before returning to the centred v7 tongue.
    leg_l = _box(MAST_X, MAST_X+TONGUE_T, -12.0, -8.5,
                 ROTOR_PLATFORM_Z1-0.01, ROTOR_PLATFORM_Z1+2.55)
    leg_r = _box(MAST_X, MAST_X+TONGUE_T, 8.5, 12.0,
                 ROTOR_PLATFORM_Z1-0.01, ROTOR_PLATFORM_Z1+2.55)
    mast_bridge = _box(MAST_X, MAST_X+TONGUE_T, -12.0, 12.0,
                       ROTOR_PLATFORM_Z1+2.35, ROTOR_PLATFORM_Z1+3.35)
    mast = _box(MAST_X, MAST_X+TONGUE_T, -8.0, 8.0,
                ROTOR_PLATFORM_Z1+2.35, z_boss0-0.5)
    tongue = _box(MAST_X, MAST_X+TONGUE_T, -TONGUE_W/2, TONGUE_W/2,
                  z_boss0-0.51, z_boss0+TONGUE_LEN-TONGUE_CLEAR)
    tongue_pilot_local = (Pos(HOLDER_BOSS_X0+TONGUE_LEN/2, HOLDER_BOSS_YC,
                              -HOLDER_BACK-HOLDER_BOSS_T-1)
                          * Cylinder(M2_PILOT_D/2, HOLDER_BOSS_T+2,
                                     align=(Align.CENTER, Align.CENTER, Align.MIN)))
    tongue_pilot = Location(BOARD_PLANE) * tongue_pilot_local
    return (disk + receiver + lower_stop_sleeve + keys
            + leg_l + leg_r + mast_bridge + mast + tongue - tongue_pilot)


@lru_cache(maxsize=None)
def stop_collar_zero():
    """Short C-collar: take the verified remote route before fitting the sleeve."""
    z0, z1 = STOP_ARM_Z0, STOP_ARM_Z1
    hub = _cyl_z(STOP_ARM_HUB_R, z0, z1) - _cyl_z(STOP_ARM_SLEEVE_CLEAR_R, z0-0.1, z1+0.1)
    # The +Y tongue enters the in-bore rotor pocket. Its two X faces carry
    # torque, while the lower C-clip provides positive axial retention.
    key_tongue = _box(STOP_ARM_KEY_X0, STOP_ARM_KEY_X1,
                      STOP_ARM_KEY_Y0, STOP_ARM_SLEEVE_R+0.20, z0, z1)
    # The open -Y mouth passes around both the fixed lower journal spokes and
    # the Ø19.0 rotor sleeve during the lateral slide. The +Y torque tongue
    # remains fully intact for registered final attachment.
    mouth = _box(-STOP_ARM_MOUTH_W/2, STOP_ARM_MOUTH_W/2,
                 -STOP_ARM_HUB_R-1.0, 0.0, z0-0.1, z1+0.1)
    # Elevated M2 mount is fused into the collar only on its inner bridge;
    # the finger approaches underneath and keys into the central socket.
    boss_bridge = _box(STOP_ARM_SLEEVE_CLEAR_R, 13.05, -STOP_FINGER_MOUNT_HALF_Y, STOP_FINGER_MOUNT_HALF_Y,
                       z1-0.30, STOP_FINGER_BOSS_Z1)
    boss_plate = _box(12.85, STOP_FINGER_MOUNT_X1, -STOP_FINGER_MOUNT_HALF_Y,
                      STOP_FINGER_MOUNT_HALF_Y, z1, STOP_FINGER_BOSS_Z1)
    key_socket = _box(STOP_FINGER_KEY_X0-0.15, STOP_FINGER_KEY_X1+0.15,
                      -STOP_FINGER_KEY_HALF_Y-0.15, STOP_FINGER_KEY_HALF_Y+0.15,
                      z1-0.05, STOP_FINGER_BOSS_Z1+0.10)
    collar = hub + key_tongue + boss_bridge + boss_plate - mouth - key_socket
    for y in (-STOP_FINGER_BOLT_Y, STOP_FINGER_BOLT_Y):
        collar = collar - Pos(STOP_FINGER_BOLT_X, y, z1-0.1) * Cylinder(
            M2_PILOT_D/2, STOP_FINGER_BOSS_Z1-z1+0.3,
            align=(Align.CENTER, Align.CENTER, Align.MIN))
    return collar


@lru_cache(maxsize=None)
def stop_finger_zero():
    """Straight radial stop finger; install below the collar and fasten upward with two M2s."""
    z0, z1 = STOP_ARM_Z0, STOP_ARM_Z1
    web = _box(STOP_FINGER_MOUNT_X0, STOP_R, -(STOP_W-0.6)/2, (STOP_W-0.6)/2, z0, z1)
    stop = Pos(STOP_R, 0, z0) * Box(12.0, STOP_W-0.6, z1-z0,
                                    align=(Align.MAX, Align.CENTER, Align.MIN))
    ears = _box(STOP_FINGER_MOUNT_X0, STOP_FINGER_MOUNT_X1,
                -STOP_FINGER_MOUNT_HALF_Y, STOP_FINGER_MOUNT_HALF_Y, z0, z1)
    key = _box(STOP_FINGER_KEY_X0, STOP_FINGER_KEY_X1,
               -STOP_FINGER_KEY_HALF_Y, STOP_FINGER_KEY_HALF_Y,
               z1-0.35, STOP_FINGER_BOSS_Z1-0.15)
    finger = web + stop + ears + key
    for y in (-STOP_FINGER_BOLT_Y, STOP_FINGER_BOLT_Y):
        finger = finger - Pos(STOP_FINGER_BOLT_X, y, z0-1) * Cylinder(
            M2_CLEAR_D/2, z1-z0+2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return finger


@lru_cache(maxsize=None)
def stop_arm_zero():
    """Compatibility alias for the collar generator retained by older print scripts."""
    return stop_collar_zero()


@lru_cache(maxsize=None)
def stop_arm_retainer_zero():
    """Bottom-installed C-clip in the sleeve's lower groove; prevents arm drop."""
    clip = (_cyl_z(10.25, STOP_ARM_RETAINER_Z0, STOP_ARM_RETAINER_Z1)
            - _cyl_z(9.00, STOP_ARM_RETAINER_Z0-0.1, STOP_ARM_RETAINER_Z1+0.1))
    return clip - _box(0.0, 12.0, -1.8, 1.8,
                       STOP_ARM_RETAINER_Z0-0.2, STOP_ARM_RETAINER_Z1+0.2)


@lru_cache(maxsize=None)
def wheel_retainer_zero():
    """Printed C-clip below wheel: snap into rotor sleeve groove after wheel installation."""
    clip = _cyl_z(10.25, WHEEL_Z0-1.00, WHEEL_Z0) - _cyl_z(9.00, WHEEL_Z0-1.15, WHEEL_Z0+0.10)
    return clip - _box(0.0, 12.0, -1.8, 1.8, WHEEL_Z0-1.2, WHEEL_Z0+0.4)


@lru_cache(maxsize=None)
def rotor_retainer_zero():
    """Printed C-clip above rotor: snaps over the reduced journal neck, retaining axial pan position."""
    z0, z1 = ROTOR_PLATFORM_Z1+0.05, ROTOR_PLATFORM_Z1+1.25
    clip = _cyl_z(8.70, z0, z1) - _cyl_z(7.55, z0-0.1, z1+0.1)
    return clip - _box(0.0, 10.0, -1.9, 1.9, z0-0.2, z1+0.2)


@lru_cache(maxsize=None)
def motor_retainer_zero():
    """M2-screwed end-stop plate; remove it from above after lifting tube/rotor."""
    plate = _box(41.25, 42.55, -26.35, -13.65, 24.65, 35.25)
    ears = _box(41.05, 42.70, -26.0, -22.2, 34.95, DECK_Z0)
    ears = ears + _box(41.05, 42.70, -17.8, -14.0, 34.95, DECK_Z0)
    retainer = plate + ears
    for (x, y) in MOTOR_RETAINER_POINTS:
        retainer = retainer - Pos(x, y, 34.8) * Cylinder(M2_PILOT_D/2, 2.0,
                                                          align=(Align.CENTER, Align.CENTER, Align.MIN))
    return retainer


@lru_cache(maxsize=None)
def drv_retainer_zero():
    """M2-screwed open frame: retains PCB lift without invading the 6 mm header envelope."""
    z0, z1 = DRV_Z0+DRV_PCB_T+DRV_HEADER_CLEAR+0.55, DRV_Z0+DRV_PCB_T+DRV_HEADER_CLEAR+1.65
    left = _box(-16.1, -14.3, 13.0, 38.0, z0, z1)
    right = _box(14.3, 16.1, 13.0, 38.0, z0, z1)
    front = _box(-16.1, 16.1, 13.0, 14.6, z0, z1)
    back = _box(-16.1, 16.1, 36.2, 38.0, z0, z1)
    # Two inward lips catch only assumed bare PCB edge strips. They begin 0.05
    # mm above nominal PCB top, so a 0.2 mm upward lift is positively arrested.
    tab_z0, tab_z1 = DRV_Z0+DRV_PCB_T+0.05, DRV_Z0+DRV_PCB_T+0.75
    tab_l = _box(-14.4, DRV_X0+DRV_BARE_EDGE_STRIP-0.10,
                 DRV_Y0+DRV_BARE_EDGE_STRIP, DRV_Y1-DRV_BARE_EDGE_STRIP, tab_z0, tab_z1)
    tab_r = _box(DRV_X1-DRV_BARE_EDGE_STRIP+0.10, 14.4,
                 DRV_Y0+DRV_BARE_EDGE_STRIP, DRV_Y1-DRV_BARE_EDGE_STRIP, tab_z0, tab_z1)
    # Continuous outboard side stems fuse the low tabs to the removable frame
    # without occupying either the board envelope or header keepout.
    stem_l = _box(-16.1, -14.20, DRV_Y0+DRV_BARE_EDGE_STRIP, DRV_Y1-DRV_BARE_EDGE_STRIP,
                  tab_z0, z1+0.05)
    stem_r = _box(14.20, 16.1, DRV_Y0+DRV_BARE_EDGE_STRIP, DRV_Y1-DRV_BARE_EDGE_STRIP,
                  tab_z0, z1+0.05)
    retainer = left + right + front + back + tab_l + tab_r + stem_l + stem_r
    for (x, y) in DRV_RETAINER_POINTS:
        retainer = retainer - Pos(x, y, DRV_Z0-1) * Cylinder(M2_CLEAR_D/2, DRV_HEADER_CLEAR+DRV_PCB_T+3,
                                                              align=(Align.CENTER, Align.CENTER, Align.MIN))
    return retainer


def _board_box(x0, x1, y0, y1, z0, z1):
    return Location(BOARD_PLANE) * _box(x0, x1, y0, y1, z0, z1)


@lru_cache(maxsize=None)
def holder_zero():
    """v7-derived XIAO carrier: 0.4-side pocket, 0.95 lips, 0.2 lip clearance, open top."""
    x0, x1 = -HOLDER_POCKET-HOLDER_WALL, HOLDER_BOARD_L+HOLDER_POCKET+0.5
    y0, y1 = -HOLDER_POCKET-HOLDER_WALL, HOLDER_BOARD_W+HOLDER_POCKET+HOLDER_WALL
    back = _board_box(x0, x1, y0, y1, -HOLDER_BACK, 0)
    left = _board_box(x0, x1, y0, y0+HOLDER_WALL, -HOLDER_BACK, 6.0)
    right = _board_box(x0, x1, y1-HOLDER_WALL, y1, -HOLDER_BACK, 6.0)
    lip_z0 = HOLDER_PCB_T + HOLDER_LIP_GAP
    lips = _board_box(-HOLDER_POCKET, x1, -HOLDER_POCKET, -HOLDER_POCKET+HOLDER_LIP_OVER, lip_z0, lip_z0+HOLDER_LIP_H)
    lips = lips + _board_box(-HOLDER_POCKET, x1, HOLDER_BOARD_W+HOLDER_POCKET-HOLDER_LIP_OVER,
                              HOLDER_BOARD_W+HOLDER_POCKET, lip_z0, lip_z0+HOLDER_LIP_H)
    rail = _board_box(x0, -HOLDER_POCKET, y0, y1, -HOLDER_BACK, lip_z0+HOLDER_LIP_H)
    boss = _board_box(HOLDER_BOSS_X0, HOLDER_BOSS_X1,
                      HOLDER_BOSS_YC-6.0, HOLDER_BOSS_YC+6.0,
                      -HOLDER_BACK-HOLDER_BOSS_T, -HOLDER_BACK+0.01)
    holder = back + left + right + lips + rail + boss
    usb = _board_box(x0-1, -HOLDER_POCKET+1, HOLDER_BOARD_W/2-USB_OPEN_W/2,
                     HOLDER_BOARD_W/2+USB_OPEN_W/2, -HOLDER_BACK-1, lip_z0+HOLDER_LIP_H+1)
    socket_z0 = -HOLDER_BACK-HOLDER_BOSS_T/2-TONGUE_T/2-TONGUE_CLEAR
    socket_z1 = -HOLDER_BACK-HOLDER_BOSS_T/2+TONGUE_T/2+TONGUE_CLEAR
    socket = _board_box(HOLDER_BOSS_X0-1, HOLDER_BOSS_X0+TONGUE_LEN+TONGUE_CLEAR,
                        HOLDER_BOSS_YC-TONGUE_W/2-TONGUE_CLEAR,
                        HOLDER_BOSS_YC+TONGUE_W/2+TONGUE_CLEAR,
                        socket_z0, socket_z1)
    pilot_local = (Pos(HOLDER_BOSS_X0+TONGUE_LEN/2, HOLDER_BOSS_YC,
                       -HOLDER_BACK-HOLDER_BOSS_T-1)
                   * Cylinder(M2_PILOT_D/2, HOLDER_BOSS_T+2,
                              align=(Align.CENTER, Align.CENTER, Align.MIN)))
    pilot = Location(BOARD_PLANE) * pilot_local
    # Extended side ears put the removable top-latch screws outside the board.
    holder = holder + _board_box(HOLDER_BOARD_L+0.20, 24.3, -HOLDER_POCKET-HOLDER_WALL, -HOLDER_POCKET,
                                 -HOLDER_BACK, 0.20)
    holder = holder + _board_box(HOLDER_BOARD_L+0.20, 24.3, HOLDER_BOARD_W+HOLDER_POCKET, HOLDER_BOARD_W+HOLDER_POCKET+HOLDER_WALL,
                                 -HOLDER_BACK, 0.20)
    for y in (-1.4, HOLDER_BOARD_W+1.4):
        latch_pilot = Location(BOARD_PLANE) * (Pos(LATCH_SCREW_X, y, -3.0)
                                               * Cylinder(M2_PILOT_D/2, 4.0,
                                                          align=(Align.CENTER, Align.CENTER, Align.MIN)))
        holder = holder - latch_pilot
    return holder - usb - socket - pilot


@lru_cache(maxsize=None)
def holder_latch_zero():
    """Removable M2-screwed crossbar: install after sliding the XIAO down into its holder."""
    # Crossbar lies over the board's upper edge, while screw ears sit on the
    # *front* faces of the holder's extended side ears (face contact only).
    crossbar = _board_box(HOLDER_BOARD_L+0.20, 22.2,
                          0.0, HOLDER_BOARD_W,
                          0.05, 1.35)
    ear_l = _board_box(22.0, 24.8, -3.0, -HOLDER_POCKET,
                       0.20, 1.35)
    ear_r = _board_box(22.0, 24.8, HOLDER_BOARD_W+HOLDER_POCKET,
                       HOLDER_BOARD_W+3.0, 0.20, 1.35)
    bridge_l = _board_box(22.0, 22.2, -HOLDER_POCKET, 0.0, 0.20, 1.35)
    bridge_r = _board_box(22.0, 22.2, HOLDER_BOARD_W, HOLDER_BOARD_W+HOLDER_POCKET, 0.20, 1.35)
    latch = crossbar + ear_l + ear_r + bridge_l + bridge_r
    for y in (-1.4, HOLDER_BOARD_W+1.4):
        hole = Location(BOARD_PLANE) * (Pos(LATCH_SCREW_X, y, -3.0)
                                        * Cylinder(M2_CLEAR_D/2, 4.0,
                                                   align=(Align.CENTER, Align.CENTER, Align.MIN)))
        latch = latch - hole
    return latch


@lru_cache(maxsize=None)
def cap_zero():
    return _cyl_z(CAP_PLUG_D/2, TUBE_Z1-CAP_PLUG_H, TUBE_Z1) + _cyl_z(TUBE_OD/2, TUBE_Z1, TUBE_Z1+CAP_TOP_T)


@lru_cache(maxsize=None)
def tube_envelope():
    return _cyl_z(TUBE_OD/2, TUBE_Z0, TUBE_Z1) - _cyl_z(TUBE_ID/2, TUBE_Z0-1, TUBE_Z1+1)


@lru_cache(maxsize=None)
def mesh_coupon_zero():
    """Single-piece supported mesh-test fixture for the production worm/wheel.

    Print this fixture plus ``print_worm`` and ``print_wheel``.  The wheel drops
    over the vertical post and the worm snaps into the two open-top cradles at
    the same 20 mm centre distance and Z alignment used by the assembly.
    """
    plate = _box(-22.0, 24.0, -29.0, 20.0, 0.0, 3.0)
    wheel_bottom = COUPON_AXIS_Z-WHEEL_FACE/2
    shoulder = _cyl_z(COUPON_WHEEL_SHOULDER_R, 3.0, wheel_bottom)
    pilot = _cyl_z(COUPON_WHEEL_PILOT_R, wheel_bottom, COUPON_AXIS_Z+3.5)
    wheel_post = shoulder + pilot - _cyl_z(CABLE_BORE_D/2, 2.0, COUPON_AXIS_Z+4.5)
    fixture = plate + wheel_post
    coupon_axis_z = COUPON_AXIS_Z
    for x0, x1 in ((-11.2, -7.2), (13.8, 17.2)):
        cradle = _box(x0, x1, -24.9, -15.1, 3.0, coupon_axis_z+5.0)
        bearing = _cyl_x(COUPON_WORM_JOURNAL_R, x0-1, x1+1).moved(
            Location((0, -CENTER_DISTANCE, coupon_axis_z)))
        top_slot = _box(x0-1, x1+1,
                        -CENTER_DISTANCE-(WORM_ROOT_D/2+0.15),
                        -CENTER_DISTANCE+(WORM_ROOT_D/2+0.15),
                        coupon_axis_z, coupon_axis_z+6.0)
        fixture = fixture + (cradle - bearing - top_slot)
    return fixture


def worm_angle_for_pan(pan_deg: float) -> float:
    """Coupled motor phase; positive worm rotation produces negative pan."""
    return -pan_deg * WHEEL_RATIO


def build_parts(pan_deg: float = 0.0):
    rotating = {
        "printed_rotor_platform": rotor_platform_zero(),
        "printed_bottom_stop_collar": stop_collar_zero(),
        "printed_bottom_stop_finger": stop_finger_zero(),
        "printed_bottom_stop_arm_axial_c_clip": stop_arm_retainer_zero(),
        "printed_wheel_24t_prototype": wheel_zero(),
        "printed_wheel_axial_c_clip": wheel_retainer_zero(),
        "printed_camera_holder_v7_dimensions": holder_zero(),
        "printed_holder_top_latch": holder_latch_zero(),
        "purchased_xiao_camera_reference": xiao_zero().moved(Location(BOARD_PLANE)),
    }
    rotating = {name: shape.rotate(PAN_AXIS, pan_deg) for name, shape in rotating.items()}
    fixed = {
        "printed_base": base_zero(),
        "printed_bottom_lid": lid_zero(),
        "printed_motor_service_retainer": motor_retainer_zero(),
        "printed_drv8833_service_retainer": drv_retainer_zero(),
        "printed_rotor_axial_c_clip": rotor_retainer_zero(),
        "printed_single_start_worm": (worm_zero()
                                        .rotate(Axis.X, worm_angle_for_pan(pan_deg))
                                        .moved(Location((0, WORM_AXIS_Y, WORM_AXIS_Z)))),
        "purchased_n20_envelope": n20_world(),
        "clearance_envelope_adafruit_drv8833": drv8833_envelope(),
        "purchased_50_8mm_tube_envelope": tube_envelope(),
        "printed_tube_cap": cap_zero(),
    }
    return {"fixed": fixed, "rotating": rotating}


def build_assembly(pan_deg: float = 0.0):
    # ``scripts/step`` provides the installed helper under cadpy.assembly.
    from cadpy.assembly import AssemblyHelper, label_shape
    groups = build_parts(pan_deg)
    asm = AssemblyHelper("n20_worm_v8_labeled_assembly")
    fixed = [label_shape(s, n) for n, s in groups["fixed"].items()]
    rotating = [label_shape(s, n) for n, s in groups["rotating"].items()]
    fixed_mod = asm.compound(fixed, label="fixed_case_and_purchased_envelopes")
    rotor_mod = asm.compound(rotating, label="pan_rotor_group")
    asm.children.extend([fixed_mod, rotor_mod])
    asm.revolute_frame(fixed_mod, "pan_axis", PAN_AXIS)
    return asm.build()
