# Device status

One line per device, updated when something is proven or breaks. The
vocabulary is `camera.toml`'s: **designed** → **built** → **live** →
**archived**. "Proven" means exercised on the real device, not read from
the code.

| Device | Dir | Status | Last proven | Notes |
|---|---|---|---|---|
| owlcam `rt1062cam` | `cameras/openmv_rt1062` | **live** 2.0.8-rt | 2026-09-03 | pull OTA + rollback, config pull, setup mode; no SD card (spool off) |
| `n6cam` | `cameras/openmv_n6` | **live** on `game_lowpower` 2.1.7-n6 (was monitor 2.0.10) | 2026-09-13 | proven on the device: standby + RTC wake, SD spool with the chain loader, button contact over the phone hotspot (join 3.5 s, clock set, config pull cfg 6→8, ranked drain 36 + 15 frames, telemetry mode 3), NPU gate 26 ms with the hard-fault guard. Numbers: ~2.6 s awake per wake, 1.7–2.4 s per uploaded file (TLS handshake bound, ~60 KB/s). Open: standby current (meter), RTC drift (weeks), rollback of a bad build on this profile, setup page from the phone. Button cannot wake standby: hold USER up to `period_s`. Bench tuning in config.toml: period_s 10, debug_frames on |
| `goouuu1` | `cameras/esp32_s3_cam` | built, silent since 2026-08-18 | 2026-08-18 | camlogger; Docker build path broken — phase 4 |
| pi5cam `dusty` | `cameras/pi5cam` | built, uploads nothing | — | crash-looping test file as service; phase 6, bench steps in its README |
| `xiaocam1` (was pantilt xiao) | `cameras/xiao_pantilt` | designed: ESP-IDF `game_lowpower` firmware builds, unflashed; static case modeled | 2026-09-12 | N20 worm on DRV8833 from a 1S cell: BOOT-button demo moves both ways on battery; needs ~100 % duty (fast-decay PWM starves it). Pan dropped for now: `hardware/tubecase` v2 is a static camera entirely inside a 2" acrylic tube: base liner with the bq25185 and 500 mAh cell standing up, barrel jack out the bottom, mid plate with the camera, 3 prints, 34/34 checks pass, not printed; camera + SD proven 2026-09-12 (`software/bench/sd_camera_test`: OV3660 UXGA JPEG to a 64 GB card via Arduino core). Off-grid firmware written 2026-09-12 per `PLAN.md` (wake cycle, SD spool, hotspot contact, night policy, gate) on new `cameras/common/espidf` components, 48 host tests pass, Docker build OK; pan software archived under `archive/pantilt/`. `hardware/puckcase` v1 (2026-09-13): sealed XIAO case that presses into the power puck's front mouth (front plate + ring with eave + coupling back plate, 4 × M2), check.py passes, not printed. **BLE/phone P0 spike proven 2026-09-15** (`cameras/common/espidf/bench/ble_spike` + `apps/dustyphone`): Pixel 6 ↔ NimBLE hello/auth/status/preview at 65–85 KB/s, sequential BLE→Wi-Fi→BLE handoff with UDP beacon discovery, 21 round trips heap-flat; plan `docs/phone_app_plan.md`, next = P1 (dusty_ble full ops, NVS identity, config push). Next on the camera: bench gate 1 (BOOT-button wake from deep sleep); print the puckcase bay coupon |
| `speedcam1` | `cameras/n6_speedcam` | designed | — | radar parser tested on the host; carrier/case/power designed 2026-09-02, unbuilt — phase 5 |
| `xiaomic1` | `sensors/miclogger` | built | 2026-08-26 | continuous audio to sensorhub; not on the standard |
| espnowbridge | `sensors/espnowbridge` | built | 2026-08-26 | ESP-NOW repeater for the miclogger |
| espnowmeter | `sensors/espnowmeter` | built | 2026-08 | bench RSSI meter |
| plantlogger | `sensors/plantlogger` | built, deployed | 2026-07-21 | FeatherS3 soil logger → plantlog :8087 |
| CornsnowBase | `mesh/` | live | 2026-09-01 | Heltec V4 base station node (serial owned by sensorhub's meshbase.service) |
| DuckBisonRepeater | `mesh/` | live | 2026-09-01 | RAK4631 MeshCore repeater 1.17.1 |

Server side for all of them: `~/code/sensorhub` (ingest, blob gate, MQTT,
pages, OTA staging in `/hd2/sensorhub/`).

## The standard

`docs/camera_standard.md` is in force. Phases (from
`docs/camera_standard_proposal.md` §9): 0 docs, 1 server gate, 2 shared
MicroPython runtime + `tools/dustygen`, 3 N6 — **done 2026-09-03**;
4 esp32 camlogger, 5 speedcam from the recipe, 6 pi5cam — open.
