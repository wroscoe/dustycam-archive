# ARCHIVED N20 version (2026-09-08). Superseded by the servo version in ../../

# xiao_pantilt CAD (hardware/pantilt)

Geared pan-tilt head for the XIAO ESP32S3 Sense with two N20 gearmotors.
Spec: `../../SPEC.md`. Built 2026-09-08 with the cad skill (build123d).

## Files

| file | what |
|---|---|
| `pantilt_lib.py` | all geometry + `build_parts(pan, tilt)` / `build_assembly()`; every dimension is a named parameter at the top |
| `xiao_pantilt.step.py` | generator entry (zero pose), declares the sidecar |
| `xiao_pantilt.step` | exported STEP of the zero pose |
| `xiao_pantilt.params.js` | CAD Viewer sidecar: `pan_deg` / `tilt_deg` sliders, gear spins derived |
| `sweep.py` | interference sweep, writes `clash_table.md` |
| `clash_table.md` | 130-pose sweep result (backlash 0.15) |
| `clash_corners_backlash0.md` | 5-pose gear check at zero backlash |
| `snaps/` | review PNGs + pan/tilt GIFs |

Imported parts (from sarg, `../../ref/`): `amz-xiao-esp32s3-sense.step`
(vendor, verified) and `amz-n20-gearmotor.step` (envelope). Re-fetch with
`sarg cad get sarg/seeed-xiao-esp32s3-sense -o ref/xiao` and
`sarg cad get sarg/n20-gearmotor -o ref/n20` if the folder is missing.

## Commands (run from this directory)

```bash
S=~/.claude/skills/cad; P=$S/.venv/bin/python
export PYTHONPATH=$S/scripts/packages/cadgen/src
$P $S/scripts/gen xiao_pantilt.step.py --write          # rebuild + STEP
$P $S/scripts/inspect interfere xiao_pantilt.step.py --tolerance 1
$P sweep.py                                             # 130 poses, ~100 s
PANTILT_BACKLASH=0 $P sweep.py --corners --out clash_corners_backlash0.md
$P $S/scripts/snapshot --input xiao_pantilt.step.py \
   --params '{"animate":{"pan_deg":{"from":-90,"to":90}}}' --output snaps/pan_sweep.gif
```

Viewer: start the cad-viewer skill and open
`http://127.0.0.1:3245/home/wroscoe/code/dustycam/cameras/xiao_pantilt?file=hardware/pantilt/xiao_pantilt.step.py`.

## Layout (world frame: pan axis = Z, camera looks +X, tilt axis = Y through the lens)

- Base Ø76 x 28, hollow below a 3 mm top plate, journal bore Ø16.3 x 8, cable bore Ø8.
- Pan: N20 in a saddle at (-30.15, 0), 12T pinion -> 48T gear (4:1) under the yoke plate.
- Yoke: plate 34.5 x 40.3 x 3 at Z 35..38, arms 3 thick at Y ±17.15..20.15, Ø16 journal post.
- Tilt: N20 through the left arm at 215° from the tilt axis, 12T pinion -> 36T sector (3:1, 100° arc).
- Cradle: board pocket per the tripod case numbers, USB slot in the bottom rail, pivots Ø3.2.
- Z_TILT = 61 (lens centre); ranges pan ±90, tilt -30..+60.

## Verification that ran

- `inspect validate`: all authored solids valid. The camera (vendor STEP) reports
  `selfIntersecting`; the raw import reports the same, so that is the vendor file.
- `inspect interfere` at zero pose: clean, 25 pairs tested.
- `sweep.py`: 130 poses, cross-group pairs, 0 overlaps > 1e-6 mm^3.
- Zero-backlash corners: 0 gear penetration (polyline involute sits inside the true curve).
- Static: lens centre on tilt axis within 0.003 mm; centre distances 30.15 / 24.15;
  sector-to-arm gap 1.0; sector lowest point 5.6 above the plate.
- Snapshots: iso x2, front, left, two posed stills, exploded, pan/tilt GIFs. No section
  view: the headless renderer ignored the clip setting.

Two sweep findings were fixed in source: the yoke plate corner (radius 35) hit the pan
motor shaft tip, so the motor face now sits 4.5 below the base top; that pushed the
motor body through the floor, so the base grew to 28.

## Modeling simplifications (not yet real)

1. Pinion bores are round Ø3.05, not D. The imported shaft doesn't spin, so a D would
   clash at every pose but one. Add the flat in the slicer or as a print-time parameter.
2. No fasteners: motor clamp screws, pivot screws (modeled as Ø3 pins), gear-to-yoke screws.
3. No pan hard-stop lugs, no DRV8833 pocket, no foot holes, no fillets.
4. Board retention in the cradle is friction only; front is open.
5. Printed journal instead of a bearing. A 686 bearing conflicts with the Ø8 cable bore;
   a thin-section 20 x 27 x 4 would fit around the post if wanted.
6. N20 dimensions are envelope grade (caliper the shaft and gearbox before printing).
