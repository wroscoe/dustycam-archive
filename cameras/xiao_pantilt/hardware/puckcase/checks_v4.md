-- 1. solids
  ok  front_cup solid count: 1.0000 == 1 
  ok  front_cup valid: 1.0000 == 1 
     front_cup volume 25158 mm^3
  ok  back_plate_v4 solid count: 1.0000 == 1 
  ok  back_plate_v4 valid: 1.0000 == 1 
     back_plate_v4 volume 18230 mm^3
  ok  holder_v4 solid count: 1.0000 == 1 
  ok  holder_v4 valid: 1.0000 == 1 
     holder_v4 volume 2452 mm^3
-- 2. seated interference
  ok  holder x cup (without the slot ribs): 0.0000 == 0.0 mm^3
  ok  holder x back plate: 0.0000 == 0.0 mm^3
  ok  board+headers x cup: 0.0000 == 0.0 mm^3
  ok  board+headers x back plate: 0.0000 == 0.0 mm^3
  ok  back plate x cup = 6 edge crush ribs: 10.2960 >= 3.0 mm
  ok  back plate x cup upper: 10.2960 <= 14.0 mm
     holder x slot ribs 2.2400 mm^3 (4 ribs, 0.10 crush)
  ok  rail x slot ribs, seated (crush): 2.2400 >= 0.1 mm
  ok  rail x slot ribs upper: 2.2400 <= 3.0 mm
-- 3. holder slide-in along the slot (holder + board moved +Z out of the cup, 12 steps)
  ok  slide-in sweep max: 0.0000 == 0.0 mm^3
-- 4. back plate press-on sweep (plate moved +Z, 6 steps)
  ok  press-on sweep: plate x holder/board max: 0.0000 == 0.0 mm^3
-- 5. clearances and geometry
  ok  rail top to slot bottom: 0.5000 >= 0.3 mm
  ok  rail flank clearance (per side): 0.3621 >= 0.15 mm
  ok  holder end wall to boss face: 0.1500 >= 0.15 mm
  ok  slot/boss end before the rebate: 0.5000 >= 0.3 mm
  ok  holder back to the back plate: 5.2000 >= 1.0 mm
  ok  lens tip inside the hole (behind the outer face): 0.4900 >= 0.3 mm
-- 5b. camera glued to the holder's plate (no keyhole, no dip)
  ok  glue plate is solid over the head (head x plate): 0.0000 == 0.0 mm^3
  ok  glue area under the head: 68.8900 >= 60.0 mm^2
  ok  plate margin around the head (-x): 0.6300 >= 0.5 mm
  ok  plate margin around the head (+x): 0.8200 >= 0.5 mm
  ok  head sits in FRONT of the plate (glued back face): 0.0000 == 0.0 mm
  ok  head clear of the cup's inner front face: 1.7500 >= 0.5 mm
  ok  glued camera x cup: 0.0000 == 0.0 mm^3
  ok  glued camera x board: 0.0000 == 0.0 mm^3
  ok  rail bottoms on the slot's closed end (depth stop): 0.0000 == 0.0 mm
-- 5c. board slides in under the plate (board moved -x in the board frame, 10 steps)
  ok  board insertion sweep x holder (no ribs) + camera: 0.0000 == 0.0 mm^3
  ok  USB plug (+0.30) x cup (walls): 0.0000 == 0.0 mm^3
  ok  USB plug (+0.30) x back plate: 0.0000 == 0.0 mm^3
  ok  header pin tails to the back plate: 5.0500 >= 0.5 mm
  ok  headers (+0.30) x cup/back plate: 0.0000 == 0.0 mm^3
  ok  card x cup: 0.0000 == 0.0 mm^3
     lens at Y 56.73; no eave now (lens tip 0.49 inside the hole)
-- 6. overhang audits
     down-facing 3.60 mm^2 at Z=26.85
  ok  front cup face-down (+Z faces off the bed): 5.6048 <= 12.0 mm^2
  ok  holder face-down: 1.1438 <= 2.0 mm^2
  ok  back plate front-face-down: 0.0000 <= 12.0 mm^2
-- 7. grip rib variants (board retention is the ribs alone; the posts are gone)
  ok  std: solid count: 1.0000 == 1 mm
  ok  std: valid: 1.0000 == 1 mm
  ok  std: net crush per side: 0.1000 == 0.1 mm
     std: 4 ribs, 0.25 proud, crush 0.10/side, PCB interference 0.447 mm^3
  ok  std: ribs actually bite the PCB: 0.4471 >= 0.05 mm^3
  ok  std: face-down overhang: 1.1438 <= 2.0 mm^2
  ok  std: x cup (without the slot ribs): 0.0000 == 0.0 mm^3
  ok  fine: solid count: 1.0000 == 1 mm
  ok  fine: valid: 1.0000 == 1 mm
  ok  fine: net crush per side: 0.0500 == 0.05 mm
     fine: 8 ribs, 0.20 proud, crush 0.05/side, PCB interference 0.335 mm^3
  ok  fine: ribs actually bite the PCB: 0.3348 >= 0.05 mm^3
  ok  fine: face-down overhang: 1.4400 <= 2.0 mm^2
  ok  fine: x cup (without the slot ribs): 0.0000 == 0.0 mm^3
  ok  firm: solid count: 1.0000 == 1 mm
  ok  firm: valid: 1.0000 == 1 mm
  ok  firm: net crush per side: 0.1700 == 0.17 mm
     firm: 4 ribs, 0.32 proud, crush 0.17/side, PCB interference 0.713 mm^3
  ok  firm: ribs actually bite the PCB: 0.7134 >= 0.05 mm^3
  ok  firm: face-down overhang: 1.3856 <= 2.0 mm^2
  ok  firm: x cup (without the slot ribs): 0.0000 == 0.0 mm^3

CHECK PASSED
