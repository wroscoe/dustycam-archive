/* dusty_ble: the NimBLE peripheral side of dustyphone (docs/
 * phone_app_plan.md §2, §3). One connection, JSON request/response +
 * framed notify streams (ble_frame.h), HMAC-challenge auth, no pairing.
 *
 * Lifecycle: dusty_ble_start() brings the controller+host up, adds the
 * GATT service and starts advertising; dusty_ble_stop() tears all of that
 * back down (adv stop, terminate any connection, nimble_port_stop(),
 * nimble_port_deinit()) and blocks until esp_bt_controller_get_status()
 * reports ESP_BT_CONTROLLER_STATUS_IDLE, logging the result. Never call
 * esp_bt_mem_release()/esp_bt_controller_mem_release(ESP_BT_MODE_BLE):
 * both are one-way on this target and would make a later dusty_ble_start()
 * impossible for the rest of the boot.
 *
 * Every op except `hello`/`auth` is refused with err:"auth" until the
 * phone completes the HMAC challenge (§2 Session) against hooks->ble_key.
 *
 * `prov.set` (docs/phone_app_plan.md §2, decision 5, §6 P1): a NULL/empty
 * hooks->device means unprovisioned. An unprovisioned board accepts a
 * PLAINTEXT body (the request's own top-level fields, no envelope) for as
 * long as it stays unprovisioned and hasn't used one yet -- i.e. the
 * whole unprovisioned radio window the caller (radio.c) grants, not a
 * fixed cutoff from dusty_ble_start() (review finding: 120 s was wrong,
 * it's the caller's whole unprovisioned-window duration, e.g. 600 s).
 * Every other case (already provisioned, or a plaintext prov.set already
 * landed) requires the encrypted envelope:
 *   env = base64( IV(DUSTY_BLE_PROV_ENV_IV_LEN bytes)
 *               || AES-256-GCM(sk, json)
 *               || TAG(DUSTY_BLE_PROV_ENV_TAG_LEN bytes) )
 *   sk  = HMAC-SHA256(ble_key, "sk" || cam_nonce || phone_nonce)   (32 B)
 * IV || ciphertext || TAG are concatenated in that order BEFORE
 * base64-encoding; no AAD. `json` (plaintext or decrypted) is
 * `{device,ssid,pass,host,port,tls,token,ble_key}` either way -- the
 * phone app's encoder must match this layout byte-for-byte.
 */
#ifndef DUSTY_BLE_H
#define DUSTY_BLE_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define DUSTY_BLE_PROV_ENV_IV_LEN 12
#define DUSTY_BLE_PROV_ENV_TAG_LEN 16

typedef struct {
    /* 32 raw bytes (not hex/text) -- the owner's ble_key. Required
     * (non-NULL, 32 B) or every session fails auth. */
    const uint8_t *ble_key;
    /* Adv name is "dc-<device>", or "dc-new-<mac4>" when device is empty
     * (unprovisioned). Also echoed in `info` as "device". */
    const char *device;
    const char *fw_version; /* echoed in `info` as "v" */

    /* GET-shaped: fill buf with a JSON object, return length or <0. */
    int (*status_json)(char *buf, size_t n);

    /* `preview`: lazy camera init, one capture, deinit (docs/
     * phone_app_plan.md decision 10). *jpg is malloc'd by the hook; this
     * component sends it on the data channel and free()s it. Returns 1 on
     * success (jpg/jpg_len/focus/lum all filled), 0 on failure (e.g. sd/
     * camera error -- the op answers err:"sd" or a generic failure). */
    int (*preview)(uint8_t **jpg, size_t *jpg_len, float *focus, int *lum);

    /* `thumb`/`frame`: decode (thumb) or read verbatim (frame) the spooled
     * JPEG at boot/seq from the SD card, no sensor. *jpg malloc'd by the
     * hook, freed by this component. Returns 1 on success, 0 if the file
     * is missing (err:"nofile"), -1 if a drain currently holds the SD
     * card's bus mutex (err:"busy" -- the hook should take it non-blocking
     * and report this rather than block ble_req). Same signature as
     * dusty_control's `frame`/`thumb` hooks -- share one implementation
     * (docs/phone_app_plan.md §3 "contact.c's hooks table is shared by
     * HTTP and BLE"). */
    int (*thumb)(uint32_t boot, uint32_t seq, uint8_t **jpg, size_t *jpg_len);
    int (*frame)(uint32_t boot, uint32_t seq, uint8_t **jpg, size_t *jpg_len);

    /* `spool.list`: req_json is the request object verbatim (tier/n/after
     * per §2); write the `{"items":[...],"more":bool}` response into
     * out_json. Returns length or <0. */
    int (*spool_list)(const char *req_json, char *out_json, size_t out_cap);

    void (*shoot)(void); /* `shoot`: lazy init/capture/deinit, spool it */

    /* `wifi.up`/`contact`: only RECORD the request (docs/phone_app_plan.md
     * §3) -- mode is "view" or "contact"; ssid/pass may be NULL (use the
     * compiled-in hotspot). Called LAST, after this component's reply +
     * `evt bye` have gone out and the link has been terminated (review
     * finding: calling it first made the caller's "handoff requested" flag
     * visible, and pollable, before the link was actually quiet -- the
     * caller's radio state machine must not tear BLE down out from under
     * an in-flight notify). Still "only records": the caller's state
     * machine is the one that performs the handoff, on its next loop
     * iteration after dusty_ble_stop(). */
    void (*handoff)(const char *mode, const char *ssid, const char *pass);

    /* Optional, side-effect-free: the IP the camera had on the last WIFI
     * phase (or "" / NULL if there hasn't been one yet), so the `wifi.up`/
     * `contact` reply's `expect_ip` can save the app a prompt on cycle 2+.
     * Called once at the START of the handoff, before anything else --
     * unlike `handoff` above, reading this has no side effects and
     * doesn't need to wait for the link to go quiet. */
    const char *(*last_ip)(void);

    void (*live)(void);                      /* `live`: end the window */
    void (*time_set)(int64_t ts, int tz_min); /* `time.set` */

    /* `cfg.schema`/`cfg.get`: fill buf with a JSON object (the
     * <id>.schema.json shape / dc_cfg_to_json respectively), return
     * length or <0. */
    int (*cfg_schema)(char *buf, size_t n);
    int (*cfg_get)(char *buf, size_t n);

    /* `cfg.set`: `json` is the request's "cfg" sub-object, re-serialised
     * to a string (dusty_config_set_local() takes it as-is). *out_cfg
     * gets the new version on success. Returns 1 ok, 0 bad request
     * (malformed cfg object -> err:"badreq"), -1 if a drain is currently
     * running (err:"busy"). */
    int (*cfg_set)(const char *json, int *out_cfg);

    /* `prov.get`: fill buf with the NON-secret identity object
     * (`{"device","host","port","tls","ssid"}` -- no pass/token/ble_key),
     * return length or <0. */
    int (*prov_get)(char *buf, size_t n);

    /* `prov.set`: `json` arrives already plaintext -- dusty_ble has
     * either accepted the request body as-is (inside the unprovisioned
     * presence window) or decrypted the `env` envelope itself (see the
     * file comment above). Parse it as
     * `{device,ssid,pass,host,port,tls,token,ble_key}`, save it (e.g.
     * dusty_ident_save()), and write the new device id into device_out
     * (device_out_cap bytes) for the reply. Returns 1 on success, 0 on a
     * malformed body (err:"badreq"). Do NOT restart from inside this hook:
     * dusty_ble sends the `{"ok":true,"device":...}` reply first, flushes
     * it, and only then sets its internal restart-requested flag -- it
     * never calls esp_restart() itself (see dusty_ble_restart_requested()
     * below). The caller polls that flag after dusty_ble_stop() and
     * performs the actual restart once its own teardown is done. */
    int (*prov_set)(const char *json, char *device_out, size_t device_out_cap);

    /* `wifi.scan`: fill buf with `{"aps":[{"ssid","rssi","ch"},...]}`
     * (dusty_uplink_wifi_scan(), capped at 10 per §2), return length or
     * <0. Runs with BLE still up (decision-9-adjacent risk noted in §7:
     * if this turns out not to be internal-RAM-safe next to the BT
     * controller, it moves to a WIFI-phase `GET /scan` instead). */
    int (*wifi_scan)(char *buf, size_t n);
} dusty_ble_hooks_t;

/* Brings NimBLE up and starts advertising. Safe to call again after a
 * matching dusty_ble_stop(); hooks is copied (the struct, not what it
 * points to -- ble_key/device/fw_version must stay valid until stop()). */
void dusty_ble_start(const dusty_ble_hooks_t *hooks);

/* Tears NimBLE all the way down (see the file comment). Blocks until the
 * controller reports idle. Safe to call when not started. */
void dusty_ble_stop(void);

int dusty_ble_connected(void);

/* 1 if `reboot` or a successful `prov.set` asked for a restart this
 * session (dusty_ble never calls esp_restart() itself -- see the file
 * comment). Check this right after dusty_ble_stop() returns; the flag is
 * cleared again by the next dusty_ble_start(), so the caller must act on
 * it (esp_restart(), after its own camera/SD/Wi-Fi teardown) before
 * starting BLE again. */
int dusty_ble_restart_requested(void);

/* esp_timer_get_time() at the start of the most recent request; 0 if none
 * yet this session. Used for the caller's link-idle timeout. */
int64_t dusty_ble_last_request_us(void);

/* Sends `{"ev":...}` (id 0) on the evt notify characteristic, framed and
 * fragmented like any other message. No-op if not connected or the
 * central hasn't subscribed to evt. */
void dusty_ble_event(const char *json);

/* Sends `n` bytes on the data notify characteristic under request id
 * `id`, with the §2 BIN prefix (total+crc32) on the first fragment, paced
 * on each notify's return + a 2 ms yield. Returns 1 on success, 0 if not
 * connected/subscribed or a notify failed partway through. Exposed
 * directly (not just used internally by preview/thumb/frame) so a future
 * op can stream something ad hoc. */
int dusty_ble_send_data(uint8_t id, const uint8_t *buf, size_t n);

#ifdef __cplusplus
}
#endif
#endif
