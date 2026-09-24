"""xiao_pantilt geometry library — v6 DIRECT-DRIVE pan-only tube + BATTERY BAY (2026-09-09).

One 9 g servo on the pan axis under the base top plate (classic 23 x 12.2
pocket, flange under the plate); the camera pod's foot sits on the servo boss
with a socket over the spline. No gears, no well, no journal. A 2" clear
acrylic tube drops into a groove in the base top and a printed cap plugs it.

Cable: the USB-C plug is on the pan axis, so the cable exits sideways (a
right-angle plug, 10 mm under the board) and drops through a hole in the base
top beside the servo body; the service loop lives in the hollow base.

Battery (v6): a 503035 1S pouch lies flat in a ribbed pocket on a snap-in
bottom lid, under the servo. The cell wires to the XIAO's BAT pads through the
pan joint (BAT+, GND) plus the servo signal; the servo runs straight off the
cell (bench-tested floor 3.5 V, see sarg). No boost, no external charger.

World frame: origin on the pan axis at the base bottom, Z up, +X = look
direction at pan 0; pan about +Z, +pan turns the camera toward +Y.
"""

from __future__ import annotations

import math
import os
from functools import lru_cache
from pathlib import Path

from build123d import Align, Axis, Box, Cylinder, Location, Plane, Pos
from cadgen.step_scene import import_step

HERE = Path(__file__).resolve().parent
REF = HERE.parent.parent / "ref"
XIAO_STEP = REF / "xiao" / "amz-xiao-esp32s3-sense.step"
SERVO_STEP = REF / "mg90s" / "amz-mg90s-micro-servo.step"

HAS_TILT = False

# ----------------------------------------------------------------- parameters
gear_backlash_mm = 0.0                           # no gears (kept for sweep.py compatibility)
pan_min_deg, pan_max_deg = -90.0, 90.0           # direct drive: pan = servo angle
fixed_tilt_deg = float(os.environ.get("PANTILT_FIXED_TILT", "0"))   # + = look up

wall_mm = 2.0
pocket_clearance_mm = 0.25
servo_pocket_clearance = 0.2
usb_plug_space_mm = 10.0         # right-angle USB-C plug under the board (straight plug needs 13-15)

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
tube_od, tube_id, tube_len = 50.8, 44.5, 55.0

# 1S LiPo pouch 503035 (5 x 30 x 35, 500 mAh) - envelope, caliper the real cell
bat_t, bat_w, bat_l = 5.0, 30.0, 35.0
bat_clear = 0.25
lid_t = 1.5                      # snap-in bottom lid
bay_rib_w, bay_rib_h = 1.5, 3.0  # ribs on the lid that locate the pouch
bat_to_servo_clear = 1.0
tube_fit = 0.2
cap_plug_depth, cap_top = 3.0, 2.0

# ------------------------------------------------------------ derived layout
plate_thick = 4.0                                        # base top plate (groove needs 2 under it)
Z_BAT0 = lid_t                                           # pouch rests on the lid
Z_BAT1 = Z_BAT0 + bat_t
pan_servo_z0 = Z_BAT1 + bat_clear + bat_to_servo_clear   # 7.75: servo bottom above the pouch
Z_TOP = pan_servo_z0 + servo_flange_z1 + plate_thick     # 23.4: base top face (flange under it)
Z_BOSS_TOP = pan_servo_z0 + servo_boss_top_z             # 27.9
Z_SPLINE_TOP = pan_servo_z0 + servo_spline_top_z         # 30.9
foot_thick = 4.0
foot_d = 20.0
Z_FOOT0, Z_FOOT1 = Z_BOSS_TOP, Z_BOSS_TOP + foot_thick   # 27.9 .. 31.9
Z_SEAT = Z_TOP
groove_depth = 2.0
groove_r0 = tube_id / 2 - tube_fit / 2                   # 22.15
groove_r1 = tube_od / 2 + tube_fit / 2                   # 25.5
Z_TUBE0 = Z_SEAT - groove_depth                          # 21.4
Z_TUBE1 = Z_TUBE0 + tube_len                             # 76.4
base_wall = 2.0
base_r = groove_r1 + base_wall                           # 27.5 -> Ø55
hollow_r = groove_r1                                     # hollow under the plate = groove outer radius
cable_hole_d = 5.0                                       # 3 wires now, not a USB cable
cable_hole_xy = (0.0, 16.5)                              # beside the servo (ear reaches Y 11.1)
PAN_AXIS = Axis((0, 0, 0), (0, 0, 1))
pan_pinion_xy = (0.0, 0.0)                               # servo axis = pan axis
well_r = hollow_r                                        # names kept for sweep.py
Z_RIM = Z_TOP
ring_r_in = groove_r0

# camera pod: USB-C plug centred on the pan axis
pcb_x = -usb_center_bz                                  # -2.36
cradle_x0 = pcb_x - wall_mm                             # -4.36
cradle_x1 = pcb_x + 15.0                                # 12.64
rail_depth = 3.0
cradle_inner_y = board_w / 2 + pocket_clearance_mm
cradle_outer_y = cradle_inner_y + wall_mm               # 11.15
Z_CRADLE0 = Z_FOOT1 + usb_plug_space_mm                 # 41.9: bottom rail
Z_BOARD0 = Z_CRADLE0 + wall_mm + pocket_clearance_mm    # 44.15
Z_CRADLE1 = Z_BOARD0 + board_len + 0.5 + wall_mm        # 67.6
Z_BOARD_CENTER = Z_BOARD0 + board_len / 2
BOARD_PLANE = Plane(origin=(pcb_x, board_w / 2, Z_BOARD0), x_dir=(0, 0, 1), z_dir=(1, 0, 0))
TILT_AXIS = Axis((pcb_x + 7.0, 0, Z_BOARD_CENTER), (0, -1, 0))
mast_y = 8.0
pod_r = math.hypot(cradle_x1, cradle_outer_y)           # 16.8


# ------------------------------------------------------------------- helpers
def _cyl(r, h):
    return Cylinder(r, h, align=(Align.CENTER, Align.CENTER, Align.MIN))


def spline_socket():
    """Round socket over the 4.7 spline, 3 deep. Print as a servo-horn pocket."""
    return Pos(0, 0, -1) * _cyl((servo_spline_d + 0.1) / 2, (servo_spline_top_z - servo_boss_top_z) + 1)


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


PAN_SERVO_PLANE = _servo_plane((0.0, 0.0, Z_TOP - plate_thick), (1, 0, 0), (0, 0, 1))


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
    """Ø55 puck: hollow under a 4 mm top plate, servo pocket on the axis, tube groove,
    cable hole beside the servo."""
    body = _cyl_z(0, 0, 0, Z_TOP, 2 * base_r)
    body = body - _cyl_z(0, 0, -1, Z_TOP - plate_thick, 2 * hollow_r)
    body = body - (_cyl_z(0, 0, Z_TUBE0, Z_TOP + 1, 2 * groove_r1) - _cyl_z(0, 0, Z_TUBE0 - 1, Z_TOP + 2, 2 * groove_r0))
    body = body - _servo_pocket_xy(0.0, 0.0, Z_TOP - plate_thick - 1, Z_TOP + 1)
    body = body - _cyl_z(cable_hole_xy[0], cable_hole_xy[1], Z_TOP - plate_thick - 1, Z_TOP + 1, cable_hole_d)
    return body


@lru_cache(maxsize=None)
def lid_zero():
    """Bottom lid: disc inside the hollow + a ribbed frame that locates the pouch."""
    disc = _cyl_z(0, 0, 0, lid_t, 2 * (hollow_r - 0.2))
    ox, oy = bat_w / 2 + bat_clear, bat_l / 2 + bat_clear
    frame = _box(-ox - bay_rib_w, ox + bay_rib_w, -oy - bay_rib_w, oy + bay_rib_w, lid_t - 0.01, lid_t + bay_rib_h)
    frame = frame - _box(-ox, ox, -oy, oy, lid_t - 1, lid_t + bay_rib_h + 1)
    frame = frame & _cyl_z(0, 0, lid_t - 1, lid_t + bay_rib_h + 1, 2 * (hollow_r - 0.2))   # clip corners to the disc
    return disc + frame


@lru_cache(maxsize=None)
def battery_zero():
    return _box(-bat_w / 2, bat_w / 2, -bat_l / 2, bat_l / 2, Z_BAT0, Z_BAT1)


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
    """Cradle (at fixed_tilt_deg) + mast + foot disc with the spline socket."""
    c = cradle_zero().rotate(TILT_AXIS, fixed_tilt_deg)
    mast = _box(cradle_x0, pcb_x, -mast_y, mast_y, Z_FOOT1 - 0.01, Z_BOARD_CENTER)
    foot = _cyl_z(0, 0, Z_FOOT0, Z_FOOT1, foot_d) - (Pos(0, 0, Z_FOOT0) * spline_socket())
    # cable slot in the foot toward the base hole side (+Y)
    slot = _box(-4.5, 4.5, 6.0, foot_d / 2 + 1, Z_FOOT0 - 1, Z_FOOT1 + 1)
    return c + mast + (foot - slot)


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
    return 0.0, pan_deg, 0.0


def build_parts(pan_deg: float = 0.0, tilt_deg: float = 0.0) -> dict:
    base = base_zero()
    pan_servo = servo_zero().moved(Location(PAN_SERVO_PLANE))
    tube = tube_zero()
    cap = cap_zero()
    pod = pod_zero()
    camera = xiao_zero().moved(Location(BOARD_PLANE)).rotate(TILT_AXIS, fixed_tilt_deg)
    yoke_group = {"pod": pod, "camera": camera}
    yoke_group = {k: v.rotate(PAN_AXIS, pan_deg) for k, v in yoke_group.items()}
    base_group = {"base": base, "pan_servo": pan_servo, "tube": tube, "cap": cap,
                  "base_lid": lid_zero(), "battery_503035": battery_zero()}
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
