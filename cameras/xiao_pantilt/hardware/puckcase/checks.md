# puckcase v2.4 — check output

Run 2026-09-13 from `cameras/xiao_pantilt/hardware/puckcase/`, exit 0,
**no warnings**.

`check.py` implements DESIGN_v2.md §6 as amended by §9 (v2.1, v2.2, v2.3) and
§10 (v2.4); see README.md "Deviations" for the places where §6's literal
wording and §3's parameter tables disagree and which one the check follows.

v2.4 moves the lens collar off the ring and onto the front plate as the **head
window boss**, and cleans up what was left of the ring's overhangs. The ring's
45° overhang audit drops from **253.4 mm² over 14 faces to 9.3 mm² over 7**
(hook undersides, four rail rib crests, the cord slot's 1.5 mm flat — all
accepted), and the boss adds **nothing** to the front plate's 1.3 mm². Group 5
is new: the plate, boss and all, stepped onto its seat over 7 approach steps at
each of the 9 board play positions.

Numbers that moved from the v2.3 run:

| Check | v2.3 | v2.4 | Why |
|---|---|---|---|
| front_plate volume | 10 801.14 | 11 269.80 mm³ | + the head window boss |
| ring volume | 19 256.62 | 18 498.81 mm³ | − the collar sheet, − the side walls' forward band |
| `front_plate × ring` | 11.4800 | 11.7227 mm³ | the front-mouth lead-in no longer undercuts the +Y crush rib's first 0.6 mm (expected 11.8213 ± 10 %) |
| ring overhang | 253.4 mm² / 14 | 9.3 mm² / 7 | §10 |
| head swung rigidly with the PCB × ring | 1.89 mm³ at −4° | 0.0000 at every angle | there is no collar to feed the head into any more — hard-checked |
| coupon_ring_bay | 11 439 mm³ | 10 681 mm³ | same two deletions |
| coupon_front_plate | 4 719 mm³ | 5 188 mm³ | + the boss |

Everything else — every clearance, the tongue mechanics, the screw stack, the
brow and the card roof — is unchanged to the printed digit.

```
$ ~/.claude/skills/cad/.venv/bin/python check.py
==============================================================================
puckcase v2.4 — fail-closed fit check (DESIGN_v2.md §6 + §9 + §10)
==============================================================================

-- 1. printable solids
front_plate  solids=1 valid=True volume= 11269.80 mm^3
             bbox=(-0.000, -0.000, -0.000) .. (47.210, 78.500, 8.400)
ring         solids=1 valid=True volume= 18498.81 mm^3
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
  front_plate      x ring               11.7227 mm^3  (designed contact)
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
  camera head (head-window-located, nominal) x ring_rigid   0.0000 mm^3
  camera head (head-window-located, nominal) x front_plate  0.0000 mm^3
  camera head (head-window-located, nominal) x back_plate   0.0000 mm^3

-- 5. plate fitting sweep (v2.4): the front plate stepped onto its seat
   the plate approaches from OUTSIDE the case (-Z) and travels +Z to seat;
   'short' is how far the plate still is from its seated position.
  Y -0.20 (stop ribs)  X -0.15          worst pcb/card/roll/header 0.0000   head x boss 0.2766   chamfer-mouth margin 0.700
  Y -0.20 (stop ribs)  X 0.00           worst pcb/card/roll/header 0.0000   head x boss 0.0000   chamfer-mouth margin 0.700
  Y -0.20 (stop ribs)  X +0.15 (rails)  worst pcb/card/roll/header 0.0000   head x boss 0.2629   chamfer-mouth margin 0.700
  Y nominal            X -0.15          worst pcb/card/roll/header 0.0000   head x boss 0.0000   chamfer-mouth margin 0.750
  Y nominal            X 0.00           worst pcb/card/roll/header 0.0000   head x boss 0.0000   chamfer-mouth margin 0.900
  Y nominal            X +0.15 (rails)  worst pcb/card/roll/header 0.0000   head x boss 0.0000   chamfer-mouth margin 0.750
  Y +0.20 (tongue faces, soft) X -0.15          worst pcb/card/roll/header 0.0000   head x boss 0.3206   chamfer-mouth margin 0.700
  Y +0.20 (tongue faces, soft) X 0.00           worst pcb/card/roll/header 0.0000   head x boss 0.0055   chamfer-mouth margin 0.700
  Y +0.20 (tongue faces, soft) X +0.15 (rails)  worst pcb/card/roll/header 0.0000   head x boss 0.3067   chamfer-mouth margin 0.700
  plate positions checked: 63/63  (7 approach steps x 9 board play positions)
     8.60 window vs the 8.00 head: 0.300 per side (>= the 0.20 / 0.15 play), so the square head never touches;
     Ø8.25 bore vs the Ø7.84 barrel: 0.205 radial vs a worst play-extreme radial shift of 0.250 — a barrel contact, not a head-in-window one.
     guided by the chamfer: head x boss 0.2766 mm^3 at Y -0.20 X -0.15  (the head is carried rigidly with the PCB here, which it is not: DESIGN_v2 §9 C.9 — it hangs on its flex, the 45 deg lead-in and the bore recentre it and the flex takes up the difference)
     guided by the chamfer: head x boss 0.2629 mm^3 at Y -0.20 X +0.15  (the head is carried rigidly with the PCB here, which it is not: DESIGN_v2 §9 C.9 — it hangs on its flex, the 45 deg lead-in and the bore recentre it and the flex takes up the difference)
     guided by the chamfer: head x boss 0.3206 mm^3 at Y +0.20 X -0.15  (the head is carried rigidly with the PCB here, which it is not: DESIGN_v2 §9 C.9 — it hangs on its flex, the 45 deg lead-in and the bore recentre it and the flex takes up the difference)
     guided by the chamfer: head x boss 0.0055 mm^3 at Y +0.20 X +0.00  (the head is carried rigidly with the PCB here, which it is not: DESIGN_v2 §9 C.9 — it hangs on its flex, the 45 deg lead-in and the bore recentre it and the flex takes up the difference)
     guided by the chamfer: head x boss 0.3067 mm^3 at Y +0.20 X +0.15  (the head is carried rigidly with the PCB here, which it is not: DESIGN_v2 §9 C.9 — it hangs on its flex, the 45 deg lead-in and the bore recentre it and the flex takes up the difference)

-- 6. tilt insertion (board rotated about its far-edge PCB-back corner line)
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

   camera head swung RIGIDLY with the PCB x ring (v2.4: must be 0 at every angle — there is no collar to feed it into; the plate's head window drops over it afterwards):
       0 deg   head x ring  0.0000
      -2 deg   head x ring  0.0000
      -4 deg   head x ring  0.0000
      -8 deg   head x ring  0.0000
     -13 deg   head x ring  0.0000

-- 7. named clearances (DESIGN_v2 §6.3, §10)
   v2.4: the first eleven are features of the FRONT PLATE's head window boss
  head window -> head, per side                         0.300   (contract >= 0.15)
  head window bore -> lens barrel, radial               0.205   (contract >= 0.15)
  head window step -> head top (Z)                      0.200   (contract >= 0.15)
  boss mouth -> SD card top                             0.500   (contract >= 0.50)
  boss mouth -> SD socket                               0.970   (contract >= 0.50)
  boss FPC relief -> FPC roll                           0.750   (contract >= 0.50)
  head window wall thickness                            1.600   (contract == 1.60)
  boss -> ring side wall inner face (X)                 3.850   (contract >= 0.30)
  boss -> ring far-end wall (Y)                        13.770   (contract >= 0.30)
  boss -> plate lip band inner prism (BAY_Y1)           2.990   (contract >= 0.30)
  window step -> head top = USB-end stop (plate on)     0.200   (contract == 0.20)
  hook underside -> PCB top                             0.150   (contract == 0.15)
  ledge face -> PCB back                                0.100   (contract == 0.10)
  tongue lip -> PCB back                                0.100   (contract == 0.10)
  rail face -> expansion PCB edge                       0.150   (contract == 0.15)
  rail rib crest into the expansion edge (crush)        0.100   (contract == 0.10)
  rib crest -> FPC socket (board y)                     0.220   (contract == 0.22)
  far-end wall -> expansion PCB overhang                0.350   (contract == 0.35)
  stop rib -> PCB far edge                              0.200   (contract == 0.20)
  tongue face -> PCB end edge (soft +Y stop)            0.200   (contract == 0.20)
  card tip -> top wall inner face (roof)                4.000   (contract == 4.00)
  lens tip -> plate inner face (Z)                      1.000   (contract == 1.00)
  eave proud of the front plate face (Z)                8.000   (contract == 8.00)

   forward travel of the board (head rigid on the PCB, PLATE FITTED) before a stop catches it: 0.155 mm  (contract <= 0.35)
      first contact: ring (far-end hooks)
      hooks (ring) at 0.150, plate boss step at 0.200 — both stops, hooks first, with the plate fitted

   0.30-clearance proofs (mock inflated by 0.3, expect 0 interference)
     header body + pins       x all printed: 0.0000 mm^3
     U.FL plug (+1.3 z)       x all printed: 0.0000 mm^3
     U.FL cable path Ø1.2     x all printed: 0.0000 mm^3
     button_rst               x all printed: 0.0000 mm^3
     button_boot              x all printed: 0.0000 mm^3

-- 8. snap tongues (DESIGN_v2 §6.5, two pillar tongues, v2.3 root)
  tongue 1 (board y -0.50..+3.90, case X 27.955..32.355, 4.40 wide)
     lip bearing on the PCB back       1.1163 mm^2 (2.791 effective length)
     on the STRAIGHT end edge           1.994 mm   (require >= 1.90; PCB corners are R1.906)
     snap force at 0.6 deflection       1.67 N     (E = 2000 MPa, PETG)
  tongue 2 (board y +13.88..+18.28, case X 13.575..17.975, 4.40 wide)
     lip bearing on the PCB back       1.1163 mm^2 (2.791 effective length)
     on the STRAIGHT end edge           1.994 mm   (require >= 1.90; PCB corners are R1.906)
     snap force at 0.6 deflection       1.67 N     (E = 2000 MPa, PETG)
  lip reach over the PCB back edge                0.400   (contract == 0.40)
  free gap, tongue 2 -> -X side wall              1.000   (contract >= 0.80)
  free gap, tongue 1 -> +X side wall              1.000   (contract >= 0.80)
  tongue thickness                                0.800   (contract == 0.80)
  tongue free length                              7.400   (contract == 7.40)
  root strip height                               1.500   (contract == 1.50)
  root strip thickness                            1.400   (contract == 1.40)
  clear of the USB-C shell, tongue 1 (board y)    0.510   (contract >= 0.50)
  clear of the USB-C shell, tongue 2 (board y)    0.530   (contract >= 0.50)
  outer-fibre strain at 0.60 deflection (%)       1.315   (contract <= 1.50)
  total snap force, both tongues (N)              3.336   (contract >= 0.00)

  root strip: 1.40 thick x 1.50 tall, wall to wall over 20.78, carrying both tongue roots
     strip BENDING under the root shear 1.67 N (fixed-fixed, load at a = 3.20): 0.0161 mm at the lip   (contract < 0.05)
     strip TORSION under the root moment 12.34 N.mm (J = 0.616, G = 741): 0.5417 mm at the lip
     -> tongue alone 2.78 N/mm, strip 2.99 N/mm, series 1.44 N/mm; snap force at 0.6 of total travel 0.86 N per tongue
  removal: press BOTH tongues outward through the back mouth

-- 9. eave brow, card roof, screws
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

-- 10. overhang audit: planar faces steeper than 45 deg from vertical, in each part's print orientation
  front_plate: 1 faces, 1.3 mm^2 (v2.3 was 1.3; budget <= 1.4) (bed at Z 0.00, -Z is down; first-layer faces excluded)
         1.25 mm^2  n.down=1.00  X 20.61..26.61  Y 78.25..78.50  Z 2.40..2.40
  ring: 7 faces, 9.3 mm^2 (v2.3 was 253.4; budget <= 12.0) (bed at Z 26.36, +Z is down; first-layer faces excluded)
         3.60 mm^2  n.down=1.00  X 12.25..13.75  Y 0.00..2.40  Z 22.86..22.86
         1.37 mm^2  n.down=1.00  X 30.25..32.36  Y 50.14..50.79  Z 15.96..15.96
         1.36 mm^2  n.down=1.00  X 13.57..15.68  Y 50.14..50.79  Z 15.96..15.96
         0.75 mm^2  n.down=1.00  X 31.25..31.51  Y 54.29..58.29  Z 13.16..13.16
         0.75 mm^2  n.down=1.00  X 14.43..14.68  Y 58.79..62.79  Z 13.16..13.16
         0.75 mm^2  n.down=1.00  X 31.25..31.50  Y 58.79..62.79  Z 13.16..13.16
         0.75 mm^2  n.down=1.00  X 14.42..14.68  Y 54.29..58.29  Z 13.16..13.16
  back_plate: 4 faces, 9.1 mm^2 (v2.3 was 9.1; budget <= 9.2) (bed at Z 26.36, -Z is down; first-layer faces excluded)
         2.27 mm^2  n.down=1.00  X 5.65..7.35  Y 5.65..7.35  Z 29.76..29.76
         2.27 mm^2  n.down=1.00  X 39.86..41.56  Y 5.65..7.35  Z 29.76..29.76
         2.27 mm^2  n.down=1.00  X 5.65..7.35  Y 73.45..75.15  Z 29.76..29.76
         2.27 mm^2  n.down=1.00  X 39.86..41.56  Y 73.45..75.15  Z 29.76..29.76
  accepted (no change asked, each is a sub-4 mm^2 tab or a short bridge anchored at both ends): far-end hook undersides 2.1 x 0.65 each, the four rail rib crests 0.25 x 4.0 each, the cord slot's 1.5 mm flat roof, and the back plate's four Ø1.7 pilot bottoms.

-- 11. insertion feasibility
  microSD card fitted, swept through the tilt range x ring: 0.0000 mm^3  (v2.1: the bridge band is gone)
  head swung rigidly with the PCB, worst of -2/-4/-8/-13 deg x ring: 0.0000 mm^3
     v2.4: the collar is gone, so the head needs no separate straight-in feed — it rides in with the board and the front plate's head window drops over it (group 5).  Hard-checked in group 6.

-- checks run: printable solids + bounds; crush references; static pair sweep; ring x back_plate; pcb/header/head vs printed, nominal + play extremes; plate fitting sweep; tilt insertion 0/-2/-4/-8/-13 deg + groove + tongue swing + rigid head swing; named clearances; 0.30 clearance proofs; snap tongue; brow / roof / screws; overhang audit; insertion feasibility

CHECK PASSED
exit 0
```
