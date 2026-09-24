/* radio: the docs/phone_app_plan.md §3 radio state machine -- sequential
 * BLE<->Wi-Fi, never concurrent (decision 9). One call per "window"
 * (button press, cold boot, or a pending-verify boot); app_main() decides
 * when to call this at all -- most wakes never touch a radio.
 */
#ifndef XIAOCAM1_RADIO_H
#define XIAOCAM1_RADIO_H

#include "contact.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Review finding (BLOCKER): dusty_ble must never esp_restart() itself --
 * radio.c is the one that knows whether a camera/SD/Wi-Fi session is up
 * and needs to be torn down first. RADIO_END_RESTART tells main.c that a
 * `reboot` or a successful `prov.set` asked for a restart during this
 * window (dusty_ble_restart_requested() was true after dusty_ble_stop());
 * main.c must record NVS "first_contact"=1 (so the reboot's first wake
 * opens a window even though it isn't a cold boot or a button wake -- see
 * main.c), tear down its own camera/SD/Wi-Fi state, and esp_restart()
 * itself. RADIO_END_NORMAL is the ordinary "window over, go to sleep"
 * exit. */
typedef enum {
    RADIO_END_NORMAL,
    RADIO_END_RESTART,
} radio_end_t;

/* Blocks until the window is over: NimBLE deinit'd, Wi-Fi deinit'd, both
 * radios idle, on every exit path (the "radio:" heap line is logged at
 * every transition). Never touches the camera itself -- contact.c's
 * hooks lazily reuse whatever main.c already has open around this call,
 * or lazy-init/deinit their own session via cam_ensure()/cam_finish()
 * (see contact.c's header comment on that deliberate deviation from
 * decision 10 for this app). */
radio_end_t radio_window_run(contact_reason_t reason);

#ifdef __cplusplus
}
#endif
#endif
