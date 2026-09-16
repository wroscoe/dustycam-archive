# ble_spike

P0 bench spike for dustyphone (`docs/phone_app_plan.md` §6 P0). Throwaway
`main/`, real components: `dusty_ble` (this repo's new NimBLE peripheral),
`dusty_core`, `dusty_uplink`, `dusty_spool`, `dusty_control`. Targets the
same physical board as `cameras/xiao_pantilt` (Seeed XIAO ESP32S3 Sense);
`main/board.h`, `camera.h`, `camera.c` are copied verbatim from that app
(see those files' header comments) since it's the same hardware.

## What this proves

Straight from `docs/phone_app_plan.md` §6, verbatim:

**P0.1a** BLE + lazy camera: internal free ≥ 80 KB with NimBLE up and the
camera initialised; `thumb` 10/10 crc-ok at ≥ 10 KB/s (log KB/s);
`preview` init/capture/deinit 20x with no SCCB hang.

**P0.1b** handoff: BLE session → `wifi.up` → `esp_bt_controller_get_status()
==IDLE`, hotspot joined, `/status` answers over the phone's Wi-Fi,
`POST /ble` → Wi-Fi off, re-advertising within 3 s, app reconnects by
address; **10 cycles without a reboot or leak** — internal free per state
per cycle flat within ±2 KB. The spike prints the table `state |
internal_free | largest_block` for SLEEP-side, BLE idle, BLE+camera, WIFI,
WIFI+TLS(+camera) and it goes in this README + sarg. 3 walk-away
disconnects each recover by re-advertise + rescan.

This spike does NOT prove: the phone app side (a separate P0 app spike per
§6), `cfg.*`/`prov.*`/`wifi.scan` (P1), or WIFI+TLS (the spike's WIFI
phase has no server contact, so there is no TLS+camera state to measure --
that number comes from the real `xiao_pantilt` app instead).

## Deviations from the plan text (and why)

- No button, no `dusty_led`: the real app's LED/SD-CS pin-sharing dance
  isn't exercised here. The SD card is mounted once at boot and stays
  mounted for the whole run.
- No `dusty_config`/`dusty_ident`: `ble_key` comes straight from
  `CONFIG_DUSTY_BLE_KEY` (`main/Kconfig.projbuild`), not NVS identity.
  `cfg.*`, `prov.*`, `wifi.scan` all answer `err:"unsupported"`
  unconditionally, per the task scope for P0.
- A BLE window that ends with no link and no handoff goes straight to
  `done` (deep sleep) rather than falling back to a button-less contact
  the way the real camera's `radio_window_run` does -- P0 only exercises
  the phone-driven handoff.
- `preview`/camera-failure errors use `err:"busy"` (no closer code exists
  in the §2 error list, which has no "camera" entry); `thumb`/`frame`
  file-not-found uses `err:"nofile"`.
- `back_in_s` in the handoff reply is a fixed placeholder
  (`DUSTY_BLE_HANDOFF_BACK_S` = 60 s in `dusty_ble.c`) until P1's
  `dusty_config` provides `hotspot_join_s` etc.

### Bench-review fixes (first real-hardware pass)

A first flash surfaced several issues fixed in `dusty_ble.c`/`dusty_uplink.c`/
this project's sdkconfig, worth knowing about before the next bench session:
- `notify_sink()` now retries on `BLE_HS_ENOMEM` (up to ~2 s per fragment)
  instead of aborting a thumb/frame transfer on the first transient
  allocation failure -- a real transfer pushes fragments faster than the
  link drains them, so this was hit almost immediately. Bumped
  `CONFIG_BT_NIMBLE_MSYS_1_BLOCK_COUNT` 8->16 alongside it (PSRAM-backed,
  cheap). `handle_thumb`/`handle_frame`/`handle_preview` now check
  `dusty_ble_send_data()`'s return and answer `err:"busy"` on the rsp
  channel instead of leaving the app waiting on that id forever.
- `handle_handoff()`/`handle_live()` now call the hook (which sets the
  bench's flag `main.c` polls) LAST, after the reply/bye/flush/terminate
  sequence, not first -- calling it first let `main.c` call
  `dusty_ble_stop()` while a notify could still be in flight.
- `main.c`'s `radio_log_state()` calls were reordered to log the state
  AFTER it's actually true (post `xc_cam_init()`, post `dusty_ble_start()`
  settling, post a successful Wi-Fi join, post `dusty_control_start()`),
  not at the moment the transition is merely requested.
- `CONFIG_ESP_COEX_SW_COEXIST_ENABLE` is now explicit `n` (IDF 5.5 defaults
  it to `y` once both BT and Wi-Fi are enabled, contrary to decision 9);
  `CONFIG_SPIRAM_ALLOW_STACK_EXTERNAL_MEMORY` is renamed to
  `CONFIG_FREERTOS_TASK_CREATE_ALLOW_EXT_MEM` (the code checks both, new
  name first); a bogus `CONFIG_MBEDTLS_DYNAMIC_FREE_PEER_CERT` line
  (unknown symbol, silently ignored) was dropped;
  `CONFIG_BT_NIMBLE_HOST_TASK_STACK_SIZE` raised 4096->5120.
- `dusty_ble_stop()`/`dusty_ble_start()` now `esp_restart()` if
  `nimble_port_stop()`/`nimble_port_init()` fail -- leaving the radio in a
  half-torn-down state would otherwise fail every later attempt silently.
- `dusty_uplink_wifi_off()` now unregisters its Wi-Fi/IP event handlers
  BEFORE calling `esp_wifi_disconnect()` (that call fires a DISCONNECTED
  event, and the handler used to answer it with `esp_wifi_connect()` mid-
  teardown).
- `run_img_op()` (preview/thumb/frame/shoot) has a 15 s timeout -> `err:
  "busy"` instead of blocking forever on a wedged camera; a second op
  while one is already in flight also gets an immediate `busy` instead of
  clobbering the single pending-request slot.
- Added `last_ip` to `dusty_ble_hooks_t`: a side-effect-free query the
  handoff reply's `expect_ip` now uses (real IP from the previous WIFI
  phase on cycle 2+, instead of always `""`).
- SD: `dusty_spool_mount()` now goes through `esp_vfs_fat_sdspi_mount`
  (the sdmmc variant returned `INVALID_STATE` on the real board -- see
  `dusty_spool.c`); with no card inserted the spike logs one INFO line and
  keeps going (`spool.list` answers an empty list, `shoot` a no-op,
  `thumb`/`frame` `err:"nofile"`).

## Build

No network at configure time: `main/idf_component.yml`, `dependencies.lock`
and `managed_components/` are symlinked from
`cameras/xiao_pantilt/software/app/` (verified to resolve correctly
through the Docker bind mount -- the whole repo root is mounted, so a
relative symlink across the two project directories works exactly like it
would on the host). If a host or CI environment can't traverse symlinks
into the mount, fall back to copying those three paths instead.

```sh
cd cameras/common/espidf/bench/ble_spike
make build
```

First build takes several minutes (the Docker layer already has the IDF
toolchain, but component registration + the vendored `managed_components/`
still need a full configure+compile pass). Run in the background if your
shell has a short timeout.

`make size` runs `idf.py size` against the last build for the flash
breakdown.

## Flash

**Not run automatically.** `make flash` only prints the command; the root
session flashes by hand:

```sh
esptool --port /dev/serial/by-id/usb-Espressif_USB_JTAG_serial_debug_unit_1C:DB:D4:76:AF:3C-if00 \
  --baud 921600 write-flash \
  0x0     build/bootloader/bootloader.bin \
  0xc000  build/partition_table/partition-table.bin \
  0x13000 build/ota_data_initial.bin \
  0x20000 build/ble_spike.bin
```

Adjust `PORT` (`make flash PORT=/dev/ttyACM1`, say) if the by-id path
above doesn't match this bench's cable.

`sdkconfig.secrets` is NOT in this directory (gitignored, camera-specific).
The build points `-DSDKCONFIG_DEFAULTS` at
`cameras/xiao_pantilt/software/app/sdkconfig.secrets` directly (see
`Makefile`) so the WIFI phase has a real hotspot SSID/password to join.
Confirm that file exists and has real (not placeholder) `CONFIG_DUSTY_WIFI_SSID`
/ `CONFIG_DUSTY_WIFI_PASS` values before a bench session that needs the
WIFI phase to actually join something.

## Monitor

Reuses the xiao app's serial console tool (same USB-Serial-JTAG console):

```sh
python3 ../../../../xiao_pantilt/software/host/monitor.py /dev/serial/by-id/usb-Espressif_USB_JTAG_serial_debug_unit_1C:DB:D4:76:AF:3C-if00
```

or `make monitor` (uses the Makefile's `PORT`).

Every radio state transition logs one line at INFO on the `radio` tag
(re-enabled at boot despite `CONFIG_LOG_DEFAULT_LEVEL_WARN`), immediately
followed by `heap_caps_print_heap_info(MALLOC_CAP_INTERNAL)`:

```
I (12345) radio: state=BLE internal_free=123456 largest=65536 cycle=0
I (12346) radio: ...heap_caps_print_heap_info table...
```

`esp_bt_controller_get_status()` is logged by `dusty_ble_stop()` itself
(component `dusty_ble`, not this bench) after every stop, e.g.:

```
I (23456) dusty_ble: stopped; esp_bt_controller_get_status()=0 (IDLE)
```

## Measured — 2026-09-15, XIAO ESP32S3 Sense, Pixel 6 (Android 15)

Build: this tree (NimBLE host heap in PSRAM, MSYS_1 16 blocks, coex off,
Wi-Fi static RX 4 / dynamic 8, AMPDU off, mbedtls dynamic buffers). Phone
hotspot `sweetpotato`, 2.4 GHz. Antenna on. No SD card inserted
(`sdmmc_card_init 0x107`), so `thumb`/`spool.list` answered empty.

### Internal heap per state (bytes, `heap_caps_get_free_size(MALLOC_CAP_INTERNAL)`)

| state | internal_free | largest_block | note |
|---|---|---|---|
| SLEEP (boot, no radio) | 209,991–210,131 | 118,784 | |
| BLE advertising, first init | 166,439–166,571 | 94,208 | NimBLE ≈ 43 KB |
| BLE + camera (UXGA fb ×2, PSRAM) | 143,959–144,199 | 69,632 | camera ≈ 22 KB internal |
| BLE after camera deinit | 165,987–166,211 | 90,112 | returns fully |
| BLE after `dusty_ble_stop` (before any Wi-Fi) | 202,379 | 90,112 | ≈ 7.6 KB kept by the first BT init |
| WIFI joined | 143,827–144,415 | 65,536–69,632 | |
| WIFI + httpd + beacon | 134,007–134,303 | 61,440–65,536 | |
| BLE advertising, after ≥1 Wi-Fi phase | 155,967–156,563 | 65,536–69,632 | one-time ≈ 10 KB kept by lwIP/netif/PHY |

### P0.1a — BLE + lazy camera: PASS

- `preview` (lazy `xc_cam_init` → capture → 1/8 decode → JPEG → deinit): 12/12 then
  30+ more, every transfer CRC-clean, **64–87 KB/s** at 244 B per notification
  (MTU cap 247), 4.5–17 KB per image, ~40–220 ms on the air; camera
  init→deinit 391–430 ms; no SCCB hang; heap byte-identical across all cycles.
- With 514 B notifications (MTU 517) **every transfer failed**: NimBLE reported
  rc=0 for all fragments, the phone received only the final short one. See
  the sarg lesson `esp32-s3-nimble-notifications-over-244-b-payload`.

### P0.1b — handoff round trips: PASS

- `wifi.up` → reply → `bye` → `ble_gap_terminate` → `nimble_port_deinit` →
  controller **IDLE** (every time) → hotspot joined in 1.7 s → httpd + beacon →
  phone finds the camera from the UDP beacon ≈ 1.9 s after the tap →
  `/status` 200 in 30 ms. `POST /ble` → Wi-Fi off in ~0.4 s → advertising
  12 ms later → phone reconnected + authed in 2.1 s by hand.
- **Cycle ×10 (app-driven, hands-free): 10/10 twice** — ~2.0 s to Wi-Fi,
  3.2–4.9 s back to BLE. The board did 21 round trips on one boot with no
  reboot, no error/warn lines, and per-state internal_free drift ≤ 300 B
  (gate: ±2 KB).

| cycle (board count) | BLE idle | WIFI | WIFI+HTTP |
|---|---|---|---|
| 1 | 156,247 | 144,095 | 134,231 |
| 10 | 156,215 | 144,095 | 134,267 |
| 11 | 156,251 | 143,979 | 134,107 |
| 15 | 156,011 | 143,827 | 134,031 |
| 20 | 155,991 | 143,859 | 134,027 |
| 21 | 156,007 | — | — |

### Bugs found on the bench (all fixed in this tree)

1. `dusty_spool` used `esp_vfs_fat_sdmmc_mount` for an SPI card → 0x103; now `esp_vfs_fat_sdspi_mount`.
2. 514 B notifications lost (above); frames capped at 244 B payload.
3. Preview colours wrong: `jpg2rgb565` is little-endian, `fmt2jpg` reads big-endian; swap before encoding.
4. Wi-Fi idle timer measured from `dusty_control_last_request_us()` (0 / stale) → phase ended instantly once uptime > idle; origin is now max(last request, phase start).
5. App: `requestNetwork(TRANSPORT_WIFI)` bound HTTP to the home LAN while tethering → unreachable; now unbound unless a network's link prefix covers the target.
6. App: Android suppresses scan results after 5 `startScan` in 30 s → post-`/ble` reconnect is now a direct `connectGatt`, scan only as fallback.
7. App: IP prompt removed — the camera broadcasts a UDP beacon (`:8267`) while its control plane is up.
