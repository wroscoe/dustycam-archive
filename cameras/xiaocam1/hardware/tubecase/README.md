# tubecase v2

Everything lives inside the 2" clear acrylic tube -- nothing is outside Ø50.8. A
printed base liner cup sits inside the tube at the bottom and carries the
bq25185 charger and the 500 mAh LiPo standing vertically; a mid plate sits on
the liner's rim, screwed down, and carries the XIAO ESP32S3 Sense camera
cradle; a cap plugs the top. A barrel jack passes straight through the base
floor, plug hanging out of the bottom. Two M2 screws through the tube wall
(drilled by hand at assembly time, using guide holes modelled in the tube)
lock the whole chassis to the tube. No mounting insert.

Full contract: `DESIGN.md` in this directory. Replaces v1 (bayonet-twist
sleeve + separate deck/door), archived at `archive/v1_sleeve/`.

## Parts

- **base** (printed, one solid) -- Ø44.1/Ø40.9 liner cup, standing on its
  floor. Battery-bay floor and wall ribs, charger-slot wall ribs and PCB
  floor pads (all fused into the cylindrical wall), two Ø5 bosses cast into
  the wall near the rim (vertical M2 pilots for the mid-plate screws, radial
  M2 pilots through the wall for the tube screws), a barrel-jack hole with a
  counterbore from below, and a drain hole through the floor.
- **mid_plate** (printed flat, cradle up, one solid) -- disc that seats on
  the liner's rim, two counterbored M2 clearance holes over the base's
  bosses, a tangential wire notch cut past the rim, and the camera cradle
  (pocket + lips + walls + pedestal + wire channel, carried over unchanged
  from v1's `pantilt`-derived geometry) standing up off the top.
- **cap** (printed, plug down) -- plug with an O-ring groove cut into its
  cylindrical face, chamfered top disc. Plugs the tube's open top.
- **tube** (purchased, modelled) -- 2" OD 50.8 / ID 44.5 clear acrylic
  cylinder, the full height of the assembly, with two Ø2.2 radial guide
  holes at z 35.0 for the tube screws (drilled by hand at assembly time).
- **charger_bq25185**, **camera_xiao**, **battery_1578** -- imported vendor
  STEP occurrences (`../../ref/bq25185`, `../../ref/xiao`, `../../ref/lipo500`),
  all standing vertically this round (charger on its USB edge, battery on a
  short end, camera lens pointing +X).
- **battery_swell_envelope** -- checks-only labelled box over the battery
  footprint (+1.5 mm thickness swell, +0.5 mm/side lateral), not printed.
- **jack_envelope** -- checks-only labelled, distinctly coloured envelope
  (flange + barrel + body/nut) for the panel-mount DC barrel jack -- no
  vendor STEP for this connector, only user-measured/estimated numbers.
- **coupon_neck** -- unchanged from v1: a small test ring (prints in
  minutes) with three stepped OD bands (44.4/44.2/44.0) to find which one the
  real acrylic tube (vendor-nominal ID 44.5, not measured) actually grips.
  The bands now test the liner/cap fit rather than a sleeve neck.

## Assembly order

1. Thread the nut onto the barrel jack from below, through the base's floor
   hole and counterbore, so the flange seats in the counterbore and the
   body/nut projects up inside the cup.
2. Screw the bq25185 charger and slide the LiPo into their bays standing
   vertically inside the base (charger PCB edge rests on the floor pads;
   battery stands on the floor between its bay ribs). Neither is screwed
   down -- both are captured in place once the mid plate is on.
3. Screw the mid plate onto the base's two bosses (M2 self-tap, through the
   mid plate's counterbored clearance holes into the base's vertical
   pilots), routing the charger/battery leads out through the wire notch.
4. Slide the XIAO ESP32S3 Sense into the cradle from the open (USB) end.
5. Fit the assembled chassis (base + mid plate + charger + battery + camera)
   up into the tube from the bottom.
6. Drill the tube at the two guide-hole positions (z 35.0, along X) and fit
   2x M2 screws through the tube wall into the base's radial pilots, locking
   the chassis to the tube.
7. Press the cap onto the tube's top (plug into the tube ID, O-ring seated in
   its groove against the tube's inner wall).

## Print notes

- base prints standing on its floor (as modelled, no reorientation); mid
  plate prints flat with its underside on the bed (cradle prints standing up
  off the disc); cap prints rotated 180 deg about X (plug up, top disc down
  on the bed).
- The cap's O-ring groove upper flank is a 2 mm 90 deg overhang when printed
  plug-up; acceptable at this span, or bridge/support if the first print
  shows sag.
- Print `coupon_neck` first (a few minutes) to find which of the three OD
  bands (44.4/44.2/44.0, bottom to top) actually grips the real tube, since
  the acrylic tube's ID (44.5) is vendor-nominal and not measured -- the
  bands now settle the base/mid-plate liner fit and the cap plug fit.
- Caliper the real DC barrel jack before printing: `jack_body_d` (11.0),
  `jack_flange_d`/`jack_flange_t` (10.0/2.0), `jack_barrel_d` (7.4) are
  estimated envelope numbers, not measured, and are also what `jack_envelope`
  uses for the interference checks.
- Drilling the tube: mark and drill at z 35.0 from the tube's bottom face,
  along the X axis (through the guide holes already modelled in the tube
  part), on both sides, before fitting the M2 tube screws.

## Commands

```bash
S=~/.claude/skills/cad; P=$S/.venv/bin/python; export PYTHONPATH=$S/scripts/packages/cadgen/src
$P $S/scripts/gen tubecase.step.py --write
$P $S/scripts/gen print_base.step.py print_midplate.step.py print_cap.step.py coupon_neck.step.py --write
$P $S/scripts/inspect validate print_base.step.py    # etc. per print entry
$P $S/scripts/inspect interfere tubecase.step.py --tolerance 1
$P checks.py
$P $S/scripts/export print_base.step.py --stl print/print_base.stl   # etc.
```

## Check results (see checks.md for the full tables)

- `inspect validate` on `print_base.step.py`, `print_midplate.step.py`,
  `print_cap.step.py`, `coupon_neck.step.py`: **PASS**, each exactly one
  solid (`occurrenceCount: 1, failureCount: 0`). Confirmed independently in
  Python (`len(shape.solids()) == 1`) for `base_zero()` and `mid_plate_zero()`.
- `inspect interfere tubecase.step.py --tolerance 1`: **clean** except the
  deliberately-coincident `battery_1578` vs `battery_swell_envelope` pair
  (the envelope is a checks-only label, not a printed feature).
- `checks.py`: **PASS, exit 0**. 34 static checks, all PASS; pairwise
  interference (35 pairs, all 0.0000 mm^3 except the skipped battery/envelope
  pair); every insertion-sweep sample 0.0000 mm^3. Static check highlights:

| check | value | unit | ok |
|---|---|---|---|
| jack body to liner bore | 0.45 | mm (>= 0.4) | PASS |
| jack body to battery rib face | 1.5 | mm (>= 1.0) | PASS |
| charger PCB corner radius vs bore | 3.93 | mm (>= 1.0) | PASS |
| charger component corner vs bore | 1.17 | mm (>= 0.5) | PASS |
| charger top edge + 12mm plug room vs Z_MID0 | 0.4 | mm (>= 0) | PASS |
| battery top vs mid plate underside | 3.0 | mm (>= 2.0) | PASS |
| mid-plate boss bottom vs jack body top | 16.3 | mm (>= 5.0) | PASS |
| radial pilot vs vertical pilot separation | 1.65 | mm (>= 1.0) | PASS |
| cradle top vs cap plug underside | 5.85 | mm (>= 2.0) | PASS |
| SD-card top vs cap plug underside | 3.237 | mm (>= 2.0) | PASS |
| lens tip x vs tube inner wall | 4.0 | mm (>= 3.99) | PASS |
| wire notch vs cradle footprint / bosses | 0.0 / 0.0 | mm^3 (<= 1.0) | PASS |
| lens height above floor bottom | 69.62 | mm | PASS |
| overall height (Z_CAP1) | 89.5 | mm (== 89.5) | PASS |
| overall body diameter (tube_od) | 50.8 | mm (== 50.8) | PASS |

Every part's max radius is within the tube OD (25.40) and every internal
part (base, mid plate, charger, camera, battery, its envelope, jack
envelope, the cap plug) is within the tube ID (22.25); full per-part rows
are in `checks.md`.

Sample counts: pairwise interference 35 pairs tested (9 parts, C(9,2)=36,
minus the deliberately skipped battery/envelope pair); insertion sweeps --
charger vs base (7 steps, dz 0..30), battery vs base (7 steps), mid plate vs
base (3 steps, dz 0..10), camera vs mid plate (2 samples, +5/+25), whole
chassis vs tube (10 steps, dz 0..90), cap vs tube+camera (3 steps, dz
0..10) -- every sample is 0.0000 mm^3.

One informational note, not a failure: the design's estimate of the
charger's tallest-component reach (`charger_components_x1 = 10.94`, used in
the "component corner vs bore" check) is conservative -- the actual imported
vendor STEP measures a max reach of 9.37 mm, so real clearance to the bore
is larger than the spec check assumes. Safe direction; no action needed.

## Snapshots

See `snaps/`: assembly iso, opposite iso, transparent iso, two internal-stack
reveals (`--hide` the tube and cap, camera "90:12" and "0:12") showing the
base/charger/battery stack below the mid plate and the camera cradle above
it, and one print-orientation iso per printed part (base, mid plate, cap).
Reviewed all eight: the outer tube/cap views show a plain chamfered cylinder
with the two drill-guide holes at z 35 (correct -- everything really is
inside the tube skin); the internal views show the charger/battery/ribs
correctly seated in the base below the mid plate, and the camera cradle
with the XIAO board (lens, SD card, FPC rail) correctly seated above it; the
print-orientation views show the base's two bosses and jack floor hole (no
volumetric clash even though they overlap in a top-down silhouette -- the
boss lives at z 31.5-43.5, the jack hole at z 0-5, confirmed separated by the
checks), the mid plate's cradle/pedestal/notch/counterbored screw holes, and
the cap's stepped profile (top-disc flange -> plug -> O-ring groove near the
tip). Nothing floating, no feature on the wrong side, no missing rib.

## STL exports

`print/print_base.stl`, `print/print_midplate.stl`, `print/print_cap.stl`
(all new this round); `print/coupon_neck.stl` (unchanged from v1).

## Completion level

**Mechanically plausible prototype.** Geometry builds, every printed part is
one valid solid, all pairwise-interference and insertion-path checks pass at
0.0000 mm^3, all 34 static checks pass. Not printed yet. First-print checks:
the coupon-neck band that grips the real tube, the M2 self-tap pilots (both
the mid-plate boss pilots and the radial tube-screw pilots), the 0.4/side
cradle pocket and 0.2 mm lip gap after shrink, the O-ring groove's 2 mm
overhang on the cap, and -- since these numbers are estimated, not measured
-- whether the real DC barrel jack's nut/body and flange actually fit the
floor hole/counterbore as modelled (caliper it and adjust
`jack_body_d`/`jack_flange_d`/`jack_flange_t`/`jack_barrel_d` if not).

## Not in scope

Mounting feature, antenna holder, wire modelling, screws as solids, an
O-ring on the base (wall too thin) -- per DESIGN.md.
