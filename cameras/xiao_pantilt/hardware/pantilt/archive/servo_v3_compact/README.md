# ARCHIVED v3 compact pan-tilt (2026-09-08). Superseded by v4 pan-only tube version in ../../

# xiao_pantilt CAD (hardware/pantilt) — v3 compact servo version

Geared pan-tilt head for the XIAO ESP32S3 Sense with two 9 g micro servos
(MG90S / SG90 body), laid out to fit under a clear cover. Spec: `../../SPEC.md`.
Built 2026-09-08 with the cad skill (build123d). Earlier versions: `archive/n20/`
(N20 gearmotors) and `archive/servo_v2/` (servos, tall layout, side gear cover).

## What v3 changes (all for height and cover compatibility)

- **Pan stage in a well.** Servo, 30T pinion and 26T gear sit inside the base under a
  closing ring (Ø104, top at Z 44). The yoke plate rotates 1 mm under that ring, so the
  88 mm-wide pinion never meets the cover. The ring is the cover seat.
- **Tilt axis through the board centre.** Board stays vertical (USB down, sensor
  landscape); the lens is 6.95 mm below the axis. Cradle swing radius 19.1 (was 24).
- **Tilt servo behind the cradle**, standing vertically inside the fork, flange on the
  left arm's inner face, body through an open-back pocket. 22T pinion -> 30T sector
  outside the left arm. No gear cover.
- **Journal post is part of the pan gear** (prints gear-face-down); the gear rides on a
  thrust ring on the well floor. Tilt pivots are 5 mm metal pins.

Result: head about 73 mm across and 35 mm tall above the cover seat (v2: 88 x 72).
Total height 79 (v2: 98).

## Cover compatibility (from the sweep with the cover as a part)

| Cover | Sweep | Margin | Notes |
|---|---|---|---|
| 4" acrylic dome, 95 ID, with a 10 mm straight skirt | PASS | 3.7 mm at the ceiling | needs the skirt; a pure hemisphere is too tight at the tilt pinion |
| 4.5" to 6" domes | not run | comfortable | 6" B0DR8LZ9YT is 88 tall, far more than needed |
| Wide-mouth pint jar, 76 ID | FAIL | -8 mm | the tilt pinion behind the cradle reaches r 46 from the pan axis; the jar wall is at r 38 |
| PET 110-400 jar, ~105 ID | not run | ~6 mm radial | fits by geometry |

To fit a 76 mm jar the tilt drive would have to change: direct-drive tilt (servo in the
arm, no gears) or the v2-style servo-below layout, which costs height.

## Files

| file | what |
|---|---|
| `pantilt_lib.py` | geometry + `build_parts(pan, tilt)`; `PANTILT_COVER=dome4|jar_pint` adds a cover envelope |
| `xiao_pantilt.step.py` / `.step` | generator (zero pose) and exported STEP |
| `xiao_pantilt.params.js` | viewer sidecar: pan/tilt sliders, gear spins derived |
| `sweep.py`, `run_sweeps.sh` | interference sweep + static checks; the script runs all four |
| `clash_table.md` | 130 poses, no cover, backlash 0.15: PASS |
| `clash_table_dome4.md` | same with the 4" dome envelope: PASS |
| `clash_table_jar_pint.md` | same with the pint jar envelope: FAIL (tilt pinion vs jar wall) |
| `clash_corners_backlash0.md` | 5 poses, zero backlash gear check: PASS |
| `snaps/` | iso x2, gear side, front, left, top, two posed stills, pan + tilt GIFs |

Imported parts from sarg in `../../ref/`: `seeed-xiao-esp32s3-sense`, `mg90s-micro-servo`
(both vendor STEP, verified). Re-fetch with `sarg cad get sarg/<part> -o ref/<name>`.

Viewer: `http://127.0.0.1:3245/home/wroscoe/code/dustycam/cameras/xiao_pantilt?file=hardware/pantilt/xiao_pantilt.step.py`

## Commands (run from this directory)

```bash
S=~/.claude/skills/cad; P=$S/.venv/bin/python
export PYTHONPATH=$S/scripts/packages/cadgen/src
$P $S/scripts/gen xiao_pantilt.step.py --write
$P $S/scripts/inspect interfere xiao_pantilt.step.py --tolerance 1
./run_sweeps.sh                      # corners@0 backlash, plain, dome4, jar_pint (~15 min)
```

## Layout numbers (world: pan axis Z, look +X, tilt axis Y)

- Base: Ø96 cup, well radius 45.65, floor plate Z 23..26, wall to Z 41, ring Z 41..44
  from r 37.5 to 52. Pan servo pocket at (-28.15, 0); journal bore Ø14.3 x 8; cable Ø7;
  thrust ring r 9..13 at Z 26..31.3.
- Gear band Z 31.5..36.5. Yoke plate Z 37..40, X -33.25..6, Y ±15.15, corners r 6.
- Arms 3 thick at Y ±12.15..15.15, Z 37..73.4. Left arm: open-back servo pocket
  X -32.25..-20.05, Z 43.5..66.5; plate notch 1.5 deep for the bottom flange ear.
- Tilt axis Z 60.3. Tilt pinion 22T at (-26.15, *, 60.3), sector 30T (100 deg arc),
  band Y -20.65..-25.65. Servo body X -32.05..-20.25, Y -23.6..6.3, Z 39..71.4.
- Cradle Z 47.6..73.3, X -14..3, Y ±11.15; pin bores Ø5.05 (print 4.9 for press fit).

## Verification that ran

- `inspect validate`: authored solids valid; camera vendor STEP self-intersects (same raw).
- `inspect interfere` zero pose: clean, 19 pairs.
- Sweeps: see the cover table. Static: lens 6.95 below the axis (by design), centre
  distances 28.15 / 26.15, servo front face 1.0 clear of the cradle sweep circle, pinion
  1.55 clear of the well wall and 4.5 under the ring, servo travel 156 / 123 deg.

## Modeling simplifications

1. Round spline sockets (use a servo horn pocket when printing), round sector bore on
   the pin (print a D or add a grub screw), no pin retention modeled.
2. No fasteners: servo flange screws, gear-to-yoke screws, ring-to-base, cover fixing.
3. No pan hard stops, no fillets except the plate corners, no cable routing.
4. The tilt servo's front face is 1.0 mm from the cradle's swing circle; bump
   `tilt_center_dist` if prints come out fat.
5. The 1 mm gap between the yoke plate and the ring is a dust path; a lip on the ring's
   underside would close it.
