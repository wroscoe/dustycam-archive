#include "contact.h"

#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>
#include <time.h>

#include "esp_log.h"
#include "esp_timer.h"
#include "esp_heap_caps.h"
#include "esp_random.h"
#include "esp_system.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"

#include "cJSON.h"

#include "board.h"
#include "app_state.h"
#include "camera.h"
#include "record.h"
#include "telemetry.h"
#include "dusty_core.h"
#include "dusty_uplink.h"
#include "dusty_spool.h"
#include "dusty_config.h"
#include "dusty_ota.h"
#include "dusty_led.h"
#include "dusty_control.h"
#include "crashdbg.h"

#if __has_include("tuning_schema.h")
#include "tuning_schema.h"
#endif

static const char *TAG = "contact";

#define SPOOL_SCAN_CAP 4096
#define SPOOL_LIST_CAP 512

/* ---------------- shared state for the control-plane hooks ----------------
 * dusty_control's/dusty_ble's hooks are plain function pointers with no
 * user-data, so the state they need lives here at file scope; contact_run()
 * is never reentrant, and the dusty_ble hooks table below (used from the
 * BLE phase) shares this same state with the HTTP hooks table (used from
 * the WIFI phase) -- the two radios are never up together, so there is no
 * actual concurrency between them (docs/phone_app_plan.md decision 9). */
static telemetry_extra_t s_tel;
static volatile int s_live_requested;
static volatile int s_ble_requested; /* POST /ble (WIFI phase only) */
static camera_fb_t *s_stream_fb;
static float s_last_focus;
static float s_focus_best;
static volatile int s_draining; /* true while drain_tier() is running: cfg.set answers err:"busy" */

/* Radio-state fields for GET /status (docs/phone_app_plan.md §2), set by
 * radio.c via contact_set_radio_state() before each phase. "contact_mode"
 * (view|contact), not "mode": dc_cfg_t already has a tier-2 "mode"
 * (live|setup) in this same JSON object, and duplicating that key would
 * make the JSON ambiguous. */
static const char *s_radio_phase = "wifi";
static const char *s_contact_mode = "contact";
/* Review finding (MINOR): these used to be plain seconds-remaining
 * snapshots, taken once when radio.c entered a phase and never updated
 * again -- so a GET /status polled mid-phase saw a frozen win_left_s and
 * an always-0 ble_back_in_s (nothing ever passed a nonzero value in).
 * Store absolute deadlines instead and compute the live countdown in
 * status_json_hook() below. 0 means "no active countdown" (reported as
 * 0 s remaining). */
static int64_t s_win_deadline_us;
static int64_t s_ble_back_deadline_us;

/* handoff request recorded by the BLE `wifi.up`/`contact` op, consumed by
 * radio.c after dusty_ble_stop() returns. */
static volatile int s_handoff_pending;
static char s_handoff_mode[16];
static char s_handoff_ssid[64];
static char s_handoff_pass[64];

void contact_set_radio_state(const char *radio, const char *contact_mode, int ble_back_in_s, int win_left_s)
{
    s_radio_phase = radio ? radio : "wifi";
    s_contact_mode = contact_mode ? contact_mode : "contact";
    int64_t now = esp_timer_get_time();
    s_ble_back_deadline_us = ble_back_in_s > 0 ? now + (int64_t)ble_back_in_s * 1000000 : 0;
    s_win_deadline_us = win_left_s > 0 ? now + (int64_t)win_left_s * 1000000 : 0;
}

/* Live seconds-remaining for GET /status, computed from the deadlines
 * contact_set_radio_state() (and, for ble_back, ble_hook() below) stashed
 * -- never frozen at the value seen when the phase started. */
static int radio_seconds_left(int64_t deadline_us)
{
    if (deadline_us <= 0) return 0;
    int64_t left = (deadline_us - esp_timer_get_time()) / 1000000;
    return left > 0 ? (int)left : 0;
}

int contact_take_live(void)
{
    int v = s_live_requested;
    s_live_requested = 0;
    return v;
}

int contact_take_handoff(char *mode_out, size_t mode_cap, char *ssid_out, size_t ssid_cap, char *pass_out, size_t pass_cap)
{
    if (!s_handoff_pending) return 0;
    s_handoff_pending = 0;
    if (mode_out) strlcpy(mode_out, s_handoff_mode, mode_cap);
    if (ssid_out) strlcpy(ssid_out, s_handoff_ssid, ssid_cap);
    if (pass_out) strlcpy(pass_out, s_handoff_pass, pass_cap);
    return 1;
}

/* The LED pin is the SD chip select (PLAN.md §7): the card is mounted only
 * while it is needed (drain, reclaim) and the LED language is shown in
 * between. Both helpers are idempotent. */
static int sd_take(void)
{
    if (dusty_spool_mounted()) return 1;
    dusty_led_suspend();
    if (!dusty_spool_mount()) {
        dusty_led_resume();
        return 0;
    }
    return 1;
}

static void sd_give(void)
{
    if (!dusty_spool_mounted()) return;
    dusty_spool_unmount();
    dusty_led_resume();
}

/* Working buffers for contact_run_contact() and drain_tier(), in PSRAM
 * instead of on the main task's stack: that call chain (contact -> drain ->
 * dusty_uplink_post_file -> TLS) overflowed the old 12 KB main stack on
 * every upload (docs/phone_app_status.md, 2026-09-16). Allocated once and
 * kept; both functions only ever run on the main task, never re-entrantly. */
#define CONTACT_BUF 1024
static struct {
    char cfg[CONTACT_BUF];       /* GET /config body */
    char live[CONTACT_BUF];      /* local config JSON for the push */
    char push_resp[CONTACT_BUF]; /* POST /config response (409 body) */
    char meta[CONTACT_BUF];      /* drain_tier(): one frame's sidecar */
} *s_cbuf;

static int contact_bufs_ready(void)
{
    if (!s_cbuf) s_cbuf = heap_caps_calloc(1, sizeof(*s_cbuf), MALLOC_CAP_SPIRAM);
    return s_cbuf != NULL;
}

static void count_pending(void)
{
    int had = dusty_spool_mounted();
    if (!had && !sd_take()) return;
    s_tel.pending_cold = dusty_spool_count("spool");
    s_tel.debug_pending = dusty_spool_count("debug");
    s_tel.pending_files = s_tel.pending_cold + s_tel.debug_pending;
    if (!had) sd_give();
}

/* Review finding (MAJOR): main.c runs radio_window_run() BEFORE
 * dusty_spool_mount() during a button-press or cold-boot window (the
 * announce/drain mount happens later, inside contact_run_contact()), so
 * a BLE-phase thumb/frame/spool_list/shoot call that only checked
 * dusty_spool_mounted() would report "no card" even when one is present
 * and perfectly mountable. Generalises count_pending()'s take/give
 * idiom above so any hook can safely lazy-mount for its own duration
 * without disturbing an SD session main.c's wake cycle or drain_tier()
 * already holds -- `*had_out` records whether the card was already up so
 * sd_finish() only unmounts what this call itself mounted. */
static int sd_ensure(int *had_out)
{
    int had = dusty_spool_mounted();
    if (had_out) *had_out = had;
    return had ? 1 : sd_take();
}

static void sd_finish(int had)
{
    if (!had) sd_give();
}

/* Review finding (MAJOR): same take/give ownership idea, for the camera
 * sensor. contact.c's hooks used to assume main.c's wake cycle had
 * always already called xc_cam_init() before radio_window_run() -- true
 * for a live-mode wake, not for the button/cold-boot window this same
 * review moved xc_cam_init() to run AFTER (see main.c). A hook that needs
 * the sensor now lazy-inits it if it isn't up yet, and only deinits what
 * it itself inited -- never a double init (the sarg SCCB lesson: P0 ran
 * 40+ init/deinit cycles on this exact board with no hang, so a lazy
 * init/deinit *pair* per hook call is fine; it's re-init-without-deinit
 * that wedges the bus) and never tears down a session another caller
 * still owns. */
static int cam_ensure(int *had_out)
{
    int had = xc_cam_inited();
    if (had_out) *had_out = had;
    if (had) return 1;
    return xc_cam_init() == ESP_OK;
}

static void cam_finish(int had)
{
    if (!had) xc_cam_deinit();
}

static int send_telemetry(int mode)
{
    char buf[512];
    int n = telemetry_build(buf, sizeof(buf), mode, &s_tel);
    if (n < 0) {
        ESP_LOGW(TAG, "telemetry_build overflowed");
        return 0;
    }
    return dusty_uplink_post_telemetry(buf);
}

static float compute_focus_from_fb(camera_fb_t *fb)
{
    int w, h;
    uint16_t *rgb = cam_decode(fb, JPG_SCALE_8X, &w, &h);
    if (!rgb) return 0.0f;
    int cw = 100, ch = 75;
    int x0 = (w - cw) / 2, y0 = (h - ch) / 2;
    float s = cam_sharpness_rgb565(rgb, w, h, x0, y0, cw, ch);
    free(rgb);
    return s;
}

/* ---------------- control hooks (shared by dusty_control and dusty_ble) ---------------- */

static int status_json_hook(char *buf, size_t n)
{
    const dc_cfg_t *cfg = dusty_config_get();
    uint32_t boot_count = dusty_nvs_get_u32("boot_count", 0);
    uint32_t night_pred = dc_night_predict(&g_state.night);
    dusty_ident_t id;
    dusty_ident_load(&id);

    int r = snprintf(buf, n,
        "{\"device\":\"%s\",\"v\":\"%s\",\"cfg\":%d,\"mode\":\"%s\","
        "\"radio\":\"%s\",\"contact_mode\":\"%s\",\"ble_back_in_s\":%d,\"win_left_s\":%d,"
        "\"cfg_src\":\"%s\",\"cfg_base\":%d,"
        "\"uptime_s\":%lld,\"ip\":\"%s\",\"rssi\":%d,"
        "\"pending\":%d,\"pending_debug\":%d,"
        "\"night\":%d,\"night_len_pred\":%u,"
        "\"clock\":\"%s\",\"clock_skew_s\":%d,"
        "\"lum\":%d,\"focus\":%.1f,\"focus_best\":%.1f,"
        "\"sent\":%d,\"failed\":%d,\"seq\":%u,\"boot_count\":%u,"
        "\"crash_n\":%u,\"reset_reason\":%d,"
        "\"drain\":{\"sent\":%d,\"pending\":%d,\"failed\":%d}}",
        id.device, dusty_ota_running_version(), cfg ? cfg->cfg : 0,
        cfg ? cfg->mode : "live",
        s_radio_phase, s_contact_mode,
        radio_seconds_left(s_ble_back_deadline_us), radio_seconds_left(s_win_deadline_us),
        dusty_config_cfg_src(), dusty_config_cfg_base(),
        (long long)(esp_timer_get_time() / 1000000),
        dusty_uplink_ip(), dusty_uplink_rssi(),
        s_tel.pending_cold, s_tel.debug_pending,
        g_state.night.in_night, (unsigned)night_pred,
        app_state_clock_str(), s_tel.clock_skew_s,
        g_state.last_lum, s_last_focus, s_focus_best,
        s_tel.frames_sent, s_tel.upload_failures,
        (unsigned)g_state.seq, (unsigned)boot_count,
        (unsigned)dusty_nvs_get_u32("crash_n", 0), (int)esp_reset_reason(),
        s_tel.frames_sent, s_tel.pending_files, s_tel.upload_failures);
    return (r < 0 || (size_t)r >= n) ? -1 : r;
}

static int stream_frame_hook(uint8_t **jpg, size_t *n)
{
    camera_fb_t *fb = cam_capture();
    if (!fb) return 0;
    s_stream_fb = fb;
    s_last_focus = compute_focus_from_fb(fb);
    if (s_last_focus > s_focus_best) s_focus_best = s_last_focus;
    *jpg = fb->buf;
    *n = fb->len;
    return 1;
}

static void stream_release_hook(void)
{
    if (s_stream_fb) {
        cam_release(s_stream_fb);
        s_stream_fb = NULL;
    }
}

static void shoot_hook(void)
{
    /* Review finding (MAJOR, camera lifecycle): a BLE-phase `shoot`
     * (dusty_ble hook) can run before anything else has opened the
     * camera -- the WIFI-phase path (dusty_control hook) already finds
     * it open via contact_run_contact()'s session-level cam_ensure(), so
     * this is a no-op there (cam_had=1). */
    int cam_had;
    if (!cam_ensure(&cam_had)) {
        ESP_LOGW(TAG, "shoot: camera init failed");
        return;
    }
    camera_fb_t *fb = cam_capture();
    if (!fb) {
        ESP_LOGW(TAG, "shoot: capture failed");
        cam_finish(cam_had);
        return;
    }

    record_req_t req = { 0 };
    req.fb = fb;
    req.thumb = NULL;
    req.lum = g_state.last_lum;
    req.diff = 0.0f;
    req.jr = NULL;
    req.why = "manual";
    req.mode = "contact";
    req.night_s = -1;
    req.update_motion_ref = 0;
    req.sharpness = compute_focus_from_fb(fb);

    /* Deliver now, straight from the frame buffer, if we're on Wi-Fi with
     * a server to talk to; a BLE-phase shoot (no uplink) always spools. */
    char meta[768];
    int n = record_build_meta(&req, g_state.seq, meta, sizeof(meta));
    if (strcmp(s_radio_phase, "wifi") == 0 && n > 0 && dusty_uplink_post_blob("frame", fb->buf, fb->len, meta)) {
        g_state.seq++;
        s_tel.frames_sent++;
        app_state_note_frame_time((int64_t)time(NULL));
        ESP_LOGI(TAG, "shoot: uploaded (seq %u)", (unsigned)(g_state.seq - 1));
    } else {
        int had;
        if (sd_ensure(&had) && record_frame(&req, NULL)) {
            ESP_LOGI(TAG, "shoot: spooled for the next drain");
        } else {
            s_tel.upload_failures++;
            ESP_LOGW(TAG, "shoot: upload failed and could not spool, frame dropped");
        }
        sd_finish(had);
    }
    cam_release(fb);
    cam_finish(cam_had);
}

static void refresh_hook(void)
{
    /* Review finding (same clobber as the step-5 push/pull bug): a pull
     * must not overwrite a BLE local edit that hasn't been pushed yet.
     * POST /refresh doesn't push -- it's a plain pull -- so just refuse
     * while cfg_src=="ble"; the next real contact's push+pull handles it. */
    if (strcmp(dusty_config_cfg_src(), "ble") == 0) {
        ESP_LOGI(TAG, "refresh: skipped, a local (ble) edit is still pending push");
        return;
    }
    dusty_ident_t id;
    dusty_ident_load(&id);
    char path[64];
    snprintf(path, sizeof(path), "/config/%s", id.device);
    char buf[1024];
    int status = 0;
    if (dusty_uplink_get(path, buf, sizeof(buf), &status) && dusty_config_apply(buf)) {
        dusty_config_mark_server(dusty_config_get()->cfg);
        dusty_led_set(DUSTY_LED_UPDATED);
        ESP_LOGI(TAG, "refresh: config changed (cfg=%d)", dusty_config_get()->cfg);
    } else if (status == 404) {
        /* MINOR review finding: a freshly-provisioned id has no config on
         * the server yet -- that's not a failure, just "nothing to pull". */
        ESP_LOGI(TAG, "refresh: no config yet for this device (404)");
    }
}

static void live_hook(void)
{
    s_live_requested = 1;
}

static void ble_hook(void)
{
    s_ble_requested = 1;
    /* Matches dusty_control.c's ble_post_handler BLE_RESP, which promises
     * the phone {"in_s":2} -- keep GET /status's ble_back_in_s honest
     * about that same promise instead of reporting 0 the whole time. */
    s_ble_back_deadline_us = esp_timer_get_time() + 2LL * 1000000;
}

static int draining_hook(void)
{
    return s_draining;
}

/* ---------------- P1: preview/thumb/frame/spool.list ----------------
 * Review finding (MAJOR, camera lifecycle) superseded the original
 * comment here: `preview` used to just assume main.c's wake cycle had
 * already called xc_cam_init(), which broke as soon as main.c stopped
 * doing that unconditionally before the BLE window (see main.c's header
 * comment on xc_cam_init() moving to after the window block). It now
 * uses cam_ensure()/cam_finish() like `shoot` -- reuses an already-open
 * session (the common case: a live-mode wake, or the WIFI phase's own
 * session-level ensure) and otherwise lazy-inits/deinits for just this
 * one call, which P0 already proved safe on this exact board (40+
 * init/deinit cycles, no SCCB wedge -- that lesson is specifically about
 * re-init *without* a deinit first, which cam_ensure()/xc_cam_init()'s
 * own guard now also can't do by accident). `thumb`/`frame` never touch
 * the sensor (SD-only), so they have no such constraint. */
static int preview_hook(uint8_t **jpg, size_t *jpg_len, float *focus, int *lum)
{
    int cam_had;
    if (!cam_ensure(&cam_had)) return 0;
    camera_fb_t *fb = cam_capture();
    if (!fb) {
        cam_finish(cam_had);
        return 0;
    }
    int w = 0, h = 0;
    uint16_t *rgb = cam_decode(fb, JPG_SCALE_8X, &w, &h);
    int ok = 0;
    if (rgb) {
        uint8_t *out = NULL;
        size_t outn = 0;
        if (cam_preview_jpeg(rgb, &out, &outn)) {
            int cw = 100, ch = 75;
            *focus = cam_sharpness_rgb565(rgb, w, h, (w - cw) / 2, (h - ch) / 2, cw, ch);
            dc_thumb_t thumb;
            dc_thumb_from_rgb565(rgb, w, h, &thumb);
            *lum = dc_thumb_lum(&thumb);
            *jpg = out;
            *jpg_len = outn;
            ok = 1;
        }
        free(rgb);
    }
    cam_release(fb);
    cam_finish(cam_had);
    return ok;
}

/* Returns 1 ok, 0 not found/no card, -1 if a drain holds the SD bus
 * mutex (non-blocking take, per dusty_ble.h/dusty_control.h's tri-state
 * thumb/frame contract). */
static int read_spool_jpg_locked(const char *tier, uint32_t boot, uint32_t seq, uint8_t **buf_out, size_t *len_out)
{
    int had;
    if (!sd_ensure(&had)) return 0;
    SemaphoreHandle_t mtx = dusty_spool_bus_mutex();
    if (mtx && xSemaphoreTake(mtx, 0) != pdTRUE) {
        sd_finish(had);
        return -1;
    }

    int ok = 0;
    char path[96];
    if (dc_spool_path(path, sizeof(path), "/sd", tier, boot, seq, "jpg") >= 0) {
        FILE *f = fopen(path, "rb");
        if (f) {
            fseek(f, 0, SEEK_END);
            long sz = ftell(f);
            fseek(f, 0, SEEK_SET);
            if (sz > 0) {
                uint8_t *buf = heap_caps_malloc((size_t)sz, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
                if (buf) {
                    size_t got = fread(buf, 1, (size_t)sz, f);
                    if (got == (size_t)sz) {
                        *buf_out = buf;
                        *len_out = (size_t)sz;
                        ok = 1;
                    } else {
                        free(buf);
                    }
                }
            }
            fclose(f);
        }
    }
    if (mtx) xSemaphoreGive(mtx);
    sd_finish(had);
    return ok;
}

static int thumb_hook(uint32_t boot, uint32_t seq, uint8_t **jpg, size_t *jpg_len)
{
    uint8_t *filebuf;
    size_t filelen;
    int rc = read_spool_jpg_locked("spool", boot, seq, &filebuf, &filelen);
    if (rc <= 0) return rc;

    camera_fb_t fake;
    memset(&fake, 0, sizeof(fake));
    fake.buf = filebuf;
    fake.len = filelen;
    int w = 0, h = 0;
    uint16_t *rgb = cam_decode(&fake, JPG_SCALE_8X, &w, &h);
    free(filebuf);
    if (!rgb) return 0;

    uint8_t *out = NULL;
    size_t outn = 0;
    int ok = cam_preview_jpeg(rgb, &out, &outn);
    free(rgb);
    if (!ok) return 0;
    *jpg = out;
    *jpg_len = outn;
    return 1;
}

static int frame_hook(uint32_t boot, uint32_t seq, uint8_t **jpg, size_t *jpg_len)
{
    return read_spool_jpg_locked("spool", boot, seq, jpg, jpg_len);
}

static int spool_list_hook(const char *req_json, char *out, size_t cap)
{
    int n_req = 24;
    char tier[16] = "spool";
    cJSON *req = cJSON_Parse(req_json);
    if (req) {
        cJSON *nj = cJSON_GetObjectItemCaseSensitive(req, "n");
        if (cJSON_IsNumber(nj)) n_req = (int)nj->valuedouble;
        cJSON *tj = cJSON_GetObjectItemCaseSensitive(req, "tier");
        if (cJSON_IsString(tj) && tj->valuestring[0]) strlcpy(tier, tj->valuestring, sizeof(tier));
        cJSON_Delete(req);
    }
    if (n_req <= 0 || n_req > 64) n_req = 24;
    int had;
    if (!sd_ensure(&had)) {
        int n = snprintf(out, cap, "{\"items\":[],\"more\":false}");
        return n;
    }

    static dusty_spool_entry_t entries[SPOOL_LIST_CAP]; /* static: not on the caller's stack */
    int total = dusty_spool_scan(tier, entries, SPOOL_LIST_CAP);
    int n = total > SPOOL_LIST_CAP ? SPOOL_LIST_CAP : total;
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
    sd_finish(had);
    return (int)off;
}

/* ---------------- P1: cfg / prov / wifi.scan / handoff / time.set ---------------- */

static int cfg_schema_hook(char *buf, size_t n)
{
#if __has_include("tuning_schema.h")
    size_t len = strlen(TUNING_SCHEMA_JSON);
    if (len >= n) return -1;
    memcpy(buf, TUNING_SCHEMA_JSON, len + 1);
    return (int)len;
#else
    (void)buf;
    (void)n;
    return -1; /* dustygen hasn't stamped tuning_schema.h yet */
#endif
}

static int cfg_get_hook(char *buf, size_t n)
{
    const dc_cfg_t *cfg = dusty_config_get();
    if (!cfg) return -1;
    return dc_cfg_to_json(cfg, buf, n);
}

static int cfg_set_hook(const char *json, int *out_cfg)
{
    if (s_draining) return -1; /* err:"busy" -- a drain currently owns the SD card */
    int rc = dusty_config_set_local(json);
    if (rc < 0) return 0;
    *out_cfg = rc;
    return 1;
}

static int prov_get_hook(char *buf, size_t n)
{
    dusty_ident_t id;
    dusty_ident_load(&id);
    int r = snprintf(buf, n, "{\"device\":\"%s\",\"host\":\"%s\",\"port\":%d,\"tls\":%s,\"ssid\":\"%s\"}",
                      id.device, id.host, id.port, id.tls ? "true" : "false", id.ssid);
    return (r > 0 && (size_t)r < n) ? r : -1;
}

static int prov_set_hook(const char *json, char *device_out, size_t device_out_cap)
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
    if (cJSON_IsString(j) && strlen(j->valuestring) == 64) {
        int ok = 1;
        uint8_t key[32];
        for (int i = 0; i < 32 && ok; i++) {
            unsigned b;
            if (sscanf(j->valuestring + 2 * i, "%2x", &b) != 1) ok = 0;
            else key[i] = (uint8_t)b;
        }
        if (ok) {
            memcpy(id.ble_key, key, sizeof(key));
            id.ble_key_len = 32;
        }
    }
    cJSON_Delete(root);

    if (!id.device[0]) return 0; /* device is mandatory -- it is the identity */

    dusty_ident_save(&id);
    strlcpy(device_out, id.device, device_out_cap);
    return 1;
}

static void time_set_hook(int64_t ts, int tz_min)
{
    (void)tz_min;
    struct timeval tv = { .tv_sec = (time_t)ts, .tv_usec = 0 };
    settimeofday(&tv, NULL);
    g_state.clock_state = APP_CLOCK_SET;
    app_state_note_frame_time(ts);
    ESP_LOGI(TAG, "time_set (ble): ts=%lld", (long long)ts);
}

static void handoff_hook(const char *mode, const char *ssid, const char *pass)
{
    strlcpy(s_handoff_mode, mode ? mode : "view", sizeof(s_handoff_mode));
    strlcpy(s_handoff_ssid, ssid ? ssid : "", sizeof(s_handoff_ssid));
    strlcpy(s_handoff_pass, pass ? pass : "", sizeof(s_handoff_pass));
    s_handoff_pending = 1;
    ESP_LOGI(TAG, "handoff requested: mode=%s ssid=%s", s_handoff_mode, s_handoff_ssid[0] ? s_handoff_ssid : "(ident)");
}

static const char *last_ip_hook(void)
{
    const char *ip = dusty_uplink_ip();
    return (ip && strcmp(ip, "0.0.0.0") != 0) ? ip : "";
}

static int wifi_scan_hook(char *buf, size_t n)
{
    unsigned before = (unsigned)heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
    dusty_wifi_ap_t aps[10];
    int count = dusty_uplink_wifi_scan(aps, 10);
    unsigned after = (unsigned)heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
    ESP_LOGI(TAG, "wifi_scan: %d AP(s), internal_free before=%u after=%u (delta=%d) -- BLE stayed up throughout",
             count, before, after, (int)before - (int)after);

    size_t off = 0;
    int w = snprintf(buf + off, n - off, "{\"aps\":[");
    off += (w > 0) ? (size_t)w : 0;
    for (int i = 0; i < count && off < n; i++) {
        w = snprintf(buf + off, n - off, "%s{\"ssid\":\"%s\",\"rssi\":%d,\"ch\":%d}",
                     i ? "," : "", aps[i].ssid, aps[i].rssi, aps[i].ch);
        off += (w > 0) ? (size_t)w : 0;
    }
    w = snprintf(buf + off, n - off, "]}");
    off += (w > 0) ? (size_t)w : 0;
    return (int)off;
}

static const dusty_control_hooks_t s_hooks = {
    .status_json = status_json_hook,
    .stream_frame = stream_frame_hook,
    .stream_release = stream_release_hook,
    .shoot = shoot_hook,
    .refresh = refresh_hook,
    .live = live_hook,
    .ble = ble_hook,
    .draining = draining_hook,
    .spool_list = spool_list_hook,
    .frame = frame_hook,
    .thumb = thumb_hook,
    /* .device is set by radio.c on the copy it actually passes to
     * dusty_control_start(), same reason as dusty_ble's hooks below. */
};

static const dusty_ble_hooks_t s_ble_hooks = {
    .status_json = status_json_hook,
    .preview = preview_hook,
    .thumb = thumb_hook,
    .frame = frame_hook,
    .spool_list = spool_list_hook,
    .shoot = shoot_hook,
    .handoff = handoff_hook,
    .last_ip = last_ip_hook,
    .live = live_hook,
    .time_set = time_set_hook,
    .cfg_schema = cfg_schema_hook,
    .cfg_get = cfg_get_hook,
    .cfg_set = cfg_set_hook,
    .prov_get = prov_get_hook,
    .prov_set = prov_set_hook,
    .wifi_scan = wifi_scan_hook,
    /* .device/.ble_key/.fw_version are set by radio.c on the copy it
     * passes to dusty_ble_start() -- this table has no identity of its
     * own (contact.h). */
};

const dusty_control_hooks_t *contact_http_hooks(void)
{
    return &s_hooks;
}

const dusty_ble_hooks_t *contact_ble_hooks(void)
{
    return &s_ble_hooks;
}

/* ---------------- drain ---------------- */

static int drain_tier(const char *tier, int cap, const dc_cfg_t *cfg, int64_t *last_tel_us)
{
    dusty_spool_entry_t *entries = (dusty_spool_entry_t *)heap_caps_malloc(
        sizeof(dusty_spool_entry_t) * SPOOL_SCAN_CAP, MALLOC_CAP_SPIRAM);
    if (!entries) {
        ESP_LOGE(TAG, "drain %s: entries alloc failed", tier);
        return 0;
    }

    int total = dusty_spool_scan(tier, entries, SPOOL_SCAN_CAP);
    CRASHDBG("drain: after scan");
    int n = total > SPOOL_SCAN_CAP ? SPOOL_SCAN_CAP : total;
    if (total > SPOOL_SCAN_CAP) {
        ESP_LOGW(TAG, "drain %s: %d entries found, scan capped at %d (%d not considered this contact)",
                 tier, total, SPOOL_SCAN_CAP, total - SPOOL_SCAN_CAP);
    }
    dusty_spool_sort_desc(entries, n);

    int uploaded = 0, consec_fail = 0;
    for (int i = 0; i < n && uploaded < cap; i++) {
        char jpg_path[96], json_path[96];
        char *meta = s_cbuf->meta;
        if (dc_spool_path(jpg_path, sizeof(jpg_path), "/sd", tier, entries[i].boot, entries[i].seq, "jpg") < 0) continue;
        if (dc_spool_path(json_path, sizeof(json_path), "/sd", tier, entries[i].boot, entries[i].seq, "json") < 0) continue;
        if (!dusty_spool_read_text(json_path, meta, CONTACT_BUF)) {
            s_tel.frames_skipped++;
            continue;
        }

        int status = 0;
        if (dusty_uplink_post_file("frame", jpg_path, meta, &status)) {
            dusty_spool_delete(tier, entries[i].boot, entries[i].seq);
            uploaded++;
            s_tel.frames_sent++;
            consec_fail = 0;
        } else {
            s_tel.upload_failures++;
            consec_fail++;
            ESP_LOGW(TAG, "drain %s: upload failed (status %d), %d consecutive", tier, status, consec_fail);
            if (consec_fail >= 5) {
                ESP_LOGW(TAG, "drain %s: stopping after 5 consecutive failures", tier);
                break;
            }
        }

        vTaskDelay(pdMS_TO_TICKS(1)); /* yield so dusty_control can serve mid-drain */

        int64_t now = esp_timer_get_time();
        if (now - *last_tel_us >= (int64_t)cfg->telemetry_s * 1000000) {
            s_tel.pending_files = dusty_spool_count("spool") + dusty_spool_count("debug");
            send_telemetry(TELEMETRY_MODE_CONTACT);
            *last_tel_us = now;
        }
    }
    free(entries);
    ESP_LOGI(TAG, "drain %s: uploaded %d of %d found", tier, uploaded, total);
    return uploaded;
}

/* ---------------- shared serve loop ----------------
 * Used by both contact and view modes. Origin for the idle timeout is
 * max(last request, phase start) -- review finding (the "P0 bug"): using
 * the raw last-request timestamp alone means a phase with NO requests yet
 * reads as idle since forever (dusty_control_last_request_us() defaults
 * to 0, or can carry a stale value from a much earlier phase), ending the
 * serve loop the instant it starts. */
static contact_end_t serve_until_end(const dc_cfg_t *cfg, int64_t serve_start_us, int64_t *last_tel_us, int do_telemetry)
{
    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(500));
        if (contact_take_live()) return CONTACT_END_LIVE;
        if (s_ble_requested) {
            s_ble_requested = 0;
            return CONTACT_END_BLE;
        }

        int64_t now = esp_timer_get_time();
        int64_t last_req = dusty_control_last_request_us();
        int64_t idle_origin = last_req > serve_start_us ? last_req : serve_start_us;
        int64_t idle_us = now - idle_origin;
        int64_t total_us = now - serve_start_us;
        int pinned_setup = cfg && strcmp(cfg->mode, "setup") == 0;

        if (total_us >= (int64_t)cfg->setup_secs * 1000000) {
            ESP_LOGI(TAG, "contact: serve hit setup_secs cap");
            return CONTACT_END_SETUP_CAP;
        }
        if (!pinned_setup && idle_us >= (int64_t)cfg->contact_idle_s * 1000000) return CONTACT_END_IDLE;

        if (do_telemetry && now - *last_tel_us >= (int64_t)cfg->telemetry_s * 1000000) {
            send_telemetry(TELEMETRY_MODE_CONTACT);
            *last_tel_us = now;
        }
    }
}

/* ---------------- contact_run ---------------- */

static contact_end_t contact_run_view(const char *ssid_in, const char *pass_in)
{
    s_contact_mode = "view";
    s_ble_requested = 0;

    dc_cfg_t view_defaults = *dusty_config_get(); /* copy: contact_idle_s/setup_secs still apply */
    /* view mode joins whatever the handoff recorded, falling back to
     * identity (docs/phone_app_plan.md §3: "join, control plane, no
     * clock/announce/firmware/drain"). Review finding (MAJOR): this used
     * to call contact_take_handoff() itself, but radio.c's BLE phase had
     * already drained that one-shot queue to capture ssid/pass/mode
     * before calling here -- so this always saw an empty queue and fell
     * straight through to identity, silently ignoring a phone's ssid/pass
     * override. Now the caller passes through what it actually captured. */
    char ssid[64] = "", pass[64] = "";
    if (ssid_in) strlcpy(ssid, ssid_in, sizeof(ssid));
    if (pass_in) strlcpy(pass, pass_in, sizeof(pass));
    dusty_ident_t id;
    dusty_ident_load(&id);
    if (!ssid[0]) strlcpy(ssid, id.ssid, sizeof(ssid));
    if (!pass[0]) strlcpy(pass, id.pass, sizeof(pass));

    dusty_led_set(DUSTY_LED_SEARCHING);
    int joined = dusty_uplink_wifi_join(ssid, pass, view_defaults.hotspot_join_s);
    if (!joined) {
        ESP_LOGW(TAG, "view: hotspot join failed");
        dusty_led_set(DUSTY_LED_FAIL);
        vTaskDelay(pdMS_TO_TICKS(900));
        return CONTACT_END_JOIN_FAILED;
    }

    dusty_led_set(DUSTY_LED_SOLID);
    /* Session-level cam_ensure() (MAJOR review finding): view mode's
     * stream_frame_hook calls cam_capture() once per MJPEG frame --
     * ensuring once here, for the whole control-plane session, is right;
     * per-frame ensure/finish in the hook itself would init/deinit the
     * sensor on every single frame. Reuses an already-open session (the
     * common "phone linked, then went to view" case) or opens one for
     * just this span. */
    int cam_had;
    cam_ensure(&cam_had);
    dusty_control_hooks_t view_hooks = *contact_http_hooks();
    view_hooks.device = id.device[0] ? id.device : NULL;
    dusty_control_start(&view_hooks);

    int64_t serve_start_us = esp_timer_get_time();
    int64_t last_tel_us = serve_start_us;
    contact_end_t end = serve_until_end(&view_defaults, serve_start_us, &last_tel_us, 0);

    dusty_control_stop();
    cam_finish(cam_had);
    dusty_uplink_wifi_off();
    dusty_led_set(DUSTY_LED_OFF);
    ESP_LOGI(TAG, "view: ended (%d)", (int)end);
    return end;
}

static contact_end_t contact_run_contact(contact_reason_t reason, const char *ssid_in, const char *pass_in)
{
    memset(&s_tel, 0, sizeof(s_tel));
    s_ble_requested = 0;
    s_stream_fb = NULL;
    s_last_focus = 0.0f;
    s_focus_best = 0.0f;
    s_contact_mode = "contact";

    if (!contact_bufs_ready()) {
        ESP_LOGE(TAG, "contact: buffer alloc failed");
        return CONTACT_END_JOIN_FAILED;
    }

    const dc_cfg_t *cfg = dusty_config_get();
    int pending_verify = dusty_ota_pending_verify();
    int max_attempts = pending_verify ? 3 : 1;

    /* Counts for the announce, then hand the LED pin back for the search. */
    count_pending();
    sd_give();

    dusty_ident_t id;
    dusty_ident_load(&id);
    /* Review finding (MAJOR): a `contact` handoff's ssid/pass override was
     * dropped on the floor here -- only the identity's saved hotspot was
     * ever tried. Same fallback rule as view mode: empty override -> use
     * the saved identity. */
    const char *ssid = (ssid_in && ssid_in[0]) ? ssid_in : id.ssid;
    const char *pass = (pass_in && pass_in[0]) ? pass_in : id.pass;
    char config_path[64];
    snprintf(config_path, sizeof(config_path), "/config/%s", id.device);
    char *cfg_buf = s_cbuf->cfg;
    cfg_buf[0] = '\0';
    int joined = 0, first_contact_ok = 0;

    for (int attempt = 0; attempt < max_attempts && !first_contact_ok; attempt++) {
        dusty_led_set(DUSTY_LED_SEARCHING);
        joined = dusty_uplink_wifi_join(ssid, pass, cfg->hotspot_join_s);
        if (!joined) {
            ESP_LOGW(TAG, "contact: hotspot join failed (attempt %d/%d)", attempt + 1, max_attempts);
            continue;
        }
        int status = 0;
        first_contact_ok = dusty_uplink_get(config_path, cfg_buf, CONTACT_BUF, &status);
        if (!first_contact_ok && status == 404) {
            /* MINOR review finding: a freshly-provisioned id has no
             * config on the server yet -- the server WAS reached (clock
             * sync above is still valid), so this is not a failed
             * contact, just "nothing to pull". Discard whatever body a
             * 404 page carried so it's never mistaken for config JSON. */
            ESP_LOGI(TAG, "contact: no config yet for this device (404), continuing");
            first_contact_ok = 1;
            cfg_buf[0] = '\0';
        } else if (!first_contact_ok) {
            ESP_LOGW(TAG, "contact: GET %s failed, status %d (attempt %d/%d)",
                     config_path, status, attempt + 1, max_attempts);
            dusty_uplink_wifi_off();
        }
    }

    if (!joined || !first_contact_ok) {
        dusty_led_set(DUSTY_LED_FAIL);
        vTaskDelay(pdMS_TO_TICKS(900)); /* let the five blinks show before the card takes the pin */
        if (pending_verify) {
            ESP_LOGE(TAG, "pending-verify image could not contact after %d attempt(s): "
                          "clearing fw_pending, restarting for bootloader rollback", max_attempts);
            dusty_nvs_set_str("fw_pending", "");
            esp_restart();
        }
        return CONTACT_END_JOIN_FAILED;
    }

    CRASHDBG("contact: after join + config GET");
    dusty_led_set(DUSTY_LED_SOLID);
    dusty_control_hooks_t hooks = *contact_http_hooks();
    hooks.device = id.device[0] ? id.device : NULL;
    dusty_control_start(&hooks);
    CRASHDBG("contact: after control_start");
    /* Session-level cam_ensure() (MAJOR review finding), same reasoning
     * as contact_run_view(): shoot/stream/preview hooks may fire any
     * number of times during the serve-until-end span below; ensure once
     * for the whole session rather than per hook call. */
    int cam_had;
    cam_ensure(&cam_had);
    CRASHDBG("contact: after cam_ensure");

    /* Clock: this GET's Date header is the first server contact. */
    int64_t server_t = dusty_uplink_last_server_time();
    int64_t board_t = (int64_t)time(NULL);
    if (server_t > 0) {
        s_tel.clock_skew_s = (int)(server_t - board_t);
        struct timeval tv = { .tv_sec = (time_t)server_t, .tv_usec = 0 };
        settimeofday(&tv, NULL);
        g_state.clock_state = APP_CLOCK_SET;
        app_state_note_frame_time(server_t);
    }

    uint32_t contact_n = dusty_nvs_get_u32("contact_n", 0);
    s_tel.contact_n = (int)contact_n;

    /* Announce. dusty_ota_boot_check() (main.c, at boot) already resolved a
     * rollback; a fresh pending-verify image marks itself valid on the
     * first 2xx it gets here (the sarg lesson: it must not sleep first). */
    int announce_ok = send_telemetry(TELEMETRY_MODE_CONTACT);
    CRASHDBG("contact: after announce");
    heap_guard("contact: after announce");
    if (pending_verify && announce_ok) {
        dusty_ota_mark_valid();
    }

    /* Firmware first, then config (docs/camera_standard.md §4 law). */
    char verpath[64];
    snprintf(verpath, sizeof(verpath), "/firmware/%s/version", id.device);
    char verbuf[48] = { 0 };
    int vstatus = 0;
    if (dusty_uplink_get(verpath, verbuf, sizeof(verbuf), &vstatus)) {
        size_t L = strlen(verbuf);
        while (L > 0 && (verbuf[L - 1] == '\n' || verbuf[L - 1] == '\r' || verbuf[L - 1] == ' ')) verbuf[--L] = 0;
        dusty_ota_check_and_install(verbuf); /* restarts on success; does not return */
    }

    /* Step 5, config push (docs/phone_app_plan.md §3): a BLE local edit
     * not yet reconciled with the server gets pushed FIRST, base-checked.
     * Review finding (BLOCKER): the pull below used to run unconditionally
     * afterwards, applying `cfg_buf` -- fetched from the GET *before* this
     * push -- which is the server's OLD config. On a push 2xx that
     * reverted the just-accepted local edit right back and marked it
     * "server" anyway; on a push failure it silently discarded the
     * unpushed local edit. Now: a push attempt (successful or not) always
     * skips the pull -- 2xx means we're already in sync (no need to
     * re-fetch what we just sent), 409 applies the server's body (already
     * did, below), and any other failure just leaves cfg_src="ble" so the
     * next contact retries the push instead of the pull clobbering it. */
    int pushed_this_contact = (strcmp(dusty_config_cfg_src(), "ble") == 0);
    if (pushed_this_contact) {
        const dc_cfg_t *live = dusty_config_get();
        char *live_json = s_cbuf->live;
        int ln = dc_cfg_to_json(live, live_json, CONTACT_BUF);
        if (ln > 0) {
#if __has_include("tuning_schema.h")
            const char *schema_json = TUNING_SCHEMA_JSON;
#else
            const char *schema_json = "null";
#endif
            /* tuning_schema.h can run to a few KB (~2.8 KB for xiaocam1's
             * current schema) -- heap-allocate rather than guess a fixed
             * stack buffer size (the format-truncation warning that used
             * to fire here, -Werror, was correctly catching an undersized
             * one). */
            size_t push_body_cap = (size_t)ln + strlen(schema_json) + 64;
            char *push_body = heap_caps_malloc(push_body_cap, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
            int pn = push_body ? snprintf(push_body, push_body_cap, "{\"base\":%d,\"config\":%s,\"schema\":%s}",
                                           dusty_config_cfg_base(), live_json, schema_json)
                                : -1;
            if (push_body && pn > 0 && (size_t)pn < push_body_cap) {
                char *push_resp = s_cbuf->push_resp;
                push_resp[0] = '\0';
                int push_status = 0;
                int push_ok = dusty_uplink_post_json(config_path, push_body, push_resp, CONTACT_BUF, &push_status);
                if (push_ok) {
                    dusty_config_mark_server(live->cfg);
                    ESP_LOGI(TAG, "contact: config push accepted, cfg=%d now source=server", live->cfg);
                } else if (push_status == 409) {
                    dusty_config_apply(push_resp);
                    dusty_config_mark_server(dusty_config_get()->cfg);
                    ESP_LOGI(TAG, "contact: config push rejected (409): server wins, cfg=%d", dusty_config_get()->cfg);
                } else {
                    ESP_LOGW(TAG, "contact: config push failed, status=%d (will retry next contact)", push_status);
                }
            } else if (!push_body) {
                ESP_LOGE(TAG, "contact: config push body alloc (%u B) failed", (unsigned)push_body_cap);
            }
            free(push_body);
        }
    }

    /* Config: reuse the body from the clock-sync GET above -- nothing on
     * the server changed between that call and here within one contact,
     * and a firmware update would already have restarted us before this
     * point if one had installed. Skipped entirely when a push was
     * attempted this contact (see the comment above) -- cfg_buf is the
     * server's config from BEFORE the push and applying it now would
     * clobber whatever the push block just decided. */
    if (!pushed_this_contact && dusty_config_apply(cfg_buf)) {
        dusty_config_mark_server(dusty_config_get()->cfg);
        dusty_led_set(DUSTY_LED_UPDATED);
        ESP_LOGI(TAG, "contact: config changed, cfg=%d", dusty_config_get()->cfg);
        vTaskDelay(pdMS_TO_TICKS(700)); /* three quick blinks, visible before the drain */
    }
    cfg = dusty_config_get();

    /* Drain: spool first (ranked), then debug previews. The card owns the
     * LED pin for this phase: the flicker of card activity is "draining". */
    int64_t last_tel_us = esp_timer_get_time();
    s_draining = 1;
    CRASHDBG("drain: entry, before mount");
    CRASHDBG_ARM();
    if (sd_take()) {
        CRASHDBG("drain: after mount");
        drain_tier("spool", cfg->upload_cap, cfg, &last_tel_us);
        s_tel.pending_cold = dusty_spool_count("spool");
        drain_tier("debug", cfg->debug_max, cfg, &last_tel_us);
        s_tel.debug_pending = dusty_spool_count("debug");
        s_tel.pending_files = s_tel.pending_cold + s_tel.debug_pending;
        sd_give();
    } else {
        ESP_LOGW(TAG, "contact: SD mount failed, nothing drained");
    }
    s_draining = 0;
    heap_guard("contact: after drain");
    dusty_led_set(DUSTY_LED_SOLID);

    if (pending_verify && dusty_ota_pending_verify()) {
        /* The announce telemetry never landed a 2xx (network hiccup after
         * the config GET that got us this far). Give it one more try now
         * -- the drain likely proved the upload path works anyway, but
         * mark_valid is specifically gated on telemetry per contract. If
         * this also fails, this image has never gotten a single 2xx this
         * whole contact: don't risk a rollback-triggering sleep. */
        if (send_telemetry(TELEMETRY_MODE_CONTACT)) {
            dusty_ota_mark_valid();
        } else {
            ESP_LOGE(TAG, "pending-verify image never got a 2xx this contact: "
                          "clearing fw_pending, restarting for bootloader rollback");
            dusty_nvs_set_str("fw_pending", "");
            dusty_control_stop();
            cam_finish(cam_had);
            dusty_uplink_wifi_off();
            esp_restart();
        }
    }

    /* Serve: setup page + control plane until contact_idle_s of silence
     * (cfg->mode == "setup" pins it open), hard-capped at setup_secs so a
     * stuck viewer can't hold the radio up forever. GET /live or POST
     * /ble end it early. */
    int64_t serve_start_us = esp_timer_get_time();
    contact_end_t end = serve_until_end(cfg, serve_start_us, &last_tel_us, 1);

    /* Leave. */
    send_telemetry(TELEMETRY_MODE_CONTACT);

    dusty_control_stop();
    cam_finish(cam_had);
    dusty_uplink_wifi_off();
    dusty_led_set(DUSTY_LED_OFF);

    contact_n++;
    dusty_nvs_set_u32("contact_n", contact_n);

    /* Reclaim and recount; the card stays mounted (LED suspended) for the
     * caller's wake cycle. */
    if (sd_take()) {
        dusty_spool_reclaim("spool", cfg->spool_max_frames);
        g_state.pending_n = dusty_spool_count("spool");
    }
    g_state.debug_written = 0;
    g_state.thumb_valid = 0; /* motion reference reset (PLAN.md §5 step 8) */

    ESP_LOGI(TAG, "contact done: sent=%d skipped=%d failed=%d pending=%d contact_n=%u end=%d",
             s_tel.frames_sent, s_tel.frames_skipped, s_tel.upload_failures,
             g_state.pending_n, (unsigned)contact_n, (int)end);
    return end;
}

contact_end_t contact_run(contact_reason_t reason, contact_mode_t mode, const char *ssid, const char *pass)
{
    if (mode == CONTACT_MODE_VIEW) return contact_run_view(ssid, pass);
    return contact_run_contact(reason, ssid, pass);
}
