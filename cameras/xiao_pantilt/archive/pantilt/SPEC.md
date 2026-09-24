# xiao_pantilt — geared pan-tilt for the XIAO ESP32S3 Sense

Status: MODELED 2026-09-09 — current CAD is **v5 DIRECT-DRIVE PAN-ONLY**
(one 9 g servo on the axis, Ø55 base, 2" acrylic tube + printed cap; see
`hardware/pantilt/README.md`; 13-pose sweep PASSED with tube + cap as parts).
Archived: `archive/n20` (this brief), `archive/servo_v2`,
`archive/servo_v3_compact` (pan-tilt, fits a 4" skirted dome), `archive/servo_v4_tube`
(pan-only geared, Ø96 base). The N20 text below is the original brief; the README is
authoritative where they differ.

## 1. Goal

A two-axis pan-tilt head that carries one XIAO ESP32S3 Sense, driven by two
N20 micro gearmotors through printed spur gears. The primary purpose of
this pass is the CAD mechanism itself: a parametric assembly whose pan and
tilt angles can be swept, animated in the viewer, and checked for
interference at every pose. Electronics and firmware are secondary and
only pinned down far enough to keep the mechanical envelope honest.

Non-goals for this pass: weatherproofing, battery bay, closed-loop control
tuning, and a PCB. Those come after the mechanism is proven.

## 2. Parts (all owned unless noted)

| Role | Part | sarg id | Owned | Facts grade |
|---|---|---|---|---|
| Camera / MCU | Seeed XIAO ESP32S3 Sense | `seeed-xiao-esp32s3-sense` | 1 (currently xiaomic1) | vendor STEP, verified |
| Pan motor | N20 / GA12-N20 gearmotor | `n20-gearmotor` | 3 | envelope, face holes UNMODELED |
| Tilt motor | N20 / GA12-N20 gearmotor | `n20-gearmotor` | (same 3) | envelope |
| Driver | Adafruit DRV8833 dual H-bridge | `ada-3297-drv8833` | 1 | ok, 26 x 18 x 3 |
| Gears, yoke, base, cradle | printed, PETG on Bambu | — | — | — |
| Pan bearing | printed journal (686 conflicts with the cable bore) | — | — | — |
| Tilt pivots | 2 x M3 x 16 socket screw + printed bushings | — | assumed in stock | — |
| Fasteners | M2 x 6 (motor clamps), M3 heat inserts x 6 | — | assumed in stock | — |
| Feedback | none in v1; AS5600 on each axis is the v2 plan | — | NOT OWNED | — |

Motor alternative: the 9g servo family (`mg90s-micro-servo`, 6 owned;
`adafruit-169-micro-servo-towerpro-sg92r`, 8 owned) drops in as a variant
with identical gear geometry. Keep the motor pocket a swappable child part
so the variant is one file, not a redesign.

## 3. Key dimensions from sarg

XIAO ESP32S3 Sense, board frame: origin PCB plan bottom-left, Z=0 PCB
bottom, USB-C edge at X=0, +X along the long edge.
- Envelope 20.95 x 17.78 x 13.96 mm including the Sense expansion board.
- Castellated 7+7 at 2.54 mm pitch; no mounting holes. Retain by the PCB
  edge in a pocket, same approach as the existing tripod case
  (`seeed-xiao-esp32s3-sense-tripod-case-body-lid`, which was checked
  against the vendor STEP at zero interference).
- Lens is on the Sense board, on the top face. Measure its XY center from
  the vendor STEP with `inspect refs`; do not guess. Tilt axis passes
  through that point (section 5).

N20 gearmotor, part frame: X=0 at gearbox mounting face, shaft overhangs to
X=-10, gearbox X=0..9, motor can behind it; body 12 x 10 mm cross-section,
34 mm overall.
- Shaft: 3 mm D-flat, 10 mm long. Assume 2.5 mm across the flat. CALIPER.
- M1.6 face holes are ambiguous in the drawing. Per sarg: clamp the
  gearbox block in a printed saddle instead of relying on the face holes.
- Vin 3-6 V for the owned variant. Fits DRV8833 at 5 V.

## 4. Architecture

Base -> pan platform (yoke) -> tilt cradle -> camera. Two moving bodies,
two motors, both motors mounted on the body one level down from the one
they drive, so no wire crosses a joint it doesn't have to.

```
            [tilt cradle + XIAO]      <- tilt_deg about the Y axis
              |     (tilt sector gear, 36T, on the cradle)
   [yoke]  ---+---  (tilt pinion 12T on N20 #2, N20 clamped in yoke arm)
     |
   (pan gear 48T under the yoke, on the pan axis)
   (pan pinion 12T on N20 #1, N20 clamped in base)
   [base]                             <- fixed root
```

- Pan axis: world Z, through the yoke center. Bearing: 686 ball bearing
  seated in the base, 6 mm printed post on the yoke. Fallback if the
  bearing isn't ordered: printed journal, 6.0 post in 6.3 bore, 8 mm long.
- Tilt axis: world Y, through the lens center. Two M3 shoulder pivots, one
  in each yoke arm, into printed bushings in the cradle.
- Pan axis is HOLLOW, 7 mm bore minimum, so the camera USB-C cable drops
  through the yoke and base without wrapping. Tilt gets a 30 mm slack loop.

## 5. Gears

Module 1.0, 20 deg pressure angle, straight spur, 5 mm face width. Module
1 is the smallest that prints cleanly at 0.4 mm nozzle; anything finer
needs metal gears.

| Stage | Pinion | Driven | Ratio | Center distance | Notes |
|---|---|---|---|---|---|
| Pan | 12T on N20 shaft | 48T full gear on yoke | 4:1 | 30.0 mm + 0.15 backlash | full gear because pan goes both ways past center |
| Tilt | 12T on N20 shaft | 36T SECTOR, 100 deg arc | 3:1 | 24.0 mm + 0.15 backlash | sector saves space; arc = travel + 10 deg |

Derived in code, never typed: pitch diameters (12, 48, 36 mm), center
distances, sector arc from tilt range, pinion bore from the shaft D-flat.
Pinion is a press fit on the D-shaft with a 0.1 mm interference; add an M2
set screw boss on the tilt pinion only if it slips in testing.

Backlash allowance is a parameter (`gear_backlash_mm`, default 0.15). The
interference sweep must run at backlash 0 as well, to prove the tooth
profiles don't intersect even with a perfect print.

## 6. Motion ranges

| Axis | Range | Hard stop | Soft stop |
|---|---|---|---|
| pan_deg | -90 .. +90 | printed lug on base at +-95 | firmware at +-88 |
| tilt_deg | -30 (down) .. +60 (up) | sector end faces at -35 / +65 | firmware at -28 / +58 |

Pan is limited to 180 deg on purpose: the cable goes through the bore
untwisted only if the head never spins continuously. Homing in v1 is by
driving into the hard stop with a current-limited pulse, then counting
motor time. v2 adds AS5600 on each axis.

## 7. Bodies and named features

Every part is a labeled child so the sidecar and inspect can address it.

| Feature id | Body | Fixed to | Notes |
|---|---|---|---|
| `base` | fixed root | world | holds pan bearing, pan N20 saddle, DRV8833 pocket, 3 x M3 foot holes on a 40 mm circle |
| `pan_motor` | N20 #1 | base | shaft vertical, pinion up |
| `pan_pinion` | 12T | pan_motor shaft | rotates `pan_deg * 4` |
| `pan_gear` | 48T | yoke, underside | concentric with pan axis |
| `yoke` | U bracket | pan_gear | two arms, tilt pivots at arm tips, tilt N20 saddle on the left arm |
| `tilt_motor` | N20 #2 | yoke left arm | shaft along Y |
| `tilt_pinion` | 12T | tilt_motor shaft | rotates `tilt_deg * 3` |
| `tilt_sector` | 36T sector | cradle, left side | concentric with tilt axis |
| `cradle` | camera carrier | tilt pivots | pocket for the XIAO per the tripod case, lens window, cable exit down |
| `camera` | XIAO Sense vendor STEP | cradle | placed by its board frame |

Datums to declare in source: `pan_axis` (Z line through yoke center),
`tilt_axis` (Y line through lens center), `pan_mesh_point`,
`tilt_mesh_point`, `cable_bore_axis`.

## 8. Parameters (source + sidecar)

| Name | Default | Range | Drives |
|---|---|---|---|
| `pan_deg` | 0 | -90..90 | yoke + everything above, pan_pinion derived |
| `tilt_deg` | 0 | -30..60 | cradle + camera, tilt_pinion derived |
| `gear_module_mm` | 1.0 | 0.8..1.5 | all gear geometry |
| `gear_backlash_mm` | 0.15 | 0..0.3 | center distance offset |
| `pan_ratio` | 4 | 3..6 | pan gear tooth count = 12 * ratio |
| `tilt_ratio` | 3 | 2..5 | sector tooth count |
| `wall_mm` | 2.0 | 1.6..3 | yoke, base, cradle walls |
| `tilt_arm_clearance_mm` | 1.0 | 0.5..3 | gap between cradle and yoke arms |
| `motor_variant` | `n20` | n20, sg90 | swaps the motor child and saddle |
| `show_camera` | true | bool | style only |

Sidecar (`xiao_pantilt.params.js`, declared from `gen_step()`): exposes
`pan_deg` and `tilt_deg` as sliders, an `animate` sweep, and derives both
pinion rotations from the ratios. Style controls do not touch geometry.

## 9. Validation plan

Deterministic, in this order, all must pass before any snapshot counts:

1. `inspect validate` on the assembly: every solid closed, positive
   volume, no self-intersection.
2. `inspect refs --facts --planes --positioning`: labels present, frames
   where section 7 says.
3. `inspect frame` on `tilt_axis` vs the camera lens center: coincident
   within 0.2 mm in X and Z.
4. `inspect measure` pan mesh center distance = 30.15 +-0.02;
   tilt = 24.15 +-0.02.
5. `inspect measure` cradle-to-yoke-arm gap >= `tilt_arm_clearance_mm`
   at tilt = -30, 0, +60.
6. Interference sweep: pan -90..90 step 15 (13 values) x tilt -30..60
   step 10 (10 values) = 130 poses. At each pose regenerate and run
   `inspect interfere --tolerance 1` on the moving subtree
   (`yoke` and above) against `base` and `pan_motor`, and on `cradle` and
   `camera` against `yoke` and `tilt_motor`. Pass = zero pairs above
   tolerance. Gear pairs are checked separately with tolerance 0.5 and
   backlash 0; contact is allowed, penetration is not.
7. Repeat step 6 at the four range corners with `gear_backlash_mm` = 0.
8. Cable bore: `measure` bore diameter >= 7.0 at every pan angle (it's on
   the pan axis so it shouldn't change; the check is that nothing else
   intrudes).

Visual, after the deterministic pass:
- PNG at (0, 0), (90, 60), (-90, -30), exploded view.
- GIF: pan sweep at tilt 0, tilt sweep at pan 0, then a combined loop
  that returns exactly to (0, 0).
- Section snapshot through the pan axis showing bearing, bore, and gear
  mesh.

Output: `clash_table.md` with pose, pair, intersection mm^3, and pass/fail.

## 10. Print and assembly notes

- PETG, 0.2 mm layers, 4 walls on gears. Gears printed flat, teeth up.
- Yoke printed upright with arms as-is; no supports if the saddle is a
  slot open to the top.
- Motor saddles: 12.2 x 10.2 slot, 9 mm long on the gearbox only, M2
  clamp screw across the open side. Never rely on the N20 face holes
  (sarg: positions unmodeled).
- XIAO retained exactly as in the tripod case pocket. Reuse that pocket's
  numbers; they were verified against the vendor STEP.
- Tilt pivots: M3 screws through the yoke arms into 3.2 mm printed
  bushings in the cradle, with a 0.3 mm washer gap.

## 11. Electrical envelope (only what affects the CAD)

- DRV8833 lives in the base, 26 x 18 x 3 pocket plus 6 mm for headers.
- Power in over one USB-C to the XIAO; XIAO 5 V pin feeds DRV8833 VM.
  Motor current draw at stall on the N20 is the number to confirm before
  trusting the XIAO's 5 V rail; if it's over ~500 mA, add a second USB
  feed to the base.
- Four GPIO from the XIAO down through the bore for the two H-bridges.
  This is a five-wire bundle plus USB; the 7 mm bore is sized for that.

## 12. Assumptions to retire before printing

1. N20 shaft: 3 mm D, 2.5 across flats, 10 mm long. CALIPER.
2. N20 body 12 x 10 x 9 gearbox. CALIPER.
3. Lens center XY on the Sense board: take from the vendor STEP, then
   confirm on the real board.
4. Bearing: a 686 cannot coexist with the Ø8 cable bore, so the CAD uses the
   printed journal. A thin-section 20 x 27 x 4 around the post is the upgrade.
5. Owned N20 gear ratio (which of 30:1 / 100:1 / 298:1 these are) sets
   pan speed; not a CAD input but decides whether 4:1 is too slow.
6. M3 inserts and M2 screws are actually in the drawer.
