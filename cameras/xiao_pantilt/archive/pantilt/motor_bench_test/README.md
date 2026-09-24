# XIAO ESP32S3 DRV8833 bench motor test

This Arduino sketch is a supervised wiring/direction test only. It does not use the camera, limit switch, microSD, scheduler, or any automatic movement.

Wiring:

| XIAO ESP32S3 | DRV8833 |
| --- | --- |
| D0 / GPIO1 | AIN1 |
| D1 / GPIO2 | AIN2 |
| D2 / GPIO3 | SLP (nSLEEP) |

SLP is driven by the sketch: LOW (driver asleep) at boot, idle, and after every pulse; HIGH only for
the 2 ms wake-up plus the pulse itself. The breakout's internal pulldown keeps the driver asleep while
the XIAO is in reset or unpowered. GPIO3 is a strapping pin (JTAG source select) and reads LOW at
reset with this load, which is the default, so it does not disturb boot.

The sketch sets both inputs LOW before serial starts, never moves automatically, and detaches PWM then drives both pins LOW after each fixed 200 ms pulse. Duty defaults to a deliberately low 18% and can be raised with the number keys. Verify motor supply polarity and that the mechanism is clear before connecting motor power.

## Build and upload

The local Arduino CLI is 1.5.1, but this workspace currently has no ESP32 Arduino core installed, so a target compile was not run here. The sketch supports ESP32 Arduino Core 2.x and 3.x LEDC APIs.

Install the core if needed, then compile:

```sh
arduino-cli core update-index
arduino-cli core install esp32:esp32
arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32S3 motor_bench_test
```

Upload only after completing the safety checks above, replacing the serial device with the actual XIAO port:

```sh
arduino-cli upload -p /dev/ttyACM0 --fqbn esp32:esp32:XIAO_ESP32S3 motor_bench_test
```

## Battery demo wiring (1S LiPo, no USB)

The XIAO 5V pin is VBUS only and is dead on battery, so VM must come straight
from the cell. The XIAO's BAT+ / BAT- pads on the underside feed its 3.3 V
regulator and the onboard charger (USB charges the cell at about 100 mA).

| Cell (JST-PH) | goes to |
| --- | --- |
| + | XIAO BAT+ pad **and** DRV8833 VM |
| - | XIAO BAT- pad **and** DRV8833 GND |

Keep SLP on D2/GPIO3, AIN1/AIN2 on D0/D1, motor on AOUT1/AOUT2, and put
220-470 uF low-ESR plus 0.1 uF across VM/GND at the driver. Use a cell with a
protection PCB; the XIAO has no low-voltage cutoff. Flash over USB, unplug,
connect the cell, wait about two seconds, press BOOT: ten forward/reverse
cycles run, then everything returns LOW.

### Bench supply standing in for the cell while USB stays connected

Wiring a 4 V bench supply to the BAT pads with USB plugged in works, with two
caveats. The XIAO runs from VBUS whenever USB is present, so this does not
prove the BAT-pad power path; only a real unplugged test does. And the onboard
charger will push up to 100 mA into the "battery" node and pull it toward
4.2 V, so set the supply to 4.2 V (the charger then sees a full cell and
terminates) or expect the idle VM reading to disagree with the knob. Low-voltage
sweeps with USB connected should feed VM/GND only, not the BAT pads.

## Bench result (2026-09-12)

Proven on the real head with the XIAO 5 V pin feeding DRV8833 VM and SLP tied
to XIAO 3V3: the N20 worm drive did **not** break away with 200 ms pulses at
18, 30, 50, or 70 % duty and moved in both directions at 90 %. A two-minute alternating
90 % sweep on a bench supply then kept reasonable torque down to **2.6 V at
VM**, so a single LiPo straight into VM is fine across its whole discharge
range at near-full duty. Note the asymmetry: 70 % PWM from 5 V (about 3.5 V
average) did not move the head but 2.6 V DC did. With one input PWM and the
other LOW the DRV8833 runs fast decay, so low-duty torque is much worse than
the average voltage suggests. In the firmware prefer near-100 % duty, or
slow-decay drive (one input held HIGH, the other PWM'd) if PWM is needed.
Add bulk capacitance (220-470 uF low-ESR plus 0.1 uF) on VM at the driver so
breakaway current does not sag the shared cell into the XIAO's brownout.

The XIAO's BOOT button must be released before reset, otherwise the board
re-enters the ROM bootloader on every reset and the sketch never runs.

**Battery demo proven 2026-09-12:** with a 1S cell on the XIAO BAT pads and
DRV8833 VM, SLP on D2/GPIO3, and USB unplugged, the heartbeat LED blinks and a
BOOT press runs the ten-cycle forward/reverse demo at 100 % duty. Flashing and
the same demo over serial (`d`) work with the cell left connected and USB in.

## Use

Open serial monitor at 115200 baud. Commands are single characters:

- `f` — one forward 200 ms pulse.
- `r` — one reverse 200 ms pulse.
- `t` — one 200 ms pulse, alternating direction on each use.
- `s` — force stop; both AIN pins LOW.
- `1`…`9` — set the duty for later pulses to 10…90 %. Selecting a duty never moves the motor.
- `0` — set 100 % duty: plain DC drive with no PWM, the right setting for a 1S LiPo on VM.
- `d` — demo: 10 bounded forward/reverse cycles (200 ms pulses, 600 ms gaps) at 100 %, then stop.
- **BOOT button**, pressed after boot — runs the same demo with no host attached. Press again during
  the demo to abort. GPIO0 is only a strapping pin at reset; afterwards the sketch reads it as an input.
- `h` or `?` — print help, safety reminder, and the current duty.

`f`, `r`, and `t` always return the bridge inputs to LOW after the bounded pulse.
