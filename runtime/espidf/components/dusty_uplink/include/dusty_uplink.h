/* dusty_uplink: HTTP(S) talk to sensorhub, and the WiFi STA join used to
 * reach it. Contract: docs/camera_standard.md §4, docs/camera_operation.md
 * §5. Blocking calls; run from a task with a few KB of stack headroom
 * (esp_http_client + TLS wants some).
 */
#ifndef DUSTY_UPLINK_H
#define DUSTY_UPLINK_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Configure host/credentials. Safe to call again to change them. */
void dusty_uplink_init(const char *host, int port, int tls, const char *token, const char *device);

/* POST /blob/<device>/<kind>, body streamed from `path` on the mounted
 * filesystem in 4 KB chunks (spool drain: no whole-file heap copy).
 * Content-Type: image/jpeg, X-Meta: meta_json, X-Token, Connection: close.
 * Returns 1 on 2xx, 0 otherwise; *status gets the HTTP status (0 if the
 * request never got a response). status may be NULL. */
int dusty_uplink_post_file(const char *kind, const char *path, const char *meta_json, int *status);

/* Same, from a buffer already in memory (e.g. a live shoot). */
int dusty_uplink_post_blob(const char *kind, const uint8_t *data, size_t len, const char *meta_json);

/* POST /telemetry/<device>, body = json (a JSON object of numbers). */
int dusty_uplink_post_telemetry(const char *json);

/* POST <path> (e.g. "/config/<device>"), body = json
 * (application/json). The response body -- present even on a non-2xx,
 * e.g. a config-push 409's body carries the server's current config for
 * the caller to apply -- is copied into resp (NUL-terminated, truncated
 * to fit); resp/n may be NULL/0 to ignore it. Returns 1 on 2xx, 0
 * otherwise; *status gets the HTTP status. status may be NULL. */
int dusty_uplink_post_json(const char *path, const char *json, char *resp, size_t n, int *status);

/* GET <path> (e.g. "/config/xiaocam1", "/firmware/xiaocam1/version") into
 * buf (NUL-terminated, truncated to fit). Returns 1 on 2xx, 0 otherwise;
 * *status gets the HTTP status. status may be NULL. */
int dusty_uplink_get(const char *path, char *buf, size_t n, int *status);

/* Epoch seconds parsed from the `Date` response header of the most recent
 * request that carried one (any of the calls above); 0 if none yet. */
int64_t dusty_uplink_last_server_time(void);

/* WiFi STA: scan for `ssid` then connect, retrying on disconnect, up to
 * timeout_s. Idempotent across off/join cycles (docs/phone_app_plan.md
 * §3, P0.1b: 10 BLE<->Wi-Fi handoff cycles with no reboot). Returns 1 once
 * an IP is obtained, 0 on timeout. */
int dusty_uplink_wifi_join(const char *ssid, const char *pass, int timeout_s);

/* Full teardown, not just disconnect+stop: esp_wifi_disconnect,
 * esp_wifi_stop, esp_wifi_deinit, then destroys the default STA netif and
 * unregisters this component's event handlers, so a later
 * dusty_uplink_wifi_join() re-inits cleanly and BLE gets its internal RAM
 * back (docs/phone_app_plan.md decision 9, "sequential radios"). Safe to
 * call when not joined/started. */
void dusty_uplink_wifi_off(void);
const char *dusty_uplink_ip(void);   /* "0.0.0.0" when not joined */
int dusty_uplink_rssi(void);         /* 0 when not joined */

typedef struct {
    char ssid[33];
    int rssi;
    int ch;
} dusty_wifi_ap_t;

/* Ad-hoc Wi-Fi scan for `wifi.scan` (docs/phone_app_plan.md §2): its own
 * self-contained esp_wifi_init -> set STA -> start -> blocking scan ->
 * stop -> deinit -> netif destroy, entirely independent of
 * dusty_uplink_wifi_join()'s state (that call's globals are untouched).
 * Meant to run with BLE still up and Wi-Fi otherwise off (sequential
 * radios) -- measure internal free before/after at the call site if you
 * care whether it's actually coexistence-safe on this target. Blocking,
 * takes a few seconds. Returns the number of APs written to out (<= max
 * and <= 10 per §2), or 0 on failure. */
int dusty_uplink_wifi_scan(dusty_wifi_ap_t *out, int max);

#ifdef __cplusplus
}
#endif
#endif
