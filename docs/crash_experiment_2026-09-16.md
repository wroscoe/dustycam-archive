# xiaocam1 crash — instrumented build to separate the causes

Context: `phone_app_status.md` → "LIVE BUG". Diagnosis by a Fable review on
2026-09-16; the main-task frame sizes were re-checked against `build/xiaocam1.elf`.

Hypotheses:
- **B (certain)** main-task stack overflow at the drain's first upload
  (12 720 B of frames on entry to `dusty_uplink_post_file` vs a 12 288 B stack).
- **A** a damaged heap header in the 22 KB internal region at `0x3fce9710` makes a
  later allocation overlap the esp_timer task's TCB; its owner overwrites the
  TCB's first ~44 B.
- **A′** a local overflow on the esp_timer task itself (`adv_interval_timer_cb`,
  `dusty_ble.c:1215-1232`).

This build moves the crash around (poisoning changes the heap layout). Only an
integrity-check failure or a watchpoint hit counts as evidence — a crash that
disappears is not a fix.

## sdkconfig (experiment build only)

```
CONFIG_HEAP_POISONING_COMPREHENSIVE=y
CONFIG_FREERTOS_WATCHPOINT_END_OF_STACK=y   # watchpoint 0: catches B with the PC
```

## Code (all after the Wi-Fi join, so WARN stays the default)

1. Stack high-water, `ESP_LOGW(TAG, "main hwm=%u", uxTaskGetStackHighWaterMark(NULL))`,
   at: contact start, after the config GET, after the announce, at drain entry,
   and right after `fopen()` in `dusty_uplink_post_file()`.
   B is confirmed if drain entry is below ~4.5 KB or the post-`fopen` line
   never prints.
2. Once at drain entry, before `sd_take()`:
   ```c
   TaskHandle_t t = xTaskGetHandle("esp_timer");
   ESP_LOGW(TAG, "esp_timer tcb=%p main stack=%p", t, pxTaskGetStackStart(NULL));
   heap_caps_dump(MALLOC_CAP_INTERNAL);
   ```
   Shows the TCB's neighbours. If an esp_timer block sits directly below the main
   stack, B is the direct writer and A collapses into it.
3. `heap_caps_check_integrity_all(true)` after: `dusty_ble_stop` (`radio.c:134`),
   the join, `dusty_control_start`, `cam_ensure`, the announce, before mount #2,
   after mount #2, after the scan. The first failing checkpoint locates A's origin.
4. Store-watchpoint on the corrupted field, armed right before the drain's `sd_take()`:
   ```c
   static void arm_wp(void *arg) { esp_cpu_set_watchpoint(1, arg, 4, ESP_CPU_WATCHPOINT_STORE); }
   uint8_t *p = (uint8_t *)xTaskGetHandle("esp_timer") + 40; /* xEventListItem.pxContainer */
   arm_wp(p);
   esp_ipc_call_blocking(1, arm_wp, p);   /* watchpoints are per CPU */
   ```

## Reading the result

| output | meaning |
|---|---|
| watchpoint 0 fires (end of stack) | B — raise the main stack and rerun for A |
| watchpoint 1, backtrace in `sdmmc_read_sectors` / FATFS / newlib `memcpy` | A — an overlapping allocation; its owner is innocent, look at the first failed integrity check |
| watchpoint 1, backtrace on the esp_timer task | A′ — the culprit callback is on screen |
| watchpoint 1 in `vListInsert` from `xQueueSemaphoreTake` on the esp_timer task | a legitimate block from a Wi-Fi callback — re-arm and continue |
| no watchpoint, assert still fires | a DMA writer (SPI RX into a misplaced buffer) — log the camera's and SPI2's GDMA descriptors against the TCB address |

## Fixes, smallest first (none touch the proven constraints)

**Status 2026-09-16 10:13 — all five done and on the XIAO as the field image**
(no `sdkconfig.crashdebug`): cold cycle drained 6/6, `contact_n=4`, the
advertising switch still fires at 31 s from the host task, no
`spi_bus … already initialized` line, then 31 consecutive warm timer wakes
over 30 min with no crash and no `heap_guard` abort. Telemetry now carries
`crash_n` and `reset_reason`. The main stack stays at 20 KB even though ~8 KB
of locals moved to PSRAM — re-measure with the overlay before shrinking it;
BLE-phase internal free is 118.7 KB (was 134.6), so BLE + camera should sit
near 97 KB against the 80 KB gate. The SPI bus is now kept up across
remounts on purpose (no DMA churn), rather than freed on unmount.

1. `CONFIG_ESP_MAIN_TASK_STACK_SIZE=20480` (24576 if the TLS high-water says so);
   move `dusty_uplink_post_file`'s `buf[4096]`, `contact_run_contact`'s 1 KB
   buffers, `drain_tier`'s `meta[1024]` and `app_main`'s 2.6 KB frame to PSRAM or static.
2. `CONFIG_ESP_TIMER_TASK_STACK_SIZE` 3584 → 4096–6144, and have
   `adv_interval_timer_cb` set a flag (or post to the NimBLE host task) instead of
   calling `ble_gap_adv_stop/start` and logging from the esp_timer context.
3. `dusty_spool_unmount()` frees the SPI bus when `mount_locked()` initialised it;
   drop the unconditional `spi_bus_free()` on the mount-failure path.
4. `CONFIG_HEAP_POISONING_LIGHT` + `heap_caps_check_integrity_all(false)` at the
   same phase boundaries feeding `crash_n`, so the next corruption aborts at its
   origin; add `crash_n` and the reset reason to `/status` and telemetry.
5. Check the reallocs in `dusty_spool_reclaim()`.
