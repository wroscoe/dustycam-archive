/* telemetry: the numbers-only report of camera_standard.md §4 / §7 plus
 * the off-grid additions of camera_operation.md §9 (clock_skew_s, night,
 * pending_cold, contact_n).
 */
#ifndef XIAOCAM1_TELEMETRY_H
#define XIAOCAM1_TELEMETRY_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define TELEMETRY_MODE_LIVE     0
#define TELEMETRY_MODE_SETUP    1
#define TELEMETRY_MODE_RECOVERY 2
#define TELEMETRY_MODE_CONTACT  3

/* Fields telemetry_build cannot pull from another component itself
 * (uptime_s, mem_free, rssi, cfg, boot_count, lum, night come from
 * esp_timer/esp_system/dusty_uplink/dusty_config/app_state directly).
 * Zero any field that does not apply this call. */
typedef struct {
    int frames_sent;
    int frames_skipped;
    int upload_failures;
    int pending_files;
    int pending_cold;
    int clock_skew_s;
    int contact_n;
    int debug_pending;
} telemetry_extra_t;

/* Writes a flat JSON object of numbers to buf. Returns the length written,
 * or -1 if it did not fit. */
int telemetry_build(char *buf, size_t n, int mode, const telemetry_extra_t *extra);

#ifdef __cplusplus
}
#endif
#endif
