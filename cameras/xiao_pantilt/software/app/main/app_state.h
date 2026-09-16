/* app_state: the RTC-memory state that must survive deep sleep (but not a
 * power cycle), plus the small bits of NVS bookkeeping that go with it.
 * Contract: PLAN.md §3, §4, §6, §8.
 */
#ifndef APP_STATE_H
#define APP_STATE_H

#include <stdint.h>
#include "dusty_core.h"

#ifdef __cplusplus
extern "C" {
#endif

/* clock_state values (camera_operation.md §8) */
#define APP_CLOCK_NONE 0
#define APP_CLOCK_EST  1
#define APP_CLOCK_SET  2

typedef struct {
    uint32_t magic;
    dc_thumb_t thumb;
    int thumb_valid;
    uint32_t wake_n;
    uint32_t seq;
    uint32_t awake_ms;    /* accumulated awake time since the last recorded frame */
    int pending_n;        /* spool count estimate */
    int debug_written;
    dc_night_t night;
    int clock_state;      /* APP_CLOCK_* */
    int last_lum;
    uint32_t crc;         /* must be last: covers everything above it */
} app_state_t;

/* The live RTC-memory instance. Every field above `crc` is covered by the
 * checksum; touch it through this pointer, then call app_state_save()
 * before every sleep. */
extern app_state_t g_state;

/* Validates magic+crc. On success (warm wake from deep sleep) returns 0
 * and leaves g_state untouched. On failure (first-ever boot, a power
 * cycle, or corruption) zeroes g_state, sets the magic, bumps NVS
 * "boot_count", resets seq to 0, and returns 1 ("cold boot"). */
int app_state_load(void);

/* Sets clock_state from the system clock vs. NVS "last_ts"
 * (camera_operation.md §8): if time() looks unset (< 2020-01-01), restore
 * the last known epoch from NVS and mark APP_CLOCK_EST (or APP_CLOCK_NONE
 * if there is no persisted value yet); if the clock already reads sane
 * (a deep-sleep wake keeps the RTC timer running), clock_state is left as
 * whatever survived in RTC memory. Call once per boot, after
 * app_state_load(). */
void app_state_clock_init(void);

/* Persist NVS "last_ts" = ts. Call on every recorded frame and at contact
 * (the clock sync point). */
void app_state_note_frame_time(int64_t ts);

/* Recomputes the crc and writes the struct back to RTC memory (a no-op
 * beyond the crc on real hardware, since g_state already lives there, but
 * keeps the checksum valid for the next wake's validation). Call
 * immediately before every esp_deep_sleep_start(). */
void app_state_save(void);

/* "set" | "est" | "none", for dc_meta_t.clock and telemetry. */
const char *app_state_clock_str(void);

#ifdef __cplusplus
}
#endif
#endif
