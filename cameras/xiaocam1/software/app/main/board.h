/* Board facts for the Seeed XIAO ESP32S3 Sense (xiaocam1). Tier 3:
 * changes only with a hardware revision. Source: PLAN.md §2, the proven
 * Arduino bench sketch (software/bench/sd_camera_test/sd_camera_test.ino)
 * and the archived pantilt firmware's sdspi mount
 * (archive/pantilt/firmware/main/main.c).
 */
#ifndef XIAOCAM1_BOARD_H
#define XIAOCAM1_BOARD_H

/* ---- camera: official CAMERA_MODEL_XIAO_ESP32S3 pin map, OV3660 ---- */
#define BOARD_CAM_PWDN     -1
#define BOARD_CAM_RESET    -1
#define BOARD_CAM_XCLK     10
#define BOARD_CAM_SIOD     40
#define BOARD_CAM_SIOC     39
#define BOARD_CAM_D0       15
#define BOARD_CAM_D1       17
#define BOARD_CAM_D2       18
#define BOARD_CAM_D3       16
#define BOARD_CAM_D4       14
#define BOARD_CAM_D5       12
#define BOARD_CAM_D6       11
#define BOARD_CAM_D7       48
#define BOARD_CAM_VSYNC    38
#define BOARD_CAM_HREF     47
#define BOARD_CAM_PCLK     13

/* capture: sensor-JPEG UXGA, 2 fb in PSRAM, XCLK 20 MHz, warm-up frames */
#define BOARD_CAM_XCLK_HZ      20000000
#define BOARD_CAM_FRAMESIZE    FRAMESIZE_UXGA   /* 1600x1200 */
#define BOARD_CAM_JPEG_QUALITY 10
#define BOARD_CAM_FB_COUNT     2
#define BOARD_CAM_WARMUP_FRAMES 4

/* ---- SD: SPI mode, CS shared with the LED ---- */
#define BOARD_SD_CS_GPIO    21
#define BOARD_SD_SCK_GPIO   7
#define BOARD_SD_MISO_GPIO  8
#define BOARD_SD_MOSI_GPIO  9
#define BOARD_SD_MOUNT      "/sd"

/* ---- LED: GPIO21, active-low, shared with SD CS (camera_operation.md §7 /
 * PLAN.md §7 — the LED task must only toggle it through the SD bus mutex) */
#define BOARD_LED_GPIO       21
#define BOARD_LED_ACTIVE_LOW 1

/* ---- button: BOOT, active-low, strapping pin ---- */
#define BOARD_BUTTON_GPIO 0

#endif
