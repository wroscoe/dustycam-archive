# tubecase

Static XIAO ESP32S3 Sense tube camera with a bq25185 solar/USB charge
compartment. Replaces the pan mechanism in `../pantilt` (kept as-is, unmodified).
No motor: a 2" clear acrylic tube sits on a printed sleeve; a deck inside the
sleeve carries the camera cradle (derived from `../pantilt/pantilt_lib.py::holder_zero`)
and the bq25185 charger hanging underneath it; a door closes the sleeve's open
bottom and carries the 500 mAh 1S LiPo; a cap plugs the tube's top.

Full contract: `DESIGN.md` in this directory.

## Parts

- **sleeve** (printed) -- Ø55 body with a panel-mount DC barrel jack housing
  (replaces the old mounting tab), a 45 deg cone stepping down to a
  Ø44.1/Ø40.9 neck, two ribs (with blind M2 pilots for the door's screws
  only), chamfered drip edge.
- **deck** (printed, one solid) -- disc + bayonet notches + the camera cradle
  (pedestal, back plate with a wire channel, side walls/lips, closed rail at
  the FPC end) + charger mounting pilots + two blind holes for the door's
  anti-rotation pins. No screws of its own: held down by the rib tops, held
  up by the cone above, held against rotation by the door's pins.
- **door** (printed, one solid) -- disc + battery-bay locating ribs + screw
  holes/counterbores (into the rib bottom pilots) + two anti-rotation pins
  (fused on) that key into the deck's blind holes + drain hole. No cable hole
  any more -- wires now enter through the sleeve's jack housing instead. The
  only screwed part; goes on last, straight up.
- **cap** (printed) -- plug + chamfered top disc + skirt, plugs the tube top.
- **tube** (purchased) -- 2" OD 50.8 / ID 44.5 clear acrylic, modelled as a
  plain cylinder (no vendor STEP for this part).
- **charger_bq25185**, **camera_xiao**, **battery_1578** -- imported vendor
  STEP occurrences (`../../ref/bq25185`, `../../ref/xiao`, `../../ref/lipo500`).
- **battery_swell_envelope** -- checks-only labelled box, not printed.
- **jack_envelope** -- checks-only labelled, distinctly coloured envelope for
  the panel-mount DC barrel jack (no vendor STEP -- there is no CAD model for
  this connector, only user-measured/estimated numbers), not printed.
- **coupon_neck** -- separate small test ring (prints in minutes) with three
  stepped OD bands (44.4 / 44.2 / 44.0) to find which one the real acrylic
  tube (vendor-nominal ID 44.5, not measured) actually grips.

### DC barrel jack housing (new this round)

A panel-mount DC barrel jack is fused to the sleeve at -X, replacing the
mounting tab and the door's cable hole -- power now enters through the
sleeve wall instead of through the door. The housing ("ear") is a box behind
the sleeve wall with a cavity that opens directly into the Ø51 bore; the jack
drops in from -X, panel-side out, nut tightened from inside the sleeve (with
the door off, reaching in through the bore). A brow (a small triangular
visor, like a case-kit drip visor) sits above the jack opening and sheds
water off the panel face; its underside is the slanted/overhang face, sized
to print standing without support. Two wings (small mounting ears, each with
a Ø4.5 through hole) flank the housing for an external bracket or cable
clamp. Wires route from the jack's solder lugs, through the wall opening
(the cavity cut), across the sleeve bore, to the charger's DC input pads
(not modelled -- see "Not in scope").

Jack facts: panel hole Ø7.5 and 13.0 mm outer-face-to-lug-end are
user-measured. The nut/body envelope (Ø11.0 behind the panel), the flange
(Ø10.0 x 2.0 proud of the outer face), and the threaded barrel (Ø7.4 through
the panel) are ESTIMATED -- caliper the real connector (nut diameter across
flats or envelope circle, flange OD/thickness) before printing and adjust
`jack_body_d`/`jack_flange_d`/`jack_flange_t` if they differ.

## Assembly order

1. Press the panel-mount DC barrel jack into the sleeve's jack housing from
   -X (panel-side out); reach in through the sleeve's open bottom (door off)
   to tighten the nut against the inside of the panel.
2. Screw the bq25185 charger to the deck underside (4x M2 self-tap into the
   blind pilots at world (+-10.16, +-13.335)).
3. Drop the deck (+charger) in from the sleeve's open bottom with its bayonet
   notches over the sleeve ribs, then twist per DESIGN.md's bayonet geometry
   until it lands on the rib tops. No screws here -- the deck is retained down
   by the rib tops and up by the cone above it; rotation is keyed later by the
   door's pins.
4. Slide the XIAO ESP32S3 Sense into the cradle from the open (USB) end.
5. Route the jack's solder-lug wires (and the battery/charger leads, once the
   battery is seated in step 7) across the sleeve bore to the charger's DC
   input pads; solder up before the tube goes on (wire routing itself is not
   modelled).
6. Slide the acrylic tube over the neck down onto the shoulder.
7. Press the cap onto the tube top (plug into the tube ID, skirt over the
   tube OD).
8. Seat the 500 mAh LiPo in the door's battery-bay ribs.
9. Fit the door (with its two anti-rotation pins) into the sleeve's bottom
   opening straight up -- the pins enter the deck's blind holes and key it
   against rotation -- then two M2 self-tap screws from below, through the
   door's counterbored holes, into the rib bottom pilots. The door is the last
   part installed and the only one with screws.

## Print notes

- sleeve, deck, door print as modelled (no reorientation); cap prints rotated
  180 deg about X (top disc down on the bed).
- The sleeve's cone bore is self-supporting at 45 deg when printed standing
  on its open bottom rim, per DESIGN.md.
- The jack housing's cavity ceiling is a 15 mm flat bridge (jack_cavity_w)
  when the sleeve prints standing; most FDM printers bridge that span fine,
  but check the first print. The brow's underside is a slanted overhang
  (angled well off vertical) and needs no support.
- Print `coupon_neck` first (a few minutes) to find which of the three OD
  bands (44.4/44.2/44.0, bottom to top) actually grips the real tube, since
  the acrylic tube's ID (44.5) is vendor-nominal and not measured.
- Caliper the real DC barrel jack before printing: `jack_body_d` (11.0),
  `jack_flange_d`/`jack_flange_t` (10.0 / 2.0) are estimated envelope numbers,
  not measured, and are also what `jack_envelope` uses for the interference
  checks.

## Commands

```bash
S=~/.claude/skills/cad; P=$S/.venv/bin/python; export PYTHONPATH=$S/scripts/packages/cadgen/src
$P $S/scripts/gen tubecase.step.py --write
$P $S/scripts/gen print_sleeve.step.py print_deck.step.py print_door.step.py print_cap.step.py coupon_neck.step.py --write
$P $S/scripts/inspect validate tubecase.step.py
$P $S/scripts/inspect interfere tubecase.step.py --tolerance 1
$P checks.py
$P $S/scripts/export print_sleeve.step.py --stl print/print_sleeve.stl   # etc.
```

## Check results (see checks.md for the full tables)

- `inspect validate` on `print_sleeve.step.py` and `print_door.step.py`
  (the two parts touched by the jack): **PASS**, each exactly one solid.
  (`print_deck.step.py`/`print_cap.step.py`/`coupon_neck.step.py` untouched
  this round; last validated clean in the previous round.)
- `inspect interfere tubecase.step.py --tolerance 1`: **clean** except the
  deliberately-coincident `battery_1578` vs `battery_swell_envelope` pair
  (the envelope is a checks-only label, not a printed feature) -- and now
  also clean for `jack_envelope` against every other part.
- `checks.py`: **PASS, 22 of 22 static checks**; pairwise interference (44
  pairs, all parts including the new `jack_envelope`), the full bayonet
  rotate+drop-in sweep, the door-insertion sweep, and the
  camera-insertion/lip-trap sweep are all clean at 0. Static check table:

| check | value | unit | ok |
|---|---|---|---|
| charger long edge to rib face | 1.125 | mm (>= 1.0) | PASS |
| charger components bottom vs battery swell top | 4.38 | mm (>= 2.0) | PASS |
| cradle max radius (no board) | 15.276 | mm (<= neck_id/2 - 0.5 = 19.950) | PASS |
| lens tip x vs tube inner wall | 4.0 | mm (>= 3.99) | PASS |
| cradle top vs cap plug underside | 5.97 | mm (>= 2.0) | PASS |
| SD-card top vs cap plug underside | 3.357 | mm (>= 2.0) | PASS |
| pin engagement into deck | 3.0 | mm (== pin_engage = 3.0) | PASS |
| pin to charger min XY clearance | 5.814 | mm (>= 1.0) | PASS |
| pin to battery envelope min XY clearance | 1.0 | mm (>= 1.0) | PASS |
| rib pilot inner wall | 3.15 | mm (>= 1.5) | PASS |
| deck disc top z | 23.5 | mm (== Z_DECK1 = 23.500) | PASS |
| deck max radius vs cone | 25.3 | mm (<= sleeve_id/2 - 0.15 = 25.350) | PASS |
| door ribs vs sleeve ribs | 0.5 | mm (>= 0.4) | PASS |
| lens height above seat | 19.0 | mm (== 19.0) | PASS |
| overall height (Z_CAP1) | 62.55 | mm | PASS |
| overall body diameter (sleeve_od) | 55.0 | mm | PASS |
| overall reach incl. jack flange (-X) | 44.5 | mm | PASS |
| overall reach incl. jack brow (-X) | 46.5 | mm | PASS |
| jack cavity clearance (y) | 2.0 | mm (>= 1.0) | PASS |
| jack cavity clearance (z) | 2.0 | mm (>= 1.0) | PASS |
| wire room, lug ends to sleeve bore | 4.0 | mm (>= 3.0) | PASS |
| jack lug ends to charger plugs | 8.5 | mm (>= 5.0) | PASS |
| rib bearing fill fraction | 99.5 | % (>= 90%) | PASS |

Sample counts: pairwise interference 44 pairs tested (10 parts, C(10,2)=45,
minus the deliberately skipped battery/envelope pair), bayonet rotation sweep
11 steps (t=0..20 by 2) x {deck,charger}, bayonet drop-in sweep 13 steps
(dz=0..24 by 2) x {deck,charger}, door-insertion sweep 6 steps (z=-25..0 by
5) x {sleeve,deck,charger}, camera-insertion sweep 2 steps (+5/+25 mm) --
every one of those is 0.0000 mm^3.

The old "overall reach incl. mounting tab" check no longer applies (the tab
is gone) and has been replaced by the jack flange/brow reach rows above; the
mounting tab's own parameters (`tab_len`/`tab_w`/`tab_t`/`tab_hole_d`) and the
door's `cable_hole_d`/`cable_hole_xy` are removed from `tubecase_lib.py`
entirely, per this round's brief.

**Geometry bug caught and fixed during this round** (not a spec issue --
an implementation mistake, corrected before reporting results): the brow's
triangular-prism sketch (`Polygon` on `Plane(x_dir=(1,0,0), z_dir=(0,1,0))`)
initially had clockwise vertex winding, so `extrude(..., amount=2*ear_y)`
built it face-first in -Y instead of +Y, floating the brow off to one side
with zero overlap with the ear box -- `sleeve_zero().solids()` returned 2
(a disconnected compound), even though `inspect validate` reports a single
occurrence regardless (it doesn't check inter-solid connectivity within one
compound). Caught by checking `len(shape.solids())` after noticing the first
snapshot render looked like the brow was floating apart from the housing;
fixed by reordering the polygon's vertices (CCW), reconfirmed
`sleeve_zero().solids() == 1` and re-rendered before finalizing.

## Spec inconsistencies from earlier rounds (now resolved)

`neck_id` is fixed at the formula value (40.9, r 20.45) in DESIGN.md itself
(the printed 41.3/r 20.65 was the error, not the formula); `tube_len = 32.0`
gives the SD-card-top-to-cap-plug-underside clearance a full 3.357 mm; the
deck's own screws were removed entirely (replaced by the door's
anti-rotation pins), so the old "deck screw head reach vs neck bore" check no
longer applies; and the pins were moved to `pin_xy = ((21.5, 6.0), (21.5,
-6.0))`, giving exactly 1.0 mm clearance to the battery envelope (was 0.5 mm
at the first pin position) while staying 5.8 mm clear of the charger.

Completion level: **mechanically plausible prototype**. Geometry builds,
every printed part is one valid solid, interfaces and insertion paths pass
geometric review, all 22 static checks pass. Not printed yet. First-print
checks: the neck band that grips the real tube (coupon), the 0.4/side cradle
pocket and 0.2 lip gap after shrink, the 20 deg bayonet twist by hand, the
Ø4.4 pin holes over Ø4 pins, the M2 self-tap pilots (Ø1.7) in the rib bottoms
and deck underside, the 15 mm bridge over the jack cavity, and -- most
importantly, since these numbers are estimated, not measured -- whether the
real DC barrel jack's nut/body and flange actually fit the housing as
modelled (caliper it and adjust `jack_body_d`/`jack_flange_d`/`jack_flange_t`
if not).

## Snapshots

See `snaps/`: assembly iso, opposite iso, transparent iso, an internal-stack
reveal, an iso from the back showing the new jack housing (`--camera
"200:20"`), and one print-orientation iso per printed part (sleeve
regenerated this round to show the jack housing/brow/wings).
The installed CAD skill's `scripts/snapshot --mode section` does not expose a
configurable cut plane in this version's job schema (it always renders the
default XY plane at Z=0, `"CUT LOCATOR: XY @ Z=0.000"`, regardless of a
`section`/`render.section` job field); the requested "section through the YZ
plane (X=0) showing the internal stack" was produced instead as a `view` mode
render with `--camera "90:12"` (looking down the X axis, i.e. at the YZ
plane) and `--hide sleeve --hide tube --hide cap` (dropping the three
enclosure parts) to reveal the deck/cradle/charger/battery stack directly --
`snaps/tubecase_internal_stack*.png`.

## STL exports

`print/print_sleeve.stl`, `print/print_door.stl` (both re-exported this
round); `print/print_deck.stl`, `print/print_cap.stl`,
`print/coupon_neck.stl` (unchanged, from the previous round).

## Not in scope

O-ring on the neck, a mounting bracket, antenna holder, wire modelling,
screws as solids (per DESIGN.md).
