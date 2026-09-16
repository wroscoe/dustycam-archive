#include "dusty_uplink.h"
#include "dusty_core.h"

#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <strings.h>
#include <sys/stat.h>

#include "esp_log.h"
#include "esp_heap_caps.h"
#include "esp_http_client.h"
#include "esp_crt_bundle.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "freertos/task.h"

static const char *TAG = "dusty_uplink";

#define HTTP_TIMEOUT_MS 15000
#define CHUNK 4096

/* Review finding (MINOR): these used to be hardcoded to 64 bytes while
 * dusty_config's dusty_ident_t (the caller of dusty_uplink_init() below)
 * sizes host/token at DUSTY_IDENT_HOST_MAX/DUSTY_IDENT_TOKEN_MAX (both 96,
 * dusty_config/include/dusty_config.h) -- a saved value between 64 and 96
 * bytes would silently truncate here with no error. dusty_uplink is a
 * lower-level component that (deliberately) doesn't REQUIRE dusty_config,
 * so these are plain literals, not the shared #define -- keep them >= the
 * ident struct's host/token sizes if either grows. device stays at 32,
 * matching DUSTY_IDENT_DEVICE_MAX. */
static char s_host[96];
static int s_port = 10000;
static int s_tls = 1;
static char s_token[96];
static char s_device[32];

static int64_t s_last_server_time;
static char s_ip[16] = "0.0.0.0";
static bool s_wifi_started;
static EventGroupHandle_t s_wifi_events;
static esp_netif_t *s_sta_netif;
static esp_event_handler_instance_t s_wifi_evt_handle;
static esp_event_handler_instance_t s_ip_evt_handle;
#define WIFI_GOT_IP_BIT BIT0
#define WIFI_FAIL_BIT   BIT1

void dusty_uplink_init(const char *host, int port, int tls, const char *token, const char *device)
{
    if (host) strlcpy(s_host, host, sizeof(s_host));
    s_port = port;
    s_tls = tls ? 1 : 0;
    if (token) strlcpy(s_token, token, sizeof(s_token));
    if (device) strlcpy(s_device, device, sizeof(s_device));
}

static esp_err_t http_event_cb(esp_http_client_event_t *evt)
{
    if (evt->event_id == HTTP_EVENT_ON_HEADER) {
        if (evt->header_key && strcasecmp(evt->header_key, "Date") == 0 && evt->header_value) {
            int64_t t = dc_parse_http_date(evt->header_value);
            if (t > 0) s_last_server_time = t;
        }
    }
    return ESP_OK;
}

static esp_http_client_handle_t open_client(const char *path, esp_http_client_method_t method,
                                             const char *content_type, const char *meta_json)
{
    char url[192];
    snprintf(url, sizeof(url), "%s://%s:%d%s", s_tls ? "https" : "http", s_host, s_port, path);

    esp_http_client_config_t cfg = {
        .url = url,
        .method = method,
        .timeout_ms = HTTP_TIMEOUT_MS,
        .event_handler = http_event_cb,
        .crt_bundle_attach = s_tls ? esp_crt_bundle_attach : NULL,
    };
    esp_http_client_handle_t c = esp_http_client_init(&cfg);
    if (!c) return NULL;
    if (s_token[0]) esp_http_client_set_header(c, "X-Token", s_token);
    esp_http_client_set_header(c, "Connection", "close");
    if (content_type) esp_http_client_set_header(c, "Content-Type", content_type);
    if (meta_json) esp_http_client_set_header(c, "X-Meta", meta_json);
    return c;
}

static int finish_and_status(esp_http_client_handle_t c, int *status_out)
{
    esp_err_t err = esp_http_client_fetch_headers(c) >= 0 ? ESP_OK : ESP_FAIL;
    int status = 0;
    if (err == ESP_OK) status = esp_http_client_get_status_code(c);
    if (status_out) *status_out = status;
    esp_http_client_close(c);
    esp_http_client_cleanup(c);
    return (status >= 200 && status < 300) ? 1 : 0;
}

int dusty_uplink_post_file(const char *kind, const char *path, const char *meta_json, int *status)
{
    if (status) *status = 0;
    struct stat st;
    if (stat(path, &st) != 0) {
        ESP_LOGE(TAG, "post_file: stat %s failed", path);
        return 0;
    }
    FILE *f = fopen(path, "rb");
    if (!f) {
        ESP_LOGE(TAG, "post_file: open %s failed", path);
        return 0;
    }
#ifdef CONFIG_DUSTY_CRASH_DEBUG
    /* docs/crash_experiment_2026-09-16.md: stack left after the deep drain call chain */
    ESP_LOGW(TAG, "[post_file after fopen] task=%s stack_hwm=%u B",
             pcTaskGetName(NULL), (unsigned)uxTaskGetStackHighWaterMark(NULL));
#endif
    char urlpath[96];
    snprintf(urlpath, sizeof(urlpath), "/blob/%s/%s", s_device, kind);
    esp_http_client_handle_t c = open_client(urlpath, HTTP_METHOD_POST, "image/jpeg", meta_json);
    if (!c) { fclose(f); return 0; }

    int ok = 0;
    if (esp_http_client_open(c, (int)st.st_size) == ESP_OK) {
        /* Heap, not stack: this runs at the bottom of the main task's
         * deepest call chain (contact -> drain -> here -> TLS), and a
         * 4 KB local here overflowed the old 12 KB main stack on every
         * upload (docs/phone_app_status.md, 2026-09-16). */
        uint8_t *buf = heap_caps_malloc(CHUNK, MALLOC_CAP_SPIRAM);
        if (!buf) buf = malloc(CHUNK);
        size_t remaining = (size_t)st.st_size;
        ok = buf != NULL;
        while (ok && remaining > 0) {
            size_t want = remaining < CHUNK ? remaining : CHUNK;
            size_t got = fread(buf, 1, want, f);
            if (got != want) { ok = 0; break; }
            if (esp_http_client_write(c, (const char *)buf, (int)got) != (int)got) { ok = 0; break; }
            remaining -= got;
        }
        free(buf);
    } else {
        ESP_LOGW(TAG, "post_file: open request failed");
    }
    fclose(f);
    if (!ok) {
        esp_http_client_close(c);
        esp_http_client_cleanup(c);
        return 0;
    }
    return finish_and_status(c, status);
}

int dusty_uplink_post_blob(const char *kind, const uint8_t *data, size_t len, const char *meta_json)
{
    char urlpath[96];
    snprintf(urlpath, sizeof(urlpath), "/blob/%s/%s", s_device, kind);
    esp_http_client_handle_t c = open_client(urlpath, HTTP_METHOD_POST, "image/jpeg", meta_json);
    if (!c) return 0;
    int ok = 0;
    if (esp_http_client_open(c, (int)len) == ESP_OK) {
        ok = (esp_http_client_write(c, (const char *)data, (int)len) == (int)len);
    }
    if (!ok) {
        esp_http_client_close(c);
        esp_http_client_cleanup(c);
        return 0;
    }
    return finish_and_status(c, NULL);
}

int dusty_uplink_post_telemetry(const char *json)
{
    char urlpath[64];
    snprintf(urlpath, sizeof(urlpath), "/telemetry/%s", s_device);
    esp_http_client_handle_t c = open_client(urlpath, HTTP_METHOD_POST, "application/json", NULL);
    if (!c) return 0;
    size_t len = strlen(json);
    int ok = 0;
    if (esp_http_client_open(c, (int)len) == ESP_OK) {
        ok = (esp_http_client_write(c, json, (int)len) == (int)len);
    }
    if (!ok) {
        esp_http_client_close(c);
        esp_http_client_cleanup(c);
        return 0;
    }
    return finish_and_status(c, NULL);
}

int dusty_uplink_post_json(const char *path, const char *json, char *resp, size_t n, int *status)
{
    if (status) *status = 0;
    if (resp && n) resp[0] = 0;
    esp_http_client_handle_t c = open_client(path, HTTP_METHOD_POST, "application/json", NULL);
    if (!c) return 0;
    size_t len = strlen(json);
    if (esp_http_client_open(c, (int)len) != ESP_OK) {
        esp_http_client_cleanup(c);
        return 0;
    }
    if (esp_http_client_write(c, json, (int)len) != (int)len) {
        esp_http_client_close(c);
        esp_http_client_cleanup(c);
        return 0;
    }
    esp_http_client_fetch_headers(c);
    int st = esp_http_client_get_status_code(c);
    if (status) *status = st;
    /* Read the body regardless of status: a config-push 409's body is the
     * server's current config, which the caller needs precisely because
     * this wasn't a plain success. */
    size_t off = 0;
    if (resp && n > 1) {
        int r;
        while (off < n - 1 && (r = esp_http_client_read(c, resp + off, (int)(n - 1 - off))) > 0)
            off += (size_t)r;
        resp[off] = 0;
    }
    esp_http_client_close(c);
    esp_http_client_cleanup(c);
    return (st >= 200 && st < 300) ? 1 : 0;
}

int dusty_uplink_get(const char *path, char *buf, size_t n, int *status)
{
    if (status) *status = 0;
    if (buf && n) buf[0] = 0;
    esp_http_client_handle_t c = open_client(path, HTTP_METHOD_GET, NULL, NULL);
    if (!c) return 0;
    if (esp_http_client_open(c, 0) != ESP_OK) {
        esp_http_client_cleanup(c);
        return 0;
    }
    esp_http_client_fetch_headers(c);
    int st = esp_http_client_get_status_code(c);
    if (status) *status = st;
    size_t off = 0;
    if (buf && n > 1) {
        int r;
        while (off < n - 1 && (r = esp_http_client_read(c, buf + off, (int)(n - 1 - off))) > 0)
            off += (size_t)r;
        buf[off] = 0;
    }
    esp_http_client_close(c);
    esp_http_client_cleanup(c);
    return (st >= 200 && st < 300) ? 1 : 0;
}

int64_t dusty_uplink_last_server_time(void)
{
    return s_last_server_time;
}

/* ---------------- wifi ---------------- */

static void wifi_event_handler(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        esp_wifi_connect();
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *evt = (ip_event_got_ip_t *)data;
        snprintf(s_ip, sizeof(s_ip), IPSTR, IP2STR(&evt->ip_info.ip));
        if (s_wifi_events) xEventGroupSetBits(s_wifi_events, WIFI_GOT_IP_BIT);
    }
}

int dusty_uplink_wifi_join(const char *ssid, const char *pass, int timeout_s)
{
    if (!s_wifi_started) {
        /* Re-init from scratch every time: dusty_uplink_wifi_off() below
         * tears all of this back down (including the netif and event
         * handlers) so that a following join here starts clean -- this is
         * exactly what P0.1b's 10 BLE<->Wi-Fi cycles exercise, and it is
         * also what gives BLE its internal RAM back between cycles
         * (docs/phone_app_plan.md decision 9, §3 risk "leak across
         * BLE<->Wi-Fi cycles"). */
        if (!s_wifi_events) s_wifi_events = xEventGroupCreate();
        esp_err_t err = esp_netif_init();
        if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) ESP_LOGW(TAG, "netif_init: %s", esp_err_to_name(err));
        err = esp_event_loop_create_default();
        if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) ESP_LOGW(TAG, "event_loop: %s", esp_err_to_name(err));
        s_sta_netif = esp_netif_create_default_wifi_sta();
        wifi_init_config_t wcfg = WIFI_INIT_CONFIG_DEFAULT();
        ESP_ERROR_CHECK(esp_wifi_init(&wcfg));
        esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL, &s_wifi_evt_handle);
        esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL, &s_ip_evt_handle);
        ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
        s_wifi_started = true;
    }
    xEventGroupClearBits(s_wifi_events, WIFI_GOT_IP_BIT);

    wifi_config_t sta = { 0 };
    strlcpy((char *)sta.sta.ssid, ssid, sizeof(sta.sta.ssid));
    strlcpy((char *)sta.sta.password, pass ? pass : "", sizeof(sta.sta.password));
    sta.sta.scan_method = WIFI_FAST_SCAN;
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &sta));
    if (esp_wifi_start() != ESP_OK) {
        /* already started from a previous join attempt this boot */
        esp_wifi_connect();
    }

    EventBits_t bits = xEventGroupWaitBits(s_wifi_events, WIFI_GOT_IP_BIT, pdFALSE, pdTRUE,
                                            pdMS_TO_TICKS(timeout_s * 1000));
    return (bits & WIFI_GOT_IP_BIT) ? 1 : 0;
}

void dusty_uplink_wifi_off(void)
{
    if (!s_wifi_started) return;

    /* review finding: esp_wifi_disconnect() fires a WIFI_EVENT_STA_
     * DISCONNECTED, and wifi_event_handler() answers that with
     * esp_wifi_connect() -- which mid-teardown just fights the stop that
     * follows. Unregister first so the handler can't run during any of
     * this. */
    if (s_wifi_evt_handle) {
        esp_event_handler_instance_unregister(WIFI_EVENT, ESP_EVENT_ANY_ID, s_wifi_evt_handle);
        s_wifi_evt_handle = NULL;
    }
    if (s_ip_evt_handle) {
        esp_event_handler_instance_unregister(IP_EVENT, IP_EVENT_STA_GOT_IP, s_ip_evt_handle);
        s_ip_evt_handle = NULL;
    }

    esp_wifi_disconnect();
    esp_wifi_stop();
    esp_wifi_deinit();

    if (s_sta_netif) {
        esp_netif_destroy_default_wifi(s_sta_netif);
        s_sta_netif = NULL;
    }

    s_wifi_started = false;
    strlcpy(s_ip, "0.0.0.0", sizeof(s_ip));
    ESP_LOGI(TAG, "wifi off: disconnect+stop+deinit+netif destroyed");
}

const char *dusty_uplink_ip(void)
{
    return s_ip;
}

int dusty_uplink_rssi(void)
{
    if (!s_wifi_started) return 0;
    wifi_ap_record_t info;
    if (esp_wifi_sta_get_ap_info(&info) != ESP_OK) return 0;
    return info.rssi;
}

#define WIFI_SCAN_MAX_RECORDS 10

int dusty_uplink_wifi_scan(dusty_wifi_ap_t *out, int max)
{
    if (!out || max <= 0) return 0;
    if (s_wifi_started) {
        /* Refuse rather than risk a double esp_wifi_init: this call is
         * meant for the BLE phase, where dusty_uplink_wifi_join() has
         * never run this cycle (sequential radios). */
        ESP_LOGW(TAG, "wifi_scan: wifi_join's state is already up, refusing");
        return 0;
    }

    esp_err_t err = esp_netif_init();
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) ESP_LOGW(TAG, "wifi_scan: netif_init: %s", esp_err_to_name(err));
    err = esp_event_loop_create_default();
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) ESP_LOGW(TAG, "wifi_scan: event_loop: %s", esp_err_to_name(err));
    esp_netif_t *netif = esp_netif_create_default_wifi_sta();

    wifi_init_config_t wcfg = WIFI_INIT_CONFIG_DEFAULT();
    if (esp_wifi_init(&wcfg) != ESP_OK) {
        ESP_LOGW(TAG, "wifi_scan: esp_wifi_init failed");
        if (netif) esp_netif_destroy_default_wifi(netif);
        return 0;
    }
    esp_wifi_set_mode(WIFI_MODE_STA);
    if (esp_wifi_start() != ESP_OK) {
        ESP_LOGW(TAG, "wifi_scan: esp_wifi_start failed");
        esp_wifi_deinit();
        esp_netif_destroy_default_wifi(netif);
        return 0;
    }

    wifi_scan_config_t scan_cfg = { 0 };
    scan_cfg.show_hidden = false;
    int n = 0;
    if (esp_wifi_scan_start(&scan_cfg, true /* block until done */) == ESP_OK) {
        uint16_t num = WIFI_SCAN_MAX_RECORDS;
        wifi_ap_record_t recs[WIFI_SCAN_MAX_RECORDS];
        if (esp_wifi_scan_get_ap_records(&num, recs) == ESP_OK) {
            for (int i = 0; i < (int)num && n < max && n < WIFI_SCAN_MAX_RECORDS; i++) {
                strlcpy(out[n].ssid, (const char *)recs[i].ssid, sizeof(out[n].ssid));
                out[n].rssi = recs[i].rssi;
                out[n].ch = recs[i].primary;
                n++;
            }
        }
    } else {
        ESP_LOGW(TAG, "wifi_scan: esp_wifi_scan_start failed");
    }

    esp_wifi_stop();
    esp_wifi_deinit();
    esp_netif_destroy_default_wifi(netif);
    ESP_LOGI(TAG, "wifi_scan: %d AP(s) found", n);
    return n;
}
