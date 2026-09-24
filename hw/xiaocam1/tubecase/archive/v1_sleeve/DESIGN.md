# tubecase — static XIAO Sense tube camera with a bq25185 solar compartment

Contract written 2026-09-12. Replaces the pan mechanism in `../pantilt` (kept as is).
No motor. One clear 2" acrylic tube holds the camera; a printed sleeve under it
holds the Adafruit bq25185 solar charger and a 500 mAh 1S cell.

## Frame

Units mm. World origin on the tube axis at the door's bottom face (the bench).
Z up. +X = camera look direction. All parts modelled at their installed pose.

## Purchased parts (all vendor STEP, in `../../ref/`)

| part | file | frame facts |
|---|---|---|
| XIAO ESP32S3 Sense | `ref/xiao/amz-xiao-esp32s3-sense.step` | board frame: origin base-PCB plan bottom-left, +x along the long edge, USB-C at x=0, z=0 PCB bottom, lens +z. PCB 20.95 x 17.78 x 1.25; expansion PCB to x 21.25; stack top z 13.96; lens axis (3.53, 8.25); SD card sticks out to x -3.11 at z 6.85..8.5; FPC pins to x 21.12 |
| bq25185 charger, Adafruit 6091 | `ref/bq25185/adafruit-6091-...step` | board frame: origin PCB plan bottom-left, z=0 PCB bottom (back face, flat). PCB 31.75 x 25.4 x 1.57. Components on +z to 6.37. USB-C shell x 11.4..20.35, y 18.49..26.39 (overhangs the +y edge by 1.0), z 0.57..4.77. Two JST-PH right-angle sockets on the y=0 edge at x 7.48..15.38 and 16.37..24.27, z to 6.37, plugs insert from -y. Holes Ø2.5 at (2.54,2.54) (29.21,2.54) (2.54,22.86) (29.21,22.86) |
| LiPo 500 mAh, Adafruit 1578 | `ref/lipo500/ada-1578-lipo-500.step` | 36 x 29 x 4.75, origin plan bottom-left, z=0 bottom. Bay rule: height 4.75 + 1.5 swell = 6.25, lateral +0.5/side |
| 2" acrylic tube | model as a cylinder | OD 50.8, ID 44.5 (vendor nominal, NOT measured), cut length `tube_len` |
| Panel-mount DC barrel jack | no vendor STEP; envelope only | User-measured: panel hole Ø7.5; 13.0 mm from the OUTER face of the panel to the end of the solder lugs. ESTIMATED (caliper before printing): nut/body envelope Ø11.0 behind the panel, flange Ø10.0 x 2.0 proud of the outer face, threaded barrel Ø7.4 through the panel. |

## Parameters (names to use in `tubecase_lib.py`)

```
tube_od, tube_id, tube_len = 50.8, 44.5, 32.0
tube_fit = 0.4            # diametral: neck_od = tube_id - tube_fit = 44.1
neck_wall = 1.6           # neck_id = neck_od - 2*neck_wall = 40.9  (r 20.45)
neck_h = 8.0
wall = 2.0                # sleeve wall
sleeve_od = 55.0          # sleeve_id = 51.0 (r 25.5)
door_t = 2.0
deck_t = 4.5
deck_clear = 0.2          # deck_d = sleeve_id - 2*deck_clear = 50.6 ; door same
rib_w, rib_r0 = 5.0, 17.0 # ribs on the Y axis: x ±rib_w/2, y from rib_r0 to the wall (+0.5 overlap)
screw_r = 21.0            # door screws (+ rib bottom pilots) at (0, ±screw_r). No deck screws.
m2_pilot, m2_clear, m2_head = 1.7, 2.2, 4.0
pilot_depth = 6.0         # rib bottom pilots only, from door_t upward
bayonet_twist_deg = 20.0
notch_w, notch_r0 = 6.0, 16.5   # deck notches, tangential width, from this radius outward
bat_l, bat_w, bat_t = 36.0, 29.0, 4.75      # 36 along X
bat_swell, bat_side = 1.5, 0.5
bay_rib_w, bay_rib_h = 1.5, 3.0
charger_pilot_depth = 3.5
lens_above_seat = 19.0
lens_to_tube = 4.0        # lens tip to the tube inner wall
cap_plug_h, cap_top_t, cap_skirt_h = 3.0, 2.0, 5.0
cap_plug_fit, cap_skirt_fit = 0.3, 0.4     # diametral
shoulder_chamfer = 1.5
drain_hole_d, drain_hole_xy = 2.0, (12.0, -20.0)
pin_d = 4.0               # anti-rotation pins, door -> deck (replace the deck's own screws)
pin_xy = ((21.5, 6.0), (21.5, -6.0))
pin_engage = 3.0          # pin top sits this far above Z_DECK0, inside the deck's blind hole
pin_hole_d = 4.4
pin_hole_depth = 3.5      # blind hole depth in the deck underside (0.5 mm tip clearance)

# panel-mount DC barrel jack housing at -X (replaces the mounting tab and the door
# cable hole)
jack_hole_d = 7.5
jack_depth = 13.0             # outer panel face -> lug ends (measured)
jack_body_d = 11.0            # ESTIMATED nut envelope behind the panel
jack_flange_d, jack_flange_t = 10.0, 2.0   # ESTIMATED, outside
jack_panel_t = 2.0
jack_cavity_w, jack_cavity_h = 15.0, 15.0  # y width, z height of the housing cavity
jack_cavity_z0 = 2.0
jack_z = jack_cavity_z0 + jack_cavity_h / 2       # 9.5, jack axis height
ear_wall = 2.0
brow_proj = 4.0
wing_w, wing_t, wing_hole_d = 7.5, 4.0, 4.5
```

## Derived layout (compute in code from the parameters; these are the expected values)

```
Z_DOOR1   = door_t                      = 2.0
Z_BAT1    = Z_DOOR1 + bat_t             = 6.75   (swell envelope top 8.25)
Z_DECK0   = 19.0                        (rib tops; charger PCB back face is here)
Z_DECK1   = Z_DECK0 + deck_t            = 23.5
Z_SEAT    = Z_DECK1 + (sleeve_id/2 - neck_id/2) = 23.5 + 5.05 = 28.55   (45° cone)
Z_NECK1   = Z_SEAT + neck_h             = 36.55
Z_TUBE1   = Z_SEAT + tube_len           = 60.55
Z_CAP1    = Z_TUBE1 + cap_top_t         = 62.55
```
`Z_DECK0` is a parameter (`deck_z0 = 19.0`), chosen so the charger components
(hanging to Z_DECK0 - 6.37 = 12.63) clear the battery swell top (8.25) by 4.4.

## Parts

### sleeve (printed, standing on its open bottom rim)
- Body: cylinder Ø55 z 0..Z_SEAT. Bore Ø51 z -1..Z_DECK1. Cone bore from r 25.5 at Z_DECK1
  to r 20.45 at Z_SEAT (45°, self-supporting when printed standing). Above Z_SEAT the neck:
  OD 44.1, ID 40.9, z Z_SEAT..Z_NECK1. Chamfer the outer top edge of the Ø55 body by
  `shoulder_chamfer` (drip edge). The shoulder annulus carries the tube's end.
- Two ribs: box x ±2.5, y from rib_r0 (17) to 26.0 (0.5 into the wall), z door_t..Z_DECK0,
  mirrored to -y. Pilots Ø1.7 at (0, ±screw_r): from door_t up `pilot_depth`, for the
  door's screws only (the deck has no screws of its own — see deck/door below).
- Panel-mount DC barrel jack housing at -X (world frame; jack axis along -X at the
  back of the sleeve, plug inserts from -X), replacing the old mounting tab:
    * Housing ("ear") fused to the sleeve at -X: box x from
      -(sleeve_od/2 + jack_depth + jack_panel_t) = -42.5 to -(sleeve_od/2 - 0.5) = -27.0,
      y ±(jack_cavity_w/2 + ear_wall) = ±9.5, z 0 .. jack_cavity_z0 + jack_cavity_h +
      ear_wall = 19.0.
    * Cavity cut: box x -40.5 .. -24.0 (passes through the sleeve wall so the housing
      opens into the compartment; -24 is inside the Ø51 bore, nothing else is there),
      y ±7.5, z 2.0 .. 17.0. The 15 mm flat ceiling is a bridge when printed standing;
      noted in the print notes.
    * Jack hole Ø7.5 along X through the back panel (x -42.5 .. -40.5) at (y 0,
      z jack_z). Overshoot the cut.
    * Brow: a triangular prism (like caseskit.visor) on the back face above the jack:
      in the XZ plane, points (x -42.5, z 17.0), (x -42.5, z 19.0),
      (x -42.5 - brow_proj, z 19.0), extruded y ±9.5. Its underside is the slanted
      face, so it prints standing without support.
    * Wings: two boxes x -42.5 .. -27.0, y from ±9.5 to ±(9.5 + wing_w) = ±17.0,
      z 0 .. 4.0, each with a Ø4.5 vertical through hole at (x -34.75, y ±13.25).
- Cut order: body → add ribs, jack housing (ear + brow + wings) → subtract bores, cone,
  pilots, jack cavity/hole, wing holes. One solid.

### deck (printed flat, underside on the bed) — carries the camera cradle and the charger
- Disc Ø50.6, z Z_DECK0..Z_DECK1.
- Two bayonet notches: tangential width notch_w, from r notch_r0 outward past the rim, at
  angles 90° - bayonet_twist_deg (= 70°) and 270° - bayonet_twist_deg (= 250°). (Installed
  pose has the ribs at 90°/270°; the deck goes in from below with the notches over the
  ribs, then twists +20° CCW seen from above, and lands on the rib tops.)
- No screws of its own: retained down by the sleeve rib tops, up by the cone above (its
  disc is too wide to pass the cone/neck), and against rotation by the door's two
  anti-rotation pins (see door, below), which engage two blind holes Ø`pin_hole_d` (4.4)
  x `pin_hole_depth` (3.5) drilled up into the deck underside at world `pin_xy`
  ((21.5, 6.0), (21.5, -6.0)).
- Charger, hanging, components DOWN, PCB back face against the deck underside. Board
  frame → world: `Plane(origin=(-12.7, -15.875, Z_DECK0), x_dir=(0,1,0), z_dir=(0,0,-1))`
  i.e. world x = by - 12.7, world y = bx - 15.875, world z = Z_DECK0 - bz.
  JST sockets then face -X (plugs at x -12.7..-21), USB-C at +X (overhang to +13.7),
  long PCB edges at y ±15.875 (1.1 from the rib faces at 17 — check ≥ 1.0).
  Four blind pilots Ø1.7 x charger_pilot_depth up into the deck underside at the hole
  positions, world (±10.16, ±13.335).
- Camera cradle on the deck top, board VERTICAL, USB-C and SD card UP, lens looking +X.
  Board frame → world: `Plane(origin=(pcb_x, -17.78/2, Z_BOARD_TOP), x_dir=(0,0,-1), z_dir=(1,0,0))`
  (board x → -Z, board y → +Y, board z → +X). With
  `Z_LENS = Z_SEAT + lens_above_seat`, `Z_BOARD_TOP = Z_LENS + 3.53`,
  `pcb_x = tube_id/2 - lens_to_tube - 13.96` (= 4.29).
  Cradle geometry = the verified holder from `../pantilt/pantilt_lib.py::holder_zero`
  (pocket 0.4/side, lips 0.95 over the PCB top corners with a 0.2 gap, lip height 2,
  side walls 2 thick reaching 6 above the PCB bottom) with these changes:
    * back plate 3.0 thick (was 2) with a wire channel 6 wide x 1.5 deep cut into its
      board-facing surface, centred on by = 8.89, running the full length and out the
      rail end (the XIAO BAT pads are on the PCB underside near the USB end; the wires
      lie in the channel and leave at the bottom).
    * the closed end (rail, 2 thick, no USB opening) is at the FPC end: bx 21.65..23.65.
      The open end is at the USB end: walls, lips and back end at bx -0.5.
    * no tongue boss. Instead a pedestal: box from the rail bottom down to the deck top,
      same x/y footprint as the cradle back+walls, with the wire channel continued down
      its -X face as a 6 x 1.5 slot to the deck top.
- The deck + cradle + pedestal + charger pilots = ONE printed solid (`deck_zero`). The
  charger is a separate imported occurrence.

### door (printed flat, ribs up) — the only screwed part; goes on last, straight up
- Disc Ø50.6, z 0..door_t, sits inside the sleeve bottom flush.
- Screw holes Ø2.2 at (0, ±screw_r = ±21.0) with Ø4.0 x 1.5 counterbores from below,
  into the sleeve's rib bottom pilots (this leaves the pilot 3 mm of rib on the inner
  side, vs. 0.65 mm at the old screw_r = 18.5).
- Two anti-rotation pins Ø`pin_d` (4.0) at world `pin_xy` ((21.5, 6.0), (21.5, -6.0)),
  fused to the disc (one solid), from the door top (z door_t) up to `Z_DECK0 + pin_engage`
  (pin_engage = 3.0). They pass beside the charger's USB-C end (charger x max 13.7) and
  just outside the battery bay (bay half-length 18.5) — checks.py confirms the actual
  clearances.
- Battery bay ribs 1.5 wide x 3 tall on the door top: bay inside = (bat_l + 2*bat_side) x
  (bat_w + 2*bat_side) = 37 x 30 centred. Two long ribs at y ±(15.0..16.5), x ±10; two end
  ribs at x ±(18.5..20.0), y ±7. (Sleeve ribs start at y 17: 0.5 clear.)
- Drain hole Ø2 at drain_hole_xy. No cable hole any more (removed): wires now enter
  through the sleeve's DC jack housing instead, routed from the lugs through the wall
  opening (the jack cavity cut, which opens directly into the sleeve bore) to the
  charger's DC input pads.
- Battery occurrence: box/vendor STEP at x ±18, y ±14.5, z door_t..Z_BAT1. Also build a
  labelled `battery_swell_envelope` box 37 x 30 x 6.25 at the same place for the checks
  (not part of the print).

### jack_envelope (checks only, not printed)
Estimated envelope for the DC barrel jack, coloured distinctly in the assembly: union of
a cylinder Ø7.4 along X from x -44.5 to -29.5 (threaded barrel), a cylinder Ø11 from
x -40.5 to -29.5 (nut/body behind the panel), and a cylinder Ø10 from x -44.5 to -42.5
(flange outside), all on the jack axis (y 0, z jack_z). Must intersect nothing.

### cap (printed top-down)
- Plug Ø(tube_id - cap_plug_fit) z Z_TUBE1 - cap_plug_h .. Z_TUBE1.
- Top disc Ø sleeve_od z Z_TUBE1 .. Z_CAP1, 1.0 chamfer on the top outer edge.
- Skirt: OD sleeve_od, ID tube_od + cap_skirt_fit, z Z_TUBE1 - cap_skirt_h .. Z_TUBE1.
- One solid.

### tube (purchased)
Cylinder OD 50.8 ID 44.5, z Z_SEAT .. Z_TUBE1.

### coupon_neck (printed test ring, separate entry)
Ring ID 38, z 0..10, OD stepped: 44.0 for z 6.7..10 (top), 44.2 for z 3.3..6.7, 44.4 for
z 0..3.3. Label the bands in the docstring. Prints in minutes; the tube slides on from
the top and stops at the band that fits.

## Files to produce (all in this directory)

- `tubecase_lib.py` — parameters, derived Z's, `sleeve_zero()`, `deck_zero()`, `door_zero()`,
  `cap_zero()`, `tube_zero()`, `battery_zero()`, `battery_envelope_zero()`, imported
  `charger_zero()` / `xiao_zero()` placed, `build_parts()` → dict of labelled shapes,
  `build_assembly()` with `cadgen.assembly.AssemblyHelper` (labels: sleeve, deck, door,
  cap, tube, charger_bq25185, camera_xiao, battery_1578, battery_swell_envelope,
  jack_envelope — the last coloured distinctly, checks-only).
  Follow the style of `../pantilt/pantilt_lib.py` (lru_cache, `_box`, `_cyl_z`,
  `cadgen.step_scene.import_step`, Plane placement).
- `tubecase.step.py` — assembly entry (`gen_step()` returns the compound).
- `print_sleeve.step.py`, `print_deck.step.py`, `print_door.step.py`, `print_cap.step.py`,
  `coupon_neck.step.py` — single parts in print orientation on the bed (sleeve: as modelled,
  bottom on bed; deck: as modelled; door: as modelled; cap: rotated 180° about X, top on bed).
- `checks.py` — fail-closed check script (exit 1 on any failure, exceptions, NaN):
  1. pairwise interference of every pair in `build_parts()` (skip the envelope vs battery
     pair, and camera vs the XIAO vendor STEP self-intersection is known — if the vendor
     model fails a boolean, substitute its bounding box and SAY SO in the output).
     Tolerance 1.0 mm³. Note: the charger PCB back face touches the deck underside and the
     deck bottom touches the rib tops: touching = 0 volume, fine. Includes `jack_envelope`
     vs every other part (must be 0).
  2. static numbers (print a table with PASS/FAIL):
     - charger long edge to rib face ≥ 1.0
     - charger components bottom vs battery swell top ≥ 2.0
     - cradle max radius (no board) ≤ neck_id/2 - 0.5 (must pass up through the neck)
     - lens tip x vs tube inner wall ≥ lens_to_tube - 0.01
     - cradle top and SD-card top vs cap plug underside ≥ 2.0
     - pin engagement into the deck == pin_engage (pin top z minus Z_DECK0)
     - pin to charger min XY clearance ≥ 1.0 (from the parameters)
     - pin to battery envelope min XY clearance ≥ 1.0 (from the parameters)
     - rib pilot inner wall = screw_r - m2_pilot/2 - rib_r0 ≥ 1.5
     - deck rim vs cone: deck top z == Z_DECK1 and deck r ≤ sleeve_id/2 - 0.15
     - door ribs vs sleeve ribs ≥ 0.4
     - lens height above seat == lens_above_seat
     - overall height and diameter; overall reach incl. the jack flange and brow
       (44.5 / 46.5) — replaces the old mounting-tab reach check
     - jack cavity clearance around the (estimated) body ≥ 1.0 in y and z
       ((jack_cavity_w - jack_body_d)/2 and (jack_cavity_h - jack_body_d)/2)
     - wire room from the lug ends to the sleeve inner bore ≥ 3.0 (x: -29.5 vs -25.5)
     - jack lug ends vs the charger's JST plugs (x -12.7..-21): min X gap ≥ 5.0
     - rib bearing: intersect the deck with a box x ±2.5, y 17..25.3, z Z_DECK0..Z_DECK0+0.5
       — volume must be ≥ 90 % of the box (the deck really sits on the ribs after the twist)
  3. bayonet path: rotate {deck, charger} about Z by -t for t in 0,2,...,20 and intersect
     with the sleeve: all 0. At t = 20 also translate the pair down by dz for dz in
     0,2,...,24 and intersect with the sleeve: all 0 (it must come in from below). Then
     the door (with its anti-rotation pins, no cable hole any more), translated straight
     up from z -25 to 0 in 5 mm steps, against the sleeve, deck, and charger: all 0 (it
     goes on last).
  4. camera insertion: translate the XIAO up by +5 and +25 (sliding out of the cradle top)
     and intersect with the deck: 0 (the lips must not trap it).
  Write results to `checks.md`.
- `README.md` — short: what it is, parts, assembly order, print notes, commands, check
  results, completion level "geometry builds / mechanically plausible prototype" only if the
  checks pass.

## Commands (cwd = this directory)

```bash
S=~/.claude/skills/cad; P=$S/.venv/bin/python; export PYTHONPATH=$S/scripts/packages/cadgen/src
$P $S/scripts/gen tubecase.step.py --write
$P $S/scripts/gen print_sleeve.step.py print_deck.step.py print_door.step.py print_cap.step.py coupon_neck.step.py --write
$P $S/scripts/inspect validate tubecase.step.py
$P $S/scripts/inspect interfere tubecase.step.py --tolerance 1
$P checks.py
$P $S/scripts/export print_sleeve.step.py --format stl   # etc. (see $S/scripts/export --help)
```

## Not in scope
O-ring on the neck, a mounting bracket, antenna holder, wire modelling, screws as solids.
