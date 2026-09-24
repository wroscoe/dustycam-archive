# ARCHIVED v4 pan-only geared tube version (2026-09-08). Superseded by v5 direct-drive in ../../

# xiao_pantilt CAD (hardware/pantilt) — v4 pan-only tube version

Pan-only camera pod for the XIAO ESP32S3 Sense: one 9 g servo, a 30T:26T spur
stage in a well in the base, the camera in a cradle on a mast bolted to the pan
gear, all under a 2" clear acrylic tube with a printed cap. Built 2026-09-08 with
the cad skill. Earlier versions in `archive/`: `n20` (N20 pan-tilt), `servo_v2`
(servo pan-tilt, tall), `servo_v3_compact` (servo pan-tilt, well base, 4" dome).

## Layout

- **Base** (unchanged from v3): Ø96 cup, well r 45.65 holding servo + gears, floor
  plate Z 23..26, closing ring Z 41..44 with a 2 mm deep groove for the tube
  (r 22.15..25.5). Ring opening r 19.5. Journal bore Ø14.3, cable bore Ø7, thrust ring.
- **Pan gear** 26T with the Ø14 journal post; its top face at Z 37 is the pod platform.
- **Pod** = cradle + mast in one printed part. Board vertical, USB edge down, USB-C
  connector centred on the pan axis so the cable drops through the journal. 15 mm
  under the board for a straight plug (8 mm is enough for a right-angle plug: set
  `usb_plug_space_mm`). Cradle X -4.4..12.6, Y ±11.15, Z 50..75.7; lens at X ~9.6.
  `PANTILT_FIXED_TILT=<deg>` builds the cradle at a fixed tilt (+ = up).
- **Tube**: 2" acrylic, 50.8 OD x 44.5 ID (1/8" wall), cut to 45 mm. Sits in the
  groove at Z 42..87. Pod radius 16.9 leaves 5.4 mm to the wall.
- **Cap**: printed plug (Ø44.3 x 3) + top disc (Ø50.8 x 2). Pod top is 8.3 below it.
- Overall: Ø96 x 89 tall; pod 31.7 above the cover seat.

## Files

| file | what |
|---|---|
| `pantilt_lib.py` | geometry + `build_parts(pan)`; `HAS_TILT = False` |
| `xiao_pantilt.step.py` / `.step` | generator and exported STEP (pan 0) |
| `xiao_pantilt.params.js` | viewer sidecar: pan slider, tube/cap visibility toggle |
| `sweep.py` | 13-pose pan sweep + static checks -> `clash_table.md` |
| `clash_corners_backlash0.md` | 4 poses at zero backlash: PASS |
| `snaps/` | iso (with and without tube), transparent iso, front, left, bottom, pan GIF |

Imported parts from sarg in `../../ref/` (`seeed-xiao-esp32s3-sense`, `mg90s-micro-servo`).

Viewer: `http://127.0.0.1:3245/home/wroscoe/code/dustycam/cameras/xiao_pantilt?file=hardware/pantilt/xiao_pantilt.step.py`

## Commands

```bash
S=~/.claude/skills/cad; P=$S/.venv/bin/python; export PYTHONPATH=$S/scripts/packages/cadgen/src
$P $S/scripts/gen xiao_pantilt.step.py --write
$P $S/scripts/inspect interfere xiao_pantilt.step.py --tolerance 1
$P sweep.py && PANTILT_BACKLASH=0 $P sweep.py --corners --out clash_corners_backlash0.md
```

## Verification that ran

- `inspect validate`: authored solids valid; the camera vendor STEP self-intersects (same raw).
- `inspect interfere` at pan 0: clean, 12 pairs (includes tube and cap).
- 13-pose pan sweep with tube + cap as parts: 0 overlaps. Zero-backlash corners: 0.
- Static: pod r 16.85 vs tube r 22.25; ring opening margin 2.65; cap margin 8.3; plug
  space 15.2; pinion 1.55 from the well wall, 4.5 under the ring; servo travel 156 deg.

## Print notes

- Base upside down (ring face on the bed). Pan gear teeth-down, post up. Pod: back of the
  mast on the bed, cradle walls growing up; the top rail needs a small support or a
  bridge. Cap flat. PLA for the gear, PETG or PLA for the rest.
- Pod bolts to the pan gear top through the foot (screws not modeled). Tube is a drop-in;
  a dab of silicone in the groove holds it. Cap is a friction plug.

## Simplifications

1. Round spline socket on the pinion (use a servo horn pocket); no fasteners modeled.
2. No pan hard stops; the ring opening is a 1 mm dust gap around the pod.
3. Board retention in the cradle is friction only; front open.
4. Cable is not modeled; the USB-C plug is assumed <= 15 mm long overmold.
