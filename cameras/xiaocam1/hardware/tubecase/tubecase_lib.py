"""tubecase geometry library -- v2: everything inside the 2" tube.

Contract: DESIGN.md in this directory. Nothing is outside Ø50.8: the acrylic
tube is the whole skin, bottom to top. A printed base liner cup sits inside
the tube at the bottom and carries the charger and battery standing
vertically; a mid plate sits on the liner's rim and carries the camera
cradle; a cap plugs the top. Barrel jack through the base floor, plug
hanging out of the bottom. Two M2 screws through the tube wall lock the
chassis (drilled by hand at assembly time, guided by holes modelled in the
tube). No mounting insert.

World frame: origin on the tube axis at the bottom face (tube bottom edge
and base floor bottom are flush at z 0). Z up. +X = lens direction.

Replaces v1 (`archive/v1_sleeve/`): no bayonet, no door, no anti-rotation
pins -- the mid plate is instead screwed straight down onto two bosses cast
into the base liner wall, and further locked to the tube itself by two M2
screws through the tube wall into those same bosses.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from build123d import Align, Axis, Box, Cylinder, Location, Plane, Pos, chamfer
from cadgen.step_scene import import_step

HERE = Path(__file__).resolve().parent
REF = HERE.parent.parent / "ref"
XIAO_STEP = REF / "xiao" / "amz-xiao-esp32s3-sense.step"
CHARGER_STEP = REF / "bq25185" / "adafruit-6091-adafruit-bq25185-usb-dc-solar-lithium-ion-poly.step"
LIPO_STEP = REF / "lipo500" / "ada-1578-lipo-500.step"

# ----------------------------------------------------------------- parameters
tube_od, tube_id, tube_len = 50.8, 44.5, 87.5
tube_fit = 0.4                          # diametral -> liner_od = 44.1 (base and mid plate)
base_wall = 1.6                         # base_id = 40.9  (r 20.45)
floor_t = 4.5
base_h = 43.5                           # liner rim = mid plate seat  (Z_MID0)
mid_t = 4.0                             # Z_MID1 = 47.5
boss_d, boss_h = 5.0, 12.0              # mid-plate bosses inside the liner wall, top at Z_MID0
boss_xy = ((18.75, 0.0), (-18.75, 0.0))
m2_pilot, m2_clear, m2_head, m2_cb_depth = 1.7, 2.2, 4.0, 1.5
pilot_depth = 6.0                       # vertical pilots from the boss top (mid plate screws)
tube_screw_z, tube_screw_pilot_depth = 35.0, 5.0   # radial pilots Ø1.7 along X from the outside of the liner into the bosses
tube_hole_d = 2.2                       # drill guide holes modelled in the tube part
rib_w, rib_h_floor, rib_z1 = 1.5, 4.0, 32.5        # floor ribs 4 tall; wall ribs from floor_t to rib_z1
bat_l, bat_w, bat_t, bat_swell, bat_side = 36.0, 29.0, 4.75, 1.5, 0.5
bay_x0, bay_x1, bay_y = -6.0, 0.25, 15.0           # battery bay (x thickness incl. swell = 6.25, y = 29 + 2*0.5)
ch_x = 3.0                              # charger PCB back face plane (PCB x 3.0..4.57, components to 10.94)
ch_slot_w, ch_slot_x0 = 2.1, 2.75       # PCB slot x 2.75..4.85 between rib pairs at the y ends
ch_rib_y0 = 16.3                        # slot ribs run from |y| 16.3 to the wall
ch_pad_z1 = 5.7                         # PCB bottom edge rests on pads at z 5.7 (USB shell bottom then at 4.7)
jack_xy = (-14.5, 0.0)
jack_hole_d, jack_cb_d, jack_cb_depth = 7.5, 10.5, 2.2
jack_depth, jack_body_d, jack_flange_d, jack_flange_t, jack_barrel_d = 13.0, 11.0, 10.0, 2.0, 7.4
drain_d, drain_xy = 2.0, (13.0, -13.0)
lens_to_tube, cap_plug_fit = 4.0, 0.3
cap_plug_h, cap_top_t, cap_chamfer = 8.0, 2.0, 1.0
oring_w, oring_groove_d, oring_z_from_top = 3.3, 40.25, 3.5     # 40 x 2.5 metric O-ring; groove centre 3.5 below the tube top
notch_w, notch_r0, notch_angle_deg = 6.0, 18.5, -60.0           # mid plate wire notch

# cradle: identical numbers to v1 (pocket 0.4/side, lips 0.95 over the PCB with a 0.2
# gap, lip h 2, walls 2 to 6 above the PCB, back 3.0 with a 6 x 1.5 wire channel, rail
# 2 at the FPC end bx 21.65..23.65, open at the USB end bx -0.5, pedestal 2.0 tall
# under the rail with the channel continued down its -X face)
pocket_side = 0.4
lip_over = 0.95
lip_gap = 0.2
lip_h = 2.0
holder_wall = 2.0
holder_wall_depth = 6.0
pcb_t = 1.25
holder_back = 3.0
cradle_x_open = -0.5
rail_x0, rail_x1 = 21.65, 23.65
wire_channel_w, wire_channel_d = 6.0, 1.5

# -------------------------------------------------------- vendor frame facts
# XIAO ESP32S3 Sense (board frame: origin base-PCB plan bottom-left, +x along
# the long edge, USB-C at x=0, z=0 PCB bottom, lens +z).
xiao_board_len, xiao_board_w = 20.95, 17.78
xiao_stack_top = 13.96                  # component stack top (also the lens tip's board-z)
xiao_lens_bx, xiao_lens_by = 3.53, 8.25
xiao_sd_bx = -3.11                      # SD card sticks out past the USB end to board x -3.11

# bq25185 charger (board frame: origin PCB plan bottom-left, z=0 PCB bottom/back
# face). PCB 31.75 x 25.4 x 1.57.
charger_pcb_l, charger_pcb_w, charger_pcb_t = 31.75, 25.4, 1.57
charger_components_x1 = 10.94           # world x reach of the tallest components (PCB back at ch_x=3.0, front at 4.57)

# --------------------------------------------------------------- derived
liner_od = tube_id - tube_fit                        # 44.1
liner_id = liner_od - 2 * base_wall                   # 40.9  (r 20.45)
liner_r = liner_od / 2                                # 22.05
bore_r = liner_id / 2                                 # 20.45

Z_MID0 = base_h                                       # 43.5
Z_MID1 = Z_MID0 + mid_t                                # 47.5
Z_TUBE1 = tube_len                                    # 87.5
Z_CAP1 = Z_TUBE1 + cap_top_t                          # 89.5

pcb_x = tube_id / 2 - lens_to_tube - xiao_stack_top   # 4.29
pedestal_h = 2.0
Z_BOARD_TOP = Z_MID1 + pedestal_h + rail_x1           # 73.15
Z_LENS = Z_BOARD_TOP - xiao_lens_bx                   # 69.62

CH_ORIGIN_Z = 31.1                                    # charger PCB top edge (board y=0, JST-socket edge) world z
JACK_FLANGE_Z0 = 0.2
JACK_FLANGE_Z1 = JACK_FLANGE_Z0 + jack_flange_t       # 2.2
JACK_BODY_Z1 = JACK_FLANGE_Z1 + jack_depth            # 15.2

BOARD_PLANE = Plane(origin=(pcb_x, -xiao_board_w / 2, Z_BOARD_TOP), x_dir=(0, 0, -1), z_dir=(1, 0, 0))
CHARGER_PLANE = Plane(origin=(ch_x, charger_pcb_l / 2, CH_ORIGIN_Z), x_dir=(0, -1, 0), z_dir=(1, 0, 0))
BATTERY_PLANE = Plane(origin=(bay_x0, bat_w / 2, floor_t), x_dir=(0, 0, 1), z_dir=(1, 0, 0))


# ------------------------------------------------------------------- helpers
def _cyl(r, h):
    return Cylinder(r, h, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _box(x0, x1, y0, y1, z0, z1):
    return Pos(x0, y0, z0) * Box(x1 - x0, y1 - y0, z1 - z0, align=(Align.MIN, Align.MIN, Align.MIN))


def _cyl_z(cx, cy, z0, z1, d):
    return Pos(cx, cy, z0) * _cyl(d / 2, z1 - z0)


def _cyl_x(x0, x1, cy, cz, d):
    """Cylinder along the X axis from x0 to x1, centred at (cy, cz) in the YZ plane."""
    c = _cyl(d / 2, x1 - x0).rotate(Axis.Y, 90)
    return Pos(x0, cy, cz) * c


def _radial_box(angle_deg, r0, r1, w, z0, z1):
    """Box radiating from the Z axis: local x = radial (r0..r1), local y = tangential
    (+-w/2), then rotated about Z by angle_deg (0 = +X, 90 = +Y, CCW seen from above)."""
    return _box(r0, r1, -w / 2, w / 2, z0, z1).rotate(Axis.Z, angle_deg)


def _bbox_board(plane, x0, x1, y0, y1, z0, z1):
    """Box in a board-local frame, placed in world through `plane`."""
    return Location(plane) * _box(x0, x1, y0, y1, z0, z1)


def _boss_solid(bx, by):
    """One mid-plate boss cylinder (Ø boss_d, z Z_MID0-boss_h .. Z_MID0), before fusing
    into the liner wall."""
    return _cyl_z(bx, by, Z_MID0 - boss_h, Z_MID0, boss_d)


FUSE_R = bore_r + 0.5   # wall ribs/bosses are extended past the bore and clipped to this radius so they fuse cleanly


def _wall_rib(x0, x1, y_in, z0, z1):
    """A pair of ribs (mirrored about the X axis) running from y_in out to the wall,
    at x [x0, x1], z [z0, z1]. Extended past the bore and intersected with a cylinder
    of radius FUSE_R so both ribs fuse cleanly into the circular wall."""
    rib = _box(x0, x1, y_in, FUSE_R + 2, z0, z1) + _box(x0, x1, -(FUSE_R + 2), -y_in, z0, z1)
    clip = _cyl_z(0, 0, z0 - 1, z1 + 1, 2 * FUSE_R)
    return rib & clip


# ----------------------------------------------------------- imported parts
@lru_cache(maxsize=None)
def xiao_zero():
    return import_step(str(XIAO_STEP)).moved(Location(BOARD_PLANE))


@lru_cache(maxsize=None)
def charger_zero():
    return import_step(str(CHARGER_STEP)).moved(Location(CHARGER_PLANE))


@lru_cache(maxsize=None)
def battery_zero():
    """500 mAh 1S LiPo (Adafruit 1578), vendor STEP, plan bottom-left, z=0 bottom,
    standing on a short end via BATTERY_PLANE."""
    return import_step(str(LIPO_STEP)).moved(Location(BATTERY_PLANE))


@lru_cache(maxsize=None)
def battery_envelope_zero():
    """Swell envelope over the battery footprint: x -6..0.25, y +-15, z 4.5..40.5.
    Checks only, not a printed feature."""
    ox = bat_w / 2 + bat_side
    return _box(bay_x0, bay_x0 + bat_t + bat_swell, -ox, ox, floor_t, floor_t + bat_l)


@lru_cache(maxsize=None)
def jack_envelope_zero():
    """Estimated envelope for the panel-mount DC barrel jack (checks only, not
    printed): flange Ø10 z 0.2..2.2, barrel Ø7.4 z 2.2..floor_t, body/nut Ø11
    z floor_t..15.2, axis vertical at jack_xy."""
    jx, jy = jack_xy
    flange = _cyl_z(jx, jy, JACK_FLANGE_Z0, JACK_FLANGE_Z1, jack_flange_d)
    barrel = _cyl_z(jx, jy, JACK_FLANGE_Z1, floor_t, jack_barrel_d)
    body = _cyl_z(jx, jy, floor_t, JACK_BODY_Z1, jack_body_d)
    return flange + barrel + body


# -------------------------------------------------------------- base (liner cup)
@lru_cache(maxsize=None)
def base_zero():
    """Printed liner cup, standing on its floor. Cup -> cut the bore -> ADD ribs,
    pads, bosses (they live inside the bore) -> cut pilots, jack, drain. One solid."""
    cup = _cyl_z(0, 0, 0, base_h, liner_od)
    bottom_edge = cup.edges().group_by(Axis.Z)[0]
    cup = chamfer(bottom_edge, 0.5)
    cup = cup - _cyl_z(0, 0, floor_t, base_h + 0.5, liner_id)

    # battery bay floor ribs (1.5 wide, 4 tall, z floor_t..floor_t+rib_h_floor):
    # along Y at x -7.5..-6.0 and bay_x1..bay_x1+rib_w, spanning y +-bay_y; end
    # ribs at y +-(bay_y..bay_y+rib_w) spanning x -7.5..bay_x1.
    fz0, fz1 = floor_t, floor_t + rib_h_floor
    bx0 = bay_x0 - rib_w   # -7.5
    ribs = _box(bx0, bay_x0, -bay_y, bay_y, fz0, fz1)
    ribs = ribs + _box(bay_x1, bay_x1 + rib_w, -bay_y, bay_y, fz0, fz1)
    ribs = ribs + _box(bx0, bay_x1 + rib_w, bay_y, bay_y + rib_w, fz0, fz1)
    ribs = ribs + _box(bx0, bay_x1 + rib_w, -(bay_y + rib_w), -bay_y, fz0, fz1)

    # battery wall ribs (z floor_t..rib_z1), x -7.5..-6.0, fused into the wall
    ribs = ribs + _wall_rib(bx0, bay_x0, bay_y, floor_t, rib_z1)

    # charger slot ribs (z floor_t..rib_z1): x bay_x1..ch_slot_x0 and
    # ch_slot_x0+ch_slot_w..ch_slot_x0+ch_slot_w+rib_w, fused into the wall
    slot_x1 = ch_slot_x0 + ch_slot_w
    ribs = ribs + _wall_rib(bay_x1, ch_slot_x0, ch_rib_y0, floor_t, rib_z1)
    ribs = ribs + _wall_rib(slot_x1, slot_x1 + rib_w, ch_rib_y0, floor_t, rib_z1)

    # charger PCB floor pads: x ch_slot_x0..slot_x1, |y| 6.0..ch_rib_y0, z floor_t..ch_pad_z1
    pads = _box(ch_slot_x0, slot_x1, 6.0, ch_rib_y0, floor_t, ch_pad_z1)
    pads = pads + _box(ch_slot_x0, slot_x1, -ch_rib_y0, -6.0, floor_t, ch_pad_z1)

    bosses = None
    for bx, by in boss_xy:
        b = _boss_solid(bx, by)
        bosses = b if bosses is None else bosses + b

    cup = cup + ribs + pads + bosses

    # vertical pilots (mid-plate screws), Ø m2_pilot x pilot_depth, from each boss top
    for bx, by in boss_xy:
        cup = cup - _cyl_z(bx, by, Z_MID0 - pilot_depth, Z_MID0 + 0.5, m2_pilot)

    # radial tube-screw pilots: Ø m2_pilot along X, from the outside of the liner
    # inward tube_screw_pilot_depth, into each boss, at z tube_screw_z
    for bx, by in boss_xy:
        sign = 1 if bx >= 0 else -1
        x_outer = sign * (liner_r + 2.0)
        x_inner = sign * (liner_r - tube_screw_pilot_depth)
        x0, x1 = (x_inner, x_outer) if sign > 0 else (x_outer, x_inner)
        cup = cup - _cyl_x(x0, x1, by, tube_screw_z, m2_pilot)

    # jack: floor hole + counterbore from below
    jx, jy = jack_xy
    cup = cup - _cyl_z(jx, jy, -0.5, floor_t + 0.5, jack_hole_d)
    cup = cup - _cyl_z(jx, jy, -0.5, jack_cb_depth, jack_cb_d)

    # drain hole through the floor
    cup = cup - _cyl_z(drain_xy[0], drain_xy[1], -0.5, floor_t + 0.5, drain_d)

    return cup


# -------------------------------------------------------- camera cradle (mid plate)
@lru_cache(maxsize=None)
def cradle_zero():
    """Board holder, unchanged from v1 pantilt-derived geometry: back plate 3.0
    thick carrying a wire channel to the rail end; rail (closed end) at the FPC
    end; open end (no rail) at the USB end. Re-based on Z_MID1 and pcb_x."""
    x0, x1 = cradle_x_open, rail_x1
    y0, y1 = -pocket_side - holder_wall, xiao_board_w + pocket_side + holder_wall
    back = _bbox_board(BOARD_PLANE, x0, x1, y0, y1, -holder_back, 0)
    wall_l = _bbox_board(BOARD_PLANE, x0, x1, y0, y0 + holder_wall, -holder_back, holder_wall_depth)
    wall_r = _bbox_board(BOARD_PLANE, x0, x1, y1 - holder_wall, y1, -holder_back, holder_wall_depth)
    lip_z0, lip_z1 = pcb_t + lip_gap, pcb_t + lip_gap + lip_h
    lip_l = _bbox_board(BOARD_PLANE, x0, x1, -pocket_side, -pocket_side + lip_over, lip_z0, lip_z1)
    lip_r = _bbox_board(BOARD_PLANE, x0, x1, xiao_board_w + pocket_side - lip_over, xiao_board_w + pocket_side, lip_z0, lip_z1)
    rail = _bbox_board(BOARD_PLANE, rail_x0, rail_x1, y0, y1, -holder_back, lip_z1)

    cradle = back + wall_l + wall_r + lip_l + lip_r + rail
    channel = _bbox_board(BOARD_PLANE, x0 - 1, rail_x1 + 1, xiao_board_w / 2 - wire_channel_w / 2, xiao_board_w / 2 + wire_channel_w / 2, -wire_channel_d, 0.1)
    cradle = cradle - channel

    # pedestal: box from the mid plate top up to the rail bottom, same x/y
    # footprint as the cradle back+walls, wire channel continued down its -X face
    ped_x0, ped_x1 = pcb_x - holder_back, pcb_x + holder_wall_depth
    ped_y0, ped_y1 = -xiao_board_w / 2 + y0, -xiao_board_w / 2 + y1
    ped_z0, ped_z1 = Z_MID1, Z_BOARD_TOP - rail_x1
    pedestal = _box(ped_x0, ped_x1, ped_y0, ped_y1, ped_z0, ped_z1)
    ped_slot = _box(ped_x0 - 0.5, ped_x0 + wire_channel_d, -wire_channel_w / 2, wire_channel_w / 2, ped_z0 - 1, ped_z1 + 1)
    pedestal = pedestal - ped_slot

    return cradle + pedestal


def _notch_cut():
    """The mid plate's wire notch cutting volume (tangential width notch_w, from
    r notch_r0 outward past the rim, at notch_angle_deg). Split out as its own
    function so checks.py can verify it clears the cradle footprint and the bosses."""
    r1 = liner_od / 2 + 2.0
    return _radial_box(notch_angle_deg, notch_r0, r1, notch_w, Z_MID0 - 1, Z_MID1 + 1)


@lru_cache(maxsize=None)
def mid_plate_zero():
    """Printed flat, underside on the bed, cradle up. Disc + screw holes/
    counterbores at the bosses + wire notch + cradle/pedestal. One solid. No
    charger pilots, no pin holes, no bayonet notches (v1 features, dropped)."""
    disc = _cyl_z(0, 0, Z_MID0, Z_MID1, liner_od)
    plate = disc + cradle_zero()

    for bx, by in boss_xy:
        plate = plate - _cyl_z(bx, by, Z_MID0 - 0.5, Z_MID1 + 0.5, m2_clear)
        plate = plate - _cyl_z(bx, by, Z_MID1 - m2_cb_depth, Z_MID1 + 0.5, m2_head)

    plate = plate - _notch_cut()
    return plate


# -------------------------------------------------------------- cap / tube
@lru_cache(maxsize=None)
def cap_zero():
    """Plug (with an O-ring groove cut into its cylindrical face) + top disc,
    chamfered on the outer top edge. One solid."""
    plug_od = tube_id - cap_plug_fit
    plug = _cyl_z(0, 0, Z_TUBE1 - cap_plug_h, Z_TUBE1 + 0.01, plug_od)

    groove_z0 = Z_TUBE1 - oring_z_from_top - oring_w / 2
    groove_z1 = Z_TUBE1 - oring_z_from_top + oring_w / 2
    groove = _cyl_z(0, 0, groove_z0, groove_z1, plug_od) - _cyl_z(0, 0, groove_z0 - 1, groove_z1 + 1, oring_groove_d)
    plug = plug - groove

    top = _cyl_z(0, 0, Z_TUBE1, Z_CAP1, tube_od)
    top_edge = top.edges().group_by(Axis.Z)[-1]
    top = chamfer(top_edge, cap_chamfer)

    return plug + top


@lru_cache(maxsize=None)
def tube_zero():
    """Purchased 2" acrylic tube, modelled: OD 50.8 ID 44.5 z 0..87.5, with two
    Ø tube_hole_d radial drill-guide holes along X at z tube_screw_z."""
    body = _cyl_z(0, 0, 0, Z_TUBE1, tube_od) - _cyl_z(0, 0, -0.5, Z_TUBE1 + 0.5, tube_id)
    hole = _cyl_x(-(tube_od / 2 + 2.0), tube_od / 2 + 2.0, 0, tube_screw_z, tube_hole_d)
    return body - hole


# ----------------------------------------------------------------- coupon
@lru_cache(maxsize=None)
def coupon_neck_zero():
    """Test ring: ID 38, OD stepped in three bands to bracket the real (measured)
    tube ID against the vendor-nominal 44.5. Bands, bottom to top: 44.4 (0..3.3),
    44.2 (3.3..6.7), 44.0 (6.7..10). The bands settle the liner/cap fit."""
    ring_id = 38.0
    bands = ((0.0, 3.3, 44.4), (3.3, 6.7, 44.2), (6.7, 10.0, 44.0))
    ring = None
    for z0, z1, od in bands:
        band = _cyl_z(0, 0, z0, z1, od) - _cyl_z(0, 0, z0 - 1, z1 + 1, ring_id)
        ring = band if ring is None else ring + band
    return ring


# ----------------------------------------------------------------- build
def build_parts() -> dict:
    return {
        "base": base_zero(),
        "mid_plate": mid_plate_zero(),
        "cap": cap_zero(),
        "tube": tube_zero(),
        "charger_bq25185": charger_zero(),
        "camera_xiao": xiao_zero(),
        "battery_1578": battery_zero(),
        "battery_swell_envelope": battery_envelope_zero(),
        "jack_envelope": jack_envelope_zero(),
    }


def build_assembly():
    from build123d import Color
    from cadgen.assembly import AssemblyHelper

    asm = AssemblyHelper("tubecase")
    for name, shape in build_parts().items():
        color = Color(1.0, 0.55, 0.0, 0.5) if name == "jack_envelope" else None
        asm.add(shape, name, color=color)
    return asm.build()
