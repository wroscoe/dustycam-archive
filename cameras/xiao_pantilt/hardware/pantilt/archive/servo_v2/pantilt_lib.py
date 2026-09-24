"""xiao_pantilt geometry library — SERVO version (v2, 2026-09-08).

Geared pan-tilt head for the Seeed XIAO ESP32S3 Sense driven by two 9 g micro
servos (MG90S / SG90 body, sarg `mg90s-micro-servo`). See ../../SPEC.md and
README.md. Every body is built in WORLD coordinates at the zero pose, then
posed by explicit parameterised rotations. `build_parts()` is shared by the
STEP generator, the interference sweep and mirrored by the viewer sidecar.

Layout (v2)
  - Pan servo hangs under the base top plate through the classic 23 x 12.2
    pocket, flange against the plate underside; spline + pinion above the plate.
  - Tilt servo lies horizontally INSIDE the yoke fork, below the cradle's
    sweep, flange against the left arm's inner face, body through a pocket in
    the arm; spline + pinion on the OUTSIDE of the arm.
  - Tilt sector rides on a stub shaft that is part of the cradle and passes
    through the left arm, so sector + pinion are outside and a cap covers them.
  - Servos are positional (~180 deg), so both stages are speed-ups or mild
    reductions: pan 32T -> 28T (servo +-78 for pan +-90), tilt 18T -> 28T
    (servo travel 140 deg for tilt -30..+60; servo neutral = tilt +15).

World frame
  origin  pan axis at the base bottom face, Z up
  +X      camera look direction at pan=0, tilt=0
  tilt    rotation about the -Y axis through (0, *, Z_TILT); +tilt looks UP
  pan     rotation about +Z; +pan turns the camera toward +Y
"""

from __future__ import annotations

import math
import os
from functools import lru_cache
from pathlib import Path

from build123d import Align, Axis, Box, Cylinder, Location, Plane, Polygon, Pos, extrude
from cadgen.step_scene import import_step

HERE = Path(__file__).resolve().parent
REF = HERE.parent.parent / "ref"
XIAO_STEP = REF / "xiao" / "amz-xiao-esp32s3-sense.step"
SERVO_STEP = REF / "mg90s" / "amz-mg90s-micro-servo.step"

# ----------------------------------------------------------------- parameters
# gears (module 1 spur, printed)
gear_module_mm = 1.0
pressure_angle_deg = 20.0
gear_face_mm = 5.0
gear_backlash_mm = float(os.environ.get("PANTILT_BACKLASH", "0.15"))   # added to centre distance
pan_pinion_teeth, pan_gear_teeth = 30, 26        # servo -> yoke, ratio 0.867 (servo +-78 for pan +-90)
tilt_pinion_teeth, tilt_gear_teeth = 18, 28      # servo -> cradle, ratio 1.556
tilt_sector_margin_deg = 5.0

# motion
pan_min_deg, pan_max_deg = -90.0, 90.0
tilt_min_deg, tilt_max_deg = -30.0, 60.0

# structure
wall_mm = 2.0
arm_gap_mm = 1.0                 # cradle wall to arm inner face
pocket_clearance_mm = 0.25       # board edge to cradle rail
servo_pocket_clearance = 0.2     # per side, classic 23.0 x 12.2 pocket

# 9 g servo, its own frame (sarg mg90s-micro-servo, vendor STEP, verified):
# origin plan bottom-left incl. ears, Z=0 body bottom; body y 4.7..27.3, x 0..11.8;
# flange plate z 15.9..18.4; body top z 22.7; boss to z 26.9; spline r 2.35 z 26.9..29.9
# at (x 5.9, y 21.3); ear holes (5.9, 2.4) / (5.9, 29.6) dia 2.0.
servo_w, servo_len, servo_ears_len = 11.8, 22.6, 32.4
servo_body_y0, servo_body_y1 = 4.7, 27.3
servo_flange_z0, servo_flange_z1 = 15.9, 18.4
servo_body_top_z, servo_boss_top_z, servo_spline_top_z = 22.7, 26.9, 29.9
servo_axis_x, servo_axis_y = 5.9, 21.3
servo_spline_d = 4.7
servo_ear_extent = (0.0, 32.4)

# XIAO ESP32S3 Sense, board frame facts (sarg vendor STEP, measured 2026-09-08)
board_len, board_w = 20.95, 17.78
lens_bx, lens_by = 3.53, 8.25
usb_w = 8.94

# ------------------------------------------------------------ derived layout
def _pitch_r(n):
    return gear_module_mm * n / 2.0

pan_center_dist = _pitch_r(pan_pinion_teeth) + _pitch_r(pan_gear_teeth) + gear_backlash_mm      # 30.15
tilt_center_dist = _pitch_r(tilt_pinion_teeth) + _pitch_r(tilt_gear_teeth) + gear_backlash_mm   # 23.15
tilt_gear_tip_r = _pitch_r(tilt_gear_teeth) + gear_module_mm                                     # 15
tilt_pinion_tip_r = _pitch_r(tilt_pinion_teeth) + gear_module_mm                                 # 10
pan_pinion_tip_r = _pitch_r(pan_pinion_teeth) + gear_module_mm                                   # 17

# Z stack. Servo flange sits against the underside of a 3 mm plate; the gear
# band starts at the boss top (spline bottom).
plate_thick = 3.0
gear_band_above_plate = servo_boss_top_z - servo_flange_z1 - plate_thick        # 5.5
Z_BASE_TOP = 26.0
pan_servo_z0 = Z_BASE_TOP - plate_thick - servo_flange_z1                       # 4.6
Z_PAN_GEAR = Z_BASE_TOP + gear_band_above_plate                                 # 31.5
pan_gear_thick = gear_face_mm + 0.5
Z_PLATE = Z_PAN_GEAR + pan_gear_thick                                           # 37
Z_PLATE_TOP = Z_PLATE + plate_thick                                             # 40
journal_od, journal_bore, journal_len = 14.0, 7.0, 8.0
Z_JOURNAL_BOTTOM = Z_BASE_TOP - journal_len                                     # 18

# tilt stage: pinion straight below the tilt axis (270 deg); servo horizontal in
# the fork. Z_TILT chosen so the gear cover bottom clears the pan pinion top.
tilt_mesh_dir_deg = 270.0
cover_wall = 2.0
cover_cavity_margin = 1.0
Z_TILT = 74.0
Z_TILT_SHAFT = Z_TILT - tilt_center_dist                                        # 50.85
Z_ARM_TOP = Z_TILT + 6.0
sector_arc = (tilt_mesh_dir_deg - tilt_max_deg - tilt_sector_margin_deg,        # 205
              tilt_mesh_dir_deg - tilt_min_deg + tilt_sector_margin_deg)        # 305

# Y stack
cradle_inner_y = board_w / 2 + pocket_clearance_mm      # 9.15
cradle_outer_y = cradle_inner_y + wall_mm               # 11.15
arm_y0 = cradle_outer_y + arm_gap_mm                    # 12.15 inner face
arm_thick = plate_thick
arm_y1 = arm_y0 + arm_thick                             # 15.15 outer face
# tilt servo: flange top (z 18.4) at the arm inner face, +z -> -Y
tilt_servo_y_of = lambda z: -arm_y0 - (z - servo_flange_z1)
gear_y0 = tilt_servo_y_of(servo_boss_top_z)             # -20.65 (band start, toward -Y)
gear_y1 = gear_y0 - gear_face_mm                        # -25.65
cover_y_in = -arm_y1                                    # -15.15
cover_y_out = gear_y1 - cover_cavity_margin - cover_wall  # -28.65
TILT_PLANE = Plane(origin=(0, gear_y0, Z_TILT), x_dir=(1, 0, 0), z_dir=(0, -1, 0))
TILT_AXIS = Axis((0, 0, Z_TILT), (0, -1, 0))
PAN_AXIS = Axis((0, 0, 0), (0, 0, 1))
pivot_shaft_d = 5.0
pivot_bore_arm = 5.3

# camera / cradle
pcb_x = -12.0
BOARD_PLANE = Plane(origin=(pcb_x, board_w / 2, Z_TILT - lens_bx), x_dir=(0, 0, 1), z_dir=(1, 0, 0))
cradle_x0 = pcb_x - wall_mm
cradle_x1 = 3.0
rail_depth = 3.0
cradle_z0 = Z_TILT - lens_bx - pocket_clearance_mm - wall_mm
cradle_z1 = Z_TILT - lens_bx + board_len + 0.5 + wall_mm
hub_d = 10.0

# yoke plate / arms
plate_x0, plate_x1 = -23.0, 6.0
tilt_servo_x_of = lambda y: y - servo_axis_y            # servo y -> world X (shaft at X=0)
ear_tab_x1 = tilt_servo_x_of(servo_ear_extent[1]) + 1.5                 # 12.6
pocket_x0 = tilt_servo_x_of(servo_body_y0) - servo_pocket_clearance     # -16.8
pocket_x1 = tilt_servo_x_of(servo_body_y1) + servo_pocket_clearance     # 6.2
pocket_z0 = Z_TILT_SHAFT - servo_w / 2 - servo_pocket_clearance
pocket_z1 = Z_TILT_SHAFT + servo_w / 2 + servo_pocket_clearance
ear_tab_z1 = pocket_z1 + 3.0

# base
base_d, base_h = 90.0, Z_BASE_TOP      # pan servo ears reach r 40.2; pinion tip r 44.15
base_plate_thick = plate_thick
base_boss_d = 22.0
base_boss_z0 = 12.0
pan_pinion_xy = (-pan_center_dist, 0.0)
pan_mesh_dir_deg = 180.0


# ------------------------------------------------------------------- gears
def involute_gear_sketch(n_teeth: int, module: float = gear_module_mm,
                         pa_deg: float = pressure_angle_deg, steps: int = 8) -> Polygon:
    """Closed polygon of an external spur gear, tooth 0 centred on +X."""
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
    """Blind socket for the servo spline: round, 0.1 over the 4.7 spline OD.
    The real part is splined (21T); modeled round."""
    return Pos(0, 0, -1) * _cyl((servo_spline_d + 0.1) / 2, (servo_spline_top_z - servo_boss_top_z) + 1)


@lru_cache(maxsize=None)
def pan_pinion_zero():
    return extrude(involute_gear_sketch(pan_pinion_teeth), amount=gear_face_mm) - spline_socket()


@lru_cache(maxsize=None)
def tilt_pinion_zero():
    return extrude(involute_gear_sketch(tilt_pinion_teeth), amount=gear_face_mm) - spline_socket()


@lru_cache(maxsize=None)
def pan_gear_zero():
    g = extrude(involute_gear_sketch(pan_gear_teeth), amount=pan_gear_thick)
    return g - Pos(0, 0, -1) * _cyl((journal_od + 0.3) / 2, pan_gear_thick + 2)


@lru_cache(maxsize=None)
def sector_zero():
    """28T sector + hub in TILT_PLANE local coords; a tooth sits on the line of
    centres at tilt 0. Rides on the cradle's stub shaft (round bore here; print
    with a D)."""
    g = extrude(involute_gear_sketch(tilt_gear_teeth), amount=gear_face_mm)
    g = g.rotate(Axis.Z, tilt_mesh_dir_deg)
    a0, a1 = sector_arc
    wedge_pts = [(0.0, 0.0)] + [
        (30 * math.cos(math.radians(a)), 30 * math.sin(math.radians(a)))
        for a in [a0 + (a1 - a0) * k / 20 for k in range(21)]
    ]
    wedge = extrude(Polygon(*wedge_pts, align=None), amount=gear_face_mm)
    hub = _cyl(hub_d / 2, gear_face_mm)
    bore = Pos(0, 0, -1) * _cyl((pivot_shaft_d + 0.1) / 2, gear_face_mm + 2)
    return (g & wedge) + hub - bore


# ----------------------------------------------------------- imported parts
@lru_cache(maxsize=None)
def servo_zero():
    # the vendor STEP is a 1-solid compound with its own label; take the solid so
    # our occurrence label wins
    return import_step(str(SERVO_STEP)).solids()[0]


@lru_cache(maxsize=None)
def xiao_zero():
    return import_step(str(XIAO_STEP))


def _servo_plane(axis_point_world, x_dir, z_dir):
    """Plane placing the servo so that its (axis_x, axis_y, flange_top) point
    lands on axis_point_world, with servo +z along z_dir and +x along x_dir."""
    pl = Plane(origin=(0, 0, 0), x_dir=x_dir, z_dir=z_dir)
    xd, yd, zd = pl.x_dir.to_tuple(), pl.y_dir.to_tuple(), pl.z_dir.to_tuple()
    origin = tuple(
        axis_point_world[i] - servo_axis_x * xd[i] - servo_axis_y * yd[i] - servo_flange_z1 * zd[i]
        for i in range(3)
    )
    return Plane(origin=origin, x_dir=x_dir, z_dir=z_dir)


# pan servo: +z up, body along Y (servo y -> +Y), flange top at the plate underside
PAN_SERVO_PLANE = _servo_plane((pan_pinion_xy[0], pan_pinion_xy[1], Z_BASE_TOP - plate_thick), (1, 0, 0), (0, 0, 1))
# tilt servo: +z -> -Y (shaft out through the left arm), servo y -> +X, servo x -> -Z
TILT_SERVO_PLANE = _servo_plane((0.0, -arm_y0, Z_TILT_SHAFT), (0, 0, -1), (0, -1, 0))
TILT_PINION_WORLD = (0.0, 0.0, Z_TILT_SHAFT)


# ------------------------------------------------------------ structure
def _box(x0, x1, y0, y1, z0, z1):
    return Pos(x0, y0, z0) * Box(x1 - x0, y1 - y0, z1 - z0, align=(Align.MIN, Align.MIN, Align.MIN))


def _cyl_z(cx, cy, z0, z1, d):
    return Pos(cx, cy, z0) * _cyl(d / 2, z1 - z0)


def _cyl_y(cx, cz, y0, y1, d):
    c = _cyl(d / 2, y1 - y0)
    return Location(Plane(origin=(cx, y0, cz), x_dir=(1, 0, 0), z_dir=(0, 1, 0))) * c


def _servo_pocket_xy(cx, cy, z0, z1):
    """Classic 23.0 x 12.2 pocket, long axis along Y, for a servo with +z up."""
    lx = servo_w + 2 * servo_pocket_clearance
    ly = servo_len + 2 * servo_pocket_clearance
    # body centre in y is (4.7+27.3)/2 = 16 -> offset from the axis (21.3) by -5.3
    yc = cy + (servo_body_y0 + servo_body_y1) / 2 - servo_axis_y
    return _box(cx - lx / 2, cx + lx / 2, yc - ly / 2, yc + ly / 2, z0, z1)


@lru_cache(maxsize=None)
def base_zero():
    body = _cyl_z(0, 0, 0, base_h, base_d)
    body = body - _cyl_z(0, 0, -1, base_h - base_plate_thick, base_d - 2 * wall_mm)
    body = body + _cyl_z(0, 0, base_boss_z0, base_h - base_plate_thick + 0.01, base_boss_d)
    body = body - _cyl_z(0, 0, Z_JOURNAL_BOTTOM, base_h + 1, journal_od + 0.3)
    body = body - _cyl_z(0, 0, base_boss_z0 - 1, base_h + 1, journal_bore)
    body = body - _servo_pocket_xy(pan_pinion_xy[0], pan_pinion_xy[1], base_h - base_plate_thick - 1, base_h + 1)
    return body


@lru_cache(maxsize=None)
def yoke_zero():
    plate = _box(plate_x0, plate_x1, -arm_y1, arm_y1, Z_PLATE, Z_PLATE_TOP)
    arm_l = _box(plate_x0, plate_x1, -arm_y1, -arm_y0, Z_PLATE, Z_ARM_TOP)
    arm_r = _box(plate_x0, plate_x1, arm_y0, arm_y1, Z_PLATE, Z_ARM_TOP)
    ear_tab = _box(plate_x1 - 0.01, ear_tab_x1, -arm_y1, -arm_y0, Z_PLATE, ear_tab_z1)
    post = _cyl_z(0, 0, Z_JOURNAL_BOTTOM, Z_PLATE + 0.01, journal_od)
    y = plate + arm_l + arm_r + ear_tab + post
    y = y - _cyl_z(0, 0, Z_JOURNAL_BOTTOM - 1, Z_PLATE_TOP + 1, journal_bore)
    y = y - _cyl_y(0, Z_TILT, -arm_y1 - 1, arm_y1 + 1, pivot_bore_arm)
    # tilt servo pocket through the left arm (body passes, flange inside)
    y = y - _box(pocket_x0, pocket_x1, -arm_y1 - 1, -arm_y0 + 1, pocket_z0, pocket_z1)
    return y


@lru_cache(maxsize=None)
def cradle_zero():
    back = _box(cradle_x0, pcb_x, -cradle_outer_y, cradle_outer_y, cradle_z0, cradle_z1)
    side_l = _box(cradle_x0, cradle_x1, -cradle_outer_y, -cradle_inner_y, cradle_z0, cradle_z1)
    side_r = _box(cradle_x0, cradle_x1, cradle_inner_y, cradle_outer_y, cradle_z0, cradle_z1)
    rail_b = _box(cradle_x0, pcb_x + rail_depth, -cradle_outer_y, cradle_outer_y, cradle_z0, cradle_z0 + wall_mm)
    rail_t = _box(cradle_x0, pcb_x + rail_depth, -cradle_outer_y, cradle_outer_y, cradle_z1 - wall_mm, cradle_z1)
    # stub shafts: left one carries the sector outside the arm, right one is the plain pivot
    shaft_l = _cyl_y(0, Z_TILT, gear_y1 - 0.5, -cradle_outer_y + 0.01, pivot_shaft_d)
    shaft_r = _cyl_y(0, Z_TILT, cradle_outer_y - 0.01, arm_y1 + 0.5, pivot_shaft_d)
    c = back + side_l + side_r + rail_b + rail_t + shaft_l + shaft_r
    c = c - _box(pcb_x - 0.5, pcb_x + rail_depth + 1, -usb_w / 2 - 0.5, usb_w / 2 + 0.5, cradle_z0 - 1, cradle_z0 + wall_mm + 1)
    return c


@lru_cache(maxsize=None)
def cover_zero():
    """Cap over the outside of the left arm enclosing sector + pinion."""
    r_out = tilt_gear_tip_r + cover_cavity_margin
    # the servo body top (z 18.4..22.7) stands 1.3 proud of the arm's outer face, so
    # the cavity must also clear the body outline in X
    x_cav0 = min(-r_out, pocket_x0 - cover_cavity_margin)
    x_cav1 = max(r_out, pocket_x1 + cover_cavity_margin)
    x_half = r_out + cover_wall
    z_lo = Z_TILT_SHAFT - tilt_pinion_tip_r - cover_cavity_margin
    z_hi = Z_TILT + hub_d / 2 + cover_cavity_margin
    outer = _box(x_cav0 - cover_wall, x_cav1 + cover_wall, cover_y_out, cover_y_in, z_lo - cover_wall, z_hi + cover_wall)
    cavity = _box(x_cav0, x_cav1, cover_y_out + cover_wall, cover_y_in + 1, z_lo, z_hi)
    return outer - cavity


# ----------------------------------------------------------------- build
def spin_angles(pan_deg: float, tilt_deg: float):
    """Absolute spin of each gear about its own axis, degrees (local plane sense)."""
    # the pan gear rides with the yoke group, which is rotated by pan_deg as a whole,
    # so its own spin is only the mesh phase (double-rotating it clashes at +-90)
    pan_gear = pan_mesh_dir_deg
    pan_pinion = pan_mesh_dir_deg + 180.0 + 180.0 / pan_pinion_teeth - (pan_gear_teeth / pan_pinion_teeth) * pan_deg
    tilt_pinion = tilt_mesh_dir_deg + 180.0 + 180.0 / tilt_pinion_teeth - (tilt_gear_teeth / tilt_pinion_teeth) * tilt_deg
    return pan_gear, pan_pinion, tilt_pinion


def build_parts(pan_deg: float = 0.0, tilt_deg: float = 0.0) -> dict:
    pan_gear_a, pan_pinion_a, tilt_pinion_a = spin_angles(pan_deg, tilt_deg)
    tilt_loc = Location(TILT_PLANE)

    base = base_zero()
    pan_servo = servo_zero().moved(Location(PAN_SERVO_PLANE))
    pan_pinion = Pos(pan_pinion_xy[0], pan_pinion_xy[1], Z_PAN_GEAR) * pan_pinion_zero().rotate(Axis.Z, pan_pinion_a)

    pan_gear = Pos(0, 0, Z_PAN_GEAR) * pan_gear_zero().rotate(Axis.Z, pan_gear_a)
    yoke = yoke_zero()
    tilt_servo = servo_zero().moved(Location(TILT_SERVO_PLANE))
    tilt_pinion = tilt_loc * (Pos(0, Z_TILT_SHAFT - Z_TILT, 0) * tilt_pinion_zero().rotate(Axis.Z, tilt_pinion_a))
    cover = cover_zero()

    cradle = cradle_zero()
    camera = xiao_zero().moved(Location(BOARD_PLANE))
    sector = tilt_loc * sector_zero()

    tilt_group = {"cradle": cradle, "camera": camera, "tilt_sector": sector}
    tilt_group = {k: v.rotate(TILT_AXIS, tilt_deg) for k, v in tilt_group.items()}
    yoke_group = {"pan_gear": pan_gear, "yoke": yoke, "tilt_servo": tilt_servo, "tilt_pinion": tilt_pinion,
                  "gear_cover": cover}
    yoke_group = {k: v.rotate(PAN_AXIS, pan_deg) for k, v in yoke_group.items()}
    tilt_group = {k: v.rotate(PAN_AXIS, pan_deg) for k, v in tilt_group.items()}
    base_group = {"base": base, "pan_servo": pan_servo, "pan_pinion": pan_pinion}
    return {"base_group": base_group, "yoke_group": yoke_group, "tilt_group": tilt_group}


def build_assembly(pan_deg: float = 0.0, tilt_deg: float = 0.0):
    from cadgen.assembly import AssemblyHelper, label_shape

    def labeled(group):
        out = []
        for n, s in group.items():
            label_shape(s, n)
            out.append(s)
        return out

    groups = build_parts(pan_deg, tilt_deg)
    asm = AssemblyHelper("xiao_pantilt")
    tilt_mod = asm.compound(labeled(groups["tilt_group"]), label="tilt_group")
    yoke_mod = asm.compound(labeled(groups["yoke_group"]) + [tilt_mod], label="yoke_group")
    base_mod = asm.compound(labeled(groups["base_group"]), label="base_group")
    asm.children.extend([base_mod, yoke_mod])
    asm.revolute_frame(base_mod, "pan_axis", PAN_AXIS)
    asm.revolute_frame(yoke_mod, "tilt_axis", TILT_AXIS)
    return asm.build()
