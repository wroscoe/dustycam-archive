# tubecase v2 — everything inside the 2" tube (base liner + mid plate + cap)

Contract 2026-09-12, approved by the user ("yes include the screws. go"). Replaces v1
(`archive/v1_sleeve/`). Sketch: `sketch_v2.png` / `sketch_v2.py` (drawing only, not the model).

Nothing is outside Ø50.8: the acrylic tube is the whole skin, bottom to top. A printed base
liner cup sits inside the tube at the bottom and carries the charger and battery standing
vertically; a mid plate sits on the liner's rim and carries the camera cradle; a cap plugs the top.
Barrel jack through the base floor, plug hanging out of the bottom. Two M2 screws through the
tube wall lock the chassis. No mounting insert.

## Frame

mm. Origin on the tube axis at the bottom face (tube bottom edge and base floor bottom are
flush at z 0). Z up. +X = lens direction. Parts modelled at installed pose.

## Purchased parts (vendor STEP in `../../ref/`, same facts as v1)

- XIAO ESP32S3 Sense `ref/xiao/`: board frame origin base-PCB bottom-left, +x long edge, USB-C at
  x=0, z=0 PCB bottom, lens +z. PCB 20.95 x 17.78 x 1.25; expansion PCB to x 21.25; stack top
  13.96; lens axis (3.53, 8.25); SD card to x -3.11 at z 6.85..8.5.
- bq25185 `ref/bq25185/`: PCB 31.75 x 25.4 x 1.57, z=0 back face (flat), components +z to 6.37.
  USB-C shell x 11.4..20.35, y 18.49..26.39 (1.0 past the +y edge), z 0.57..4.77. JST-PH sockets
  on the y=0 edge at x 7.48..15.38 and 16.37..24.27, plugs insert from -y. Holes Ø2.5 at
  (2.54, 2.54) (29.21, 2.54) (2.54, 22.86) (29.21, 22.86) — unused here.
- LiPo 1578 `ref/lipo500/`: 36 x 29 x 4.75, origin plan bottom-left, z=0 bottom. Lead exits a
  short (29 mm) end. Bay rule: +1.5 thickness swell, +0.5/side lateral.
- 2" acrylic tube: OD 50.8, ID 44.5 nominal (not measured; coupon bands 44.0/44.2/44.4 settle the fit).
- Barrel jack (user measured): panel hole Ø7.5, 13.0 from the flange seat to the lug ends.
  Estimated: nut/body Ø11.0 behind the panel, flange Ø10.0 x 2.0, barrel Ø7.4.

## Parameters

```
tube_od, tube_id, tube_len = 50.8, 44.5, 87.5
tube_fit = 0.4                         # diametral -> liner_od = 44.1 (base and mid plate)
base_wall = 1.6                        # base_id = 40.9  (r 20.45)
floor_t = 4.5
base_h = 43.5                          # liner rim = mid plate seat  (Z_MID0)
mid_t = 4.0                            # Z_MID1 = 47.5
boss_d, boss_h = 5.0, 12.0             # mid-plate bosses inside the liner wall, top at Z_MID0
boss_xy = ((18.75, 0.0), (-18.75, 0.0))
m2_pilot, m2_clear, m2_head, m2_cb_depth = 1.7, 2.2, 4.0, 1.5
pilot_depth = 6.0                      # vertical pilots from the boss top (mid plate screws)
tube_screw_z, tube_screw_pilot_depth = 35.0, 5.0   # radial pilots Ø1.7 along X from the outside of the liner into the bosses
tube_hole_d = 2.2                      # drill guide holes modelled in the tube part
rib_w, rib_h_floor, rib_z1 = 1.5, 4.0, 32.5       # floor ribs 4 tall; wall ribs from floor_t to rib_z1
bat_l, bat_w, bat_t, bat_swell, bat_side = 36.0, 29.0, 4.75, 1.5, 0.5
bay_x0, bay_x1, bay_y = -6.0, 0.25, 15.0          # battery bay (x thickness incl. swell = 6.25, y = 29 + 2*0.5)
ch_x = 3.0                             # charger PCB back face plane (PCB x 3.0..4.57, components to 10.94)
ch_slot_w, ch_slot_x0 = 2.1, 2.75      # PCB slot x 2.75..4.85 between rib pairs at the y ends
ch_rib_y0 = 16.3                       # slot ribs run from |y| 16.3 to the wall
ch_pad_z1 = 5.7                        # PCB bottom edge rests on pads at z 5.7 (USB shell bottom then at 4.7)
jack_xy = (-14.5, 0.0)
jack_hole_d, jack_cb_d, jack_cb_depth = 7.5, 10.5, 2.2
jack_depth, jack_body_d, jack_flange_d, jack_flange_t, jack_barrel_d = 13.0, 11.0, 10.0, 2.0, 7.4
drain_d, drain_xy = 2.0, (13.0, -13.0)
lens_to_tube, cap_plug_fit = 4.0, 0.3
cap_plug_h, cap_top_t, cap_chamfer = 8.0, 2.0, 1.0
oring_w, oring_groove_d, oring_z_from_top = 3.3, 40.25, 3.5    # 40 x 2.5 metric O-ring; groove centre 3.5 below the tube top
notch_w, notch_r0, notch_angle_deg = 6.0, 18.5, -60.0          # mid plate wire notch
# cradle: identical numbers to v1 (pocket 0.4/side, lips 0.95 over the PCB with a 0.2 gap, lip h 2, walls 2 to 6 above
# the PCB, back 3.0 with a 6 x 1.5 wire channel, rail 2 at the FPC end bx 21.65..23.65, open at the USB end bx -0.5,
# pedestal 2.0 tall under the rail with the channel continued down its -X face)
```

## Derived (expected values)

```
Z_MID0 = base_h = 43.5 ; Z_MID1 = 47.5
Z_BOARD_TOP = Z_MID1 + 2.0 (pedestal) + 23.65 = 73.15 ; Z_LENS = 69.62 ; SD top = 76.26 ; cradle top ~73.65
pcb_x = tube_id/2 - lens_to_tube - 13.96 = 4.29
Z_TUBE1 = 87.5 ; cap plug z 79.5..87.5 ; cap top z 87.5..89.5 ; overall 89.5
charger: PCB z 5.7..31.1, y ±15.875 ; battery z 4.5..40.5 ; mid plate underside 43.5
jack body z 4.5..15.2 at x -20.0..-9.0 ; mid-plate boss at -x: z 31.5..43.5 (16 above the jack body)
```

## Placement of purchased parts (board frame -> world)

- charger: `Plane(origin=(3.0, 15.875, 31.1), x_dir=(0,-1,0), z_dir=(1,0,0))`
  (bx -> -Y, by -> -Z, bz -> +X; standing on its USB edge; JST sockets at the top edge, plugs from above,
  at world (x 4.57..10.94, y ±0.5..8.4); USB shell at the bottom, y ±4.5, bottom z 4.7).
- battery: `Plane(origin=(-6.0, 14.5, 4.5), x_dir=(0,0,1), z_dir=(1,0,0))` (bx -> +Z: standing on a
  short end, 36 tall; by -> -Y; bz -> +X). Solid x -6..-1.25, y ±14.5, z 4.5..40.5.
  `battery_swell_envelope`: box x -6..0.25, y ±15, z 4.5..40.5 (checks only).
- camera: `Plane(origin=(pcb_x, -17.78/2, Z_BOARD_TOP), x_dir=(0,0,-1), z_dir=(1,0,0))` (USB up, lens +X).
- `jack_envelope` (checks only): flange cyl Ø10 z 0.2..2.2 + barrel Ø7.4 z 2.2..4.5 + body Ø11 z 4.5..15.2, axis at jack_xy.

## Parts

### base (printed, standing on its floor)
- Cup: cylinder Ø44.1 z 0..43.5 minus bore Ø40.9 z floor_t..44. 0.5 chamfer on the bottom outer edge.
- Battery bay ribs on the floor (1.5 wide, 4 tall, z 4.5..8.5): along Y at x -7.5..-6.0 and 0.25..1.75
  spanning y ±15; end ribs at y ±(15.0..16.5) spanning x -7.5..1.75.
- Battery wall ribs (z 4.5..32.5): x -7.5..-6.0, from |y| 15.0 out to the wall (extend to |y| 21.5 and
  intersect with a cylinder r 20.95 so they fuse into the wall), both sides.
- Charger slot ribs (z 4.5..32.5): x 0.25..2.75 and 4.85..6.35, from |y| 16.3 out to the wall, both sides
  (same fuse trick). Floor pads x 2.75..4.85, |y| 6.0..16.3, z 4.5..5.7 carry the PCB edge; the USB shell
  (|y| ≤ 4.5) hangs 0.2 above the floor.
- Mid-plate bosses: cylinders Ø5 at boss_xy, z Z_MID0 - boss_h .. Z_MID0 (fused to the wall; they
  overlap the wall since 18.75 + 2.5 > 20.45). Vertical pilots Ø1.7 x 6 from the boss top.
- Tube-screw pilots: Ø1.7 along X from the outside (r 22.1) inward 5.0 + wall, at (±x, y 0, z 35.0), i.e.
  through the liner wall into each boss. They must not meet the vertical pilots (vertical pilot bottom
  at 37.5; radial pilot top at 35.85 — check ≥ 1.0 apart).
- Jack: floor hole Ø7.5 through at jack_xy; counterbore Ø10.5 x 2.2 from below.
- Drain Ø2 through the floor at drain_xy.
- Cut order: cup → ribs, pads, bosses → bore already cut before adding ribs? No: build the solid cup,
  cut the bore, then ADD ribs/pads/bosses (they live inside the bore), then cut pilots, jack, drain.
  One solid.

### mid_plate (printed flat, underside on the bed, cradle up)
- Disc Ø44.1 z 43.5..47.5. Screw holes Ø2.2 at boss_xy with Ø4 x 1.5 counterbores from the top.
- Wire notch: tangential width 6 from r 18.5 outward past the rim at notch_angle_deg.
- Cradle + pedestal exactly as v1 `deck_zero` (copy from `archive/v1_sleeve/tubecase_lib.py`, re-based
  on Z_MID1 and pcb_x). No charger pilots, no pin holes, no bayonet notches.
- One solid.

### cap (printed top-down)
- Plug Ø(tube_id - cap_plug_fit) = 44.2, z Z_TUBE1 - 8 .. Z_TUBE1. O-ring groove: annular cut width 3.3,
  bottom Ø40.25, centred at Z_TUBE1 - 3.5. Top disc Ø50.8 z Z_TUBE1 .. +2, 1.0 chamfer on the top outer
  edge. One solid. (Print note: the groove's upper flank is a 2 mm 90° overhang when printed top-down;
  acceptable, or bridge.)

### tube (purchased, modelled)
- Cylinder OD 50.8 ID 44.5 z 0..87.5, with two Ø2.2 radial holes along X at z 35.0 (drill guide).

## Files (this directory)
`tubecase_lib.py`, `tubecase.step.py` (assembly, AssemblyHelper labels: base, mid_plate, cap, tube,
charger_bq25185, camera_xiao, battery_1578, battery_swell_envelope, jack_envelope),
`print_base.step.py`, `print_midplate.step.py`, `print_cap.step.py` (print orientation; cap rotated 180°
about X), `coupon_neck.step.py` (keep as is — the bands now test the liner/cap fit), `checks.py`,
`checks.md`, `README.md`. Delete `print_sleeve.step.py`, `print_deck.step.py`, `print_door.step.py`
(archived).

## checks.py (fail closed: exit 1 on any failure, exception or NaN; write checks.md)
1. Pairwise interference of every pair, tolerance 1.0 mm³ (skip battery vs its envelope). Vendor STEP
   booleans that throw → substitute the bounding box and say so.
2. Static table:
   - every part max radius ≤ 25.4 (nothing outside the tube OD); every internal part max radius ≤ 22.25
   - jack body to liner bore ≥ 0.4 ; jack body to battery rib face (x -7.5) ≥ 1.0
   - charger PCB corner radius (sqrt(4.57² + 15.875²)) vs bore r 20.45 ≥ 1.0 ; charger component corner
     (10.94, 15.875) vs bore ≥ 0.5
   - charger top edge + 12 (plug room) ≤ Z_MID0 ; battery top vs mid plate underside ≥ 2.0
   - mid-plate boss bottom (31.5) vs jack body top (15.2) ≥ 5
   - radial pilot vs vertical pilot separation ≥ 1.0
   - cradle top and SD top vs cap plug underside ≥ 2.0 ; lens tip x vs tube inner wall ≥ 3.99
   - lens height above the base floor bottom (report) ; overall height 89.5 ; overall diameter 50.8
   - wire notch clear of the cradle footprint and of the bosses
3. Insertion paths: charger translated +dz (0..30 step 5) vs base = 0; battery same; mid plate + cradle
   translated +dz (0..10 step 5) vs base = 0; camera +5/+25 vs mid plate = 0; whole chassis (base, mid
   plate, charger, battery, jack envelope, camera) translated -dz (0..90 step 10) vs tube = 0;
   cap +dz (0..10 step 5) vs tube and camera = 0.

## Commands
```bash
S=~/.claude/skills/cad; P=$S/.venv/bin/python; export PYTHONPATH=$S/scripts/packages/cadgen/src
$P $S/scripts/gen tubecase.step.py --write
$P $S/scripts/gen print_base.step.py print_midplate.step.py print_cap.step.py coupon_neck.step.py --write
$P $S/scripts/inspect validate <entry>      # each print entry: exactly one solid
$P $S/scripts/inspect interfere tubecase.step.py --tolerance 1
$P checks.py
$P $S/scripts/export print_base.step.py --stl print/print_base.stl   # etc.
```

## Not in scope
Mounting feature, antenna holder, wire modelling, screws as solids, O-ring on the base (wall too thin).
