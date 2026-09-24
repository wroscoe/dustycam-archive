# dustyphone — development status

Status of the phone-app + BLE work for dustycam cameras. Plan:
`docs/phone_app_plan.md` (Fable, 2026-09-14, revised 2026-09-15 for sequential
radios). This file is the running truth: what is **proven on hardware**, what is
**built but unproven**, what is **open**. Updated 2026-09-15 night (real firmware + SD card bench pass; P1.1b closed).

Hardware used: XIAO ESP32S3 Sense `xiaocam1` on USB
(`/dev/serial/by-id/usb-Espressif_USB_JTAG_serial_debug_unit_1C:DB:D4:76:AF:3C-if00`;
`ttyACM0` is the Heltec mesh node — leave it), Pixel 6 / Android 15 on adb,
phone hotspot `sweetpotato` 2.4 GHz. A 64 GB SD card went in for the evening pass
(spool/thumb now proven on the real firmware).

## What exists

| piece | where | state |
|---|---|---|
| Plan | `docs/phone_app_plan.md` | decided; §7 questions answered by default (see Open) |
| BLE component | `runtime/espidf/components/dusty_ble/` | all §2 ops implemented; P0 subset proven, P1 ops partly proven |
| Shared components | `dusty_config` (NVS identity, `cfg_src/cfg_base`), `dusty_uplink` (full Wi-Fi deinit, `post_json`, `wifi_scan`), `dusty_control` (`POST /ble`, UDP beacon, `/spool`, `/thumb`), `dusty_spool` (sdspi mount fix) | built; partly proven |
| Bench firmware | `runtime/espidf/bench/ble_spike/` | proven (replaced on the XIAO by the real firmware this evening); README "Measured" has the numbers |
| Real camera firmware | `cameras/xiaocam1/software/app/` (`radio.c`, `contact_run(mode)`, config push, BLE enabled) | **on the XIAO now**, proven this evening: cold boot opens the window; owner-key auth; `time.set`; Shoot → `spool/9/000000.jpg` on the card → `spool.list` → `thumb` over BLE (5.7 KB, 32 KB/s); View-over-Wi-Fi handoff → hotspot join → beacon → `/status 200` (`contact_mode:view`) → `POST /ble` → re-linked. Timer wakes don't advertise; deep sleep drops the USB port (expected) |
| dustygen | `tools/dustycli/dusty.py` (`tuning_schema.h`, `--blank`, `--phone-json`, `[ble] key`, `--verify-blank`) | done, 42 tests; writing secrets now deletes the stale `sdkconfig` (the review's blank-image blocker) |
| sensorhub | `ingest` `POST /config/<id>` (200/409/400) + `blobgate` proxy + blobgate `_drain` hang fix | done, 51 tests; **deployed 2026-09-15 night** (ingest + blobgate rebuilt, serving the real camera) |
| Android app | `apps/dustyphone/` (Java, no Gradle, docker `dustybuild`, `make build/install`) | on the Pixel with the **owner profile imported** (`~/.dusty/dusty_phone.json` via menu → Provision → Import); scan/connect/auth/status/preview/settings/provision/handoff/cycle; request-queue timeout; `bye live/window` handled |
| Docs | `docs/camera_standard.md` §5/§6, `docs/camera_operation.md` §1, `STATUS.md` | updated |
| sarg lessons | `sargbench2/esp32-s3-nimble-notifications-over-244-b-payload`, `…nimble-stop-deinit`, `android-ble-rescan-after-5-startscan-in-30`, `esp32-camera-preview-colours-wrong…`, `esp-vfs-fat-sdmmc-mount-with-an-sdspi` | recorded (private) |

Nothing is committed. `runtime/espidf/`, `cameras/xiaocam1/software/app/`,
`apps/` and the sensorhub `blobgate/` + `ingest/settings.py` are untracked
alongside older uncommitted work — commit deliberately, by path.

## Gate table

| gate | requirement | result | evidence |
|---|---|---|---|
| P0.1a RAM | ≥ 80 KB internal free, NimBLE up + camera initialised | **PASS 144 KB** | serial `radio: state=BLE+CAM` |
| P0.1a transfer | thumb/preview ≥ 10 KB/s, 10/10 CRC-ok, 20 init/deinit cycles | **PASS** 64–87 KB/s, 40+/40+, heap byte-identical | logcat `KB/s`, serial `send_data` |
| P0.1b handoff | BLE stop → controller IDLE → hotspot → HTTP → `POST /ble` → re-advertise ≤ 3 s; 10 cycles, heap flat ±2 KB | **PASS** IDLE every time, re-adv 12 ms, 21 board cycles drift ≤ 300 B, Cycle×10 10/10 twice | bench README tables |
| P1.1a cfg.set persists | `cfg.set` → cfg N+1 → survives sleep/wake | **PASS** (spike): `period_s 30→45`, cfg 0→1, intact after hard reset | logcat `cfg.get` |
| P1.1b config push | next contact pushes; device page shows N+1; server-side edit first → 409 → server wins | **PASS** both halves, real fw + deployed sensorhub | 409: `config push xiaocam1: base=0 current=1 -> 409`, camera then ran the server's `cfg 1, period_s 30`. Accept (21:13, hands-off, no phone linked): cold boot → 120 s window expires → self-contact → hotspot → `GET /config 200` → telemetry 16 vars → `config push xiaocam1: base=1 current=1 -> accepted cfg=2`; server now `cfg 2, period_s 45` |
| P1.2 field provisioning | NVS-erased board + `--blank` image → `dc-new-…` → `prov.set` → restarts as `xiaocam1`, joins, drains | **not run** — both review blockers fixed (`--blank` now blank + verifiable; `first_contact` opens a window after restart); recipe in Open item 4 | — |
| XIAO gate 1 BOOT wake | a GPIO0 press in deep sleep runs the app (`ext1`), not ROM download mode | **PASS 2026-09-16 ~09:58** (after the crash-loop fix; the 2026-09-15 attempt was invalid — the board never slept that night) | serial (non-resetting reader): timer wakes `wake_n=2…11 cause=timer cold=0`, then the press: `wake_n=12 cause=button cold=0`. `cause=button` = `esp_sleep_get_wakeup_cause()==EXT1`, only set on a deep-sleep wake; `cold=0` and the continuing `wake_n` = RTC state intact, so not a reset; the app ran, so not download mode. An external field button can be wired in parallel with BOOT, no firmware change |
| P1.3 button-only contact | no phone: button alone still contacts after `ble_adv_s` | **PASS twice** | 2026-09-16 on the fixed firmware, serial-verified: BOOT press in deep sleep (`wake_n=12 cause=button cold=0`) → 120 s window, no phone → `contact done: sent=1 skipped=0 failed=0 pending=0 contact_n=3` at 262.8 s. Earlier pass 2026-09-15 21:38 (server logs only, on the crash-looping image) |
| P1.4 drain throughput | ≥ 200-frame drain with trimmed Wi-Fi buffers, ≤ 30 % slower | **not run** — card + firmware ready; needs sensorhub deploy and a Contact | — |
| SD spool + thumb (real fw) | shoot to card, list, thumbnail over BLE | **PASS** `spool/9/000000.jpg`, 5.7 KB thumb at 32 KB/s | logcat + serial |
| Handoff on real fw | wifi.up → hotspot → beacon → `/status` → `POST /ble` → BLE | **PASS** (once) | logcat |
| `wifi.scan` beside BLE | link survives; internal cost | link survived, 8 APs in 6.7 s, −9 KB internal after (one-time or per-scan: unknown) | serial `ble_spike: wifi_scan` |

## FIXED (2026-09-16): the camera was crash-looping every ~2 minutes (found 2026-09-15 21:45)

**Outcome, 2026-09-16 09:39–09:52 (instrumented build, `sdkconfig.crashdebug`):**
with `CONFIG_ESP_MAIN_TASK_STACK_SIZE=20480` the first cold cycle drained
**33 of 33** backlogged frames (`contact done: sent=33 failed=0 contact_n=1` —
the first contact that ever completed; every earlier telemetry row said
`contact_n 0`), reached `sleep_s=45`, and later timer wakes came up warm
(`wake_n=2 cause=timer cold=0`, awake 2.3 s). Every internal-heap integrity
check passed. Measured main-stack use: 10.5 KB after the TLS config GET,
**14.3 KB right after `fopen()` in the upload** and a **15.7 KB peak** during
the upload — so the old 12 288 B stack overflowed by ~3.4 KB on every contact
with something to send. The heap dump shows the esp_timer TCB (352 B at
`0x3fcc33a8`) ending 116 B below the main stack's block (`0x3fcc357c`), so the
overflow ran straight across it: bug B was the direct cause, and Fable's
hypothesis A (the 22 KB region) does not apply to this layout. The TCB
store-watchpoint's "armed" log line was lost in the console after the heap dump
(sarg `sargbench1/the-esp32-s3-usb-serial-jtag-console-goes`), so it cannot be
confirmed that it was armed; it never fired.

**Measurement caveat found on the way:** opening the port with pyserial —
even with `dtr=False, rts=False` set before `open()` — **resets the ESP32-S3**
(DTR drops before RTS; DTR=0/RTS=1 is the USB-Serial-JTAG reset). Both of the
evening's captures, and the first "cold timer wake" this morning, were caused
by the logger itself. Use a raw `os.open()` reader (sarg
`sargbench2/esp32-s3-usb-serial-jtag-opening-the-port`; script kept as
`cameras/xiaocam1/logs/safecap.py`). The crash loop itself predates any
capture (telemetry, 21:13–21:18), and the 21:48 crash still happened 133 s
after the reader's reset, so the diagnosis stands. The older note above that
"a serial reader attached stalls the Wi-Fi join" may be this same reset and is
worth re-testing with the raw reader.

The rest of the fix list landed the same morning and the XIAO now runs the
**field image** (no debug overlay): stack locals moved to PSRAM, esp_timer
stack 4 KB with the advertising switch moved to the NimBLE host task, SPI bus
ownership tracked, light heap poisoning + `heap_guard()` at phase boundaries
(aborts → `crash_n`), and `crash_n` / `reset_reason` in `/status` and
telemetry. Verified: full contact, sleep, 31 warm timer wakes in 30 min.
Details and the RAM cost in `docs/crash_experiment_2026-09-16.md`.

### Original write-up (2026-09-15)

`readings` in `/hd2/sensorhub/sensorhub.db` (telemetry posts one row per
contact) shows every contact this evening reporting `uptime_s` 125-127 and
`boot_count` one higher than the last:

```
21:13:26  boot_count 7    uptime_s 125
21:15:43  boot_count 8    uptime_s 125
21:17:55  boot_count 9    uptime_s 125
21:35:54  boot_count 11   uptime_s 125
21:38:07  boot_count 12   uptime_s 125
21:40:24  boot_count 13   uptime_s 127
```

`boot_count` increments **only on a cold boot** (`app_state.c:55`, reached when
the RTC magic/CRC check fails), so the board is not sleeping and waking — it is
resetting, cold, about 125 s after each boot: boot → 120 s radio window →
contact → reset → repeat. It has been doing this since at least 20:41
(`boot_count` 4).

Two consequences, both of which quietly invalidated tonight's assumptions:

- **Nothing tested tonight ever entered deep sleep**, which is why the USB port
  kept reappearing and why XIAO gate 1 could not be tested: there was no sleep
  to wake from.
- **The 21:22-21:27 Recovery episode is a symptom, not a separate puzzle.**
  `GET /firmware/…/version` once a minute with no `/config` and no `/telemetry`
  is `recovery_loop()` (`main.c:141-152`), and the only way in besides a held
  button is three consecutive `ESP_RST_PANIC` boots (`main.c:157-164`). Three
  crashing cycles in a row is exactly what the contact timestamps show.

Mechanism for the cold boot is consistent with a crash: `app_state_save()`
(which recomputes the CRC over the mutated RTC state) is only called at
`main.c:565`, immediately before `esp_deep_sleep_start()`. Any reset before
that line leaves RTC state whose CRC no longer matches, so the next boot reads
as cold and bumps `boot_count`. In other words the board never reaches its
sleep path.

### The crash, caught 2026-09-15 21:48 (full log: `cameras/xiaocam1/logs/crash-2026-09-15-2148.log`)

```
assert failed: vTaskGenericNotifyGiveFromISR tasks.c:6213
    (( ( &( pxTCB->xEventListItem ) )->pxContainer ) == ((void *)0))
vTaskGenericNotifyGiveFromISR  tasks.c:6213
timer_alarm_handler            esp_timer.c:487
timer_alarm_isr                esp_timer_impl_systimer.c:93
_xt_lowint1                    (ISR over the idle task)
rst:0xc (RTC_SW_CPU_RST)
```

The esp_timer ISR notified the esp_timer task and FreeRTOS asserted that the
target TCB is sitting on an event list — the signature of a **corrupted or
freed TCB**, not of an ordinary logic bug. No app frame appears in the
backtrace because the fault is in an ISR over the idle task; the damage was
done earlier by something else.

**Diagnosis (Fable, 2026-09-16; frame sizes re-checked against the ELF).**
My first reading of the timeline was wrong. `count_pending()` (`contact.c:885`)
is mount #1 and its `sd_give()` silently unmounts; **mount #2 is the drain's
`sd_take()` (`contact.c:1055`)**. `drain_tier()` always logs `drain …: uploaded`
(`contact.c:771`) and never did, so the crash is at the *start* of the drain,
at the first upload — the end-of-contact block (`dusty_control_stop`,
`wifi_off`, reclaim) never ran. The `spi_bus already initialized` line is the
expected result of `unmount` never freeing the bus.

Two things are true at that instant:

- **B — certain: the main task's stack overflows at the first upload.** Frame
  sizes from the ELF's `entry` instructions: `main_task` 48 + `app_main` 2608 +
  `radio_window_run` 608 + `contact_run` 32 + `contact_run_contact` 3776 +
  `drain_tier` 1312 + `dusty_uplink_post_file` 4336 (its `buf[4096]`) =
  **12 720 B on entry, against `CONFIG_ESP_MAIN_TASK_STACK_SIZE=12288`** — before
  `stat`/`fopen`/DNS/TLS add another 1.5–5 KB. The scan path and the telemetry
  path fit (barely), which is why everything before the drain worked. The
  canary misses it because the spill is sparse under a mostly unwritten 4 KB
  local.
- **A — most likely for this particular assert: the esp_timer TCB's first ~44 B
  are overwritten, tail intact.** That TCB is one of the first blocks in the
  22 KB internal region at `0x3fce9710` (the one that hit `free 4`), and every
  mount, `opendir`, `fopen` and sector bounce churns small blocks there. One
  damaged TLSF header makes a later `malloc` hand out memory overlapping the
  TCB, and its new owner writes over it. Variant A′: a local overflow on the
  esp_timer task itself (`adv_interval_timer_cb`, `dusty_ble.c:1215-1232`,
  calls `ble_gap_adv_stop/start` + a log from that 3584 B stack). B is not the
  direct writer of this TCB by layout, but it must be fixed regardless.

Fixes, smallest first: main stack → 20 KB and move the big locals
(`post_file`'s 4 KB buffer, `contact_run_contact`'s 1 KB buffers,
`drain_tier`'s `meta[1024]`, `app_main`'s 2.6 KB frame) off the stack; esp_timer
stack → 4–6 KB and move `adv_interval_timer_cb`'s work to the BLE host task;
`dusty_spool_unmount()` frees the bus it initialised (B13); heap poisoning
light + integrity checks at phase boundaries feeding `crash_n`. The
experiment build that separates A / A′ / B in one flash (comprehensive
poisoning, end-of-stack watchpoint, `heap_caps_check_integrity_all()` at each
phase, a store-watchpoint on the esp_timer TCB's `xEventListItem.pxContainer`)
is in `docs/crash_experiment_2026-09-16.md`.

Current state: the board is parked in **Recovery** (`crash_n=4`), which never
sleeps, so the crash loop has stopped for now — and so has any further
evidence-gathering, since a clean wake is what clears `crash_n`.

Also worth doing regardless: `crash_n`, `reset_reason` and a `recovery` flag
belong in `/status` and in the telemetry vars, plus a `recovery` event to
sensorhub. A board that stops sleeping is invisible to both the phone and the
server today, and it burns the battery the whole design is built around.

## Proven facts worth remembering

- **Sequential radios work on IDF 5.5**: `nimble_port_stop/deinit` → `esp_bt_controller_get_status()==IDLE`; full `esp_wifi` deinit; NimBLE re-init advertises 12 ms after Wi-Fi off. Internal free: boot 210 KB, BLE 166 KB (first) / 156 KB (after any Wi-Fi phase, one-time ≈ 10 KB), BLE+camera 144 KB, Wi-Fi 144 KB, Wi-Fi+httpd 134 KB.
- **Notifications must be ≤ 244 B of value**: 514 B notifies (MTU 517) never reached the Pixel 6 although NimBLE returned rc=0; 244 B arrive 100 % at 65–85 KB/s. Frames are capped at MTU 247 on both sides.
- **Discovery after the handoff is a UDP beacon** (`:8267`, once a second while the control plane is up); the app never asks for an IP. Handoff tap → `/status 200` in ~2 s.
- **Android scan throttle**: > 5 `startScan` in 30 s silently yields nothing; post-`/ble` reconnect is a direct `connectGatt` (3–5 s), scan only as fallback.
- The phone can be a Wi-Fi client on the home LAN *and* a hotspot; HTTP must not be bound to the client network (tether subnet is only reachable unbound).
- `jpg2rgb565` is little-endian, `fmt2jpg` reads big-endian → swap before re-encoding; SPI SD cards need `esp_vfs_fat_sdspi_mount`.

### Fixed in the evening bench pass (real firmware + card)
- `main.c` never called `dusty_spool_set_pins()` → SD pins were −1 → `sdmmc_card_init 0x107` all day (the spike sets them). Fixed.
- `dusty_spool_mount()` now holds the SD bus mutex across card init (the LED shares GPIO21 with CS and toggles whenever the mutex is free).
- `shoot` on the BLE image worker panicked once the card mounted: `esp_task_stack_is_sane_cache_disabled()` — NVS write from a PSRAM stack. The worker's stack is internal now (+12 KB internal).
- Real app: `CONFIG_LOG_DEFAULT_LEVEL_WARN` + app tags at INFO — with a serial reader attached and INFO for everything, the USB-Serial-JTAG console wedged during Wi-Fi bring-up and the hotspot join timed out at 90 s (proven: same firmware joins in ~2 s with the port closed).
- App: the Provision menu always opens (owner-profile import works without an unprovisioned camera in view).
- Cosmetic: `spi: spi_bus_initialize: SPI bus already initialized` E-line on every lazy remount (harmless; free the bus on unmount or track it).

## Open items (ranked)

1. **Reopen the real firmware's window at the desk when needed**: press BOOT (this *is* XIAO gate 1 — BOOT-button wake from deep sleep, untested) or unplug/replug the XIAO (cold boot → 120 s window; a linked phone extends it). Timer wakes never advertise, by design, and deep sleep drops the USB port.
2. ~~Deploy sensorhub / run P1.1b~~ — **done 2026-09-15 night**: `ingest` + `blobgate` rebuilt and up, both P1.1b halves proven (see the gate table). Note the accept path needed the phone hotspot's **"Turn off hotspot automatically" → OFF** (`soft_ap_timeout_enabled=0`); Android's 10-minute no-client shutdown killed two earlier attempts, and a self-contact with no hotspot just sleeps again with the edit still pending.
3. ~~Insert an SD card~~ — **done**: 64 GB card in; shoot/spool.list/thumb proven on the real firmware. P1.4 (drain throughput with the trimmed Wi-Fi buffers) still needs a ≥ 200-frame spool.
4. **P1.2 field provisioning**: `python3 tools/dustycli/dusty.py cameras/xiaocam1 --blank` → `make build` → `python3 tools/dustycli/dusty.py cameras/xiaocam1 --verify-blank` → `esptool erase-region 0xd000 0x6000` (NVS) → flash → expect `dc-new-<mac4>` → app row → Provision → restarts as `dc-xiaocam1` and contacts (`first_contact` NVS flag).
5. `wifi.scan` beside BLE: −9 KB internal after the first scan; measure a second scan on the same boot (one-time vs per-scan). `ble_req` stack is 10 KB now; high-water marks are logged at `dusty_ble_stop`.
6. `ble_adv_s` as a real tuning key (dustygen + `dc_cfg_t`); plan text: `/status.mode` is `contact_mode`.
7. P2 app polish (frames grid, preview view), P3 Wi-Fi viewing (MJPEG, full-res, mDNS, LOHS experiment), P4 field sessions + standard §9/§12 rows.
8. Plan §7 questions were answered by default — confirm: one `ble_key` per owner; blank-image + NVS identity accepted; manual hotspot primary; full-res over BLE = late fallback; `cfg.set` during drain → busy; `POST /config` in P1.
9. Commit: everything above is uncommitted, mixed with older untracked work in `runtime/espidf/` and `cameras/xiaocam1/software/app/` — commit by path.

### Fixed today from the P1 review (Opus; Fable hit its usage limit)
- accepted config push no longer reverted by the stale pull; `refresh` won't clobber a pending BLE edit; GET /config 404 = "no config yet"
- `prov.set`/`reboot` no longer `esp_restart` inside the BLE task: radio.c unwinds, `first_contact` NVS flag makes the next boot open a window; cold boot opens a window (it didn't before)
- SD lazy-mounted for thumb/frame/spool.list/shoot inside the button window; camera lazy (`cam_ensure/finish`, idempotent `xc_cam_init`); a linked phone extends the window; `POST /ble` gets ≥ 30 s BLE grace; `wifi.up` ssid/pass override reaches `contact_run`; `wifi.scan` off the small task; 503 on `POST /ble` during a drain; live `win_left_s`/`ble_back_in_s`; real `cfg` in `info`; schema nested under `schema`; adv name truncation; img-op generation counter; buffer sizes; dead `CONFIG_DUSTY_BLE` removed
- dustygen deletes stale `sdkconfig` on every secrets write; `--verify-blank`
- blobgate `_drain` double-read (regression test proves the hang)
- app: cmd writes capped at 247 B; empty str/list fields ignored; `keep_labels` limits; request timeout (queue can't wedge); `bye live/window` not treated as loss; menu always reaches the profile import

## How to drive the bench

```sh
# firmware (Docker, no host toolchain)
cd runtime/espidf/bench/ble_spike && make build   # or cameras/xiaocam1/software/app
esptool --port /dev/serial/by-id/usb-Espressif_USB_JTAG_serial_debug_unit_1C:DB:D4:76:AF:3C-if00 \
  --baud 921600 write-flash 0x20000 build/ble_spike.bin   # stop any serial logger first
# app
cd apps/dustyphone && make build && make install && make run && make log
# phone must be unlocked; the button bar can be driven with uiautomator dump + input tap
```
