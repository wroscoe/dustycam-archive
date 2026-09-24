# xiaocam1: `game_lowpower` on the XIAO ESP32S3 Sense — implementation plan

Written 2026-09-12 against `docs/camera_standard.md`, `docs/camera_operation.md`
(§4.1 profile, §5 contact, §6 night, §7 storage, §8 time, §10 LED),
`docs/animal_model.md`, `docs/camera_recipe.md`. Device id **`xiaocam1`**
(the pan-era `xiaopantilt` id was never deployed; the camera is now static in
`hardware/tubecase`). The pan-era software is archived under `archive/pantilt/`.

## 0. Runtime decision: ESP-IDF 5.5

ESP-IDF, built hermetically in the `espressif/idf:release-v5.5` Docker image
that is already on this machine (the camlogger's path; no host toolchain).
Reasons, in order:

1. The standard names `runtime/espidf/components/` as the home of the
   shared stages; the Arduino core has no equivalent and would make this
   camera a second one-off.
2. Everything the profile needs is native IDF: deep sleep with RTC memory,
   `esp_ota` with bootloader rollback, `esp_https_ota`, `esp_http_server`,
   `esp-tflite-micro` + `esp-nn` as managed components, `sdspi` + FATFS.
3. The camlogger's design (RTC thumbnail diff, wake counters, fail-open gate,
   mark-valid-after-upload) is IDF code and ports directly.
4. The Arduino proof transfers: core 3.3.x is IDF 5.5 underneath and the
   same `esp32-camera` 2.1.7 driver; the proven facts are pins, PSRAM = OPI,
   SD CS 21, sensor PID 0x3660.

No blocker found. Two things to carry over from the Arduino run: the build
must select octal PSRAM (`CONFIG_SPIRAM_MODE_OCT=y`) and FATFS long names
must be on (`CONFIG_FATFS_LFN_HEAP=y`). The component cache from the
camlogger (`managed_components/`, `dependencies.lock`: esp32-camera 2.1.7,
esp-tflite-micro 1.3.7, esp-nn 1.2.5, esp_jpeg) is copied into the project
so the build needs no network. Docker is the sandbox for the build; nothing
is installed on the host.

## 1. Layout

```
cameras/xiaocam1/
  README.md  camera.toml  PLAN.md
  archive/pantilt/          pan-era firmware, sim, motor bench, SPEC (reference only)
  hardware/                 tubecase (current), pantilt, n20_worm_v8
  software/
    app/                    ESP-IDF project: CMakeLists.txt, main/, sdkconfig.defaults,
                            partitions.csv, version.txt, Makefile (docker build/flash/stage),
                            sdkconfig.secrets (generated, gitignored), managed_components/
    bench/sd_camera_test/   proven Arduino camera+SD sketch (kept)
    host/                   monitor.py (serial log + commands), bench notes
  tests/                    host unittest (pytest-collectable): test_core.py, test_dustygen.py
runtime/espidf/
  components/
    dusty_core/     portable C, no IDF headers: motion, rank, night, meta, cfg, spool naming, http date
    dusty_uplink/   esp_http_client: post_blob, post_telemetry, get_json, get_text, Date capture
    dusty_spool/    SD mount, /spool/<boot>/<seq>, sidecars, scan + rank, delete, reclaim, counts
    dusty_config/   defaults (generated header) + NVS store + apply pulled JSON
    dusty_ota/      version check, esp_https_ota, pending/bad bookkeeping, mark valid
    dusty_control/  esp_http_server :8266 — /status /setup /live /stream /shoot /refresh
    dusty_led/      one-LED pattern task (see §7 for the SD CS conflict)
  tests/            test_core.py drives libdusty_core.so through ctypes (gcc on the host)
```

`tests/` use `unittest` (stdlib): pytest is not installed on this host and
pytest collects `unittest.TestCase` when it is.

## 2. Board facts (tier 3, in `main/board.h`)

| fact | value |
|---|---|
| camera | OV3660, PID 0x3660; official XIAO map: XCLK 10, SCCB 40/39, D0..D7 15,17,18,16,14,12,11,48, VSYNC 38, HREF 47, PCLK 13; PWDN/RESET -1 |
| capture | `FRAMESIZE_UXGA` 1600x1200 sensor JPEG, quality 10, 2 fb in PSRAM, XCLK 20 MHz, 4 warm-up frames, zero-init `camera_config_t` |
| SD | sdspi CS 21, SCK 7, MISO 8, MOSI 9, mount `/sd`, 64 GB SDHC proven |
| LED | GPIO21 active-low, **shared with SD CS** (§7) |
| button | GPIO0 BOOT, active-low; strapping pin (§8 gate 1) |
| PSRAM | 8 MB octal; flash 8 MB |
| battery | no divider on the XIAO; `batt_v` not applicable in this pass (bq25185 in the tubecase has no telemetry pin wired). `charging` not applicable. |
| deny list | none known; `esp_camera_init` twice without deinit hangs SCCB (sarg) — always deinit before sleep |

## 3. Persistent state

| where | what | survives |
|---|---|---|
| RTC slow memory | `rtc_state_t`: magic, thumb 40x30 (1200 B), thumb_valid, wake_n, seq, awake_ms accumulator, last_record_awake_ms, night state (dark_n, in_night, night_start_s), clock state, contact_pending flag, debug_written | deep sleep, not power loss |
| NVS `dusty` | `cfg` JSON blob (pulled config), `boot_count`, `seq_base`, `last_ts`, `fw_pending`, `fw_bad`, `contact_n` | power loss |
| SD `/night.json` | last 7 night lengths (s) | power loss, card pull |
| SD `/spool/<boot>/<seq>.jpg,.json` | frames + sidecars | |
| SD `/debug/<boot>/<seq>.jpg,.json` | `why: watch` previews | |

`boot_count` increments on every non-deep-sleep reset. `seq` is monotonic
per boot (RTC), written in the sidecar.

## 4. One wake (`game_lowpower`), the order in `main.c`

```
app_main
  rtc magic check → cold boot: zero rtc, boot_count++, thumb invalid, clock = none/est
  wake cause: timer | ext1 GPIO0 | cold
  config: dusty_config_init(defaults from tuning_defaults.h, NVS override)
  if fw pending-verify: contact_pending = 1 (must upload + mark valid before any sleep)
  if wake by button or contact_pending: → CONTACT (§5), then continue below with a fresh capture
  mount SD (dusty_spool_mount); on failure: LED fail pattern, still run (record refused)
  camera init; capture UXGA JPEG
  thumb ← decode 1/8 (200x150 RGB565) → 40x30 box-average gray   (dusty_core)
  lum ← mean(thumb)
  NIGHT step (§6): may deep-sleep right here without recording
  diff ← dc_thumb_diff(thumb, rtc.thumb, diff_l_thresh) → frac + bbox   (invalid ref → frac 1.0, why boot)
  trigger:  why = boot (no ref) | motion (frac ≥ diff_min_frac) | interval (wake_n % interval_n == 0)
            | heartbeat (awake_ms since last record ≥ heartbeat_s*1000) | none
  if debug_frames and debug_written < debug_max: write preview JPEG (fmt2jpg of the 200x150) to /debug with why: watch
  if why != none:
     JUDGE (§9): det, keep; score = dc_score(why, conf, frac, sharp)
     if keep: dusty_spool_write(jpg, meta+score) ; rtc.thumb ← thumb ; last_record ← now ; LED blink if led_capture
  camera deinit; SD unmount; persist rtc; awake_ms += uptime
  deep sleep period_s, wake on timer + ext1(GPIO0 low)
```

Meta (every frame, `dc_meta_build`): `ts seq w h v cfg ip mode why diff gate
heartbeat buffered lum clock score` + `det` when the gate ran + `night_s` on
the morning frame. `ip` = "0.0.0.0" outside contact. `mode` = `live`
(`contact` during contact). `buffered` = true for anything from the spool
(always, on this camera).

## 5. Contact (`camera_operation.md` §5), `contact.c`

1. LED searching. `esp_wifi` STA, scan for the hotspot SSID, connect; wait
   up to `hotspot_join_s`. Fail → LED fail, return to caller (night or live).
2. Clock: first server response's `Date` header (config GET is the first
   request) → `dc_parse_http_date` → `settimeofday`; `clock_skew_s` = server −
   board; `clock` ← `set`; `last_ts` to NVS.
3. Announce telemetry: `mode 3`, `boot_count`, `pending_files`, `pending_cold`,
   `clock_skew_s`, `night`, `contact_n`, `rssi`, `mem_free`, `uptime_s`.
4. Firmware: `GET /firmware/xiaocam1/version`; if ≠ running and ≠ `fw_bad`:
   `esp_https_ota` from `/firmware/xiaocam1.bin` (X-Token), write
   `fw_pending`, set `contact_pending`, restart. The new image boots straight
   into contact and marks itself valid after its first accepted upload
   (telemetry counts). If it never gets there it must not sleep: it restarts
   → bootloader rolls back → the old image sees `fw_pending` ≠ self and
   writes `fw_bad`.
5. Config: `GET /config/xiaocam1` → `dusty_config_apply` (known keys only) →
   NVS; LED three quick blinks if `cfg` changed.
6. Drain: `dusty_spool_scan` reads every sidecar's `score`, sorts descending
   (heartbeat/boot first by score), uploads up to `upload_cap`; each 2xx →
   delete jpg+json. Then `/debug` up to `debug_max`. Telemetry every
   `telemetry_s`; `dusty_control` served between frames (esp_http_server runs
   in its own task; the drain yields).
7. Serve until `contact_idle_s` with no request (setup page may extend it;
   `/live` ends it).
8. Final telemetry, radio off, `contact_n++`, motion reference reset, one
   `why: boot` frame recorded, resume.

Uplink: `esp_http_client`, `X-Token`, TLS when `SERVER_TLS` (Funnel), cert
bundle on, `Connection: close`, 4 KB chunked body from the spool file.

## 6. Night (`camera_operation.md` §6), `dc_night_step` in dusty_core

Pure function of (state, lum, now, cfg): `lum < lum_night` for
`night_confirm_n` consecutive wakes → enter night (record night_start; sleep
`predicted − night_margin_s` if history ≥ 1 else `night_probe_s`); while in
night each probe wake: `lum > lum_day` → leave (night_len = now − start;
push to history; morning frame `why: boot` with `night_s`), else sleep
`night_probe_s`. Prediction = median of the last 3 lengths. Radio never
comes up at night except by button. The cold-boot `est` clock is fine here:
only durations matter.

## 7. LED language on this board

GPIO21 is both the user LED and the SD chip select, so the LED task may
toggle it only while it holds the SD mutex (no card I/O in flight) and the
spool component asserts CS itself per transaction. Consequences, documented
in the README as the XIAO's deviation from `camera_operation.md` §10:

- searching / fail / settings-updated / recovery patterns: as specified (SD idle).
- draining: the LED shows card activity (flicker) instead of solid.
- live: one blink per recorded frame comes for free from the write.

## 8. Bench gates, in order (each recorded in sarg)

1. **BOOT wake.** Does a GPIO0 press in deep sleep run the app (ext1 wake) or
   fall into the ROM download mode because the strapping pin is sampled on
   the wake reset? First flash tests only this. If it fails, the button moves
   to another GPIO on the mid plate (a hardware change) and this plan's
   `BUTTON_GPIO` changes.
2. Deep-sleep current with the Sense board and card fitted (sarg says 1–4 mA
   leak; measure with the tubecase wiring).
3. Hotspot join time against the real phone on 2.4 GHz, 10 tries.
4. Upload throughput through the phone for a ≥ 200-frame drain.
5. RTC drift: `clock_skew_s` at every contact for two weeks (firmware logs it;
   the measurement is just running it).
6. Gate timing: ESP-NN on, arena placement, ms per inference at 96 px.

## 9. Judge, this pass

The camlogger's `gate.cc` + `gate_model_data.cc` (MobileNet 96x96x3 int8,
2-class, 643 KB) copied into `main/`, ops list unchanged. `det` =
`[{"label":"animal","conf":c}]`. Keep if `animal` ∈ `keep_labels` and
`c*100 ≥ gate_pct`; else discard unless `keep_all` or the 1-in-`audit_n`
audit (`why` stays, meta gets `audit: true`). Fail-open: gate init or
invoke failure → keep, `det` omitted. Input = motion-centred crop from
`dc_crop_box` (bbox of the thumb mask, padded 50 %, square, clamped; full
frame when diffuse) taken from the 1/4-scale decode (400x300), nearest
resize to 96, `^0x80` to int8. Not retrained.

## 10. Config keys (tuning, tier 2)

`camera_operation.md` §4.1 verbatim plus `spool_max_frames = 20000`,
`diff_l_thresh = 8`, `led_capture`. `dustygen` stamps them into
`main/tuning_defaults.h` (committed, GENERATED header) and the server JSON.

## 11. dustygen for espidf

`runtime = "espidf"` → writes `software/app/sdkconfig.secrets`
(`CONFIG_DUSTY_DEVICE`, `CONFIG_DUSTY_WIFI_SSID/PASS` from
`[hotspot]` in secrets.toml, `CONFIG_DUSTY_SERVER_HOST/PORT/TLS`,
`CONFIG_DUSTY_BLOB_TOKEN`), stamps `tuning_defaults.h`, writes the server
config, and with `--stage` copies `software/app/build/xiaocam1.bin` and
`.version` (= `version.txt`) to `/hd2/sensorhub/firmware/`. `--public` is
the default for this camera (`hotspot` capability ⇒ Funnel). The hotspot
keys must be added to `~/.dusty/secrets.toml` by the owner; dustygen fails
with a clear message if they are missing.

## 12. Work packages

| # | package | model | depends on |
|---|---|---|---|
| A1 | `dusty_core` + host tests | sonnet | — |
| A2 | `dustygen` espidf + `camera.toml` + README skeleton + `tests/test_dustygen.py` | sonnet | — |
| A3 | IDF project skeleton + `dusty_uplink/spool/config/ota/led/control` + Docker build of a stub main | sonnet | header API in A1 (fixed in this plan) |
| B | `main.c` + `contact.c` + `judge` wiring: the wake cycle, contact, night | sonnet | A1–A3 |
| C | review (root), fixes, Docker build, `version.txt` bump, dustygen run, **ask before first flash** | root | B |
| D | bench gates 1–6, sarg lessons, README status line | root + owner | flash |

## 13. Out of scope / sensorhub needs (README lists them)

N6; mesh; model retraining; exposure ladder (camlogger's low-light gain
steps are left out so `lum` stays comparable across wakes; revisit with the
night-threshold data). Sensorhub: `mode 3` on pages, `clock` correction of
`ts`, `pending_cold` / `contact_n` on the device page, a `why: watch` debug
viewer, `score` shown on frames.
