#include "app_state.h"

#include <string.h>
#include <stddef.h>
#include <time.h>
#include <sys/time.h>

#include "esp_attr.h"
#include "esp_log.h"

#include "dusty_config.h"

static const char *TAG = "app_state";

#define APP_STATE_MAGIC 0x44435331u /* "DCS1" */
#define CLOCK_SANE_EPOCH 1577836800 /* 2020-01-01T00:00:00Z */

RTC_DATA_ATTR app_state_t g_state;

/* Small bitwise CRC32 (no table: called at most once or twice a wake, and
 * the struct is well under 2 KB). */
static uint32_t crc32_of(const void *data, size_t n)
{
    const uint8_t *p = (const uint8_t *)data;
    uint32_t crc = 0xFFFFFFFFu;
    for (size_t i = 0; i < n; i++) {
        crc ^= p[i];
        for (int b = 0; b < 8; b++) {
            uint32_t mask = -(crc & 1u);
            crc = (crc >> 1) ^ (0xEDB88320u & mask);
        }
    }
    return ~crc;
}

static uint32_t state_crc(const app_state_t *s)
{
    return crc32_of(s, offsetof(app_state_t, crc));
}

int app_state_load(void)
{
    if (g_state.magic == APP_STATE_MAGIC && g_state.crc == state_crc(&g_state)) {
        return 0; /* warm wake, state intact */
    }

    ESP_LOGI(TAG, "rtc state invalid (magic=0x%08x): cold boot", (unsigned)g_state.magic);
    memset(&g_state, 0, sizeof(g_state));
    g_state.magic = APP_STATE_MAGIC;
    g_state.thumb_valid = 0;
    g_state.wake_n = 0;
    g_state.seq = 0;
    g_state.clock_state = APP_CLOCK_NONE;

    uint32_t boot_count = dusty_nvs_get_u32("boot_count", 0) + 1;
    dusty_nvs_set_u32("boot_count", boot_count);
    ESP_LOGI(TAG, "cold boot, boot_count=%u", (unsigned)boot_count);
    return 1;
}

void app_state_clock_init(void)
{
    time_t now = time(NULL);
    if (now >= (time_t)CLOCK_SANE_EPOCH) {
        /* deep-sleep wake: the RTC timer kept running, clock_state carries
         * over from RTC memory as-is. */
        return;
    }

    uint32_t last_ts = dusty_nvs_get_u32("last_ts", 0);
    if (last_ts) {
        struct timeval tv = { .tv_sec = (time_t)last_ts, .tv_usec = 0 };
        settimeofday(&tv, NULL);
        g_state.clock_state = APP_CLOCK_EST;
        ESP_LOGI(TAG, "clock estimated from NVS last_ts=%u", (unsigned)last_ts);
    } else {
        g_state.clock_state = APP_CLOCK_NONE;
        ESP_LOGW(TAG, "clock unset, no NVS last_ts to estimate from");
    }
}

void app_state_note_frame_time(int64_t ts)
{
    if (ts > 0) dusty_nvs_set_u32("last_ts", (uint32_t)ts);
}

void app_state_save(void)
{
    g_state.magic = APP_STATE_MAGIC;
    g_state.crc = state_crc(&g_state);
}

const char *app_state_clock_str(void)
{
    switch (g_state.clock_state) {
    case APP_CLOCK_SET: return "set";
    case APP_CLOCK_EST:  return "est";
    default:             return "none";
    }
}
