# ARCHIVED servo v2 (2026-09-08). Superseded by v3 (well base, rear tilt servo, centred axis) in ../../

# xiao_pantilt CAD (hardware/pantilt) — servo version (v2)

Geared pan-tilt head for the XIAO ESP32S3 Sense with two 9 g micro servos
(MG90S / SG90 body). Spec: `../../SPEC.md`. Built 2026-09-08 with the cad
skill (build123d). The N20 gearmotor version it replaced is in `archive/n20/`.

## What changed from v1 (N20)

- Motors are 9 g servos (sarg `mg90s-micro-servo`, vendor STEP, verified). Both
  mount the classic way: body through a 23.0 x 12.2 pocket in a 3 mm plate,
  flange screwed to the plate's inner/under side, spline + pinion on the far side.
- Tilt servo lies horizontally INSIDE the yoke fork, under the cradle's sweep,
  flange against the left arm's inner face. Nothing sticks out of the fork.
- Tilt sector and pinion are OUTSIDE the left arm: the sector rides on a
  Ø5 stub shaft that is part of the cradle and passes through the arm. A cap
  (`gear_cover`) encloses sector + pinion + servo boss.
- Servos are positional (~180 deg), so the ratios changed: pan 30T -> 26T
  (servo +-78 for pan +-90), tilt 18T -> 28T sector (servo travels 140 deg for
  tilt -30..+60; servo neutral corresponds to tilt +15).
- No DRV8833; servos drive from GPIO. Pan gear rim needed a Ø14 journal (bore 7).

## Files

| file | what |
|---|---|
| `pantilt_lib.py` | all geometry + `build_parts(pan, tilt)` / `build_assembly()`; parameters at the top |
| `xiao_pantilt.step.py` | generator entry (zero pose), declares the sidecar |
| `xiao_pantilt.step` | exported STEP of the zero pose |
| `xiao_pantilt.params.js` | CAD Viewer sidecar: `pan_deg` / `tilt_deg` sliders, gear spins derived |
| `sweep.py` | interference sweep + static checks, writes `clash_table.md` |
| `clash_table.md` | 130-pose sweep result (backlash 0.15) |
| `clash_corners_backlash0.md` | 5-pose gear check at zero backlash |
| `snaps/` | review PNGs, `gears_nocover` view, pan GIF, tilt GIF with the cover hidden |
| `archive/n20/` | the N20 gearmotor version |

Imported parts from sarg live in `../../ref/` (`sarg cad get sarg/<part> -o ref/<name>`):
`seeed-xiao-esp32s3-sense` (vendor, verified), `mg90s-micro-servo` (vendor, verified).

## Commands (run from this directory)

```bash
S=~/.claude/skills/cad; P=$S/.venv/bin/python
export PYTHONPATH=$S/scripts/packages/cadgen/src
$P $S/scripts/gen xiao_pantilt.step.py --write
$P $S/scripts/inspect interfere xiao_pantilt.step.py --tolerance 1
$P sweep.py                                             # 130 poses, ~100 s
PANTILT_BACKLASH=0 $P sweep.py --corners --out clash_corners_backlash0.md
$P $S/scripts/snapshot --input xiao_pantilt.step.py --hide '#o1.2.5' \
   --params '{"animate":{"tilt_deg":{"from":-30,"to":60}}}' --output snaps/tilt.gif
```

Viewer: `http://127.0.0.1:3245/home/wroscoe/code/dustycam/cameras/xiao_pantilt?file=hardware/pantilt/xiao_pantilt.step.py`

## Layout (world: pan axis = Z, camera looks +X, tilt axis = Y through the lens)

- Base Ø90 x 26, hollow under a 3 mm top plate; pan servo pocket at (-28.15, 0), body
  along Y; journal bore Ø14.3 x 8, cable bore Ø7.
- Gear band Z 31.5..36.5 (servo boss top to spline top): pan pinion 30T on the servo,
  pan gear 26T under the yoke plate. Plate Z 37..40, X -23..6, Y +-15.15.
- Arms 3 thick at Y +-12.15..15.15, Z to 80. Left arm: servo pocket X -16.8..6.2,
  Z 44.75..56.95, plus an ear tab to X 12.6 for the front flange screw.
- Tilt axis Z 74. Tilt pinion 18T straight below at Z 50.85, sector 28T (100 deg arc),
  both in the band Y -20.65..-25.65 outside the left arm. Cover Y -15.15..-28.65,
  X -19.8..18, Z 37.85..82.
- Cradle: board pocket per the tripod case, USB slot in the bottom rail, Ø5 stub
  shafts both sides (arm bores Ø5.3).
- Overall about 90 wide x 94 tall (cradle top) at the zero pose.

## Verification that ran

- `inspect validate`: all authored solids valid; the camera (vendor STEP) reports
  `selfIntersecting`, same as the raw import.
- `inspect interfere` at zero pose: clean, 19 pairs tested.
- `sweep.py`: 130 poses, cross-group pairs, 0 overlaps > 1e-6 mm^3.
- Zero-backlash corners: 0 gear penetration.
- Static: lens on the tilt axis within 0.003 mm; centre distances 28.15 / 23.15;
  sector 5.5 outside the arm face; sector tip 15 vs cover cavity 17.8; cover bottom 1.5
  above the pan pinion; cradle at tilt +60 clears the tilt servo by 2.1; servo travel
  156 / 140 deg.
- Snapshots: iso x2, gear side, front, left, top, two posed stills, cover-hidden view,
  pan GIF, tilt GIF (cover hidden).

Sweep/corner findings fixed in source this round: pan servo ear clipped the base wall
(base Ø86 -> Ø90); servo body top clipped the cover side wall (cavity widened to the
pocket outline); pan gear was rotated twice in the pose code (own spin + group), which
only showed up at zero backlash on this ratio.

## Modeling simplifications (not yet real)

1. Pinion spline sockets are round Ø4.8; the real spline is 21T. Sector bore is round
   on a Ø5 shaft; print a D or add a grub screw.
2. No fasteners: servo flange screws (M2, holes exist in the servo model, not in the
   plates), cover attachment, gear-to-yoke screws.
3. Cradle stub shafts on both sides mean the arms flex to snap the cradle in;
   alternatively split the right shaft into a screw pin.
4. No pan hard stops, no foot holes, no fillets. Servo leads not routed.
5. Printed journal, no bearing. Board retention in the cradle is friction only.
6. Pan servo body top stands 1.3 above the base plate through its pocket (normal for
   this mount); the tilt servo does the same through the arm, inside the cover.
