/* dusty_spool: SD-card frame store. Contract: docs/camera_operation.md §7.
 * Layout: /sd/<tier>/<boot>/<seq>.jpg + .json (sidecar written first).
 * Board-neutral: pins are passed in, not compiled in.
 */
#ifndef DUSTY_SPOOL_H
#define DUSTY_SPOOL_H

#include <stdint.h>
#include <stddef.h>
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    int cs_gpio;
    int sck_gpio;
    int miso_gpio;
    int mosi_gpio;
} dusty_spool_pins_t;

/* Must be called before dusty_spool_mount(). */
void dusty_spool_set_pins(const dusty_spool_pins_t *pins);

int dusty_spool_mount(void);      /* 1 on success, 0 on failure */
void dusty_spool_unmount(void);
int dusty_spool_mounted(void);

/* Sidecar (.json) written first, then jpg to a .tmp name, fsync, rename
 * into place. Creates the tier and boot directories as needed. Returns 1
 * on success. */
int dusty_spool_write(const char *tier, uint32_t boot, uint32_t seq,
                       const uint8_t *jpg, size_t n, const char *meta_json);

typedef struct {
    uint32_t boot;
    uint32_t seq;
    float score;
    char why[12];
} dusty_spool_entry_t;

/* Walks /sd/<tier>/<boot>/ for every wake, reading each sidecar's score
 * (capped at 1 KB per sidecar). Returns the number of entries written to
 * `out` (up to max), or the total count found if that's larger. */
int dusty_spool_scan(const char *tier, dusty_spool_entry_t *out, int max);
void dusty_spool_sort_desc(dusty_spool_entry_t *entries, int n);

int dusty_spool_delete(const char *tier, uint32_t boot, uint32_t seq);
int dusty_spool_count(const char *tier);

/* Deletes the lowest boot/seq frames in `tier` until its count is <=
 * max_frames. Returns the number deleted. */
int dusty_spool_reclaim(const char *tier, int max_frames);

int dusty_spool_read_text(const char *path, char *buf, size_t n);
int dusty_spool_write_text(const char *path, const char *text);

/* The SD bus mutex every operation above takes; exported so dusty_led can
 * skip a toggle rather than block behind an in-flight card transaction
 * (LED and SD CS share a pin on the XIAO). NULL until dusty_spool_mount()
 * has been called once. */
SemaphoreHandle_t dusty_spool_bus_mutex(void);

#ifdef __cplusplus
}
#endif
#endif
