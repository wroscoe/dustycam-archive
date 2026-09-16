/* radio.c: docs/phone_app_plan.md §3.
 *
 *   SLEEP --button/cold boot--> BLE --wifi.up|contact--> WIFI
 *          --phase ends|POST /ble--> BLE --window over--> SLEEP
 *
 * Timer wakes never call radio_window_run() at all (app_main() decides).
 * Review finding (MAJOR): a BLE link now extends the window for real --
 * the deadline is ignored entirely while dusty_ble_connected(), so a
 * linked phone can keep issuing ops indefinitely; only a link going idle
 * for cfg->contact_idle_s (not a fixed constant any more) ends it early.
 * Every WIFI-phase end (contact_end_t) except CONTACT_END_LIVE returns to
 * BLE -- BLE's own deadline check is what actually ends the window,
 * matching the diagram above literally (the "phase ends" arrow always
 * goes back to BLE, never straight to SLEEP) -- except CONTACT_END_BLE,
 * which also gets RADIO_BLE_GRACE_S of guaranteed BLE time regardless of
 * the deadline (see that #define below).
 */
#include "radio.h"
#include "crashdbg.h"

#include <string.h>

#include "esp_log.h"
#include "esp_timer.h"
#include "esp_heap_caps.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "dusty_config.h"
#include "dusty_ble.h"
#include "dusty_ota.h"

static const char *TAG_RADIO = "radio";

/* TODO(dustygen): ble_adv_s belongs in tuning_defaults.h/dc_cfg_t once
 * dustygen stamps it (docs/phone_app_plan.md §5 tuning row); until then
 * this is the documented fallback the task asked for. */
#define RADIO_BLE_ADV_S 120
#define RADIO_UNPROVISIONED_WINDOW_S 600
#define RADIO_POLL_MS 200
/* Review finding (MAJOR): POST /ble's reply promises the phone BLE comes
 * back within back_in_s (DUSTY_BLE_HANDOFF_BACK_S, ~2 s) -- but if the
 * window's original deadline had already elapsed by the time the WIFI
 * phase ended, radio_window_run() used to skip the return-to-BLE phase
 * entirely and go straight to SLEEP, breaking that promise. Guarantee at
 * least this much real BLE time after a CONTACT_END_BLE, regardless of
 * the original deadline. */
#define RADIO_BLE_GRACE_S 30

static uint32_t s_cycle_n;

static void radio_log(const char *state)
{
    ESP_LOGI(TAG_RADIO, "state=%s internal_free=%u largest=%u cycle=%u", state,
             (unsigned)heap_caps_get_free_size(MALLOC_CAP_INTERNAL),
             (unsigned)heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL),
             (unsigned)s_cycle_n);
    heap_caps_print_heap_info(MALLOC_CAP_INTERNAL);
}

/* Runs the BLE phase to completion. Returns 1 if it ended because a
 * handoff was recorded (mode/ssid/pass filled in, go to WIFI), 0 if the
 * whole window is over (go to SLEEP) -- except for the one case that
 * still performs today's button-alone contact with no phone ever linked,
 * which also returns 1 with mode="contact". *restart_out is set to 1
 * (review finding, BLOCKER) if `reboot` or a successful `prov.set` asked
 * dusty_ble to restart this session -- dusty_ble never calls esp_restart()
 * itself, so the caller must notice this flag right after dusty_ble_stop()
 * and act on it. */
static int run_ble_phase(contact_reason_t reason, int provisioned, const dusty_ident_t *id, int64_t deadline_us,
                          char *mode_out, size_t mode_cap, char *ssid_out, size_t ssid_cap, char *pass_out, size_t pass_cap,
                          int *restart_out)
{
    dusty_ble_hooks_t hooks = *contact_ble_hooks();
    hooks.device = id->device[0] ? id->device : NULL;
    hooks.ble_key = id->ble_key_len == DUSTY_IDENT_BLE_KEY_LEN ? id->ble_key : NULL;
    hooks.fw_version = dusty_ota_running_version();

    int win_left_s = (int)((deadline_us - esp_timer_get_time()) / 1000000);
    if (win_left_s < 0) win_left_s = 0;
    contact_set_radio_state("ble", "contact", 0, win_left_s);
    dusty_ble_start(&hooks);
    radio_log("BLE");

    int link_idle_s = dusty_config_get()->contact_idle_s;
    if (link_idle_s <= 0) link_idle_s = 120; /* defensive: an unset/zero cfg must not spin-loop-exit BLE */

    int had_link = 0;
    int go_wifi = 0;
    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(RADIO_POLL_MS));
        int connected = dusty_ble_connected();
        if (connected) had_link = 1;

        if (contact_take_live()) break; /* go_wifi stays 0 -> SLEEP */

        if (dusty_ble_restart_requested()) {
            /* BLOCKER fix: `reboot`/a successful `prov.set` already
             * terminated the link and set this flag inside dusty_ble --
             * don't wait out the idle timeout or the window deadline to
             * notice (that could be minutes). go_wifi stays 0; the
             * caller checks the flag right after dusty_ble_stop() below. */
            break;
        }

        if (contact_take_handoff(mode_out, mode_cap, ssid_out, ssid_cap, pass_out, pass_cap)) {
            go_wifi = 1;
            break;
        }

        int64_t now = esp_timer_get_time();
        /* Review finding (MAJOR): plan §1.9 says a linked phone extends
         * the window -- only the idle rule below should end a live link,
         * not this fixed deadline. Ignore the deadline entirely while
         * connected. */
        if (now >= deadline_us && !connected) {
            if (!had_link && provisioned && reason != CONTACT_REASON_PENDING_VERIFY) {
                /* Today's button contact, preserved: no phone linked
                 * inside the window, so the camera tries the hotspot
                 * itself (docs/phone_app_plan.md §1.9). */
                strlcpy(mode_out, "contact", mode_cap);
                if (ssid_cap) ssid_out[0] = '\0';
                if (pass_cap) pass_out[0] = '\0';
                go_wifi = 1;
            }
            break;
        }

        int64_t last_req = dusty_ble_last_request_us();
        if (had_link && last_req > 0 && (now - last_req) >= (int64_t)link_idle_s * 1000000) {
            break; /* linked phone went quiet: end the window (go_wifi stays 0) */
        }
    }

    dusty_ble_stop();
    CRASHDBG("radio: after ble_stop");
    heap_guard("radio: after ble_stop");
    if (restart_out) *restart_out = dusty_ble_restart_requested();
    radio_log("BLE");
    return go_wifi;
}

radio_end_t radio_window_run(contact_reason_t reason)
{
    esp_log_level_set(TAG_RADIO, ESP_LOG_INFO); /* CONFIG_LOG_DEFAULT_LEVEL_WARN would otherwise hide this permanently */

    if (reason == CONTACT_REASON_PENDING_VERIFY) {
        /* Time-critical (sarg: deep-sleep-wake-rolls-back-pending-verify-
         * ota-image): a pending-verify image must transmit and mark
         * itself valid before its first sleep, so this goes straight to
         * a WIFI contact -- the plan's own BLE-phase pseudocode
         * deliberately excludes this reason from the "no link -> self
         * contact" fallback (`reason != PENDING_VERIFY`), i.e. it must
         * not sit in a 120 s BLE window first. contact_run_contact()
         * itself still does its usual 3 join/GET attempts, and
         * esp_restart()s for a bootloader rollback if none of them land a
         * single 2xx -- unchanged from the pre-radio.c behaviour. */
        contact_set_radio_state("wifi", "contact", 0, 0);
        contact_run(reason, CONTACT_MODE_CONTACT, NULL, NULL);
        contact_set_radio_state("ble", "contact", 0, 0);
        radio_log("SLEEP");
        return RADIO_END_NORMAL; /* this path never touches dusty_ble */
    }

    dusty_ident_t id;
    dusty_ident_load(&id);
    int provisioned = dusty_ident_is_provisioned(&id);
    int window_s = provisioned ? RADIO_BLE_ADV_S : RADIO_UNPROVISIONED_WINDOW_S;
    int64_t deadline_us = esp_timer_get_time() + (int64_t)window_s * 1000000;

    radio_log("SLEEP");

    for (;;) {
        char mode[16] = { 0 }, ssid[64] = { 0 }, pass[64] = { 0 };
        int restart_requested = 0;
        int go_wifi = run_ble_phase(reason, provisioned, &id, deadline_us,
                                     mode, sizeof(mode), ssid, sizeof(ssid), pass, sizeof(pass),
                                     &restart_requested);
        if (restart_requested) {
            /* BLOCKER fix: dusty_ble asked for a restart (`reboot` or a
             * successful `prov.set`) and has already been stopped above
             * (dusty_ble_stop() inside run_ble_phase) -- hand off to
             * main.c to do its own teardown and the actual esp_restart(). */
            contact_set_radio_state("ble", "contact", 0, 0);
            radio_log("RESTART");
            return RADIO_END_RESTART;
        }
        if (!go_wifi) break; /* window over (or `live`): -> SLEEP */

        contact_mode_t cmode = (strcmp(mode, "contact") == 0) ? CONTACT_MODE_CONTACT : CONTACT_MODE_VIEW;
        int win_left_s = (int)((deadline_us - esp_timer_get_time()) / 1000000);
        if (win_left_s < 0) win_left_s = 0;
        contact_set_radio_state("wifi", cmode == CONTACT_MODE_CONTACT ? "contact" : "view", 0, win_left_s);

        contact_end_t end = contact_run(reason, cmode, ssid, pass);
        s_cycle_n++;
        radio_log("WIFI");

        if (end == CONTACT_END_LIVE) break; /* -> SLEEP */
        if (end == CONTACT_END_BLE) {
            /* See RADIO_BLE_GRACE_S above: honour the back_in_s promise
             * even if the window's deadline has already passed. */
            int64_t grace_deadline = esp_timer_get_time() + (int64_t)RADIO_BLE_GRACE_S * 1000000;
            if (grace_deadline > deadline_us) deadline_us = grace_deadline;
        } else if (esp_timer_get_time() >= deadline_us) {
            /* Any other end (idle, setup cap, join failed) goes back to
             * BLE; that phase's own deadline check ends the window for
             * real once window_s has elapsed since this function was
             * entered -- matches the plan's diagram (every WIFI exit
             * arrow loops back to BLE, not straight to SLEEP). */
            break;
        }
    }

    contact_set_radio_state("ble", "contact", 0, 0);
    radio_log("SLEEP");
    return RADIO_END_NORMAL;
}
