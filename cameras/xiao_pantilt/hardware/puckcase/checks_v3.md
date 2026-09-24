-- 1[header] solid and bounds
  ok  [header] solid count: 1.0000 == 1 
  ok  [header] valid: 1.0000 == 1 
  ok  [header] bound x min: -1.0000 == -1.0 mm
  ok  [header] bound x max: 23.0500 == 23.05 mm
  ok  [header] bound y min: -4.2500 == -4.25 mm
  ok  [header] bound y max: 22.0300 == 22.03 mm
  ok  [header] bound z min: -3.8500 == -3.8499999999999996 mm
  ok  [header] bound z max: 14.8600 == 14.86 mm
     volume 2724 mm^3, depth 15.90, width 22.08
-- 2[header] board insertion sweep (rib-less holder; ribs reported apart)
  ok  [header] board stack x holder over the sweep, max: 0.0000 == 0.0 mm^3
  ok  [header] grip ribs x PCB, seated (0.10 crush x 4): 0.4501 >= 0.3 mm^3
  ok  [header] grip ribs x PCB, seated, upper: 0.4501 <= 1.2 mm^3
  ok  [header] grip ribs x everything else: 0.0000 == 0.0 mm^3
-- 3[header] clearances (mock inflated by g must not touch)
  ok  [header] sensor plate to face >= 0.13999999999999999: 0.0000 == 0.0 mm^3
  ok  [header] lens barrel in keyhole >= 0.19: 0.0000 == 0.0 mm^3
  ok  [header] expansion PCB to end wall >= 0.19: 0.0000 == 0.0 mm^3
  ok  [header] USB shell to holder >= 0.5: 0.0000 == 0.0 mm^3
  ok  [header] card to holder >= 0.5: 0.0000 == 0.0 mm^3
  ok  [header] fpc roll to face >= 0.5: 0.0000 == 0.0 mm^3
  ok  [header] ufl jack to leg >= 0.3: 0.0000 == 0.0 mm^3
  ok  [header] buttons to leg (rst) >= 0.3: 0.0000 == 0.0 mm^3
  ok  [header] header body 0 to lip/leg >= 0.13999999999999999: 0.0000 == 0.0 mm^3
  ok  [header] header body 1 to lip/leg >= 0.13999999999999999: 0.0000 == 0.0 mm^3
  ok  [header] header pins (+0.19) x holder: 0.0000 == 0.0 mm^3
  ok  [header] USB plug overmold (+0.30) x holder: 0.0000 == 0.0 mm^3
-- 4[header] lens datum and retention
  ok  [header] sensor plate bearing area on the face: 17.1729 >= 6.0 mm^2
  ok  [header] lens top proud of the face outer: 1.9100 >= 1.0 mm
  ok  [header] lip reach under the header strip: 0.7500 >= 0.5 mm
     z play: header board 0.15, bare board 2.65 (ribs grip the PCB edge)
     +x: end wall | +/-y: legs + ribs | +z: face on the sensor plate | -z: lips | -x: NONE on the holder — ring ledge / friction
-- 5[header] overhangs, standing on the end wall
  ok  [header] faces steeper than 45 deg facing the bed, off the bed: 0.0000 == 0.0 mm^2
-- 1[pcb] solid and bounds
  ok  [pcb] solid count: 1.0000 == 1 
  ok  [pcb] valid: 1.0000 == 1 
  ok  [pcb] bound x min: -1.0000 == -1.0 mm
  ok  [pcb] bound x max: 23.0500 == 23.05 mm
  ok  [pcb] bound y min: -4.2500 == -4.25 mm
  ok  [pcb] bound y max: 22.0300 == 22.03 mm
  ok  [pcb] bound z min: -1.3500 == -1.3499999999999999 mm
  ok  [pcb] bound z max: 14.8600 == 14.86 mm
     volume 2421 mm^3, depth 13.40, width 22.08
-- 2[pcb] board insertion sweep (rib-less holder; ribs reported apart)
  ok  [pcb] board stack x holder over the sweep, max: 0.0000 == 0.0 mm^3
  ok  [pcb] grip ribs x PCB, seated (0.10 crush x 4): 0.4501 >= 0.3 mm^3
  ok  [pcb] grip ribs x PCB, seated, upper: 0.4501 <= 1.2 mm^3
  ok  [pcb] grip ribs x everything else: 0.0000 == 0.0 mm^3
-- 3[pcb] clearances (mock inflated by g must not touch)
  ok  [pcb] sensor plate to face >= 0.13999999999999999: 0.0000 == 0.0 mm^3
  ok  [pcb] lens barrel in keyhole >= 0.19: 0.0000 == 0.0 mm^3
  ok  [pcb] expansion PCB to end wall >= 0.19: 0.0000 == 0.0 mm^3
  ok  [pcb] USB shell to holder >= 0.5: 0.0000 == 0.0 mm^3
  ok  [pcb] card to holder >= 0.5: 0.0000 == 0.0 mm^3
  ok  [pcb] fpc roll to face >= 0.5: 0.0000 == 0.0 mm^3
  ok  [pcb] ufl jack to leg >= 0.3: 0.0000 == 0.0 mm^3
  ok  [pcb] buttons to leg (rst) >= 0.3: 0.0000 == 0.0 mm^3
  ok  [pcb] USB plug overmold (+0.30) x holder: 0.0000 == 0.0 mm^3
-- 4[pcb] lens datum and retention
  ok  [pcb] sensor plate bearing area on the face: 17.1729 >= 6.0 mm^2
  ok  [pcb] lens top proud of the face outer: 1.9100 >= 1.0 mm
  ok  [pcb] lip reach under the header strip: 0.7500 >= 0.5 mm
     z play: header board -2.35, bare board 0.15 (ribs grip the PCB edge)
     +x: end wall | +/-y: legs + ribs | +z: face on the sensor plate | -z: lips | -x: NONE on the holder — ring ledge / friction
-- 5[pcb] overhangs, standing on the end wall
  ok  [pcb] faces steeper than 45 deg facing the bed, off the bed: 0.0000 == 0.0 mm^2

CHECK PASSED
