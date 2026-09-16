#include "dusty_spool.h"
#include "dusty_core.h"

#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <dirent.h>
#include <sys/stat.h>
#include <unistd.h>

#include "esp_log.h"
#include "esp_vfs_fat.h"
#include "driver/sdspi_host.h"
#include "driver/spi_common.h"
#include "sdmmc_cmd.h"

static const char *TAG = "dusty_spool";
#define MOUNT_POINT "/sd"
#define SIDECAR_CAP 1024

static dusty_spool_pins_t s_pins = { -1, -1, -1, -1 };
static sdmmc_card_t *s_card;
static bool s_mounted;
/* True once mount_locked() has initialised the SPI bus itself. The bus is
 * deliberately kept up across unmount/remount (it carries no state worth
 * resetting, and re-creating it churns DMA-capable internal RAM on every
 * lazy remount); this flag stops remounts from re-initialising it (the old
 * "spi_bus_initialize: SPI bus already initialized" E-line) and stops the
 * failure path from freeing a bus this code does not own. */
static bool s_bus_owned;
static SemaphoreHandle_t s_mutex;

void dusty_spool_set_pins(const dusty_spool_pins_t *pins)
{
    if (pins) s_pins = *pins;
}

static int mount_locked(void);

int dusty_spool_mount(void)
{
    if (s_mounted) return 1;
    if (!s_mutex) s_mutex = xSemaphoreCreateMutex();
    /* Hold the bus mutex for the whole card init: the LED shares GPIO21
     * with SD CS and its pattern task toggles the pin whenever this mutex
     * is free, which corrupted chip-select mid-init on the XIAO
     * (sdmmc_card_init 0x107 with a good card, 2026-09-15). */
    xSemaphoreTake(s_mutex, portMAX_DELAY);
    int ok = mount_locked();
    xSemaphoreGive(s_mutex);
    return ok;
}

static int mount_locked(void)
{

    spi_bus_config_t bus = {
        .mosi_io_num = s_pins.mosi_gpio,
        .miso_io_num = s_pins.miso_gpio,
        .sclk_io_num = s_pins.sck_gpio,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 16 * 1024,
    };
    sdmmc_host_t host = SDSPI_HOST_DEFAULT();
    esp_err_t err = ESP_OK;
    bool inited_now = false;
    if (!s_bus_owned) {
        err = spi_bus_initialize(host.slot, &bus, SDSPI_DEFAULT_DMA);
        if (err == ESP_OK) {
            s_bus_owned = true;
            inited_now = true;
        } else if (err != ESP_ERR_INVALID_STATE) { /* someone else's bus: use it, never free it */
            ESP_LOGE(TAG, "spi_bus_initialize: %s", esp_err_to_name(err));
            return 0;
        }
    }
    sdspi_device_config_t slot = SDSPI_DEVICE_CONFIG_DEFAULT();
    slot.gpio_cs = s_pins.cs_gpio;
    slot.host_id = host.slot;

    esp_vfs_fat_sdmmc_mount_config_t mount_cfg = {
        .format_if_mount_failed = false,
        .max_files = 8,
        .allocation_unit_size = 16 * 1024,
    };
    /* SPI-mode cards go through the sdspi mount: the sdmmc variant
     * reinterprets the slot struct and fails with ESP_ERR_INVALID_STATE
     * (seen on the first XIAO flash, 2026-09-15). */
    err = esp_vfs_fat_sdspi_mount(MOUNT_POINT, &host, &slot, &mount_cfg, &s_card);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "sd mount failed: %s", esp_err_to_name(err));
        if (inited_now) {
            spi_bus_free(host.slot);
            s_bus_owned = false;
        }
        return 0;
    }
    s_mounted = true;
    ESP_LOGI(TAG, "sd mounted, %llu MB",
             (unsigned long long)s_card->csd.capacity * s_card->csd.sector_size / (1024 * 1024));
    return 1;
}

void dusty_spool_unmount(void)
{
    if (!s_mounted) return;
    xSemaphoreTake(s_mutex, portMAX_DELAY);
    esp_vfs_fat_sdcard_unmount(MOUNT_POINT, s_card);
    s_card = NULL;
    s_mounted = false;
    xSemaphoreGive(s_mutex);
}

int dusty_spool_mounted(void)
{
    return s_mounted ? 1 : 0;
}

SemaphoreHandle_t dusty_spool_bus_mutex(void)
{
    if (!s_mutex) s_mutex = xSemaphoreCreateMutex();
    return s_mutex;
}

static void mkdir_p_one(const char *path)
{
    if (mkdir(path, 0775) != 0) {
        /* EEXIST is fine; anything else is logged by the caller's next
         * failing file op */
    }
}

static int write_whole_file(const char *path, const uint8_t *data, size_t n, int is_text)
{
    FILE *f = fopen(path, is_text ? "w" : "wb");
    if (!f) return 0;
    size_t written = fwrite(data, 1, n, f);
    fflush(f);
    fsync(fileno(f));
    fclose(f);
    return written == n;
}

int dusty_spool_write(const char *tier, uint32_t boot, uint32_t seq,
                       const uint8_t *jpg, size_t n, const char *meta_json)
{
    if (!s_mounted) return 0;
    char tier_dir[64], boot_dir[80], json_path[96], jpg_path[96], tmp_path[100];
    snprintf(tier_dir, sizeof(tier_dir), MOUNT_POINT "/%s", tier);
    snprintf(boot_dir, sizeof(boot_dir), "%s/%u", tier_dir, (unsigned)boot);

    if (dc_spool_path(json_path, sizeof(json_path), MOUNT_POINT, tier, boot, seq, "json") < 0) return 0;
    if (dc_spool_path(jpg_path, sizeof(jpg_path), MOUNT_POINT, tier, boot, seq, "jpg") < 0) return 0;
    snprintf(tmp_path, sizeof(tmp_path), "%s.tmp", jpg_path);

    xSemaphoreTake(s_mutex, portMAX_DELAY);
    mkdir_p_one(tier_dir);
    mkdir_p_one(boot_dir);

    int ok = write_whole_file(json_path, (const uint8_t *)meta_json, strlen(meta_json), 1);
    if (ok) ok = write_whole_file(tmp_path, jpg, n, 0);
    if (ok) ok = (rename(tmp_path, jpg_path) == 0);
    if (!ok) {
        ESP_LOGE(TAG, "spool_write failed for %s", jpg_path);
        unlink(tmp_path);
        unlink(json_path);
    }
    xSemaphoreGive(s_mutex);
    return ok;
}

int dusty_spool_read_text(const char *path, char *buf, size_t n)
{
    if (!s_mounted || !buf || n == 0) return 0;
    xSemaphoreTake(s_mutex, portMAX_DELAY);
    FILE *f = fopen(path, "r");
    int ok = 0;
    if (f) {
        size_t got = fread(buf, 1, n - 1, f);
        buf[got] = 0;
        fclose(f);
        ok = 1;
    }
    xSemaphoreGive(s_mutex);
    return ok;
}

int dusty_spool_write_text(const char *path, const char *text)
{
    if (!s_mounted) return 0;
    xSemaphoreTake(s_mutex, portMAX_DELAY);
    int ok = write_whole_file(path, (const uint8_t *)text, strlen(text), 1);
    xSemaphoreGive(s_mutex);
    return ok;
}

/* ---------------- scan / rank / reclaim ---------------- */

static int read_sidecar_score(const char *path, float *score, char *why, size_t why_n)
{
    FILE *f = fopen(path, "r");
    if (!f) return 0;
    char buf[SIDECAR_CAP];
    size_t got = fread(buf, 1, sizeof(buf) - 1, f);
    fclose(f);
    buf[got] = 0;
    return dc_sidecar_score(buf, score, why, why_n);
}

int dusty_spool_scan(const char *tier, dusty_spool_entry_t *out, int max)
{
    if (!s_mounted) return 0;
    char tier_dir[64];
    snprintf(tier_dir, sizeof(tier_dir), MOUNT_POINT "/%s", tier);

    xSemaphoreTake(s_mutex, portMAX_DELAY);
    int total = 0;
    DIR *td = opendir(tier_dir);
    if (!td) { xSemaphoreGive(s_mutex); return 0; }
    struct dirent *bd;
    while ((bd = readdir(td)) != NULL) {
        if (bd->d_name[0] == '.') continue;
        char *end;
        unsigned long boot = strtoul(bd->d_name, &end, 10);
        if (*end != '\0') continue; /* not a boot dir */
        char boot_dir[320];
        snprintf(boot_dir, sizeof(boot_dir), "%.200s/%.100s", tier_dir, bd->d_name);
        DIR *sd = opendir(boot_dir);
        if (!sd) continue;
        struct dirent *fe;
        while ((fe = readdir(sd)) != NULL) {
            size_t len = strlen(fe->d_name);
            if (len < 6 || strcmp(fe->d_name + len - 5, ".json") != 0) continue;
            unsigned long seq = strtoul(fe->d_name, &end, 10);
            if (strncmp(end, ".json", 5) != 0) continue;
            char json_path[420];
            snprintf(json_path, sizeof(json_path), "%.300s/%.100s", boot_dir, fe->d_name);
            float score = 0;
            char why[12] = { 0 };
            if (!read_sidecar_score(json_path, &score, why, sizeof(why))) continue;
            if (out && total < max) {
                out[total].boot = (uint32_t)boot;
                out[total].seq = (uint32_t)seq;
                out[total].score = score;
                strlcpy(out[total].why, why, sizeof(out[total].why));
            }
            total++;
        }
        closedir(sd);
    }
    closedir(td);
    xSemaphoreGive(s_mutex);
    return total;
}

static int entry_cmp_desc(const void *pa, const void *pb)
{
    const dusty_spool_entry_t *a = pa, *b = pb;
    if (a->score != b->score) return (a->score < b->score) ? 1 : -1;
    if (a->boot != b->boot) return (a->boot < b->boot) ? -1 : 1;
    if (a->seq != b->seq) return (a->seq < b->seq) ? -1 : 1;
    return 0;
}

void dusty_spool_sort_desc(dusty_spool_entry_t *entries, int n)
{
    if (entries && n > 0) qsort(entries, n, sizeof(entries[0]), entry_cmp_desc);
}

int dusty_spool_delete(const char *tier, uint32_t boot, uint32_t seq)
{
    if (!s_mounted) return 0;
    char jpg[96], json[96];
    if (dc_spool_path(jpg, sizeof(jpg), MOUNT_POINT, tier, boot, seq, "jpg") < 0) return 0;
    if (dc_spool_path(json, sizeof(json), MOUNT_POINT, tier, boot, seq, "json") < 0) return 0;
    xSemaphoreTake(s_mutex, portMAX_DELAY);
    unlink(jpg);
    unlink(json);
    xSemaphoreGive(s_mutex);
    return 1;
}

int dusty_spool_count(const char *tier)
{
    return dusty_spool_scan(tier, NULL, 0);
}

static int u32_cmp(const void *a, const void *b)
{
    uint32_t x = *(const uint32_t *)a, y = *(const uint32_t *)b;
    return (x > y) - (x < y);
}

int dusty_spool_reclaim(const char *tier, int max_frames)
{
    if (!s_mounted) return 0;
    int total = dusty_spool_count(tier);
    int need = total - max_frames;
    if (need <= 0) return 0;

    char tier_dir[64];
    snprintf(tier_dir, sizeof(tier_dir), MOUNT_POINT "/%s", tier);

    xSemaphoreTake(s_mutex, portMAX_DELAY);
    /* gather boot dir numbers, oldest first */
    uint32_t *boots = NULL;
    int nboots = 0, cap = 0;
    DIR *td = opendir(tier_dir);
    if (!td) { xSemaphoreGive(s_mutex); return 0; }
    struct dirent *bd;
    while ((bd = readdir(td)) != NULL) {
        if (bd->d_name[0] == '.') continue;
        char *end;
        unsigned long boot = strtoul(bd->d_name, &end, 10);
        if (*end != '\0') continue;
        if (nboots == cap) {
            int ncap = cap ? cap * 2 : 16;
            uint32_t *nb = realloc(boots, ncap * sizeof(uint32_t));
            if (!nb) break; /* reclaim what fits; the rest waits for the next contact */
            boots = nb;
            cap = ncap;
        }
        boots[nboots++] = (uint32_t)boot;
    }
    closedir(td);
    qsort(boots, nboots, sizeof(uint32_t), u32_cmp);

    int deleted = 0;
    for (int bi = 0; bi < nboots && deleted < need; bi++) {
        char boot_dir[96];
        snprintf(boot_dir, sizeof(boot_dir), "%s/%u", tier_dir, (unsigned)boots[bi]);
        uint32_t *seqs = NULL;
        int nseqs = 0, scap = 0;
        DIR *sd = opendir(boot_dir);
        if (!sd) continue;
        struct dirent *fe;
        while ((fe = readdir(sd)) != NULL) {
            size_t len = strlen(fe->d_name);
            if (len < 5 || strcmp(fe->d_name + len - 4, ".jpg") != 0) continue;
            char *end;
            unsigned long seq = strtoul(fe->d_name, &end, 10);
            if (strncmp(end, ".jpg", 4) != 0) continue;
            if (nseqs == scap) {
                int ncap = scap ? scap * 2 : 16;
                uint32_t *ns = realloc(seqs, ncap * sizeof(uint32_t));
                if (!ns) break;
                seqs = ns;
                scap = ncap;
            }
            seqs[nseqs++] = (uint32_t)seq;
        }
        closedir(sd);
        qsort(seqs, nseqs, sizeof(uint32_t), u32_cmp);
        for (int si = 0; si < nseqs && deleted < need; si++) {
            char jpg[160], json[160];
            snprintf(jpg, sizeof(jpg), "%s/%06u.jpg", boot_dir, (unsigned)seqs[si]);
            snprintf(json, sizeof(json), "%s/%06u.json", boot_dir, (unsigned)seqs[si]);
            unlink(jpg);
            unlink(json);
            deleted++;
        }
        free(seqs);
    }
    free(boots);
    xSemaphoreGive(s_mutex);
    ESP_LOGI(TAG, "reclaim %s: deleted %d of %d needed (had %d, cap %d)",
             tier, deleted, need, total, max_frames);
    return deleted;
}
