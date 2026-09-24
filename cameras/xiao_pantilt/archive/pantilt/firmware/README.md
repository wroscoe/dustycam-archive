# XIAO ESP32S3 Sense pan-scanner firmware

This is an ESP-IDF firmware target for the XIAO ESP32S3 Sense and the project’s DRV8833 pan drive. Every 180 seconds it attempts one phase-locked scan at headings **0°, 80°, 160°, 180°**. With the default calibrated 110° horizontal FOV those views cover about 290° around a tree, with overlap between neighboring views. The scan then uses the same saved outbound image anchors to return and verifies the final home view before declaring success.

It has no motor encoder, current measurement, or inferred position. A motor pulse is only a bounded request. After each pulse, the firmware captures a settled JPEG, decodes a small luminance profile from that exact JPEG, and performs a pinhole-aware ZNCC registration against the prior profile. Low texture, low luminance-class diversity, strongly periodic/repeating profiles, competing correlation peaks, a failed image dock, an unwritable SD card, missing home datum, or any configuration gate aborts the current scan and stops PWM.

`CONFIG_PANTILT_MOTOR_ENABLE` defaults to **off**. In that default configuration the camera may initialize but every scan is refused before a GPIO can drive the DRV8833.

## Target wiring

The camera adapter uses the official XIAO ESP32S3 Sense map, fixed in `main.c`:

| signal | GPIO |
| --- | ---: |
| XCLK | 10 |
| SCCB SDA / SCL | 40 / 39 |
| D0…D7 | 15, 17, 18, 16, 14, 12, 11, 48 |
| VSYNC / HREF / PCLK | 38 / 47 / 13 |
| PWDN / RESET | -1 / -1 |

Camera capture is JPEG in PSRAM (`SVGA`, two frame buffers). The low-resolution registration profile is decoded from the same stationary JPEG buffer that is saved at each anchor; it is not a separate sensor or a claimed encoder.

The current Sense onboard microSD defaults are SPI `CS=21, SCK=7, MISO=8, MOSI=9`. All SD pins are Kconfig settings because an external card carrier may need a different mapping. GPIO21 is accepted only for SD use; it is not available to the motor/limit adapter. These pins are intentionally not copied from `camlogger`, which uses a different board.

Motor pin assignment is intentionally unset (`AIN1=-1`, `AIN2=-1`) until configured. Kconfig exposes AIN pins, logical direction, PWM frequency/duty, maximum pulse, settling delay, nominal pulse-sizing speed, maximum visual step, move/cycle pulse and time budgets, logical limits, homing direction/backoff/time/limit switch, and all SD pins. The actuator/limit whitelist is only `1–6, 43, 44`; SD accepts its own exposed whitelist including GPIO21. Package-only/internal GPIOs are rejected. GPIO41/42 are excluded because Sense wires them to the expansion PDM microphone. Boot validation also rejects a zero home direction; duplicate motor/limit/SD pins; every collision with a camera signal; a cycle budget that cannot cover cold-home + all six bounded anchor moves + reserved recovery home; an invalid logical range; or an FOV that cannot provide the configured overlap and 290° coverage for the fixed anchors.

## Mandatory bench gates

Do these in order, with the tube clear of people, cables, and tree hardware. A hardware stop can damage the drive; this firmware does **not** detect motor current or a stall.

1. Leave `MOTOR_ENABLE=n`. Build, flash, and confirm serial reports camera/SD initialization followed by a refused, non-actuating scan. Confirm SD mount before wiring the motor supply.
2. With motor power removed, set the DRV8833 AIN pins and inspect the compiled `sdkconfig`. Keep `MOTOR_ENABLE=n`; verify no AIN changes occur at boot with a meter or logic analyzer.
3. Confirm a real home limit-switch input and polarity. Set `PANTILT_HOME_LIMIT_GPIO`, enable motor power, and only then set `MOTOR_ENABLE=y`. Verify that activation stops homing immediately and that an inactive switch causes the bounded timeout/abort.
4. `PANTILT_ALLOW_BENCH_TIMED_HOME=y` retains a bounded, warning-producing actuator path for supervised electrical bench work only. Normal `run_scan_cycle` refuses to run at all without an actual configured home limit switch, so timed-only home is never reported as a scan/home success and cannot be used unattended or strapped to a tree.
5. Start with reduced PWM duty and pulse duration. Check both electrical directions, physical clearance over the full travel, and that the configured logical `0…180°` range matches actual mechanical stops. Do not rely on image registration to protect a bad mechanical limit configuration.
6. On a textured static bench scene, inspect serial output: every pulse must show a plausible signed registration and confidence above the configured threshold. Introduce a blank/occluded view and verify the scan aborts with PWM stopped. Verify the return-anchor dock and final home dock both pass before unattended operation.
7. Confirm each anchor writes matching `/sd/pantilt/*.jpg` and `.json`; JSON records monotonic capture time, requested logical heading, phase, JPEG length, and `position_source: image_registration_only`. Names contain a persistent NVS boot/sequence pair. The firmware reserves the sequence before writing, writes each file exclusively through `.tmp`, syncs and renames it, and removes orphan/temp captures at mount. It never overwrites an existing capture or records an imaginary motor angle.

## Build and host checks

Use ESP-IDF 5.1+; `main/idf_component.yml` fetches `espressif/esp32-camera`.

```sh
cd cameras/xiao_pantilt/software/firmware
./tests/run_host_tests.sh
idf.py set-target esp32s3
idf.py build
```

The first command compiles the planner, budget guard, and pinhole/ZNCC registration core with host `gcc`. Its deterministic vectors cover positive/negative/zero turns, affine lighting, blank frames, periodic ambiguity rejection (including exact two-level repeating stripes), safety windows, coverage validation, and pulse budgets. The candidate grid is capped at 0.25° to match the reference and limit accumulated quantization drift. The vectors use the same rectilinear projection convention as the CPython reference registrar. This target was also built successfully in an isolated ESP-IDF 5.5 Docker worktree with `esp32-camera 2.1.7`; no repository-local build output is needed for that check.

## Runtime behavior and bounds

- The schedule is monotonic and phase-locked to boot. A scan that runs long advances to the next future three-minute boundary; missed scans are not queued.
- Outbound photos are saved only at `0/80/160/180`. Intermediate settled JPEGs are used only to measure one short visual-servo step. A saved source-anchor cross-check is required where overlap is broad enough (the 160→180° leg with default geometry); the 80° legs have only 30° overlap, so the firmware does not falsely treat them as independently dockable far views.
- The return walk is reverse-only through the saved outbound anchors. Each dock and the final fresh home comparison must meet confidence and ±2° thresholds. Otherwise the cycle aborts and PWM is stopped.
- A previously verified home profile is checked at the beginning of each cycle and reused when it still docks, so the motor is not hard-homed every cycle. Warm acceptance never replaces that baseline, preventing baseline random-walk. It is refreshed only after a limit-switch home plus successful full visual return. If a validated re-home no longer matches the old image (for example after a seasonal scene change), that old baseline is discarded and the fresh limit datum may complete a new full visual return before becoming the baseline. Cold start, lost image home, and abort recovery use the production limit switch. An abort reserves enough powered-motion budget for that bounded recovery even if the normal scan deadline has elapsed, then directly checks the known home image when one exists; a failed recovery image check invalidates the warm baseline.
- A configured limit switch is the production home datum. If it starts active, firmware must first see it release during a bounded backoff and then re-trigger on approach; a stuck-active switch fails closed. The optional bench timed-stop setting is not accepted by normal scan operation. Image docking is still required before a cycle can report a verified return.

The portable core is in `main/pt_core.[ch]`, deliberately independent of ESP-IDF. This makes its no-encoder constraints and registration behavior testable on the host.
