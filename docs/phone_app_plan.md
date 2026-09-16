# dustyphone: Android app + BLE link for dustycam cameras — implementation plan

Written 2026-09-14, revised 2026-09-15 (sequential radios) against `docs/camera_standard.md`,
`docs/camera_operation.md` (§3, §5, §8, §10), `cameras/xiao_pantilt/PLAN.md`. First target:
`xiaocam1` (ESP-IDF 5.5, unflashed; gate 1 pending). Three jobs: (a) provision a new camera in
the field, (b) view/edit tuning, (c) look at imagery with no Wi-Fi/cell.
Verified facts this plan leans on: app bin 2,028,672 B in a 3,145,728 B OTA slot; identity is
compile-time `CONFIG_DUSTY_*` (Kconfig.projbuild) — no NVS identity today; `dc_cfg_to_json`/
`dc_cfg_apply_json` already round-trip tier-2 JSON; `dusty_control` only runs inside
`contact_run()` after a successful `GET /config`; blobgate proxies only `GET /config|firmware`
and `POST /blob|/telemetry`; Pixel 6 (API 35) is on adb; SDK has platform 34 + build-tools 34.
**Design rule (decided 2026-09-15): BLE and Wi-Fi are sequential, never concurrent** — the
"modern IoT" model: BLE for onboarding and control, Wi-Fi for data. Internal-SRAM contention
between the BT controller, Wi-Fi and the camera is taken off the table by construction.

## 1. Decisions

1. **App lives at `~/code/dustycam/apps/dustyphone/`** (new top-level `apps/`, package
   `com.dustycam.phone`). Rejected `tools/`: workstation Python (dustygen, configurator); an
   APK has its own container, keystore and build. Rejected `cameras/xiao_pantilt/software/host/`:
   the app is cross-camera. Standard §6 gains one line for `apps/`.
2. **Java 11, no Gradle**, photodroid's `tools/build.sh` copied verbatim (aapt2/javac/d8/zipalign/
   apksigner in `eclipse-temurin:17-jdk`, new container `dustybuild` mounting `~/code/dustycam:/work`
   and `/hd2/temp_data/android-sdk:/sdk`). Rejected Kotlin: needs kotlinc in the container
   (ask-first download) and ~1.5 MB stdlib for ~1500 lines. Rejected Android Studio: nothing
   here needs Compose/Material libs. `minSdk 26, targetSdk 34` (platform 35 not installed; 34
   runs on Android 15). JSON via `org.json`, crypto via `javax.crypto`; no third-party jars.
3. **BLE stack: NimBLE, peripheral-only** (`CONFIG_BT_NIMBLE_ENABLED`, central/observer off).
   Rejected Bluedroid (~2x flash/RAM). Rejected Espressif `wifi_provisioning`/protocomm:
   provisioning-only, protobuf, fixed service; we also need settings, images, handoff.
4. **One custom GATT service, JSON request/response + framed notify streams.** Rejected CBOR
   (a lib on both ends; JSON already exists in firmware and Android). Rejected NUS-style raw
   UART (no message boundaries, no correlation). Payloads reuse the `/status` and
   `/config/<id>` JSON shapes so both transports share the standard's vocabulary.
5. **Auth = HMAC challenge with an owner key, no BLE pairing/bonding.** No display → LE pairing
   is Just Works only (unauthenticated: any phone could reprovision) and adds pairing dialogs +
   bond-loss failures. Instead `ble_key` (32 B, one per owner, `[ble] key` in
   `~/.dusty/secrets.toml`, stored in the phone once) → `hello`/`auth` HMAC-SHA256; secrets in
   `prov.set` are AES-256-GCM under a session key (mbedtls is already linked). An
   **unprovisioned** camera (no key) accepts `prov.set` only inside a physical-presence window
   (120 s after a BOOT press or cold boot) and only once. NimBLE SM is compiled out.
6. **Camera is the config sync agent; the app never talks to sensorhub.** App edits over BLE
   → NVS overlay, `cfg` += 1, `cfg_src = "ble"`, `cfg_base` = the server cfg it started from.
   Next contact: `POST /config/<id>` `{"base":cfg_base,"config":{...},"schema":{...}}` (new
   token-checked route through blobgate). Server accepts iff `server.cfg == base` (keeps the
   camera's cfg), else 409 + current → camera applies the server's (server wins a real
   conflict). Rejected: app-as-sensorhub-proxy (token in the app, cell reachability, conflict
   UI). Rejected: volatile BLE overrides (silently stale on the device page). Standard change
   (§5, §3): the *phone app* may edit tier 2; the setup page still edits nothing.
7. **Tier 1 gains a second path: NVS identity.** Firmware reads NVS namespace `ident`
   (`device ssid pass host port tls token ble_key`), falling back to `CONFIG_DUSTY_*`. `dustygen
   --blank` builds the fleet image with empty secrets; `dustygen --phone-json` writes
   `~/.dusty/dusty_phone.json` (server host/port/tls/token, hotspot ssid/pass, ble_key) that the
   app imports once via the system file picker. Rejected QR: needs a decoder jar — later.
8. **Schema ships in the firmware.** dustygen also stamps `main/tuning_schema.h` (the same
   `<id>.schema.json` object, ~2 KB string) so the settings form is data-driven off-grid and a
   field-provisioned id needs nothing pre-seeded on sensorhub. Rejected: schema in the app
   (drifts from firmware; breaks "firmware first, then config").
9. **Radio state machine (sequential, never concurrent):**
   ```
   SLEEP ──button / cold boot──▶ BLE ──wifi.up | contact──▶ WIFI ──phase ends | POST /ble──▶ BLE ──window over──▶ SLEEP
                                  │ (advertise ble_adv_s;                (NimBLE stopped and freed          (re-advertise, same MAC,
                                  │  linked phone extends)                BEFORE esp_wifi_start;            if window time remains)
                                  └──window over, no link──▶ SLEEP        contact/drain or no-server viewing)
   ```
   Timer wakes never touch a radio. A BLE link extends the window (`contact_idle_s` of silence
   ends it). Today's button contact is preserved: with no BLE link inside `ble_adv_s`, the camera
   still tries the hotspot itself (BLE → WIFI on timeout), so the phone app is optional.
   Unprovisioned: BLE up to 600 s, then sleep. Rejected: concurrent radios with SW coexistence —
   the internal-SRAM budget becomes a measurement instead of a guarantee, for progress events
   that HTTP `/status` gives anyway.
10. **Lazy camera, lazy TLS, at most two heavy peers live at once.** `esp_camera_init` runs only
    for `preview`/`shoot`/live thumb and `xc_cam_deinit` follows immediately (sarg: never init
    twice without deinit); spooled thumbnails are decoded from the SD JPEG, no sensor. TLS
    objects exist only in the WIFI phase. Live sets are therefore **BLE+camera** (preview) or
    **Wi-Fi+camera+TLS** (today's contact, already sized) — never BT controller + Wi-Fi. The
    judge (TFLite arena) is never initialised inside a window (main.c currently calls
    `judge_init()` before the contact block; it moves after it).
11. **BLE vs Wi-Fi split.** BLE: provisioning, status, schema, cfg get/set, spool list +
    thumbnails from SD (200x150 JPEG, 6-10 KB), one-shot preview (~1 fps), shoot-to-spool,
    events, time sync, Wi-Fi scan, and the two handoffs (`wifi.up`, `contact`). Wi-Fi (camera
    joins the phone's hotspot; cell not required for viewing): MJPEG `/stream`, full-res
    `/spool/<boot>/<seq>.jpg`, `/status` polling, the drain, `POST /ble` to come back. Full-res
    over BLE stays as a late slow fallback (200 KB ≈ 8-15 s) for "no Wi-Fi at all".
12. **Hotspot: two paths, honestly.** (a) The owner's regular hotspot, toggled by hand (apps
    cannot toggle tethering since API 26), 2.4 GHz / "extend compatibility"; creds are tier 1;
    gives the real contact with cell uplink. (b) `WifiManager.startLocalOnlyHotspot` (API 26+):
    app-started, random creds readable by the app and passed in `wifi.up`; no internet, dies
    with the app process, band chosen by the system (may be 5 GHz on a Pixel 6 → invisible to
    the ESP32; gate P3.2). Wi-Fi Direct rejected: no P2P GO in ESP-IDF's STA stack.

## 2. GATT protocol spec (v1)

Base UUID `7d1e00XX-dc0a-4c9b-8f6e-2e9a0c5d1b00`; service `XX=01`. Characteristics:

| XX | name | props | purpose |
|---|---|---|---|
| 02 | `info` | read (no auth) | `{"proto":1,"device":"xiaocam1","v":"…","cfg":7,"prov":1,"nonce":"<16B hex>","stage":"contact","radio":"ble"}` |
| 03 | `cmd` | write, write-no-rsp | request frames |
| 04 | `rsp` | notify | response frames (JSON) |
| 05 | `data` | notify | bulk binary (JPEG) frames |
| 06 | `evt` | notify | unsolicited JSON events |

Advertising: name `dc-<device>` (unprovisioned `dc-new-<mac4>`), 128-bit service UUID in adv
data, manufacturer data `[0xDC 0x0A][proto u8][flags u8]` (bit0 provisioned, bit1 back-from-
Wi-Fi, bit2 unprovisioned-window open). Fixed static random address (derived from the base
MAC) so the app can re-find the same camera by address after a Wi-Fi phase. Interval 100 ms
for the first 30 s, then 500 ms. Re-advertise immediately on disconnect while the window lasts
(sarg: re-advertising is what makes a link survivable). MTU: camera prefers 517
(`CONFIG_BT_NIMBLE_ATT_PREFERRED_MTU=517`); app calls `requestMtu(517)` then
`requestConnectionPriority(CONNECTION_PRIORITY_HIGH)`.

**Framing (all three notify chars and `cmd`):** header 4 B `[id u8][flags u8][idx u16 LE]`,
payload ≤ MTU-3-4 B. flags: `0x01 LAST`, `0x02 BIN`, `0x04 ERR`. `id` correlates a request with
its `rsp`/`data` frames (app increments 1..255; 0 = events). Binary transfers: the first `data`
fragment's payload starts with `[total u32 LE][crc32 u32 LE]`; then raw bytes. No per-fragment
ACK (link layer is ordered and reliable); the app checks total+crc and re-requests on mismatch.
Camera paces notifies on `ble_gatts_notify_custom` return + a 2 ms yield. Limits: request ≤ 4 KB,
response ≤ 8 KB, data ≤ 512 KB.

**Session:** `{"op":"hello","pn":"<16B hex>"}` → `{"nonce":…}` (also in `info`);
`{"op":"auth","mac":hex(HMAC-SHA256(ble_key, cam_nonce||phone_nonce))}` → `{"ok":true}`.
Every other op except `hello`, `auth`, `prov.set`-in-window answers `err:auth` until then.
Session key `sk = HMAC(ble_key, "sk"||cam_nonce||phone_nonce)` for the GCM envelope.

**Ops** (`{"id":n,"ok":true,…}` or `{"ok":false,"err":"…","msg":"…"}`):

| op | request | response / effect |
|---|---|---|
| `status` | — | the `/status` JSON + `radio` (`ble`), `led`, `stage`, `cfg_src`, `win_left_s`, `sd` |
| `cfg.schema` | — | `tuning_schema.h` object (`{"id","camera","keys":[{name,type,default,help}]}`) |
| `cfg.get` | — | `dc_cfg_to_json` object (includes `cfg`, `mode`) |
| `cfg.set` | `{"cfg":{...known keys...}}` | `dc_cfg_apply_json` minus the `cfg` key, bump `cfg`, `cfg_src=ble`, NVS; LED updated; `{"cfg":N}` |
| `prov.set` | `{"env":base64(AES-256-GCM(sk, json))}` or plaintext inside the presence window | json = `{device,ssid,pass,host,port,tls,token,ble_key}` → NVS `ident`; `{"device":…}`; camera restarts |
| `prov.get` | — | non-secret identity: `device host port tls ssid` |
| `time.set` | `{"ts":epoch,"tz_min":n}` | `settimeofday`, clock `set`, `clock_skew_s`, `clock_src:"ble"` |
| `spool.list` | `{"tier":"spool","n":24,"after":"<boot>/<seq>"}` | `{"items":[{"boot","seq","score","why","ts","lum"}],"more":true}` score desc (`dusty_spool_scan`+sort) |
| `thumb` | `{"boot":17,"seq":42}` | `data`: 200x150 JPEG decoded 1/8 from the card (`cam_decode`→`cam_preview_jpeg`; no sensor) |
| `frame` | `{"boot","seq"}` | `data`: the full JPEG from the card (slow fallback) |
| `preview` | — | lazy `xc_cam_init`, one capture, deinit; `data`: 200x150 JPEG + `rsp` `{"focus":f,"lum":n}` |
| `shoot` | — | lazy init/deinit; full capture recorded to spool `why: manual` (delivered at the next drain) |
| `wifi.scan` | — | `{"aps":[{"ssid","rssi","ch"}]}` — needs Wi-Fi driver up for ~3 s; **BLE stays up** (scan-only, no BT controller conflict is the assumption; gate P0.1b checks internal free; if it bites, `wifi.scan` becomes a WIFI-phase `/scan`) |
| `wifi.up` | `{"ssid","pass"}` optional override | **handoff**: `{"ok":true,"handoff":"wifi","expect_ip":"<last ip or ''>","back_in_s":N,"mode":"view"}` then `evt bye`, disconnect, NimBLE stopped, join, `dusty_control` up with no server needed |
| `contact` | — | same handoff shape with `"mode":"contact"`; runs the full contact sequence (clock, announce, firmware, config push/pull, drain, serve) |
| `live` | — | ends the window (the `GET /live` equivalent); camera sleeps |
| `reboot` | — | `esp_restart` |

Events on `evt` (id 0): `{"ev":"led","p":"solid|searching|updated|fail|off"}`,
`{"ev":"stage","s":"contact|setup|live|night"}`, `{"ev":"cfg","cfg":N,"src":"server|ble"}`,
`{"ev":"bye","reason":"handoff|window|live","back_in_s":n}`. No drain events over BLE: during
WIFI the phone is on the same hotspot and polls HTTP `/status`.

**HTTP additions (WIFI phase, `dusty_control` :8266):** `/status` gains `radio` (`wifi`),
`ble_back_in_s` (seconds until the Wi-Fi phase ends by itself and BLE re-advertises; 0 when
pinned by `mode: setup`), `win_left_s`, `mode` (`view|contact`), `drain` `{sent,pending,failed}`.
`POST /ble` = end the Wi-Fi phase now: reply `{"ok":true,"radio":"ble","in_s":2}`, then radio off,
NimBLE re-init, advertise (same address). `GET /spool?tier=&n=&after=` (JSON list),
`GET /spool/<boot>/<seq>.jpg` (4 KB chunks under the SD mutex; 503 while the drain holds the
card), `GET /thumb/<boot>/<seq>.jpg`.

**Re-finding the camera after WIFI:** the app keeps the BLE address from the session; on
`bye handoff` it starts polling `/status`; when `/status` stops answering or reports
`ble_back_in_s <= 2`, or after `POST /ble`, it rescans (filter = that address + service UUID)
for up to 30 s and re-runs `hello`/`auth`. The camera re-advertises within 3 s of Wi-Fi stop
(gate P0.1b). If the window has expired, `bye` said so and the app shows "press the button".
Error codes: `auth denied badreq busy nofile sd wifi toolarge unsupported window radio`
(`radio` = "not in this phase"). Versioning: `info.proto`; the app refuses unknown `proto`.

## 3. Firmware changes

New component `cameras/common/espidf/components/dusty_ble/` (REQUIRES `bt nvs_flash mbedtls
dusty_core dusty_config esp_timer`):
- `include/dusty_ble.h`: `dusty_ble_start(const dusty_ble_hooks_t*)`, `dusty_ble_stop()` (blocks
  until the controller is idle and its heap is back), `dusty_ble_connected()`,
  `dusty_ble_last_request_us()`, `dusty_ble_event(json)`, `dusty_ble_send_data(id, buf, n)`.
  Hooks mirror `dusty_control_hooks_t` plus `spool_list thumb frame preview wifi_scan handoff
  prov_set time_set`. `handoff(mode, ssid, pass)` only *records* the request; the caller's
  state machine performs it after the reply and `bye` have been flushed.
- `src/ble_frame.c` (+`include/ble_frame.h`): **portable, no IDF headers** — fragment/reassemble,
  crc32; host-tested via ctypes (`cameras/common/espidf/tests/test_ble_frame.py`).
- `src/dusty_ble.c`: NimBLE init/adv/GATT, request task (internal stack, 6 KB: it writes NVS,
  and flash writes are not allowed from a PSRAM stack), auth state, op dispatch. Image work
  (JPEG decode for `thumb`, `preview`) runs on a worker created with
  `xTaskCreateWithCaps(..., MALLOC_CAP_SPIRAM)` (12 KB stack in PSRAM; it never touches flash).
  `src/ble_auth.c`: nonce, HMAC, session key, GCM.
- **Radio teardown / re-init** (`dusty_ble_stop` → `dusty_ble_start`): `ble_gap_adv_stop`,
  `ble_gap_terminate`, `nimble_port_stop()`, `nimble_port_deinit()` — on IDF 5.5 for the S3 this
  disables and deinits the controller (`esp_bt_controller_disable/deinit` inside
  `esp_nimble_deinit`); verify `esp_bt_controller_get_status() == ESP_BT_CONTROLLER_STATUS_IDLE`
  after, and assert it in the log line. **Never call `esp_bt_mem_release()` /
  `esp_bt_controller_mem_release(ESP_BT_MODE_BLE)`: both are one-way (the BT heap region is
  handed to the general heap and the controller cannot be initialised again this boot).** The
  only mem_release allowed is `ESP_BT_MODE_CLASSIC_BT` once at boot (no-op on the S3).
- `dusty_config`: `dusty_ident_load(dusty_ident_t*)` (NVS `ident` → fallback `CONFIG_DUSTY_*`),
  `dusty_ident_save()`, `dusty_config_set_local(json)` (bump + NVS `cfg_src`, `cfg_base`).
- `dusty_uplink`: `dusty_uplink_post_json(path, json, resp, n, &status)` for `POST /config/<id>`;
  `dusty_uplink_wifi_scan(out, max)`; `dusty_uplink_wifi_off()` becomes a full
  `esp_wifi_stop`+`esp_wifi_deinit` so its buffers are returned before BLE re-init.
- `dusty_control`: `/status` fields above, `POST /ble`, `GET /spool…`, `GET /thumb…`; httpd
  config `max_open_sockets 2`, `stack_size 3072` (raise to 4096 if the high-water mark says so),
  `lru_purge_enable`.
- `main/`: `board.h` unchanged. `main.c`: identity from `dusty_ident_load`; `judge_init()` moves
  after the window block; new `radio.c` owns the state machine:
  ```
  if (woke_by_button || cold || contact_pending) radio_window_run(reason);
  radio_window_run: deadline = now + ble_adv_s (unprovisioned: 600 s)
    loop:
      BLE:  dusty_ble_start; serve until handoff | live | (no link && deadline) | (link idle contact_idle_s)
            dusty_ble_stop
            if handoff: → WIFI
            elif no link ever && provisioned && reason != PENDING_VERIFY: → WIFI(contact)   # today's button contact
            else break
      WIFI: contact_run(mode)  — mode=contact: as today; mode=view: join, control plane, no clock/announce/drain
            ends on contact_idle_s | setup_secs | GET /live | POST /ble ; radio off
            if (POST /ble or phase ended) && now < deadline: → BLE  else break
  ```
  `contact_run` gains `mode`, `POST /ble` support, step 5 config push when `cfg_src==ble` (409 →
  apply server's), `tuning_schema.h` in the body, and returns why it ended. `contact.c`'s hooks
  table is shared by HTTP and BLE (same functions; the `shoot` hook does the lazy init/deinit).
- `heap_caps_print_heap_info(MALLOC_CAP_INTERNAL)` plus one line
  `I radio: state=<SLEEP|BLE|WIFI> internal_free=<n> largest=<n>` at **every** transition, kept
  permanently (WARN level would hide it: this tag is set to INFO at boot with `esp_log_level_set`).
- Every window ends with the radio in SLEEP state (NimBLE deinit'd, Wi-Fi deinit'd, camera
  deinit'd) before `esp_deep_sleep_start`.

sdkconfig.defaults deltas (the SRAM diet; every value is a starting point that gate P0 prints
the internal-free table for):
```
# BLE (NimBLE peripheral only, HMAC auth: no SM)
CONFIG_BT_ENABLED=y
CONFIG_BT_NIMBLE_ENABLED=y
CONFIG_BT_NIMBLE_ROLE_CENTRAL=n
CONFIG_BT_NIMBLE_ROLE_OBSERVER=n
CONFIG_BT_NIMBLE_MAX_CONNECTIONS=1
CONFIG_BT_NIMBLE_MAX_BONDS=0
CONFIG_BT_NIMBLE_MAX_CCCDS=4
CONFIG_BT_NIMBLE_MSYS_1_BLOCK_COUNT=8
CONFIG_BT_NIMBLE_SECURITY_ENABLE=n
CONFIG_BT_NIMBLE_NVS_PERSIST=n
CONFIG_BT_NIMBLE_ATT_PREFERRED_MTU=517
CONFIG_BT_NIMBLE_MEM_ALLOC_MODE_EXTERNAL=y
CONFIG_BT_NIMBLE_LOG_LEVEL_WARNING=y
CONFIG_BT_CTRL_BLE_MAX_ACT=2
# (no CONFIG_ESP_COEX_SW_COEXIST_ENABLE: radios are never up together)
# Wi-Fi buffers (contact throughput is re-measured at XIAO gate 4 with these)
CONFIG_ESP_WIFI_STATIC_RX_BUFFER_NUM=4
CONFIG_ESP_WIFI_DYNAMIC_RX_BUFFER_NUM=8
CONFIG_ESP_WIFI_DYNAMIC_TX_BUFFER_NUM=8
CONFIG_ESP_WIFI_AMPDU_TX_ENABLED=n
CONFIG_ESP_WIFI_AMPDU_RX_ENABLED=n
CONFIG_SPIRAM_TRY_ALLOCATE_WIFI_LWIP=y
# TLS
CONFIG_MBEDTLS_DYNAMIC_BUFFER=y
CONFIG_MBEDTLS_DYNAMIC_FREE_PEER_CERT=y
CONFIG_MBEDTLS_DYNAMIC_FREE_CONFIG_DATA=y
CONFIG_MBEDTLS_SSL_IN_CONTENT_LEN=4096      # only if the Funnel endpoint honours max_fragment_length (verify with openssl s_client -maxfraglen 4096; else stay 16384)
# Stacks / heap
CONFIG_SPIRAM_ALLOW_STACK_EXTERNAL_MEMORY=y  # only for tasks that never write flash (image worker)
CONFIG_LOG_DEFAULT_LEVEL_WARN=y
CONFIG_LOG_MAXIMUM_LEVEL_INFO=y              # summary/radio tags re-enabled at boot
CONFIG_DUSTY_BLE=y                           # main/Kconfig.projbuild: compile-time opt-out
```
Kconfig.projbuild gains `DUSTY_BLE` (bool) and `DUSTY_BLE_KEY` (hex string; empty in `--blank`).
TFLite arena: `judge_arena_info()` already reports "(SPIRAM)"; P0 confirms it with internal-free
before/after `judge_init`, and `judge_init` becomes lazy (first motion wake, never in a window).

Flash/RAM budget: `.flash.text` 967 KB + `.flash.rodata` 915 KB (643 KB model) → bin 1.93 MB of
3.0 MB. NimBLE host + S3 controller ≈ 220-300 KB (no coex lib) → ≈ 2.25 MB, ≥ 0.85 MB headroom;
no partition change. NVS (24 KB): `ident` ≈ 400 B. Internal SRAM is reported per state by the
spike (§6 P0). Power: radios only in the button window, ~0.4 mAh per press; gate 2 unchanged.

Wake-cycle placement and LED wording: see §5 (`contact`/`unprovisioned` rows, §10 "solid while
linked over either radio").

## 4. Android app design (`apps/dustyphone/`)

```
apps/dustyphone/
  README.md  Makefile (build/install/run/log via docker exec dustybuild + /sdk adb)  AndroidManifest.xml
  tools/build.sh (photodroid's)   keystore/ (gitignored; back up to ~/.dusty/keystore/)
  res/mipmap-xxxhdpi/ic_launcher.png
  src/com/dustycam/phone/
    ScanActivity.java        list of dc-* advertisers (name, prov flag, rssi); hint "press the camera's button"
    CameraActivity.java      one screen, four panels via a bottom bar: Status | Settings | Frames | Setup
    ble/GattQueue.java       one-outstanding-op serialiser, 133 retry, MTU/priority
    ble/Framer.java          §2 framing: fragment, reassemble, crc32 (tests/FramerTest.java, plain `java`)
    ble/DustyLink.java       hello/auth, ops → callbacks, evt dispatch, address-filtered reconnect
    ble/Crypto.java          HMAC-SHA256, AES-GCM (javax.crypto)
    net/CamHttp.java         HttpURLConnection bound to the Wi-Fi Network (ConnectivityManager.requestNetwork
                             TRANSPORT_WIFI + network.openConnection); /status poll, /spool, /thumb, POST /ble
    Session.java             the app-side radio state: BLE | HANDOFF | WIFI | RETURNING | LOST; one source of truth for the UI
    ui/SettingsForm.java     schema-driven rows: int/float → EditText(number), bool → Switch, str/list → EditText
    ui/FrameGrid.java        GridView of thumbnails (cache keyed boot/seq), tap → FrameActivity
    FrameActivity.java       full frame over HTTP when in WIFI; in BLE: "switch to Wi-Fi to view" or the slow BLE `frame`
    PreviewView.java         BLE `preview` at 1 Hz (BLE phase) or WebView on http://<ip>:8266/stream (WIFI phase)
    ProvisionActivity.java   import dusty_phone.json (ACTION_OPEN_DOCUMENT), type device id, send prov.set
    Prefs.java               ble_key, imported profile, last camera address (app-private SharedPreferences)
```
- Manifest: `BLUETOOTH_SCAN` (`neverForLocation`), `BLUETOOTH_CONNECT` (31+); `BLUETOOTH`,
  `BLUETOOTH_ADMIN`, `ACCESS_FINE_LOCATION` (maxSdk 30); `NEARBY_WIFI_DEVICES` (33+) for the
  LOHS experiment; `INTERNET` + `usesCleartextTraffic=true` for `:8266`; `uses-feature
  bluetooth_le required`. Runtime prompts via `requestPermissions`; `make install` pre-grants.
- **Status panel** shows the radio state as a banner (`Bluetooth linked` / `Switching to
  Wi-Fi…` / `Wi-Fi <ip>` / `Returning to Bluetooth…` / `Lost — press the camera's button`), the
  `/status` table, LED/stage line. Buttons: Sync time (automatic on connect), Shoot, Preview,
  **Contact** and **View over Wi-Fi**, Live.
- **Handoff UX:** tapping Contact or View over Wi-Fi opens a sheet: "Turn on your phone's
  hotspot (2.4 GHz / extend compatibility). Camera will join `<ssid>`." with the SSID from
  `prov.get`; OK sends `contact`/`wifi.up`; on the `handoff` reply the app enters HANDOFF, shows
  a spinner "camera is switching to Wi-Fi (up to `hotspot_join_s` s)", requests the Wi-Fi
  network, and polls `http://<expect_ip or last ip>:8266/status` every 2 s (no IP known: the
  user is asked to read it off the hotspot's client list; P3's mDNS `dc-<device>.local` is the
  fix). In WIFI the panel shows `/status.drain` and `ble_back_in_s`; **Bring back to Bluetooth**
  sends `POST /ble` → RETURNING → rescan by address → BLE. If `/status` never answers within
  `hotspot_join_s`+10 s the app rescans: the camera has re-advertised (`bye reason` = `window`
  if it gave up).
- Settings: `cfg.schema` + `cfg.get` → form; Save → changed keys only → `cfg.set`; banner "cfg N,
  syncs to sensorhub at next contact"; `cfg_src` badge. Disabled in WIFI (edits are BLE-only in
  v1; the setup page still edits nothing).
- Frames: `spool.list` pages of 24 by score; thumbnails over BLE from SD (~0.5 s each at
  20 KB/s) in BLE, over `/thumb` in WIFI; full-res and MJPEG in WIFI only; the slow BLE `frame`
  is a labelled fallback behind a long-press.
- Foreground rules: no service; GATT held while an activity is started, released 60 s after
  `onStop`; `/status` polling only while visible. The camera never depends on the app. On an
  unexpected disconnect inside the window, rescan the saved address for 30 s.

## 5. Standard changes (diff-style)

`docs/camera_standard.md`
- §3 "The setup page edits nothing on the board": + "The owner's phone app (`apps/dustyphone`)
  may edit tuning over BLE; the board bumps `cfg`, records `cfg_src = ble`, and pushes the
  result to sensorhub at its next contact (`POST /config/<device>`, base-checked; server wins a
  real conflict). The setup page still edits nothing."
- §4 Config pull: + "Config push: boards with `ble` POST `{base, config, schema}`; sensorhub
  accepts iff `cfg == base`, else 409 with the current."
- §4 Control plane: + `POST /ble`, `GET /spool[?tier&n&after]`, `GET /spool/<boot>/<seq>.jpg`,
  `GET /thumb/…`; `/status` gains `radio`, `ble_back_in_s`, `win_left_s`, `drain`.
- §5 tier 1 "Reaches the board by": "generated secrets file flashed over USB, **or** NVS
  identity written over BLE by the phone app (`dustygen --blank` fleet image); NVS wins."
  + `ble_key` in `~/.dusty/secrets.toml [ble]`; `dustygen --phone-json`.
- §6 layout: + `apps/<app>/` for owner-facing apps; `tuning_schema.h` next to `tuning_defaults.h`.
- §8 DoD: + "Provisioned from the phone only (no USB) and reached sensorhub" for `ble` boards;
  + "10 BLE↔Wi-Fi handoff cycles without a reboot, internal heap flat".

`docs/camera_operation.md`
- §1: "There is no field provisioning" → "Field provisioning is over BLE from the phone app
  (decision 2026-09-14); USB stays the workstation path." Config editing sentence: + phone app.
  + "Radios are sequential: BLE for onboarding and control, Wi-Fi for data; never both
  (decision 2026-09-15)."
- §2 capabilities: + `ble` (yes XIAO, **no** N6: the STM32N657 has no BLE radio).
- §3 table: `unprovisioned` "Owner sees: LED double blink; advertises `dc-new-…`"; `contact`
  "Entered by: button opens a BLE window; a phone can hand the camera to Wi-Fi (`wifi.up`/
  `contact`) and back (`POST /ble`); with no phone linked inside `ble_adv_s` the camera hands
  itself to Wi-Fi for the contact".
- §4.1 tuning: + `ble_adv_s = 120`. §5 step 1: "Button press … LED searching; **advertise BLE
  for `ble_adv_s`; a linked phone may hand off to Wi-Fi at any time**". Step 5: + push rule.
  New step 7b: "view mode: `wifi.up` joins the hotspot and serves without clock/announce/drain
  (viewing off-grid); `POST /ble` returns to BLE while the window lasts".
- §8 Time: + "or from the phone over BLE (`time.set`), `clock_src` in contact telemetry".
- §9 changes table: + rows Config push, `ble_adv_s`, `cfg_src`, `clock_src`, `ble` capability,
  `radio`/`ble_back_in_s` in status.
- §10 LED: + "a phone linked over either radio: solid (it is the contact)".
- §12: + "NimBLE deinit/re-init stability across handoff cycles on IDF 5.5; LOHS band on the
  Pixel 6; contact throughput with the trimmed Wi-Fi buffers".

Sensorhub (other repo): blobgate `POST /config/<device>` proxy (token); ingest handler with the
base rule, writes `<id>.json` + `<id>.schema.json` when supplied.

## 6. Phases and bench gates

| # | package | proof (on hardware) | effort | blocked on |
|---|---|---|---|---|
| **P0 spike** | `cameras/common/espidf/bench/ble_spike/` IDF project with the sdkconfig diet above: NimBLE adv + `info`/`hello`/`auth`/`status`/`thumb`(from SD)/`preview`(lazy camera) over §2 framing, `wifi.up` handoff, minimal HTTP `/status` + `POST /ble`, radio state machine, `radio:` heap line at every transition. App: `ScanActivity` + bare `DustyLink`/`CamHttp`/`Session`: connect, MTU 517, auth, `status`, one `thumb`, `wifi.up`, poll `/status`, `POST /ble`, rescan-reconnect. | **P0.1a** BLE + lazy camera: internal free ≥ 80 KB with NimBLE up and the camera initialised; `thumb` 10/10 crc-ok at ≥ 10 KB/s (log KB/s); `preview` init/capture/deinit 20x with no SCCB hang. **P0.1b** handoff: BLE session → `wifi.up` → `esp_bt_controller_get_status()==IDLE`, hotspot joined, `/status` answers over the phone's Wi-Fi, `POST /ble` → Wi-Fi off, re-advertising within 3 s, app reconnects by address; **10 cycles without a reboot or leak** — internal free per state per cycle flat within ±2 KB. The spike prints the table `state | internal_free | largest_block` for SLEEP-side, BLE idle, BLE+camera, WIFI, WIFI+TLS(+camera) and it goes in the README + sarg. 3 walk-away disconnects each recover by re-advertise + rescan. | 3-4 d | first flash only (bench on USB; cold boot opens the window). Not gate 1. |
| **P1 firmware** | `dusty_ble` full ops, `radio.c` in `main/`, `dusty_ident`, `--blank`/`--phone-json`/`tuning_schema.h` in dustygen, `contact_run(mode)` + `POST /ble` + config push + sensorhub POST route, `/spool` HTTP, lazy `judge_init`, full Wi-Fi deinit in `dusty_uplink_wifi_off`. Host tests: `test_ble_frame.py`, dustygen tests. | **P1.1** button → `dc-xiaocam1` visible within 3 s; `cfg.set period_s=45` → `cfg` N+1 in `status`, survives sleep/wake; `contact` handoff drains and the device page shows N+1 (push accepted); a server-side edit made first yields 409 → server value wins, visible as `cfg_src`. **P1.2** NVS-erased board + `--blank` image: `dc-new-…`, `prov.set` in window → restarts as `xiaocam1`, joins, drains. **P1.3** no phone: button alone still contacts after `ble_adv_s` (today's behaviour). **P1.4** XIAO gate 4 re-run with the trimmed Wi-Fi buffers (≥ 200-frame drain; if throughput drops > 30 %, AMPDU TX goes back on). | 3-4 d | **XIAO gate 1** for the button path (cold-boot path unblocked) |
| **P2 app** | Full `CameraActivity`: settings form from schema, frames grid + thumbs, preview, handoff UX with `/status` polling and Bring-back, provisioning import, time sync, events, reconnect, Makefile/README. | **P2.1** provision a wiped camera from the phone alone, no USB, then see its frames on sensorhub. **P2.2** edit two keys off-grid (airplane mode), verify on the board, walk into cell, tap Contact → device page updates. **P2.3** 24 thumbnails browsed in < 20 s over BLE; app survives screen lock and returns; a handoff round-trip from the UI in < 30 s. | 4-5 d | P1 |
| **P3 Wi-Fi viewing** | View mode polish: `FrameActivity` over HTTP, WebView MJPEG, `/thumb` in WIFI, mDNS `dc-<device>.local` (IDF `mdns` component; drop if it costs > 10 KB internal), LOHS experiment (`startLocalOnlyHotspot` → creds → `wifi.up`), slow BLE `frame`. | **P3.1** hotspot on, cell off: full-res frame in the app in < 2 s, MJPEG ≥ 3 fps, then Bring-back works. **P3.2** LOHS: does the ESP32 see it (band)? pass/fail in sarg; if fail, dropped and the README says so. **P3.3** full-res over BLE ≤ 20 s. | 2-3 d | P1, P2 partial |
| **P4 field** | Docs (§5), README "Standard mapping" + status line + heap table, sarg lessons (NimBLE deinit/re-init on IDF 5.5, handoff heap numbers, LOHS band, trimmed-buffer throughput), `cfg_src`/`clock_src`/`radio` on the device page (sensorhub). | Two field sessions: one new camera provisioned on site; one settings change + imagery review with no cell (BLE thumbs, then Wi-Fi full-res, then back to BLE); `clock_skew_s` logged. | 2 d | P0-P3 |

Order inside P0: firmware spike first (P0.1a, then P0.1b — re-init stability decides everything
else), app spike second. XIAO gates 1-2 stay on PLAN.md's path, on the same first-flash day.

## 7. Risks, verification, questions

Risks (verify at the gate named):
- **Leak across BLE↔Wi-Fi cycles** (P0.1b): NimBLE host/controller, Wi-Fi driver, LWIP and
  esp_http_server each allocate on init; anything not returned shows as a falling
  `internal_free` per cycle. The `radio:` heap line is permanent so field logs catch it too.
  Mitigation if it leaks: `esp_wifi_deinit` + `esp_netif_destroy_default_wifi`, `httpd_stop`
  before Wi-Fi off, NimBLE `nimble_port_deinit` order; as a last resort a Wi-Fi phase ends the
  window (one handoff per press) rather than returning to BLE.
- **NimBLE deinit/re-init stability on IDF 5.5** (P0.1b): sarg has nothing on this; it is the
  lesson to record (symptom → cause → fix, with the exact call order and the
  `esp_bt_controller_get_status` check). Known pitfall: `esp_bt_mem_release` is one-way.
- Trimmed Wi-Fi buffers cut contact throughput (P1.4); AMPDU TX is the first knob to give back.
- `MBEDTLS_SSL_IN_CONTENT_LEN=4096` breaks TLS if the Funnel does not honour max fragment
  length (verify before P1; fall back to 16384 with dynamic buffers).
- `wifi.scan` from the BLE phase brings the Wi-Fi driver up next to the BT controller; if P0.1b
  shows it costs internal RAM, it moves to the WIFI phase as `GET /scan`.
- Android GATT flakiness (133 on connect, MTU, dropped notifications when backgrounded; P0,
  P2.3): GattQueue + address-filtered rescan. Unknown camera IP after a first handoff: P2
  prompts, P3's mDNS is the real fix.
- BOOT strapping pin (gate 1) may move the button: only `BOARD_BUTTON_GPIO` changes here.
  Config conflicts (P1.1) must be visible on the device page (`cfg_src`). LOHS band (P3.2) is
  likely the first thing to fail; nothing depends on it. `targetSdk 34` on Android 15 is fine;
  raising it needs a platform-35 download (ask first).
- Security: `ble_key` in app-private storage is adequate for one owner; the presence window on
  an unprovisioned board is the only unauthenticated write and can only set identity once.

Questions for the user (only where the answer changes the work):
1. One `ble_key` per owner (this plan) or per camera? Per-camera means the app manages a key
   list and dustygen prints one per id.
2. Is the "blank fleet image + NVS identity" path acceptable as a second tier-1 route, making USB
   provisioning optional? (If no, job (a) reduces to hotspot/server edits on an already-flashed id.)
3. For field viewing, is toggling the phone's regular hotspot by hand acceptable as the primary
   path, with LOHS only as an experiment? (If LOHS must work, P3.2 moves into P0.)
4. Full-res over BLE (8-20 s per frame): worth building as the fallback, or Wi-Fi only?
5. Should `cfg.set` be allowed while a drain is in progress? (Moot in v1: edits are BLE-only and
   the drain is a Wi-Fi phase; answer decides whether the setup page/HTTP ever gets an edit route.)
6. Sensorhub `POST /config/<device>`: OK to add to blobgate/ingest as part of P1, or must that
   land separately first?
