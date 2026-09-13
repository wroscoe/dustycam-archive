# puckcase v1 — check output

Run 2026-09-13 from `cameras/xiao_pantilt/hardware/puckcase/`:

```
$ ~/.claude/skills/cad/.venv/bin/python check.py
==============================================================================
puckcase v1 — fail-closed fit check
==============================================================================

-- printable solids
front_plate  solids=1 valid=True volume= 10911.54 mm^3
             bbox=(-0.000, -0.000, -0.000) .. (47.210, 78.500, 16.010)
ring         solids=1 valid=True volume= 13344.12 mm^3
             bbox=(-0.000, -0.000, -8.000) .. (47.210, 80.800, 20.360)
back_plate   solids=1 valid=True volume= 17787.13 mm^3
             bbox=(-0.000, -0.000, 20.360) .. (47.210, 80.800, 31.860)

-- designed crush reference (power_puck front_plate x tube)
power_puck front_plate x tube (6 ribs, 6.4 tall): 15.4400 mm^3
front_plate x ring expected (same 6 ribs, 4.9 tall): 11.8213 mm^3 +/- 10 %
back_plate x puck_tube expected: 15.4400 mm^3 +/- 2 % (same lip, same tube)

-- 11 occurrences, 20 bound-overlapping pairs
  front_plate      x ring               11.4800 mm^3  (designed crush)
  front_plate      x xiao_vendor         0.0000 mm^3  (clear)
  front_plate      x screw_m2x8_1        0.0000 mm^3  (MATED: screw in its own boss/pilot, excluded)
  front_plate      x screw_m2x8_2        0.0000 mm^3  (MATED: screw in its own boss/pilot, excluded)
  front_plate      x screw_m2x8_3        0.0000 mm^3  (MATED: screw in its own boss/pilot, excluded)
  front_plate      x screw_m2x8_4        0.0000 mm^3  (MATED: screw in its own boss/pilot, excluded)
  ring             x back_plate          0.0000 mm^3  (clear)
  ring             x xiao_vendor         0.0000 mm^3  (clear)
  ring             x load_lead_mock      0.0000 mm^3  (clear)
  ring             x antenna_mock        0.0000 mm^3  (clear)
  ring             x screw_m2x8_1        0.0000 mm^3  (MATED: screw in its own boss/pilot, excluded)
  ring             x screw_m2x8_2        0.0000 mm^3  (MATED: screw in its own boss/pilot, excluded)
  ring             x screw_m2x8_3        0.0000 mm^3  (MATED: screw in its own boss/pilot, excluded)
  ring             x screw_m2x8_4        0.0000 mm^3  (MATED: screw in its own boss/pilot, excluded)
  back_plate       x puck_tube          15.4400 mm^3  (designed crush)
  back_plate       x screw_m2x8_1        3.2783 mm^3  (MATED: screw in its own boss/pilot, excluded)
  back_plate       x screw_m2x8_2        3.2783 mm^3  (MATED: screw in its own boss/pilot, excluded)
  back_plate       x screw_m2x8_3        3.2783 mm^3  (MATED: screw in its own boss/pilot, excluded)
  back_plate       x screw_m2x8_4        3.2783 mm^3  (MATED: screw in its own boss/pilot, excluded)
  load_lead_mock   x antenna_mock        0.0000 mm^3  (clear)
static pairs checked: 20/20   screw mated volume total: 13.113 mm^3

ring x back_plate: 0.00000 mm^3 (expect 0 — screws are the only contact)

-- vendor XIAO STEP vs the printed parts (per-solid, transform baked)
  nominal                front_plate 0.0000   ring 0.0000   back_plate 0.0000   (expect 0)
  case X +0.50           front_plate 0.0000   ring 0.0000   back_plate 0.0000   (expect 0)
  case X -0.50           front_plate 0.0000   ring 0.0000   back_plate 0.0000   (expect 0)
  case Y +0.40           front_plate 0.0000   ring 0.0011*   back_plate 0.0000   (expect 0)
  case Y -0.35           front_plate 0.0000   ring 0.0000   back_plate 0.0000   (expect 0)
  case X +0.50 Y +0.40   front_plate 0.0000   ring 0.0037*   back_plate 0.0000   (expect 0)
  case X +0.50 Y -0.35   front_plate 0.0000   ring 0.0000   back_plate 0.0000   (expect 0)
  case X -0.50 Y +0.40   front_plate 0.0000   ring 0.0037*   back_plate 0.0000   (expect 0)
  case X -0.50 Y -0.35   front_plate 0.0000   ring 0.0000   back_plate 0.0000   (expect 0)
board positions checked: 9/9   (* = stop-face contact sliver, <= 0.01 mm^3)

-- tilt insertion (board rotated about its far-edge PCB-top corner line)
   6 deg   ring 0.0000   back_plate 0.0000   (expect 0)
   8 deg   ring 0.0000   back_plate 0.0000   (expect 0)
  10 deg   ring 0.0000   back_plate 0.0000   (expect 0)

-- numeric gaps
  hook underside -> PCB top (Z)                     0.200   (contract 0.20)
  front post -> PCB top (Z)                         0.100   (contract 0.10)
  ledge overlap under the PCB                       0.950   (contract 0.95)
  board play along the case Y (board x)             0.750   (contract 0.75)
  board play along the case X (board y)             1.000   (contract 1.00)
  lens tip -> plate inner face (Z)                  1.000   (contract 1.00)
  card tip -> top wall inner face (Y)               0.497   (contract 0.50)
  screw head -> front lip nose (Z)                  5.960
  lens tip radial -> hole wall, nominal             0.750
  eave brow half-angle from the lens tip (deg)     32.060
  RST/BOOT button -> front post (board y, extreme)    0.300
  expansion board -> stop rib front face (Z)        0.550
  eave proud of the front plate face (Z)            8.000   (contract 8.00)

-- front-plate post landing area on the PCB
  post 1: 2.635 mm^2 on the PCB   (require >= 1.00)
  post 2: 2.635 mm^2 on the PCB   (require >= 1.00)

-- checks run: printable solids + bounds; crush reference; static pair sweep; ring x back_plate; XIAO vs printed, nominal + extremes; tilt insertion 6/8/10 deg; numeric gaps; post landing area

CHECK PASSED
exit 0
```
