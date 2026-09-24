# openmv_n6 `game_lowpower` plan (2026-09-13)

Implements `docs/camera_operation.md` §4.1 on the OpenMV N6 by extending
the shared MicroPython runtime (`runtime/micropython`) rather than
writing a second app. The profile is a tuning key: the same bundle runs
`monitor` (today's LAN camera) or `game_lowpower` (off-grid, wake cycle),
chosen by `profile` in `camera.toml [tuning]` / the server config.
Sibling: `cameras/xiaocam1/PLAN.md` (ESP-IDF); the two must agree on
the contract (§9 of the operation spec), not on code.

## 0. Runtime decision: MicroPython, shared runtime

The N6 is live on `runtime/micropython` (2.0.10-n6). Everything the
profile needs exists in fw 5.0.0 and was probed on the bench 2026-09-13:

| fact | proven |
|---|---|
| `machine.deepsleep()` is STM32 standby; `machine.RTC().wakeup(ms)` wakes it | yes: 10 s and 5 s sleeps, `reset_cause() == DEEPSLEEP_RESET (4)` |
| RTC survives standby | yes: a deliberately set 2031 date came back advanced by the sleep |
| TAMP backup registers survive standby | yes: `stm.mem32[stm.TAMP_NS + 0x100 + 4*i]`, two words written before, read back after |
| `RTC.wakeup(43200000)` (12 h) accepted | yes (cancelled with `wakeup(None)`) |
| USB drops ~1.1 s after `deepsleep()`, re-enumerates ~2 s after the wake; `ticks_ms()` ≈ 1.07 s when main.py starts | yes |
| `ml.Model()` loads a ROM model, exposes `input_shape/scale/zero_point`, `predict` | yes (`/rom/person_detect.tflite`) |
| `sensor.shutdown()` / `sensor.sleep()` exist; `network.WLAN.deinit()` exists | present, effect on sleep current unmeasured |
| user button `SW` = PF4 (pull-up), LEDs B1/G10/A7, `ONOFF` = PA2 | `SW` does **not** wake standby (2 × 60 s runs); `machine.lightsleep()` never returns and drops USB → standby + RTC only, button polled per wake |
| SD card | **no card fitted**: `/sdcard` absent, `pyb.SDCard` present |

Open, needs a hand or a meter (bench gates, §8): standby current, whether
`SW` (PF4) wakes standby (it is not a documented WKUP pin; `ONOFF` PA2 is
WKUP2), what the firmware does with `main.py` and USB mass storage when a
card is fitted, and RTC drift.

Persistence across standby (RAM is lost): per-wake counters in the TAMP
backup registers (32 × 32-bit, cleared only by full power loss), the motion
thumbnail and a per-wake log on the card, night history on `/flash`
(written only at night transitions), `boot_count.txt` only on cold boots.
Nothing on `/flash` is written per wake (NOR wear).

## 1. Layout

```
cameras/n6cam/
  PLAN.md  README.md  camera.toml              (power = wake_cycle, profile in [tuning])
  software/app/board.py                        board facts + sleep/wake/lum/thumb helpers
  software/app/ota_main.py, ota.py             loader: skips WiFi/NTP/listener on a deep-sleep wake
  software/app/secrets.py                      generated (dustygen; [hotspot] creds when capability hotspot)
  software/app/gate.tflite                     converted gate model, USB copy to /flash (not OTA)
  software/build/app.py                        bundle
  software/host/monitor.py                     reconnecting USB monitor (board re-enumerates every wake)
  software/host/bench_sleep.py                 bench gates: standby/RTC/backup regs/button/SD-boot/long wakeup
  software/host/convert_gate.sh                stedgeai conversion (bundled with OpenMV IDE, no install)
  tests/test_n6_app.py, tests/test_game.py     host pytest
runtime/micropython/
  night.py    night policy (pure: state dict in, sleep_s + events out; history median)
  rank.py     score, ranked drain order, crop box, judge decision (pure)
  gamespool.py  /sdcard/spool/<boot>/<seq>.{jpg,json} + /sdcard/debug/, scan/sort/drain/delete/reclaim/count
  persist.py  backup-register state (magic + fields), file fallback on hosts without `stm`
  led.py      the LED language (blocking short patterns; non-blocking blinker for searching)
  judge.py    ml.Model gate, fail-open, hard-fault guard (model_pending/model_bad markers), motion-centred crop
  contact.py  the contact sequence §5
  wakecycle.py  one wake of §4.1 + first-boot contact + rest (deep sleep); game_run()
  app.py      run(): if TUNING profile == game_lowpower and game_run exists → game_run(poll)
  uplink.py   http_get also records the reply's Date header (LAST_DATE) for the clock
```

RT1062's bundle order does not include the new modules, so its build is
unchanged; `app.py`'s dispatch guards on `'game_run' in globals()`.

## 2. Persistent state (persist.py)

Backup registers, word 0 = magic `0xD057` in the high half + layout version
in the low half; a bad magic means power loss → defaults. Fields (one
32-bit word each unless noted): `wake_n`, `seq`, `awake_ms` (since the last
recorded frame), `dark_n`, `night` (0/1), `night_start` (epoch, 2000-based),
`night_s_last`, `clock_state` (0 none / 1 est / 2 set), `last_ts` (epoch at
the last save, for `est`), `pending_n`, `contact_n`, `debug_n`, `crash_n`,
`flags` (bit0 thumb_valid, bit1 first_contact_done, bit2 fw_pending_seen).
`persist.load()` → dict, `persist.save(d)`. On CPython (tests) or when
`stm` is missing, a JSON file (`PERSIST_FILE`) with the same API.

Clock: STM32 RTC keeps running through standby, so after a deep-sleep wake
`clock_state` is whatever it was. After a cold boot: if the RTC year is
< 2021 → `none`; else if `clock_state` was `set` before the power loss it
stays `est` (the RTC runs from VBAT-less reset value, so in practice this
is `none`); an `est` restore from `last_ts` is applied when the RTC is
behind it.

## 3. The wake (wakecycle.py)

```
game_run(poll):
  st = persist.load(); cause = wake_cause()           # 'deep' | 'cold' | 'soft'
  boot_count: read /flash/boot_count.txt; increment only when cause != 'deep'
  fw_boot_check, cfg_init(TUNING)                     # as today
  night history: night.load() from /flash/night.json
  sd = gamespool.ready()                               # /sdcard/spool, /sdcard/debug created
  if not sd: LED fail pattern, log, sleep period_s (profile not applicable without a card)
  button held at boot (SW low) or cause == 'cold' and not flags.first_contact_done → contact.run(...)
  Sense: board_sensors() + lum (mean L of the VGA grayscale preview)
  Night: sleep_s, evt = night.step(nst, lum, now, CFG); if evt in (enter, probe): record nothing,
         save, rest(sleep_s)
  Watch: thumb = board.thumb(img) (80x50 GRAYSCALE); frac, bbox = board.thumb_diff(ref, thumb, l_thresh)
         (frac = 1.0 when no valid ref)
  Trigger: why = boot (no ref) | motion (frac ≥ diff_min_frac) | interval (wake_n % interval_n == 0)
           | heartbeat (awake_ms ≥ heartbeat_s*1000) | none
  Debug: if debug_frames: gamespool.write_debug(preview jpeg, meta why=watch, diff, gate)
  Capture: camera.capture() (HD RGB565 → JPEG q85 as today)
  Judge: only when why == motion and judge available: conf = gate.score(crop of the capture around bbox
         scaled from thumb coords); keep/audit per rank.decide(conf, CFG, seq); fail-open on any error
  Record: gamespool.write(boot_count, seq, jpg, meta) with meta = standard keys + score, clock, lum,
          det, night_s (morning frame); thumb saved as the new reference; awake_ms reset; LED capture blink
  Button poll at the end of the wake → contact
  Rest: save state (awake_ms += ticks), board.rest(period_s) → RTC wakeup + sensor.shutdown + deepsleep
```

The wake log: one line per wake appended to `/sdcard/wakelog.txt`
(`wake_n cause lum diff why kept score awake_ms sleep_s`), rotated at 1 MB.
The same line goes to the USB console.

## 4. Contact (contact.py)

Exactly §5 of the operation spec, with the LED language of §10:

1. LED searching (blinker ticked from the join wait loop); `WLAN` STA join
   to `secrets.WIFI_SSID/WIFI_PASS` for `hotspot_join_s`. Failure: LED
   fail (five fast blinks), return to the caller (live/night resumes).
2. `control_init()` after the join (the listener needs the netif up).
3. Clock: `http_get('/config/<device>')`'s Date header → `clock_skew_s`,
   RTC set, `clock_state = set`.
4. Announce telemetry `mode: 3` with `boot`, `batt_v`, `pending_files`,
   `pending_cold`, `clock_skew_s`, `contact_n`, `night`.
5. `fw_check(APP_VERSION)` (may reset), then `cfg_pull(TUNING)`; LED
   updated (three quick blinks) when `cfg` changed; `fw_mark_valid()` after
   the first accepted upload as today.
6. Drain: `gamespool.drain(idle=control_poll, cap=upload_cap)` in score
   order, delete on 2xx, stop after 5 consecutive failures; then debug
   frames up to `debug_max`. Telemetry every `telemetry_s`.
7. Serve: `control_poll()` loop until `contact_idle_s` with no request or
   `GET /live`; a setup session inside runs as today.
8. Leave: telemetry, `wlan.disconnect(); wlan.active(False)`, LED off,
   `contact_n += 1`, motion reference invalidated (next frame `why: boot`),
   reclaim to `spool_max_frames`.

## 5. Night (night.py, pure)

State: `{'night': 0/1, 'dark_n', 'start', 'hist': [..7]}`. `step(state, lum,
now, cfg)` → `(sleep_s, event)` with events `none`, `enter`, `probe`,
`exit`. Enter after `night_confirm_n` consecutive `lum < lum_night`; while
night: predicted = median of the last 3 lengths; with no history probe
every `night_probe_s`; else sleep `predicted − night_margin_s − elapsed`
(min `night_probe_s`), then probe every `night_probe_s`; exit on
`lum ≥ lum_day` on a probe: length appended (keep 7), `night_s` for the
morning frame. Identical semantics to `dc_night_step` in
`runtime/espidf/components/dusty_core/src/night.c`.

## 6. Storage and ranking (gamespool.py, rank.py)

`/sdcard/spool/<boot_count>/<seq:06d>.jpg` + `.json`, sidecar first, image
to `.tmp`, rename. `rank.score(why, diff, conf, sharp)`: `boot`/`heartbeat`
→ 2.0 + tiny; else `conf` if judged else `diff`, plus `sharp/1e4` as the
tiebreak. Drain reads every sidecar (`score`, `seq`, path) → sorted
desc → upload up to cap. `/sdcard/debug/<boot>/<wake_n>.jpg+.json` with
`why: watch`. Reclaim: when the spool count > `spool_max_frames`, delete
the lowest-numbered boot dirs' oldest files first. Names never use the
clock.

## 7. Judge (judge.py)

Model: the camlogger's `gate.tflite` (96×96×3 int8, animal probability)
converted with the OpenMV IDE's bundled `stedgeai` (`~/openmvide/share/
qtcreator/stedgeai/Utilities/linux/stedgeai`, no install) for `stm32n6`
with the profile the IDE uses; output copied to `/flash/gate.tflite` over
USB. No retraining. Hard-fault check: write `/flash/model_pending.txt`
before `ml.Model()`, remove after; at boot a leftover marker becomes
`/flash/model_bad.txt` and the gate stays open until a new model file
appears (size differs). Everything else fails open: no model, load error,
predict error → keep. Crop: bbox of the thumb diff (find_blobs on the
thresholded difference) scaled to the capture, square, padded 50 %,
clamped; full frame when the mask covers > 60 % of the frame.

## 8. Bench gates (record each in sarg)

1. **SD card fitted** (owner): does the firmware still run `/flash/main.py`
   and expose flash over USB, or does the card take over? Bench script
   prints `os.listdir('/')`, `/sdcard` free space, write/read/rename speed.
2. ~~Button wake from standby~~ done 2026-09-13: no, and light sleep is unusable; the button is polled per wake (hold up to `period_s`). Was: sleep 60 s, press `SW`; if
   no early wake, try `machine.lightsleep()` (STOP, RAM kept, any EXTI
   wakes) and measure its current; decide `SLEEP_MODE` in board.py.
3. **Standby current** with a meter in series with the pack, with and
   without `sensor.shutdown(True)` and `wlan.deinit()`.
4. **Hotspot join time** on the 2.4 GHz hotspot; **upload throughput** for
   a large drain through the phone.
5. **RTC drift**: `clock_skew_s` at each contact over two weeks.
6. **Gate load and timing**: `ml.Model` on the converted model, hard-fault
   guard, `predict` ms.
7. **Wake cost**: ms from main.py start to `deepsleep()` for a no-motion
   wake (target < 1.5 s; `preview_settle_ms` tuning).

## 9. Config keys (camera.toml [tuning])

Section 4.1 of the spec plus board keys: `profile`, `period_s`,
`interval_n`, `heartbeat_s`, `diff_min_frac`, `diff_l_thresh`, `gate_pct`,
`keep_labels`, `keep_all`, `audit_n`, `debug_frames`, `debug_max`,
`upload_cap`, `lum_night`, `lum_day`, `night_confirm_n`, `night_margin_s`,
`night_probe_s`, `hotspot_join_s`, `contact_idle_s`, `setup_secs`,
`telemetry_s`, `led_capture`, `spool_max_frames`, `preview_settle_ms`,
`capture_framesize`, `capture_settle_ms`, `wifi_linger_s` (monitor only).
`keep_labels` is a list: `config._coerce` gains list handling (str items).

## 10. dustygen

MicroPython path: WiFi from `[hotspot]` when `capabilities` include
`hotspot` (same helper as espidf), `--public` default for hotspot cameras,
`--lan` to force. Everything else unchanged.

## 11. Work packages

- **A** (sonnet): common modules night/rank/gamespool/persist/led/judge/
  contact/wakecycle + app.py dispatch + uplink Date + config list coercion
  + host tests `runtime/tests/test_game.py`.
- **B** (sonnet): openmv_n6 board.py, loader, camera.toml, README, tests,
  host tools (monitor, bench_sleep), dustygen, STATUS line.
- **C** (root): model conversion script + attempt, sarg lessons.
- Review (fable agent) of A+B against this plan and the spec; fixes at root.
- Bench: card, button, current, flash (ask first), hotspot.

## 12. Out of scope

XIAO changes, mesh, model retraining, sensorhub changes (README lists
them), the second N6, the speedcam.
