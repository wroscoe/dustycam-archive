#include "judge.h"
#include "gate.h"

#include <string.h>
#include <stdlib.h>

#include "esp_log.h"
#include "esp_timer.h"
#include "esp_random.h"
#include "esp_heap_caps.h"

static const char *TAG = "judge";
static int s_gate_ready;

#define JUDGE_W 400
#define JUDGE_H 300

void judge_init(void)
{
    s_gate_ready = gate_init() ? 1 : 0;
    if (!s_gate_ready) {
        ESP_LOGW(TAG, "gate_init failed: fail-open, every triggered frame keeps");
    }
}

void judge_arena_info(void)
{
    ESP_LOGI(TAG, "gate arena: %u/%u B used (SPIRAM)",
             (unsigned)gate_arena_used(), (unsigned)gate_arena_capacity());
}

/* Nearest-neighbour resize of the cx,cy,side square crop of a JUDGE_W x
 * JUDGE_H RGB565 image to GATE_IMG x GATE_IMG int8 RGB (uint8 ^ 0x80). */
static void build_gate_input(const uint16_t *rgb, int cx, int cy, int side, int8_t *out)
{
    for (int y = 0; y < GATE_IMG; y++) {
        int sy = cy + y * side / GATE_IMG;
        if (sy >= JUDGE_H) sy = JUDGE_H - 1;
        if (sy < 0) sy = 0;
        for (int x = 0; x < GATE_IMG; x++) {
            int sx = cx + x * side / GATE_IMG;
            if (sx >= JUDGE_W) sx = JUDGE_W - 1;
            if (sx < 0) sx = 0;
            uint16_t v = rgb[(size_t)sy * JUDGE_W + sx];
            uint8_t r = ((v >> 11) & 0x1F) * 255 / 31;
            uint8_t g = ((v >> 5) & 0x3F) * 255 / 63;
            uint8_t b = (v & 0x1F) * 255 / 31;
            int8_t *o = out + (y * GATE_IMG + x) * 3;
            o[0] = (int8_t)(r ^ 0x80);
            o[1] = (int8_t)(g ^ 0x80);
            o[2] = (int8_t)(b ^ 0x80);
        }
    }
}

void judge_run(const uint16_t *rgb400x300, const dc_diff_t *d, const dc_cfg_t *cfg, judge_result_t *out)
{
    memset(out, 0, sizeof(*out));
    out->keep = 1; /* fail-open default */

    if (!s_gate_ready || !rgb400x300) {
        return;
    }

    int cx, cy, side;
    if (!dc_crop_box(d, JUDGE_W, JUDGE_H, 0.5f, 0.6f, 96, &cx, &cy, &side)) {
        /* diffuse or no motion mask: centre square of the 400x300 decode */
        side = JUDGE_H;
        cx = (JUDGE_W - side) / 2;
        cy = 0;
    }

    int8_t *gin = (int8_t *)heap_caps_malloc(GATE_IMG * GATE_IMG * 3, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (!gin) {
        ESP_LOGW(TAG, "judge_run: gate input alloc failed, fail-open");
        return;
    }
    build_gate_input(rgb400x300, cx, cy, side, gin);

    int64_t t0 = esp_timer_get_time();
    float score = gate_score(gin);
    int64_t t1 = esp_timer_get_time();
    free(gin);
    out->ms = (int)((t1 - t0) / 1000);

    if (score < 0.0f) {
        ESP_LOGW(TAG, "gate_score failed (%d ms), fail-open", out->ms);
        return; /* has_det = 0, keep = 1 already set */
    }

    out->has_det = 1;
    strlcpy(out->det_label, "animal", sizeof(out->det_label));
    out->det_conf = score;

    int label_ok = dc_cfg_has_label(cfg, out->det_label);
    int pct = (int)(score * 100.0f + 0.5f);
    out->keep = label_ok && (pct >= cfg->gate_pct);

    if (!out->keep) {
        if (cfg->keep_all) {
            out->keep = 1;
        } else if (cfg->audit_n > 0 && (int)(esp_random() % (uint32_t)cfg->audit_n) == 0) {
            out->keep = 1;
            out->audit = 1;
        }
    }

    ESP_LOGI(TAG, "judge: animal=%d%% keep=%d audit=%d ms=%d", pct, out->keep, out->audit, out->ms);
}
