/* camera: thin wrapper over esp32-camera for xiaocam1. Board facts come
 * from board.h. Contract: PLAN.md §2, §4; sarg
 * frame-buffer-allocation-is-fixed-at-esp-camera (init once at the biggest
 * size ever needed -- UXGA -- and never re-init without deinit first).
 *
 * Copied verbatim from cameras/xiaocam1/software/app/main/camera.{h,c}
 * for the dusty_ble bench spike (docs/phone_app_plan.md §6 P0) -- same
 * hardware, same driver. Keep in sync by hand.
 */
#ifndef XIAOCAM1_CAMERA_H
#define XIAOCAM1_CAMERA_H

#include <stddef.h>
#include <stdint.h>

#include "esp_camera.h"
#include "img_converters.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Zero-inits camera_config_t from board.h: UXGA sensor JPEG q10, 2 fb in
 * PSRAM, CAMERA_GRAB_LATEST, then discards BOARD_CAM_WARMUP_FRAMES frames
 * for AGC/AWB settling. */
esp_err_t xc_cam_init(void);
/* Always call before sleep and before esp_restart(), and never call
 * xc_cam_init() again without this first (sarg:
 * soft-reboot-before-reinitializing-camera-wedged-sccb-i2c). */
void xc_cam_deinit(void);

camera_fb_t *cam_capture(void);
void cam_release(camera_fb_t *fb);

/* Decode a UXGA JPEG fb to RGB565 in PSRAM. scale is JPG_SCALE_8X (->
 * 200x150) or JPG_SCALE_4X (-> 400x300). Returns NULL on failure; caller
 * frees the returned buffer with free(). */
uint16_t *cam_decode(const camera_fb_t *fb, esp_jpeg_image_scale_t scale, int *out_w, int *out_h);

/* fmt2jpg of a 200x150 RGB565 buffer (the debug preview). Returns 1 on
 * success; *out and *out_len are owned by the caller (free()). */
int cam_preview_jpeg(const uint16_t *rgb565_200x150, uint8_t **out, size_t *out_len);

/* dc_sharpness() of an RGB565 buffer's x0,y0,cw,ch region (converts to
 * gray internally; used for the setup page's focus score and the
 * sidecar's score tiebreaker). Returns 0.0f if rgb is NULL. */
float cam_sharpness_rgb565(const uint16_t *rgb, int w, int h, int x0, int y0, int cw, int ch);

#ifdef __cplusplus
}
#endif
#endif
