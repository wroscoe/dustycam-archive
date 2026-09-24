-- 1. solids
  ok  ring_v3 solid count: 1.0000 == 1 
  ok  ring_v3 valid: 1.0000 == 1 
  ok  front_plate_v3 solid count: 1.0000 == 1 
  ok  front_plate_v3 valid: 1.0000 == 1 
-- 2. seated interference
  ok  holder x ring: 0.0000 == 0.0 mm^3
  ok  holder x front plate: 0.0000 == 0.0 mm^3
  ok  holder x back plate: 0.0000 == 0.0 mm^3
  ok  board+headers x ring: 0.0000 == 0.0 mm^3
  ok  board+headers x front plate: 0.0000 == 0.0 mm^3
  ok  board+headers x back plate: 0.0000 == 0.0 mm^3
  ok  front plate x ring = 6 lip crush ribs, v2.4 value 11.72: 11.7227 >= 11.0 mm^3
  ok  front plate x ring upper: 11.7227 <= 12.5 mm^3
-- 3. holder drop-in sweep (holder + board moved -Z out of the ring, 10 steps)
  ok  drop-in sweep max: 0.0000 == 0.0 mm^3
-- 4. clearances
     wall-to-leg gap 0.15 (probe volume 18.0)
     wall-to-leg gap 0.15 (probe volume 18.0)
  ok  ear top under the front plate inner face: -0.1000 >= -0.1 mm
  ok  holder forward band inside the lip prism (Y): 0.1500 >= 0.1 mm
  ok  holder forward band inside the lip prism (X-): 6.9550 >= 0.1 mm
  ok  holder forward band inside the lip prism (X+): 5.6750 >= 0.1 mm
  ok  USB plug (+0.30) x ring/ledges: 0.0000 == 0.0 mm^3
  ok  USB plug (+0.30) x front plate: 0.0000 == 0.0 mm^3
  ok  PCB end to ledge gap (Y): 0.2000 >= 0.2 mm
  ok  lens tip to plate inner face: 1.0000 >= 1.0 mm
  ok  eave brow angle above the lens axis (deg): 61.9775 >= 40.0 deg
  ok  header pin tails clear of the back plate: 0.5000 >= 0.3 mm
-- 5. ring overhang audit (standing on its back mouth: +Z faces point down)
     down-facing 3.60 mm^2 at Z=22.86
     down-facing 4.30 mm^2 at Z=17.21
     down-facing 4.30 mm^2 at Z=17.21
  ok  ring +Z-facing area off the bed (v2.4 was 9.3): 12.2048 <= 20.0 mm^2

CHECK PASSED
