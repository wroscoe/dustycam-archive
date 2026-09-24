/* dusty_ota: version bookkeeping + esp_https_ota install with rollback.
 * Contract: docs/camera_operation.md §5.4; sarg lessons
 * deep-sleep-wake-rolls-back-pending-verify-ota-image and
 * esp-https-ota-main-task-stack-overflow-reboot-loop-bricks-ota apply to
 * every caller of dusty_ota_check_and_install (it restarts on success).
 */
#ifndef DUSTY_OTA_H
#define DUSTY_OTA_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Host/token used to fetch /firmware/<device>.bin. */
void dusty_ota_init(const char *host, int port, int tls, const char *token, const char *device);

const char *dusty_ota_running_version(void); /* esp_app_desc version */
int dusty_ota_pending_verify(void);          /* 1 if this boot must prove itself before sleeping */
void dusty_ota_mark_valid(void);             /* cancels rollback */

/* Call once at boot, before any sleep. If NVS "fw_pending" is set and
 * differs from the running version, the bootloader must have rolled the
 * pending image back: writes NVS "fw_bad" = that pending version, clears
 * "fw_pending", and returns 1 (a rollback happened, worth a telemetry/log
 * line). Returns 0 otherwise. */
int dusty_ota_boot_check(void);

/* remote_version is the string already fetched via dusty_uplink_get on
 * GET /firmware/<device>/version. Installs when dc_fw_should_install says
 * so: esp_https_ota from /firmware/<device>.bin (X-Token, cert bundle
 * when tls), and on success writes NVS "fw_pending" = remote_version and
 * calls esp_restart() (does not return). Returns 0 (nothing to do), 1
 * (should not happen: install returned without restarting), or -1 (OTA
 * failed, old image keeps running). */
int dusty_ota_check_and_install(const char *remote_version);

#ifdef __cplusplus
}
#endif
#endif
