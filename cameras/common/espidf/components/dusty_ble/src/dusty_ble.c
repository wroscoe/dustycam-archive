/* dusty_ble.c: NimBLE peripheral for dustyphone (docs/phone_app_plan.md
 * §2, §3). See include/dusty_ble.h for the lifecycle contract.
 *
 * Task layout:
 *  - the NimBLE host task (created by nimble_port_freertos_init, its own
 *    stack) runs the GATT access callback (on_cmd_write): it only
 *    reassembles fragments and hands a completed request off, fast.
 *  - "ble_req" (this file, internal-RAM stack, 6 KB -- it may write NVS in
 *    a later phase) parses JSON and dispatches ops.
 *  - "ble_img" (xTaskCreateWithCaps, INTERNAL stack: hooks may write
 *    NVS and flash writes from a PSRAM stack panic -- see the
 *    macro below) runs preview/thumb/frame/shoot, the ops that touch the
 *    camera or decode a JPEG.
 * Both tasks are created once (lazily, on the first dusty_ble_start()) and
 * left running idle across stop()/start() cycles -- only the NimBLE
 * host/controller are torn down and rebuilt each cycle.
 *
 * Concurrency assumption: exactly one request is ever in flight (the
 * phone-side GattQueue serialises ops), so the single static "pending
 * request" and "image result" buffers below are safe without their own
 * locks -- the NimBLE host task, ble_req and ble_img hand off strictly in
 * that order for a given request.
 */
#include "dusty_ble.h"
#include "ble_frame.h"
#include "ble_auth_internal.h"

#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#include "esp_log.h"
#include "esp_timer.h"
#include "esp_mac.h"
#include "esp_bt.h"
#include "esp_system.h"
#include "esp_heap_caps.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "freertos/idf_additions.h" /* xTaskCreateWithCaps */

#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "host/ble_uuid.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"

#include "cJSON.h"
#include "mbedtls/base64.h"

/* Declared by components/bt/host/nimble/nimble/nimble/host/store/config
 * (built as part of the "bt" component whenever the NimBLE host is
 * enabled); not exposed via a public include path, so forward-declared
 * here -- the same thing every IDF NimBLE example does. */
void ble_store_config_init(void);

static const char *TAG = "dusty_ble";

/* ---------------- GATT UUIDs (docs/phone_app_plan.md §2) ----------------
 * Base "7d1e00XX-dc0a-4c9b-8f6e-2e9a0c5d1b00"; BLE_UUID128_INIT wants the
 * bytes in over-the-air (little-endian) order, i.e. the string's bytes
 * reversed. */
#define DUSTY_UUID(xx) BLE_UUID128_INIT(0x00, 0x1b, 0x5d, 0x0c, 0x9a, 0x2e, 0x6e, 0x8f, \
                                         0x9b, 0x4c, 0x0a, 0xdc, (xx), 0x00, 0x1e, 0x7d)

static const ble_uuid128_t s_svc_uuid = DUSTY_UUID(0x01);
static const ble_uuid128_t s_chr_info_uuid = DUSTY_UUID(0x02);
static const ble_uuid128_t s_chr_cmd_uuid = DUSTY_UUID(0x03);
static const ble_uuid128_t s_chr_rsp_uuid = DUSTY_UUID(0x04);
static const ble_uuid128_t s_chr_data_uuid = DUSTY_UUID(0x05);
static const ble_uuid128_t s_chr_evt_uuid = DUSTY_UUID(0x06);

static uint16_t s_val_info, s_val_cmd, s_val_rsp, s_val_data, s_val_evt;

/* Placeholder until dusty_config/dusty_ident lands (P1): how long the app
 * should expect before the camera might come back to BLE after a
 * handoff. Real value will come from cfg->hotspot_join_s + the WIFI
 * phase's own timeout. */
#define DUSTY_BLE_HANDOFF_BACK_S 60

/* ---------------- state ---------------- */

static dusty_ble_hooks_t s_hooks;
static volatile int s_running;
static volatile int s_stopping;
/* Set for the deliberate disconnect at the end of handle_handoff()/
 * handle_live(): without this, the DISCONNECT event fires (almost
 * immediately -- the terminate is local) while dusty_ble is still
 * s_running and not yet s_stopping, and would otherwise re-advertise for
 * the few hundred ms until the caller's loop notices the handoff/live
 * flag and calls dusty_ble_stop(). */
static volatile int s_going_quiet;
static volatile int s_connected;
static uint16_t s_conn_handle = BLE_HS_CONN_HANDLE_NONE;
static uint16_t s_mtu = 23;
static uint8_t s_own_addr_type;
static volatile int64_t s_last_request_us;

static int s_sub_rsp, s_sub_data, s_sub_evt;

static int s_adv_fast;
static esp_timer_handle_t s_adv_timer;
static uint8_t s_mfg_flags;
static char s_adv_name[32];

/* auth session (docs/phone_app_plan.md §2 "Session") */
static uint8_t s_cam_nonce[BLE_AUTH_NONCE_LEN];
static uint8_t s_phone_nonce[BLE_AUTH_NONCE_LEN];
static int s_have_phone_nonce;
static int s_authed;

/* prov.set presence window (docs/phone_app_plan.md decision 5, dusty_ble.h
 * file comment): "unprovisioned and not used yet" -- see dusty_ble.h's
 * file comment for why this isn't a fixed time-from-start cutoff. */
static int s_prov_set_used;
static int s_provisioned; /* snapshotted from hooks.device at dusty_ble_start() */
/* Set by handle_reboot()/handle_prov_set() instead of calling
 * esp_restart() directly (review finding, BLOCKER): the caller owns
 * camera/SD/Wi-Fi teardown and must get the chance to do it first. Poll
 * dusty_ble_restart_requested() after dusty_ble_stop() returns. */
static volatile int s_restart_requested;

/* Scratch for prov.set's decrypted plaintext (BLE_FRAME_LIMIT_REQUEST: the
 * plaintext can't be longer than the whole request). Static, not on the
 * 6 KB ble_req stack. */
static uint8_t s_prov_plain[BLE_FRAME_LIMIT_REQUEST];

/* cmd reassembly */
static uint8_t s_req_reasm_buf[BLE_FRAME_LIMIT_REQUEST];
static ble_frame_reassembler_t s_req_reasm;
static uint8_t s_pending_req[BLE_FRAME_LIMIT_REQUEST + 1];
static size_t s_pending_req_len;
static uint8_t s_pending_req_id;
/* Set the instant s_pending_req is handed to ble_req, cleared only after
 * process_request() returns -- on_cmd_write() (NimBLE host task) checks
 * this before overwriting the single pending-request slot (review
 * finding: a second complete request arriving while ble_req was still
 * working the first one used to silently clobber it). */
static volatile int s_req_busy;
static SemaphoreHandle_t s_req_ready;
static TaskHandle_t s_req_task_handle;

/* Errors that on_cmd_write() (NimBLE host task, small stack) would
 * otherwise have to send itself -- deferred to ble_req instead so the
 * host task callback never calls into notify_sink()'s retry loop (review
 * finding: that loop can now legitimately take up to ~2 s). Small/short
 * strings only; best-effort (a dropped deferred error just means the
 * phone times out and retries that id, same as if the write had been
 * lost on the air). */
typedef struct {
    uint8_t id;
    char err[16];
} pending_err_t;
static QueueHandle_t s_err_q;

/* Big response staging: kept static, not on the 6 KB request-task stack
 * (a spool.list or status response can approach BLE_FRAME_LIMIT_RESPONSE). */
static char s_hook_buf[BLE_FRAME_LIMIT_RESPONSE];
static char s_rsp_buf[BLE_FRAME_LIMIT_RESPONSE + 64];

/* image worker (preview/thumb/frame/shoot) */
typedef enum { IMG_OP_PREVIEW, IMG_OP_THUMB, IMG_OP_FRAME, IMG_OP_SHOOT } img_op_t;
typedef struct {
    img_op_t op;
    uint32_t boot, seq;
    uint32_t gen; /* see s_img_gen below */
} img_work_t;
typedef struct {
    int ok;
    uint8_t *jpg;
    size_t jpg_len;
    float focus;
    int lum;
    uint32_t gen;
} img_result_t;

static QueueHandle_t s_img_q;
static SemaphoreHandle_t s_img_done;
static img_result_t s_img_res;
static TaskHandle_t s_img_task_handle;
/* Review finding (MINOR): a run_img_op() that times out used to leave the
 * worker's eventual (late) result sitting in s_img_res/s_img_done -- the
 * NEXT run_img_op() call would then immediately consume that stale give
 * and hand the caller a leftover JPEG from the timed-out op instead of
 * its own. Every submission gets a fresh generation number; a result
 * whose gen doesn't match is discarded (its jpg freed) rather than
 * accepted. */
static volatile uint32_t s_img_gen;

/* The image worker's stack is INTERNAL RAM on purpose. It was in PSRAM
 * (CONFIG_FREERTOS_TASK_CREATE_ALLOW_EXT_MEM) until the first real shoot
 * with a card mounted panicked with
 *   assert failed: spi_flash_disable_interrupts_caches_and_other_cpu
 *   (esp_task_stack_is_sane_cache_disabled())
 * -- the shoot hook's spool bookkeeping writes NVS, and flash writes are
 * not allowed from a task whose stack lives in PSRAM (2026-09-15). Any
 * hook may end up writing NVS, so no hook runs on an external stack. */
#define BLE_IMG_TASK_CAPS (MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT)

/* ---------------- forward decls ---------------- */
static void start_advertising(void);
static void resume_advertising_fast(void);
static int gatt_access_cb(uint16_t conn_handle, uint16_t attr_handle,
                           struct ble_gatt_access_ctxt *ctxt, void *arg);

static const struct ble_gatt_svc_def s_gatt_svcs[] = {
    {
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = &s_svc_uuid.u,
        .characteristics = (struct ble_gatt_chr_def[]){
            { .uuid = &s_chr_info_uuid.u, .access_cb = gatt_access_cb,
              .flags = BLE_GATT_CHR_F_READ, .val_handle = &s_val_info },
            { .uuid = &s_chr_cmd_uuid.u, .access_cb = gatt_access_cb,
              .flags = BLE_GATT_CHR_F_WRITE | BLE_GATT_CHR_F_WRITE_NO_RSP, .val_handle = &s_val_cmd },
            { .uuid = &s_chr_rsp_uuid.u, .access_cb = gatt_access_cb,
              .flags = BLE_GATT_CHR_F_NOTIFY, .val_handle = &s_val_rsp },
            { .uuid = &s_chr_data_uuid.u, .access_cb = gatt_access_cb,
              .flags = BLE_GATT_CHR_F_NOTIFY, .val_handle = &s_val_data },
            { .uuid = &s_chr_evt_uuid.u, .access_cb = gatt_access_cb,
              .flags = BLE_GATT_CHR_F_NOTIFY, .val_handle = &s_val_evt },
            { 0 },
        },
    },
    { 0 },
};

/* ---------------- notify plumbing ---------------- */

/* review finding (BLOCKER): a thumb/frame transfer pushes ~250 KB/s of
 * fragments into a link that carries maybe ~40 KB/s, so ble_gatts_ram
 * notify buffers (msys) run out well before the transfer finishes --
 * ble_gatts_notify_custom() (or the ble_hs_mbuf_from_flat() alloc before
 * it) returns BLE_HS_ENOMEM/NULL almost immediately into any real
 * transfer. Retry with a short delay instead of aborting the whole
 * message on the first transient allocation failure; only give up (return
 * -1) on a real error or after ~2 s stuck on one fragment. Note
 * ble_gatts_notify_custom() consumes its mbuf on every call including
 * failure, so each retry needs a fresh one. */
#define NOTIFY_RETRY_BUDGET_US (2LL * 1000000)

/* bench counters: reset by dusty_ble_send_data, reported when it finishes */
static uint32_t s_nf_sent, s_nf_retry;

static int notify_sink(const uint8_t *frame, size_t frame_len, void *ctx)
{
    uint16_t attr_handle = (uint16_t)(uintptr_t)ctx;
    int64_t deadline_us = esp_timer_get_time() + NOTIFY_RETRY_BUDGET_US;

    for (;;) {
        if (s_conn_handle == BLE_HS_CONN_HANDLE_NONE) return -1;

        struct os_mbuf *om = ble_hs_mbuf_from_flat(frame, frame_len);
        if (!om) {
            if (esp_timer_get_time() >= deadline_us) {
                ESP_LOGW(TAG, "notify_sink: mbuf alloc exhausted for %.2fs, giving up",
                         (double)NOTIFY_RETRY_BUDGET_US / 1e6);
                return -1;
            }
            vTaskDelay(pdMS_TO_TICKS(5));
            continue;
        }

        int rc = ble_gatts_notify_custom(s_conn_handle, attr_handle, om);
        if (rc == 0) {
            s_nf_sent++;
            /* Pace on the call's return + a short yield (docs/
             * phone_app_plan.md §3): keeps a big transfer from starving
             * other tasks. */
            vTaskDelay(pdMS_TO_TICKS(2));
            return 0;
        }
        if (rc == BLE_HS_ENOMEM && esp_timer_get_time() < deadline_us) {
            s_nf_retry++;
            vTaskDelay(pdMS_TO_TICKS(5));
            continue;
        }
        ESP_LOGW(TAG, "notify_sink: ble_gatts_notify_custom rc=%d, giving up", rc);
        return -1;
    }
}

#ifndef BLE_FRAG_MTU_CAP
#define BLE_FRAG_MTU_CAP 247
#endif
static int send_on(uint16_t attr_handle, uint8_t id, uint8_t flags, const uint8_t *payload, size_t len)
{
    if (s_conn_handle == BLE_HS_CONN_HANDLE_NONE) return 0;
    /* Permanent, not a knob: bench-confirmed 2026-09-15 on a Pixel 6.
     * Notifications larger than one LL PDU with Data Length Extension are
     * lost between this ESP32-S3 NimBLE stack (IDF 5.5) and the Pixel --
     * 514 B notifies (at the negotiated 517 B ATT MTU) never arrived
     * (ble_gatts_notify_custom() returned rc=0 on every call; the phone
     * only ever saw the final short fragment), while 244 B payloads
     * arrive 100% at 65-85 KB/s. Cap the frame at one LL packet with DLE
     * (247 = 251 B LL payload - 4 B L2CAP header) regardless of the
     * negotiated ATT MTU. */
    uint16_t eff_mtu = s_mtu > BLE_FRAG_MTU_CAP ? BLE_FRAG_MTU_CAP : s_mtu;
    int rc = ble_frame_send(id, flags, payload, len, eff_mtu, notify_sink, (void *)(uintptr_t)attr_handle);
    return rc >= 0 ? 1 : 0;
}

static void send_err(uint8_t id, const char *err, const char *msg)
{
    char buf[192];
    int n = msg ? snprintf(buf, sizeof(buf), "{\"id\":%u,\"ok\":false,\"err\":\"%s\",\"msg\":\"%s\"}", id, err, msg)
                : snprintf(buf, sizeof(buf), "{\"id\":%u,\"ok\":false,\"err\":\"%s\"}", id, err);
    if (n > 0) send_on(s_val_rsp, id, BLE_FRAME_FLAG_ERR, (const uint8_t *)buf, (size_t)n);
}

static void send_ok(uint8_t id)
{
    char buf[32];
    int n = snprintf(buf, sizeof(buf), "{\"id\":%u,\"ok\":true}", id);
    send_on(s_val_rsp, id, 0, (const uint8_t *)buf, (size_t)n);
}

int dusty_ble_send_data(uint8_t id, const uint8_t *buf, size_t n)
{
    if (s_conn_handle == BLE_HS_CONN_HANDLE_NONE) return 0;
    uint32_t crc = ble_crc32(0, buf, n);
    uint8_t *tmp = heap_caps_malloc(n + BLE_FRAME_BIN_PREFIX_LEN, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (!tmp) tmp = heap_caps_malloc(n + BLE_FRAME_BIN_PREFIX_LEN, MALLOC_CAP_8BIT); /* fall back to internal */
    if (!tmp) {
        ESP_LOGE(TAG, "send_data: alloc %u B failed", (unsigned)(n + BLE_FRAME_BIN_PREFIX_LEN));
        return 0;
    }
    ble_frame_bin_prefix_write(tmp, (uint32_t)n, crc);
    if (n) memcpy(tmp + BLE_FRAME_BIN_PREFIX_LEN, buf, n);
    s_nf_sent = s_nf_retry = 0;
    int64_t t0 = esp_timer_get_time();
    int ok = send_on(s_val_data, id, BLE_FRAME_FLAG_BIN, tmp, n + BLE_FRAME_BIN_PREFIX_LEN);
    int64_t dt = esp_timer_get_time() - t0;
    ESP_LOGI(TAG, "send_data id=%u: %u B, %lu frags, %lu enomem retries, %lld ms, mtu=%u, ok=%d",
             id, (unsigned)n, (unsigned long)s_nf_sent, (unsigned long)s_nf_retry,
             (long long)(dt / 1000), (unsigned)s_mtu, ok);
    free(tmp);
    return ok;
}

void dusty_ble_event(const char *json)
{
    if (!json) return;
    send_on(s_val_evt, 0, 0, (const uint8_t *)json, strlen(json));
}

int dusty_ble_connected(void) { return s_connected; }
int dusty_ble_restart_requested(void) { return s_restart_requested; }
int64_t dusty_ble_last_request_us(void) { return s_last_request_us; }

/* ---------------- image worker task ---------------- */

#define IMG_OP_TIMEOUT_MS 15000

/* Returns 1 once s_img_res has this op's result, 0 if the worker was
 * already busy with a previous op (its queue is depth 1) or didn't finish
 * within IMG_OP_TIMEOUT_MS -- callers must answer err:"busy" rather than
 * block the request task (and the phone) forever on a wedged camera. */
static int run_img_op(img_work_t *w)
{
    uint32_t my_gen = ++s_img_gen;
    w->gen = my_gen;
    if (xQueueSend(s_img_q, w, 0) != pdTRUE) {
        ESP_LOGW(TAG, "run_img_op: worker still busy with a previous op (op=%d)", (int)w->op);
        return 0;
    }

    TickType_t start = xTaskGetTickCount();
    TickType_t budget = pdMS_TO_TICKS(IMG_OP_TIMEOUT_MS);
    for (;;) {
        TickType_t elapsed = xTaskGetTickCount() - start;
        TickType_t remaining = elapsed < budget ? budget - elapsed : 0;
        if (xSemaphoreTake(s_img_done, remaining) != pdTRUE) {
            ESP_LOGE(TAG, "run_img_op: worker did not respond within %ds (op=%d) -- possibly wedged",
                     IMG_OP_TIMEOUT_MS / 1000, (int)w->op);
            return 0;
        }
        if (s_img_res.gen == my_gen) return 1;
        /* A result from an earlier op that timed out on some previous
         * call finally landed -- discard it (freeing its jpg so it
         * doesn't leak) and keep waiting for ours, up to the same
         * overall budget. */
        ESP_LOGW(TAG, "run_img_op: discarding stale result (gen %u, wanted %u)", s_img_res.gen, my_gen);
        free(s_img_res.jpg);
        s_img_res.jpg = NULL;
        if (remaining == 0) return 0;
    }
}

static void img_task(void *arg)
{
    (void)arg;
    img_work_t w;
    for (;;) {
        if (xQueueReceive(s_img_q, &w, portMAX_DELAY) != pdTRUE) continue;
        img_result_t res;
        memset(&res, 0, sizeof(res));
        switch (w.op) {
        case IMG_OP_PREVIEW:
            if (s_hooks.preview) res.ok = s_hooks.preview(&res.jpg, &res.jpg_len, &res.focus, &res.lum);
            break;
        case IMG_OP_THUMB:
            if (s_hooks.thumb) res.ok = s_hooks.thumb(w.boot, w.seq, &res.jpg, &res.jpg_len);
            break;
        case IMG_OP_FRAME:
            if (s_hooks.frame) res.ok = s_hooks.frame(w.boot, w.seq, &res.jpg, &res.jpg_len);
            break;
        case IMG_OP_SHOOT:
            if (s_hooks.shoot) { s_hooks.shoot(); res.ok = 1; }
            break;
        }
        res.gen = w.gen;
        s_img_res = res;
        xSemaphoreGive(s_img_done);
    }
}

/* ---------------- op handlers ---------------- */

static int parse_boot_seq(cJSON *req, uint32_t *boot, uint32_t *seq)
{
    cJSON *bj = cJSON_GetObjectItemCaseSensitive(req, "boot");
    cJSON *sj = cJSON_GetObjectItemCaseSensitive(req, "seq");
    if (!cJSON_IsNumber(bj) || !cJSON_IsNumber(sj)) return 0;
    *boot = (uint32_t)bj->valuedouble;
    *seq = (uint32_t)sj->valuedouble;
    return 1;
}

static void handle_hello(cJSON *req, uint8_t id)
{
    cJSON *pnj = cJSON_GetObjectItemCaseSensitive(req, "pn");
    const char *pn = cJSON_IsString(pnj) ? pnj->valuestring : NULL;
    if (!pn || ble_auth_hex_decode(pn, s_phone_nonce, BLE_AUTH_NONCE_LEN) != 0) {
        send_err(id, "badreq", "pn");
        return;
    }
    s_have_phone_nonce = 1;
    char nonce_hex[BLE_AUTH_NONCE_LEN * 2 + 1];
    ble_auth_hex_encode(s_cam_nonce, BLE_AUTH_NONCE_LEN, nonce_hex);
    char buf[96];
    int n = snprintf(buf, sizeof(buf), "{\"id\":%u,\"ok\":true,\"nonce\":\"%s\"}", id, nonce_hex);
    send_on(s_val_rsp, id, 0, (const uint8_t *)buf, (size_t)n);
}

static void handle_auth(cJSON *req, uint8_t id)
{
    if (!s_have_phone_nonce) {
        send_err(id, "badreq", "no hello");
        return;
    }
    cJSON *macj = cJSON_GetObjectItemCaseSensitive(req, "mac");
    const char *mac_hex = cJSON_IsString(macj) ? macj->valuestring : NULL;
    uint8_t mac_given[BLE_AUTH_HMAC_LEN];
    if (!mac_hex || ble_auth_hex_decode(mac_hex, mac_given, BLE_AUTH_HMAC_LEN) != 0) {
        send_err(id, "badreq", "mac");
        return;
    }
    if (!s_hooks.ble_key) {
        send_err(id, "auth", NULL);
        return;
    }
    uint8_t msg[BLE_AUTH_NONCE_LEN * 2];
    memcpy(msg, s_cam_nonce, BLE_AUTH_NONCE_LEN);
    memcpy(msg + BLE_AUTH_NONCE_LEN, s_phone_nonce, BLE_AUTH_NONCE_LEN);
    uint8_t expect[BLE_AUTH_HMAC_LEN];
    ble_auth_hmac_sha256(s_hooks.ble_key, BLE_AUTH_KEY_LEN, msg, sizeof(msg), expect);

    if (ble_auth_consteq(mac_given, expect, BLE_AUTH_HMAC_LEN)) {
        s_authed = 1;
        send_ok(id);
    } else {
        s_authed = 0;
        send_err(id, "auth", NULL);
    }
}

static void handle_status(uint8_t id)
{
    if (!s_hooks.status_json) {
        send_err(id, "unsupported", NULL);
        return;
    }
    int hn = s_hooks.status_json(s_hook_buf, sizeof(s_hook_buf));
    if (hn < 2 || s_hook_buf[0] != '{' || s_hook_buf[hn - 1] != '}') {
        send_err(id, "badreq", "status");
        return;
    }
    s_hook_buf[hn - 1] = '\0';
    int n = snprintf(s_rsp_buf, sizeof(s_rsp_buf), "{\"id\":%u,\"ok\":true,%s}", id, s_hook_buf + 1);
    if (n <= 0 || (size_t)n >= sizeof(s_rsp_buf)) {
        send_err(id, "toolarge", NULL);
        return;
    }
    send_on(s_val_rsp, id, 0, (const uint8_t *)s_rsp_buf, (size_t)n);
}

static void handle_spool_list(uint8_t id)
{
    if (!s_hooks.spool_list) {
        send_err(id, "unsupported", NULL);
        return;
    }
    int hn = s_hooks.spool_list((const char *)s_pending_req, s_hook_buf, sizeof(s_hook_buf));
    if (hn < 2 || s_hook_buf[0] != '{' || s_hook_buf[hn - 1] != '}') {
        send_err(id, "badreq", "spool.list");
        return;
    }
    s_hook_buf[hn - 1] = '\0';
    int n = snprintf(s_rsp_buf, sizeof(s_rsp_buf), "{\"id\":%u,\"ok\":true,%s}", id, s_hook_buf + 1);
    if (n <= 0 || (size_t)n >= sizeof(s_rsp_buf)) {
        send_err(id, "toolarge", NULL);
        return;
    }
    send_on(s_val_rsp, id, 0, (const uint8_t *)s_rsp_buf, (size_t)n);
}

static void handle_thumb(cJSON *req, uint8_t id)
{
    uint32_t boot, seq;
    if (!s_hooks.thumb) {
        send_err(id, "unsupported", NULL);
        return;
    }
    if (!parse_boot_seq(req, &boot, &seq)) {
        send_err(id, "badreq", "boot/seq");
        return;
    }
    img_work_t w = { .op = IMG_OP_THUMB, .boot = boot, .seq = seq };
    if (!run_img_op(&w)) {
        send_err(id, "busy", NULL);
        return;
    }
    if (s_img_res.ok < 0) {
        send_err(id, "busy", NULL); /* drain holds the SD bus mutex */
        return;
    }
    if (!s_img_res.ok) {
        send_err(id, "nofile", NULL);
        return;
    }
    int sent = dusty_ble_send_data(id, s_img_res.jpg, s_img_res.jpg_len);
    free(s_img_res.jpg);
    if (!sent) send_err(id, "busy", NULL); /* link couldn't take the transfer -- don't leave the app waiting */
}

static void handle_frame(cJSON *req, uint8_t id)
{
    uint32_t boot, seq;
    if (!s_hooks.frame) {
        send_err(id, "unsupported", NULL);
        return;
    }
    if (!parse_boot_seq(req, &boot, &seq)) {
        send_err(id, "badreq", "boot/seq");
        return;
    }
    img_work_t w = { .op = IMG_OP_FRAME, .boot = boot, .seq = seq };
    if (!run_img_op(&w)) {
        send_err(id, "busy", NULL);
        return;
    }
    if (s_img_res.ok < 0) {
        send_err(id, "busy", NULL); /* drain holds the SD bus mutex */
        return;
    }
    if (!s_img_res.ok) {
        send_err(id, "nofile", NULL);
        return;
    }
    int sent = dusty_ble_send_data(id, s_img_res.jpg, s_img_res.jpg_len);
    free(s_img_res.jpg);
    if (!sent) send_err(id, "busy", NULL);
}

static void handle_preview(uint8_t id)
{
    if (!s_hooks.preview) {
        send_err(id, "unsupported", NULL);
        return;
    }
    img_work_t w = { .op = IMG_OP_PREVIEW };
    if (!run_img_op(&w)) {
        send_err(id, "busy", NULL);
        return;
    }
    if (!s_img_res.ok) {
        send_err(id, "busy", NULL); /* camera/capture failure -- no closer code in §2's list */
        return;
    }
    int sent = dusty_ble_send_data(id, s_img_res.jpg, s_img_res.jpg_len);
    free(s_img_res.jpg);
    if (!sent) {
        send_err(id, "busy", NULL);
        return;
    }

    char buf[64];
    int n = snprintf(buf, sizeof(buf), "{\"id\":%u,\"ok\":true,\"focus\":%.1f,\"lum\":%d}",
                      id, (double)s_img_res.focus, s_img_res.lum);
    send_on(s_val_rsp, id, 0, (const uint8_t *)buf, (size_t)n);
}

static void handle_shoot(uint8_t id)
{
    if (!s_hooks.shoot) {
        send_err(id, "unsupported", NULL);
        return;
    }
    img_work_t w = { .op = IMG_OP_SHOOT };
    if (!run_img_op(&w)) {
        send_err(id, "busy", NULL);
        return;
    }
    send_ok(id);
}

static void handle_handoff(cJSON *req, uint8_t id, const char *mode)
{
    if (!s_hooks.handoff) {
        send_err(id, "unsupported", NULL);
        return;
    }
    cJSON *sj = cJSON_GetObjectItemCaseSensitive(req, "ssid");
    cJSON *pj = cJSON_GetObjectItemCaseSensitive(req, "pass");
    const char *ssid = cJSON_IsString(sj) ? sj->valuestring : NULL;
    const char *pass = cJSON_IsString(pj) ? pj->valuestring : NULL;

    /* Side-effect-free: safe to call before the link goes quiet. */
    const char *expect_ip = s_hooks.last_ip ? s_hooks.last_ip() : NULL;
    if (!expect_ip) expect_ip = "";

    char buf[192];
    int n = snprintf(buf, sizeof(buf),
                      "{\"id\":%u,\"ok\":true,\"handoff\":\"wifi\",\"expect_ip\":\"%s\",\"back_in_s\":%d,\"mode\":\"%s\"}",
                      id, expect_ip, DUSTY_BLE_HANDOFF_BACK_S, mode);
    send_on(s_val_rsp, id, 0, (const uint8_t *)buf, (size_t)n);

    char evtbuf[96];
    snprintf(evtbuf, sizeof(evtbuf), "{\"ev\":\"bye\",\"reason\":\"handoff\",\"back_in_s\":%d}", DUSTY_BLE_HANDOFF_BACK_S);
    dusty_ble_event(evtbuf);

    s_going_quiet = 1; /* don't let the DISCONNECT handler re-advertise before dusty_ble_stop() lands */
    vTaskDelay(pdMS_TO_TICKS(100)); /* let the notifies above actually flush */
    if (s_conn_handle != BLE_HS_CONN_HANDLE_NONE) {
        ble_gap_terminate(s_conn_handle, BLE_ERR_REM_USER_CONN_TERM);
    }

    /* review finding: call this LAST, after the link is quiet. main.c's
     * radio loop polls the flag this hook sets every 200 ms and would
     * call dusty_ble_stop() as soon as it sees it -- if that happened
     * before the reply/bye/terminate above finished, the stop could land
     * mid-send. "Only records the request" still holds: req/ssid/pass are
     * still valid (req is only freed by process_request, our caller's
     * caller, after we return). */
    s_hooks.handoff(mode, ssid, pass);
}

static void handle_live(uint8_t id)
{
    if (!s_hooks.live) {
        send_err(id, "unsupported", NULL);
        return;
    }
    send_ok(id);
    dusty_ble_event("{\"ev\":\"bye\",\"reason\":\"live\",\"back_in_s\":0}");
    s_going_quiet = 1; /* see the comment on handle_handoff()'s use of this flag */
    vTaskDelay(pdMS_TO_TICKS(100));
    if (s_conn_handle != BLE_HS_CONN_HANDLE_NONE) {
        ble_gap_terminate(s_conn_handle, BLE_ERR_REM_USER_CONN_TERM);
    }
    s_hooks.live(); /* called last -- see handle_handoff()'s comment on the same race */
}

static void handle_reboot(uint8_t id)
{
    /* Review finding (BLOCKER): dusty_ble must not esp_restart() itself --
     * the caller (radio.c) owns camera/SD/Wi-Fi teardown and needs the
     * chance to do it before the reset. Record the request instead; the
     * caller polls dusty_ble_restart_requested() after dusty_ble_stop(). */
    send_ok(id);
    dusty_ble_event("{\"ev\":\"bye\",\"reason\":\"restart\",\"back_in_s\":0}");
    s_going_quiet = 1; /* see handle_handoff()'s comment on this flag */
    vTaskDelay(pdMS_TO_TICKS(150)); /* flush before the link drops */
    if (s_conn_handle != BLE_HS_CONN_HANDLE_NONE) {
        ble_gap_terminate(s_conn_handle, BLE_ERR_REM_USER_CONN_TERM);
    }
    s_restart_requested = 1;
}

static void handle_time_set(cJSON *req, uint8_t id)
{
    if (!s_hooks.time_set) {
        send_err(id, "unsupported", NULL);
        return;
    }
    cJSON *tj = cJSON_GetObjectItemCaseSensitive(req, "ts");
    cJSON *zj = cJSON_GetObjectItemCaseSensitive(req, "tz_min");
    if (!cJSON_IsNumber(tj)) {
        send_err(id, "badreq", "ts");
        return;
    }
    int64_t ts = (int64_t)tj->valuedouble;
    int tz = cJSON_IsNumber(zj) ? (int)zj->valuedouble : 0;
    s_hooks.time_set(ts, tz);
    send_ok(id);
}

/* Merges a `{...}` object the hook wrote into s_hook_buf onto `{"id":n,
 * "ok":true,` and sends it -- the pattern handle_status()/
 * handle_spool_list() already use, reused for cfg.schema/cfg.get/
 * prov.get/wifi.scan. `what` is only for the badreq/toolarge messages. */
static void send_merged_hook_object(uint8_t id, int hook_len, const char *what)
{
    if (hook_len < 2 || s_hook_buf[0] != '{' || s_hook_buf[hook_len - 1] != '}') {
        send_err(id, "badreq", what);
        return;
    }
    s_hook_buf[hook_len - 1] = '\0';
    int n = snprintf(s_rsp_buf, sizeof(s_rsp_buf), "{\"id\":%u,\"ok\":true,%s}", id, s_hook_buf + 1);
    if (n <= 0 || (size_t)n >= sizeof(s_rsp_buf)) {
        send_err(id, "toolarge", NULL);
        return;
    }
    send_on(s_val_rsp, id, 0, (const uint8_t *)s_rsp_buf, (size_t)n);
}

static void handle_cfg_schema(uint8_t id)
{
    if (!s_hooks.cfg_schema) {
        send_err(id, "unsupported", NULL);
        return;
    }
    /* Review finding (MINOR): the schema object itself carries an "id"
     * field (the device id) -- merging it flat onto the response like
     * cfg.get/prov.get do would produce two "id" keys ({"id":<req>,
     * "ok":true,"id":"xiaocam1",...}). Nest it under "schema" instead. */
    int hn = s_hooks.cfg_schema(s_hook_buf, sizeof(s_hook_buf));
    if (hn < 2 || s_hook_buf[0] != '{' || s_hook_buf[hn - 1] != '}') {
        send_err(id, "badreq", "cfg.schema");
        return;
    }
    int n = snprintf(s_rsp_buf, sizeof(s_rsp_buf), "{\"id\":%u,\"ok\":true,\"schema\":%s}", id, s_hook_buf);
    if (n <= 0 || (size_t)n >= sizeof(s_rsp_buf)) {
        send_err(id, "toolarge", NULL);
        return;
    }
    send_on(s_val_rsp, id, 0, (const uint8_t *)s_rsp_buf, (size_t)n);
}

static void handle_cfg_get(uint8_t id)
{
    if (!s_hooks.cfg_get) {
        send_err(id, "unsupported", NULL);
        return;
    }
    send_merged_hook_object(id, s_hooks.cfg_get(s_hook_buf, sizeof(s_hook_buf)), "cfg.get");
}

static void handle_cfg_set(cJSON *req, uint8_t id)
{
    if (!s_hooks.cfg_set) {
        send_err(id, "unsupported", NULL);
        return;
    }
    cJSON *cfgj = cJSON_GetObjectItemCaseSensitive(req, "cfg");
    if (!cJSON_IsObject(cfgj)) {
        send_err(id, "badreq", "cfg");
        return;
    }
    char *json = cJSON_PrintUnformatted(cfgj);
    if (!json) {
        send_err(id, "badreq", NULL);
        return;
    }
    int out_cfg = 0;
    int rc = s_hooks.cfg_set(json, &out_cfg);
    cJSON_free(json);
    if (rc < 0) {
        send_err(id, "busy", NULL); /* a drain is running */
        return;
    }
    if (rc == 0) {
        send_err(id, "badreq", "cfg");
        return;
    }
    char buf[48];
    int n = snprintf(buf, sizeof(buf), "{\"id\":%u,\"ok\":true,\"cfg\":%d}", id, out_cfg);
    send_on(s_val_rsp, id, 0, (const uint8_t *)buf, (size_t)n);
}

static void handle_prov_get(uint8_t id)
{
    if (!s_hooks.prov_get) {
        send_err(id, "unsupported", NULL);
        return;
    }
    send_merged_hook_object(id, s_hooks.prov_get(s_hook_buf, sizeof(s_hook_buf)), "prov.get");
}

static void handle_prov_set(cJSON *req, uint8_t id)
{
    if (!s_hooks.prov_set) {
        send_err(id, "unsupported", NULL);
        return;
    }

    /* Review finding (MINOR): the plaintext presence window is "as long as
     * this board stays unprovisioned" (radio.c's whole unprovisioned
     * session, up to RADIO_UNPROVISIONED_WINDOW_S = 600 s there), not a
     * fixed 120 s from dusty_ble_start() -- dusty_ble doesn't know radio.c's
     * constant, but it doesn't need to: !s_provisioned && !s_prov_set_used
     * already captures exactly "unprovisioned and not used yet", and radio.c
     * is what bounds how long a single dusty_ble_start() session runs for
     * an unprovisioned board in the first place. */
    int window_open = !s_provisioned && !s_prov_set_used;

    cJSON *envj = cJSON_GetObjectItemCaseSensitive(req, "env");
    const char *json = NULL;
    char *json_owned = NULL;

    if (cJSON_IsString(envj)) {
        if (!s_have_phone_nonce) {
            send_err(id, "badreq", "no hello");
            return;
        }
        if (!s_hooks.ble_key) {
            send_err(id, "auth", NULL);
            return;
        }
        const char *env_b64 = envj->valuestring;
        size_t decoded_len = 0;
        /* s_hook_buf: generic 8 KB scratch, unused for the duration of a
         * single in-flight request (see its declaration). */
        int b64rc = mbedtls_base64_decode((unsigned char *)s_hook_buf, sizeof(s_hook_buf), &decoded_len,
                                           (const unsigned char *)env_b64, strlen(env_b64));
        if (b64rc != 0) {
            send_err(id, "badreq", "env base64");
            return;
        }
        uint8_t sk[BLE_AUTH_HMAC_LEN];
        uint8_t msg[2 + BLE_AUTH_NONCE_LEN * 2];
        msg[0] = 's';
        msg[1] = 'k';
        memcpy(msg + 2, s_cam_nonce, BLE_AUTH_NONCE_LEN);
        memcpy(msg + 2 + BLE_AUTH_NONCE_LEN, s_phone_nonce, BLE_AUTH_NONCE_LEN);
        ble_auth_hmac_sha256(s_hooks.ble_key, BLE_AUTH_KEY_LEN, msg, sizeof(msg), sk);

        int pt_len = ble_auth_gcm_decrypt(sk, (const uint8_t *)s_hook_buf, decoded_len, s_prov_plain);
        if (pt_len < 0) {
            /* GCM tag mismatch (wrong ble_key, corrupted envelope, or a
             * too-short one ble_auth_gcm_decrypt already rejected) --
             * "denied", not "badreq": this is an authentication failure,
             * and never a crash / silently-accepted garbled write. */
            send_err(id, "denied", NULL);
            return;
        }
        if ((size_t)pt_len >= sizeof(s_prov_plain)) {
            send_err(id, "toolarge", NULL);
            return;
        }
        s_prov_plain[pt_len] = '\0';
        json = (const char *)s_prov_plain;
    } else if (window_open) {
        /* Plaintext path: the request's own top-level fields ARE the
         * identity object (no envelope) -- re-serialise `req` as-is; the
         * extra "op"/"id" keys are harmless unknowns to the hook's parser. */
        json_owned = cJSON_PrintUnformatted(req);
        if (!json_owned) {
            send_err(id, "badreq", NULL);
            return;
        }
        json = json_owned;
    } else {
        send_err(id, "window", NULL); /* not provisioned, but the presence window is closed/used */
        return;
    }

    char devbuf[40];
    devbuf[0] = '\0';
    int rc = s_hooks.prov_set(json, devbuf, sizeof(devbuf));
    if (json_owned) cJSON_free(json_owned);
    if (!rc) {
        send_err(id, "badreq", "prov");
        return;
    }
    if (!s_provisioned) s_prov_set_used = 1;

    char buf[96];
    int n = snprintf(buf, sizeof(buf), "{\"id\":%u,\"ok\":true,\"device\":\"%s\"}", id, devbuf);
    send_on(s_val_rsp, id, 0, (const uint8_t *)buf, (size_t)n);

    /* Review finding (BLOCKER): dusty_ble must not esp_restart() itself,
     * same reasoning as handle_reboot() above -- record the request. */
    dusty_ble_event("{\"ev\":\"bye\",\"reason\":\"restart\",\"back_in_s\":0}");
    s_going_quiet = 1;
    vTaskDelay(pdMS_TO_TICKS(150)); /* let the reply/event above actually flush */
    if (s_conn_handle != BLE_HS_CONN_HANDLE_NONE) {
        ble_gap_terminate(s_conn_handle, BLE_ERR_REM_USER_CONN_TERM);
    }
    s_restart_requested = 1;
}

static void handle_wifi_scan(uint8_t id)
{
    if (!s_hooks.wifi_scan) {
        send_err(id, "unsupported", NULL);
        return;
    }
    send_merged_hook_object(id, s_hooks.wifi_scan(s_hook_buf, sizeof(s_hook_buf)), "wifi.scan");
}

static void process_request(const char *json, size_t len, uint8_t id)
{
    cJSON *req = cJSON_ParseWithLength(json, len);
    if (!req) {
        send_err(id, "badreq", "json");
        return;
    }
    cJSON *opj = cJSON_GetObjectItemCaseSensitive(req, "op");
    const char *op = cJSON_IsString(opj) ? opj->valuestring : NULL;
    if (!op) {
        send_err(id, "badreq", "op");
        cJSON_Delete(req);
        return;
    }

    if (strcmp(op, "hello") == 0) {
        handle_hello(req, id);
        cJSON_Delete(req);
        return;
    }
    if (strcmp(op, "auth") == 0) {
        handle_auth(req, id);
        cJSON_Delete(req);
        return;
    }
    if (strcmp(op, "prov.set") == 0) {
        /* Deliberately ahead of the !s_authed gate below: a truly blank
         * board (dustygen --blank, empty ble_key) can never complete
         * hello/auth, so this is the only op that must be reachable
         * without it. Still safe: the plaintext path is additionally
         * gated on the presence window (handle_prov_set), and the
         * encrypted path's AES-GCM tag can only verify if the caller
         * already knows the real ble_key -- there is no bypass, just a
         * different (cryptographic, not session-flag) gate. */
        handle_prov_set(req, id);
        cJSON_Delete(req);
        return;
    }
    if (!s_authed) {
        send_err(id, "auth", NULL);
        cJSON_Delete(req);
        return;
    }

    if (strcmp(op, "status") == 0) handle_status(id);
    else if (strcmp(op, "spool.list") == 0) handle_spool_list(id);
    else if (strcmp(op, "thumb") == 0) handle_thumb(req, id);
    else if (strcmp(op, "frame") == 0) handle_frame(req, id);
    else if (strcmp(op, "preview") == 0) handle_preview(id);
    else if (strcmp(op, "shoot") == 0) handle_shoot(id);
    else if (strcmp(op, "wifi.up") == 0) handle_handoff(req, id, "view");
    else if (strcmp(op, "contact") == 0) handle_handoff(req, id, "contact");
    else if (strcmp(op, "live") == 0) handle_live(id);
    else if (strcmp(op, "reboot") == 0) handle_reboot(id);
    else if (strcmp(op, "time.set") == 0) handle_time_set(req, id);
    else if (strcmp(op, "cfg.schema") == 0) handle_cfg_schema(id);
    else if (strcmp(op, "cfg.get") == 0) handle_cfg_get(id);
    else if (strcmp(op, "cfg.set") == 0) handle_cfg_set(req, id);
    else if (strcmp(op, "prov.get") == 0) handle_prov_get(id);
    else if (strcmp(op, "prov.set") == 0) handle_prov_set(req, id);
    else if (strcmp(op, "wifi.scan") == 0) handle_wifi_scan(id);
    else
        send_err(id, "badreq", "op");

    cJSON_Delete(req);
}

static void req_task(void *arg)
{
    (void)arg;
    for (;;) {
        /* Drain any errors on_cmd_write() deferred (badreq/busy) before
         * and between real requests -- see pending_err_t's comment. */
        pending_err_t e;
        while (xQueueReceive(s_err_q, &e, 0) == pdTRUE) {
            send_err(e.id, e.err, NULL);
        }
        if (xSemaphoreTake(s_req_ready, pdMS_TO_TICKS(50)) == pdTRUE) {
            process_request((const char *)s_pending_req, s_pending_req_len, s_pending_req_id);
            s_req_busy = 0;
        }
    }
}

/* ---------------- GATT access + GAP ---------------- */

static int build_info_json(char *buf, size_t cap)
{
    char nonce_hex[BLE_AUTH_NONCE_LEN * 2 + 1];
    ble_auth_hex_encode(s_cam_nonce, BLE_AUTH_NONCE_LEN, nonce_hex);
    const char *dev = (s_hooks.device && s_hooks.device[0]) ? s_hooks.device : "new";
    const char *ver = s_hooks.fw_version ? s_hooks.fw_version : "";
    int prov = (s_hooks.device && s_hooks.device[0]) ? 1 : 0;

    /* Review finding (MINOR): this used to hardcode "cfg":0. This callback
     * runs on the NimBLE host task (a GATT characteristic read), not on
     * ble_req, so it must NOT touch s_hook_buf (that 8 KB scratch buffer is
     * only safe from the ble_req task -- see its other users). cfg_get's
     * output (dc_cfg_to_json) is small (a handful of scalar fields, no
     * schema text), so a local stack buffer is fine; dc_cfg_to_json always
     * writes "cfg" as its first field, so a plain sscanf recovers it
     * without a full JSON parse. */
    int cfg = 0;
    if (s_hooks.cfg_get) {
        char cfg_buf[320];
        int cn = s_hooks.cfg_get(cfg_buf, sizeof(cfg_buf));
        if (cn > 0 && (size_t)cn < sizeof(cfg_buf)) {
            cfg_buf[cn] = '\0';
            sscanf(cfg_buf, "{\"cfg\":%d", &cfg);
        }
    }

    int n = snprintf(buf, cap,
                      "{\"proto\":1,\"device\":\"%s\",\"v\":\"%s\",\"cfg\":%d,\"prov\":%d,"
                      "\"nonce\":\"%s\",\"stage\":\"ble\",\"radio\":\"ble\"}",
                      dev, ver, cfg, prov, nonce_hex);
    return (n > 0 && (size_t)n < cap) ? n : -1;
}

static void on_cmd_write(struct os_mbuf *om)
{
    s_last_request_us = esp_timer_get_time();

    uint16_t om_len = OS_MBUF_PKTLEN(om);
    uint8_t frame[BLE_FRAME_HDR_LEN + 514]; /* room for any MTU up to 517 (517-3=514) */
    if (om_len < BLE_FRAME_HDR_LEN || om_len > sizeof(frame)) {
        ESP_LOGW(TAG, "cmd write: bad length %u", (unsigned)om_len);
        return;
    }
    uint16_t out_len = 0;
    if (ble_hs_mbuf_to_flat(om, frame, sizeof(frame), &out_len) != 0) return;

    ble_frame_hdr_t hdr;
    int rc = ble_frame_reassembler_feed(&s_req_reasm, frame, out_len, &hdr);
    if (rc == BLE_FRAME_DONE) {
        if (s_req_busy) {
            /* review finding: the single s_pending_req slot must not be
             * clobbered while ble_req is still working the previous
             * request. The phone's GattQueue shouldn't produce this in
             * practice (one op at a time), but answer busy rather than
             * silently drop if it ever does. */
            pending_err_t e = { .id = hdr.id };
            strlcpy(e.err, "busy", sizeof(e.err));
            xQueueSend(s_err_q, &e, 0);
            return;
        }
        size_t n = s_req_reasm.len;
        if (n > sizeof(s_pending_req) - 1) n = sizeof(s_pending_req) - 1; /* cap already enforces this */
        memcpy(s_pending_req, s_req_reasm.buf, n);
        s_pending_req[n] = '\0';
        s_pending_req_len = n;
        s_pending_req_id = hdr.id;
        s_req_busy = 1;
        xSemaphoreGive(s_req_ready);
    } else if (rc < 0) {
        ESP_LOGW(TAG, "cmd reassembly error %d (id=%u idx=%u)", rc, hdr.id, hdr.idx);
        /* Deferred to ble_req (review finding): this callback runs on the
         * NimBLE host task, which must not block in notify_sink()'s retry
         * loop. */
        pending_err_t e = { .id = hdr.id };
        strlcpy(e.err, "badreq", sizeof(e.err));
        xQueueSend(s_err_q, &e, 0);
    }
    /* BLE_FRAME_OK: more fragments still to come. */
}

static int gatt_access_cb(uint16_t conn_handle, uint16_t attr_handle,
                           struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    (void)conn_handle;
    (void)arg;
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR && attr_handle == s_val_info) {
        char buf[256];
        int n = build_info_json(buf, sizeof(buf));
        if (n < 0) return BLE_ATT_ERR_UNLIKELY;
        return os_mbuf_append(ctxt->om, buf, (uint16_t)n) == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
    }
    if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR && attr_handle == s_val_cmd) {
        on_cmd_write(ctxt->om);
        return 0;
    }
    return BLE_ATT_ERR_READ_NOT_PERMITTED;
}

static void build_adv_fields(void)
{
    struct ble_hs_adv_fields fields;
    memset(&fields, 0, sizeof(fields));
    fields.flags = BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP;
    fields.uuids128 = &s_svc_uuid;
    fields.num_uuids128 = 1;
    fields.uuids128_is_complete = 1;
    int rc = ble_gap_adv_set_fields(&fields);
    if (rc != 0) ESP_LOGW(TAG, "adv_set_fields rc=%d", rc);

    struct ble_hs_adv_fields rsp_fields;
    memset(&rsp_fields, 0, sizeof(rsp_fields));
    rsp_fields.name = (const uint8_t *)s_adv_name;
    /* Review finding (MINOR): a legacy adv/scan-rsp packet is capped at
     * 31 B total; this scan-rsp also carries the 6 B mfg_data AD
     * structure + 2 B of AD header for the name itself, leaving 23 B for
     * the name text. "dc-<device>" can run longer than that (device is up
     * to DUSTY_IDENT_DEVICE_MAX-1 = 31 chars) -- ble_gap_adv_rsp_set_fields
     * fails (silently, if nothing checks its return) rather than
     * truncating for you. Truncate here, not s_adv_name itself (that's
     * still the real device name for anything else that reads it). */
    size_t name_len = strlen(s_adv_name);
    if (name_len > 23) name_len = 23;
    rsp_fields.name_len = (uint8_t)name_len;
    rsp_fields.name_is_complete = (name_len == strlen(s_adv_name)) ? 1 : 0;

    /* bit2 (unprovisioned window open) is recomputed on every advertise
     * (this function runs whenever advertising (re)starts -- connect
     * failure, disconnect, the 30 s interval switch, ...), not fixed once
     * at dusty_ble_start(): it needs to clear itself once prov.set has
     * been used (review finding: the plaintext window is the whole
     * unprovisioned session, not a fixed 120 s -- see handle_prov_set()). */
    uint8_t flags = s_mfg_flags;
    if (!s_provisioned && !s_prov_set_used) {
        flags |= 0x04;
    } else {
        flags &= (uint8_t)~0x04;
    }
    uint8_t mfg[4] = { 0xDC, 0x0A, 0x01 /* proto */, flags };
    rsp_fields.mfg_data = mfg;
    rsp_fields.mfg_data_len = sizeof(mfg);

    rc = ble_gap_adv_rsp_set_fields(&rsp_fields);
    if (rc != 0) ESP_LOGW(TAG, "adv_rsp_set_fields rc=%d", rc);
}

static int gap_event_cb(struct ble_gap_event *event, void *arg)
{
    (void)arg;
    switch (event->type) {
    case BLE_GAP_EVENT_CONNECT:
        if (event->connect.status == 0) {
            s_conn_handle = event->connect.conn_handle;
            s_connected = 1;
            s_authed = 0;
            s_have_phone_nonce = 0;
            s_sub_rsp = s_sub_data = s_sub_evt = 0;
            ble_auth_gen_nonce(s_cam_nonce);
            esp_timer_stop(s_adv_timer); /* ignore: may not have been running */
            ESP_LOGI(TAG, "connected; conn_handle=%d", s_conn_handle);
        } else {
            ESP_LOGW(TAG, "connect failed; status=%d", event->connect.status);
            if (s_running && !s_stopping) resume_advertising_fast();
        }
        return 0;

    case BLE_GAP_EVENT_DISCONNECT:
        ESP_LOGI(TAG, "disconnected; reason=%d", event->disconnect.reason);
        s_connected = 0;
        s_conn_handle = BLE_HS_CONN_HANDLE_NONE;
        s_authed = 0;
        s_have_phone_nonce = 0;
        s_sub_rsp = s_sub_data = s_sub_evt = 0;
        if (s_running && !s_stopping && !s_going_quiet) {
            resume_advertising_fast(); /* sarg: re-advertising is what makes a link survivable */
        }
        return 0;

    case BLE_GAP_EVENT_SUBSCRIBE:
        if (event->subscribe.attr_handle == s_val_rsp) s_sub_rsp = event->subscribe.cur_notify;
        else if (event->subscribe.attr_handle == s_val_data) s_sub_data = event->subscribe.cur_notify;
        else if (event->subscribe.attr_handle == s_val_evt) s_sub_evt = event->subscribe.cur_notify;
        return 0;

    case BLE_GAP_EVENT_MTU:
        s_mtu = event->mtu.value;
        ESP_LOGI(TAG, "mtu negotiated: %u", (unsigned)s_mtu);
        return 0;

    case BLE_GAP_EVENT_ADV_COMPLETE:
        if (s_running && !s_stopping && !s_going_quiet && !s_connected) resume_advertising_fast();
        return 0;

    default:
        return 0;
    }
}

static void start_advertising(void)
{
    struct ble_gap_adv_params adv_params;
    memset(&adv_params, 0, sizeof(adv_params));
    adv_params.conn_mode = BLE_GAP_CONN_MODE_UND;
    adv_params.disc_mode = BLE_GAP_DISC_MODE_GEN;
    uint16_t itvl = s_adv_fast ? 160 /* 100 ms */ : 800 /* 500 ms */;
    adv_params.itvl_min = itvl;
    adv_params.itvl_max = itvl;

    build_adv_fields();

    int rc = ble_gap_adv_start(s_own_addr_type, NULL, BLE_HS_FOREVER, &adv_params, gap_event_cb, NULL);
    if (rc != 0) ESP_LOGW(TAG, "adv_start rc=%d", rc);
}

/* The 30 s fast->slow advertising switch runs on the NimBLE host task.
 * adv_interval_timer_cb() itself runs on the esp_timer task, whose small
 * stack (CONFIG_ESP_TIMER_TASK_STACK_SIZE) is shared with Wi-Fi's timers,
 * so it only posts this event (docs/crash_experiment_2026-09-16.md). The
 * event is allocated from NimBLE's pool: initialised after nimble_port_init()
 * and released before nimble_port_deinit(). */
static struct ble_npl_event s_adv_slow_ev;

static void adv_slow_ev_cb(struct ble_npl_event *ev)
{
    (void)ev;
    if (s_running && !s_stopping && !s_connected && s_adv_fast) {
        s_adv_fast = 0;
        ble_gap_adv_stop();
        start_advertising();
        ESP_LOGI(TAG, "adv interval: 100ms -> 500ms (30s with no link)");
    }
}

static void adv_interval_timer_cb(void *arg)
{
    (void)arg;
    if (s_running && !s_stopping) {
        ble_npl_eventq_put(nimble_port_get_dflt_eventq(), &s_adv_slow_ev);
    }
}

static void resume_advertising_fast(void)
{
    s_adv_fast = 1;
    start_advertising();
    esp_timer_stop(s_adv_timer); /* ignore ESP_ERR_INVALID_STATE if not armed */
    esp_timer_start_once(s_adv_timer, 30LL * 1000000);
}

static void set_rnd_address(void)
{
    uint8_t mac[6];
    esp_read_mac(mac, ESP_MAC_BT);
    uint8_t rnd[6];
    for (int i = 0; i < 6; i++) rnd[i] = mac[5 - i]; /* reverse to over-the-air (LE) order */
    rnd[5] |= 0xC0; /* static random: top two bits = 11 (Core Spec Vol 6, Part B, 1.3.2.1) */
    int rc = ble_hs_id_set_rnd(rnd);
    if (rc != 0) ESP_LOGW(TAG, "ble_hs_id_set_rnd rc=%d", rc);
}

static void on_sync(void)
{
    set_rnd_address();
    s_own_addr_type = BLE_OWN_ADDR_RANDOM;
    resume_advertising_fast();
}

static void on_reset(int reason)
{
    ESP_LOGW(TAG, "nimble host reset; reason=%d", reason);
}

static void host_task(void *param)
{
    (void)param;
    ESP_LOGI(TAG, "nimble host task started");
    nimble_port_run(); /* returns only after nimble_port_stop() */
    nimble_port_freertos_deinit();
}

static void build_adv_name(void)
{
    if (s_hooks.device && s_hooks.device[0]) {
        snprintf(s_adv_name, sizeof(s_adv_name), "dc-%s", s_hooks.device);
        s_mfg_flags = 0x01; /* bit0 provisioned */
    } else {
        uint8_t mac[6];
        esp_read_mac(mac, ESP_MAC_BT);
        snprintf(s_adv_name, sizeof(s_adv_name), "dc-new-%02x%02x", mac[4], mac[5]);
        s_mfg_flags = 0x04; /* bit2 unprovisioned window open */
    }
}

/* ---------------- lifecycle ---------------- */

static void ensure_tasks(void)
{
    if (!s_req_ready) s_req_ready = xSemaphoreCreateBinary();
    if (!s_img_done) s_img_done = xSemaphoreCreateBinary();
    if (!s_img_q) s_img_q = xQueueCreate(1, sizeof(img_work_t));
    if (!s_err_q) s_err_q = xQueueCreate(4, sizeof(pending_err_t));
    if (!s_req_task_handle) {
        /* Review finding (MAJOR): 6 KB was sized for JSON parsing + NVS
         * writes; wifi.scan's hook runs esp_wifi_init()/scan() (plus
         * wpa_supplicant's own stack use during that) directly on this
         * task via handle_wifi_scan() -> s_hooks.wifi_scan(). Raised
         * rather than moving the call to a separate task/queue (a bigger
         * change for the same effect) -- 10 KB comes straight from
         * internal RAM, same as before. */
        xTaskCreate(req_task, "ble_req", 10 * 1024, NULL, 5, &s_req_task_handle);
    }
    if (!s_img_task_handle) {
        xTaskCreateWithCaps(img_task, "ble_img", 12 * 1024, NULL, 5, &s_img_task_handle, BLE_IMG_TASK_CAPS);
    }
    if (!s_adv_timer) {
        const esp_timer_create_args_t args = {
            .callback = adv_interval_timer_cb,
            .name = "ble_adv_itvl",
        };
        esp_timer_create(&args, &s_adv_timer);
    }
}

void dusty_ble_start(const dusty_ble_hooks_t *hooks)
{
    if (s_running) return;
    s_hooks = hooks ? *hooks : (dusty_ble_hooks_t){ 0 };

    s_going_quiet = 0;
    s_req_busy = 0;
    s_authed = 0;
    s_have_phone_nonce = 0;
    s_connected = 0;
    s_conn_handle = BLE_HS_CONN_HANDLE_NONE;
    s_mtu = 23;
    s_sub_rsp = s_sub_data = s_sub_evt = 0;
    s_last_request_us = 0;
    s_prov_set_used = 0;
    s_restart_requested = 0;
    s_provisioned = (s_hooks.device && s_hooks.device[0]) ? 1 : 0;
    ble_frame_reassembler_init(&s_req_reasm, s_req_reasm_buf, sizeof(s_req_reasm_buf));

    ensure_tasks();
    build_adv_name();

    esp_err_t err = nimble_port_init();
    if (err != ESP_OK) {
        /* review finding: a prior dusty_ble_stop() that failed to
         * nimble_port_stop() leaves the controller enabled, and this call
         * then fails silently (ESP_ERR_INVALID_STATE) forever after --
         * every path through this bench must end with the radio actually
         * deinit'd, so treat this as fatal rather than limping on with no
         * BLE and no diagnosis. */
        ESP_LOGE(TAG, "nimble_port_init failed: %d -- radio state is inconsistent, restarting", err);
        esp_restart();
    }

    ble_hs_cfg.reset_cb = on_reset;
    ble_hs_cfg.sync_cb = on_sync;
    ble_hs_cfg.gatts_register_cb = NULL;
    ble_hs_cfg.store_status_cb = ble_store_util_status_rr;
    ble_hs_cfg.sm_bonding = 0;
    ble_hs_cfg.sm_mitm = 0;
    ble_hs_cfg.sm_sc = 0;

    ble_att_set_preferred_mtu(517);

    ble_svc_gap_init();
    ble_svc_gatt_init();
    int rc = ble_gatts_count_cfg(s_gatt_svcs);
    if (rc != 0) {
        ESP_LOGE(TAG, "ble_gatts_count_cfg failed: %d", rc);
        nimble_port_deinit();
        return;
    }
    rc = ble_gatts_add_svcs(s_gatt_svcs);
    if (rc != 0) {
        ESP_LOGE(TAG, "ble_gatts_add_svcs failed: %d", rc);
        nimble_port_deinit();
        return;
    }
    ble_svc_gap_device_name_set(s_adv_name);
    ble_store_config_init();
    ble_npl_event_init(&s_adv_slow_ev, adv_slow_ev_cb, NULL);

    s_stopping = 0;
    s_running = 1;
    nimble_port_freertos_init(host_task);
    ESP_LOGI(TAG, "started, advertising as \"%s\"", s_adv_name);
}

void dusty_ble_stop(void)
{
    if (!s_running) return;
    s_stopping = 1;

    if (s_adv_timer) esp_timer_stop(s_adv_timer);
    if (s_conn_handle != BLE_HS_CONN_HANDLE_NONE) {
        ble_gap_terminate(s_conn_handle, BLE_ERR_REM_USER_CONN_TERM);
        vTaskDelay(pdMS_TO_TICKS(50)); /* best-effort: let the disconnect land first */
    }
    ble_gap_adv_stop(); /* harmless if not currently advertising */

    int rc = nimble_port_stop();
    if (rc == 0) {
        /* the host task has exited: nothing will run the event now, and
         * nimble_port_deinit() frees the pool it came from */
        ble_npl_event_deinit(&s_adv_slow_ev);
        nimble_port_deinit();
    } else {
        /* review finding: leaving the controller enabled here means the
         * NEXT dusty_ble_start()'s nimble_port_init() fails silently
         * (ESP_ERR_INVALID_STATE) with no BLE and no obvious cause. Every
         * path through this bench must end with the radio deinit'd, so
         * restart rather than limp on in a state this component can't
         * recover from itself. */
        ESP_LOGE(TAG, "nimble_port_stop rc=%d -- NOT calling nimble_port_deinit (would double-free); restarting", rc);
        esp_restart();
    }

    s_running = 0;
    s_connected = 0;
    s_conn_handle = BLE_HS_CONN_HANDLE_NONE;
    s_stopping = 0;

    esp_bt_controller_status_t st = esp_bt_controller_get_status();
    ESP_LOGI(TAG, "stopped; esp_bt_controller_get_status()=%d (%s)", (int)st,
             st == ESP_BT_CONTROLLER_STATUS_IDLE ? "IDLE" : "NOT IDLE -- leak?");

    /* Review finding (MAJOR, wifi.scan stack sizing): watch actual
     * high-water marks on the bench rather than guess -- both tasks stay
     * alive across stop()/start() cycles, so this is cheap to check every
     * time. 0 words remaining would mean an imminent overflow. */
    if (s_req_task_handle) {
        ESP_LOGI(TAG, "ble_req stack high water mark: %u words",
                 (unsigned)uxTaskGetStackHighWaterMark(s_req_task_handle));
    }
    if (s_img_task_handle) {
        ESP_LOGI(TAG, "ble_img stack high water mark: %u words",
                 (unsigned)uxTaskGetStackHighWaterMark(s_img_task_handle));
    }
}
