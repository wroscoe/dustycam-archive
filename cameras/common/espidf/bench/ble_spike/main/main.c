/* ble_spike: P0 bench spike for dustyphone (docs/phone_app_plan.md §6 P0,
 * §3 "radio.c"). Throwaway main, real components (dusty_ble, dusty_core,
 * dusty_uplink, dusty_spool, dusty_control). Proves the radio state
 * machine: sequential BLE <-> Wi-Fi with no reboot in between, and that
 * NimBLE actually frees its RAM on dusty_ble_stop() (P0.1a/P0.1b).
 *
 * board.h / camera.c / camera.h are copied verbatim from
 * cameras/xiao_pantilt/software/app/main/ (same physical board -- see
 * those files' own header comments).
 *
 * State machine (docs/phone_app_plan.md §3, P0 form):
 *   boot: nvs init, PSRAM check, log "radio: state=SLEEP" with the heap
 *         table row
 *   loop:
 *     BLE:  dusty_ble_start(hooks); serve until handoff | live |
 *           300 s with no link | link idle 120 s; dusty_ble_stop()
 *           if handoff -> WIFI else -> done
 *     WIFI: dusty_uplink_wifi_join(secrets ssid/pass, 90 s) ->
 *           dusty_control_start(hooks: status_json + ble); serve until
 *           POST /ble | 120 s idle | 600 s; dusty_control_stop();
 *           dusty_uplink_wifi_off() -> back to BLE
 *   done: xc_cam_deinit() if inited; log; esp_deep_sleep 30 s (cold boot
 *         re-enters this whole function -- fine, this is a bench spike)
 *
 * Deliberate P0 simplifications (see the task's deliverable C text and
 * the README "Measured" section for what's left for P1):
 *  - no button, no dusty_led: the LED/SD-CS pin-sharing dance in the real
 *    xiao app's main.c is not exercised here. The SD card is mounted once
 *    at boot and left mounted for the whole run.
 *  - "no link within the BLE window" does not fall back to a button-less
 *    contact the way the real camera does (PLAN.md's `reason !=
 *    PENDING_VERIFY` button path) -- P0 only exercises the phone-driven
 *    handoff.
 *
 * P1 additions (docs/phone_app_plan.md §2, §3, §6 P1 row): dusty_config
 * (ident + tier-2 cfg, replacing the P0 direct-Kconfig ble_key read) wired
 * to `cfg.schema`/`cfg.get`/`cfg.set`/`prov.get`/`prov.set`/`wifi.scan`.
 * The spike has no drain, so `cfg.set` never answers err:"busy". To
 * exercise the unprovisioned/prov.set-in-the-presence-window path on this
 * bench (Kconfig's CONFIG_DUSTY_DEVICE defaults non-empty), erase NVS
 * first (`idf.py erase-flash`) or blank CONFIG_DUSTY_DEVICE in
 * menuconfig before flashing.
 */
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <time.h>
#include <sys/time.h>

#include "esp_log.h"
#include "esp_timer.h"
#include "esp_sleep.h"
#include "esp_system.h"
#include "esp_heap_caps.h"
#include "esp_psram.h"
#include "nvs_flash.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "cJSON.h"

#include "board.h"
#include "camera.h"

#include "dusty_core.h"
#include "dusty_config.h"
#include "dusty_spool.h"
#include "dusty_uplink.h"
#include "dusty_control.h"
#include "dusty_ble.h"

static const char *TAG = "ble_spike";
static const char *TAG_RADIO = "radio";

/* ---------------- shared state ---------------- */

static int s_sd_ok;
static int s_cam_inited;
static const char *s_radio = "sleep"; /* lowercase, echoed in status_json's "radio" field */
static uint32_t s_cycle_n;
static uint32_t s_shoot_seq;
/* Loaded once at boot (dusty_ident_load(), NVS "ident" -> CONFIG_DUSTY_*);
 * dusty_ble_hooks_t.device/.ble_key point into this, so it must outlive
 * every BLE session -- file-scope, not a local in app_main(). */
static dusty_ident_t s_ident;

static volatile int s_handoff_requested;
static char s_handoff_mode[16];
static char s_handoff_ssid[64];
static char s_handoff_pass[64];
static volatile int s_live_requested;
static volatile int s_ble_requested; /* set by the WIFI-phase POST /ble hook */

/* ---------------- heap/state logging (docs/phone_app_plan.md §3: kept
 * permanently, at every transition) ---------------- */

static void radio_log_state(const char *state)
{
    unsigned free_b = (unsigned)heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
    unsigned largest = (unsigned)heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL);
    ESP_LOGI(TAG_RADIO, "state=%s internal_free=%u largest=%u cycle=%u", state, free_b, largest, (unsigned)s_cycle_n);
    heap_caps_print_heap_info(MALLOC_CAP_INTERNAL);
}

/* ---------------- misc helpers ---------------- */

static int hex_nibble(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

/* CONFIG_DUSTY_BLE_KEY is 64 hex chars (32 raw bytes); dusty_ble wants the
 * raw bytes, not the hex text. This is a tiny local decode, not a use of
 * dusty_ble's internal ble_auth helpers (those are private to that
 * component). */
static int hex_decode32(const char *hex, uint8_t *out32)
{
    if (!hex || strlen(hex) != 64) return -1;
    for (int i = 0; i < 32; i++) {
        int hi = hex_nibble(hex[2 * i]);
        int lo = hex_nibble(hex[2 * i + 1]);
        if (hi < 0 || lo < 0) return -1;
        out32[i] = (uint8_t)((hi << 4) | lo);
    }
    return 0;
}

static int mount_sd(void)
{
    dusty_spool_pins_t pins = {
        .cs_gpio = BOARD_SD_CS_GPIO,
        .sck_gpio = BOARD_SD_SCK_GPIO,
        .miso_gpio = BOARD_SD_MISO_GPIO,
        .mosi_gpio = BOARD_SD_MOSI_GPIO,
    };
    dusty_spool_set_pins(&pins);
    return dusty_spool_mount();
}

/* Minimal tier-2 defaults for dusty_config_init() -- the spike has no
 * tuning_defaults.h (that's dustygen's job for the real app); these
 * values only need to be sane enough to round-trip through cfg.get/
 * cfg.set/cfg.schema, not to drive any actual wake-cycle behaviour (the
 * spike has none). */
static dc_cfg_t spike_cfg_defaults(void)
{
    dc_cfg_t c = { 0 };
    c.cfg = 0;
    strlcpy(c.profile, "spike", sizeof(c.profile));
    strlcpy(c.mode, "live", sizeof(c.mode));
    c.period_s = 30;
    c.interval_n = 120;
    c.heartbeat_s = 3600;
    c.diff_min_frac = 0.02f;
    c.diff_l_thresh = 8;
    c.gate_pct = 60;
    c.keep_labels_n = 0;
    c.keep_all = 0;
    c.audit_n = 20;
    c.debug_frames = 0;
    c.debug_max = 500;
    c.upload_cap = 1000;
    c.lum_night = 12;
    c.lum_day = 25;
    c.night_confirm_n = 3;
    c.night_margin_s = 2700;
    c.night_probe_s = 1200;
    c.hotspot_join_s = 90;
    c.contact_idle_s = 120;
    c.setup_secs = 300;
    c.telemetry_s = 60;
    c.led_capture = 0;
    c.spool_max_frames = 20000;
    return c;
}

/* Reads a whole spooled JPEG into a PSRAM buffer. Used by hook_thumb (via
 * a fake camera_fb_t over the buffer -- board.h's camera never has to
 * spin up) and hook_frame (verbatim). */
static int read_spool_jpg(const char *tier, uint32_t boot, uint32_t seq, uint8_t **buf_out, size_t *len_out)
{
    char path[96];
    if (dc_spool_path(path, sizeof(path), "/sd", tier, boot, seq, "jpg") < 0) return 0;
    FILE *f = fopen(path, "rb");
    if (!f) return 0;
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (sz <= 0) {
        fclose(f);
        return 0;
    }
    uint8_t *buf = heap_caps_malloc((size_t)sz, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (!buf) {
        fclose(f);
        return 0;
    }
    size_t got = fread(buf, 1, (size_t)sz, f);
    fclose(f);
    if (got != (size_t)sz) {
        free(buf);
        return 0;
    }
    *buf_out = buf;
    *len_out = (size_t)sz;
    return 1;
}

/* ---------------- dusty_ble / dusty_control shared hooks ---------------- */

static int hook_status_json(char *buf, size_t n)
{
    int r = snprintf(buf, n,
                      "{\"device\":\"%s\",\"v\":\"spike\",\"radio\":\"%s\",\"uptime_s\":%lld,"
                      "\"internal_free\":%u,\"largest\":%u,\"cycle_n\":%u,"
                      "\"cam_inited\":%s,\"sd\":%s}",
                      s_ident.device, s_radio, (long long)(esp_timer_get_time() / 1000000),
                      (unsigned)heap_caps_get_free_size(MALLOC_CAP_INTERNAL),
                      (unsigned)heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL),
                      (unsigned)s_cycle_n, s_cam_inited ? "true" : "false", s_sd_ok ? "true" : "false");
    return (r < 0 || (size_t)r >= n) ? -1 : r;
}

/* preview: lazy xc_cam_init -> cam_capture -> cam_decode(JPG_SCALE_8X) ->
 * cam_preview_jpeg -> data; cam_sharpness_rgb565 for focus, dc_thumb_lum
 * for lum; then cam_release + xc_cam_deinit. ALWAYS deinit (sarg: never
 * init twice without deinit). */
static int hook_preview(uint8_t **jpg, size_t *jpg_len, float *focus, int *lum)
{
    int ok = 0;
    if (xc_cam_init() == ESP_OK) {
        s_cam_inited = 1;
        radio_log_state("BLE+CAM"); /* review finding: log AFTER init succeeds, not before it's even attempted */
        camera_fb_t *fb = cam_capture();
        if (fb) {
            int w = 0, h = 0;
            uint16_t *rgb = cam_decode(fb, JPG_SCALE_8X, &w, &h);
            if (rgb) {
                uint8_t *out = NULL;
                size_t out_len = 0;
                if (cam_preview_jpeg(rgb, &out, &out_len)) {
                    int cw = 100, ch = 75;
                    *focus = cam_sharpness_rgb565(rgb, w, h, (w - cw) / 2, (h - ch) / 2, cw, ch);
                    dc_thumb_t thumb;
                    dc_thumb_from_rgb565(rgb, w, h, &thumb);
                    *lum = dc_thumb_lum(&thumb);
                    *jpg = out;
                    *jpg_len = out_len;
                    ok = 1;
                }
                free(rgb);
            }
            cam_release(fb);
        }
        xc_cam_deinit();
        s_cam_inited = 0;
    }
    radio_log_state("BLE");
    return ok;
}

/* thumb: read the spooled JPEG, decode 1/8 through the SAME cam_decode()
 * path preview uses -- cam_decode only reads fb->buf/fb->len, so a
 * zero-initialised camera_fb_t over the file buffer stands in for a real
 * capture with no sensor involved. */
static int hook_thumb(uint32_t boot, uint32_t seq, uint8_t **jpg, size_t *jpg_len)
{
    if (!s_sd_ok) return 0;
    uint8_t *filebuf;
    size_t filelen;
    if (!read_spool_jpg("spool", boot, seq, &filebuf, &filelen)) return 0;

    camera_fb_t fake;
    memset(&fake, 0, sizeof(fake));
    fake.buf = filebuf;
    fake.len = filelen;

    int w = 0, h = 0;
    uint16_t *rgb = cam_decode(&fake, JPG_SCALE_8X, &w, &h);
    free(filebuf);
    if (!rgb) return 0;

    uint8_t *out = NULL;
    size_t out_len = 0;
    int ok = cam_preview_jpeg(rgb, &out, &out_len);
    free(rgb);
    if (!ok) return 0;
    *jpg = out;
    *jpg_len = out_len;
    return 1;
}

static int hook_frame(uint32_t boot, uint32_t seq, uint8_t **jpg, size_t *jpg_len)
{
    if (!s_sd_ok) return 0;
    return read_spool_jpg("spool", boot, seq, jpg, jpg_len);
}

/* bench: the standard's contact_idle_s is 120; a person tapping buttons needs more slack */
#define BENCH_IDLE_S 600
#define SPOOL_LIST_SCAN_CAP 512

static int hook_spool_list(const char *req_json, char *out, size_t cap)
{
    if (!s_sd_ok) {
        int n = snprintf(out, cap, "{\"items\":[],\"more\":false}");
        return n;
    }

    int n_req = 24;
    cJSON *req = cJSON_Parse(req_json);
    if (req) {
        cJSON *nj = cJSON_GetObjectItemCaseSensitive(req, "n");
        if (cJSON_IsNumber(nj)) n_req = (int)nj->valuedouble;
        cJSON_Delete(req);
    }
    if (n_req <= 0 || n_req > 64) n_req = 24;

    static dusty_spool_entry_t entries[SPOOL_LIST_SCAN_CAP]; /* static: this runs on the 6 KB ble_req stack */
    int total = dusty_spool_scan("spool", entries, SPOOL_LIST_SCAN_CAP);
    int n = total > SPOOL_LIST_SCAN_CAP ? SPOOL_LIST_SCAN_CAP : total;
    dusty_spool_sort_desc(entries, n);
    int shown = n < n_req ? n : n_req;

    size_t off = 0;
    int w = snprintf(out + off, cap - off, "{\"items\":[");
    off += (w > 0) ? (size_t)w : 0;
    for (int i = 0; i < shown && off < cap; i++) {
        w = snprintf(out + off, cap - off, "%s{\"boot\":%u,\"seq\":%u,\"score\":%.2f,\"why\":\"%s\"}",
                     i ? "," : "", (unsigned)entries[i].boot, (unsigned)entries[i].seq,
                     (double)entries[i].score, entries[i].why);
        off += (w > 0) ? (size_t)w : 0;
    }
    w = snprintf(out + off, cap - off, "],\"more\":%s}", (n > shown) ? "true" : "false");
    off += (w > 0) ? (size_t)w : 0;
    return (int)off;
}

/* shoot: lazy init, capture UXGA, write straight to the spool via
 * dusty_spool_write (it writes the sidecar + jpg pair dusty_spool_scan
 * expects -- see dusty_spool.h; no need for a raw fwrite fallback). */
static void hook_shoot(void)
{
    if (xc_cam_init() == ESP_OK) {
        s_cam_inited = 1;
        radio_log_state("BLE+CAM"); /* review finding: log AFTER init succeeds, not before it's even attempted */
        camera_fb_t *fb = cam_capture();
        if (fb) {
            if (s_sd_ok) {
                uint32_t boot = 0; /* the spike has no boot counter (no app_state/NVS identity yet) */
                uint32_t seq = s_shoot_seq++;
                dc_meta_t m;
                memset(&m, 0, sizeof(m));
                m.ts = (int64_t)time(NULL);
                m.seq = seq;
                m.w = (int)fb->width;
                m.h = (int)fb->height;
                m.v = "spike";
                m.cfg = 0;
                m.ip = "0.0.0.0";
                m.mode = s_radio;
                m.why = "manual";
                m.diff = 0.0f;
                m.gate = 0.0f;
                m.buffered = 1;
                m.lum = 0;
                m.clock = "none";
                m.score = 0.0f;
                m.night_s = -1;
                char meta[512];
                int mn = dc_meta_build(meta, sizeof(meta), &m);
                if (mn > 0) {
                    if (!dusty_spool_write("spool", boot, seq, fb->buf, fb->len, meta)) {
                        ESP_LOGW(TAG, "shoot: spool write failed");
                    }
                } else {
                    ESP_LOGW(TAG, "shoot: meta build overflowed");
                }
            }
            cam_release(fb);
        } else {
            ESP_LOGW(TAG, "shoot: capture failed");
        }
        xc_cam_deinit();
        s_cam_inited = 0;
    } else {
        ESP_LOGW(TAG, "shoot: xc_cam_init failed");
    }
    radio_log_state("BLE");
}

/* handoff: only RECORDS the request (docs/phone_app_plan.md §3); the
 * radio loop below performs it once dusty_ble_stop() has returned. */
static void hook_handoff(const char *mode, const char *ssid, const char *pass)
{
    strlcpy(s_handoff_mode, mode ? mode : "view", sizeof(s_handoff_mode));
    strlcpy(s_handoff_ssid, ssid ? ssid : "", sizeof(s_handoff_ssid));
    strlcpy(s_handoff_pass, pass ? pass : "", sizeof(s_handoff_pass));
    s_handoff_requested = 1;
    ESP_LOGI(TAG, "handoff requested: mode=%s ssid=%s", s_handoff_mode, s_handoff_ssid[0] ? s_handoff_ssid : "(secrets)");
}

static void hook_live(void)
{
    s_live_requested = 1;
}

/* Side-effect-free (docs/phone_app_plan.md: dusty_ble.h's last_ip hook
 * comment) -- lets `wifi.up`/`contact`'s reply carry a real expect_ip on
 * cycle 2+ instead of always "" (review finding). dusty_uplink_ip()
 * returns "0.0.0.0" once wifi_off() has run; the app only cares about a
 * real address, so that's treated the same as "none yet". */
static const char *hook_last_ip(void)
{
    const char *ip = dusty_uplink_ip();
    return (ip && strcmp(ip, "0.0.0.0") != 0) ? ip : "";
}

static void hook_time_set(int64_t ts, int tz_min)
{
    (void)tz_min;
    struct timeval tv = { .tv_sec = (time_t)ts, .tv_usec = 0 };
    settimeofday(&tv, NULL);
    ESP_LOGI(TAG, "time_set: ts=%lld", (long long)ts);
}

/* WIFI-phase dusty_control hook: POST /ble -- end the WIFI phase now. */
static void hook_ble(void)
{
    s_ble_requested = 1;
}

/* ---------------- P1: cfg / prov / wifi.scan hooks ---------------- */

/* Small hard-coded schema for the spike (docs/phone_app_plan.md §6 P1:
 * "schema = a small hard-coded schema JSON for the spike"; the real app
 * uses dustygen's generated tuning_schema.h -- see
 * cameras/xiao_pantilt/software/app/main/tuning_schema.h). One key of
 * each of the five §2 types (int/float/bool/str/list) so cfg.set can be
 * exercised against all of them. */
static const char SPIKE_SCHEMA_JSON[] =
    "{\"id\":\"ble_spike\",\"camera\":\"ble_spike\",\"keys\":["
    "{\"name\":\"period_s\",\"type\":\"int\",\"default\":30,\"help\":\"wake interval\"},"
    "{\"name\":\"diff_min_frac\",\"type\":\"float\",\"default\":0.02,\"help\":\"\"},"
    "{\"name\":\"keep_all\",\"type\":\"bool\",\"default\":false,\"help\":\"keep frames the model rejects\"},"
    "{\"name\":\"mode\",\"type\":\"str\",\"default\":\"live\",\"help\":\"live | setup\"},"
    "{\"name\":\"keep_labels\",\"type\":\"list\",\"default\":[\"animal\",\"person\"],\"help\":\"\"}"
    "]}";

static int hook_cfg_schema(char *buf, size_t n)
{
    size_t len = strlen(SPIKE_SCHEMA_JSON);
    if (len >= n) return -1;
    memcpy(buf, SPIKE_SCHEMA_JSON, len + 1);
    return (int)len;
}

static int hook_cfg_get(char *buf, size_t n)
{
    const dc_cfg_t *cfg = dusty_config_get();
    if (!cfg) return -1;
    return dc_cfg_to_json(cfg, buf, n);
}

static int hook_cfg_set(const char *json, int *out_cfg)
{
    /* The spike has no drain (no contact_run), so there is never a "busy"
     * (-1) case here -- only 1 (applied) or 0 (parse error). */
    int rc = dusty_config_set_local(json);
    if (rc < 0) return 0;
    *out_cfg = rc;
    return 1;
}

static int hook_prov_get(char *buf, size_t n)
{
    dusty_ident_t id;
    dusty_ident_load(&id);
    int r = snprintf(buf, n, "{\"device\":\"%s\",\"host\":\"%s\",\"port\":%d,\"tls\":%s,\"ssid\":\"%s\"}",
                      id.device, id.host, id.port, id.tls ? "true" : "false", id.ssid);
    return (r > 0 && (size_t)r < n) ? r : -1;
}

/* `json` is already plaintext (dusty_ble.c has either accepted the
 * presence-window body as-is or decrypted the `env` envelope) --
 * {device,ssid,pass,host,port,tls,token,ble_key}. Starts from the
 * currently-loaded ident so a partial edit (e.g. just device+ble_key on
 * first provisioning, matching decision 7) doesn't blank the rest. */
static int hook_prov_set(const char *json, char *device_out, size_t device_out_cap)
{
    cJSON *root = cJSON_Parse(json);
    if (!root) return 0;

    dusty_ident_t id;
    dusty_ident_load(&id);

    cJSON *j;
    j = cJSON_GetObjectItemCaseSensitive(root, "device");
    if (cJSON_IsString(j) && j->valuestring[0]) strlcpy(id.device, j->valuestring, sizeof(id.device));
    j = cJSON_GetObjectItemCaseSensitive(root, "ssid");
    if (cJSON_IsString(j)) strlcpy(id.ssid, j->valuestring, sizeof(id.ssid));
    j = cJSON_GetObjectItemCaseSensitive(root, "pass");
    if (cJSON_IsString(j)) strlcpy(id.pass, j->valuestring, sizeof(id.pass));
    j = cJSON_GetObjectItemCaseSensitive(root, "host");
    if (cJSON_IsString(j)) strlcpy(id.host, j->valuestring, sizeof(id.host));
    j = cJSON_GetObjectItemCaseSensitive(root, "port");
    if (cJSON_IsNumber(j)) id.port = (int)j->valuedouble;
    j = cJSON_GetObjectItemCaseSensitive(root, "tls");
    if (cJSON_IsBool(j)) id.tls = cJSON_IsTrue(j) ? 1 : 0;
    j = cJSON_GetObjectItemCaseSensitive(root, "token");
    if (cJSON_IsString(j)) strlcpy(id.token, j->valuestring, sizeof(id.token));
    j = cJSON_GetObjectItemCaseSensitive(root, "ble_key");
    if (cJSON_IsString(j) && hex_decode32(j->valuestring, id.ble_key) == 0) id.ble_key_len = 32;
    cJSON_Delete(root);

    if (!id.device[0]) return 0; /* device is mandatory -- it is the identity */

    dusty_ident_save(&id);
    strlcpy(device_out, id.device, device_out_cap);
    return 1;
}

static int hook_wifi_scan(char *buf, size_t n)
{
    unsigned free_before = (unsigned)heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
    dusty_wifi_ap_t aps[10];
    int count = dusty_uplink_wifi_scan(aps, 10);
    unsigned free_after = (unsigned)heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
    ESP_LOGI(TAG, "wifi_scan: %d AP(s), internal_free before=%u after=%u (delta=%d) -- BLE stayed up throughout",
             count, free_before, free_after, (int)free_before - (int)free_after);

    size_t off = 0;
    int w = snprintf(buf + off, n - off, "{\"aps\":[");
    off += (w > 0) ? (size_t)w : 0;
    for (int i = 0; i < count && off < n; i++) {
        /* SSIDs are not JSON-escaped -- acceptable for a bench tool; a
         * quote/backslash in an SSID would produce invalid JSON here. */
        w = snprintf(buf + off, n - off, "%s{\"ssid\":\"%s\",\"rssi\":%d,\"ch\":%d}",
                     i ? "," : "", aps[i].ssid, aps[i].rssi, aps[i].ch);
        off += (w > 0) ? (size_t)w : 0;
    }
    w = snprintf(buf + off, n - off, "]}");
    off += (w > 0) ? (size_t)w : 0;
    return (int)off;
}

/* ---------------- app_main ---------------- */

void app_main(void)
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        err = nvs_flash_init();
    }
    if (err != ESP_OK) ESP_LOGE(TAG, "nvs_flash_init: 0x%x", err);

    /* CONFIG_LOG_DEFAULT_LEVEL_WARN is set (the sdkconfig diet); the
     * "radio" tag is re-enabled at INFO so its heap line survives that. */
    esp_log_level_set(TAG_RADIO, ESP_LOG_INFO);
    /* bench: the link-layer story must be visible on the serial console */
    esp_log_level_set(TAG, ESP_LOG_INFO);
    esp_log_level_set("dusty_ble", ESP_LOG_INFO);
    esp_log_level_set("NimBLE", ESP_LOG_INFO);
    esp_log_level_set("dusty_uplink", ESP_LOG_INFO);
    esp_log_level_set("dusty_control", ESP_LOG_INFO);
    esp_log_level_set("dusty_spool", ESP_LOG_INFO);

    bool psram_ok = esp_psram_is_initialized();
    ESP_LOGI(TAG, "psram: %s", psram_ok ? "ok" : "MISSING");

    s_sd_ok = mount_sd();
    if (s_sd_ok) {
        ESP_LOGI(TAG, "sd mount: ok");
    } else {
        /* Not fatal -- keep going with no card (bench review finding):
         * spool.list answers an empty {"items":[],"more":false}, shoot is
         * a no-op (logged separately), and thumb/frame answer err:"nofile"
         * (dusty_ble's contract has no separate "no card" signal from
         * "file not found" -- both come from the same hook returning 0). */
        ESP_LOGI(TAG, "sd: not mounted (thumb/frame will answer err:\"nofile\", spool.list an empty list, shoot a no-op)");
    }

    /* P1: identity (NVS "ident" -> CONFIG_DUSTY_*, dusty_config.h) replaces
     * the P0 direct Kconfig-hex-decode. File-scope: dusty_ble_hooks_t's
     * device/ble_key point into it, so it must outlive this function. */
    dusty_ident_load(&s_ident);
    ESP_LOGI(TAG, "ident: device=\"%s\" host=\"%s\" ssid=\"%s\" provisioned=%d ble_key_len=%d",
             s_ident.device, s_ident.host, s_ident.ssid, dusty_ident_is_provisioned(&s_ident), s_ident.ble_key_len);

    dc_cfg_t cfg_defaults = spike_cfg_defaults();
    dusty_config_init(&cfg_defaults);

    dusty_ble_hooks_t ble_hooks = {
        .ble_key = s_ident.ble_key_len == DUSTY_IDENT_BLE_KEY_LEN ? s_ident.ble_key : NULL,
        .device = s_ident.device,
        .fw_version = "spike",
        .status_json = hook_status_json,
        .preview = hook_preview,
        .thumb = hook_thumb,
        .frame = hook_frame,
        .spool_list = hook_spool_list,
        .shoot = hook_shoot,
        .handoff = hook_handoff,
        .last_ip = hook_last_ip,
        .live = hook_live,
        .time_set = hook_time_set,
        .cfg_schema = hook_cfg_schema,
        .cfg_get = hook_cfg_get,
        .cfg_set = hook_cfg_set,
        .prov_get = hook_prov_get,
        .prov_set = hook_prov_set,
        .wifi_scan = hook_wifi_scan,
    };

    s_radio = "sleep";
    radio_log_state("SLEEP");

    for (;;) {
        /* ---------------- BLE phase ---------------- */
        s_radio = "ble";
        s_handoff_requested = 0;
        s_live_requested = 0;
        dusty_ble_start(&ble_hooks);

        int64_t ble_start_us = esp_timer_get_time();
        int had_link = 0;
        int logged_ble_up = 0;
        for (;;) {
            vTaskDelay(pdMS_TO_TICKS(200));
            if (!logged_ble_up && esp_timer_get_time() - ble_start_us >= 1LL * 1000000) {
                /* review finding: log once advertising is actually up
                 * (post on_sync), not at the instant dusty_ble_start() was
                 * called -- gate P0.1a's "internal free with NimBLE up"
                 * row needs the post-init number. */
                radio_log_state("BLE");
                logged_ble_up = 1;
            }
            if (s_handoff_requested || s_live_requested) break;
            if (dusty_ble_connected()) had_link = 1;

            int64_t now = esp_timer_get_time();
            int64_t last_req_us = dusty_ble_last_request_us();
            int64_t idle_us = now - (last_req_us > 0 ? last_req_us : ble_start_us);

            if (!had_link && (now - ble_start_us) >= 300LL * 1000000) {
                ESP_LOGI(TAG, "ble: 300s with no link, giving up");
                break;
            }
            if (had_link && idle_us >= BENCH_IDLE_S * 1000000LL) {
                ESP_LOGI(TAG, "ble: link idle %ds, ending window", (int)BENCH_IDLE_S);
                break;
            }
        }
        dusty_ble_stop();

        if (s_live_requested) {
            ESP_LOGI(TAG, "live requested: ending run");
            break; /* -> done */
        }
        if (!s_handoff_requested) {
            /* No button/config path in this spike (see the file header):
             * a BLE window that ends with no handoff just ends the run. */
            break; /* -> done */
        }

        /* ---------------- WIFI phase ---------------- */
        s_radio = "wifi";

        const char *ssid = s_handoff_ssid[0] ? s_handoff_ssid : s_ident.ssid;
        const char *pass = s_handoff_ssid[0] ? s_handoff_pass : s_ident.pass;
        int joined = dusty_uplink_wifi_join(ssid, pass, 90);
        if (!joined) {
            ESP_LOGW(TAG, "wifi: join failed within 90s");
        } else {
            /* review finding: log AFTER the join succeeds (not before
             * attempting it), and again once the control-plane httpd is
             * actually up. */
            radio_log_state("WIFI");
            s_ble_requested = 0;
            dusty_control_hooks_t control_hooks = {
                .status_json = hook_status_json,
                .ble = hook_ble,
                .device = s_ident.device, /* enables the UDP discovery beacon (dusty_control.h) */
            };
            dusty_control_start(&control_hooks);
            radio_log_state("WIFI+HTTP");

            int64_t wifi_start_us = esp_timer_get_time();
            for (;;) {
                vTaskDelay(pdMS_TO_TICKS(200));
                if (s_ble_requested) break;
                int64_t now = esp_timer_get_time();
                /* idle origin = the later of the last HTTP request and the
                 * phase start: last_request_us is 0 (or stale from the
                 * previous phase) until a request arrives, which ended
                 * cycle 1's Wi-Fi phase 300 ms after it began (bench,
                 * 2026-09-15). */
                int64_t last_http_us = dusty_control_last_request_us();
                int64_t idle_origin_us = last_http_us > wifi_start_us ? last_http_us : wifi_start_us;
                if (now - idle_origin_us >= BENCH_IDLE_S * 1000000LL) {
                    ESP_LOGI(TAG, "wifi: %ds idle, ending phase", (int)BENCH_IDLE_S);
                    break;
                }
                if (now - wifi_start_us >= 600LL * 1000000) {
                    ESP_LOGI(TAG, "wifi: 600s cap reached, ending phase");
                    break;
                }
            }
            dusty_control_stop();
        }
        dusty_uplink_wifi_off();
        s_cycle_n++;
        /* -> back to BLE */
    }

    /* ---------------- done ---------------- */
    s_radio = "sleep";
    if (s_cam_inited) {
        xc_cam_deinit();
        s_cam_inited = 0;
    }
    radio_log_state("SLEEP");
    ESP_LOGI(TAG, "done after %u cycle(s); deep-sleeping 30s (cold boot re-enters the loop)", (unsigned)s_cycle_n);

    if (s_sd_ok) dusty_spool_unmount();
    esp_sleep_enable_timer_wakeup(30LL * 1000000);
    esp_deep_sleep_start();
}
