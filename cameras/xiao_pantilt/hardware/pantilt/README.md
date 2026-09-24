# xiao_pantilt CAD (hardware/pantilt) — v7 split pod, slot holder, horn foot, screwed lid

Pan-only camera pod for the XIAO ESP32S3 Sense: one 9 g servo on the pan axis
drives the pod directly, under a 2" clear acrylic tube with a printed cap, with a
1S LiPo pouch in the base. Built 2026-09-09 with the cad skill. Earlier versions in
`archive/`: `n20`, `servo_v2`, `servo_v3_compact` (pan-tilt), `servo_v4_tube`
(pan-only, geared), `servo_v5_direct` (no battery), `servo_v6_battery` (one-piece pod).

## v7: how the camera mounts, and the split pod

- **Holder** (board cradle) is built in the board's own frame with the retention numbers
  from the verified XIAO tripod case in sarg: pocket 0.4/side, edge lips 0.95 over the PCB
  top corners with a 0.2 gap above the 1.25 PCB, 2 mm walls, bottom rail with a 13.3 mm
  USB opening. The board slides in from the top along both long edges; the rail stops it
  at the bottom; the tube cap (5.5 mm above the pod) stops it lifting out. No screws
  through the board, no glue.
- **Pod base** = foot + mast + tongue. The foot (Ø41.7 x 5.7) has a pocket from below
  shaped like the servo's real single-arm horn (calipered 2026-09-10: 22 long overall,
  Ø6.7 at the pivot tapering to 4.0 at the tip, hub 4 tall assumed), 0.2 clearance,
  1.5 mm roof. Two screws from above: the horn screw through a Ø2.4 hole on the axis,
  and an M2 x 4 self-tap through a Ø2.2 hole 2 mm from the arm tip into the horn's outer
  hole (set `horn_tip_hole_from_tip` after measuring). The horn keys the rotation; the
  two screws stop lift. Wire slot toward +Y. The mast ends in an 8 x 2 x 10 tongue.
- **Joint**: a 4 mm boss on the holder's back takes the tongue (0.15 clearance) with one
  M2 self-tap screw through a Ø1.7 pilot. Different fixed tilts = holders with the socket
  cut at an angle (not modeled yet).
- **Lid**: two Ø4.5 bosses in the base at (±22.5, 0), each joined to the cylindrical
  sidewall by a 2 mm radial web, with Ø1.7 pilots and matching Ø2.2 holes in the lid.
  M2 x 6 self-tap. The lid is the battery door and the servo goes in from below.
- Six printed/bought parts: base, lid, pod base, holder, cap (printed); tube (bought).

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
  r 22.15..25.5, 2 deep. A 5 mm-wide side-entry relief joins the +Y end of the servo
  pocket to the Ø5 wire hole at (0, 16.5), so the MG90S lead can slip into place.
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
| `pantilt_lib.py` | geometry + `build_parts(pan)`; `PANTILT_BOARD_DX/DY` shift the board for the fit check |
| `print_*.step.py` -> `print/` | one generator per printed part in print orientation; STL + 3MF |
| `xiao_pantilt.step.py` / `.step` | generator and exported STEP |
| `xiao_pantilt.params.js` | viewer sidecar: pan slider, tube/cap toggle |
| `sweep.py` -> `clash_table.md` | 13-pose pan sweep + static checks; `--boardfit` = holder vs vendor board at the pocket extremes |
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
- 13-pose pan sweep with tube, cap, lid, pouch (re-run 2026-09-10 after the horn
  pocket change): 0 overlaps. Static: pod r 20.85 vs 22.25; cap margin 5.05; foot 5.0
  above the plate; plug space 10.0; lip gap 0.2; pocket 0.4/side;
  servo ears 4.2 inside the hollow; wire hole 2.9 from the servo ear; pouch 1.25 under the
  servo; lid frame 0.2 inside the hollow.
- Board fit (`sweep.py --boardfit`): holder vs the vendor STEP at nominal and at the six
  pocket extremes (x -0.4, y ±0.4): max 0.005 mm^3 = touching the rail, PASS at the 0.01
  contact threshold the case used.

## Print notes

- Base upside down (top face on the bed): groove, pocket, wire hole and lid lugs all vertical.
- Lid flat, frame up. Pod base on its foot (horn pocket bridges 7.1 mm at the hub, fine). Holder
  standing on its bottom rail, open top up: lips and boss are vertical, no supports.
  Cap top-down. Five prints, none need supports.
- First-print checks (from the case notes): pocket width after shrink, the 0.2 lip gap,
  the tongue fit (0.15), and the tube groove.
- Pod on its foot: mast and cradle grow up; the top rail bridges 22 mm, add a support or
  print the rail as a clip. Cap flat.
- Foot socket: the horn pocket matches the calipered horn; the horn screw plus one M2
  in the outer horn hole hold the pod down. Test-fit the horn in the pocket before
  fitting the servo: the taper and the 0.2 clearance are from one photo measurement.

## Simplifications

Screws are holes only (2 x M2 servo flange from below, 1 x horn screw, 1 x M2 into the
horn tip, 1 x M2 tongue, 2 x M2 lid). No pan hard stops. Wires not modeled. Horn plan
is calipered (22 x 6.7 -> 4.0); hub height 4, arm thickness 2 and the outer-hole
position 2 mm from the tip are still assumed: set `horn_*` if yours differ.
