/*
 * XIAO ESP32S3 Sense: capture a JPEG from the OV2640 and save it to the
 * expansion board's microSD. Bench proof for the camera + SD path only.
 *
 * Sense expansion board:
 *   camera  - official CAMERA_MODEL_XIAO_ESP32S3 map (XCLK 10, SCCB 40/39,
 *             D0..D7 15,17,18,16,14,12,11,48, VSYNC 38, HREF 47, PCLK 13)
 *   microSD - SPI, CS GPIO21 (shared with the user LED), SCK 7, MISO 8, MOSI 9
 *
 * The DRV8833 bench wiring (GPIO1 AIN1, GPIO2 AIN2, GPIO3 SLP) is still on
 * the head, so those three pins are driven LOW before anything else and never
 * touched again.
 *
 * Serial 115200, single-character commands:
 *   c  capture one JPEG and save /xiao_sd_test/NNNNN.jpg (+ prints size)
 *   l  list the directory
 *   i  card + camera info
 *   g  dump the last saved file as base64 between BEGIN/END markers
 *   a  toggle auto capture every 10 s
 *   h  help
 * One capture is taken automatically at boot so it works without a host.
 */

#include "esp_camera.h"
#include "FS.h"
#include "SD.h"
#include "SPI.h"
#include <Preferences.h>

#define PWDN_GPIO_NUM  -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM  10
#define SIOD_GPIO_NUM  40
#define SIOC_GPIO_NUM  39
#define Y9_GPIO_NUM    48
#define Y8_GPIO_NUM    11
#define Y7_GPIO_NUM    12
#define Y6_GPIO_NUM    14
#define Y5_GPIO_NUM    16
#define Y4_GPIO_NUM    18
#define Y3_GPIO_NUM    17
#define Y2_GPIO_NUM    15
#define VSYNC_GPIO_NUM 38
#define HREF_GPIO_NUM  47
#define PCLK_GPIO_NUM  13

static constexpr uint8_t SD_CS_PIN = 21;
static constexpr uint8_t AIN1_PIN = 1, AIN2_PIN = 2, SLP_PIN = 3;
static const char *DIR_PATH = "/xiao_sd_test";

static Preferences prefs;
static bool cam_ok = false, sd_ok = false, auto_capture = false;
static String last_path;
static uint32_t last_auto_ms = 0;

static void motor_pins_safe() {
  pinMode(AIN1_PIN, OUTPUT); digitalWrite(AIN1_PIN, LOW);
  pinMode(AIN2_PIN, OUTPUT); digitalWrite(AIN2_PIN, LOW);
  pinMode(SLP_PIN, OUTPUT);  digitalWrite(SLP_PIN, LOW);
}

static bool camera_init() {
  camera_config_t cfg = {};  // zero-init: unset fields must not be garbage
  cfg.ledc_channel = LEDC_CHANNEL_0;
  cfg.ledc_timer = LEDC_TIMER_0;
  cfg.pin_d0 = Y2_GPIO_NUM; cfg.pin_d1 = Y3_GPIO_NUM; cfg.pin_d2 = Y4_GPIO_NUM; cfg.pin_d3 = Y5_GPIO_NUM;
  cfg.pin_d4 = Y6_GPIO_NUM; cfg.pin_d5 = Y7_GPIO_NUM; cfg.pin_d6 = Y8_GPIO_NUM; cfg.pin_d7 = Y9_GPIO_NUM;
  cfg.pin_xclk = XCLK_GPIO_NUM; cfg.pin_pclk = PCLK_GPIO_NUM;
  cfg.pin_vsync = VSYNC_GPIO_NUM; cfg.pin_href = HREF_GPIO_NUM;
  cfg.pin_sccb_sda = SIOD_GPIO_NUM; cfg.pin_sccb_scl = SIOC_GPIO_NUM;
  cfg.pin_pwdn = PWDN_GPIO_NUM; cfg.pin_reset = RESET_GPIO_NUM;
  cfg.xclk_freq_hz = 20000000;
  cfg.pixel_format = PIXFORMAT_JPEG;
  cfg.frame_size = FRAMESIZE_UXGA;      // 1600x1200; largest we will ever ask for
  cfg.jpeg_quality = 10;
  cfg.fb_count = 2;
  cfg.fb_location = CAMERA_FB_IN_PSRAM;
  cfg.grab_mode = CAMERA_GRAB_LATEST;
  if (!psramFound()) {
    Serial.println("WARN: no PSRAM, falling back to SVGA in DRAM");
    cfg.frame_size = FRAMESIZE_SVGA;
    cfg.fb_count = 1;
    cfg.fb_location = CAMERA_FB_IN_DRAM;
  }
  esp_err_t err = esp_camera_init(&cfg);
  if (err != ESP_OK) {
    Serial.printf("camera init failed: 0x%x\n", err);
    return false;
  }
  sensor_t *s = esp_camera_sensor_get();
  if (s) {
    Serial.printf("camera sensor PID 0x%04x\n", s->id.PID);
    s->set_vflip(s, 0);
    s->set_hmirror(s, 0);
  }
  // warm-up: let AEC/AWB settle and flush stale buffers
  for (int i = 0; i < 4; i++) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (fb) esp_camera_fb_return(fb);
    delay(60);
  }
  return true;
}

static bool sd_init() {
  if (!SD.begin(SD_CS_PIN)) {
    Serial.println("SD mount failed (no card, bad contact, or not FAT32/exFAT)");
    return false;
  }
  uint8_t t = SD.cardType();
  if (t == CARD_NONE) {
    Serial.println("SD: no card attached");
    return false;
  }
  Serial.printf("SD mounted: type %s, %llu MB, used %llu MB\n",
                t == CARD_MMC ? "MMC" : t == CARD_SD ? "SDSC" : t == CARD_SDHC ? "SDHC" : "?",
                SD.cardSize() / (1024ULL * 1024ULL), SD.usedBytes() / (1024ULL * 1024ULL));
  if (!SD.exists(DIR_PATH) && !SD.mkdir(DIR_PATH)) {
    Serial.printf("mkdir %s failed\n", DIR_PATH);
    return false;
  }
  return true;
}

static bool capture_and_save() {
  if (!cam_ok || !sd_ok) {
    Serial.println("capture refused: camera or SD not ready");
    return false;
  }
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("esp_camera_fb_get failed");
    return false;
  }
  uint32_t seq = prefs.getUInt("seq", 0) + 1;
  prefs.putUInt("seq", seq);  // reserve before writing so a crash never reuses a name
  char path[48], tmp[52];
  snprintf(path, sizeof path, "%s/%05lu.jpg", DIR_PATH, (unsigned long)seq);
  snprintf(tmp, sizeof tmp, "%s.tmp", path);
  uint32_t t0 = millis();
  File f = SD.open(tmp, FILE_WRITE);
  bool ok = false;
  if (!f) {
    Serial.printf("open %s failed\n", tmp);
  } else {
    size_t n = f.write(fb->buf, fb->len);
    f.flush();
    f.close();
    ok = (n == fb->len);
    if (!ok) Serial.printf("short write %u of %u\n", (unsigned)n, (unsigned)fb->len);
  }
  uint32_t dt = millis() - t0;
  if (ok) {
    if (SD.exists(path)) SD.remove(path);
    ok = SD.rename(tmp, path);
    if (!ok) Serial.println("rename failed");
  }
  if (!ok) SD.remove(tmp);
  Serial.printf("%s %s: %ux%u, %u bytes, %lu ms write\n", ok ? "saved" : "FAILED", path,
                fb->width, fb->height, (unsigned)fb->len, (unsigned long)dt);
  esp_camera_fb_return(fb);
  if (ok) last_path = path;
  return ok;
}

static void list_dir() {
  if (!sd_ok) { Serial.println("SD not mounted"); return; }
  File d = SD.open(DIR_PATH);
  if (!d || !d.isDirectory()) { Serial.println("dir open failed"); return; }
  int count = 0;
  for (File e = d.openNextFile(); e; e = d.openNextFile()) {
    Serial.printf("  %s  %u bytes\n", e.name(), (unsigned)e.size());
    count++;
  }
  Serial.printf("%d files in %s\n", count, DIR_PATH);
}

static void dump_last_base64() {
  if (last_path.isEmpty()) { Serial.println("nothing saved yet"); return; }
  File f = SD.open(last_path, FILE_READ);
  if (!f) { Serial.println("open failed"); return; }
  static const char tbl[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  Serial.printf("BEGIN %s %u\n", last_path.c_str(), (unsigned)f.size());
  uint8_t in[3]; int col = 0;
  while (f.available()) {
    int n = f.read(in, 3);
    uint32_t v = ((uint32_t)in[0] << 16) | (n > 1 ? (uint32_t)in[1] << 8 : 0) | (n > 2 ? in[2] : 0);
    char out[5] = { tbl[(v >> 18) & 63], tbl[(v >> 12) & 63],
                    n > 1 ? tbl[(v >> 6) & 63] : '=', n > 2 ? tbl[v & 63] : '=', 0 };
    Serial.print(out);
    if (++col == 19) { Serial.print('\n'); col = 0; }
  }
  f.close();
  Serial.println("\nEND");
}

static void info() {
  Serial.printf("psram: %s (%u KB free), heap %u KB free\n", psramFound() ? "yes" : "no",
                (unsigned)(ESP.getFreePsram() / 1024), (unsigned)(ESP.getFreeHeap() / 1024));
  Serial.printf("camera: %s, sd: %s, auto: %s, seq: %lu, last: %s\n",
                cam_ok ? "ok" : "FAILED", sd_ok ? "mounted" : "FAILED", auto_capture ? "on" : "off",
                (unsigned long)prefs.getUInt("seq", 0), last_path.c_str());
  if (sd_ok) Serial.printf("sd: %llu MB total, %llu MB used\n",
                           SD.totalBytes() / (1024ULL * 1024ULL), SD.usedBytes() / (1024ULL * 1024ULL));
}

static void help() {
  Serial.println("XIAO ESP32S3 Sense camera -> microSD test");
  Serial.println("c capture+save | l list | i info | g base64 dump of last file | a toggle auto 10 s | h help");
}

void setup() {
  motor_pins_safe();
  Serial.begin(115200);
  delay(1500);
  Serial.println();
  help();
  prefs.begin("sdcam", false);
  cam_ok = camera_init();
  sd_ok = sd_init();
  info();
  capture_and_save();
}

void loop() {
  if (Serial.available()) {
    int c = Serial.read();
    switch (c) {
      case 'c': capture_and_save(); break;
      case 'l': list_dir(); break;
      case 'i': info(); break;
      case 'g': dump_last_base64(); break;
      case 'a': auto_capture = !auto_capture; Serial.printf("auto capture %s\n", auto_capture ? "on" : "off"); break;
      case 'h': case '?': help(); break;
      default: break;
    }
  }
  if (auto_capture && millis() - last_auto_ms >= 10000) {
    last_auto_ms = millis();
    capture_and_save();
  }
}
