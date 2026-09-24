# N20 worm v8 — printable pan drive

This is an independent sibling of `hardware/pantilt` v7; it does not modify that design. It puts one Acxico/GA12-N20 motor horizontally in the Ø98 mm (nominal “~96 mm”) lower case. Its 3 mm D shaft drives a printed extension worm, outboard nose journal and thrust shoulders, then a separately printed 24T vertical-axis wheel and rotor platform. The camera holder preserves v7's verified holder intent: 20.95 × 17.78 board, 0.4 mm side clearance, 2 mm walls/back, 0.95 mm lips and 0.2 mm lip gap.

## Design contract

| item | value |
|---|---:|
| axial module / worm lead | 1.25 / 3.927 mm |
| worm pitch / OD / root diameter | 10 / 12.5 / 6.875 mm |
| wheel | 24T, 30 mm pitch diameter, 8 mm face |
| nominal centre distance / ratio | 20 mm / 24:1 |
| pan range | usable ±90°; physical stops at ±95° |
| cable bore | Ø8.5 mm continuous through journal and lid |
| tube | 50.8 OD, 44.5 ID acrylic tube interface |
| N20 envelope | 34 × 12 × 10 mm, Ø3 D shaft × 10 mm |
| DRV8833 keepout | 26 × 18 × 3 mm PCB + 6 mm headers |

`positive worm rotation -> negative pan = -15° per worm revolution`. The worm hand is explicitly positive/right-hand in source. The motor, tube and camera are labeled purchased; the DRV8833 is an envelope only; all labeled `printed_*` case/structure/gear components are printable.

## Important prototype note

The worm is a true swept trapezoidal helix with a 1.10 mm crest, formed as one continuous BREP solid rather than sub-nozzle fins. The 24T wheel still has radial trapezoidal tooth gaps rather than a numerically hobbed conjugate surface. The pair is therefore intentionally labeled **PROTOTYPE, not print-ready for load use**. Print the `mesh_coupon` fixture plus the normal worm and wheel, snap the worm into the two open-top cradles, and check rolling resistance/backlash before committing to the full case. The fixture reproduces the 20 mm shaft spacing and gear-height alignment. This is not a torque, wear, or backlash guarantee.

## Parts

- Printed: `base`, `lid`, `rotor_platform`, `bottom_stop_collar`, `bottom_stop_finger`, `bottom_stop_arm_axial_c_clip`, `worm`, `wheel`, `holder`, `holder_latch`, `cap`, `mesh_coupon`, `motor_retainer`, `drv_retainer`, `wheel_retainer`, and `rotor_retainer`.
- Purchased: Acxico N20 motor (the project reference STEP is used); 50.8 mm acrylic tube; XIAO ESP32S3 Sense; Adafruit DRV8833 breakout.
- A 2.3 mm upper annular deck covers the drive compartment. The tube wall bears on this deck and is radially located by a printed outer lip; the cap remains a separate plug. Rotor sweep has 0.45 mm radial clearance to the deck's Ø43.3 opening.
- The motor rests on a wall-tied saddle and is positively captured in X by a removable end-stop plate (two M2 screws: base Ø2.2 clearance, retainer Ø1.7 pilot). The DRV8833 rests on its shelf and is held by a removable two-M2 open frame. Its inward tabs overlap only an assumed 1.5 mm bare PCB perimeter strip, and stay outside the central 6 mm populated-header keepout; confirm that edge strip is unpopulated on the actual board. The bottom lid is retained by three M2 screws in webbed bosses.
- A printed central Ø16 journal, four ribs and rotor Ø16.45 bore preserve the Ø8.5 wire path; no bearing is assumed. The Ø16 journal head passes through the rotor bore but is larger than the Ø15.1 top-clip ID, so a top C-clip on the reduced neck retains rotor lift. The wheel counterbore accepts an annular rotor receiver and three printed torque keys; a lower C-clip on the rotor sleeve retains wheel drop. The rotor's lower sleeve remains inside the wheel bore (Ø19.0 versus Ø19.5) and has an internal +Y key pocket for a separate C-hub `bottom_stop_collar`; its tongue carries pan torque and a separate lower C-clip prevents collar drop. A separately installed `bottom_stop_finger` keys into the collar's elevated receiver and is fastened upward by two M2 screws. None of these features enter the central cable bore.
- The XIAO slides into the v7-derived holder and is then positively retained by a separate two-M2 top latch; remove the latch for board service. The USB rail/slot remains the bottom service opening; use a right-angle USB-C plug and verify its exact overmold clearance before print.
- v7's 503035 battery bay is intentionally not retained: this revision reserves the lower service volume for the N20, nose bracket, DRV8833 and wire bend radius. Add a separately measured battery tray only after choosing the intended power source.

The separate print generators place parts on Z=0. The worm is stood vertically on its solid nose, the cap is top-face-down, the wheel is teeth-up, and the remaining parts retain their natural upright orientation. The base and rotor are support-sensitive prototypes; inspect the internal shelves and lower stop-sleeve geometry in the slicer before printing.

## Mechanical assembly order

1. With the bottom lid removed, insert the wheel through the upper deck opening from above.
2. Insert the rotor platform (without the stop arm) from above; its Ø16.0 journal head passes through the Ø16.45 rotor bore.
3. From below, snap the wheel C-clip into the sleeve groove. Route the short C-hub collar with its bottom at Z=12.7 around the -X-side 30 mm-radius semicircle, move from Y=+30 to +21 while low, raise it to Z=15.45, then slide it inward around the Ø19.0 lower sleeve through its 19.6 mm -Y mouth. Engage its +Y tongue in the sleeve pocket and snap its lower C-clip into the groove.
4. Keep the straight stop finger low (bottom Z=12.7; key top Z=17.95, below the receiver at Z=18.15), slide it from Y=-10 to Y=0, then lift vertically to Z=15.45. Engage its rectangular key in the elevated collar receiver and install two M2 screws upward through the finger into the collar's Ø1.7 pilot holes.
5. From above, snap the rotor C-clip over the reduced journal neck; its Ø15.1 ID is retained below the Ø16.0 journal head.
6. Install the motor, DRV frame, holder/camera, tube and cap, then install the bottom lid. The fixed stop blocks are deliberately at ±95°; use only the validated ±90° operating range.

## Driver routing

| DRV8833 connection | route |
|---|---|
| `VMOTOR` | regulated supply appropriate for the owned 3–6 V N20 |
| `GND` | common motor/XIAO ground |
| `AIN1`, `AIN2` | two XIAO control GPIOs |
| `AOUT1`, `AOUT2` | the two N20 motor leads |

The second H-bridge is unused in this pan-only version. Confirm startup/stall current on the actual motor before choosing the supply path.

## Generate and check

```bash
CAD_SKILL=/home/wroscoe/.agents/skills/cad
CAD_PY=$CAD_SKILL/.venv/bin/python3
cd cameras/xiao_pantilt/hardware/n20_worm_v8
$CAD_PY $CAD_SKILL/scripts/step n20_worm_v8.step.py -o n20_worm_v8.step --force
$CAD_PY $CAD_SKILL/scripts/step print_worm.step.py -o print_worm.step \
  --stl print/n20_worm_v8_worm.stl --3mf print/n20_worm_v8_worm.3mf --force
$CAD_PY sweep.py
```

The local Sarg service was unavailable. The step.parts API was reachable after network permission but had no relevant exact N20 or DRV8833 model, so the assembly uses the existing project N20 envelope at `ref/n20/amz-n20-gearmotor.step`. The driver is a labeled clearance envelope: 26 × 18 × 3 mm plus 6 mm above for populated headers, based on [Adafruit's nominal 25.4 × 17.78 mm fabrication drawing](https://learn.adafruit.com/adafruit-drv8833-dc-stepper-motor-driver-breakout-board/downloads).
