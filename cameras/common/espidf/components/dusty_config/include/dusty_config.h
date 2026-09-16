/* dusty_config: tier-2 tuning storage. Defaults stamped into the firmware
 * (dustygen -> main/tuning_defaults.h) are overridden by whatever was last
 * pulled from the server and persisted in NVS. Contract:
 * docs/camera_standard.md §5, docs/camera_operation.md §4.1.
 */
#ifndef DUSTY_CONFIG_H
#define DUSTY_CONFIG_H

#include <stdint.h>
#include <stddef.h>
#include "dusty_core.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Copies *defaults, then overlays the NVS "cfg" blob (namespace "dusty")
 * on top if one is stored. Safe to call once at boot. Also loads the
 * cfg_src/cfg_base pair (dc_cfg_src_t, dusty_core.h) from NVS, defaulting
 * to source="server", base=the config's own `cfg` if nothing is stored
 * yet (a fresh board's compiled-in/pulled defaults count as "server"). */
void dusty_config_init(dc_cfg_t *defaults);

const dc_cfg_t *dusty_config_get(void);

/* Applies known keys from `json` onto the live config and persists the
 * result to NVS. Returns 1 if `cfg` (the version number) changed, 0
 * otherwise (including on a parse error, in which case nothing changes).
 * Does NOT touch cfg_src/cfg_base -- this is the server-pull path
 * (docs/camera_standard.md §4 "Config pull"); see dusty_config_mark_server()
 * below, which the caller invokes once the pull is known to have landed. */
int dusty_config_apply(const char *json);

/* The BLE local-edit path (docs/phone_app_plan.md §2 `cfg.set`, §3):
 * applies known keys from `json` (any "cfg" key in it is ignored -- the
 * version always bumps by exactly 1 here), persists, marks cfg_src="ble"
 * and updates cfg_base per dc_cfg_src_on_local_edit()'s rule. Returns the
 * new `cfg` value, or -1 on a parse error (nothing changes). */
int dusty_config_set_local(const char *json);

/* "server" or "ble" -- whether the live config's most recent change came
 * from a sensorhub pull/push (dusty_config_mark_server()) or a BLE edit
 * (dusty_config_set_local()) that hasn't been reconciled with the server
 * yet. */
const char *dusty_config_cfg_src(void);
/* The server `cfg` version the current cfg_src="ble" chain diverged from
 * (meaningless but still returned when cfg_src=="server", where it equals
 * the current `cfg`). This is the `base` a config-push body carries. */
int dusty_config_cfg_base(void);
/* Call after a successful pull from, or accepted/rejected push to,
 * sensorhub: cfg_src becomes "server" and cfg_base becomes `cfg` (the
 * version now agreed with the server, whichever side it came from). */
void dusty_config_mark_server(int cfg);

/* Tier-1 identity (docs/camera_standard.md §5, docs/phone_app_plan.md
 * decision 7): NVS namespace "ident" (device/ssid/pass/host/port/tls/
 * token/ble_key), falling back per-field to the compiled-in CONFIG_DUSTY_*
 * (main/Kconfig.projbuild) when NVS has nothing -- ble_key falls back to
 * CONFIG_DUSTY_BLE_KEY (hex) decoded to raw bytes. Every project that
 * links this component must declare those Kconfig options (xiao_pantilt's
 * and bench/ble_spike's main/Kconfig.projbuild both already do). */
#define DUSTY_IDENT_DEVICE_MAX 32
#define DUSTY_IDENT_SSID_MAX 33
#define DUSTY_IDENT_PASS_MAX 65
#define DUSTY_IDENT_HOST_MAX 96
#define DUSTY_IDENT_TOKEN_MAX 96
#define DUSTY_IDENT_BLE_KEY_LEN 32

typedef struct {
    char device[DUSTY_IDENT_DEVICE_MAX];
    char ssid[DUSTY_IDENT_SSID_MAX];
    char pass[DUSTY_IDENT_PASS_MAX];
    char host[DUSTY_IDENT_HOST_MAX];
    int port;
    int tls;
    char token[DUSTY_IDENT_TOKEN_MAX];
    uint8_t ble_key[DUSTY_IDENT_BLE_KEY_LEN];
    int ble_key_len; /* DUSTY_IDENT_BLE_KEY_LEN if valid (NVS or Kconfig hex decoded OK), 0 otherwise */
} dusty_ident_t;

/* Never fails outright: any field missing from both NVS and Kconfig just
 * comes back empty/zero (ble_key_len 0 means "no BLE auth possible yet"). */
void dusty_ident_load(dusty_ident_t *out);
void dusty_ident_save(const dusty_ident_t *id);
/* device non-empty AND (host non-empty OR ssid non-empty) -- decision 7's
 * "blank fleet image" is device=="" (an unprovisioned NVS-blank board). */
int dusty_ident_is_provisioned(const dusty_ident_t *id);

/* Small NVS helpers ("dusty" namespace) other components use directly
 * (boot_count, seq_base, last_ts, fw_pending, fw_bad, contact_n, ...). */
uint32_t dusty_nvs_get_u32(const char *key, uint32_t dflt);
void dusty_nvs_set_u32(const char *key, uint32_t val);
int dusty_nvs_get_str(const char *key, char *buf, size_t n); /* 1 on success */
void dusty_nvs_set_str(const char *key, const char *val);

#ifdef __cplusplus
}
#endif
#endif
