/* xiaocam1 (Seeed XIAO ESP32S3 Sense): game_lowpower wake cycle.
 * PLAN.md §4 (wake), §5 (contact, contact.c), §6 (night), §9 (judge,
 * judge.c). Package B replaces the A3 stub with the full cycle.
 *
 * Bring-up notes carried over from the camlogger sarg lessons:
 *  - deep-sleep-wake-rolls-back-pending-verify-ota-image: a pending-verify
 *    image must transmit and mark itself valid before its first sleep;
 *    contact_run() does this (and never lets this function reach
 *    esp_deep_sleep_start() while still pending-verify -- see the check
 *    right after the contact block below).
 *  - soft-reboot-before-reinitializing-camera-wedged-sccb-i2c /
 *    frame-buffer-allocation-is-fixed-at-esp-camera: this function's own
 *    xc_cam_init() runs once per wake, AFTER the radio window block (a
 *    review finding moved it here: a button/BLE-only window that never
 *    falls through to a self-contact shouldn't pay camera init cost, and
 *    the window's own contact.c hooks lazy-init/reuse the sensor via
 *    cam_ensure()/cam_finish() if they need it sooner) -- xc_cam_init()
 *    itself now also guards against a double-init if something upstream
 *    already opened it. xc_cam_deinit() always runs before sleep and
 *    before any esp_restart() this function calls directly.
 *  - the LED (GPIO21) is also the SD SPI CS pin: dusty_led_suspend()/
 *    resume() wrap the whole SD-mounted window every wake (see the
 *    README's LED section for what that means for visible patterns).
 */
#include <string.h>
#include <stdlib.h>
#include <time.h>

#include "esp_log.h"
#include "esp_sleep.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "driver/gpio.h"
#include "driver/rtc_io.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "board.h"
#include "tuning_defaults.h"
#include "app_state.h"
#include "camera.h"
#include "judge.h"
#include "record.h"
#include "contact.h"
#include "radio.h"
#include "crashdbg.h"

#include "dusty_core.h"
#include "dusty_config.h"
#include "dusty_spool.h"
#include "dusty_uplink.h"
#include "dusty_ota.h"
#include "dusty_led.h"
#include "dusty_control.h"

static const char *TAG = "xiaocam1";

#define NIGHT_JSON_PATH "/sd/night.json"

static dc_cfg_t cfg_defaults(void)
{
    dc_cfg_t c = { 0 };
    c.cfg = 0;
    strlcpy(c.profile, DUSTY_DEF_PROFILE, sizeof(c.profile));
    strlcpy(c.mode, DUSTY_DEF_MODE, sizeof(c.mode));
    c.period_s = DUSTY_DEF_PERIOD_S;
    c.interval_n = DUSTY_DEF_INTERVAL_N;
    c.heartbeat_s = DUSTY_DEF_HEARTBEAT_S;
    c.diff_min_frac = DUSTY_DEF_DIFF_MIN_FRAC;
    c.diff_l_thresh = DUSTY_DEF_DIFF_L_THRESH;
    c.gate_pct = DUSTY_DEF_GATE_PCT;
    {
        static const char *labels[] = DUSTY_DEF_KEEP_LABELS;
        int nlabels = DUSTY_DEF_KEEP_LABELS_N;
        if (nlabels > DC_KEEP_LABELS_MAX) nlabels = DC_KEEP_LABELS_MAX;
        for (int i = 0; i < nlabels; i++)
            strlcpy(c.keep_labels[i], labels[i], sizeof(c.keep_labels[i]));
        c.keep_labels_n = nlabels;
    }
    c.keep_all = DUSTY_DEF_KEEP_ALL;
    c.audit_n = DUSTY_DEF_AUDIT_N;
    c.debug_frames = DUSTY_DEF_DEBUG_FRAMES;
    c.debug_max = DUSTY_DEF_DEBUG_MAX;
    c.upload_cap = DUSTY_DEF_UPLOAD_CAP;
    c.lum_night = DUSTY_DEF_LUM_NIGHT;
    c.lum_day = DUSTY_DEF_LUM_DAY;
    c.night_confirm_n = DUSTY_DEF_NIGHT_CONFIRM_N;
    c.night_margin_s = DUSTY_DEF_NIGHT_MARGIN_S;
    c.night_probe_s = DUSTY_DEF_NIGHT_PROBE_S;
    c.hotspot_join_s = DUSTY_DEF_HOTSPOT_JOIN_S;
    c.contact_idle_s = DUSTY_DEF_CONTACT_IDLE_S;
    c.setup_secs = DUSTY_DEF_SETUP_SECS;
    c.telemetry_s = DUSTY_DEF_TELEMETRY_S;
    c.led_capture = DUSTY_DEF_LED_CAPTURE;
    c.spool_max_frames = DUSTY_DEF_SPOOL_MAX_FRAMES;
    return c;
}

static void button_init(void)
{
    gpio_config_t io = {
        .pin_bit_mask = 1ULL << BOARD_BUTTON_GPIO,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&io);
}

static int button_pressed(void)
{
    return gpio_get_level(BOARD_BUTTON_GPIO) == 0;
}

static void enable_button_wake(void)
{
    button_init();
    /* the digital pull above only holds while that domain is powered;
     * ext1 wake needs the RTC-domain pull held through deep sleep. */
    rtc_gpio_pullup_en(BOARD_BUTTON_GPIO);
    rtc_gpio_pulldown_dis(BOARD_BUTTON_GPIO);
    esp_sleep_enable_ext1_wakeup(1ULL << BOARD_BUTTON_GPIO, ESP_EXT1_WAKEUP_ANY_LOW);
}

/* Control-plane-only, no camera, no SD, never sleeps. Escape hatch for a
 * board stuck crash-looping: the owner can still reach /status and a
 * fixed firmware build can still be pushed to it. */
static void recovery_loop(const dc_cfg_t *cfg) __attribute__((noreturn));
static void recovery_loop(const dc_cfg_t *cfg)
{
    ESP_LOGW(TAG, "RECOVERY mode");
    dusty_led_set(DUSTY_LED_RECOVERY);

    dusty_ident_t id;
    dusty_ident_load(&id);
    dusty_uplink_init(id.host, id.port, id.tls, id.token, id.device);
    dusty_uplink_wifi_join(id.ssid, id.pass, cfg->hotspot_join_s);

    static const dusty_control_hooks_t no_hooks = { 0 };
    dusty_control_start(&no_hooks);

    int64_t last_fw_check_us = 0;
    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(1000));
        int64_t now = esp_timer_get_time();
        if (now - last_fw_check_us >= 60LL * 1000000) {
            char path[64], verbuf[48] = { 0 };
            int status = 0;
            snprintf(path, sizeof(path), "/firmware/%s/version", id.device);
            if (dusty_uplink_get(path, verbuf, sizeof(verbuf), &status)) {
                dusty_ota_check_and_install(verbuf); /* restarts on success */
            }
            last_fw_check_us = now;
        }
    }
}

static int should_enter_recovery(int cold)
{
    if (esp_reset_reason() == ESP_RST_PANIC) {
        uint32_t crash_n = dusty_nvs_get_u32("crash_n", 0) + 1;
        dusty_nvs_set_u32("crash_n", crash_n);
        ESP_LOGW(TAG, "reset reason PANIC, crash_n=%u", (unsigned)crash_n);
        if (crash_n >= 3) return 1;
    }
    if (cold && button_pressed()) {
        vTaskDelay(pdMS_TO_TICKS(3000));
        if (button_pressed()) return 1;
    }
    return 0;
}

/* Shared by this file's live wake-cycle record path and contact.c's
 * `shoot` control hook -- see record.h. */
int record_build_meta(const record_req_t *req, uint32_t seq, char *buf, size_t n)
{
    if (!req || !req->fb || !buf) return -1;
    const dc_cfg_t *cfg = dusty_config_get();

    float sharp_norm = req->sharpness / 50.0f;
    if (sharp_norm > 1.0f) sharp_norm = 1.0f;
    if (sharp_norm < 0.0f) sharp_norm = 0.0f;
    float conf = (req->jr && req->jr->has_det) ? req->jr->det_conf : -1.0f;
    float score = dc_score(req->why, conf, req->diff, sharp_norm);

    dc_meta_t m;
    memset(&m, 0, sizeof(m));
    m.ts = (int64_t)time(NULL);
    m.seq = seq;
    m.w = (int)req->fb->width;
    m.h = (int)req->fb->height;
    m.v = dusty_ota_running_version();
    m.cfg = cfg ? cfg->cfg : 0;
    m.ip = (req->mode && strcmp(req->mode, "contact") == 0) ? dusty_uplink_ip() : "0.0.0.0";
    m.mode = req->mode ? req->mode : "live";
    m.why = req->why ? req->why : "none";
    m.diff = req->diff;
    m.gate = cfg ? cfg->diff_min_frac : 0.0f;
    m.heartbeat = (req->why && strcmp(req->why, "heartbeat") == 0) ? 1 : 0;
    m.buffered = 1;
    m.lum = req->lum;
    m.clock = app_state_clock_str();
    m.score = score;
    m.has_det = (req->jr && req->jr->has_det) ? 1 : 0;
    m.det_label = m.has_det ? req->jr->det_label : NULL;
    m.det_conf = m.has_det ? req->jr->det_conf : 0.0f;
    m.audit = (req->jr && req->jr->audit) ? 1 : 0;
    m.night_s = req->night_s;
    return dc_meta_build(buf, n, &m);
}

int record_frame(const record_req_t *req, uint32_t *seq_out)
{
    if (!req || !req->fb) return 0;
    uint32_t boot = dusty_nvs_get_u32("boot_count", 0);
    uint32_t seq = g_state.seq;

    char meta_buf[768];
    int n = record_build_meta(req, seq, meta_buf, sizeof(meta_buf));
    if (n < 0) {
        ESP_LOGE(TAG, "record_frame: meta build overflow");
        return 0;
    }
    if (!dusty_spool_write("spool", boot, seq, req->fb->buf, req->fb->len, meta_buf)) {
        ESP_LOGE(TAG, "record_frame: spool write failed (boot=%u seq=%u)", (unsigned)boot, (unsigned)seq);
        return 0;
    }

    g_state.seq++;
    g_state.pending_n++;
    if (req->update_motion_ref && req->thumb) {
        g_state.thumb = *req->thumb;
        g_state.thumb_valid = 1;
        g_state.awake_ms = 0;
    }
    app_state_note_frame_time((int64_t)time(NULL));
    if (seq_out) *seq_out = seq;

    ESP_LOGI(TAG, "recorded spool/%u/%06u.jpg why=%s", (unsigned)boot, (unsigned)seq, req->why ? req->why : "none");
    return 1;
}

void app_main(void)
{
    /* CONFIG_LOG_DEFAULT_LEVEL_WARN: keep the app's own story visible. */
    static const char *const info_tags[] = { "xiaocam1", "contact", "radio", "dusty_ble",
        "dusty_uplink", "dusty_control", "dusty_spool", "dusty_ota", "dusty_config", "dusty_led" };
    for (size_t i = 0; i < sizeof(info_tags) / sizeof(info_tags[0]); i++)
        esp_log_level_set(info_tags[i], ESP_LOG_INFO);
    esp_sleep_wakeup_cause_t wake_cause = esp_sleep_get_wakeup_cause();
    /* GPIO21 (LED / SD CS) was held high through deep sleep: release it
     * before anything reconfigures the pin. */
    gpio_deep_sleep_hold_dis();
    gpio_hold_dis(BOARD_LED_GPIO);
    button_init();
    int cold = app_state_load();
    g_state.wake_n++;

    const char *cause_str;
    int woke_by_button = 0;
    if (cold) {
        cause_str = "cold";
    } else if (wake_cause == ESP_SLEEP_WAKEUP_EXT1) {
        cause_str = "button";
        woke_by_button = 1;
    } else if (wake_cause == ESP_SLEEP_WAKEUP_TIMER) {
        cause_str = "timer";
    } else {
        cause_str = "other";
    }

    dusty_ident_t ident;
    dusty_ident_load(&ident);
    dusty_uplink_init(ident.host, ident.port, ident.tls, ident.token, ident.device);
    dusty_ota_init(ident.host, ident.port, ident.tls, ident.token, ident.device);
    if (dusty_ota_boot_check()) {
        ESP_LOGW(TAG, "firmware rollback occurred this boot (fw_bad recorded)");
    }

    dc_cfg_t defaults = cfg_defaults();
    dusty_config_init(&defaults);
    const dc_cfg_t *cfg = dusty_config_get();

    app_state_clock_init();
    /* SD pins from board.h: dusty_spool is board-neutral and defaults to
     * -1 (no bus) — the first flash (2026-09-15) spent the day with
     * sdmmc_card_init 0x107 because this call was missing. */
    dusty_spool_pins_t sd_pins = {
        .cs_gpio = BOARD_SD_CS_GPIO, .sck_gpio = BOARD_SD_SCK_GPIO,
        .miso_gpio = BOARD_SD_MISO_GPIO, .mosi_gpio = BOARD_SD_MOSI_GPIO,
    };
    dusty_spool_set_pins(&sd_pins);
    dusty_led_init(BOARD_LED_GPIO, BOARD_LED_ACTIVE_LOW, dusty_spool_bus_mutex());

    ESP_LOGI(TAG, "wake_n=%u cause=%s cold=%d cfg=%d period_s=%d device=%s provisioned=%d",
             (unsigned)g_state.wake_n, cause_str, cold, cfg->cfg, cfg->period_s,
             ident.device, dusty_ident_is_provisioned(&ident));

    if (should_enter_recovery(cold)) {
        recovery_loop(cfg); /* never returns */
    }

    int contact_pending = dusty_ota_pending_verify();
    /* Review finding (BLOCKER): RTC_DATA_ATTR g_state (app_state.c) survives
     * esp_restart() (only power-loss clears it), so `cold` alone can't tell
     * "this is the wake right after a dusty_ble `reboot`/`prov.set` asked
     * for a restart" from an ordinary warm wake -- a plain esp_restart()
     * looks exactly like a timer wake to app_state_load(). NVS "first_contact"
     * is the separate, non-volatile signal for that case: main.c sets it
     * right before the esp_restart() below (RADIO_END_RESTART) and consumes
     * it here on the very next boot. */
    int first_contact = dusty_nvs_get_u32("first_contact", 0) != 0;

    /* Radio window first, with the card unmounted: contact_run() (via
     * radio_window_run()) mounts it only for the drain, so the searching /
     * updated / fail LED patterns are visible (PLAN.md §7). It leaves the
     * card mounted and the LED suspended on return. judge_init() is lazy
     * (docs/phone_app_plan.md §3): it used to run unconditionally before
     * this block; it now only runs once we know this wake will actually
     * reach the motion-gate code below, after the window (if any) is
     * done -- a button/BLE-only wake with no live-wake gate call never
     * pays the TFLite arena init cost. Review finding (BLOCKER): a cold
     * boot used to open no window at all, contradicting docs/phone_app_plan.md
     * §3's own pseudocode (`if (woke_by_button || cold || contact_pending)
     * radio_window_run(reason)`) -- `cold` and `first_contact` are added
     * here, both mapped to CONTACT_REASON_FIRST_BOOT (BLE window, then
     * today's self-contact fallback if nothing links). Review finding
     * (MAJOR, camera lifecycle): xc_cam_init() used to run before this
     * block unconditionally; it now runs after (below), since every hook
     * that might need the sensor during the window (contact.c's
     * cam_ensure()/cam_finish()) lazy-inits/reuses it itself -- a
     * button/BLE-only window with no phone linked pays for camera init
     * only if it actually falls through to a self-contact. */
    if (woke_by_button || cold || first_contact || contact_pending) {
        if (first_contact) dusty_nvs_set_u32("first_contact", 0); /* consumed */
        contact_reason_t reason = contact_pending  ? CONTACT_REASON_PENDING_VERIFY
                                   : woke_by_button ? CONTACT_REASON_BUTTON
                                                     : CONTACT_REASON_FIRST_BOOT;
        radio_end_t rend = radio_window_run(reason);
        if (rend == RADIO_END_RESTART) {
            /* dusty_ble asked for a restart (`reboot` or a successful
             * `prov.set`) and has already been stopped by radio.c --
             * BLOCKER fix: dusty_ble never calls esp_restart() itself, so
             * this is where that actually happens, after our own
             * teardown. Re-arm first_contact so the reboot this causes
             * also opens a window (it won't be a cold boot -- RTC memory
             * survives -- and won't be a button/pending-verify wake
             * either). */
            ESP_LOGI(TAG, "radio window asked for a restart (reboot/prov.set): restarting");
            dusty_nvs_set_u32("first_contact", 1);
            xc_cam_deinit();
            esp_restart();
        }
        if (contact_pending && dusty_ota_pending_verify()) {
            /* Belt and suspenders: contact_run() (inside radio_window_run)
             * only returns for a pending-verify caller after marking the
             * image valid (or it restarts internally). If we somehow got
             * here still pending, do not risk a rollback-triggering sleep. */
            ESP_LOGE(TAG, "still pending-verify after contact: restarting rather than sleeping");
            xc_cam_deinit();
            esp_restart();
        }
        cfg = dusty_config_get(); /* the window may have applied/pushed a new config */
    }

    esp_err_t cam_err = xc_cam_init();
    if (cam_err != ESP_OK) {
        ESP_LOGE(TAG, "cam_init failed: %s", esp_err_to_name(cam_err));
    }

    judge_init();
    judge_arena_info();

    dusty_led_suspend(); /* GPIO21 becomes SD SPI CS for the rest of this wake */
    int sd_ok = dusty_spool_mount();
    if (!sd_ok) {
        dusty_led_resume();
        dusty_led_set(DUSTY_LED_FAIL);
        ESP_LOGW(TAG, "SD mount failed: recording refused this wake");
    }

    if (cold && sd_ok) {
        char hist_buf[128];
        if (dusty_spool_read_text(NIGHT_JSON_PATH, hist_buf, sizeof(hist_buf))) {
            dc_night_hist_from_json(&g_state.night, hist_buf);
        }
    }

    uint32_t sleep_s = (uint32_t)cfg->period_s;
    int recorded_this_wake = 0;
    dc_diff_t diff;
    memset(&diff, 0, sizeof(diff));
    const char *why = "none";
    judge_result_t jr;
    memset(&jr, 0, sizeof(jr));
    int have_jr = 0;
    int lum = g_state.last_lum;

    camera_fb_t *fb = cam_capture();
    if (!fb) {
        ESP_LOGE(TAG, "cam_capture failed this wake");
    } else {
        int w200 = 0, h200 = 0;
        uint16_t *rgb200 = cam_decode(fb, JPG_SCALE_8X, &w200, &h200);
        dc_thumb_t thumb;
        int have_thumb = 0;
        if (rgb200) {
            dc_thumb_from_rgb565(rgb200, w200, h200, &thumb);
            lum = dc_thumb_lum(&thumb);
            have_thumb = 1;
        } else {
            ESP_LOGW(TAG, "cam_decode(200x150) failed");
        }
        g_state.last_lum = lum;

        dc_night_cfg_t night_cfg = {
            .lum_night = cfg->lum_night,
            .lum_day = cfg->lum_day,
            .night_confirm_n = cfg->night_confirm_n,
            .night_margin_s = (uint32_t)cfg->night_margin_s,
            .night_probe_s = (uint32_t)cfg->night_probe_s,
            .period_s = (uint32_t)cfg->period_s,
        };
        dc_night_out_t night_out;
        memset(&night_out, 0, sizeof(night_out));
        uint32_t now_s = (uint32_t)time(NULL);
        dc_night_step(&g_state.night, lum, now_s, &night_cfg, &night_out);
        sleep_s = night_out.sleep_s;

        if (night_out.left && sd_ok) {
            char hbuf[128];
            if (dc_night_hist_to_json(&g_state.night, hbuf, sizeof(hbuf)) > 0)
                dusty_spool_write_text(NIGHT_JSON_PATH, hbuf);
        }

        int skip_recording = night_out.entered || (night_out.in_night && !night_out.left);
        if (skip_recording) {
            ESP_LOGI(TAG, "night: %s, sleeping %u s",
                     night_out.entered ? "entered" : "probing", (unsigned)sleep_s);
        } else {
            if (have_thumb && g_state.thumb_valid) {
                dc_thumb_diff(&thumb, &g_state.thumb, cfg->diff_l_thresh, &diff);
            } else {
                diff.frac = 1.0f;
                diff.n = 0;
                diff.x0 = diff.y0 = diff.x1 = diff.y1 = -1;
            }

            if (night_out.left || !have_thumb || !g_state.thumb_valid) {
                why = "boot";
            } else if (diff.frac >= cfg->diff_min_frac) {
                why = "motion";
            } else if (cfg->interval_n > 0 && (g_state.wake_n % (uint32_t)cfg->interval_n) == 0) {
                why = "interval";
            } else if (g_state.awake_ms >= (uint32_t)cfg->heartbeat_s * 1000) {
                why = "heartbeat";
            } else {
                why = "none";
            }

            if (cfg->debug_frames && g_state.debug_written < cfg->debug_max && have_thumb && sd_ok) {
                uint8_t *dbg_jpg = NULL;
                size_t dbg_len = 0;
                if (cam_preview_jpeg(rgb200, &dbg_jpg, &dbg_len)) {
                    dc_meta_t dm;
                    memset(&dm, 0, sizeof(dm));
                    dm.ts = (int64_t)time(NULL);
                    dm.seq = g_state.seq;
                    dm.w = w200;
                    dm.h = h200;
                    dm.v = dusty_ota_running_version();
                    dm.cfg = cfg->cfg;
                    dm.ip = "0.0.0.0";
                    dm.mode = "live";
                    dm.why = "watch";
                    dm.diff = diff.frac;
                    dm.gate = cfg->diff_min_frac;
                    dm.buffered = 1;
                    dm.lum = lum;
                    dm.clock = app_state_clock_str();
                    dm.night_s = -1;
                    char meta_buf[512];
                    int mn = dc_meta_build(meta_buf, sizeof(meta_buf), &dm);
                    if (mn > 0) {
                        uint32_t boot = dusty_nvs_get_u32("boot_count", 0);
                        if (dusty_spool_write("debug", boot, (uint32_t)g_state.debug_written,
                                               dbg_jpg, dbg_len, meta_buf)) {
                            g_state.debug_written++;
                        }
                    }
                    free(dbg_jpg);
                }
            }

            if (strcmp(why, "none") != 0 && sd_ok) {
                if (strcmp(why, "motion") == 0) {
                    /* only motion frames face the gate: boot, interval and
                     * heartbeat frames are proof of life and always keep */
                    int w400 = 0, h400 = 0;
                    uint16_t *rgb400 = cam_decode(fb, JPG_SCALE_4X, &w400, &h400);
                    judge_run(rgb400, &diff, cfg, &jr);
                    have_jr = 1;
                    if (rgb400) free(rgb400);
                } else {
                    jr.keep = 1;
                }

                if (jr.keep) {
                    int cw = 100, ch = 75;
                    float sharp = rgb200 ? cam_sharpness_rgb565(rgb200, w200, h200,
                                                                 (w200 - cw) / 2, (h200 - ch) / 2, cw, ch)
                                          : 0.0f;
                    record_req_t req = { 0 };
                    req.fb = fb;
                    req.thumb = have_thumb ? &thumb : NULL;
                    req.lum = lum;
                    req.diff = diff.frac;
                    req.jr = have_jr ? &jr : NULL;
                    req.why = why;
                    req.mode = "live";
                    req.night_s = night_out.left ? (int64_t)night_out.night_len_s : -1;
                    req.update_motion_ref = 1;
                    req.sharpness = sharp;
                    if (record_frame(&req, NULL)) {
                        recorded_this_wake = 1;
                    }
                }
            }
        }
        if (rgb200) free(rgb200);
    }

    /* Button pressed live during this wake (not the wake cause): open a
     * radio window before sleeping. Camera is up; contact_run() unmounts /
     * remounts the card around its own phases. */
    if (!woke_by_button && !contact_pending && button_pressed()) {
        ESP_LOGI(TAG, "button pressed during wake: opening a radio window");
        radio_end_t rend = radio_window_run(CONTACT_REASON_BUTTON);
        if (rend == RADIO_END_RESTART) {
            /* Same BLOCKER fix as the earlier window block: dusty_ble
             * asked for a restart and has already been stopped by
             * radio.c. The camera is up this time (this wake's capture
             * cycle already ran) and fb may still be held. */
            ESP_LOGI(TAG, "radio window asked for a restart (reboot/prov.set): restarting");
            dusty_nvs_set_u32("first_contact", 1);
            if (fb) cam_release(fb);
            xc_cam_deinit();
            esp_restart();
        }
        cfg = dusty_config_get();
    }

    if (fb) cam_release(fb);
    xc_cam_deinit();
    dusty_spool_unmount();
    dusty_led_resume();
    /* led_capture's blink is queued only now, after resume(): the LED pin
     * is suspended (routed to SD SPI CS) for the whole mounted window
     * above, so a blink requested earlier would be silently swallowed. */
    if (recorded_this_wake && cfg->led_capture) dusty_led_blink_ms(50);

    if (dusty_nvs_get_u32("crash_n", 0)) dusty_nvs_set_u32("crash_n", 0); /* clean wake */

    heap_guard("before sleep");
    g_state.awake_ms += (uint32_t)(esp_timer_get_time() / 1000);
    app_state_save();

    enable_button_wake();
    esp_sleep_enable_timer_wakeup((uint64_t)sleep_s * 1000000ULL);

    float score = have_jr ? dc_score(why, jr.has_det ? jr.det_conf : -1.0f, diff.frac, 0.0f)
                          : (recorded_this_wake ? dc_score(why, -1.0f, diff.frac, 0.0f) : 0.0f);
    ESP_LOGI(TAG, "wake_n=%u cause=%s lum=%d diff=%.3f why=%s kept=%d score=%.1f awake_ms=%u sleep_s=%u",
             (unsigned)g_state.wake_n, cause_str, lum, diff.frac, why, recorded_this_wake,
             (double)score, (unsigned)g_state.awake_ms, (unsigned)sleep_s);

    if (recorded_this_wake && cfg->led_capture) vTaskDelay(pdMS_TO_TICKS(80)); /* let the blink show */
    /* Keep the shared LED / SD CS line high (card deselected, LED off)
     * while the digital domain is off. Released at the top of app_main. */
    gpio_set_level(BOARD_LED_GPIO, BOARD_LED_ACTIVE_LOW ? 1 : 0);
    gpio_hold_en(BOARD_LED_GPIO);
    gpio_deep_sleep_hold_en();
    esp_deep_sleep_start();
}
