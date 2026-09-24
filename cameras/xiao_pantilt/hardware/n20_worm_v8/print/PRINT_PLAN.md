# N20 Worm V8 print plan

Status: **print the calibration coupon first; do not commit to the full assembly yet.**

The exported STEP, STL, and 3MF geometry rebuilds cleanly. Every STL is a closed,
watertight manifold with no degenerate triangles, and every 3MF archive is valid.
Those checks do not validate gear torque transfer, hardware fit, support removal,
strength, wear, or slicer settings.

The 3MF files contain geometry only. They do not contain a printer profile,
material profile, supports, or a sliced toolpath.

## Stage 1: print now

Load these three 3MFs on one plate:

- `n20_worm_v8_mesh_coupon.3mf`
- `n20_worm_v8_worm.3mf`
- `n20_worm_v8_wheel.3mf`

Starting profile for a 0.4 mm nozzle:

- Material: PLA for the first crisp dimensional trial, then repeat in the intended
  final gear material.
- Layer height: 0.12-0.16 mm for the worm and wheel.
- Walls: 4.
- Supports: none on the coupon or wheel; keep support off the worm flanks.
- Orientation: leave all three as imported. The worm is vertical, solid nose down;
  the wheel is teeth-up.
- Add a 6-8 mm brim to the worm only. Its bed contact is small.
- Preview the first 5 mm of the worm layer by layer. Its abrupt thread start can
  create an unsupported island/cantilever. If the slicer cannot bridge it cleanly
  without touching a working flank, stop and remodel the run-in before printing.
- Keep the brim physically clear of the wheel teeth. Use calibrated per-object
  elephant-foot compensation and verify the bed-facing first-layer tooth outline.

Acceptance gate:

1. The worm snaps into both coupon cradles without cracking them.
2. The wheel drops freely over the coupon's 19 mm pilot.
3. Turn the worm in both directions for at least 24 turns (one wheel revolution).
4. Reject on binding, tooth skipping, crest damage, or visible fixture flex.
5. Measure and decide an acceptable reversal backlash for the camera.
6. Repeat the coupon in the intended final material/settings before printing the
   remaining parts.

The current wheel uses radial trapezoidal gaps rather than a conjugate/hobbed
worm-wheel tooth form. The nominal static gap is 0.624-0.649 mm. The coupon is the
required proof of motion; the CAD check alone does not prove load capacity.

## Stage 2: real-hardware fit checks

Before the housing, print and test the cap, holder/latch, motor retainer, and DRV
retainer against the actual tube, XIAO, right-angle USB cable, N20 motor, and
DRV8833 board. In particular, the DRV retainer assumes an unpopulated 1.5 mm board
edge and has only 0.05 mm nominal clearance above the PCB. Test the worm's 3.15 mm
D-socket and 2.65 mm flat span on the actual 3 mm / 2.5 mm-flat motor shaft.
These small fit parts do not validate the base's motor/PCB pockets or tube locator;
measure those interfaces before committing to the base.

Recommended orientation:

- Cap: as imported, top face down.
- Holder and motor retainer: as imported, with a 4-8 mm brim for their narrow bed
  contact.
- Holder latch: as imported, with a 3-5 mm brim.
- DRV retainer: invert in the slicer so its upper frame face is on the bed.

## Stage 3: full prototype only after Stages 1-2 pass

The base and rotor must be printed separately. Their current one-piece geometry
requires removable support on functional internal surfaces; neither part is a
validated production print.

- Base: upright as imported, 5-8 mm brim. Paint support under the annular deck,
  motor saddle, radial ribs, nose web/bracket, stop webs, and low spokes. Block
  support from the 8.5 mm cable bore, 16 mm journal, M2 holes, tube locator, and
  horizontal worm nose bore. Expect to ream the 7.325 mm nose journal.
- Rotor platform: upright as imported, 6-10 mm brim. Use tree/organic support or a
  breakaway/soluble interface under the receiver, torque-key tips, disk underside,
  and small mast bridges. Block support from the 16.45 mm bore, 19 mm sleeve, key
  pocket, and clip grooves.
- Lid, wheel, stop parts, and clips: as imported, generally support-free.
- Print 3-5 copies of each thin clip: `rotor_retainer`, `wheel_retainer`, and
  `stop_arm_retainer`. Their installation life is not yet validated. PETG or
  unfilled nylon is preferable for the clips.

For PETG housing parts, start with 0.20 mm layers and 4 walls. Inspect the sliced
preview for adequate paths on the 1.10 mm worm crest, 1.1 mm DRV frame, 1.3 mm
motor plate, and 1.0-1.2 mm clips. Printer-specific speed, temperature, cooling,
flow, support interface, and XY compensation must come from a calibrated profile.

## Final checks before adding the camera

- Verify the actual motor shaft/body, PCB edges/components, tube ID/OD, XIAO, and
  USB overmold dimensions.
- After removing supports and before installing clips, dry-fit the 16/16.45 mm
  journal, 19/19.5 mm sleeve-wheel interface, receiver/keys, and reamed 7.325 mm
  worm nose journal. Reject any fit that binds after cleanup.
- Confirm all three clips survive installation and remain seated.
- Confirm the complete 8.5 mm cable passage is clear.
- Rotate through the full travel by hand and verify the physical stops.
- Run the motor unloaded at low voltage before fitting the tube/camera payload.

Assembly order and nominal dimensions are documented in `../README.md`.
