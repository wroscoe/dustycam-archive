# Camera operation: lifecycle, profiles, policies

**Status: draft skeleton, 2026-09-12.** Decisions from the first design
pass are marked *decided*; everything marked *open* still needs an answer.

This document sits on top of [`camera_standard.md`](camera_standard.md).
The standard fixes the loop, the modes, the device↔sensorhub contract and
the config tiers. This document says what a camera *does* with that loop
given the hardware it has and the job it has been given, so that two
different boards give the same user experience. Where this document
changes the standard, section 9 lists the change.

The two target cameras are the **Seeed XIAO ESP32S3 Sense**
(`cameras/xiaocam1`, ESP32-S3, OV3660, SD card, deep sleep, one LED)
and the **OpenMV N6** (`cameras/n6cam`, STM32N657 with a neural
accelerator, 1280x800, no SD card fitted yet, RGB LED).

## 1. The deployment this is written for

*Decided 2026-09-12.*

- Cameras are provisioned by the owner over USB on the workstation, **or**
  in the field over BLE from the phone app (decision 2026-09-14): a
  `dustygen --blank` fleet image carries no identity, and the app writes it
  into NVS (`docs/camera_standard.md` §5). USB stays the workstation path.
- Cameras operate where there is **no LAN and no internet**. They never come
  home to the workstation network.
- The owner's **Android phone is the only link**. Its hotspot has cell data.
  The camera joins the hotspot on a button press and then behaves exactly as
  a standard camera on a LAN: it drains its spool to sensorhub, pulls config
  and firmware, and reports telemetry. Nothing is stored on the phone.
- Images are processed in the cloud (sensorhub). The camera's job is to
  record the right frames and hand them over in bulk. Target: **the best
  ~1000 frames per week** per camera, plus optional low-resolution debug
  frames for tuning the motion trigger.
- A frame is deleted from the camera once sensorhub has accepted it. With
  the hotspot model, "on the phone" and "in the cloud" are the same event.
- **Night is decided by daylight, not by the clock.** The camera has no
  infrared, so it sleeps with the radio off from dark until light. It does
  not wake for heartbeats at night. Only the button wakes it.
- Mesh (MeshCore) is out of scope for this pass. The policy hooks are kept
  so it can be added as a notification channel later.
- Configuration is edited on the sensorhub device page's settings form (or
  in `~/.dusty/config.toml` for defaults); `dustygen` seeds the server
  config and never overwrites a value already there unless `--reset-config`.
  The camera pulls it at the next contact and the device page shows the new
  `cfg`: that is the "settings updated" signal, mirrored by an LED pattern
  on the board.

## 2. Capability vocabulary

Every conditional clause in this document keys off a capability or a
setting, never off a board name. `camera.toml` `capabilities` gains:

| capability | meaning | XIAO | N6 |
|---|---|---|---|
| `deep_sleep` | can power down between wakes and resume with state | yes | *open: verify `machine.deepsleep` current and RTC survival* |
| `sd` | removable storage large enough to hold a week of frames | yes (64 GB proven 2026-09-12) | **no card fitted**; required for the game profile |
| `light` | can read scene luminance cheaply (exposure / mean of a preview) | yes (`lum`, `exp` from the sensor) | yes |
| `ir` | can see in the dark | no | no |
| `model` | runs an on-device gate on a frame | TFLite-micro + ESP-NN, 3-class MobileNetV2 gate ([`animal_model.md`](animal_model.md)) | NPU, same gate at higher input size; detector later |
| `button` | user button that wakes the board | BOOT button | user button (press unverified) |
| `hotspot` | can join a phone hotspot as a WiFi station | yes | yes |
| `pir` | hardware motion interrupt | no | no |
| `mesh` | radio to a MeshCore node | no | no |

Existing capabilities (`preview`, `focus_score`, `motion`, `full_res`,
`spool`, `pull_config`, `pull_firmware`, `setup_mode`, `shoot`) keep their
meaning.

## 3. Lifecycle stages

Stages of use, from the box to the field. Each stage says what runs, what
the owner sees, and how it is entered and left. `setup` and `recovery` are
the standard's; `contact` and `night` are new.

| Stage | What runs | Owner sees | Entered by | Left by |
|---|---|---|---|---|
| **unprovisioned** | nothing but the loader; no `secrets` present | LED: fast double blink | first flash; secrets deleted | USB copy of secrets + app, reset |
| **first boot** | boot, then a contact attempt (section 5) so the owner sees it work | LED: searching, then contact | first boot after provisioning | contact ends → **live** |
| **live** | the profile loop (section 4) | LED off; one short blink per recorded frame (setting `led_capture`) | first boot, end of contact, end of night | button → contact; dark → night; crash → recovery |
| **night** | deep sleep with the radio off; rare probe wakes to look for light | nothing | dark for `night_confirm_n` consecutive wakes | light on a probe wake → live; button → contact |
| **contact** | join the hotspot, sync clock, pull firmware then config, drain the spool, report, then serve the setup page while the phone is attached | LED: searching → solid → confirm or fail; device page updates on the phone | button press (any stage), first boot | timeout after last request, or `GET /live` |
| **setup** | as the standard: preview with focus score, shoot, sensor readouts, refresh | phone page at `http://<ip>:8266/setup` | inside contact, when the phone opens the page | `setup_secs` idle, `GET /live` |
| **recovery** | control plane only, reachable on the hotspot | LED: slow heartbeat | crash with nothing to roll back to; button held at boot | successful firmware update at a contact |

Rules:

- **The button always works.** In every stage, including night and mid
  drain, a press is honoured within a few seconds. On a deep-sleeping
  board it is the wake source.
- **Contact replaces reachability.** The standard's law that the heartbeat
  frame keeps a board reachable does not hold off-grid. Its replacement:
  the camera records a heartbeat frame every `heartbeat_s` of *awake* time
  so that every drain carries proof of life even with zero motion, and the
  camera is fully reachable at every contact.
- **Nothing is delivered in live mode.** The Deliver stage of the standard
  is deferred to contact. The spool is the primary store, not a fallback.

## 4. Profiles

A profile is a named bundle of tuning values plus the set of policies that
are switched on. It is tuning (tier 2), so it changes without a reflash and
is pulled at a contact. `profile` becomes a tuning key.

| profile | for | power | trigger | judge | delivery |
|---|---|---|---|---|---|
| `game_lowpower` | animals, off-grid, battery | wake cycle, night sleep | interval wake, motion diff, heartbeat | model gate if `model`, ranked | spool to SD, drain at contact |
| `monitor` | the N6 today on a LAN | always on | motion diff, heartbeat | optional | live upload, spool as fallback |
| `timelapse` | scene change over days | wake cycle, night sleep | interval only | none | spool, drain at contact |
| `speedcam` | `n6_speedcam` | wake on radar | sensor | none | live upload |

This pass specifies `game_lowpower` fully. `monitor` is the standard as it
stands. The others are placeholders so the profile names are reserved.

### 4.1 `game_lowpower`, one wake

```
wake (timer period_s, or button)
  Sense    battery, charge, lum
  Night?   lum < lum_night for night_confirm_n wakes → enter night (section 6)
  Watch    small grayscale preview; diff against the last *recorded* thumbnail
           (persisted across sleep)
  Trigger  motion: diff ≥ diff_min_frac
           interval: every interval_n wakes regardless (timelapse spine)
           heartbeat: heartbeat_s of awake time since the last recorded frame
           debug: every wake, if debug_frames (records the preview, not a capture)
  Capture  full resolution, sensor JPEG where the sensor can
  Judge    if model: detections; keep if any label in keep_labels with
           conf ≥ gate_pct; else discard, unless keep_all or the 1-in-N audit
           score = rank for the drain (section 7)
  Record   JPEG + sidecar JSON to the SD spool (standard meta + score)
  Rest     deep sleep period_s
```

Tuning keys (defaults are proposals):

```toml
[tuning]
profile = "game_lowpower"
period_s = 30            # wake interval
interval_n = 120         # record a frame every N wakes even without motion (≈1 h)
heartbeat_s = 3600       # awake-time between forced frames
diff_min_frac = 0.02
diff_l_thresh = 8
gate_pct = 60            # model confidence to keep
keep_labels = ["animal", "person"]   # the gate's classes: animal / person / empty (animal_model.md)
keep_all = false         # keep frames the model rejects
audit_n = 20             # keep 1 in N rejected frames anyway
debug_frames = false     # record the preview + diff of every wake
debug_max = 500          # debug frames kept per contact interval
upload_cap = 1000        # ranked frames uploaded per contact
lum_night = 12           # open: calibrate on real data
lum_day = 25             # hysteresis; must exceed lum_night
night_confirm_n = 3
night_margin_s = 2700    # wake this long before the learned dawn
night_probe_s = 1200     # probe interval while dark and not yet at the learned dawn
hotspot_join_s = 90      # how long to search for the phone at a contact
contact_idle_s = 120     # end contact this long after the last request
setup_secs = 300
telemetry_s = 60         # only meaningful during contact
led_capture = true
```

## 5. Contact: the phone as the network

*Decided 2026-09-12: option A, the camera joins the phone hotspot.*

The hotspot SSID and password are identity (tier 1), generated into the
board's secrets by `dustygen` from `~/.dusty/secrets.toml`. The sensorhub
host is the Funnel address, so `dustygen --public`.

Sequence, all boards:

1. Button press. If asleep, wake. LED: searching. Note the stage we came
   from so it can be resumed.
2. Join the hotspot as a station for up to `hotspot_join_s`. Failure: LED
   fail pattern, return to the previous stage. This is the only path that
   costs battery without producing anything, so the timeout is short.
3. **Clock.** Set the RTC from the server (HTTP `Date` header or NTP). Record
   `clock_skew_s` = server time minus board time before the set, and
   `clock` = how the board's time had been kept (section 8).
4. **Announce** telemetry: `mode = 3` (contact), boot reason, battery,
   pending count, `clock_skew_s`.
5. **Firmware first, then config.** Check `GET /firmware/<device>/version`,
   install with rollback if newer. Then `GET /config/<device>`, apply, store.
   LED: three quick blinks when `cfg` changed ("settings updated"). The
   device page on the phone shows the new `cfg` in the next telemetry.
6. **Drain**, ranked (section 7), up to `upload_cap` frames, then debug frames
   up to `debug_max`. Each accepted frame is deleted from the card. Telemetry
   every `telemetry_s` so the owner can watch progress on the device page.
   The control plane is polled between frames; the setup page works mid drain.
7. **Serve.** Keep the radio up and the setup page available until
   `contact_idle_s` passes with no request. The owner reaches the page from
   the device page's setup link, which follows the `ip` in the meta.
8. **Leave.** Final telemetry, radio off, resume: night if it is dark, else
   live. Motion reference reset; one confirmation frame recorded (`why: boot`).

Phone-side facts that must go in the camera README: Android hotspot must be
set to 2.4 GHz (or "extend compatibility"); the phone stays on cell data
while the camera is attached; the sensorhub device page is opened over cell
and its setup link points at the hotspot's private network, which the phone
routes locally.

Budget: 1000 frames × 150–300 KB is 150–300 MB per weekly contact. At a
realistic 0.5–1 MB/s from an ESP32 that is 3–10 minutes with the phone next
to the camera. *Open: measure on both boards; if it is much slower, the
default `upload_cap` or the capture size comes down.*

## 6. Night policy

*Decided 2026-09-12: daylight only, radio off, no clock or location.*

- **Detect.** Each wake reads `lum` (mean of the preview, or the sensor's
  exposure/gain product where cheaper). Below `lum_night` for
  `night_confirm_n` consecutive wakes → night. Above `lum_day` on a probe
  wake → day. The gap between the two thresholds is the hysteresis.
- **Learn.** The board stopwatches each night with its RTC and keeps the
  last seven night lengths in a file that survives sleep and power loss.
  The prediction for tonight is the median of the last three.
- **Sleep.** With no history (first night after provisioning or a battery
  swap) sleep `night_probe_s` between probes all night. With history, sleep
  until `predicted_length − night_margin_s`, then probe every
  `night_probe_s` until light. The margin absorbs day-to-day change and RTC
  drift (section 8).
- **Wake.** The first light wake records a frame (`why: boot`) with the
  measured night length in the meta (`night_s`), so the server can plot it.
- **Button** wakes the board at night and runs a contact; after the contact
  it goes back to night sleep if still dark.
- The morning frame and every frame carry `lum`, so the thresholds can be
  tuned from real data. *Open: record a week of `lum` per wake with
  `debug_frames` on before fixing the defaults.*

## 7. Storage, ranking and the 1000-frame budget

The card is large relative to the need (64 GB holds hundreds of thousands
of frames), so the camera does not have to choose what to keep at capture
time. It chooses what to *upload*.

- **Tiers.** Every frame that passes Judge is written to the spool as
  today: sidecar JSON first, image to a temp name, rename. Frames the model
  rejects are written only if `keep_all`, or as the 1-in-`audit_n` audit.
- **Score.** The sidecar carries `score`, a rank for the drain. Proposal:
  detection confidence if any, else motion `diff`, with a sharpness term
  (the setup page's focus score) as a tiebreaker. `why: heartbeat` and
  `why: boot` frames rank above everything so proof of life always goes.
- **Drain order.** At contact, read the sidecars, sort by score descending,
  upload up to `upload_cap`. Then debug frames up to `debug_max`.
- **Reclaim.** Frames not uploaded stay on the card as a cold tier. When
  the card passes `spool_max_frames` (or 80 % full) the oldest cold frames
  are deleted first. Uploaded frames are deleted on acceptance.
- **Debug frames.** With `debug_frames`, every wake writes its preview (the
  small grayscale used for the diff, JPEG) with `why: watch`, `diff` and
  `gate` in the meta. They are the data for tuning `diff_min_frac` and
  `diff_l_thresh`. They never count against `upload_cap`.
- **Layout on the card** (readable when the card is pulled): one directory
  per boot, `/spool/<boot_count>/<seq>.jpg` + `.json`. Names never depend
  on the clock, because the clock is not trusted (section 8). `ts` is in
  the sidecar.

## 8. Time

The standard says `ts` is the truth. Off-grid there is no NTP between
contacts, so time is a first-class problem:

- The RTC is set at every contact from the server. `clock_skew_s` in the
  contact telemetry records how far it had drifted since the last contact.
- Between contacts frames carry the board's clock and a `clock` key:
  `set` (set at a contact and running since), `est` (running from a
  persisted value after a reset, likely wrong by the down time), or `none`
  (never set since power loss). The server corrects `ts` for frames between
  two contacts by a linear fit using `clock_skew_s`. *Sensorhub work.*
- The ESP32-S3 deep-sleep timer runs on an internal RC oscillator; drift is
  reported at percent level and is temperature dependent. Over a week that
  is hours. *Open: measure on the XIAO (log RTC vs server at every contact
  for two weeks). If it is bad, an external RTC (DS3231) is a small add.*
- The night policy needs only durations, not absolute time, so percent-level
  drift is covered by `night_margin_s`.

## 9. Changes to the standard

Firmware first, then config: none of these keys may be published before a
firmware that understands them is on the board.

| Area | Change |
|---|---|
| Modes | new mode `contact` (`mode: contact` in meta, `3` in telemetry); new stage `night`, reported as `mode: live` with `night: 1` in telemetry |
| Laws | the heartbeat-reachability law is replaced for off-grid profiles by section 3's contact rule; the radio is off at night by design |
| Pipeline | Deliver is deferred to contact for wake-cycle off-grid profiles; the spool is primary |
| Meta keys | `score` (drain rank), `clock` (`set`/`est`/`none`), `lum` mandatory when `light`, `night_s` on the morning frame, `why: watch` for debug previews |
| Telemetry | `clock_skew_s`, `night`, `pending_cold`, `contact_n` |
| Config keys | section 4.1: `profile`, `interval_n`, `keep_labels`, `keep_all`, `audit_n`, `debug_frames`, `debug_max`, `upload_cap`, `lum_night`, `lum_day`, `night_confirm_n`, `night_margin_s`, `night_probe_s`, `hotspot_join_s`, `contact_idle_s`, `led_capture` |
| Secrets | hotspot SSID and password; `dustygen --public` becomes the default for off-grid cameras |
| Capabilities | section 2 |
| Setup page | shows pending, cold and uploaded counts, night state and learned night length, `clock` state; **still edits nothing** |

## 10. What must be identical across boards

*Open: confirm this list.* Proposal, from strongest to weakest:

1. The contract: meta keys, telemetry keys, config keys, profile names.
2. The contact sequence and its timings.
3. The LED language below, as the lowest common denominator (one LED). The
   N6 may add colour but never a pattern the XIAO cannot show.
4. The setup page and the sensorhub device page.
5. Analogous, not identical: capture size, model and label set, `lum` scale
   (the thresholds are per-board tuning).

LED language (one LED, `on`/`off` only):

| state | pattern |
|---|---|
| unprovisioned | double blink every second |
| searching for the hotspot | one blink per second |
| contact, draining | solid |
| settings updated | three quick blinks, then solid |
| contact failed | five fast blinks, then off |
| live | off; one 50 ms blink per recorded frame if `led_capture` |
| night | off |
| recovery | one blink every two seconds |

## 11. Per-board mapping

One row per stage or policy; the camera README carries the authoritative
copy under "Standard mapping".

| Stage / policy | XIAO ESP32S3 Sense | OpenMV N6 |
|---|---|---|
| Boot / secrets | flashed over USB; *open: ESP-IDF (unflashed) vs Arduino core (camera + SD proven)*; the spec is runtime-neutral | loader + `secrets.py` over USB as today |
| Wake cycle | deep sleep, timer + button (EXT wake) | *open: verify deep sleep, wake sources, sleep current* |
| Light | `lum`/`exp` from the OV3660 preview | mean of the VGA preview |
| Watch / motion | small grayscale diff, thumbnail in RTC memory or on the card | `common/micropython/motion.py` as today, thumbnail persisted to flash |
| Capture | UXGA 1600x1200 JPEG from the sensor | 1280x800 RGB565 + software JPEG |
| Judge / model | 3-class MobileNetV2 α0.35 gate, 96–128 px, motion-centred crop, esp-tflite-micro + ESP-NN | same gate at 160–224 px on the NPU via `stedgeai`; phase 2: ST-YOLO-LC / YOLOv8n two-class detector ([`animal_model.md`](animal_model.md)) |
| Spool | SD card (proven) | **needs an SD card fitted**; until then not applicable and the profile cannot run |
| Contact | STA join to the hotspot, `dusty_uplink` | `network.WLAN` STA, `common/micropython/uplink.py` |
| Clock | set from the server at contact; internal RC drift to measure | STM32 RTC, backup domain; drift to measure |
| Night | file on the card | file on flash |
| LED | one user LED | RGB LED, one channel for the standard patterns |
| Button | BOOT button | user button (*press unverified*) |
| Setup page | `common/espidf` control component | `common/micropython/control.py` as today |

## 12. Open items, in order of risk

1. **Hotspot join on both boards** against a real Android hotspot, including
   the 2.4 GHz setting and how long a join takes. Nothing recorded in sarg
   yet.
2. **Upload throughput** for a 1000-frame drain from each board through a
   phone, to validate `upload_cap` and the capture size.
3. **ESP32-S3 RTC drift** through deep sleep over two weeks.
4. **N6 deep sleep**: current, wake sources, RTC survival, whether MicroPython
   state and the persisted thumbnail come back.
5. **N6 SD card**: fit one; without it the game profile is not applicable.
6. **Night thresholds**: a week of `lum` per wake from a real site with
   `debug_frames` on, before defaults are fixed.
7. **The gate model**: decided in [`animal_model.md`](animal_model.md)
   (one 3-class MobileNetV2 classifier on both boards, motion-centred
   crop, trained on LILA camera-trap data with MegaDetector labels). Open
   there: the XIAO's 0.5 s timing, and N6 custom-model conversion.
8. **XIAO runtime** decision (ESP-IDF vs Arduino core) so the shared
   components have a home.
9. **Sensorhub work**: `mode: contact`, `clock` correction, cold/pending
   counts on the device page, debug-frame viewer for motion tuning.
10. Whether frames the model rejects should be kept as thumbnails when there
    is a card (cheap, and useful for judging the gate).
