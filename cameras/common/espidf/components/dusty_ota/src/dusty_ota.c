#include "dusty_ota.h"
#include "dusty_core.h"

#include <string.h>
#include <stdio.h>
#include <stdbool.h>

#include "esp_log.h"
#include "esp_app_desc.h"
#include "esp_ota_ops.h"
#include "esp_https_ota.h"
#include "esp_http_client.h"
#include "esp_crt_bundle.h"
#include "nvs.h"
#include "nvs_flash.h"

static const char *TAG = "dusty_ota";
#define NVS_NS "dusty"

static char s_host[64];
static int s_port = 10000;
static int s_tls = 1;
static char s_token[64];
static char s_device[32];

void dusty_ota_init(const char *host, int port, int tls, const char *token, const char *device)
{
    if (host) strlcpy(s_host, host, sizeof(s_host));
    s_port = port;
    s_tls = tls ? 1 : 0;
    if (token) strlcpy(s_token, token, sizeof(s_token));
    if (device) strlcpy(s_device, device, sizeof(s_device));
}

const char *dusty_ota_running_version(void)
{
    return esp_app_get_description()->version;
}

int dusty_ota_pending_verify(void)
{
    esp_ota_img_states_t st;
    const esp_partition_t *run = esp_ota_get_running_partition();
    if (esp_ota_get_state_partition(run, &st) == ESP_OK)
        return st == ESP_OTA_IMG_PENDING_VERIFY;
    return 0;
}

void dusty_ota_mark_valid(void)
{
    esp_err_t err = esp_ota_mark_app_valid_cancel_rollback();
    if (err == ESP_OK) ESP_LOGI(TAG, "app marked valid");
}

static void nvs_ensure_init(void)
{
    static bool done;
    if (done) return;
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }
    done = true;
}

static int nvs_get_string(const char *key, char *buf, size_t n)
{
    nvs_ensure_init();
    nvs_handle_t h;
    int ok = 0;
    if (nvs_open(NVS_NS, NVS_READONLY, &h) == ESP_OK) {
        size_t len = n;
        if (nvs_get_str(h, key, buf, &len) == ESP_OK) ok = 1;
        nvs_close(h);
    }
    if (!ok && n) buf[0] = 0;
    return ok;
}

static void nvs_set_string(const char *key, const char *val)
{
    nvs_ensure_init();
    nvs_handle_t h;
    if (nvs_open(NVS_NS, NVS_READWRITE, &h) == ESP_OK) {
        nvs_set_str(h, key, val);
        nvs_commit(h);
        nvs_close(h);
    }
}

static void nvs_erase(const char *key)
{
    nvs_ensure_init();
    nvs_handle_t h;
    if (nvs_open(NVS_NS, NVS_READWRITE, &h) == ESP_OK) {
        nvs_erase_key(h, key);
        nvs_commit(h);
        nvs_close(h);
    }
}

int dusty_ota_boot_check(void)
{
    char pending[32];
    if (!nvs_get_string("fw_pending", pending, sizeof(pending)) || !pending[0]) return 0;
    const char *running = dusty_ota_running_version();
    if (strcmp(pending, running) == 0) {
        /* we ARE the pending image, running normally: caller (contact/
         * package B) still needs to see pending-verify and mark valid
         * after its first successful upload. */
        return 0;
    }
    /* pending names a DIFFERENT version than what's running: the
     * bootloader rolled back (sarg: deep-sleep-wake-rolls-back-pending-
     * verify-ota-image). Blacklist it so we never retry the same bad
     * build, and clear pending. */
    ESP_LOGW(TAG, "fw_pending=%s but running=%s: bootloader rolled back", pending, running);
    nvs_set_string("fw_bad", pending);
    nvs_erase("fw_pending");
    return 1;
}

static esp_err_t ota_http_init(esp_http_client_handle_t client)
{
    if (s_token[0]) esp_http_client_set_header(client, "X-Token", s_token);
    esp_http_client_set_header(client, "Connection", "close");
    return ESP_OK;
}

int dusty_ota_check_and_install(const char *remote_version)
{
    char bad[32];
    nvs_get_string("fw_bad", bad, sizeof(bad));
    if (!dc_fw_should_install(remote_version, dusty_ota_running_version(), bad))
        return 0;

    ESP_LOGW(TAG, "firmware update: %s -> %s", dusty_ota_running_version(), remote_version);
    char url[128];
    snprintf(url, sizeof(url), "%s://%s:%d/firmware/%s.bin",
             s_tls ? "https" : "http", s_host, s_port, s_device);

    esp_http_client_config_t http_cfg = {
        .url = url,
        .timeout_ms = 15000,
        .keep_alive_enable = true,
        .crt_bundle_attach = s_tls ? esp_crt_bundle_attach : NULL,
    };
    esp_https_ota_config_t ota_cfg = { .http_config = &http_cfg, .http_client_init_cb = ota_http_init };

    esp_err_t err = esp_https_ota(&ota_cfg);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_https_ota failed: %s", esp_err_to_name(err));
        return -1;
    }
    /* Must persist fw_pending and restart before any deep sleep: a
     * pending-verify image that goes to sleep without proving itself
     * gets rolled back by the bootloader on the next wake (sarg). */
    nvs_set_string("fw_pending", remote_version);
    ESP_LOGW(TAG, "OTA ok, restarting into %s", remote_version);
    esp_restart();
    return 1; /* unreachable */
}
