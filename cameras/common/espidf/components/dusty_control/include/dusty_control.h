/* dusty_control: the board's control plane, docs/camera_standard.md §4 /
 * "Control plane on the board" and the setup page,
 * docs/camera_standard.md §3. One esp_http_server on :8266. Every hook may
 * be NULL; a NULL hook answers 501 (or, for /stream, closes the
 * connection without a frame).
 *
 * Also runs a UDP discovery beacon (docs/phone_app_plan.md: the user must
 * never type an IP) while the control plane is up: once a second, a small
 * JSON announcement to 255.255.255.255:8267 and the STA netif's
 * subnet-directed broadcast, `{"dc":1,"device":"<id>","ip":"<a.b.c.d>",
 * "port":8266,"radio":"wifi"}`. Set hooks->device to enable it; NULL/empty
 * means no beacon.
 */
#ifndef DUSTY_CONTROL_H
#define DUSTY_CONTROL_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    /* Fill buf with a JSON object (device, mode, counters, cfg, night,
     * clock, rssi, ip, ...) for GET /status. Returns the length written,
     * or <0 on failure. */
    int (*status_json)(char *buf, size_t n);

    /* Hand back one JPEG frame for the MJPEG stream (small/preview-sized;
     * the board decides). stream_release() is called once the server has
     * finished writing that frame, before the next stream_frame() call. */
    int (*stream_frame)(uint8_t **jpg, size_t *n);
    void (*stream_release)(void);

    void (*shoot)(void);   /* POST /shoot: capture + deliver one full frame now */
    void (*refresh)(void); /* POST /refresh: pull /config/<device> now */
    void (*live)(void);    /* GET /live: end setup, resume live mode */

    /* POST /ble (docs/phone_app_plan.md §3): end the WIFI phase now and go
     * back to BLE. Replies {"ok":true,"radio":"ble","in_s":2} BEFORE this
     * hook runs, then calls it; the hook should behave like `live` plus
     * whatever bookkeeping marks the radio state machine's next loop
     * iteration as BLE instead of sleep. NULL answers 501, same as any
     * other hook. */
    void (*ble)(void);

    /* Optional, side-effect-free: return nonzero while a drain currently
     * owns the SD card (dusty_control.c review finding, MINOR: POST /ble
     * used to always reply {"in_s":2} even mid-drain, a promise it then
     * couldn't honour until the drain finished). When this returns
     * nonzero, POST /ble answers 503 instead of calling `ble` above; NULL
     * means "never draining". */
    int (*draining)(void);

    /* GET /spool?tier=&n=&after=: req_json is built from the query string
     * as `{"tier":"...","n":N,"after":"..."}` (defaults tier="spool",
     * n=24, after=""); write the `{"items":[...],"more":bool}` response
     * into out_json. Returns length or <0. Same shape as dusty_ble's
     * `spool.list` hook -- share one implementation between the two hook
     * tables (docs/phone_app_plan.md §3 "contact.c's hooks table is
     * shared by HTTP and BLE"). */
    int (*spool_list)(const char *req_json, char *out_json, size_t out_cap);

    /* GET /spool/<boot>/<seq>.jpg (full frame) and GET /thumb/<boot>/<seq>.jpg
     * (decoded 200x150 preview). *jpg is malloc'd by the hook and freed
     * here once streamed out in ~4 KB chunks. Returns 1 on success, 0 if
     * not found (404), -1 if a drain currently holds the SD card's bus
     * mutex (503 -- the hook is expected to take it non-blocking and
     * report this rather than block the httpd worker). Same signature as
     * dusty_ble's `frame`/`thumb` hooks -- share one implementation. */
    int (*frame)(uint32_t boot, uint32_t seq, uint8_t **jpg, size_t *jpg_len);
    int (*thumb)(uint32_t boot, uint32_t seq, uint8_t **jpg, size_t *jpg_len);

    /* Device id for the UDP discovery beacon (docs/phone_app_plan.md: the
     * user must never type an IP). NULL/empty -> no beacon is sent. Not a
     * callback: a plain string, copied in dusty_control_start(). */
    const char *device;
} dusty_control_hooks_t;

void dusty_control_start(const dusty_control_hooks_t *h);
void dusty_control_stop(void);

/* esp_timer_get_time() at the start of the most recent request; used for
 * contact_idle_s. 0 if no request has arrived yet. */
int64_t dusty_control_last_request_us(void);

#ifdef __cplusplus
}
#endif
#endif
