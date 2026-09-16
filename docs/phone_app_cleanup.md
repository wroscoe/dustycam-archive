# dustyphone — cleanup plan

Merged from two reviews run 2026-09-15 night (firmware and app/tooling) over the
P0/P1 work described in `phone_app_status.md`. Findings cite `file:line` but were
**not individually re-verified** — confirm each at the line before changing it.

Risk key: **P** touches hardware-proven behaviour (re-run the gate), **p**
adjacent to it, **—** neither.

## Do not touch without a bench re-run

These are facts paid for in debugging time. Every one of them looks like
something a tidy-up would "simplify".

- BLE notify payload cap 244 B (`dusty_ble.c` `BLE_FRAG_MTU_CAP`) and the app's
  `Math.min(mtu, 247)` (`DustyLink.java:453`). 514 B notifies returned `rc=0`
  and never arrived on the Pixel 6.
- `ble_img` task stack must be internal RAM — any hook may write NVS, which
  panics from a PSRAM stack.
- SD bus mutex held across the whole of `mount_locked()` — the LED shares
  GPIO21 with SD CS; narrowing it brings back `sdmmc_card_init 0x107`.
- `esp_vfs_fat_sdspi_mount`, not the sdmmc variant.
- Default log level WARN; no new `ESP_LOGI` or bare `printf` on the Wi-Fi
  bring-up path (an attached serial reader + chatty logs stalled the join at 90 s).
- Strictly sequential radios: full NimBLE stop/deinit before Wi-Fi, full Wi-Fi
  deinit before NimBLE re-init.
- `handle_handoff`/`handle_live`/`handle_reboot` ordering: reply → `evt bye` →
  `s_going_quiet` → delay → terminate → hook. Keep the comments verbatim.
- No `esp_restart()` inside a `dusty_ble` handler — the `s_restart_requested` /
  `first_contact` chain is the fix for a blocker, not indirection to remove.
- No `esp_bt_mem_release()` — one-way on this target, kills later `dusty_ble_start()`.
- Reconnect after `POST /ble` stays a direct `connectGatt` (Android ignores
  >5 `startScan` per 30 s, silently).
- Discovery after handoff stays the UDP beacon on :8267 — never an IP prompt.
- `radio.c`'s "linked phone ignores the deadline" rule and `RADIO_BLE_GRACE_S`
  are two separate bug fixes; they cannot be collapsed into one deadline check.

## Done 2026-09-16 (with the crash fix)

`A4` (reclaim reallocs checked), `B13` (SPI bus ownership tracked; the bus is
kept up across remounts), the `adv_interval_timer_cb` work moved off the
esp_timer task, the `.idf_component_cache/` ignore (part of `A9`/`B7`), and
`crash_n`/`reset_reason` in `/status` + telemetry. The app's compiled-in dev
BLE key was replaced by a publicly derived, labelled one (the repo is public).
Everything else below is still open — in particular `A1` (Wi-Fi left up after a
failed join, then BLE started beside it).

## A — before committing

Firmware:

1. **`A1` Wi-Fi left initialised when a hotspot join times out** (`contact.c:837-843`,
   `:901-936`; `dusty_uplink.c:281`). `radio.c:192-209` then loops back into
   `dusty_ble_start()` with Wi-Fi still up and coex disabled — reachable whenever
   a join fails early in the window, and every time for an unprovisioned board's
   600 s window. Fix: `dusty_uplink_wifi_off()` on every failure exit, plus a
   `dusty_uplink_wifi_is_up()` check in `run_ble_phase()`. Risk **p**. S.
2. **`A2` `dusty_ble_stop()` does not wait for the controller to go IDLE**
   (`dusty_ble.c:1406-1408`) although `dusty_ble.h:5-12` promises it does. Add a
   bounded poll, then log + restart, matching the `nimble_port_stop` policy. Risk **p**. S.
3. **`A3` `heap_caps_print_heap_info()` on every radio state change** (`radio.c:57`)
   is raw `printf`, so WARN does not suppress it — exactly the serial-volume
   hazard above. Put it behind `#ifdef RADIO_HEAP_DUMP`. Risk **p**. S.
4. **`A4` unchecked `realloc` in SD reclaim** (`dusty_spool.c:300-305`, `:324-328`)
   → NULL deref under heap pressure, which feeds `crash_n` → Recovery. Risk **—**. S.
5. **`A5` `dusty_spool_mount()` accepts unset pins** (`dusty_spool.c:21`) and fails
   deep in the driver — this cost a full day. Guard + explicit error. Risk **—**. S.
6. **`A6` `ESP_ERROR_CHECK` on Wi-Fi bring-up** (`dusty_uplink.c:277, 280, 289`)
   panics on `ESP_ERR_NO_MEM` coming out of a BLE phase; return
   `CONTACT_END_JOIN_FAILED` instead. Risk **p**. S–M.
7. **`A7` `dusty_ota` truncates host/token at 64 B** while everything else uses 96
   (`dusty_ota.c:20-24`) — a long Funnel hostname silently points OTA elsewhere. **—**. S.
8. **`A8` `back_in_s` has two values** (`dusty_ble.c:83` says 60, `dusty_control.c:231`
   and `contact.c:367` say 2) and an obsolete "placeholder until P1" comment. **p**. S.
9. **`A10` dead `reason` parameter** in `contact_run_contact` (`contact.c:871`). **—**. S.

App / server:

10. **`B1` `ScanSettings` built and discarded** — `CameraActivity.java:468-483` and
    `ProvisionActivity.java:392-413` call the 1-arg `startScan(cb)`, so both
    reconnect paths scan at LOW_POWER instead of LOW_LATENCY. `ScanActivity.java:230-235`
    has the correct 3-arg form. Risk **—**. Trivial.
11. **`B2` `disconnect()`/`close()` drop in-flight callbacks silently**
    (`DustyLink.java:202-214`, `GattQueue.java:87-94`) — a disconnect mid-request
    leaves the UI silent with no error. Call `onError("disconnected")` first. **—**. S.
12. **`B3` `ProvisionActivity` rescan callback has no destroyed-activity guard**
    (`:384-422`, `onDestroy` `:119-123` never stops the scan) → `startActivity()`
    from a dead activity. Port `CameraActivity`'s `closed` flag. **—**. S.
13. **`B4` dead `CHANGE_NETWORK_STATE` permission** (`AndroidManifest.xml:24`) — the
    binding approach it was for was removed (`CamHttp.java:27-37`). **—**. Trivial.
14. **`B5` `apps/dustyphone/README.md` describes the removed `requestNetwork`
    binding** — fix before a future agent trusts it. **—**. Trivial.
15. **`B6` sensorhub: hand-rolled atomic write** in the `/d/<id>/settings` POST
    (`ingest.py:1249-1255`) duplicates `_write_json_atomic` (`:664-674`). **—**. Trivial.
16. **`A9`/`B7` repo hygiene**: `.gitignore` for `.idf_component_cache/` at repo
    level; keep `host/*.so`, `build/`, `sdkconfig`, `sdkconfig.secrets`,
    `__pycache__` out; **commit by path** — a lot of unrelated untracked CAD/N6
    work is sitting alongside. Delete or annotate the dead public API surface
    (`Session.removeListener/getCameraAddress`, `Framer.Reassembler.isPending`,
    `GattQueue.gatt`, `DustyLink.getMtu/getAddress`, `Beacon.isRunning`,
    `dusty_led_suspended()`, the unread `s_sub_*` flags in `dusty_ble.c`).

Sequencing: A1 → A2 → A6 (one cluster, then re-run the P0.1b handoff cycle) →
the rest → commit.

## B — soon

Firmware:

- **One hooks struct.** `contact.c:668-704` builds `dusty_control_hooks_t` and
  `dusty_ble_hooks_t` with the same pointers, and `.device` is patched on copies
  in three places. A shared `dusty_hooks.h` is what decides whether the N6 and
  RT1062 ports can reuse these components. M.
- **~45 KB internal RAM in `.bss` scratch** (`dusty_ble.c:162-163`, `:130`,
  `:133-135`; `dusty_control.c:241`; `contact.c:513` a 12 KB `entries[512]` of
  which 448 can never be shown, `n_req` caps at 64). Move `entries` to PSRAM
  first — free, no wire change. Risk **P** for the buffers on the transfer path.
- **`spool.list` blocks the httpd worker for a whole drain** (`contact.c:494-532`
  via `dusty_spool_scan()`'s `portMAX_DELAY`), while `frame`/`thumb` correctly
  answer busy. One of only two sockets. **p**. S.
- **`/stream` has no cap and can hang `httpd_stop()`** (`dusty_control.c:343-367`);
  `mark_request()` fires once at entry, so the idle rule can stop httpd mid-chunk.
  Also a frame leak when `stream_release` is NULL. **p**. S–M.
- **Four copies of hex→bytes; two copies of the NVS helpers** writing the same
  `"dusty"` namespace from components that don't depend on each other
  (`dusty_config.c:242-288` vs `dusty_ota.c:55-101`). M.
- **`contact.c` writes `dusty_ota`'s private NVS key** (`:932`, `:1080`) — export
  `dusty_ota_clear_pending()`. **p**. S.
- **SD/LED ownership split three ways** with an undocumented asymmetric hand-off
  (`main.c:374-380`, `contact.c:120-168`, `:1106-1111`): a second BLE window after
  a contact runs with the LED dead. Document the contract at minimum; better,
  give `dusty_spool` sole ownership of GPIO21. Do **not** convert
  `dusty_led_suspend/resume` to a counter without auditing every path. M.
- **`camera.c:95-110` hardcodes UXGA-derived sizes** — add a `_Static_assert` on
  `BOARD_CAM_FRAMESIZE`. **p**. S.
- **`dusty_ident_load()` does a full NVS read on every `/status` poll** (every 2 s
  from the setup page) — cache it. **—**. S.
- **SPI bus lifetime** (`dusty_spool.c:59-63`, `:79`, `:88-96`): track what this
  code actually initialised; that's the `spi_bus already initialized` E-line. **p**. S.
- **`dusty_config_apply()` leaves a half-applied config on a parse error**
  (`:84-91`) while `set_local` restores correctly. **—**. S.

App:

- **Decompose `CameraActivity.java` (995 lines)** into: the Activity (~200 lines,
  views + delegation); `ble/LinkSession` (connect/listener/link-lost/reconnect/
  rescan, `:343-511`); `HandoffController` (the whole BLE↔Wi-Fi state machine,
  `:636-852` — the largest chunk and where both silent-failure bugs live);
  `SettingsPanelController` (`:276-302`, `:903-994`); `BenchCycleDriver`
  (`:854-896`, the P0.1b gate driver — keep it, just not in this file). Do this
  before P2 piles a frame grid and preview view on top.
- **`ble/Ops.java` constants** — every op name is a bare literal in three files;
  a typo compiles and dies as "unsupported op" at runtime. S.
- **`GattQueue` has no watchdog on a wedged in-flight op** — if Android never
  fires the callback, the queue stalls forever while the link still reports
  READY, so every later request times out one by one with no Reconnect button.
  Needs its own bench pass. M, risk **medium**.
- **Fixed 8 s request timeout** (`DustyLink.java:119`) is already below the plan's
  own 8–15 s estimate for a full-res `frame`; make it a per-fragment stall timer
  before P3 adds that button. S–M.
- **Two silent failures**: Wi-Fi status polling never gives up and never logs a
  non-200 (`CameraActivity.java:746-774`); a failed bring-back leaves the session
  stuck in `RETURNING` with every button disabled, because `onTimeout`
  (`:839`) never sets `LOST` the way `onLinkLost()` does. S each.
- **Rotation destroys the radio session**; no activity sets `configChanges`.
  Cheapest fix is an orientation lock for a bench tool. Also `onDestroy()`
  doesn't `removeCallbacks(releaseGattRunnable)` (`:164-177`). Trivial–M.
- **Shared scan budget**: three independent `startScan` call sites with no shared
  counter, and a tripped Android throttle is indistinguishable from "camera not
  there" in the logs. Fold into a `ble/Rescanner` with the counter logged once.

## C — later

- Freeze or de-duplicate `bench/ble_spike` (733 lines, a parallel copy of the
  hook table and the radio FSM; its `camera.c` has **already diverged** — it
  lacks the double-init guard). Its README "Measured" tables are gate evidence
  and must survive. Banner it `FROZEN` at minimum.
- Promote `camera.c`/`board.h` out of `main/` into a `dusty_camera` component
  taking a pin struct (keep the `jpg2rgb565`/`fmt2jpg` endianness comment with it).
- Extract the two decision tables that produced the most bugs — `radio_next()`
  (`radio.c:89-209`) and `dc_cfg_sync_decide()` (`contact.c:994-1048`) — as pure
  host-testable functions in `dusty_core`.
- Wire-protocol naming (`wifi.up` vs `contact`; `live` colliding with
  `cfg.mode == "live"`): **only** as a versioned `proto: 2` release with a matched
  app, never as a tidy-up. Documenting the C return conventions is the cheap 90 %.
- The HTTP control plane is unauthenticated by design — write the threat model
  into `dusty_control.h` so the next port doesn't assume otherwise.
- `Prefs.DEV_BLE_KEY_HEX` is a real key compiled into the APK — a hard blocker
  for any non-bench build.
- Multi-fragment `cmd` partial-failure gap (`DustyLink.sendNow()` `:453-477`):
  fragments queued after a failed one still reach the firmware, so a `prov.set`
  or handoff the app believes it aborted can still be acted on. Verify on
  hardware before changing.

## Cheap tests that would have caught the bugs already paid for

- `sdkconfig` invariants per app: `CONFIG_LOG_DEFAULT_LEVEL_WARN=y`,
  `ESP_COEX_SW_COEXIST_ENABLE=n`, `BT_NIMBLE_ATT_PREFERRED_MTU=517`,
  `SPIRAM_MODE_OCT=y`, `BOOTLOADER_APP_ROLLBACK_ENABLE=y` — each assertion
  carrying the hardware fact in its failure message.
- Move `BLE_FRAG_MTU_CAP` into `ble_frame.h` so `test_ble_frame.py` can assert
  the 244/247 cap. The value must not change.
- `_Static_assert` that the `ble_img` task caps include `MALLOC_CAP_INTERNAL`.
- A text test that every app linking `dusty_spool` calls `dusty_spool_set_pins()`.
- Extract `DustyLink`'s id-correlation/queue/timeout state machine into an
  Android-free class and test it like `Framer`/`Crypto` (this is where the
  busy-queue and rsp-after-data bugs lived).
- Extract `SettingsForm.collectChangedCfg()`/`isKeepLabelsValid()` and test them
  (the `keep_labels` limit was one of the P1 review bugs).
- Test `ingest.py`'s real config-push handler the way `blobgate/test_blobgate.py`
  already tests its own — today only the pure `apply_push()` is covered.

## Comments to add where a hardware fact drove the code

`main.c:245-249` (log-level loop — say why); `dusty_led.c:23-33` (GPIO21 = LED =
SD CS, the 0-timeout take is what protects chip select); `dusty_uplink.c:300-330`
(full deinit before NimBLE, 21 cycles, drift ≤ 300 B); `contact.c:1106-1111` (the
card-mounted/LED-suspended hand-off and who unmounts); `main.c:579-581` +
`:251-254` (holding the shared LED/CS line high through deep sleep keeps the card
deselected); `camera.c:113-120` (add the sarg lesson id); `DustyLink` class doc
(main-thread-only contract — most fields are unguarded `HashMap`s).
