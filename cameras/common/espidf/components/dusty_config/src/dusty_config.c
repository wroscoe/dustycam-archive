#include "dusty_config.h"

#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "esp_log.h"
#include "nvs.h"
#include "nvs_flash.h"

static const char *TAG = "dusty_config";
#define NVS_NS "dusty"
#define CFG_KEY "cfg"

static dc_cfg_t s_cfg;
static bool s_have_cfg;
static dc_cfg_src_t s_cfg_src;

#define IDENT_NS "ident"

static void nvs_ensure_init(void)
{
    static bool done;
    if (done) return;
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        err = nvs_flash_init();
    }
    if (err != ESP_OK) ESP_LOGE(TAG, "nvs_flash_init: 0x%x", err);
    done = true;
}

void dusty_config_init(dc_cfg_t *defaults)
{
    nvs_ensure_init();
    if (defaults) s_cfg = *defaults;
    s_have_cfg = true;

    nvs_handle_t h;
    if (nvs_open(NVS_NS, NVS_READONLY, &h) == ESP_OK) {
        size_t len = 0;
        if (nvs_get_blob(h, CFG_KEY, NULL, &len) == ESP_OK && len > 0) {
            char *json = malloc(len + 1);
            if (json) {
                if (nvs_get_blob(h, CFG_KEY, json, &len) == ESP_OK) {
                    json[len] = 0;
                    int applied = dc_cfg_apply_json(&s_cfg, json);
                    ESP_LOGI(TAG, "loaded NVS cfg (%d keys applied), cfg=%d", applied, s_cfg.cfg);
                }
                free(json);
            }
        }
        nvs_close(h);
    }

    /* cfg_src/cfg_base (docs/phone_app_plan.md §3): a fresh board (nothing
     * in NVS yet) counts its compiled-in/blob-loaded config as
     * source="server", base=that config's own cfg. */
    s_cfg_src.cfg_src_is_ble = (int)dusty_nvs_get_u32("cfg_src_ble", 0);
    s_cfg_src.cfg_base = (int)dusty_nvs_get_u32("cfg_base", (uint32_t)s_cfg.cfg);
}

const dc_cfg_t *dusty_config_get(void)
{
    return s_have_cfg ? &s_cfg : NULL;
}

static void persist(void)
{
    nvs_handle_t h;
    if (nvs_open(NVS_NS, NVS_READWRITE, &h) != ESP_OK) return;
    char json[1024];
    int n = dc_cfg_to_json(&s_cfg, json, sizeof(json));
    if (n > 0) {
        nvs_set_blob(h, CFG_KEY, json, (size_t)n);
        nvs_commit(h);
    } else {
        ESP_LOGE(TAG, "dc_cfg_to_json overflowed, cfg not persisted");
    }
    nvs_close(h);
}

int dusty_config_apply(const char *json)
{
    if (!s_have_cfg) return 0;
    int before = s_cfg.cfg;
    if (dc_cfg_apply_json(&s_cfg, json) < 0) return 0;
    persist();
    return s_cfg.cfg != before;
}

static void persist_cfg_src(void)
{
    dusty_nvs_set_u32("cfg_src_ble", (uint32_t)s_cfg_src.cfg_src_is_ble);
    dusty_nvs_set_u32("cfg_base", (uint32_t)s_cfg_src.cfg_base);
}

int dusty_config_set_local(const char *json)
{
    if (!s_have_cfg) return -1;
    dc_cfg_t before_cfg = s_cfg; /* restore on parse error -- dc_cfg_apply_json may have partially applied */
    int cfg_before = s_cfg.cfg;
    if (dc_cfg_apply_json(&s_cfg, json) < 0) {
        s_cfg = before_cfg;
        return -1;
    }
    /* The bump is always exactly 1 here, regardless of any "cfg" key in
     * the request body (docs/phone_app_plan.md §2 cfg.set: "apply known
     * keys" -- cfg itself is this function's business, not the client's). */
    s_cfg.cfg = cfg_before + 1;
    dc_cfg_src_on_local_edit(&s_cfg_src, cfg_before);
    persist();
    persist_cfg_src();
    ESP_LOGI(TAG, "local (ble) edit: cfg %d -> %d, base=%d", cfg_before, s_cfg.cfg, s_cfg_src.cfg_base);
    return s_cfg.cfg;
}

const char *dusty_config_cfg_src(void)
{
    return s_cfg_src.cfg_src_is_ble ? "ble" : "server";
}

int dusty_config_cfg_base(void)
{
    return s_cfg_src.cfg_base;
}

void dusty_config_mark_server(int cfg)
{
    dc_cfg_src_on_server_sync(&s_cfg_src, cfg);
    persist_cfg_src();
}

/* ---------------- identity (docs/camera_standard.md §5) ---------------- */

static int hex_nibble(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

/* Decodes exactly DUSTY_IDENT_BLE_KEY_LEN bytes (64 hex chars, no
 * separators, nothing trailing). Returns 0 on success. Not shared with
 * dusty_ble's identical-in-spirit ble_auth_hex_decode(): that one is
 * private to that component, and duplicating ~10 lines beats a new
 * cross-component dependency for it. */
static int hex_decode_ble_key(const char *hex, uint8_t *out)
{
    if (!hex) return -1;
    size_t i;
    for (i = 0; i < DUSTY_IDENT_BLE_KEY_LEN; i++) {
        int hi = hex_nibble(hex[2 * i]);
        int lo = hex_nibble(hex[2 * i + 1]);
        if (hi < 0 || lo < 0) return -1;
        out[i] = (uint8_t)((hi << 4) | lo);
    }
    return hex[2 * i] == '\0' ? 0 : -1;
}

/* Reads a string field from an already-open handle into a fixed buffer.
 * Returns 1 on success (found and fit), 0 otherwise (buf left alone). */
static int ident_get_str(nvs_handle_t h, const char *key, char *buf, size_t cap)
{
    size_t len = cap;
    return (nvs_get_str(h, key, buf, &len) == ESP_OK) ? 1 : 0;
}

void dusty_ident_load(dusty_ident_t *out)
{
    if (!out) return;
    memset(out, 0, sizeof(*out));
    nvs_ensure_init();

    nvs_handle_t h;
    bool have_ns = (nvs_open(IDENT_NS, NVS_READONLY, &h) == ESP_OK);

    if (!have_ns || !ident_get_str(h, "device", out->device, sizeof(out->device)))
        strlcpy(out->device, CONFIG_DUSTY_DEVICE, sizeof(out->device));
    if (!have_ns || !ident_get_str(h, "ssid", out->ssid, sizeof(out->ssid)))
        strlcpy(out->ssid, CONFIG_DUSTY_WIFI_SSID, sizeof(out->ssid));
    if (!have_ns || !ident_get_str(h, "pass", out->pass, sizeof(out->pass)))
        strlcpy(out->pass, CONFIG_DUSTY_WIFI_PASS, sizeof(out->pass));
    if (!have_ns || !ident_get_str(h, "host", out->host, sizeof(out->host)))
        strlcpy(out->host, CONFIG_DUSTY_SERVER_HOST, sizeof(out->host));
    if (!have_ns || !ident_get_str(h, "token", out->token, sizeof(out->token)))
        strlcpy(out->token, CONFIG_DUSTY_BLOB_TOKEN, sizeof(out->token));

    int32_t port_nvs = 0;
    if (have_ns && nvs_get_i32(h, "port", &port_nvs) == ESP_OK) out->port = (int)port_nvs;
    else out->port = CONFIG_DUSTY_SERVER_PORT;

    uint8_t tls_nvs = 0;
    if (have_ns && nvs_get_u8(h, "tls", &tls_nvs) == ESP_OK) out->tls = tls_nvs ? 1 : 0;
    else out->tls = CONFIG_DUSTY_SERVER_TLS ? 1 : 0;

    size_t bklen = sizeof(out->ble_key);
    if (have_ns && nvs_get_blob(h, "ble_key", out->ble_key, &bklen) == ESP_OK && bklen == DUSTY_IDENT_BLE_KEY_LEN) {
        out->ble_key_len = DUSTY_IDENT_BLE_KEY_LEN;
    } else if (hex_decode_ble_key(CONFIG_DUSTY_BLE_KEY, out->ble_key) == 0) {
        out->ble_key_len = DUSTY_IDENT_BLE_KEY_LEN;
    } else {
        memset(out->ble_key, 0, sizeof(out->ble_key));
        out->ble_key_len = 0;
    }

    if (have_ns) nvs_close(h);
}

void dusty_ident_save(const dusty_ident_t *id)
{
    if (!id) return;
    nvs_ensure_init();
    nvs_handle_t h;
    if (nvs_open(IDENT_NS, NVS_READWRITE, &h) != ESP_OK) {
        ESP_LOGE(TAG, "dusty_ident_save: nvs_open failed");
        return;
    }
    nvs_set_str(h, "device", id->device);
    nvs_set_str(h, "ssid", id->ssid);
    nvs_set_str(h, "pass", id->pass);
    nvs_set_str(h, "host", id->host);
    nvs_set_str(h, "token", id->token);
    nvs_set_i32(h, "port", (int32_t)id->port);
    nvs_set_u8(h, "tls", id->tls ? 1 : 0);
    if (id->ble_key_len == DUSTY_IDENT_BLE_KEY_LEN) {
        nvs_set_blob(h, "ble_key", id->ble_key, DUSTY_IDENT_BLE_KEY_LEN);
    }
    nvs_commit(h);
    nvs_close(h);
    ESP_LOGI(TAG, "ident saved: device=%s host=%s ssid=%s", id->device, id->host, id->ssid);
}

int dusty_ident_is_provisioned(const dusty_ident_t *id)
{
    if (!id) return 0;
    return id->device[0] != '\0' && (id->host[0] != '\0' || id->ssid[0] != '\0');
}

uint32_t dusty_nvs_get_u32(const char *key, uint32_t dflt)
{
    nvs_ensure_init();
    nvs_handle_t h;
    uint32_t v = dflt;
    if (nvs_open(NVS_NS, NVS_READONLY, &h) == ESP_OK) {
        nvs_get_u32(h, key, &v);
        nvs_close(h);
    }
    return v;
}

void dusty_nvs_set_u32(const char *key, uint32_t val)
{
    nvs_ensure_init();
    nvs_handle_t h;
    if (nvs_open(NVS_NS, NVS_READWRITE, &h) == ESP_OK) {
        nvs_set_u32(h, key, val);
        nvs_commit(h);
        nvs_close(h);
    }
}

int dusty_nvs_get_str(const char *key, char *buf, size_t n)
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

void dusty_nvs_set_str(const char *key, const char *val)
{
    nvs_ensure_init();
    nvs_handle_t h;
    if (nvs_open(NVS_NS, NVS_READWRITE, &h) == ESP_OK) {
        nvs_set_str(h, key, val);
        nvs_commit(h);
        nvs_close(h);
    }
}
