/* Copied verbatim from cameras/xiaocam1/software/app/main/camera.c for
 * the dusty_ble bench spike (docs/phone_app_plan.md §6 P0). See camera.h. */
#include "camera.h"
#include "board.h"

#include <string.h>
#include <stdlib.h>

#include "esp_log.h"
#include "esp_heap_caps.h"
#include "driver/ledc.h"

#include "dusty_core.h"

static const char *TAG = "camera";
static int s_inited;

esp_err_t xc_cam_init(void)
{
    camera_config_t cfg;
    memset(&cfg, 0, sizeof(cfg));

    cfg.pin_pwdn = BOARD_CAM_PWDN;
    cfg.pin_reset = BOARD_CAM_RESET;
    cfg.pin_xclk = BOARD_CAM_XCLK;
    cfg.pin_sccb_sda = BOARD_CAM_SIOD;
    cfg.pin_sccb_scl = BOARD_CAM_SIOC;
    cfg.pin_d0 = BOARD_CAM_D0;
    cfg.pin_d1 = BOARD_CAM_D1;
    cfg.pin_d2 = BOARD_CAM_D2;
    cfg.pin_d3 = BOARD_CAM_D3;
    cfg.pin_d4 = BOARD_CAM_D4;
    cfg.pin_d5 = BOARD_CAM_D5;
    cfg.pin_d6 = BOARD_CAM_D6;
    cfg.pin_d7 = BOARD_CAM_D7;
    cfg.pin_vsync = BOARD_CAM_VSYNC;
    cfg.pin_href = BOARD_CAM_HREF;
    cfg.pin_pclk = BOARD_CAM_PCLK;
    cfg.xclk_freq_hz = BOARD_CAM_XCLK_HZ;
    cfg.ledc_timer = LEDC_TIMER_0;
    cfg.ledc_channel = LEDC_CHANNEL_0;
    cfg.pixel_format = PIXFORMAT_JPEG;
    cfg.frame_size = BOARD_CAM_FRAMESIZE;
    cfg.jpeg_quality = BOARD_CAM_JPEG_QUALITY;
    cfg.fb_count = BOARD_CAM_FB_COUNT;
    cfg.fb_location = CAMERA_FB_IN_PSRAM;
    cfg.grab_mode = CAMERA_GRAB_LATEST;

    esp_err_t err = esp_camera_init(&cfg);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_camera_init failed: %s", esp_err_to_name(err));
        return err;
    }
    s_inited = 1;

    for (int i = 0; i < BOARD_CAM_WARMUP_FRAMES; i++) {
        camera_fb_t *fb = esp_camera_fb_get();
        if (fb) esp_camera_fb_return(fb);
    }
    ESP_LOGI(TAG, "cam_init ok, %d warm-up frames discarded", BOARD_CAM_WARMUP_FRAMES);
    return ESP_OK;
}

void xc_cam_deinit(void)
{
    if (!s_inited) return;
    esp_camera_deinit();
    s_inited = 0;
}

camera_fb_t *cam_capture(void)
{
    if (!s_inited) return NULL;
    return esp_camera_fb_get();
}

void cam_release(camera_fb_t *fb)
{
    if (fb) esp_camera_fb_return(fb);
}

uint16_t *cam_decode(const camera_fb_t *fb, esp_jpeg_image_scale_t scale, int *out_w, int *out_h)
{
    if (!fb || !fb->buf || !fb->len) return NULL;
    int w, h;
    switch (scale) {
    case JPG_SCALE_2X: w = 800; h = 600; break;
    case JPG_SCALE_4X: w = 400; h = 300; break;
    case JPG_SCALE_8X: w = 200; h = 150; break;
    default:           w = 1600; h = 1200; break;
    }
    size_t n = (size_t)w * (size_t)h * 2;
    uint16_t *rgb = (uint16_t *)heap_caps_malloc(n, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (!rgb) {
        ESP_LOGE(TAG, "cam_decode: alloc %u B failed", (unsigned)n);
        return NULL;
    }
    if (!jpg2rgb565(fb->buf, fb->len, (uint8_t *)rgb, scale)) {
        ESP_LOGE(TAG, "jpg2rgb565 failed (%dx%d)", w, h);
        free(rgb);
        return NULL;
    }
    if (out_w) *out_w = w;
    if (out_h) *out_h = h;
    return rgb;
}

int cam_preview_jpeg(const uint16_t *rgb565_200x150, uint8_t **out, size_t *out_len)
{
    if (!rgb565_200x150 || !out || !out_len) return 0;
    /* jpg2rgb565() writes native (little-endian) RGB565, which is what
     * cam_sharpness_rgb565() reads; fmt2jpg() reads RGB565 as big-endian
     * (the sensor's wire order) and its jpgSetRgb565BE() toggle has C++
     * linkage. Swap into a scratch copy or the preview's colours come out
     * wrong (seen on the phone, 2026-09-15). */
    const size_t n = (size_t)200 * 150;
    uint16_t *be = heap_caps_malloc(n * 2, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (!be) be = malloc(n * 2);
    if (!be) return 0;
    for (size_t i = 0; i < n; i++) {
        uint16_t v = rgb565_200x150[i];
        be[i] = (uint16_t)((v >> 8) | (v << 8));
    }
    int ok = fmt2jpg((uint8_t *)be, n * 2, 200, 150, PIXFORMAT_RGB565, 80, out, out_len) ? 1 : 0;
    free(be);
    return ok;
}

float cam_sharpness_rgb565(const uint16_t *rgb, int w, int h, int x0, int y0, int cw, int ch)
{
    if (!rgb || w <= 0 || h <= 0) return 0.0f;
    uint8_t *gray = (uint8_t *)malloc((size_t)w * (size_t)h);
    if (!gray) return 0.0f;
    for (int i = 0; i < w * h; i++) {
        uint16_t v = rgb[i];
        int r5 = (v >> 11) & 0x1F, g6 = (v >> 5) & 0x3F, b5 = v & 0x1F;
        int r8 = (r5 << 3) | (r5 >> 2), g8 = (g6 << 2) | (g6 >> 4), b8 = (b5 << 3) | (b5 >> 2);
        int y = (r8 * 77 + g8 * 150 + b8 * 29) >> 8;
        gray[i] = (uint8_t)(y < 0 ? 0 : (y > 255 ? 255 : y));
    }
    float s = dc_sharpness(gray, w, h, x0, y0, cw, ch);
    free(gray);
    return s;
}
