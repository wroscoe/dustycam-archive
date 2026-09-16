# dustyphone — Android BLE link for dustycam cameras (P0)

Owner-facing Android app that talks to a dustycam camera over BLE (and, after
a handoff, over the camera's Wi-Fi hotspot join). Built with the bare Android
toolchain — no Gradle, no Android Studio — following `~/code/photodroid`'s
approach. See `~/code/dustycam/docs/phone_app_plan.md` for the full design;
this is the **P0 spike** subset (§6 P0 row): a test-bench UI over the real
GATT protocol (§2), enough to prove the radio hand-off works before the full
P2 app is built.

## Build / install / run

```sh
cd ~/code/dustycam/apps/dustyphone
make container   # once: creates the long-lived `dustybuild` docker container
make build       # -> Dusty.apk
make test        # Framer round-trip / crc / ordering tests (plain java, no Android)
make install     # adb install -r + pm grant BLUETOOTH_SCAN/BLUETOOTH_CONNECT
make run         # am start .ScanActivity
make log         # adb logcat -s Dusty
```

`ADB` defaults to `/hd2/temp_data/android-sdk/platform-tools/adb` (not on
PATH on this workstation). `keystore/` and `build/` are gitignored; the debug
keystore is generated on first `make build` — back it up if you care about
reinstalling over the same signature later (`~/.dusty/keystore/` per the
plan, not yet automated here).

## What P0 proves

From `docs/phone_app_plan.md` §6:

- **P0.1a** (firmware, not this app): BLE + lazy camera internal-RAM
  headroom, `thumb` transfers crc-ok at >= 10 KB/s, `preview` init/capture/
  deinit stability.
- **P0.1b** (this app is the driver): BLE session -> `wifi.up` handoff ->
  camera joins the phone's hotspot -> `/status` answers over Wi-Fi ->
  `POST /ble` -> camera re-advertises within 3 s -> app reconnects **by BLE
  address** -> auth again. Repeated **10 cycles without a reboot or leak**
  (internal free per state flat within +-2 KB on the firmware side). The
  **Cycle x10** button in `CameraActivity` drives exactly this loop and logs
  per-cycle wifi-reached / ble-reached timings.

There is no camera advertising yet (firmware is P1 work), so `ScanActivity`'s
list is expected to be empty right now — this build only proves the phone
side: permissions, scanning, GATT framing/serialisation, and that the app
does not crash.

## Dev key caveat

`Prefs.DEV_BLE_KEY_HEX` is the **bench key compiled into the firmware
spike** (plan §1 decision 5), used until `ProvisionActivity` (P2) can import
a real per-owner `dusty_phone.json` via `dustygen --phone-json`. The UI
should label this key "DEV" wherever it's shown (P2 settings/about screen —
not yet built in P0, since P0 has no settings screen).

## Architecture (P0 subset of §4)

- `ble/Framer.java` — pure Java (no Android imports) implementation of the
  §2 wire framing: `[id u8][flags u8][idx u16 LE]` header, LAST/BIN/ERR
  flags, binary `[total u32 LE][crc32 u32 LE]` header, and the `Reassembler`
  that rejects out-of-order fragments and enforces the 4 KB/8 KB/512 KB
  request/response/data limits. Host-tested (`tests/FramerTest.java`, `make
  test`) so it can be checked without any hardware, matching the firmware's
  own `ble_frame.c` byte-for-byte.
- `ble/Crypto.java` — HMAC-SHA256 (`javax.crypto`) for the `hello`/`auth`
  challenge, hex helpers, 16-byte `SecureRandom` nonces. AES-256-GCM (for
  `prov.set`'s `env` field) is P2 work.
- `ble/GattQueue.java` — serialises Android's one-outstanding-GATT-op
  limitation (write/read/notify-enable/MTU/priority), with the standard
  status-133 (close + 500 ms + reconnect, up to 3x) workaround. Uses the
  API-33 `writeCharacteristic(char, byte[], writeType)` overload when
  available, the legacy setter otherwise.
- `ble/DustyLink.java` — one camera session: connect -> discover -> enable
  notifications on `rsp`/`data`/`evt` -> MTU 517 + high connection priority
  -> read `info` (refusing `proto != 1`) -> `hello`/`auth` -> READY. After
  that, `request(op, args, callback)` correlates replies by rolling id
  (1..255; 0 = events) and delivers `data` transfers with measured KB/s.
  Every op and its round-trip time is logged under tag `Dusty`.
- `Session.java` — app-side radio state: `BLE | HANDOFF | WIFI | RETURNING |
  LOST`, drives the `CameraActivity` status banner.
- `net/CamHttp.java` — HTTP to the camera's `:8266` control plane during the
  WIFI phase, bound to the phone's Wi-Fi transport specifically via
  `ConnectivityManager.requestNetwork(TRANSPORT_WIFI)` (the phone's default
  route may still be cellular).
- `Prefs.java` — `SharedPreferences`: ble_key, last camera address, last IP.
- `ScanActivity.java` — permission flow (BLUETOOTH_SCAN/CONNECT on 31+,
  ACCESS_FINE_LOCATION below), BLE scan (service UUID match, falling back to
  the `dc-` name prefix in-callback since some stacks are flaky about
  surfacing 128-bit UUIDs through the OS-level `ScanFilter`), lists name /
  address / rssi / provisioned flag (from manufacturer data), tap ->
  `CameraActivity`.
- `CameraActivity.java` — the P0 test bench: status banner, scrolling log,
  an `ImageView` for previews/thumbnails, and buttons for every P0 op
  (Status, Preview, Thumb, Shoot, View over Wi-Fi, Bring back to Bluetooth,
  Live) plus **Cycle x10**, the automated wifi.up/poll/POST-ble/reconnect
  loop that is gate P0.1b's driver. Reconnects by address on an unexpected
  disconnect (30 s rescan window); releases the GATT 60 s after `onStop`.

## Bench log

_(fill in as hardware becomes available — no camera has advertised yet as of
this build)_

| date | build | what was tested | result |
|---|---|---|---|
| 2026-09-15 | first P0 build | `make build`/`make test`/`make install`/`make run` on Pixel 6 (API 35, serial 1A041FDF600AHR) | `Dusty.apk` built (45,560 B); 68/68 Framer tests pass; app installs, launches to `ScanActivity`, no crash (empty list expected — no camera advertising yet) |
