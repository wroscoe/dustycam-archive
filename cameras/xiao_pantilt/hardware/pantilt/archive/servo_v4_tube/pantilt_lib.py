"""xiao_pantilt geometry library — v4 PAN-ONLY tube version (2026-09-08).

Pan-only camera pod for the Seeed XIAO ESP32S3 Sense driven by one 9 g micro
servo through a 30T:26T spur stage sunk in a well in the base. The camera
sits in a cradle on a mast that bolts straight onto the pan gear. A clear
acrylic tube (2", 50.8 OD x 44.5 ID) drops into a groove in the base's
closing ring and a printed cap plugs its top.

Kept from v3: base cup + well + closing ring, pan servo mount (23 x 12.2
pocket, flange under the floor plate), pan gear with integral journal post,
thrust ring. Removed: tilt servo, sector, pinion, yoke arms, pivot pins.

Board orientation: vertical, USB edge DOWN (sensor landscape), USB-C plug
centred on the pan axis so the cable drops straight through the journal
bore. `fixed_tilt_deg` rotates cradle + camera about the board centre and
the mast is fused afterwards.

World frame: origin on the pan axis at the base bottom, Z up, +X = look
direction at pan 0; pan about +Z, +pan turns the camera toward +Y.
"""

from __future__ import annotations

import math
import os
from functools import lru_cache
from pathlib import Path

from build123d import Align, Axis, Box, Cylinder, Location, Plane, Polygon, Pos, extrude, fillet
from cadgen.step_scene import import_step

HERE = Path(__file__).resolve().parent
REF = HERE.parent.parent / "ref"
XIAO_STEP = REF / "xiao" / "amz-xiao-esp32s3-sense.step"
SERVO_STEP = REF / "mg90s" / "amz-mg90s-micro-servo.step"

HAS_TILT = False

# ----------------------------------------------------------------- parameters
gear_module_mm = 1.0
pressure_angle_deg = 20.0
gear_face_mm = 5.0
gear_backlash_mm = float(os.environ.get("PANTILT_BACKLASH", "0.15"))
pan_pinion_teeth, pan_gear_teeth = 30, 26        # servo -> pod, ratio 0.867 (servo +-78 for pan +-90)
pan_min_deg, pan_max_deg = -90.0, 90.0
fixed_tilt_deg = float(os.environ.get("PANTILT_FIXED_TILT", "0"))   # + = look up

wall_mm = 2.0
pocket_clearance_mm = 0.25
servo_pocket_clearance = 0.2
usb_plug_space_mm = 13.0         # straight USB-C plug overmold under the board (right-angle plug: 8)

# 9 g servo frame facts (sarg mg90s-micro-servo)
servo_w, servo_len = 11.8, 22.6
servo_body_y0, servo_body_y1 = 4.7, 27.3
servo_flange_z0, servo_flange_z1 = 15.9, 18.4
servo_body_top_z, servo_boss_top_z, servo_spline_top_z = 22.7, 26.9, 29.9
servo_axis_x, servo_axis_y = 5.9, 21.3
servo_spline_d = 4.7

# XIAO ESP32S3 Sense board facts (sarg vendor STEP)
board_len, board_w = 20.95, 17.78
lens_bx, lens_by = 3.53, 8.25
usb_w, usb_center_bz = 8.94, 2.36

# clear tube cover: 2" acrylic tube, 1/8" wall
tube_od, tube_id, tube_len = 50.8, 44.5, 45.0
tube_fit = 0.2
cap_plug_depth, cap_top = 3.0, 2.0

# ------------------------------------------------------------ derived layout
def _pitch_r(n):
    return gear_module_mm * n / 2.0

pan_center_dist = _pitch_r(pan_pinion_teeth) + _pitch_r(pan_gear_teeth) + gear_backlash_mm      # 28.15
pan_pinion_tip_r = _pitch_r(pan_pinion_teeth) + gear_module_mm                                   # 17

plate_thick = 3.0
gear_band_above_plate = servo_boss_top_z - servo_flange_z1 - plate_thick        # 5.5
Z_FLOOR_TOP = 26.0
pan_servo_z0 = Z_FLOOR_TOP - plate_thick - servo_flange_z1                      # 4.6
Z_PAN_GEAR = Z_FLOOR_TOP + gear_band_above_plate                                # 31.5
pan_gear_thick = gear_face_mm + 0.5
Z_GEAR_TOP = Z_PAN_GEAR + pan_gear_thick                                        # 37 = pod platform
journal_od, journal_bore, journal_len = 14.0, 7.0, 8.0
Z_JOURNAL_BOTTOM = Z_FLOOR_TOP - journal_len
thrust_ring_r0, thrust_ring_r1, thrust_gap = 9.0, 13.0, 0.2

pan_pinion_xy = (-pan_center_dist, 0.0)
pan_mesh_dir_deg = 180.0
well_r = pan_pinion_tip_r + pan_center_dist + 1.5                               # 46.65
base_wall = 2.0
base_r = well_r + base_wall
Z_RIM = Z_GEAR_TOP + 4.0                                                        # 41
ring_thick = 3.0
Z_SEAT = Z_RIM + ring_thick                                                     # 44
ring_r_out = base_r
ring_r_in = 19.5                                                                # pod stays inside r 18
groove_depth = 2.0
groove_r0 = tube_id / 2 - tube_fit / 2                                          # 22.15
groove_r1 = tube_od / 2 + tube_fit / 2                                          # 25.5
Z_TUBE0 = Z_SEAT - groove_depth                                                 # 42
Z_TUBE1 = Z_TUBE0 + tube_len                                                    # 87
base_boss_d = 22.0
base_boss_z0 = 12.0
PAN_AXIS = Axis((0, 0, 0), (0, 0, 1))

# camera pod: USB-C plug centred on the pan axis
pcb_x = -usb_center_bz                                  # -2.36
cradle_x0 = pcb_x - wall_mm                             # -4.36
cradle_x1 = pcb_x + 15.0                                # 12.64 (front of side walls, past the lens)
rail_depth = 3.0
cradle_inner_y = board_w / 2 + pocket_clearance_mm
cradle_outer_y = cradle_inner_y + wall_mm               # 11.15
Z_CRADLE0 = Z_GEAR_TOP + usb_plug_space_mm              # 50: bottom rail
Z_BOARD0 = Z_CRADLE0 + wall_mm + pocket_clearance_mm    # 52.25: board bottom edge (bx=0)
Z_CRADLE1 = Z_BOARD0 + board_len + 0.5 + wall_mm        # 75.7
Z_BOARD_CENTER = Z_BOARD0 + board_len / 2
BOARD_PLANE = Plane(origin=(pcb_x, board_w / 2, Z_BOARD0), x_dir=(0, 0, 1), z_dir=(1, 0, 0))
TILT_AXIS = Axis((pcb_x + 7.0, 0, Z_BOARD_CENTER), (0, -1, 0))   # fixed tilt pivot (about the board's mid-depth)
mast_y = 8.0
pod_r = math.hypot(cradle_x1, cradle_outer_y)           # 16.8


# ------------------------------------------------------------------- gears
def involute_gear_sketch(n_teeth: int, module: float = gear_module_mm,
                         pa_deg: float = pressure_angle_deg, steps: int = 8) -> Polygon:
    pa = math.radians(pa_deg)
    r = module * n_teeth / 2.0
    rb = r * math.cos(pa)
    ra = r + module
    rf = r - 1.25 * module
    inv = lambda a: math.tan(a) - a
    half_base = math.pi / (2 * n_teeth) + inv(pa)

    def phi(rho):
        return half_base - inv(math.acos(rb / rho))

    rho0 = max(rb, rf)
    pts = []
    for i in range(n_teeth):
        c = 2 * math.pi * i / n_teeth
        if rf < rb:
            pts.append((rf, c - phi(rho0)))
        for k in range(steps + 1):
            rho = rho0 + (ra - rho0) * k / steps
            pts.append((rho, c - phi(rho)))
        for k in range(steps, -1, -1):
            rho = rho0 + (ra - rho0) * k / steps
            pts.append((rho, c + phi(rho)))
        if rf < rb:
            pts.append((rf, c + phi(rho0)))
        pts.append((rf, c + math.pi / n_teeth))
    xy = [(rho * math.cos(a), rho * math.sin(a)) for rho, a in pts]
    return Polygon(*xy, align=None)


def _cyl(r, h):
    return Cylinder(r, h, align=(Align.CENTER, Align.CENTER, Align.MIN))


def spline_socket():
    return Pos(0, 0, -1) * _cyl((servo_spline_d + 0.1) / 2, (servo_spline_top_z - servo_boss_top_z) + 1)


@lru_cache(maxsize=None)
def pan_pinion_zero():
    return extrude(involute_gear_sketch(pan_pinion_teeth), amount=gear_face_mm) - spline_socket()


@lru_cache(maxsize=None)
def pan_gear_zero():
    g = extrude(involute_gear_sketch(pan_gear_teeth), amount=pan_gear_thick)
    post = Pos(0, 0, Z_JOURNAL_BOTTOM - Z_PAN_GEAR) * _cyl(journal_od / 2, journal_len + 0.01)
    return (g + post) - Pos(0, 0, Z_JOURNAL_BOTTOM - Z_PAN_GEAR - 1) * _cyl(journal_bore / 2, pan_gear_thick + journal_len + 2)


# ----------------------------------------------------------- imported parts
@lru_cache(maxsize=None)
def servo_zero():
    return import_step(str(SERVO_STEP)).solids()[0]


@lru_cache(maxsize=None)
def xiao_zero():
    return import_step(str(XIAO_STEP))


def _servo_plane(axis_point_world, x_dir, z_dir):
    pl = Plane(origin=(0, 0, 0), x_dir=x_dir, z_dir=z_dir)
    xd, yd, zd = pl.x_dir.to_tuple(), pl.y_dir.to_tuple(), pl.z_dir.to_tuple()
    origin = tuple(
        axis_point_world[i] - servo_axis_x * xd[i] - servo_axis_y * yd[i] - servo_flange_z1 * zd[i]
        for i in range(3)
    )
    return Plane(origin=origin, x_dir=x_dir, z_dir=z_dir)


PAN_SERVO_PLANE = _servo_plane((pan_pinion_xy[0], pan_pinion_xy[1], Z_FLOOR_TOP - plate_thick), (1, 0, 0), (0, 0, 1))


# ------------------------------------------------------------ structure
def _box(x0, x1, y0, y1, z0, z1):
    return Pos(x0, y0, z0) * Box(x1 - x0, y1 - y0, z1 - z0, align=(Align.MIN, Align.MIN, Align.MIN))


def _cyl_z(cx, cy, z0, z1, d):
    return Pos(cx, cy, z0) * _cyl(d / 2, z1 - z0)


def _servo_pocket_xy(cx, cy, z0, z1):
    lx = servo_w + 2 * servo_pocket_clearance
    ly = servo_len + 2 * servo_pocket_clearance
    yc = cy + (servo_body_y0 + servo_body_y1) / 2 - servo_axis_y
    return _box(cx - lx / 2, cx + lx / 2, yc - ly / 2, yc + ly / 2, z0, z1)


@lru_cache(maxsize=None)
def base_zero():
    body = _cyl_z(0, 0, 0, Z_RIM, 2 * base_r)
    body = body - _cyl_z(0, 0, -1, Z_FLOOR_TOP - plate_thick, 2 * well_r)
    body = body - _cyl_z(0, 0, Z_FLOOR_TOP, Z_RIM + 1, 2 * well_r)
    ring = _cyl_z(0, 0, Z_RIM - 0.01, Z_SEAT, 2 * ring_r_out) - _cyl_z(0, 0, Z_RIM - 1, Z_SEAT + 1, 2 * ring_r_in)
    boss = _cyl_z(0, 0, base_boss_z0, Z_FLOOR_TOP - plate_thick + 0.01, base_boss_d)
    thrust = _cyl_z(0, 0, Z_FLOOR_TOP - 0.01, Z_PAN_GEAR - thrust_gap, 2 * thrust_ring_r1) - _cyl_z(0, 0, Z_FLOOR_TOP - 1, Z_PAN_GEAR, 2 * thrust_ring_r0)
    body = body + ring + boss + thrust
    # tube groove in the ring top
    body = body - (_cyl_z(0, 0, Z_TUBE0, Z_SEAT + 1, 2 * groove_r1) - _cyl_z(0, 0, Z_TUBE0 - 1, Z_SEAT + 2, 2 * groove_r0))
    body = body - _cyl_z(0, 0, Z_JOURNAL_BOTTOM, Z_FLOOR_TOP + 1, journal_od + 0.3)
    body = body - _cyl_z(0, 0, base_boss_z0 - 1, Z_FLOOR_TOP + 1, journal_bore)
    body = body - _servo_pocket_xy(pan_pinion_xy[0], pan_pinion_xy[1], Z_FLOOR_TOP - plate_thick - 1, Z_FLOOR_TOP + 1)
    return body


@lru_cache(maxsize=None)
def cradle_zero():
    """Board holder at fixed tilt 0: back plate, side walls, bottom/top rails."""
    back = _box(cradle_x0, pcb_x, -cradle_outer_y, cradle_outer_y, Z_CRADLE0, Z_CRADLE1)
    side_l = _box(cradle_x0, cradle_x1, -cradle_outer_y, -cradle_inner_y, Z_CRADLE0, Z_CRADLE1)
    side_r = _box(cradle_x0, cradle_x1, cradle_inner_y, cradle_outer_y, Z_CRADLE0, Z_CRADLE1)
    rail_b = _box(cradle_x0, pcb_x + rail_depth, -cradle_outer_y, cradle_outer_y, Z_CRADLE0, Z_CRADLE0 + wall_mm)
    rail_t = _box(cradle_x0, pcb_x + rail_depth, -cradle_outer_y, cradle_outer_y, Z_CRADLE1 - wall_mm, Z_CRADLE1)
    c = back + side_l + side_r + rail_b + rail_t
    c = c - _box(pcb_x - 0.5, pcb_x + rail_depth + 1, -usb_w / 2 - 0.5, usb_w / 2 + 0.5, Z_CRADLE0 - 1, Z_CRADLE0 + wall_mm + 1)
    return c


@lru_cache(maxsize=None)
def pod_zero():
    """Cradle (at fixed_tilt_deg) fused with the mast down to the pan gear top."""
    c = cradle_zero().rotate(TILT_AXIS, fixed_tilt_deg)
    mast = _box(cradle_x0, pcb_x, -mast_y, mast_y, Z_GEAR_TOP, Z_BOARD_CENTER)
    foot = _box(cradle_x0 - 1.0, pcb_x + 6.0, -mast_y, mast_y, Z_GEAR_TOP, Z_GEAR_TOP + 3.0)
    p = c + mast + foot
    return p


@lru_cache(maxsize=None)
def tube_zero():
    return _cyl_z(0, 0, Z_TUBE0, Z_TUBE1, tube_od) - _cyl_z(0, 0, Z_TUBE0 - 1, Z_TUBE1 + 1, tube_id)


@lru_cache(maxsize=None)
def cap_zero():
    plug = _cyl_z(0, 0, Z_TUBE1 - cap_plug_depth, Z_TUBE1 + 0.01, tube_id - tube_fit)
    top = _cyl_z(0, 0, Z_TUBE1, Z_TUBE1 + cap_top, tube_od)
    return plug + top


# ----------------------------------------------------------------- build
def spin_angles(pan_deg: float, tilt_deg: float = 0.0):
    pan_gear = pan_mesh_dir_deg
    pan_pinion = pan_mesh_dir_deg + 180.0 + 180.0 / pan_pinion_teeth - (pan_gear_teeth / pan_pinion_teeth) * pan_deg
    return pan_gear, pan_pinion, 0.0


def build_parts(pan_deg: float = 0.0, tilt_deg: float = 0.0) -> dict:
    pan_gear_a, pan_pinion_a, _ = spin_angles(pan_deg)
    base = base_zero()
    pan_servo = servo_zero().moved(Location(PAN_SERVO_PLANE))
    pan_pinion = Pos(pan_pinion_xy[0], pan_pinion_xy[1], Z_PAN_GEAR) * pan_pinion_zero().rotate(Axis.Z, pan_pinion_a)
    tube = tube_zero()
    cap = cap_zero()

    pan_gear = Pos(0, 0, Z_PAN_GEAR) * pan_gear_zero().rotate(Axis.Z, pan_gear_a)
    pod = pod_zero()
    camera = xiao_zero().moved(Location(BOARD_PLANE)).rotate(TILT_AXIS, fixed_tilt_deg)

    yoke_group = {"pan_gear": pan_gear, "pod": pod, "camera": camera}
    yoke_group = {k: v.rotate(PAN_AXIS, pan_deg) for k, v in yoke_group.items()}
    base_group = {"base": base, "pan_servo": pan_servo, "pan_pinion": pan_pinion, "tube": tube, "cap": cap}
    return {"base_group": base_group, "yoke_group": yoke_group}


def build_assembly(pan_deg: float = 0.0, tilt_deg: float = 0.0):
    from cadgen.assembly import AssemblyHelper, label_shape

    def labeled(group):
        out = []
        for n, s in group.items():
            label_shape(s, n)
            out.append(s)
        return out

    groups = build_parts(pan_deg)
    asm = AssemblyHelper("xiao_pantilt")
    yoke_mod = asm.compound(labeled(groups["yoke_group"]), label="pod_group")
    base_mod = asm.compound(labeled(groups["base_group"]), label="base_group")
    asm.children.extend([base_mod, yoke_mod])
    asm.revolute_frame(base_mod, "pan_axis", PAN_AXIS)
    return asm.build()
