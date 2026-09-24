"""tubecase geometry library -- static XIAO Sense tube camera + bq25185 solar charger.

Contract: DESIGN.md in this directory. No motor, no pan/tilt: a 2" clear
acrylic tube sits on a printed sleeve; a deck at the bottom of the sleeve
carries the camera cradle (derived from ../pantilt/pantilt_lib.py::holder_zero)
and the bq25185 solar charger (hanging underneath); a door closes the bottom
and carries the 500 mAh 1S cell; a cap plugs the tube's top.

World frame: origin on the tube axis at the door's bottom face (the bench).
Z up. +X = camera look direction.

Retention (v2, post spec-fix): the deck carries NO screws of its own -- it is
held down by the sleeve's rib tops, held up by the cone (its disc is too wide
to pass the cone/neck), and held against rotation by two anti-rotation pins
that stand up off the door and engage blind holes in the deck underside. The
door is the only screwed part (two M2 self-tap into the sleeve's rib bottom
pilots) and goes on last, straight up, after the deck/cradle/camera/tube/cap
are already in place.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from build123d import Align, Axis, Box, Cone, Cylinder, Location, Plane, Polygon, Pos, chamfer, extrude
from cadgen.step_scene import import_step

HERE = Path(__file__).resolve().parent
REF = HERE.parent.parent / "ref"
XIAO_STEP = REF / "xiao" / "amz-xiao-esp32s3-sense.step"
CHARGER_STEP = REF / "bq25185" / "adafruit-6091-adafruit-bq25185-usb-dc-solar-lithium-ion-poly.step"
LIPO_STEP = REF / "lipo500" / "ada-1578-lipo-500.step"

# ----------------------------------------------------------------- parameters
tube_od, tube_id, tube_len = 50.8, 44.5, 32.0
tube_fit = 0.4              # diametral: neck_od = tube_id - tube_fit
neck_wall = 1.6              # neck_id = neck_od - 2*neck_wall = 40.9 (r 20.45)
neck_h = 8.0
wall = 2.0                   # sleeve wall
sleeve_od = 55.0             # sleeve_id = sleeve_od - 2*wall
door_t = 2.0
deck_t = 4.5
deck_clear = 0.2             # deck_d = sleeve_id - 2*deck_clear; door same
rib_w, rib_r0 = 5.0, 17.0    # ribs on the Y axis: x +-rib_w/2, y from rib_r0 to the wall (+0.5 overlap)
screw_r = 21.0                # door screws (+ rib bottom pilots) at (0, +-screw_r). No deck screws.
m2_pilot, m2_clear, m2_head = 1.7, 2.2, 4.0
pilot_depth = 6.0             # rib bottom pilots, from door_t upward
bayonet_twist_deg = 20.0
notch_w, notch_r0 = 6.0, 16.5     # deck notches, tangential width, from this radius outward
bat_l, bat_w, bat_t = 36.0, 29.0, 4.75        # 36 along X
bat_swell, bat_side = 1.5, 0.5
bay_rib_w, bay_rib_h = 1.5, 3.0
charger_pilot_depth = 3.5
lens_above_seat = 19.0
lens_to_tube = 4.0            # lens tip to the tube inner wall
cap_plug_h, cap_top_t, cap_skirt_h = 3.0, 2.0, 5.0
cap_plug_fit, cap_skirt_fit = 0.3, 0.4        # diametral
shoulder_chamfer = 1.5
drain_hole_d, drain_hole_xy = 2.0, (12.0, -20.0)

# panel-mount DC barrel jack housing at -X (replaces the mounting tab and the
# door's cable hole). Jack facts are user-measured except where noted ESTIMATED.
jack_hole_d = 7.5
jack_depth = 13.0             # outer panel face -> lug ends (measured)
jack_body_d = 11.0            # ESTIMATED nut envelope behind the panel
jack_flange_d, jack_flange_t = 10.0, 2.0      # ESTIMATED, outside
jack_panel_t = 2.0
jack_cavity_w, jack_cavity_h = 15.0, 15.0     # y width, z height of the housing cavity
jack_cavity_z0 = 2.0
ear_wall = 2.0
brow_proj = 4.0
wing_w, wing_t, wing_hole_d = 7.5, 4.0, 4.5

# anti-rotation pins, door -> deck (replace the deck's own screws entirely)
pin_d = 4.0
pin_xy = ((21.5, 6.0), (21.5, -6.0))
pin_engage = 3.0               # pin top sits this far above Z_DECK0, inside the deck's blind hole
pin_hole_d = 4.4
pin_hole_depth = 3.5           # blind hole depth in the deck underside (0.5 mm tip clearance)

deck_z0 = 19.0                # Z_DECK0: chosen so the charger clears the battery swell top by 4.4

# -------------------------------------------------------- vendor frame facts
# XIAO ESP32S3 Sense (board frame: origin base-PCB plan bottom-left, +x along
# the long edge, USB-C at x=0, z=0 PCB bottom, lens +z). From DESIGN.md's
# purchased-parts table.
xiao_board_len, xiao_board_w = 20.95, 17.78
xiao_stack_top = 13.96                 # component stack top (also the lens tip's board-z)
xiao_lens_bx, xiao_lens_by = 3.53, 8.25
xiao_sd_bx = -3.11                     # SD card sticks out past the USB end to board x -3.11

# bq25185 charger, Adafruit 6091 (board frame: origin PCB plan bottom-left,
# z=0 PCB bottom/back face). PCB 31.75 x 25.4 x 1.57.
charger_pcb_l, charger_pcb_w = 31.75, 25.4
charger_hole_xy = ((2.54, 2.54), (29.21, 2.54), (2.54, 22.86), (29.21, 22.86))

# ------------------------------------------------------------ derived layout
neck_od = tube_id - tube_fit                         # 44.1
neck_id = neck_od - 2 * neck_wall                    # 40.9 (r 20.45)
sleeve_id = sleeve_od - 2 * wall                      # 51.0
deck_d = sleeve_id - 2 * deck_clear                   # 50.6 (door same)

Z_DOOR1 = door_t                                      # 2.0
Z_BAT1 = Z_DOOR1 + bat_t                              # 6.75
Z_DECK0 = deck_z0                                     # 19.0
Z_DECK1 = Z_DECK0 + deck_t                            # 23.5
Z_SEAT = Z_DECK1 + (sleeve_id / 2 - neck_id / 2)      # cone: sleeve bore r -> neck bore r, 45 deg
Z_NECK1 = Z_SEAT + neck_h
Z_TUBE1 = Z_SEAT + tube_len
Z_CAP1 = Z_TUBE1 + cap_top_t

battery_envelope_h = bat_t + bat_swell                # 6.25

# jack housing derived layout (world frame; jack axis along -X at the back of the sleeve)
jack_z = jack_cavity_z0 + jack_cavity_h / 2            # 9.5, jack axis height
jack_x_outer = -(sleeve_od / 2 + jack_depth + jack_panel_t)   # -42.5, outer panel face
jack_x_ear0 = -(sleeve_od / 2 - 0.5)                          # -27.0, ear meets the sleeve body

# camera cradle: board frame -> world. Board x -> -Z, board y -> +Y, board z -> +X.
pcb_x = tube_id / 2 - lens_to_tube - xiao_stack_top   # 4.29
Z_LENS = Z_SEAT + lens_above_seat
Z_BOARD_TOP = Z_LENS + xiao_lens_bx
BOARD_PLANE = Plane(origin=(pcb_x, -xiao_board_w / 2, Z_BOARD_TOP), x_dir=(0, 0, -1), z_dir=(1, 0, 0))

# cradle numbers carried over unchanged from pantilt_lib.holder_zero() (board frame)
pocket_side = 0.4
lip_over = 0.95
lip_gap = 0.2
lip_h = 2.0
holder_wall = 2.0
holder_wall_depth = 6.0
pcb_t = 1.25
# tubecase changes: thicker back (was 2), rail moved to the FPC end, open end at the USB end
holder_back = 3.0
cradle_x_open = -0.5                  # open end (USB end): back, walls, lips all reach here
rail_x0, rail_x1 = 21.65, 23.65       # closed end (FPC end): rail, no USB opening
wire_channel_w, wire_channel_d = 6.0, 1.5

# bq25185 charger: board frame -> world. board x -> +Y, board y -> +X, board z -> -Z
CHARGER_PLANE = Plane(origin=(-12.7, -15.875, Z_DECK0), x_dir=(0, 1, 0), z_dir=(0, 0, -1))


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


def _cone_z(cx, cy, z0, z1, r0, r1):
    """Frustum from radius r0 at z0 to radius r1 at z1 (a 45 deg cone when r0-r1 == z1-z0)."""
    return Pos(cx, cy, z0) * Cone(r0, r1, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _radial_box(angle_deg, r0, r1, w, z0, z1):
    """Box radiating from the Z axis: local x = radial (r0..r1), local y = tangential
    (+-w/2), then rotated about Z by angle_deg (0 = +X, 90 = +Y, CCW seen from above)."""
    return _box(r0, r1, -w / 2, w / 2, z0, z1).rotate(Axis.Z, angle_deg)


def _bbox_board(plane, x0, x1, y0, y1, z0, z1):
    """Box in a board-local frame, placed in world through `plane`."""
    return Location(plane) * _box(x0, x1, y0, y1, z0, z1)


# ----------------------------------------------------------- imported parts
@lru_cache(maxsize=None)
def xiao_zero():
    return import_step(str(XIAO_STEP)).moved(Location(BOARD_PLANE))


@lru_cache(maxsize=None)
def charger_zero():
    return import_step(str(CHARGER_STEP)).moved(Location(CHARGER_PLANE))


@lru_cache(maxsize=None)
def battery_zero():
    """500 mAh 1S LiPo (Adafruit 1578), vendor STEP, plan bottom-left, z=0 bottom."""
    return import_step(str(LIPO_STEP)).moved(Location(Pos(-bat_l / 2, -bat_w / 2, door_t)))


@lru_cache(maxsize=None)
def battery_envelope_zero():
    """Labelled 37 x 30 x 6.25 swell envelope over the battery footprint. Checks only,
    not part of the door print."""
    ox, oy = bat_l / 2 + bat_side, bat_w / 2 + bat_side
    return _box(-ox, ox, -oy, oy, door_t, door_t + battery_envelope_h)


# ----------------------------------------------------------- jack housing
def _jack_ear_and_wings():
    """Housing ('ear') for the panel-mount DC barrel jack, fused to the sleeve at -X,
    plus a brow (drip visor) over the panel and two mounting wings. Returns the ADD
    geometry (housing + brow + wings); the caller cuts the cavity/hole/wing holes."""
    ear_y = jack_cavity_w / 2 + ear_wall           # 9.5
    ear_z1 = jack_cavity_z0 + jack_cavity_h + ear_wall   # 19.0
    ear = _box(jack_x_outer, jack_x_ear0, -ear_y, ear_y, 0, ear_z1)

    # brow: triangular prism above the jack, points (in XZ) (x_outer, ceiling),
    # (x_outer, ear_top), (x_outer - brow_proj, ear_top); underside is the slanted
    # face so it prints standing without support.
    ceiling_z = jack_cavity_z0 + jack_cavity_h     # 17.0
    pl = Plane(origin=(0, -ear_y, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0))
    tri = Polygon((jack_x_outer, -ceiling_z), (jack_x_outer - brow_proj, -ear_z1), (jack_x_outer, -ear_z1), align=None)
    brow = extrude(pl * tri, amount=2 * ear_y)

    wing_y0, wing_y1 = ear_y, ear_y + wing_w       # 9.5 .. 17.0
    wings = (
        _box(jack_x_outer, jack_x_ear0, wing_y0, wing_y1, 0, wing_t)
        + _box(jack_x_outer, jack_x_ear0, -wing_y1, -wing_y0, 0, wing_t)
    )
    return ear + brow + wings


def _jack_cuts():
    """Cavity (opens the housing into the sleeve bore) + through jack hole + wing holes."""
    cavity = _box(jack_x_outer + jack_panel_t, -24.0, -jack_cavity_w / 2, jack_cavity_w / 2, jack_cavity_z0, jack_cavity_z0 + jack_cavity_h)
    hole = _cyl_x(jack_x_outer - 1, jack_x_outer + jack_panel_t + 1, 0, jack_z, jack_hole_d)
    wing_x = (jack_x_outer + jack_x_ear0) / 2
    wing_yc = jack_cavity_w / 2 + ear_wall + wing_w / 2
    wing_holes = None
    for sy in (1, -1):
        h = _cyl_z(wing_x, sy * wing_yc, -1, wing_t + 1, wing_hole_d)
        wing_holes = h if wing_holes is None else wing_holes + h
    return cavity + hole, wing_holes


# -------------------------------------------------------------- sleeve
@lru_cache(maxsize=None)
def sleeve_zero():
    """Cylinder Ø55 body -> cone -> neck, ribs, DC jack housing; bores/pilots/holes cut
    last. Ribs carry only the door's bottom-entry screw pilots -- the deck has no screws
    of its own (retained by the rib tops + the cone above, and against rotation by the
    door's anti-rotation pins)."""
    body = _cyl_z(0, 0, 0, Z_SEAT, sleeve_od)
    top_edge = body.edges().group_by(Axis.Z)[-1]
    body = chamfer(top_edge, shoulder_chamfer)
    neck = _cyl_z(0, 0, Z_SEAT, Z_NECK1, neck_od)
    rib_r1 = sleeve_id / 2 + 0.5     # 0.5 into the wall
    ribs = _radial_box(90, rib_r0, rib_r1, rib_w, door_t, Z_DECK0) + _radial_box(270, rib_r0, rib_r1, rib_w, door_t, Z_DECK0)
    jack_add = _jack_ear_and_wings()

    solid = body + neck + ribs + jack_add
    solid = solid - _cyl_z(0, 0, -1, Z_DECK1, sleeve_id)
    solid = solid - _cone_z(0, 0, Z_DECK1, Z_SEAT, sleeve_id / 2, neck_id / 2)
    solid = solid - _cyl_z(0, 0, Z_SEAT - 0.5, Z_NECK1 + 1, neck_id)
    for sy in (1, -1):
        solid = solid - _cyl_z(0, sy * screw_r, door_t - 0.5, door_t + pilot_depth, m2_pilot)

    jack_cut, wing_holes = _jack_cuts()
    solid = solid - jack_cut - wing_holes
    return solid


@lru_cache(maxsize=None)
def jack_envelope_zero():
    """Estimated envelope for the panel-mount DC barrel jack (checks only, not printed):
    threaded barrel Ø7.4 through the panel, nut/body Ø11 behind the panel, flange Ø10
    proud of the outer face. Must not intersect any other part."""
    barrel = _cyl_x(-44.5, -29.5, 0, jack_z, 7.4)
    body = _cyl_x(-40.5, -29.5, 0, jack_z, jack_body_d)
    flange = _cyl_x(-44.5, -42.5, 0, jack_z, jack_flange_d)
    return barrel + body + flange


# -------------------------------------------------------------- deck cradle
@lru_cache(maxsize=None)
def cradle_zero():
    """Board holder derived from pantilt_lib.holder_zero(), with: back plate 3.0
    thick (was 2) carrying a wire channel to the rail end; rail (closed end) moved
    to the FPC end; open end (no rail) at the USB end; a pedestal replaces the
    tongue boss, standing from the deck top up to the rail bottom."""
    x0, x1 = cradle_x_open, rail_x1
    y0, y1 = -pocket_side - holder_wall, xiao_board_w + pocket_side + holder_wall
    back = _bbox_board(BOARD_PLANE, x0, x1, y0, y1, -holder_back, 0)
    wall_l = _bbox_board(BOARD_PLANE, x0, x1, y0, y0 + holder_wall, -holder_back, holder_wall_depth)
    wall_r = _bbox_board(BOARD_PLANE, x0, x1, y1 - holder_wall, y1, -holder_back, holder_wall_depth)
    lip_z0, lip_z1 = pcb_t + lip_gap, pcb_t + lip_gap + lip_h
    lip_l = _bbox_board(BOARD_PLANE, x0, x1, -pocket_side, -pocket_side + lip_over, lip_z0, lip_z1)
    lip_r = _bbox_board(BOARD_PLANE, x0, x1, xiao_board_w + pocket_side - lip_over, xiao_board_w + pocket_side, lip_z0, lip_z1)
    rail = _bbox_board(BOARD_PLANE, rail_x0, rail_x1, y0, y1, -holder_back, lip_z1)   # closed end, no USB opening

    cradle = back + wall_l + wall_r + lip_l + lip_r + rail
    # wire channel: cut into the back plate's board-facing surface (bw near 0),
    # 6 wide centred on by = board_w/2, running the full length and out the rail end
    channel = _bbox_board(BOARD_PLANE, x0 - 1, rail_x1 + 1, xiao_board_w / 2 - wire_channel_w / 2, xiao_board_w / 2 + wire_channel_w / 2, -wire_channel_d, 0.1)
    cradle = cradle - channel

    # pedestal: box from the rail bottom down to the deck top, same x/y footprint
    # as the cradle back+walls, with the wire channel continued down its -X face
    ped_x0, ped_x1 = pcb_x - holder_back, pcb_x + holder_wall_depth
    ped_y0, ped_y1 = -xiao_board_w / 2 + y0, -xiao_board_w / 2 + y1
    ped_z0, ped_z1 = Z_DECK1, Z_BOARD_TOP - rail_x1
    pedestal = _box(ped_x0, ped_x1, ped_y0, ped_y1, ped_z0, ped_z1)
    ped_slot = _box(ped_x0 - 0.5, ped_x0 + wire_channel_d, -wire_channel_w / 2, wire_channel_w / 2, ped_z0 - 1, ped_z1 + 1)
    pedestal = pedestal - ped_slot

    return cradle + pedestal


# -------------------------------------------------------------- deck
@lru_cache(maxsize=None)
def deck_zero():
    """Disc + bayonet notches + charger pilots + anti-rotation-pin blind holes + the
    cradle/pedestal. ONE printed solid; the charger itself is a separate imported
    occurrence. No screw holes of its own -- see sleeve_zero()/door_zero()."""
    disc = _cyl_z(0, 0, Z_DECK0, Z_DECK1, deck_d)
    deck = disc + cradle_zero()

    notch_r1 = deck_d / 2 + 2.0
    for angle in (90 - bayonet_twist_deg, 270 - bayonet_twist_deg):
        deck = deck - _radial_box(angle, notch_r0, notch_r1, notch_w, Z_DECK0 - 1, Z_DECK1 + 1)

    for bx, by in charger_hole_xy:
        wx = by - 12.7
        wy = bx - 15.875
        deck = deck - _cyl_z(wx, wy, Z_DECK0 - 0.5, Z_DECK0 + charger_pilot_depth, m2_pilot)

    # blind holes for the door's anti-rotation pins, drilled up from the deck underside
    for px, py in pin_xy:
        deck = deck - _cyl_z(px, py, Z_DECK0 - 0.5, Z_DECK0 + pin_hole_depth, pin_hole_d)

    return deck


# -------------------------------------------------------------- door
@lru_cache(maxsize=None)
def door_zero():
    """Disc + battery bay ribs + screw holes/counterbores + drain hole + the
    anti-rotation pins (fused on, one solid) that key the deck against rotation.
    No cable hole -- wires now enter through the sleeve's DC jack housing instead."""
    disc = _cyl_z(0, 0, 0, door_t, deck_d)

    long_rib = _box(-10.0, 10.0, 15.0, 16.5, door_t, door_t + bay_rib_h)
    long_rib = long_rib + _box(-10.0, 10.0, -16.5, -15.0, door_t, door_t + bay_rib_h)
    end_rib = _box(18.5, 20.0, -7.0, 7.0, door_t, door_t + bay_rib_h)
    end_rib = end_rib + _box(-20.0, -18.5, -7.0, 7.0, door_t, door_t + bay_rib_h)
    door = disc + long_rib + end_rib

    pins = None
    for px, py in pin_xy:
        pin = _cyl_z(px, py, door_t, Z_DECK0 + pin_engage, pin_d)
        pins = pin if pins is None else pins + pin
    door = door + pins

    for sy in (1, -1):
        door = door - _cyl_z(0, sy * screw_r, -1, door_t + 1, m2_clear)
        door = door - _cyl_z(0, sy * screw_r, -1, 1.5, m2_head)
    door = door - _cyl_z(drain_hole_xy[0], drain_hole_xy[1], -1, door_t + 1, drain_hole_d)
    return door


# -------------------------------------------------------------- cap / tube
@lru_cache(maxsize=None)
def cap_zero():
    plug = _cyl_z(0, 0, Z_TUBE1 - cap_plug_h, Z_TUBE1 + 0.01, tube_id - cap_plug_fit)
    top = _cyl_z(0, 0, Z_TUBE1, Z_CAP1, sleeve_od)
    top_edge = top.edges().group_by(Axis.Z)[-1]
    top = chamfer(top_edge, 1.0)
    skirt = _cyl_z(0, 0, Z_TUBE1 - cap_skirt_h, Z_TUBE1, sleeve_od) - _cyl_z(0, 0, Z_TUBE1 - cap_skirt_h - 1, Z_TUBE1 + 1, tube_od + cap_skirt_fit)
    return plug + top + skirt


@lru_cache(maxsize=None)
def tube_zero():
    return _cyl_z(0, 0, Z_SEAT, Z_TUBE1, tube_od) - _cyl_z(0, 0, Z_SEAT - 1, Z_TUBE1 + 1, tube_id)


# ----------------------------------------------------------------- coupon
@lru_cache(maxsize=None)
def coupon_neck_zero():
    """Test ring: ID 38, OD stepped in three bands to bracket the real (measured)
    tube ID against the vendor-nominal 44.5. Bands, bottom to top: 44.4 (0..3.3),
    44.2 (3.3..6.7), 44.0 (6.7..10)."""
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
        "sleeve": sleeve_zero(),
        "deck": deck_zero(),
        "door": door_zero(),
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
