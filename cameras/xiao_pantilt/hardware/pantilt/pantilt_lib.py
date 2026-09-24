"""xiao_pantilt geometry library — v7: split pod + slot holder + horn foot + screwed lid (2026-09-09).

One 9 g servo on the pan axis under the base top plate (classic 23 x 12.2
pocket, flange under the plate); the camera pod's foot sits on the servo boss
with a socket over the spline. No gears, no well, no journal. A 2" clear
acrylic tube drops into a groove in the base top and a printed cap plugs it.

Cable: the USB-C plug is on the pan axis, so the cable exits sideways (a
right-angle plug, 10 mm under the board) and drops through a hole in the base
top beside the servo body; the service loop lives in the hollow base.

v7 changes: the pod is two prints. `pod_base` = foot (servo-horn pocket, horn
screw hole, wire slot) + mast ending in a tongue. `holder` = board cradle built
in the BOARD frame with the tripod case's retention numbers: 0.4/side pocket,
full-length edge lips 0.95 over the PCB top with a 0.2 gap, bottom rail with the
USB opening; board slides in from the top, the tube cap stops it lifting. A boss
on the holder's back takes the tongue with one M2 self-tap screw. The lid gets
two M2 lugs in the base.

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

from build123d import Align, Axis, Box, Cylinder, Location, Plane, Polygon, Pos, extrude
from cadgen.step_scene import import_step

HERE = Path(__file__).resolve().parent
REF = HERE.parent.parent / "ref"
XIAO_STEP = REF / "xiao" / "amz-xiao-esp32s3-sense.step"
SERVO_STEP = REF / "mg90s" / "amz-mg90s-micro-servo.step"

HAS_TILT = False

# ----------------------------------------------------------------- parameters
gear_backlash_mm = 0.0                           # no gears (kept for sweep.py compatibility)
pan_min_deg, pan_max_deg = -90.0, 90.0           # direct drive: pan = servo angle
board_shift = (float(os.environ.get("PANTILT_BOARD_DX", "0")), float(os.environ.get("PANTILT_BOARD_DY", "0")))  # board-frame x/y play for the fit check

wall_mm = 2.0
pocket_clearance_mm = 0.25
servo_pocket_clearance = 0.2
usb_plug_space_mm = 10.0         # right-angle USB-C plug under the board (straight plug needs 13-15)

# holder retention (board frame, from the verified tripod case): pocket 0.4/side,
# lips 0.95 over the PCB top corners, 0.2 gap above the 1.25 PCB
pocket_side = 0.4
lip_over = 0.95
lip_gap = 0.2
lip_h = 2.0
holder_wall = 2.0
holder_back = 2.0
holder_wall_depth = 6.0          # side walls reach this far above the PCB bottom (board z)
usb_open_w = 12.3 + 1.0          # plug overmold + 0.5/side
pcb_t = 1.25

# tongue joint (pod_base mast -> holder boss)
tongue_w, tongue_t, tongue_len = 8.0, 2.0, 10.0
tongue_clear = 0.15
boss_t = 4.0
m2_pilot = 1.7

# servo horn (single arm, from the servo bag). Calipered 2026-09-10 (deskcam shot
# /hd2/temp_data/v4kshot/v4k-20260910-080416.jpg): 22 mm overall from the back of the hub
# to the tip, 6.7 wide at the pivot, tapering to 4.0 at the tip, 6 holes. Hub height,
# arm thickness and the outer-hole position are still envelope: caliper and set.
horn_hub_d, horn_hub_h = 6.7, 4.0
horn_len_overall = 22.0                                  # back of hub -> tip
horn_tip_w, horn_arm_t = 4.0, 2.0
horn_tip_r = horn_len_overall - horn_hub_d / 2           # 18.65: pivot centre -> tip
horn_tip_hole_from_tip = 2.0                             # outer hole centre from the tip
horn_clear = 0.2
horn_roof = 1.5                                          # foot material above the horn
horn_tip_screw_d = 2.2                                   # M2 self-tap through the roof into the outer hole
foot_clear_above_servo = 0.5

# lid screws: round bosses tied into the cylindrical sidewall by narrow radial webs
lid_lug_d, lid_lug_xy = 4.5, 22.5
lid_lug_web_w = 2.0
lid_lug_web_overlap = 0.5

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
foot_thick = horn_hub_h + horn_clear + horn_roof         # 5.7: pocket + roof
foot_d = 2 * (horn_tip_r + horn_clear + 2.0)             # 41.7: arm pocket + 2 mm rim (tube ID 44.5)
horn_tip_hole_x = -(horn_tip_r - horn_tip_hole_from_tip)  # -16.65: outer hole, arm along -X
Z_FOOT0 = Z_BOSS_TOP + foot_clear_above_servo
Z_FOOT1 = Z_FOOT0 + foot_thick
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
servo_lead_relief_w = 5.0                                # side-entry slot for the MG90S lead
servo_lead_relief_overlap = 0.5                          # overlap pocket and cable hole for a clean cut
PAN_AXIS = Axis((0, 0, 0), (0, 0, 1))
pan_pinion_xy = (0.0, 0.0)                               # servo axis = pan axis
well_r = hollow_r                                        # names kept for sweep.py
Z_RIM = Z_TOP
ring_r_in = groove_r0

# camera pod: USB-C plug centred on the pan axis. Board frame -> world:
# board x -> +Z, board y -> -Y, board z -> +X (BOARD_PLANE); board (0,0,0) at (pcb_x, board_w/2, Z_BOARD0)
pcb_x = -usb_center_bz                                  # -2.36
rail_x0 = -pocket_side - holder_wall                    # board x of the bottom rail: -2.4..-0.4
Z_BOARD0 = Z_FOOT1 + usb_plug_space_mm - rail_x0        # rail bottom sits usb_plug_space above the foot
BOARD_PLANE = Plane(origin=(pcb_x, board_w / 2, Z_BOARD0), x_dir=(0, 0, 1), z_dir=(1, 0, 0))
holder_x1 = board_len + pocket_side + 0.5               # 21.85: open top, walls end here
holder_y0, holder_y1 = -pocket_side - holder_wall, board_w + pocket_side + holder_wall   # -2.4 .. 20.18
boss_x0, boss_x1 = 4.0, 16.0                            # boss on the holder back, board x
boss_yc = board_w / 2
mast_x = pcb_x - holder_back - boss_t + tongue_clear + (boss_t - tongue_t) / 2   # world X of the tongue/mast back face
Z_BOARD_CENTER = Z_BOARD0 + board_len / 2


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


def _servo_lead_relief_slot(cx, cy, z0, z1):
    """Through-slot from the servo pocket's +Y end into the cable hole."""
    pocket_y1 = cy + servo_body_y1 - servo_axis_y + servo_pocket_clearance
    return _box(
        cx - servo_lead_relief_w / 2,
        cx + servo_lead_relief_w / 2,
        pocket_y1 - servo_lead_relief_overlap,
        cable_hole_xy[1] + servo_lead_relief_overlap,
        z0,
        z1,
    )


@lru_cache(maxsize=None)
def base_zero():
    """Ø55 puck: hollow under a 4 mm top plate, servo pocket on the axis, tube groove,
    cable hole beside the servo, servo lead-relief slot, and wall-integrated lid bosses."""
    body = _cyl_z(0, 0, 0, Z_TOP, 2 * base_r)
    body = body - _cyl_z(0, 0, -1, Z_TOP - plate_thick, 2 * hollow_r)
    body = body - (_cyl_z(0, 0, Z_TUBE0, Z_TOP + 1, 2 * groove_r1) - _cyl_z(0, 0, Z_TUBE0 - 1, Z_TOP + 2, 2 * groove_r0))
    body = body - _servo_pocket_xy(0.0, 0.0, Z_TOP - plate_thick - 1, Z_TOP + 1)
    body = body - _cyl_z(cable_hole_xy[0], cable_hole_xy[1], Z_TOP - plate_thick - 1, Z_TOP + 1, cable_hole_d)
    body = body - _servo_lead_relief_slot(0.0, 0.0, Z_TOP - plate_thick - 1, Z_TOP + 1)
    for sx in (-1, 1):
        lug = _cyl_z(sx * lid_lug_xy, 0, lid_t, Z_TOP - plate_thick + 0.01, lid_lug_d)
        web_inner_x = sx * (lid_lug_xy + lid_lug_d / 2 - lid_lug_web_overlap)
        web_outer_x = sx * (hollow_r + lid_lug_web_overlap)
        web = _box(
            min(web_inner_x, web_outer_x),
            max(web_inner_x, web_outer_x),
            -lid_lug_web_w / 2,
            lid_lug_web_w / 2,
            lid_t,
            Z_TOP - plate_thick + 0.01,
        )
        body = body + lug + web
        body = body - _cyl_z(sx * lid_lug_xy, 0, lid_t - 1, lid_t + 8, m2_pilot)
    return body


@lru_cache(maxsize=None)
def lid_zero():
    """Bottom lid: disc inside the hollow + ribbed pouch frame + two M2 clearance holes."""
    disc = _cyl_z(0, 0, 0, lid_t, 2 * (hollow_r - 0.2))
    ox, oy = bat_w / 2 + bat_clear, bat_l / 2 + bat_clear
    frame = _box(-ox - bay_rib_w, ox + bay_rib_w, -oy - bay_rib_w, oy + bay_rib_w, lid_t - 0.01, lid_t + bay_rib_h)
    frame = frame - _box(-ox, ox, -oy, oy, lid_t - 1, lid_t + bay_rib_h + 1)
    frame = frame & _cyl_z(0, 0, lid_t - 1, lid_t + bay_rib_h + 1, 2 * (hollow_r - 0.2))
    lid = disc + frame
    for sx in (-1, 1):
        lid = lid - _cyl_z(sx * lid_lug_xy, 0, -1, lid_t + bay_rib_h + 1, 2.2)
    return lid


@lru_cache(maxsize=None)
def battery_zero():
    return _box(-bat_w / 2, bat_w / 2, -bat_l / 2, bat_l / 2, Z_BAT0, Z_BAT1)


def _bbox(x0, x1, y0, y1, z0, z1):
    """Box in BOARD coordinates, returned in world (through BOARD_PLANE)."""
    return Location(BOARD_PLANE) * _box(x0, x1, y0, y1, z0, z1)


@lru_cache(maxsize=None)
def holder_zero():
    """Board holder, built in the board frame then placed. Back plate at z -2..0,
    side walls at the long edges, edge lips 0.95 over the PCB top with a 0.2 gap,
    bottom rail with the USB opening, open top (the tube cap stops lift-out).
    A boss on the back takes the pod_base tongue + one M2 self-tap screw."""
    x0 = rail_x0
    back = _bbox(x0, holder_x1, holder_y0, holder_y1, -holder_back, 0)
    wall_l = _bbox(x0, holder_x1, holder_y0, holder_y0 + holder_wall, -holder_back, holder_wall_depth)
    wall_r = _bbox(x0, holder_x1, holder_y1 - holder_wall, holder_y1, -holder_back, holder_wall_depth)
    lip_z0, lip_z1 = pcb_t + lip_gap, pcb_t + lip_gap + lip_h
    lip_l = _bbox(-pocket_side, holder_x1, -pocket_side, -pocket_side + lip_over, lip_z0, lip_z1)
    lip_r = _bbox(-pocket_side, holder_x1, board_w + pocket_side - lip_over, board_w + pocket_side, lip_z0, lip_z1)
    rail = _bbox(x0, -pocket_side, holder_y0, holder_y1, -holder_back, lip_z1)
    boss = _bbox(boss_x0, boss_x1, boss_yc - 6.0, boss_yc + 6.0, -holder_back - boss_t, -holder_back + 0.01)
    h = back + wall_l + wall_r + lip_l + lip_r + rail + boss
    # USB opening through the rail + back (plug overmold passes)
    h = h - _bbox(x0 - 1, -pocket_side + 1, board_w / 2 - usb_open_w / 2, board_w / 2 + usb_open_w / 2, -holder_back - 1, lip_z1 + 1)
    # tongue socket, open toward -x (downward in world), centred in the boss thickness
    sz0 = -holder_back - boss_t / 2 - tongue_t / 2 - tongue_clear
    sz1 = -holder_back - boss_t / 2 + tongue_t / 2 + tongue_clear
    h = h - _bbox(boss_x0 - 1, boss_x0 + tongue_len + tongue_clear, boss_yc - tongue_w / 2 - tongue_clear, boss_yc + tongue_w / 2 + tongue_clear, sz0, sz1)
    # M2 pilot through boss (and tongue), along board z
    pilot = Location(BOARD_PLANE) * (Pos(boss_x0 + tongue_len / 2, boss_yc, -holder_back - boss_t - 1) * _cyl(m2_pilot / 2, boss_t + 2))
    return h - pilot


@lru_cache(maxsize=None)
def _horn_outline(z0, z1, clear=0.0):
    """Tapered single-arm horn plan (hub circle at the pivot, tip circle at horn_tip_r,
    straight taper between) grown by `clear`, extruded z0..z1. Arm along -X."""
    r_hub = horn_hub_d / 2 + clear
    r_tip = horn_tip_w / 2 + clear
    x_tip = -(horn_tip_r - horn_tip_w / 2)                # tip circle centre
    hub = _cyl_z(0, 0, z0, z1, 2 * r_hub)
    tip = _cyl_z(x_tip, 0, z0, z1, 2 * r_tip)
    taper = extrude(Plane.XY.offset(z0) * Polygon((0, r_hub), (x_tip, r_tip), (x_tip, -r_tip), (0, -r_hub), align=None), amount=z1 - z0)
    return hub + tip + taper


def horn_zero():
    """Servo horn (single arm) sitting on the servo boss, arm toward -X."""
    hub = _cyl_z(0, 0, Z_BOSS_TOP, Z_BOSS_TOP + horn_hub_h, horn_hub_d)
    arm = _horn_outline(Z_BOSS_TOP + horn_hub_h - horn_arm_t, Z_BOSS_TOP + horn_hub_h)
    spline_bore = _cyl_z(0, 0, Z_BOSS_TOP - 1, Z_SPLINE_TOP + 0.1, servo_spline_d + 0.1)
    tip_hole = _cyl_z(horn_tip_hole_x, 0, Z_BOSS_TOP - 1, Z_BOSS_TOP + horn_hub_h + 1, 1.3)
    return (hub + arm) - spline_bore - tip_hole


@lru_cache(maxsize=None)
def pod_base_zero():
    """Foot (horn pocket from below, horn-screw hole, wire slot) + mast with the tongue."""
    foot = _cyl_z(0, 0, Z_FOOT0, Z_FOOT1, foot_d)
    c = horn_clear
    z_pocket_top = Z_BOSS_TOP + horn_hub_h + c
    hub_p = _cyl_z(0, 0, Z_FOOT0 - 1, z_pocket_top, horn_hub_d + 2 * c)
    arm_p = _horn_outline(Z_FOOT0 - 1, z_pocket_top, clear=c)   # full-depth tapered pocket, horn drops in from below
    screw = _cyl_z(0, 0, Z_FOOT0 - 1, Z_FOOT1 + 1, 2.4)          # horn screw, from above
    tip_screw = _cyl_z(horn_tip_hole_x, 0, Z_FOOT0 - 1, Z_FOOT1 + 1, horn_tip_screw_d)   # M2 into the horn's outer hole
    slot = _box(-2.5, 2.5, 6.0, foot_d / 2 + 1, Z_FOOT0 - 1, Z_FOOT1 + 1)
    foot = foot - hub_p - arm_p - screw - tip_screw - slot
    # mast: wide plate up to the boss, then the tongue
    z_boss0 = Z_BOARD0 + boss_x0
    mast = _box(mast_x, mast_x + tongue_t, -8.0, 8.0, Z_FOOT1 - 0.01, z_boss0 - 0.5)
    tongue = _box(mast_x, mast_x + tongue_t, -tongue_w / 2, tongue_w / 2, z_boss0 - 0.5 - 0.01, z_boss0 + tongue_len - tongue_clear)
    pilot = Location(BOARD_PLANE) * (Pos(boss_x0 + tongue_len / 2, boss_yc, -holder_back - boss_t - 1) * _cyl(m2_pilot / 2, boss_t + 2))
    return foot + mast + tongue - pilot


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
    horn = horn_zero()
    pod_base = pod_base_zero()
    holder = holder_zero()
    camera = xiao_zero().moved(Location(BOARD_PLANE))
    if board_shift != (0.0, 0.0):
        camera = camera.moved(Location((0, -board_shift[1], board_shift[0])))   # board x -> +Z, board y -> -Y
    yoke_group = {"pod_base": pod_base, "holder": holder, "camera": camera, "servo_horn": horn}
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
