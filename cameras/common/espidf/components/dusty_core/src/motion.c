/* motion.c: thumbnail generation, luma, mean-normalised diff, motion-centred
 * crop box, and Laplacian sharpness. See dusty_core.h for the contract. */
#include "dusty_core.h"
#include <math.h>

static uint8_t rgb565_to_gray(uint16_t v) {
    int r5 = (v >> 11) & 0x1F;
    int g6 = (v >> 5) & 0x3F;
    int b5 = v & 0x1F;
    int r8 = (r5 << 3) | (r5 >> 2);
    int g8 = (g6 << 2) | (g6 >> 4);
    int b8 = (b5 << 3) | (b5 >> 2);
    int y = (r8 * 77 + g8 * 150 + b8 * 29) >> 8;
    if (y < 0) y = 0;
    if (y > 255) y = 255;
    return (uint8_t)y;
}

/* Box bounds for output cell `o` (0..cells-1) over a source dimension of
 * length `src`, guaranteed non-empty and clamped to [0, src). */
static void box_bounds(int o, int cells, int src, int *lo, int *hi) {
    int a = (o * src) / cells;
    int b = ((o + 1) * src) / cells;
    if (b <= a) b = a + 1;
    if (b > src) b = src;
    *lo = a; *hi = b;
}

void dc_thumb_from_rgb565(const uint16_t *rgb, int w, int h, dc_thumb_t *out) {
    for (int oy = 0; oy < DC_TH_H; oy++) {
        int y0, y1;
        box_bounds(oy, DC_TH_H, h, &y0, &y1);
        for (int ox = 0; ox < DC_TH_W; ox++) {
            int x0, x1;
            box_bounds(ox, DC_TH_W, w, &x0, &x1);
            long sum = 0;
            int cnt = 0;
            for (int y = y0; y < y1; y++) {
                const uint16_t *row = rgb + (size_t)y * (size_t)w;
                for (int x = x0; x < x1; x++) {
                    sum += rgb565_to_gray(row[x]);
                    cnt++;
                }
            }
            out->px[oy * DC_TH_W + ox] = (uint8_t)(cnt ? (sum / cnt) : 0);
        }
    }
}

void dc_thumb_from_gray(const uint8_t *gray, int w, int h, dc_thumb_t *out) {
    for (int oy = 0; oy < DC_TH_H; oy++) {
        int y0, y1;
        box_bounds(oy, DC_TH_H, h, &y0, &y1);
        for (int ox = 0; ox < DC_TH_W; ox++) {
            int x0, x1;
            box_bounds(ox, DC_TH_W, w, &x0, &x1);
            long sum = 0;
            int cnt = 0;
            for (int y = y0; y < y1; y++) {
                const uint8_t *row = gray + (size_t)y * (size_t)w;
                for (int x = x0; x < x1; x++) {
                    sum += row[x];
                    cnt++;
                }
            }
            out->px[oy * DC_TH_W + ox] = (uint8_t)(cnt ? (sum / cnt) : 0);
        }
    }
}

int dc_thumb_lum(const dc_thumb_t *t) {
    long sum = 0;
    for (int i = 0; i < DC_TH_N; i++) sum += t->px[i];
    return (int)(sum / DC_TH_N);
}

void dc_thumb_diff(const dc_thumb_t *cur, const dc_thumb_t *ref, int l_thresh, dc_diff_t *out) {
    long sum_c = 0, sum_r = 0;
    for (int i = 0; i < DC_TH_N; i++) {
        sum_c += cur->px[i];
        sum_r += ref->px[i];
    }
    float mean_c = (float)sum_c / (float)DC_TH_N;
    float mean_r = (float)sum_r / (float)DC_TH_N;

    int n = 0, x0 = DC_TH_W, y0 = DC_TH_H, x1 = -1, y1 = -1;
    for (int yy = 0; yy < DC_TH_H; yy++) {
        for (int xx = 0; xx < DC_TH_W; xx++) {
            int i = yy * DC_TH_W + xx;
            float dc = (float)cur->px[i] - mean_c;
            float dr = (float)ref->px[i] - mean_r;
            float delta = dc - dr;
            if (delta < 0) delta = -delta;
            if (delta >= (float)l_thresh) {
                n++;
                if (xx < x0) x0 = xx;
                if (xx > x1) x1 = xx;
                if (yy < y0) y0 = yy;
                if (yy > y1) y1 = yy;
            }
        }
    }

    out->n = n;
    out->frac = (float)n / (float)DC_TH_N;
    if (n == 0) {
        out->x0 = out->y0 = out->x1 = out->y1 = -1;
    } else {
        out->x0 = x0; out->y0 = y0; out->x1 = x1; out->y1 = y1;
    }
}

int dc_crop_box(const dc_diff_t *d, int frame_w, int frame_h, float pad, float diffuse_frac,
                int min_side, int *cx, int *cy, int *side) {
    if (d->n == 0) return 0;
    int bbox_area = (d->x1 - d->x0 + 1) * (d->y1 - d->y0 + 1);
    if ((float)bbox_area > diffuse_frac * (float)DC_TH_N) return 0;

    float fx0 = ((float)d->x0 + 0.5f) * (float)frame_w / (float)DC_TH_W;
    float fx1 = ((float)d->x1 + 0.5f) * (float)frame_w / (float)DC_TH_W;
    float fy0 = ((float)d->y0 + 0.5f) * (float)frame_h / (float)DC_TH_H;
    float fy1 = ((float)d->y1 + 0.5f) * (float)frame_h / (float)DC_TH_H;

    float bw = fx1 - fx0, bh = fy1 - fy0;
    float padpx = pad * (bw > bh ? bw : bh);
    fx0 -= padpx; fx1 += padpx; fy0 -= padpx; fy1 += padpx;
    bw = fx1 - fx0; bh = fy1 - fy0;

    float cxf = (fx0 + fx1) * 0.5f;
    float cyf = (fy0 + fy1) * 0.5f;
    float side_f = bw > bh ? bw : bh;
    if (side_f < (float)min_side) side_f = (float)min_side;

    float max_side = (float)(frame_w < frame_h ? frame_w : frame_h);
    if (side_f > max_side) side_f = max_side;

    float x = cxf - side_f * 0.5f;
    float y = cyf - side_f * 0.5f;
    if (x + side_f > (float)frame_w) x = (float)frame_w - side_f;
    if (x < 0) x = 0;
    if (y + side_f > (float)frame_h) y = (float)frame_h - side_f;
    if (y < 0) y = 0;

    *cx = (int)(x + 0.5f);
    *cy = (int)(y + 0.5f);
    *side = (int)(side_f + 0.5f);
    return 1;
}

float dc_sharpness(const uint8_t *gray, int w, int h, int x0, int y0, int cw, int ch) {
    if (w <= 0 || h <= 0) return 0.0f;
    if (x0 < 0) { cw += x0; x0 = 0; }
    if (y0 < 0) { ch += y0; y0 = 0; }
    if (x0 + cw > w) cw = w - x0;
    if (y0 + ch > h) ch = h - y0;
    if (cw <= 0 || ch <= 0) return 0.0f;

    double sum = 0.0, sumsq = 0.0;
    long count = 0;
    for (int y = y0; y < y0 + ch; y++) {
        int yu = y > 0 ? y - 1 : 0;
        int yd = y + 1 < h ? y + 1 : h - 1;
        for (int x = x0; x < x0 + cw; x++) {
            int xl = x > 0 ? x - 1 : 0;
            int xr = x + 1 < w ? x + 1 : w - 1;
            int center = gray[(size_t)y * w + x];
            int up = gray[(size_t)yu * w + x];
            int down = gray[(size_t)yd * w + x];
            int left = gray[(size_t)y * w + xl];
            int right = gray[(size_t)y * w + xr];
            double lap = 4.0 * center - up - down - left - right;
            sum += lap;
            sumsq += lap * lap;
            count++;
        }
    }
    if (count == 0) return 0.0f;
    double mean = sum / (double)count;
    double var = sumsq / (double)count - mean * mean;
    if (var < 0) var = 0;
    return (float)sqrt(var);
}
