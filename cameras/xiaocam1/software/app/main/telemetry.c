#include "telemetry.h"

#include <stdio.h>

#include "esp_system.h"
#include "esp_timer.h"

#include "app_state.h"
#include "dusty_config.h"
#include "dusty_uplink.h"

int telemetry_build(char *buf, size_t n, int mode, const telemetry_extra_t *extra)
{
    static const telemetry_extra_t zero = { 0 };
    if (!extra) extra = &zero;

    const dc_cfg_t *cfg = dusty_config_get();
    int64_t uptime_s = esp_timer_get_time() / 1000000;
    uint32_t mem_free = esp_get_free_heap_size();
    int rssi = dusty_uplink_rssi();
    uint32_t boot_count = dusty_nvs_get_u32("boot_count", 0);

    int r = snprintf(buf, n,
        "{"
        "\"uptime_s\":%lld,"
        "\"mem_free\":%u,"
        "\"rssi\":%d,"
        "\"frames_sent\":%d,"
        "\"frames_skipped\":%d,"
        "\"upload_failures\":%d,"
        "\"pending_files\":%d,"
        "\"pending_cold\":%d,"
        "\"mode\":%d,"
        "\"cfg\":%d,"
        "\"boot_count\":%u,"
        "\"lum\":%d,"
        "\"night\":%d,"
        "\"clock_skew_s\":%d,"
        "\"contact_n\":%d,"
        "\"debug_pending\":%d,"
        "\"crash_n\":%u,"
        "\"reset_reason\":%d"
        "}",
        (long long)uptime_s,
        (unsigned)mem_free,
        rssi,
        extra->frames_sent,
        extra->frames_skipped,
        extra->upload_failures,
        extra->pending_files,
        extra->pending_cold,
        mode,
        cfg ? cfg->cfg : 0,
        (unsigned)boot_count,
        g_state.last_lum,
        g_state.night.in_night,
        extra->clock_skew_s,
        extra->contact_n,
        extra->debug_pending,
        (unsigned)dusty_nvs_get_u32("crash_n", 0),
        (int)esp_reset_reason());

    if (r < 0 || (size_t)r >= n) return -1;
    return r;
}
