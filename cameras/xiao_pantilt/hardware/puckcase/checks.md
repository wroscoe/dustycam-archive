# puckcase v2.2 — check output

Run 2026-09-13 from `cameras/xiao_pantilt/hardware/puckcase/`, exit 0,
**no warnings**.

`check.py` implements DESIGN_v2.md §6 as amended by §9 (v2.1 and v2.2); see
README.md "Deviations" for the places where §6's literal wording and §3's
parameter tables disagree and which one the check follows.

v2.1 cleared the microSD card and the M2 × 12 engagement. v2.2 cleared the
last one: the single central snap tongue, which the USB-C shell swept through,
is replaced by two pillar tongues outside the shell's span — their bodies are
0.0000 mm³ against the full swept board at every insertion angle and only
their cam ramps are touched.

```
==============================================================================
puckcase v2.2 — fail-closed fit check (DESIGN_v2.md §6 + §9)
==============================================================================

-- 1. printable solids
front_plate  solids=1 valid=True volume= 10801.14 mm^3
             bbox=(-0.000, -0.000, -0.000) .. (47.210, 78.500, 8.400)
ring         solids=1 valid=True volume= 19235.61 mm^3
             bbox=(-0.000, -0.000, -8.000) .. (47.210, 80.800, 26.360)
back_plate   solids=1 valid=True volume= 17787.13 mm^3
             bbox=(-0.000, -0.000, 26.360) .. (47.210, 80.800, 37.860)

-- 2. designed crush references
power_puck front_plate x tube (6 ribs, 6.4 tall): 15.4400 mm^3
front_plate x ring expected (same 6 ribs, 4.9 tall): 11.8213 mm^3 +/- 10 %
back_plate x puck_tube expected: 15.4400 mm^3 +/- 2 %
4 rail crush ribs x expansion PCB edges: 1.1808 mm^3 (0.10/side nominal)
LOAD lead x header pins (soldered joint, 2 pins): 1.3926 mm^3

-- 3. 14 occurrences, 23 bound-overlapping pairs
  front_plate      x ring               11.4800 mm^3  (designed contact)
  front_plate      x xiao_vendor         0.0000 mm^3  (clear)
  ring             x back_plate          0.0000 mm^3  (clear)
  ring             x xiao_vendor         1.1808 mm^3  (designed contact)
  ring             x header_mock         0.0000 mm^3  (clear)
  ring             x ufl_plug_mock       0.0000 mm^3  (clear)
  ring             x ufl_cable_mock      0.0000 mm^3  (clear)
  ring             x load_lead_mock      0.0000 mm^3  (clear)
  ring             x antenna_mock        0.0000 mm^3  (clear)
  ring             x screw_m2x12_1       0.0000 mm^3  (MATED: screw in its own boss/pilot, excluded)
  ring             x screw_m2x12_2       0.0000 mm^3  (MATED: screw in its own boss/pilot, excluded)
  ring             x screw_m2x12_3       0.0000 mm^3  (MATED: screw in its own boss/pilot, excluded)
  ring             x screw_m2x12_4       0.0000 mm^3  (MATED: screw in its own boss/pilot, excluded)
  back_plate       x puck_tube          15.4400 mm^3  (designed contact)
  back_plate       x screw_m2x12_1       2.6154 mm^3  (MATED: screw in its own boss/pilot, excluded)
  back_plate       x screw_m2x12_2       2.6154 mm^3  (MATED: screw in its own boss/pilot, excluded)
  back_plate       x screw_m2x12_3       2.6154 mm^3  (MATED: screw in its own boss/pilot, excluded)
  back_plate       x screw_m2x12_4       2.6154 mm^3  (MATED: screw in its own boss/pilot, excluded)
  xiao_vendor      x header_mock         0.0000 mm^3  (clear)
  xiao_vendor      x ufl_plug_mock       0.0000 mm^3  (clear)
  xiao_vendor      x ufl_cable_mock      0.0000 mm^3  (clear)
  header_mock      x load_lead_mock      1.3926 mm^3  (designed contact)
  load_lead_mock   x antenna_mock        0.0000 mm^3  (clear)
static pairs checked: 23/23   screw mated volume total: 10.462 mm^3

ring x back_plate: 0.00000 mm^3 (expect 0 — screws are the only contact)

-- 4. board (PCB assembly + fitted microSD card, head excluded) vs the printed parts
   rigid ring = ring without the rail crush ribs and without the snap tongue
  Y -0.20 (stop ribs)  X -0.15          ring_rigid 0.0000/0.0000  front_plate 0.0000/0.0000  back_plate 0.0000/0.0000  tongue 0.0000  ribs 1.8435
  Y -0.20 (stop ribs)  X 0.00           ring_rigid 0.0000/0.0000  front_plate 0.0000/0.0000  back_plate 0.0000/0.0000  tongue 0.0000  ribs 1.1808
  Y -0.20 (stop ribs)  X +0.15 (rails)  ring_rigid 0.0000/0.0000  front_plate 0.0000/0.0000  back_plate 0.0000/0.0000  tongue 0.0000  ribs 1.8435
  Y nominal            X -0.15          ring_rigid 0.0000/0.0000  front_plate 0.0000/0.0000  back_plate 0.0000/0.0000  tongue 0.0000  ribs 1.8450
  Y nominal            X 0.00           ring_rigid 0.0000/0.0000  front_plate 0.0000/0.0000  back_plate 0.0000/0.0000  tongue 0.0000  ribs 1.1808
  Y nominal            X +0.15 (rails)  ring_rigid 0.0000/0.0000  front_plate 0.0000/0.0000  back_plate 0.0000/0.0000  tongue 0.0000  ribs 1.8450
  Y +0.20 (tongue faces, soft) X -0.15          ring_rigid 0.0000/0.0000  front_plate 0.0000/0.0000  back_plate 0.0000/0.0000  tongue 0.0000  ribs 1.8450
  Y +0.20 (tongue faces, soft) X 0.00           ring_rigid 0.0000/0.0000  front_plate 0.0000/0.0000  back_plate 0.0000/0.0000  tongue 0.0000  ribs 1.1808
  Y +0.20 (tongue faces, soft) X +0.15 (rails)  ring_rigid 0.0000/0.0000  front_plate 0.0000/0.0000  back_plate 0.0000/0.0000  tongue 0.0000  ribs 1.8450
board positions checked: 9/9   (cells are board/header interference, expect 0)
  camera head (collar-located, nominal) x ring_rigid   0.0000 mm^3
  camera head (collar-located, nominal) x front_plate  0.0000 mm^3
  camera head (collar-located, nominal) x back_plate   0.0000 mm^3

-- 5. tilt insertion (board rotated about its far-edge PCB-back corner line)
   v2.1: the microSD card is FITTED and rides with the PCB
    0 deg   ring_rigid 0.0000   back_plate 0.0000   card alone 0.0000   rail ribs 1.1808 (deliberate crush)
   -2 deg   ring_rigid 0.0000   back_plate 0.0000   card alone 0.0000   rail ribs 0.9091 (deliberate crush)
   -4 deg   ring_rigid 0.0000   back_plate 0.0000   card alone 0.0000   rail ribs 0.6431 (deliberate crush)
   -8 deg   ring_rigid 0.0000   back_plate 0.0000   card alone 0.0000   rail ribs 0.2146 (deliberate crush)
  -13 deg   ring_rigid 0.0000   back_plate 0.0000   card alone 0.0000   rail ribs 0.0334 (deliberate crush)
  far-edge groove at 13 deg: slot 1.500 vs 1.25*cos13 + 0.80*sin13 = 1.398

   snap tongues during the swing (cam ramp = designed contact, tongue BODY = must be 0):
       0 deg   cam ramps  0.0000   tongue bodies  0.0000
      -2 deg   cam ramps  1.3626   tongue bodies  0.0000
      -4 deg   cam ramps  1.4618   tongue bodies  0.0000
      -8 deg   cam ramps  0.0000   tongue bodies  0.0000
     -13 deg   cam ramps  0.0000   tongue bodies  0.0000

-- 6. named clearances (DESIGN_v2 §6.3)
  collar window -> head, per side                   0.300   (contract >= 0.15)
  collar bore -> lens barrel, radial                0.205   (contract >= 0.15)
  collar step -> head top (Z)                       0.200   (contract >= 0.15)
  collar back face -> SD card top                   0.500   (contract >= 0.50)
  collar back face -> SD socket                     0.970   (contract >= 0.50)
  collar relief -> FPC roll                         0.750   (contract >= 0.50)
  collar step -> head top = USB-end forward stop    0.200   (contract == 0.20)
  hook underside -> PCB top                         0.150   (contract == 0.15)
  ledge face -> PCB back                            0.100   (contract == 0.10)
  tongue lip -> PCB back                            0.100   (contract == 0.10)
  rail face -> expansion PCB edge                   0.150   (contract == 0.15)
  rail rib crest into the expansion edge (crush)    0.100   (contract == 0.10)
  rib crest -> FPC socket (board y)                 0.220   (contract == 0.22)
  far-end wall -> expansion PCB overhang            0.350   (contract == 0.35)
  stop rib -> PCB far edge                          0.200   (contract == 0.20)
  tongue face -> PCB end edge (soft +Y stop)        0.200   (contract == 0.20)
  card tip -> top wall inner face (roof)            4.000   (contract == 4.00)
  lens tip -> plate inner face (Z)                  1.000   (contract == 1.00)
  eave proud of the front plate face (Z)            8.000   (contract == 8.00)

   forward travel of the board (head rigid on the PCB) before the ring catches it: 0.155 mm  (contract <= 0.35)
      caught by the far-end hooks at 0.150, before the collar step at 0.200 — both stops, hooks first

   0.30-clearance proofs (mock inflated by 0.3, expect 0 interference)
     header body + pins       x all printed: 0.0000 mm^3
     U.FL plug (+1.3 z)       x all printed: 0.0000 mm^3
     U.FL cable path Ø1.2     x all printed: 0.0000 mm^3
     button_rst               x all printed: 0.0000 mm^3
     button_boot              x all printed: 0.0000 mm^3

-- 7. snap tongues (DESIGN_v2 §6.5, two pillar tongues in v2.2)
  tongue 1 (board y -0.50..+3.90, case X 27.955..32.355, 4.40 wide)
     lip bearing on the PCB back       1.1163 mm^2 (2.791 effective length)
     on the STRAIGHT end edge           1.994 mm   (require >= 1.90; PCB corners are R1.906)
     snap force at 0.6 deflection       1.46 N     (E = 2000 MPa, PETG)
  tongue 2 (board y +13.88..+18.28, case X 13.575..17.975, 4.40 wide)
     lip bearing on the PCB back       1.1163 mm^2 (2.791 effective length)
     on the STRAIGHT end edge           1.994 mm   (require >= 1.90; PCB corners are R1.906)
     snap force at 0.6 deflection       1.46 N     (E = 2000 MPa, PETG)
  lip reach over the PCB back edge                0.400   (contract == 0.40)
  free gap, tongue 2 -> -X side wall              2.600   (contract >= 0.80)
  free gap, tongue 1 -> +X side wall              1.000   (contract >= 0.80)
  tongue thickness                                0.900   (contract == 0.90)
  tongue free length                              8.700   (contract == 8.70)
  clear of the USB-C shell, tongue 1 (board y)    0.510   (contract >= 0.50)
  clear of the USB-C shell, tongue 2 (board y)    0.530   (contract >= 0.50)
  outer-fibre strain at 0.60 deflection (%)       1.070   (contract <= 1.50)
  total snap force, both tongues (N)              2.923   (contract >= 0.00)
  removal: press BOTH tongues outward through the back mouth

-- 8. eave brow, card roof, screws
  eave brow angle above the lens axis (deg)      43.025   (contract >= 40.00)
  card roof to the top wall inner face            4.000   (contract >= 3.50)
  boss bore diameter                              2.200   (contract == 2.20)
  boss diameter                                   5.500   (contract == 5.50)
  pilot diameter                                  1.700   (contract == 1.70)
  pilot depth                                     3.400   (contract == 3.40)
  boss length (screw head -> back plate)          9.000   (contract == 9.00)
  M2 x 12 thread engagement in the back plate     3.000   (contract >= 3.00)
  M2 x 12 tip short of the pilot bottom           0.400   (contract >= 0.30)
  screw head -> front lip nose (driver reach)     7.460   (contract >= 0.00)
   driver access down each boss axis (Ø5.5 column, Z 2.40..17.36):
     boss 1 at (6.50, 6.50): 0.0000 mm^3 (expect 0)
     boss 2 at (40.71, 6.50): 0.0000 mm^3 (expect 0)
     boss 3 at (6.50, 74.30): 0.0000 mm^3 (expect 0)
     boss 4 at (40.71, 74.30): 0.0000 mm^3 (expect 0)

-- 9. overhang audit: planar faces steeper than 45 deg from vertical, in each part's print orientation
  front_plate: 1 faces, 1.3 mm^2 (bed at Z 0.00, -Z is down; first-layer faces excluded)
         1.25 mm^2  n.down=1.00  X 20.61..26.61  Y 78.25..78.50  Z 2.40..2.40
  ring: 14 faces, 253.4 mm^2 (bed at Z 26.36, +Z is down; first-layer faces excluded)
       129.07 mm^2  n.down=1.00  X 12.57..33.36  Y 61.49..72.89  Z 8.36..8.36
        28.48 mm^2  n.down=1.00  X 1.80..45.41  Y 74.80..79.00  Z 2.40..2.40
        28.17 mm^2  n.down=1.00  X 6.00..41.21  Y 78.40..79.20  Z -6.50..-6.50
        20.50 mm^2  n.down=1.00  X 19.30..27.91  Y 63.46..72.06  Z 6.86..6.86
        16.08 mm^2  n.down=1.00  X 19.30..27.91  Y 61.49..63.36  Z 7.86..7.86
        14.55 mm^2  n.down=1.00  X 12.57..33.36  Y 72.89..73.59  Z 6.86..6.86
         7.20 mm^2  n.down=1.00  X 33.36..34.95  Y 52.30..56.80  Z 21.86..21.86
         3.60 mm^2  n.down=1.00  X 12.25..13.75  Y 0.00..2.40  Z 22.86..22.86
         1.37 mm^2  n.down=1.00  X 30.25..32.36  Y 50.14..50.79  Z 15.96..15.96
         1.36 mm^2  n.down=1.00  X 13.57..15.68  Y 50.14..50.79  Z 15.96..15.96
         0.75 mm^2  n.down=1.00  X 31.25..31.51  Y 54.29..58.29  Z 13.16..13.16
         0.75 mm^2  n.down=1.00  X 31.25..31.50  Y 58.79..62.79  Z 13.16..13.16
         0.75 mm^2  n.down=1.00  X 14.43..14.68  Y 58.79..62.79  Z 13.16..13.16
         0.75 mm^2  n.down=1.00  X 14.42..14.68  Y 54.29..58.29  Z 13.16..13.16
  back_plate: 4 faces, 9.1 mm^2 (bed at Z 26.36, -Z is down; first-layer faces excluded)
         2.27 mm^2  n.down=1.00  X 5.65..7.35  Y 5.65..7.35  Z 29.76..29.76
         2.27 mm^2  n.down=1.00  X 39.86..41.56  Y 5.65..7.35  Z 29.76..29.76
         2.27 mm^2  n.down=1.00  X 5.65..7.35  Y 73.45..75.15  Z 29.76..29.76
         2.27 mm^2  n.down=1.00  X 39.86..41.56  Y 73.45..75.15  Z 29.76..29.76

-- 10. insertion feasibility
  microSD card fitted, swept through the tilt range x ring: 0.0000 mm^3  (v2.1: the bridge band is gone)
  head swung rigidly with the PCB at -4 deg x ring: 1.89 mm^3 (it is flex-mounted, so it is fed into the collar separately — see group 5)

-- checks run: printable solids + bounds; crush references; static pair sweep; ring x back_plate; pcb/header/head vs printed, nominal + play extremes; tilt insertion 0/-2/-4/-8/-13 deg + groove + tongue swing + head entry; named clearances; 0.30 clearance proofs; snap tongue; brow / roof / screws; overhang audit; insertion feasibility

CHECK PASSED
exit 0
```
