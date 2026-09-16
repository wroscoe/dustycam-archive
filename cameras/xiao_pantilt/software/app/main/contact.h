/* contact: the phone-hotspot contact sequence, docs/camera_operation.md
 * §5 / PLAN.md §5 / docs/phone_app_plan.md §3. Review finding (MAJOR,
 * camera lifecycle) superseded the "camera must already be initialised
 * before calling contact_run()" contract this used to document: main.c
 * no longer guarantees that (xc_cam_init() moved to run AFTER the radio
 * window), so contact_run() and every hook that might touch the sensor
 * (shoot/preview/stream) now use cam_ensure()/cam_finish() (this file) to
 * lazily init it if needed and reuse it (never re-init) if a wake cycle
 * already has it open. Also owns the dusty_ble hooks table (shared with
 * HTTP) that radio.c wires into dusty_ble_start().
 */
#ifndef XIAOCAM1_CONTACT_H
#define XIAOCAM1_CONTACT_H

#include "dusty_ble.h"
#include "dusty_control.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    CONTACT_REASON_BUTTON,
    CONTACT_REASON_FIRST_BOOT,
    CONTACT_REASON_PENDING_VERIFY,
} contact_reason_t;

/* "contact" = today's full sequence (join, clock, announce, firmware,
 * config, drain, serve); "view" = join + control plane + serve only, no
 * clock/announce/firmware/drain (docs/phone_app_plan.md §3 -- viewing
 * off-grid needs no cell reachability). */
typedef enum {
    CONTACT_MODE_CONTACT,
    CONTACT_MODE_VIEW,
} contact_mode_t;

/* Why contact_run() ended, so radio.c's state machine knows whether to
 * fall back to BLE or go to sleep. */
typedef enum {
    CONTACT_END_JOIN_FAILED, /* never reached the hotspot/server */
    CONTACT_END_IDLE,        /* contact_idle_s of silence (origin = max(last request, phase start)) */
    CONTACT_END_SETUP_CAP,   /* setup_secs hard cap */
    CONTACT_END_LIVE,        /* GET /live: end the whole window, go to sleep */
    CONTACT_END_BLE,         /* POST /ble: radio.c should return to the BLE phase */
} contact_end_t;

/* Runs the sequence for `mode`. `ssid`/`pass` are the handoff override the
 * BLE phase captured via contact_take_handoff() (radio.c consumes that
 * queue once, before calling here) -- NULL or "" means "no override, use
 * the saved identity's hotspot" (review finding, MAJOR: contact_run_view()
 * used to call contact_take_handoff() a second time itself, which always
 * came back empty since radio.c had already drained it, so a phone's
 * ssid/pass override was silently discarded for `wifi.up`; contact_run_
 * contact() never even looked, so `contact`'s override was dropped too).
 * On a pending-verify boot that cannot reach the server after 3 attempts,
 * this clears NVS "fw_pending" and calls esp_restart() instead of
 * returning (the bootloader then rolls back the bad image) -- it never
 * returns in that case, and it never sleeps. */
contact_end_t contact_run(contact_reason_t reason, contact_mode_t mode, const char *ssid, const char *pass);

/* The dusty_ble hooks table (preview/thumb/frame/spool_list/shoot/
 * handoff/live/time_set/cfg.get/cfg.set/cfg.schema/prov.get/prov.set/
 * wifi_scan) and the dusty_control (HTTP) hooks table -- one
 * implementation shared between the two radios,
 * per docs/phone_app_plan.md §3 ("contact.c's hooks table is shared by
 * HTTP and BLE"). Neither table's .device/.ble_key/.fw_version are filled
 * in here: radio.c copies the struct and sets those from dusty_ident_t
 * before each dusty_ble_start()/dusty_control_start(). */
const dusty_ble_hooks_t *contact_ble_hooks(void);
const dusty_control_hooks_t *contact_http_hooks(void);

/* Radio-state fields folded into GET /status (docs/phone_app_plan.md §2):
 * radio.c calls this before/at the start of each phase. contact_mode is
 * "view"|"contact" (NOT reusing the JSON key "mode", which is already
 * dc_cfg_t's tier-2 live|setup mode in the same object). */
void contact_set_radio_state(const char *radio, const char *contact_mode, int ble_back_in_s, int win_left_s);

/* Consumed by radio.c's state machine: `live` (GET /live or the BLE `live`
 * op) ends the WHOLE window, from either radio -- both hook tables' .live
 * points at the same underlying flag. Returns 1 (and clears it) if a
 * `live` was requested since the last check. */
int contact_take_live(void);

/* Consumed by radio.c right after a BLE session that ended because
 * hooks.handoff() ran (dusty_ble.h: called only once the link is quiet).
 * Returns 1 (and clears the record) if a handoff was requested;
 * mode_out/ssid_out/pass_out (may be NULL) receive what was recorded. */
int contact_take_handoff(char *mode_out, size_t mode_cap, char *ssid_out, size_t ssid_cap, char *pass_out, size_t pass_cap);

#ifdef __cplusplus
}
#endif
#endif
