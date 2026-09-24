"""xiao_pantilt geometry library.

Geared pan-tilt head for the Seeed XIAO ESP32S3 Sense driven by two N20
gearmotors. See ../../SPEC.md. Every body is built in WORLD coordinates at the
zero pose, then posed by explicit, parameterised rotations (pan about world Z,
tilt about the -Y axis through the lens). `build()` is shared by the STEP
generator, the interference sweep and the viewer sidecar (which mirrors the
same axes in JS).

World frame
  origin  pan axis at the base bottom face, Z up
  +X      camera look direction at pan=0, tilt=0
  tilt    rotation about the -Y axis through (0, *, Z_TILT); +tilt looks UP
  pan     rotation about +Z; +pan turns the camera toward +Y (counter-clockwise
          seen from above)

Gear planes
  pan gears live in Plane.XY; tilt gears in TILT_PLANE (local x->world X,
  local y->world Z, local z->world -Y) so that a positive local rotation is a
  positive tilt.
"""

from __future__ import annotations

import math
import os
from functools import lru_cache
from pathlib import Path

from build123d import (
    Align, Axis, Box, Cylinder, Location, Plane, Polygon, Pos, extrude,
)
from cadgen.step_scene import import_step

HERE = Path(__file__).resolve().parent
REF = HERE.parent.parent / "ref"
XIAO_STEP = REF / "xiao" / "amz-xiao-esp32s3-sense.step"
N20_STEP = REF / "n20" / "amz-n20-gearmotor.step"

# ----------------------------------------------------------------- parameters
# gears
gear_module_mm = 1.0
pressure_angle_deg = 20.0
gear_face_mm = 5.0
gear_backlash_mm = float(os.environ.get("PANTILT_BACKLASH", "0.15"))   # added to centre distance
pinion_teeth = 12
pan_ratio = 4                    # pan gear = 12 * 4 = 48 T
tilt_ratio = 3                   # tilt sector = 12 * 3 = 36 T
tilt_sector_margin_deg = 5.0

# motion
pan_min_deg, pan_max_deg = -90.0, 90.0
tilt_min_deg, tilt_max_deg = -30.0, 60.0

# structure
wall_mm = 2.0
tilt_arm_clearance_mm = 1.0      # gap between sector/hub and the yoke arms
pocket_clearance_mm = 0.25       # board edge to cradle rail

# N20 envelope (sarg n20-gearmotor, envelope grade - caliper before printing)
n20_face_w, n20_face_h = 12.0, 10.0
n20_gearbox_l, n20_body_l, n20_shaft_d, n20_shaft_l = 9.0, 24.0, 3.0, 10.0
n20_shaft_flat_across = 2.5
n20_axis_y, n20_axis_z = 6.0, 5.0   # shaft axis in the motor's own frame
saddle_clearance = 0.1

# XIAO ESP32S3 Sense, board frame facts (sarg vendor STEP, measured 2026-09-08)
board_len, board_w = 20.95, 17.78          # bx 0..20.95 (USB at bx=0), by 0..17.78
lens_bx, lens_by = 3.53, 8.25              # lens barrel centre in board XY
lens_top_bz = 13.86
usb_w, usb_h_top_bz, usb_overhang = 8.94, 4.46, 1.53

# ------------------------------------------------------------ derived layout
def _pitch_r(n):
    return gear_module_mm * n / 2.0

pan_gear_teeth = pinion_teeth * pan_ratio
tilt_gear_teeth = pinion_teeth * tilt_ratio
pan_center_dist = _pitch_r(pinion_teeth) + _pitch_r(pan_gear_teeth) + gear_backlash_mm
tilt_center_dist = _pitch_r(pinion_teeth) + _pitch_r(tilt_gear_teeth) + gear_backlash_mm
tilt_gear_tip_r = _pitch_r(tilt_gear_teeth) + gear_module_mm

# Z stack
Z_BASE_TOP = 28.0                              # base height; pan motor body needs 24 + 0.5 floor
Z_PAN_GEAR = Z_BASE_TOP + 1.5                  # bottom of pan gear + pinion band
pan_gear_thick = gear_face_mm + 0.5            # 0.5 taller than pinion so the
Z_PLATE = Z_PAN_GEAR + pan_gear_thick          # pinion never touches the plate
plate_thick = 3.0
Z_PLATE_TOP = Z_PLATE + plate_thick            # 37
Z_TILT = Z_PLATE_TOP + 23.0                    # 60: sector tip r 19 + 4 clearance
Z_ARM_TOP = Z_TILT + 6.0
journal_od, journal_bore, journal_len = 16.0, 8.0, 8.0
Z_JOURNAL_BOTTOM = Z_BASE_TOP - journal_len     # 19

# pan stage: pinion behind the axis (-X). The motor face sits 3.5 below the
# base top so the 10 mm shaft ends flush with the pinion top: the yoke plate
# corner sweeps radius 35 and would otherwise hit the shaft tip (sweep finding).
pan_pinion_xy = (-pan_center_dist, 0.0)
pan_motor_face_z = Z_BASE_TOP - (n20_shaft_l - (Z_PAN_GEAR + gear_face_mm - Z_BASE_TOP))   # 23.5
pan_mesh_dir_deg = 180.0

# tilt stage: pinion direction from the tilt axis, in the tilt plane
tilt_mesh_dir_deg = 215.0
tilt_pinion_local = (
    tilt_center_dist * math.cos(math.radians(tilt_mesh_dir_deg)),
    tilt_center_dist * math.sin(math.radians(tilt_mesh_dir_deg)),
)
# sector arc in the cradle frame at tilt 0
sector_arc = (
    tilt_mesh_dir_deg - tilt_max_deg - tilt_sector_margin_deg,   # 150
    tilt_mesh_dir_deg - tilt_min_deg + tilt_sector_margin_deg,   # 250
)

# Y stack (symmetric)
cradle_inner_y = board_w / 2 + pocket_clearance_mm      # 9.15
cradle_outer_y = cradle_inner_y + wall_mm               # 11.15
sector_y0, sector_y1 = cradle_outer_y, cradle_outer_y + gear_face_mm   # 11.15..16.15
arm_y0 = sector_y1 + tilt_arm_clearance_mm              # 17.15
arm_thick = 3.0
arm_y1 = arm_y0 + arm_thick                              # 20.15
TILT_PLANE = Plane(origin=(0, -sector_y0, Z_TILT), x_dir=(1, 0, 0), z_dir=(0, -1, 0))
TILT_AXIS = Axis((0, 0, Z_TILT), (0, -1, 0))
PAN_AXIS = Axis((0, 0, 0), (0, 0, 1))

# camera / cradle
pcb_x = -12.0                                   # PCB bottom face plane (world X)
BOARD_PLANE = Plane(origin=(pcb_x, board_w / 2, Z_TILT - lens_bx), x_dir=(0, 0, 1), z_dir=(1, 0, 0))
cradle_x0 = pcb_x - wall_mm                     # -14 back of cradle
cradle_x1 = 3.0                                 # front of side walls
rail_depth = 3.0                                # bottom/top rails wrap PCB edge only
cradle_z0 = Z_TILT - lens_bx - pocket_clearance_mm - wall_mm       # 54.22
cradle_z1 = Z_TILT - lens_bx + board_len + 0.5 + wall_mm           # 79.9 (FPC connector needs 0.5)
hub_d = 10.0
pivot_pin_d = 3.0
pivot_bore_cradle = 3.2
pivot_bore_arm = 3.4

# yoke plate footprint
plate_x0, plate_x1 = -28.5, 6.0

# base
base_d, base_h = 76.0, Z_BASE_TOP
base_plate_thick = 3.0
base_boss_d = 24.0
base_boss_z0 = 12.0


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


def d_bore(height: float):
    """Pinion bore. The real part is a press fit on the N20 D-shaft (3.0, 2.5
    across the flat). Modeled ROUND at 3.0 + 0.05 because the imported motor
    shaft does not spin with the pinion, so a modeled flat would clash at
    every pose except one. The D-flat is a print/slicer detail."""
    bore = Cylinder((n20_shaft_d + 0.05) / 2, height + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return Pos(0, 0, -1) * bore


@lru_cache(maxsize=None)
def pinion_zero():
    g = extrude(involute_gear_sketch(pinion_teeth), amount=gear_face_mm)
    return g - d_bore(gear_face_mm)


@lru_cache(maxsize=None)
def pan_gear_zero():
    g = extrude(involute_gear_sketch(pan_gear_teeth), amount=pan_gear_thick)
    hole = Cylinder((journal_od + 0.3) / 2, pan_gear_thick + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return g - Pos(0, 0, -1) * hole


@lru_cache(maxsize=None)
def sector_zero():
    """36T sector + hub, in TILT_PLANE local coords, tooth 0 on +x, then the
    whole gear rotated so a tooth sits on the line of centres at tilt 0."""
    g = extrude(involute_gear_sketch(tilt_gear_teeth), amount=gear_face_mm)
    g = g.rotate(Axis.Z, tilt_mesh_dir_deg)
    a0, a1 = sector_arc
    wedge_pts = [(0.0, 0.0)] + [
        (30 * math.cos(math.radians(a)), 30 * math.sin(math.radians(a)))
        for a in [a0 + (a1 - a0) * k / 20 for k in range(21)]
    ]
    wedge = extrude(Polygon(*wedge_pts, align=None), amount=gear_face_mm)
    hub = Cylinder(hub_d / 2, gear_face_mm, align=(Align.CENTER, Align.CENTER, Align.MIN))
    bore = Pos(0, 0, -1) * Cylinder(pivot_bore_cradle / 2, gear_face_mm + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return (g & wedge) + hub - bore


@lru_cache(maxsize=None)
def hub_zero():
    hub = Cylinder(hub_d / 2, gear_face_mm, align=(Align.CENTER, Align.CENTER, Align.MIN))
    bore = Pos(0, 0, -1) * Cylinder(pivot_bore_cradle / 2, gear_face_mm + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return hub - bore


# ----------------------------------------------------------- imported parts
@lru_cache(maxsize=None)
def n20_zero():
    return import_step(str(N20_STEP))


@lru_cache(maxsize=None)
def xiao_zero():
    return import_step(str(XIAO_STEP))


# N20 placement planes. Motor frame: X=0 gearbox face, shaft along -X,
# shaft axis at (y=6, z=5).
def _n20_plane(face_point, shaft_dir, z_dir):
    """Plane that puts the motor's shaft axis (at its face) on face_point with
    the shaft pointing along shaft_dir. Motor +X maps to -shaft_dir."""
    x_dir = tuple(-c for c in shaft_dir)
    # world = origin + y*y_dir + z*z_dir for the axis point (0, 6, 5)
    pl = Plane(origin=(0, 0, 0), x_dir=x_dir, z_dir=z_dir)
    y_dir = pl.y_dir.to_tuple()
    origin = tuple(face_point[i] - n20_axis_y * y_dir[i] - n20_axis_z * z_dir[i] for i in range(3))
    return Plane(origin=origin, x_dir=x_dir, z_dir=z_dir)


PAN_MOTOR_PLANE = _n20_plane((pan_pinion_xy[0], pan_pinion_xy[1], pan_motor_face_z), (0, 0, 1), (1, 0, 0))
_tp = tilt_pinion_local
TILT_PINION_WORLD = (_tp[0], 0.0, Z_TILT + _tp[1])
TILT_MOTOR_PLANE = _n20_plane((_tp[0], -arm_y1, Z_TILT + _tp[1]), (0, 1, 0), (1, 0, 0))


# ------------------------------------------------------------ structure
def _box(x0, x1, y0, y1, z0, z1):
    return Pos(x0, y0, z0) * Box(x1 - x0, y1 - y0, z1 - z0, align=(Align.MIN, Align.MIN, Align.MIN))


def _cyl_z(cx, cy, z0, z1, d):
    return Pos(cx, cy, z0) * Cylinder(d / 2, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _cyl_y(cx, cz, y0, y1, d):
    c = Cylinder(d / 2, y1 - y0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return Location(Plane(origin=(cx, y0, cz), x_dir=(1, 0, 0), z_dir=(0, 1, 0))) * c


@lru_cache(maxsize=None)
def base_zero():
    body = _cyl_z(0, 0, 0, base_h, base_d)
    hollow = _cyl_z(0, 0, -1, base_h - base_plate_thick, base_d - 2 * wall_mm)
    body = body - hollow
    boss = _cyl_z(0, 0, base_boss_z0, base_h - base_plate_thick + 0.01, base_boss_d)
    mx, my = pan_pinion_xy
    sw, sh = n20_face_h + 2 * saddle_clearance + 2 * wall_mm, n20_face_w + 2 * saddle_clearance + 2 * wall_mm
    saddle = _box(mx - sw / 2, mx + sw / 2, my - sh / 2, my + sh / 2, base_boss_z0, base_h - base_plate_thick + 0.01)
    body = body + boss + saddle
    body = body - _cyl_z(0, 0, Z_JOURNAL_BOTTOM, base_h + 1, journal_od + 0.3)
    body = body - _cyl_z(0, 0, base_boss_z0 - 1, base_h + 1, journal_bore)
    pw, ph = n20_face_h + 2 * saddle_clearance, n20_face_w + 2 * saddle_clearance
    body = body - _box(mx - pw / 2, mx + pw / 2, my - ph / 2, my + ph / 2, base_boss_z0 - 1, base_h + 1)
    return body


@lru_cache(maxsize=None)
def yoke_zero():
    plate = _box(plate_x0, plate_x1, -arm_y1, arm_y1, Z_PLATE, Z_PLATE_TOP)
    arm_l = _box(plate_x0, plate_x1, -arm_y1, -arm_y0, Z_PLATE, Z_ARM_TOP)
    arm_r = _box(plate_x0, plate_x1, arm_y0, arm_y1, Z_PLATE, Z_ARM_TOP)
    post = _cyl_z(0, 0, Z_JOURNAL_BOTTOM, Z_PLATE + 0.01, journal_od)
    px, _, pz = TILT_PINION_WORLD
    sw = n20_face_h + 2 * saddle_clearance + 2 * wall_mm     # along X (motor z)
    sh = n20_face_w + 2 * saddle_clearance + 2 * wall_mm     # along Z (motor y)
    saddle = _box(px - sw / 2, px + sw / 2, -arm_y1 - n20_gearbox_l, -arm_y1 + 0.01, pz - sh / 2, pz + sh / 2)
    y = plate + arm_l + arm_r + post + saddle
    y = y - _cyl_z(0, 0, Z_JOURNAL_BOTTOM - 1, Z_PLATE_TOP + 1, journal_bore)
    y = y - _cyl_y(0, Z_TILT, -arm_y1 - 1, arm_y1 + 1, pivot_bore_arm)
    pw, ph = n20_face_h + 2 * saddle_clearance, n20_face_w + 2 * saddle_clearance
    y = y - _box(px - pw / 2, px + pw / 2, -arm_y1 - n20_gearbox_l - 1, -arm_y1 + 0.5, pz - ph / 2, pz + ph / 2)
    y = y - _cyl_y(px, pz, -arm_y1 - 1, -arm_y0 + 1, n20_shaft_d + 0.5)
    return y


@lru_cache(maxsize=None)
def cradle_zero():
    back = _box(cradle_x0, pcb_x, -cradle_outer_y, cradle_outer_y, cradle_z0, cradle_z1)
    side_l = _box(cradle_x0, cradle_x1, -cradle_outer_y, -cradle_inner_y, cradle_z0, cradle_z1)
    side_r = _box(cradle_x0, cradle_x1, cradle_inner_y, cradle_outer_y, cradle_z0, cradle_z1)
    rail_b = _box(cradle_x0, pcb_x + rail_depth, -cradle_outer_y, cradle_outer_y, cradle_z0, cradle_z0 + wall_mm)
    rail_t = _box(cradle_x0, pcb_x + rail_depth, -cradle_outer_y, cradle_outer_y, cradle_z1 - wall_mm, cradle_z1)
    c = back + side_l + side_r + rail_b + rail_t
    # USB-C slot through the bottom rail
    c = c - _box(pcb_x - 0.5, pcb_x + rail_depth + 1, -usb_w / 2 - 0.5, usb_w / 2 + 0.5, cradle_z0 - 1, cradle_z0 + wall_mm + 1)
    # cable/FPC relief in the back plate below the board bottom edge is not needed: FPC loop sits at X>-5.2
    c = c - _cyl_y(0, Z_TILT, -cradle_outer_y - 1, cradle_outer_y + 1, pivot_bore_cradle)
    return c


def pivot_pin_zero(side: int):
    y0 = side * (cradle_inner_y)
    y1 = side * (arm_y1)
    return _cyl_y(0, Z_TILT, min(y0, y1), max(y0, y1), pivot_pin_d)


# ----------------------------------------------------------------- build
def spin_angles(pan_deg: float, tilt_deg: float):
    """Absolute spin of each gear about its own axis, degrees."""
    pan_gear = pan_mesh_dir_deg + pan_deg
    pan_pinion = pan_mesh_dir_deg + 180.0 + 180.0 / pinion_teeth - pan_ratio * pan_deg
    tilt_pinion = tilt_mesh_dir_deg + 180.0 + 180.0 / pinion_teeth - tilt_ratio * tilt_deg
    return pan_gear, pan_pinion, tilt_pinion


def build_parts(pan_deg: float = 0.0, tilt_deg: float = 0.0) -> dict:
    """World-posed shapes keyed by part name, plus group membership."""
    pan_gear_a, pan_pinion_a, tilt_pinion_a = spin_angles(pan_deg, tilt_deg)
    tilt_loc = Location(TILT_PLANE)

    # ---- base group (fixed)
    base = base_zero()
    pan_motor = n20_zero().moved(Location(PAN_MOTOR_PLANE))
    pan_pinion = Pos(pan_pinion_xy[0], pan_pinion_xy[1], Z_PAN_GEAR) * pinion_zero().rotate(Axis.Z, pan_pinion_a)

    # ---- yoke group (pans)
    pan_gear = Pos(0, 0, Z_PAN_GEAR) * pan_gear_zero().rotate(Axis.Z, pan_gear_a)
    yoke = yoke_zero()
    tilt_motor = n20_zero().moved(Location(TILT_MOTOR_PLANE))
    tp = tilt_pinion_local
    tilt_pinion = tilt_loc * (Pos(tp[0], tp[1], 0) * pinion_zero().rotate(Axis.Z, tilt_pinion_a))
    pin_l = pivot_pin_zero(-1)
    pin_r = pivot_pin_zero(+1)

    # ---- tilt group (tilts, then pans)
    cradle = cradle_zero()
    camera = xiao_zero().moved(Location(BOARD_PLANE))
    sector = tilt_loc * sector_zero()
    hub_r = Location(Plane(origin=(0, sector_y0, Z_TILT), x_dir=(1, 0, 0), z_dir=(0, 1, 0))) * hub_zero()

    tilt_group = {"cradle": cradle, "camera": camera, "tilt_sector": sector, "tilt_hub_right": hub_r}
    tilt_group = {k: v.rotate(TILT_AXIS, tilt_deg) for k, v in tilt_group.items()}
    yoke_group = {"pan_gear": pan_gear, "yoke": yoke, "tilt_motor": tilt_motor, "tilt_pinion": tilt_pinion,
                  "pivot_pin_left": pin_l, "pivot_pin_right": pin_r}
    yoke_group = {k: v.rotate(PAN_AXIS, pan_deg) for k, v in yoke_group.items()}
    tilt_group = {k: v.rotate(PAN_AXIS, pan_deg) for k, v in tilt_group.items()}
    base_group = {"base": base, "pan_motor": pan_motor, "pan_pinion": pan_pinion}
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
    # named datums (joint axes) for inspection
    asm.revolute_frame(base_mod, "pan_axis", PAN_AXIS)
    asm.revolute_frame(yoke_mod, "tilt_axis", TILT_AXIS)
    return asm.build()
