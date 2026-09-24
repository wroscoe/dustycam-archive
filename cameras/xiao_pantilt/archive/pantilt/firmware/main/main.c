/* XIAO ESP32S3 Sense pan scanner.
 *
 * Position is never read from a motor, current sensor, or imagined encoder.
 * Timed PWM is only a bounded actuator; every accepted step is measured from
 * a profile decoded from a stationary JPEG captured by esp32-camera.
 */
#include <dirent.h>
#include <fcntl.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "driver/gpio.h"
#include "driver/ledc.h"
#include "driver/sdspi_host.h"
#include "driver/spi_common.h"
#include "esp_camera.h"
#include "esp_check.h"
#include "esp_err.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "esp_vfs_fat.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "img_converters.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "sdmmc_cmd.h"

#include "pt_core.h"

#define TAG "pantilt"
#define SD_MOUNT "/sd"
#define PHOTO_DIR SD_MOUNT "/pantilt"
#define TRACK_W 100
#define TRACK_H 75
#define PWM_MAX 1023

/* Official Seeed XIAO ESP32S3 Sense camera signal map. Do not borrow pins
 * from the unrelated GOOUUU camlogger board. */
#define CAM_PIN_XCLK 10
#define CAM_PIN_SIOD 40
#define CAM_PIN_SIOC 39
#define CAM_PIN_D0 15
#define CAM_PIN_D1 17
#define CAM_PIN_D2 18
#define CAM_PIN_D3 16
#define CAM_PIN_D4 14
#define CAM_PIN_D5 12
#define CAM_PIN_D6 11
#define CAM_PIN_D7 48
#define CAM_PIN_VSYNC 38
#define CAM_PIN_HREF 47
#define CAM_PIN_PCLK 13
#define CAM_PIN_PWDN -1
#define CAM_PIN_RESET -1

typedef struct {
    camera_fb_t *fb;
    pt_profile_t profile;
} captured_t;

typedef struct {
    pt_profile_t profile;
    float yaw_deg;
} anchor_t;

static sdmmc_card_t *s_card;
static bool s_sd_mounted;
static bool s_motor_ready;
static uint32_t s_boot_id;
static uint32_t s_file_sequence;
static bool s_have_verified_home;
static pt_profile_t s_verified_home;

static const int s_camera_pins[] = {
    CAM_PIN_XCLK, CAM_PIN_SIOD, CAM_PIN_SIOC, CAM_PIN_D0, CAM_PIN_D1, CAM_PIN_D2,
    CAM_PIN_D3, CAM_PIN_D4, CAM_PIN_D5, CAM_PIN_D6, CAM_PIN_D7, CAM_PIN_VSYNC,
    CAM_PIN_HREF, CAM_PIN_PCLK,
};

static bool is_camera_pin(int pin)
{
    for (unsigned i = 0; i < sizeof(s_camera_pins) / sizeof(s_camera_pins[0]); ++i)
        if (s_camera_pins[i] == pin) return true;
    return false;
}

static bool is_actuator_or_limit_pin(int pin)
{
    /* Do not drive Sense's camera, PDM mic (41/42), or onboard SD signals.
     * This is intentionally narrower than the full XIAO pinout. */
    static const int allowed[] = {1, 2, 3, 4, 5, 6, 43, 44};
    for (unsigned i = 0; i < sizeof(allowed) / sizeof(allowed[0]); ++i)
        if (allowed[i] == pin) return true;
    return false;
}

static bool is_sd_usable_pin(int pin)
{
    /* GPIO21 is exposed for the Sense onboard card CS; it is not offered to
     * the motor/limit whitelist. Other exposed pins remain available for an
     * explicitly wired external SPI carrier. */
    static const int allowed[] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 21, 43, 44};
    for (unsigned i = 0; i < sizeof(allowed) / sizeof(allowed[0]); ++i)
        if (allowed[i] == pin) return true;
    return false;
}

static bool configured_pins_are_safe(void)
{
    const int pins[] = {CONFIG_PANTILT_MOTOR_IN1_GPIO, CONFIG_PANTILT_MOTOR_IN2_GPIO,
                        CONFIG_PANTILT_HOME_LIMIT_GPIO, CONFIG_PANTILT_SD_CS_GPIO,
                        CONFIG_PANTILT_SD_SCK_GPIO, CONFIG_PANTILT_SD_MISO_GPIO, CONFIG_PANTILT_SD_MOSI_GPIO};
    for (unsigned i = 0; i < sizeof(pins) / sizeof(pins[0]); ++i) {
        bool is_actuator = i < 3u;
        if (pins[i] >= 0 && ((!is_actuator && !is_sd_usable_pin(pins[i])) ||
                             (is_actuator && !is_actuator_or_limit_pin(pins[i])) || is_camera_pin(pins[i]))) return false;
        for (unsigned j = 0; j < i; ++j)
            if (pins[i] >= 0 && pins[i] == pins[j]) return false;
    }
    return true;
}

static bool production_limit_configured(void)
{
#if CONFIG_PANTILT_HOME_LIMIT_GPIO >= 0
    return true;
#else
    return false;
#endif
}

static bool configured_budgets_can_recover_home(void)
{
    unsigned home_pulses = (CONFIG_PANTILT_HOME_MAX_MS + CONFIG_PANTILT_MAX_PULSE_MS - 1u) /
                           CONFIG_PANTILT_MAX_PULSE_MS;
    unsigned backoff_pulses = (CONFIG_PANTILT_HOME_BACKOFF_MS + CONFIG_PANTILT_MAX_PULSE_MS - 1u) /
                              CONFIG_PANTILT_MAX_PULSE_MS;
    /* A cold/lost home may consume a full approach, and a failure immediately
     * afterwards must still be able to back off/re-approach once. */
    unsigned full_move_count = 2u * (PT_SCAN_ANCHOR_COUNT - 1u);
    return 2u * CONFIG_PANTILT_HOME_MAX_MS + CONFIG_PANTILT_HOME_BACKOFF_MS +
               full_move_count * CONFIG_PANTILT_MAX_MOVE_MOTION_MS <= CONFIG_PANTILT_MAX_CYCLE_MOTION_MS &&
           2u * home_pulses + backoff_pulses + full_move_count * CONFIG_PANTILT_MAX_MOVE_PULSES <=
               CONFIG_PANTILT_MAX_CYCLE_PULSES;
}

#if CONFIG_PANTILT_HOME_LIMIT_GPIO >= 0
static bool active_limit(void)
{
    int level = gpio_get_level(CONFIG_PANTILT_HOME_LIMIT_GPIO);
#if CONFIG_PANTILT_HOME_LIMIT_ACTIVE_LOW
    return level == 0;
#else
    return level != 0;
#endif
}
#endif

static esp_err_t camera_init_xiao(void)
{
    camera_config_t cfg = {0};
    cfg.ledc_channel = LEDC_CHANNEL_2;
    cfg.ledc_timer = LEDC_TIMER_1;
    cfg.pin_d0 = CAM_PIN_D0; cfg.pin_d1 = CAM_PIN_D1; cfg.pin_d2 = CAM_PIN_D2; cfg.pin_d3 = CAM_PIN_D3;
    cfg.pin_d4 = CAM_PIN_D4; cfg.pin_d5 = CAM_PIN_D5; cfg.pin_d6 = CAM_PIN_D6; cfg.pin_d7 = CAM_PIN_D7;
    cfg.pin_xclk = CAM_PIN_XCLK; cfg.pin_pclk = CAM_PIN_PCLK; cfg.pin_vsync = CAM_PIN_VSYNC; cfg.pin_href = CAM_PIN_HREF;
    cfg.pin_sccb_sda = CAM_PIN_SIOD; cfg.pin_sccb_scl = CAM_PIN_SIOC;
    cfg.pin_pwdn = CAM_PIN_PWDN; cfg.pin_reset = CAM_PIN_RESET;
    cfg.xclk_freq_hz = 20000000;
    cfg.pixel_format = PIXFORMAT_JPEG;
    cfg.frame_size = FRAMESIZE_SVGA;
    cfg.jpeg_quality = 12;
    cfg.fb_count = 2;
    cfg.fb_location = CAMERA_FB_IN_PSRAM;
    cfg.grab_mode = CAMERA_GRAB_LATEST;
    ESP_RETURN_ON_ERROR(esp_camera_init(&cfg), TAG, "camera init");
    /* JPEG + PSRAM is intentional: esp32-camera documents this as the stable
     * high-resolution path. Tracking is decoded from that same settled JPEG. */
    for (int i = 0; i < 2; ++i) {
        camera_fb_t *warm = esp_camera_fb_get();
        if (warm) esp_camera_fb_return(warm);
        vTaskDelay(pdMS_TO_TICKS(100));
    }
    return ESP_OK;
}

static bool profile_from_jpeg(const camera_fb_t *fb, pt_profile_t *profile)
{
    static uint8_t rgb565[TRACK_W * TRACK_H * 2];
    if (!fb || !profile || fb->format != PIXFORMAT_JPEG ||
        !jpg2rgb565(fb->buf, fb->len, rgb565, JPG_SCALE_8X)) return false;
    profile->width = TRACK_W;
    for (unsigned x = 0; x < TRACK_W; ++x) {
        uint32_t sum = 0;
        for (unsigned y = 0; y < TRACK_H; ++y) {
            const uint8_t *p = &rgb565[(y * TRACK_W + x) * 2];
            uint16_t px = ((uint16_t)p[0] << 8) | p[1];
            unsigned r = (px >> 11) & 0x1f, g = (px >> 5) & 0x3f, b = px & 0x1f;
            sum += (r * 255 / 31 + g * 255 / 63 + b * 255 / 31) / 3;
        }
        profile->value[x] = (uint8_t)(sum / TRACK_H);
    }
    return true;
}

static bool capture_stationary(captured_t *out)
{
    memset(out, 0, sizeof(*out));
    out->fb = esp_camera_fb_get();
    if (!out->fb) { ESP_LOGE(TAG, "JPEG capture failed"); return false; }
    if (!profile_from_jpeg(out->fb, &out->profile)) {
        ESP_LOGE(TAG, "JPEG tracking decode failed");
        esp_camera_fb_return(out->fb); out->fb = NULL; return false;
    }
    return true;
}

static void release_capture(captured_t *capture)
{
    if (capture && capture->fb) esp_camera_fb_return(capture->fb);
    if (capture) capture->fb = NULL;
}

static esp_err_t init_persistent_naming(void)
{
    esp_err_t err = nvs_flash_init();
    if (err != ESP_OK) return err; /* fail closed; do not erase unrelated NVS */
    nvs_handle_t nvs;
    ESP_RETURN_ON_ERROR(nvs_open("pantilt", NVS_READWRITE, &nvs), TAG, "open naming NVS");
    uint32_t previous_boot = 0;
    err = nvs_get_u32(nvs, "boot", &previous_boot);
    if (err != ESP_OK && err != ESP_ERR_NVS_NOT_FOUND) { nvs_close(nvs); return err; }
    s_boot_id = previous_boot == UINT32_MAX ? 1u : previous_boot + 1u;
    s_file_sequence = 0;
    err = nvs_set_u32(nvs, "boot", s_boot_id);
    if (err == ESP_OK) err = nvs_set_u32(nvs, "seq", s_file_sequence);
    if (err == ESP_OK) err = nvs_commit(nvs);
    nvs_close(nvs);
    return err;
}

static bool allocate_photo_name(uint32_t *sequence)
{
    nvs_handle_t nvs;
    if (!sequence || nvs_open("pantilt", NVS_READWRITE, &nvs) != ESP_OK) return false;
    uint32_t next = s_file_sequence == UINT32_MAX ? 1u : s_file_sequence + 1u;
    esp_err_t err = nvs_set_u32(nvs, "seq", next);
    if (err == ESP_OK) err = nvs_commit(nvs); /* reserve before filesystem IO: never reuse after reset */
    nvs_close(nvs);
    if (err != ESP_OK) return false;
    s_file_sequence = next;
    *sequence = next;
    return true;
}

static bool write_exclusive_synced(const char *path, const void *data, size_t length)
{
    int fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0644);
    if (fd < 0) return false; /* never overwrite an already complete capture */
    const uint8_t *p = data;
    size_t sent = 0;
    while (sent < length) {
        ssize_t n = write(fd, p + sent, length - sent);
        if (n <= 0) { close(fd); unlink(path); return false; }
        sent += (size_t)n;
    }
    bool okay = fsync(fd) == 0 && close(fd) == 0;
    if (!okay) unlink(path);
    return okay;
}

static void cleanup_incomplete_captures(void)
{
    DIR *dir = opendir(PHOTO_DIR);
    if (!dir) return;
    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL) {
        const char *name = entry->d_name;
        size_t len = strlen(name);
        /* FATFS dirent names are at most 255 bytes; leave ample headroom so
         * cleanup never truncates a path before unlinking it. */
        char path[512], peer[512];
        snprintf(path, sizeof(path), PHOTO_DIR "/%s", name);
        if (len > 4 && strcmp(name + len - 4, ".tmp") == 0) { unlink(path); continue; }
        if (len > 4 && strcmp(name + len - 4, ".jpg") == 0) {
            snprintf(peer, sizeof(peer), PHOTO_DIR "/%.*s.json", (int)(len - 4), name);
            struct stat st;
            if (stat(peer, &st) != 0) unlink(path);
        } else if (len > 5 && strcmp(name + len - 5, ".json") == 0) {
            snprintf(peer, sizeof(peer), PHOTO_DIR "/%.*s.jpg", (int)(len - 5), name);
            struct stat st;
            if (stat(peer, &st) != 0) unlink(path);
        }
    }
    closedir(dir);
}

static esp_err_t mount_sd(void)
{
    spi_bus_config_t bus = {
        .mosi_io_num = CONFIG_PANTILT_SD_MOSI_GPIO,
        .miso_io_num = CONFIG_PANTILT_SD_MISO_GPIO,
        .sclk_io_num = CONFIG_PANTILT_SD_SCK_GPIO,
        .quadwp_io_num = -1, .quadhd_io_num = -1, .max_transfer_sz = 16 * 1024,
    };
    sdmmc_host_t host = SDSPI_HOST_DEFAULT();
    esp_err_t err = spi_bus_initialize(host.slot, &bus, SDSPI_DEFAULT_DMA);
    if (err != ESP_OK) return err;
    sdspi_device_config_t slot = SDSPI_DEVICE_CONFIG_DEFAULT();
    slot.gpio_cs = CONFIG_PANTILT_SD_CS_GPIO;
    slot.host_id = host.slot;
    esp_vfs_fat_sdmmc_mount_config_t mount = {
        .format_if_mount_failed = false, .max_files = 4, .allocation_unit_size = 16 * 1024,
    };
    err = esp_vfs_fat_sdmmc_mount(SD_MOUNT, &host, &slot, &mount, &s_card);
    if (err != ESP_OK) { spi_bus_free(host.slot); return err; }
    mkdir(PHOTO_DIR, 0775);
    cleanup_incomplete_captures();
    s_sd_mounted = true;
    return ESP_OK;
}

static bool save_photo(const captured_t *capture, float yaw_deg, const char *phase, const char *position_status)
{
    if (!s_sd_mounted || !capture || !capture->fb) return false;
    int64_t stamp_us = esp_timer_get_time();
    char jpg[112], json[112], jpg_tmp[120], json_tmp[120], metadata[512];
    uint32_t sequence;
    if (!allocate_photo_name(&sequence)) return false;
    snprintf(jpg, sizeof(jpg), PHOTO_DIR "/B%08lu_S%08lu.jpg", (unsigned long)s_boot_id, (unsigned long)sequence);
    snprintf(json, sizeof(json), PHOTO_DIR "/B%08lu_S%08lu.json", (unsigned long)s_boot_id, (unsigned long)sequence);
    snprintf(jpg_tmp, sizeof(jpg_tmp), "%s.tmp", jpg);
    snprintf(json_tmp, sizeof(json_tmp), "%s.tmp", json);
    int n = snprintf(metadata, sizeof(metadata),
        "{\n  \"captured_monotonic_us\": %lld,\n  \"logical_yaw_deg\": %.1f,\n"
        "  \"phase\": \"%s\",\n  \"position_source\": \"image_registration_only\",\n"
        "  \"position_status\": \"%s\",\n  \"jpeg_bytes\": %u\n}\n",
        (long long)stamp_us, (double)yaw_deg, phase, position_status, (unsigned)capture->fb->len);
    if (n < 0 || (size_t)n >= sizeof(metadata)) return false;
    bool okay = n >= 0 && (size_t)n < sizeof(metadata) &&
                write_exclusive_synced(jpg_tmp, capture->fb->buf, capture->fb->len) &&
                write_exclusive_synced(json_tmp, metadata, (size_t)n) &&
                rename(jpg_tmp, jpg) == 0 && rename(json_tmp, json) == 0;
    if (!okay) {
        ESP_LOGE(TAG, "atomic photo/metadata write failed");
        unlink(jpg_tmp); unlink(json_tmp); unlink(jpg); unlink(json);
    }
    return okay;
}

static esp_err_t motor_init(void)
{
#if !CONFIG_PANTILT_MOTOR_ENABLE
    ESP_LOGW(TAG, "MOTOR_ENABLE is off: scanner is fail-closed and will not move");
    return ESP_ERR_INVALID_STATE;
#else
    if (CONFIG_PANTILT_MOTOR_IN1_GPIO < 0 || CONFIG_PANTILT_MOTOR_IN2_GPIO < 0 ||
        CONFIG_PANTILT_MOTOR_IN1_GPIO == CONFIG_PANTILT_MOTOR_IN2_GPIO ||
        (CONFIG_PANTILT_MOTOR_POSITIVE_DIRECTION != -1 && CONFIG_PANTILT_MOTOR_POSITIVE_DIRECTION != 1) ||
        (CONFIG_PANTILT_HOME_DIRECTION != -1 && CONFIG_PANTILT_HOME_DIRECTION != 1) ||
        !configured_pins_are_safe() ||
        !configured_budgets_can_recover_home() ||
        !pt_scan_plan_is_within(CONFIG_PANTILT_LOGICAL_MIN_DEG, CONFIG_PANTILT_LOGICAL_MAX_DEG) ||
        !pt_scan_plan_is_safe(CONFIG_PANTILT_TRACK_FOV_DEG, CONFIG_PANTILT_MIN_OVERLAP_DEG,
                              CONFIG_PANTILT_MIN_SCENE_COVERAGE_DEG)) {
        ESP_LOGE(TAG, "unsafe motor/pin/home/FOV/scan-limit configuration");
        return ESP_ERR_INVALID_ARG;
    }
    ledc_timer_config_t timer = {.speed_mode = LEDC_LOW_SPEED_MODE, .duty_resolution = LEDC_TIMER_10_BIT,
        .timer_num = LEDC_TIMER_0, .freq_hz = CONFIG_PANTILT_PWM_HZ, .clk_cfg = LEDC_AUTO_CLK};
    ESP_RETURN_ON_ERROR(ledc_timer_config(&timer), TAG, "PWM timer");
    ledc_channel_config_t a = {.gpio_num = CONFIG_PANTILT_MOTOR_IN1_GPIO, .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel = LEDC_CHANNEL_0, .intr_type = LEDC_INTR_DISABLE, .timer_sel = LEDC_TIMER_0, .duty = 0, .hpoint = 0};
    ledc_channel_config_t b = a; b.gpio_num = CONFIG_PANTILT_MOTOR_IN2_GPIO; b.channel = LEDC_CHANNEL_1;
    ESP_RETURN_ON_ERROR(ledc_channel_config(&a), TAG, "AIN1 PWM");
    ESP_RETURN_ON_ERROR(ledc_channel_config(&b), TAG, "AIN2 PWM");
#if CONFIG_PANTILT_HOME_LIMIT_GPIO >= 0
    gpio_config_t limit = {.pin_bit_mask = 1ULL << CONFIG_PANTILT_HOME_LIMIT_GPIO,
        .mode = GPIO_MODE_INPUT, .pull_up_en = GPIO_PULLUP_ENABLE, .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE};
    ESP_RETURN_ON_ERROR(gpio_config(&limit), TAG, "limit switch");
#elif !CONFIG_PANTILT_ALLOW_BENCH_TIMED_HOME
    ESP_LOGE(TAG, "no home limit and bench timed-stop mode is disabled");
    return ESP_ERR_INVALID_STATE;
#else
    ESP_LOGW(TAG, "BENCH TIMED HOME ENABLED: no limit/current/encoder feedback exists");
#endif
    s_motor_ready = true;
    return ESP_OK;
#endif
}

static void motor_stop(void)
{
    if (!s_motor_ready) return;
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, 0); ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_1, 0); ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_1);
}

static bool cycle_wall_time_ok(int64_t cycle_started_us)
{
    return esp_timer_get_time() - cycle_started_us <= (int64_t)CONFIG_PANTILT_MAX_CYCLE_WALL_MS * 1000LL;
}

static bool motor_pulse(int direction, unsigned milliseconds, pt_budget_t *cycle_budget, pt_budget_t *move_budget)
{
    if (!s_motor_ready || milliseconds == 0 || milliseconds > CONFIG_PANTILT_MAX_PULSE_MS) return false;
    /* Keep enough cycle budget in reserve for a full, bounded production-home
     * attempt if the visual operation fails immediately after this pulse. */
    if (move_budget) {
        unsigned reserve_pulses = (CONFIG_PANTILT_HOME_MAX_MS + CONFIG_PANTILT_MAX_PULSE_MS - 1u) /
                                  CONFIG_PANTILT_MAX_PULSE_MS;
        if (cycle_budget->pulses + 1u + reserve_pulses > CONFIG_PANTILT_MAX_CYCLE_PULSES ||
            cycle_budget->motion_ms + milliseconds + CONFIG_PANTILT_HOME_MAX_MS > CONFIG_PANTILT_MAX_CYCLE_MOTION_MS)
            return false;
    }
    if (!pt_budget_take(cycle_budget, CONFIG_PANTILT_MAX_CYCLE_PULSES,
                        CONFIG_PANTILT_MAX_CYCLE_MOTION_MS, milliseconds)) return false;
    if (move_budget && !pt_budget_take(move_budget, CONFIG_PANTILT_MAX_MOVE_PULSES,
                                       CONFIG_PANTILT_MAX_MOVE_MOTION_MS, milliseconds)) return false;
    unsigned duty = PWM_MAX * CONFIG_PANTILT_PWM_DUTY_PCT / 100;
    bool positive = (direction * CONFIG_PANTILT_MOTOR_POSITIVE_DIRECTION) > 0;
    motor_stop();
    ledc_channel_t driven = positive ? LEDC_CHANNEL_0 : LEDC_CHANNEL_1;
    ledc_set_duty(LEDC_LOW_SPEED_MODE, driven, duty); ledc_update_duty(LEDC_LOW_SPEED_MODE, driven);
    vTaskDelay(pdMS_TO_TICKS(milliseconds));
    motor_stop();
    vTaskDelay(pdMS_TO_TICKS(CONFIG_PANTILT_SETTLE_MS));
    return true;
}

static bool home_to_datum(pt_budget_t *cycle_budget, int64_t cycle_started_us, bool respect_cycle_deadline)
{
    if (!s_motor_ready) return false;
#if CONFIG_PANTILT_HOME_LIMIT_GPIO >= 0
    /* An active switch at entry is not proof of home: it might be stuck or
     * electrically shorted. It must release during a bounded backoff and then
     * be seen active again while approaching from the configured direction. */
    if (active_limit()) {
        unsigned backed_off = 0;
        while (active_limit() && backed_off < CONFIG_PANTILT_HOME_BACKOFF_MS &&
               (!respect_cycle_deadline || cycle_wall_time_ok(cycle_started_us))) {
            unsigned chunk = CONFIG_PANTILT_HOME_BACKOFF_MS - backed_off;
            if (chunk > CONFIG_PANTILT_MAX_PULSE_MS) chunk = CONFIG_PANTILT_MAX_PULSE_MS;
            if (!motor_pulse(-CONFIG_PANTILT_HOME_DIRECTION, chunk, cycle_budget, NULL)) return false;
            backed_off += chunk;
        }
        if (active_limit()) { ESP_LOGE(TAG, "home switch did not release during bounded backoff"); return false; }
    }
    unsigned elapsed = 0;
    while (!active_limit() && elapsed < CONFIG_PANTILT_HOME_MAX_MS &&
           (!respect_cycle_deadline || cycle_wall_time_ok(cycle_started_us))) {
        unsigned chunk = CONFIG_PANTILT_HOME_MAX_MS - elapsed;
        if (chunk > CONFIG_PANTILT_MAX_PULSE_MS) chunk = CONFIG_PANTILT_MAX_PULSE_MS;
        if (!motor_pulse(CONFIG_PANTILT_HOME_DIRECTION, chunk, cycle_budget, NULL)) return false;
        elapsed += chunk;
    }
    if (!active_limit()) { ESP_LOGE(TAG, "home limit not reached within bound"); return false; }
    ESP_LOGI(TAG, "home limit switch reached");
    return true;
#elif CONFIG_PANTILT_ALLOW_BENCH_TIMED_HOME
    ESP_LOGW(TAG, "BENCH ONLY timed home: command is bounded but stop is not sensed");
    unsigned elapsed = 0;
    while (elapsed < CONFIG_PANTILT_HOME_MAX_MS &&
           (!respect_cycle_deadline || cycle_wall_time_ok(cycle_started_us))) {
        unsigned chunk = CONFIG_PANTILT_HOME_MAX_MS - elapsed;
        if (chunk > CONFIG_PANTILT_MAX_PULSE_MS) chunk = CONFIG_PANTILT_MAX_PULSE_MS;
        if (!motor_pulse(CONFIG_PANTILT_HOME_DIRECTION, chunk, cycle_budget, NULL)) return false;
        elapsed += chunk;
    }
    return elapsed == CONFIG_PANTILT_HOME_MAX_MS;
#else
    return false;
#endif
}

static bool move_visually(const pt_profile_t *source, float desired_deg, const pt_profile_t *dock_target,
                          pt_profile_t *arrived, pt_budget_t *cycle_budget, int64_t cycle_started_us)
{
    pt_profile_t previous = *source;
    float measured = 0.0f;
    unsigned no_motion = 0;
    pt_budget_t move_budget = {0};
    int64_t move_started_us = esp_timer_get_time();
    const float min_conf = CONFIG_PANTILT_MIN_REG_CONFIDENCE_PCT / 100.0f;
    for (unsigned attempt = 0; attempt < 28; ++attempt) {
        if (!cycle_wall_time_ok(cycle_started_us) ||
            esp_timer_get_time() - move_started_us > (int64_t)CONFIG_PANTILT_MAX_MOVE_WALL_MS * 1000LL) return false;
        float error = desired_deg - measured;
        if (fabsf(error) <= 2.0f) {
            if (dock_target) {
                pt_registration_t dock = pt_register_profile(dock_target, &previous, CONFIG_PANTILT_TRACK_FOV_DEG, -8, 8);
                ESP_LOGI(TAG, "dock %.2f deg conf %.2f", (double)dock.yaw_delta_deg, (double)dock.confidence);
                if (dock.confidence < min_conf || fabsf(dock.yaw_delta_deg) > 2.0f) return false;
            }
            *arrived = previous;
            return true;
        }
        float step_deg = fminf(fabsf(error), (float)CONFIG_PANTILT_MAX_STEP_DEG);
        unsigned ms = (unsigned)lroundf(1000.0f * step_deg / CONFIG_PANTILT_NOMINAL_SPEED_DEG_S);
        if (ms > CONFIG_PANTILT_MAX_PULSE_MS) ms = CONFIG_PANTILT_MAX_PULSE_MS;
        if (!motor_pulse(error > 0 ? 1 : -1, ms, cycle_budget, &move_budget)) return false;
        captured_t c;
        if (!capture_stationary(&c)) return false;
        float slack = 5.0f;
        pt_registration_t r = pt_register_profile(&previous, &c.profile, CONFIG_PANTILT_TRACK_FOV_DEG,
            error > 0 ? -3.0f : -step_deg - slack, error > 0 ? step_deg + slack : 3.0f);
        release_capture(&c); /* only anchors are persisted, this is a tracking exposure */
        ESP_LOGI(TAG, "step %u delta %.2f conf %.2f score %.2f", attempt, (double)r.yaw_delta_deg,
                 (double)r.confidence, (double)r.score);
        if (r.confidence < min_conf) return false;
        if (fabsf(r.yaw_delta_deg) < 0.75f) { if (++no_motion >= 2) return false; } else no_motion = 0;
        measured += r.yaw_delta_deg;
        previous = c.profile;
    }
    return false;
}

static bool profile_docks(const pt_profile_t *reference, const pt_profile_t *current)
{
    pt_registration_t r = pt_register_profile(reference, current, CONFIG_PANTILT_TRACK_FOV_DEG, -8.0f, 8.0f);
    ESP_LOGI(TAG, "home dock delta %.2f confidence %.2f", (double)r.yaw_delta_deg, (double)r.confidence);
    return r.confidence >= CONFIG_PANTILT_MIN_REG_CONFIDENCE_PCT / 100.0f && fabsf(r.yaw_delta_deg) <= 2.0f;
}

static bool cross_check_outbound_anchor(const anchor_t *source, const anchor_t *current)
{
    float expected = current->yaw_deg - source->yaw_deg;
    float overlap = CONFIG_PANTILT_TRACK_FOV_DEG - fabsf(expected);
    /* Long 80-degree transitions retain only the configured 30-degree
     * overlap, which is insufficient for an independent anchor registration.
     * Apply a fixed-source check where the overlap is broad enough (the final
     * 160->180 leg by default) instead of pretending a weak far match is safe. */
    if (overlap < 45.0f) return true;
    pt_registration_t r = pt_register_profile(&source->profile, &current->profile,
                                               CONFIG_PANTILT_TRACK_FOV_DEG,
                                               expected - 6.0f, expected + 6.0f);
    ESP_LOGI(TAG, "outbound source-anchor check expected %.1f got %.2f conf %.2f",
             (double)expected, (double)r.yaw_delta_deg, (double)r.confidence);
    return r.confidence >= CONFIG_PANTILT_MIN_REG_CONFIDENCE_PCT / 100.0f &&
           fabsf(r.yaw_delta_deg - expected) <= 2.0f;
}

static void abort_cycle(const char *why, pt_budget_t *cycle_budget, int64_t cycle_started_us,
                        const pt_profile_t *known_home)
{
    ESP_LOGE(TAG, "cycle aborted: %s", why);
    motor_stop();
    if (!production_limit_configured()) {
        ESP_LOGW(TAG, "no production limit: refusing timed-home recovery");
        return;
    }
    if (!home_to_datum(cycle_budget, cycle_started_us, false)) {
        ESP_LOGE(TAG, "bounded recovery home failed");
        if (known_home) s_have_verified_home = false;
        motor_stop(); return;
    }
    if (known_home) {
        captured_t verify = {0};
        bool image_ok = capture_stationary(&verify) && profile_docks(known_home, &verify.profile);
        if (!image_ok) {
            ESP_LOGE(TAG, "recovery home image verification failed");
            s_have_verified_home = false;
        }
        release_capture(&verify);
    }
    motor_stop();
}

static bool acquire_cycle_home(captured_t *home, pt_budget_t *cycle_budget, int64_t cycle_started_us,
                               bool *mechanically_homed)
{
    *mechanically_homed = false;
    if (s_have_verified_home && capture_stationary(home)) {
        if (profile_docks(&s_verified_home, &home->profile)) return true;
        release_capture(home);
        ESP_LOGW(TAG, "retained home image no longer matches; using production limit");
    }
    if (!production_limit_configured() || !home_to_datum(cycle_budget, cycle_started_us, true)) return false;
    *mechanically_homed = true;
    if (!capture_stationary(home)) return false;
    /* A seasonal lighting/scene change can invalidate an otherwise sound old
     * image baseline. The re-approached limit is the new physical datum, so
     * discard stale imagery and continue; only full return verification below
     * is allowed to publish this fresh baseline. */
    if (s_have_verified_home && !profile_docks(&s_verified_home, &home->profile)) {
        ESP_LOGW(TAG, "old home image stale after validated limit home; invalidating it");
        s_have_verified_home = false;
    }
    return true;
}

static void run_scan_cycle(void)
{
    pt_budget_t cycle_budget = {0};
    int64_t cycle_started_us = esp_timer_get_time();
    if (!s_motor_ready || !production_limit_configured()) {
        ESP_LOGW(TAG, "cycle refused: an actual production home limit is required; bench timed-home cannot scan unattended");
        return;
    }
    anchor_t anchors[PT_SCAN_ANCHOR_COUNT] = {0};
    captured_t home = {0};
    bool mechanically_homed = false;
    if (!acquire_cycle_home(&home, &cycle_budget, cycle_started_us, &mechanically_homed)) {
        abort_cycle("home acquisition", &cycle_budget, cycle_started_us, s_have_verified_home ? &s_verified_home : NULL);
        return;
    }
    anchors[0].yaw_deg = pt_scan_anchors_deg[0]; anchors[0].profile = home.profile;
    bool saved = cycle_wall_time_ok(cycle_started_us) &&
                 save_photo(&home, anchors[0].yaw_deg, "outbound", "image_home_reference");
    release_capture(&home);
    if (!saved) { abort_cycle("initial photo/JSON save or cycle time", &cycle_budget, cycle_started_us, &anchors[0].profile); return; }

    for (unsigned i = 1; i < PT_SCAN_ANCHOR_COUNT; ++i) {
        pt_profile_t at_target;
        if (!move_visually(&anchors[i - 1].profile, pt_scan_anchors_deg[i] - anchors[i - 1].yaw_deg, NULL,
                           &at_target, &cycle_budget, cycle_started_us)) {
            abort_cycle("outbound visual lock/budget", &cycle_budget, cycle_started_us, &anchors[0].profile); return;
        }
        captured_t shot = {0};
        if (!capture_stationary(&shot)) { abort_cycle("anchor JPEG/profile", &cycle_budget, cycle_started_us, &anchors[0].profile); return; }
        anchors[i].yaw_deg = pt_scan_anchors_deg[i]; anchors[i].profile = shot.profile;
        if (!cross_check_outbound_anchor(&anchors[i - 1], &anchors[i])) {
            release_capture(&shot);
            abort_cycle("outbound fixed-anchor cross-check", &cycle_budget, cycle_started_us, &anchors[0].profile); return;
        }
        saved = cycle_wall_time_ok(cycle_started_us) && save_photo(&shot, anchors[i].yaw_deg, "outbound", "image_registered");
        release_capture(&shot);
        if (!saved) { abort_cycle("anchor photo/JSON save or cycle time", &cycle_budget, cycle_started_us, &anchors[0].profile); return; }
    }

    pt_profile_t current = anchors[PT_SCAN_ANCHOR_COUNT - 1].profile;
    for (int i = PT_SCAN_ANCHOR_COUNT - 2; i >= 0; --i) {
        pt_profile_t next;
        if (!move_visually(&current, anchors[i].yaw_deg - anchors[i + 1].yaw_deg, &anchors[i].profile,
                           &next, &cycle_budget, cycle_started_us)) {
            abort_cycle("return anchor mismatch/budget", &cycle_budget, cycle_started_us, &anchors[0].profile); return;
        }
        current = next;
    }
    captured_t final = {0};
    if (!capture_stationary(&final) || !cycle_wall_time_ok(cycle_started_us) || !profile_docks(&anchors[0].profile, &final.profile)) {
        release_capture(&final);
        abort_cycle("final home image verification", &cycle_budget, cycle_started_us, &anchors[0].profile); return;
    }
    release_capture(&final);
    /* A warm image match permits use of the existing datum but never replaces
     * it: otherwise small accepted registration errors would random-walk the
     * baseline across cycles. Only a limit-home followed by this full visual
     * return verification can refresh the baseline. */
    if (mechanically_homed) {
        s_verified_home = anchors[0].profile;
        s_have_verified_home = true;
    }
    ESP_LOGI(TAG, "scan complete: return and home image verified (%u pulses, %u powered ms)",
             cycle_budget.pulses, cycle_budget.motion_ms);
}

void app_main(void)
{
    if (!configured_pins_are_safe() ||
        !configured_budgets_can_recover_home() ||
        (CONFIG_PANTILT_HOME_DIRECTION != -1 && CONFIG_PANTILT_HOME_DIRECTION != 1) ||
        !pt_scan_plan_is_within(CONFIG_PANTILT_LOGICAL_MIN_DEG, CONFIG_PANTILT_LOGICAL_MAX_DEG) ||
        !pt_scan_plan_is_safe(CONFIG_PANTILT_TRACK_FOV_DEG, CONFIG_PANTILT_MIN_OVERLAP_DEG,
                              CONFIG_PANTILT_MIN_SCENE_COVERAGE_DEG)) {
        ESP_LOGE(TAG, "configuration collision or scan coverage/overlap validation failure");
        return;
    }
    ESP_ERROR_CHECK(camera_init_xiao());
    ESP_ERROR_CHECK(init_persistent_naming());
    ESP_ERROR_CHECK(mount_sd());
    esp_err_t motor = motor_init();
    if (motor != ESP_OK) ESP_LOGW(TAG, "motor unavailable (%s); camera remains non-actuating", esp_err_to_name(motor));
    /* Phase is monotonic boot time. Missed intervals coalesce; no backlog of
     * stale scans is ever executed. */
    const int64_t period_us = 180LL * 1000LL * 1000LL;
    int64_t next_due = esp_timer_get_time();
    for (;;) {
        int64_t now = esp_timer_get_time();
        if (now >= next_due) {
            run_scan_cycle();
            now = esp_timer_get_time();
            do { next_due += period_us; } while (next_due <= now);
        }
        int64_t wait_us = next_due - esp_timer_get_time();
        vTaskDelay(pdMS_TO_TICKS(wait_us > 0 ? (wait_us / 1000) : 10));
    }
}
