#include "dusty_control.h"

#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>

#include "esp_http_server.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"

#include "lwip/sockets.h"

static const char *TAG = "dusty_control";

static httpd_handle_t s_server;
static dusty_control_hooks_t s_hooks;
static volatile int64_t s_last_request_us;

/* ---------------- UDP discovery beacon ----------------
 * The user must never type an IP: while the control plane is up, broadcast
 * once a second so a phone on the same hotspot can find the camera without
 * one. Small, dedicated task (2.5 KB stack -- it only builds a short JSON
 * string and calls sendto twice) so it doesn't compete with the httpd's
 * own stack budget. */
#define BEACON_PORT 8267
#define BEACON_INTERVAL_MS 1000
#define BEACON_TASK_STACK 2560

static TaskHandle_t s_beacon_task;
static volatile int s_beacon_running;
static char s_beacon_device[32];
/* Given to once beacon_task() has closed its socket and is about to
 * self-delete. beacon_stop() waits on it: the caller (dusty_control_stop(),
 * and in turn the radio loop's dusty_uplink_wifi_off() right after it) must
 * not race a live UDP socket against esp_wifi_deinit() tearing the netif
 * out from under it, and a leaked fd would show up as exactly the kind of
 * per-cycle leak this whole spike is watching for. */
static SemaphoreHandle_t s_beacon_stopped;
#define BEACON_POLL_MS 100 /* how often the loop re-checks s_beacon_running */

static void beacon_task(void *arg)
{
    (void)arg;
    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_IP);
    if (sock < 0) {
        ESP_LOGW(TAG, "beacon: socket() failed, errno=%d", errno);
        s_beacon_task = NULL;
        if (s_beacon_stopped) xSemaphoreGive(s_beacon_stopped);
        vTaskDelete(NULL);
        return;
    }
    int bcast_on = 1;
    setsockopt(sock, SOL_SOCKET, SO_BROADCAST, &bcast_on, sizeof(bcast_on));

    int logged = 0;
    TickType_t last_send = (TickType_t)0 - pdMS_TO_TICKS(BEACON_INTERVAL_MS); /* send immediately on entry */
    while (s_beacon_running) {
        TickType_t now = xTaskGetTickCount();
        if ((now - last_send) >= pdMS_TO_TICKS(BEACON_INTERVAL_MS)) {
            last_send = now;
            esp_netif_t *netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
            esp_netif_ip_info_t ip_info = { 0 };
            if (netif && esp_netif_get_ip_info(netif, &ip_info) == ESP_OK && ip_info.ip.addr != 0) {
                char ip_str[16];
                snprintf(ip_str, sizeof(ip_str), IPSTR, IP2STR(&ip_info.ip));

                char payload[128];
                int n = snprintf(payload, sizeof(payload),
                                  "{\"dc\":1,\"device\":\"%s\",\"ip\":\"%s\",\"port\":8266,\"radio\":\"wifi\"}",
                                  s_beacon_device, ip_str);
                if (n > 0 && (size_t)n < sizeof(payload)) {
                    struct sockaddr_in dst = { 0 };
                    dst.sin_family = AF_INET;
                    dst.sin_port = htons(BEACON_PORT);

                    /* Global broadcast: cheap, and some Android hotspot/
                     * router combos don't forward the subnet-directed one. */
                    dst.sin_addr.s_addr = htonl(INADDR_BROADCAST);
                    sendto(sock, payload, (size_t)n, 0, (struct sockaddr *)&dst, sizeof(dst));

                    /* Subnet-directed broadcast (ip | ~netmask): some
                     * networks only forward this one. ip/netmask are
                     * already in network byte order, so a plain bitwise
                     * combination is correct regardless of host endianness. */
                    uint32_t subnet_bcast = (ip_info.ip.addr & ip_info.netmask.addr) | (~ip_info.netmask.addr);
                    if (subnet_bcast != htonl(INADDR_BROADCAST)) {
                        dst.sin_addr.s_addr = subnet_bcast;
                        sendto(sock, payload, (size_t)n, 0, (struct sockaddr *)&dst, sizeof(dst));
                    }

                    if (!logged) {
                        ESP_LOGI(TAG, "beacon: %s -> :%d", ip_str, BEACON_PORT);
                        logged = 1;
                    }
                }
            }
        }
        vTaskDelay(pdMS_TO_TICKS(BEACON_POLL_MS)); /* re-check s_beacon_running promptly */
    }

    close(sock);
    s_beacon_task = NULL;
    if (s_beacon_stopped) xSemaphoreGive(s_beacon_stopped);
    vTaskDelete(NULL);
}

static void beacon_start(const char *device)
{
    if (!device || !device[0] || s_beacon_task) return;
    if (!s_beacon_stopped) s_beacon_stopped = xSemaphoreCreateBinary();
    else xSemaphoreTake(s_beacon_stopped, 0); /* clear any stale give from a previous stop */

    strlcpy(s_beacon_device, device, sizeof(s_beacon_device));
    s_beacon_running = 1;
    if (xTaskCreate(beacon_task, "dc_beacon", BEACON_TASK_STACK, NULL, 4, &s_beacon_task) != pdPASS) {
        ESP_LOGW(TAG, "beacon: xTaskCreate failed");
        s_beacon_task = NULL;
        s_beacon_running = 0;
    }
}

static void beacon_stop(void)
{
    if (!s_beacon_running && !s_beacon_task) return;
    s_beacon_running = 0;
    if (s_beacon_stopped) {
        if (xSemaphoreTake(s_beacon_stopped, pdMS_TO_TICKS(BEACON_POLL_MS + 500)) != pdTRUE) {
            ESP_LOGW(TAG, "beacon: did not confirm stop in time (socket may be leaked)");
        }
    }
}

#define STREAM_PART_BOUNDARY "\r\n--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n"

static const char SETUP_HTML[] =
"<!doctype html><html><head><meta charset=utf-8>"
"<meta name=viewport content=\"width=device-width,initial-scale=1\">"
"<title>dustycam setup</title>"
"<style>body{font-family:sans-serif;margin:0;padding:12px;background:#111;color:#eee}"
"img{max-width:100%;border:1px solid #444}button{font-size:1em;padding:8px 16px;margin:4px 4px 4px 0}"
"table{border-collapse:collapse}td{padding:2px 8px 2px 0}#dev{color:#8f8}</style></head><body>"
"<h2>dustycam <span id=dev>-</span></h2>"
"<img id=stream src=/stream>"
"<div><button onclick=\"fetch('/shoot',{method:'POST'})\">Shoot</button>"
"<button onclick=\"fetch('/refresh',{method:'POST'})\">Refresh</button>"
"<button onclick=\"location='/live'\">Live</button></div>"
"<table id=status></table>"
"<script>"
"function poll(){fetch('/status').then(r=>r.json()).then(j=>{"
"document.getElementById('dev').textContent=j.device||'';"
"var t=document.getElementById('status');var h='';"
"for(var k in j){h+='<tr><td>'+k+'</td><td>'+j[k]+'</td></tr>';}"
"t.innerHTML=h;"
"}).catch(function(){});}"
"setInterval(poll,2000);poll();"
"function reopen(){var i=document.getElementById('stream');var s=i.src;i.src='';i.src=s+'?'+Date.now();}"
"setInterval(reopen,30000);"
"</script></body></html>";

static const char LIVE_HTML[] =
"<!doctype html><html><head><meta charset=utf-8><title>dustycam</title></head>"
"<body style=\"font-family:sans-serif\"><p>Back to live mode.</p>"
"<p><a href=/setup>setup</a></p></body></html>";

static void mark_request(void)
{
    s_last_request_us = esp_timer_get_time();
}

static esp_err_t setup_get_handler(httpd_req_t *req)
{
    mark_request();
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, SETUP_HTML, strlen(SETUP_HTML));
}

static esp_err_t status_get_handler(httpd_req_t *req)
{
    mark_request();
    if (!s_hooks.status_json) return httpd_resp_send_err(req, HTTPD_501_METHOD_NOT_IMPLEMENTED, "no status hook");
    char buf[1024];
    int n = s_hooks.status_json(buf, sizeof(buf));
    if (n < 0) return httpd_resp_send_500(req);
    httpd_resp_set_type(req, "application/json");
    return httpd_resp_send(req, buf, n);
}

static esp_err_t shoot_post_handler(httpd_req_t *req)
{
    mark_request();
    if (!s_hooks.shoot) return httpd_resp_send_err(req, HTTPD_501_METHOD_NOT_IMPLEMENTED, "no shoot hook");
    s_hooks.shoot();
    httpd_resp_set_type(req, "text/plain");
    return httpd_resp_send(req, "ok", 2);
}

static esp_err_t refresh_post_handler(httpd_req_t *req)
{
    mark_request();
    if (!s_hooks.refresh) return httpd_resp_send_err(req, HTTPD_501_METHOD_NOT_IMPLEMENTED, "no refresh hook");
    s_hooks.refresh();
    httpd_resp_set_type(req, "text/plain");
    return httpd_resp_send(req, "ok", 2);
}

static esp_err_t live_get_handler(httpd_req_t *req)
{
    mark_request();
    if (s_hooks.live) s_hooks.live();
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, LIVE_HTML, strlen(LIVE_HTML));
}

static esp_err_t ble_post_handler(httpd_req_t *req)
{
    mark_request();
    if (!s_hooks.ble) return httpd_resp_send_err(req, HTTPD_501_METHOD_NOT_IMPLEMENTED, "no ble hook");
    if (s_hooks.draining && s_hooks.draining()) {
        /* Review finding (MINOR): don't promise in_s:2 if the phase can't
         * actually turn BLE back on yet (a drain currently owns the SD
         * card / bus mutex). Same 503-while-busy shape as frame/thumb. */
        httpd_resp_set_status(req, "503 Service Unavailable");
        httpd_resp_set_type(req, "text/plain");
        return httpd_resp_send(req, "draining", 8);
    }
    static const char BLE_RESP[] = "{\"ok\":true,\"radio\":\"ble\",\"in_s\":2}";
    httpd_resp_set_type(req, "application/json");
    esp_err_t res = httpd_resp_send(req, BLE_RESP, strlen(BLE_RESP));
    s_hooks.ble(); /* after the reply, per docs/phone_app_plan.md §3 */
    return res;
}

/* Not on the httpd worker's own stack (config.stack_size = 4096): a
 * spool.list response can run to a few KB. */
#define SPOOL_LIST_BUF_SIZE 4096
static char s_spool_list_buf[SPOOL_LIST_BUF_SIZE];

static esp_err_t spool_list_get_handler(httpd_req_t *req)
{
    mark_request();
    if (!s_hooks.spool_list) return httpd_resp_send_err(req, HTTPD_501_METHOD_NOT_IMPLEMENTED, "no spool_list hook");

    char query[160] = { 0 };
    httpd_req_get_url_query_str(req, query, sizeof(query));
    char tier[16] = "spool";
    char after[40] = "";
    char val[40];
    int n = 24;
    if (httpd_query_key_value(query, "tier", val, sizeof(val)) == ESP_OK) strlcpy(tier, val, sizeof(tier));
    if (httpd_query_key_value(query, "n", val, sizeof(val)) == ESP_OK) n = atoi(val);
    if (httpd_query_key_value(query, "after", val, sizeof(val)) == ESP_OK) strlcpy(after, val, sizeof(after));

    char req_json[220];
    snprintf(req_json, sizeof(req_json), "{\"tier\":\"%s\",\"n\":%d,\"after\":\"%s\"}", tier, n, after);

    int len = s_hooks.spool_list(req_json, s_spool_list_buf, sizeof(s_spool_list_buf));
    if (len < 0) return httpd_resp_send_500(req);
    httpd_resp_set_type(req, "application/json");
    return httpd_resp_send(req, s_spool_list_buf, len);
}

/* "/spool/<prefix_len chars>/<boot>/<seq>.jpg" style paths -- pass the
 * fixed prefix ("/spool/" or "/thumb/"); strips a trailing query string
 * defensively (req->uri is expected to already exclude it). */
static int parse_boot_seq_uri(const char *uri, const char *prefix, uint32_t *boot, uint32_t *seq)
{
    size_t plen = strlen(prefix);
    if (strncmp(uri, prefix, plen) != 0) return 0;
    char rel[64];
    strlcpy(rel, uri + plen, sizeof(rel));
    char *q = strchr(rel, '?');
    if (q) *q = '\0';
    unsigned b = 0, s = 0;
    if (sscanf(rel, "%u/%u.jpg", &b, &s) != 2) return 0;
    *boot = (uint32_t)b;
    *seq = (uint32_t)s;
    return 1;
}

static esp_err_t send_jpg_chunked(httpd_req_t *req, const uint8_t *jpg, size_t len)
{
    httpd_resp_set_type(req, "image/jpeg");
    size_t off = 0;
    esp_err_t res = ESP_OK;
    while (off < len && res == ESP_OK) {
        size_t chunk = (len - off) < 4096 ? (len - off) : 4096;
        res = httpd_resp_send_chunk(req, (const char *)(jpg + off), chunk);
        off += chunk;
    }
    if (res == ESP_OK) res = httpd_resp_send_chunk(req, NULL, 0);
    return res;
}

static esp_err_t spool_frame_get_handler(httpd_req_t *req)
{
    mark_request();
    if (!s_hooks.frame) return httpd_resp_send_err(req, HTTPD_501_METHOD_NOT_IMPLEMENTED, "no frame hook");
    uint32_t boot, seq;
    if (!parse_boot_seq_uri(req->uri, "/spool/", &boot, &seq))
        return httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "want /spool/<boot>/<seq>.jpg");

    uint8_t *jpg = NULL;
    size_t len = 0;
    int rc = s_hooks.frame(boot, seq, &jpg, &len);
    if (rc < 0) {
        httpd_resp_set_status(req, "503 Service Unavailable");
        httpd_resp_set_type(req, "text/plain");
        return httpd_resp_send(req, "busy", 4);
    }
    if (rc == 0) return httpd_resp_send_err(req, HTTPD_404_NOT_FOUND, "no such frame");
    esp_err_t res = send_jpg_chunked(req, jpg, len);
    free(jpg);
    return res;
}

static esp_err_t thumb_get_handler(httpd_req_t *req)
{
    mark_request();
    if (!s_hooks.thumb) return httpd_resp_send_err(req, HTTPD_501_METHOD_NOT_IMPLEMENTED, "no thumb hook");
    uint32_t boot, seq;
    if (!parse_boot_seq_uri(req->uri, "/thumb/", &boot, &seq))
        return httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "want /thumb/<boot>/<seq>.jpg");

    uint8_t *jpg = NULL;
    size_t len = 0;
    int rc = s_hooks.thumb(boot, seq, &jpg, &len);
    if (rc < 0) {
        httpd_resp_set_status(req, "503 Service Unavailable");
        httpd_resp_set_type(req, "text/plain");
        return httpd_resp_send(req, "busy", 4);
    }
    if (rc == 0) return httpd_resp_send_err(req, HTTPD_404_NOT_FOUND, "no such thumb");
    esp_err_t res = send_jpg_chunked(req, jpg, len);
    free(jpg);
    return res;
}

static esp_err_t stream_get_handler(httpd_req_t *req)
{
    mark_request();
    if (!s_hooks.stream_frame) return httpd_resp_send_err(req, HTTPD_501_METHOD_NOT_IMPLEMENTED, "no stream hook");

    esp_err_t res = httpd_resp_set_type(req, "multipart/x-mixed-replace;boundary=frame");
    if (res != ESP_OK) return res;

    char part_buf[80];
    while (1) {
        uint8_t *jpg = NULL;
        size_t len = 0;
        if (!s_hooks.stream_frame(&jpg, &len) || !jpg || !len) break;

        size_t hlen = snprintf(part_buf, sizeof(part_buf), STREAM_PART_BOUNDARY, (unsigned)len);
        res = httpd_resp_send_chunk(req, part_buf, hlen);
        if (res == ESP_OK) res = httpd_resp_send_chunk(req, (const char *)jpg, len);
        if (s_hooks.stream_release) s_hooks.stream_release();
        if (res != ESP_OK) break; /* client dropped */

        vTaskDelay(pdMS_TO_TICKS(200)); /* <= 5 fps */
    }
    httpd_resp_send_chunk(req, NULL, 0);
    return ESP_OK;
}

void dusty_control_start(const dusty_control_hooks_t *h)
{
    if (h) s_hooks = *h;
    else memset(&s_hooks, 0, sizeof(s_hooks));

    if (s_server) return; /* already started */

    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = 8266;
    config.lru_purge_enable = true;
    config.max_uri_handlers = 11;
    config.max_open_sockets = 2; /* docs/phone_app_plan.md §3: bound the WIFI-phase httpd's fd/heap use */
    config.stack_size = 4096;    /* keep at 4096 for now; raise if the high-water mark says so */
    config.uri_match_fn = httpd_uri_match_wildcard; /* the spool and thumb frame routes carry boot/seq in the path */

    if (httpd_start(&s_server, &config) != ESP_OK) {
        ESP_LOGE(TAG, "httpd_start failed");
        s_server = NULL;
        return;
    }

    static const httpd_uri_t uris[] = {
        { .uri = "/",        .method = HTTP_GET,  .handler = setup_get_handler },
        { .uri = "/setup",   .method = HTTP_GET,  .handler = setup_get_handler },
        { .uri = "/status",  .method = HTTP_GET,  .handler = status_get_handler },
        { .uri = "/shoot",   .method = HTTP_POST, .handler = shoot_post_handler },
        { .uri = "/refresh", .method = HTTP_POST, .handler = refresh_post_handler },
        { .uri = "/live",    .method = HTTP_GET,  .handler = live_get_handler },
        { .uri = "/stream",  .method = HTTP_GET,  .handler = stream_get_handler },
        { .uri = "/ble",     .method = HTTP_POST, .handler = ble_post_handler },
        { .uri = "/spool",   .method = HTTP_GET,  .handler = spool_list_get_handler },
        { .uri = "/spool/*", .method = HTTP_GET,  .handler = spool_frame_get_handler },
        { .uri = "/thumb/*", .method = HTTP_GET,  .handler = thumb_get_handler },
    };
    for (size_t i = 0; i < sizeof(uris) / sizeof(uris[0]); i++)
        httpd_register_uri_handler(s_server, &uris[i]);

    ESP_LOGI(TAG, "control plane on :%d", config.server_port);

    beacon_start(s_hooks.device); /* no-op if device is NULL/empty */
}

void dusty_control_stop(void)
{
    beacon_stop();
    if (!s_server) return;
    httpd_stop(s_server);
    s_server = NULL;
}

int64_t dusty_control_last_request_us(void)
{
    return s_last_request_us;
}
