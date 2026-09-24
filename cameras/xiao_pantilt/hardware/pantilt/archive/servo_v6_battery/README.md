# ARCHIVED v6 (one-piece pod, friction board mount). Superseded by v7 split pod + slot holder in ../../

# xiao_pantilt CAD (hardware/pantilt) — v6 direct-drive pan-only tube + battery bay

Pan-only camera pod for the XIAO ESP32S3 Sense: one 9 g servo on the pan axis
drives the pod directly, under a 2" clear acrylic tube with a printed cap, with a
1S LiPo pouch in the base. Built 2026-09-09 with the cad skill. Earlier versions in
`archive/`: `n20`, `servo_v2`, `servo_v3_compact` (pan-tilt), `servo_v4_tube`
(pan-only, geared), `servo_v5_direct` (no battery).

## Power (v6)

- Cell: 503035 pouch, 500 mAh, 5 x 30 x 35, on a snap-in bottom lid with a ribbed
  frame (1.5 walls, 3 tall). 1.25 mm between the pouch and the servo bottom.
- Cell -> XIAO BAT pads (charged by the XIAO's own USB-C at ~100 mA, reached by lifting
  the cap). Servo runs straight off the cell: bench-tested Miuzei MG90S is fine at 3.7 V,
  floor 3.5 V (sarg lesson "MG90S (Miuzei) 9 g servo runs straight off a 1S LiPo").
  Firmware cutoff 3.5 V. Load switch on the servo supply + 100 uF at the servo.
- Three wires cross the pan joint (BAT+, GND, servo signal) through the Ø5 hole beside
  the servo and the slot in the pod's foot.

## Layout

- **Base**: Ø55 x 30.15 puck, open bottom closed by the lid, hollow under a 4 mm top
  plate. Servo in the classic 23 x 12.2 pocket on the axis, flange screwed under the
  plate, boss + spline above; servo bottom at Z 7.75 over the pouch. Tube groove
  r 22.15..25.5, 2 deep. Ø5 wire hole at (0, 16.5) beside the servo.
- **Lid**: Ø50.6 x 1.5 disc + pouch frame, drops into the base bottom (screws/snap not
  modeled).
- **Pod** (one print): foot disc Ø20 x 4 sitting on the servo boss with a socket over the
  spline (print as a servo-horn pocket), slot toward +Y for the cable; mast; cradle.
  Board vertical, USB down and centred on the axis; right-angle plug, 12 mm free below.
  Cradle X -4.4..12.6, Y ±11.15, Z 41.9..67.6.
- **Tube**: 2" acrylic, 50.8 OD x 44.5 ID, cut to 55 mm, Z 28.15..83.15. Pod r 16.9.
- **Cap**: printed plug Ø44.3 x 3 + top disc Ø50.8 x 2. Pod top 5.8 below it.
- Overall: Ø55 x 85 tall. Pan = servo angle, ±90.

## Cable path

Right-angle USB-C plug on the board's bottom edge, cable runs +Y across the foot slot,
down through the base hole, service loop in the hollow base, out the open bottom.
±90 of pan is a 180 deg wrap, fine with ~60 mm of slack.

## Files

| file | what |
|---|---|
| `pantilt_lib.py` | geometry + `build_parts(pan)`; `PANTILT_FIXED_TILT=<deg>` for a fixed tilt |
| `xiao_pantilt.step.py` / `.step` | generator and exported STEP |
| `xiao_pantilt.params.js` | viewer sidecar: pan slider, tube/cap toggle |
| `sweep.py` -> `clash_table.md` | 13-pose pan sweep + static checks |
| `snaps/` | transparent iso, iso without tube, bay view (base hidden) |

Imported parts from sarg in `../../ref/` (`seeed-xiao-esp32s3-sense`, `mg90s-micro-servo`).
Tube: Amazon B07JG6NB9V (2" OD x 1-3/4" ID x 12", 1/8" wall) or any 1/8"-wall 2" acrylic tube.

Viewer: `http://127.0.0.1:3245/home/wroscoe/code/dustycam/cameras/xiao_pantilt?file=hardware/pantilt/xiao_pantilt.step.py`

## Commands

```bash
S=~/.claude/skills/cad; P=$S/.venv/bin/python; export PYTHONPATH=$S/scripts/packages/cadgen/src
$P $S/scripts/gen xiao_pantilt.step.py --write
$P $S/scripts/inspect interfere xiao_pantilt.step.py --tolerance 1
$P sweep.py
```

## Verification that ran

- `inspect validate`: authored solids valid; camera vendor STEP self-intersects (same raw).
- `inspect interfere` at pan 0: clean (tube and cap included).
- 13-pose pan sweep: 0 overlaps. Static: pod r 16.85 vs 22.25; cap margin 5.8; foot 4.5
  above the plate; plug space 12.2; servo ears 4.2 inside the hollow; wire hole 2.9 from
  the servo ear and 3.15 inside the groove; pouch 1.25 under the servo; lid frame 0.2
  inside the hollow.

## Print notes

- Base upside down (top face on the bed): groove, pocket and wire hole all vertical.
- Lid flat, frame up. Print 4 parts: base, lid, pod, cap.
- Pod on its foot: mast and cradle grow up; the top rail bridges 22 mm, add a support or
  print the rail as a clip. Cap flat.
- Foot socket: model the servo horn pocket instead of the round socket; the horn screw
  holds the pod down.

## Simplifications

No fasteners (servo flange screws from below, horn screw), no pan hard stops, board
retention by friction, cable not modeled. Servo end stops are the ±90 mechanical limit.
