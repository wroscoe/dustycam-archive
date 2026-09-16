/* night.c: night policy (camera_operation.md §6), pure function of state,
 * lum, now and cfg -- see dusty_core.h for exact field semantics. */
#include "dusty_core.h"
#include "json_lite.h"
#include "jsonw.h"

uint32_t dc_night_predict(const dc_night_t *st) {
    if (st->hist_n <= 0) return 0;
    int k = st->hist_n < 3 ? st->hist_n : 3;
    uint32_t vals[3];
    for (int i = 0; i < k; i++) {
        int idx = (st->hist_head - 1 - i + 2 * DC_NIGHT_HIST) % DC_NIGHT_HIST;
        vals[i] = st->hist[idx];
    }
    for (int i = 0; i < k; i++)
        for (int j = i + 1; j < k; j++)
            if (vals[j] < vals[i]) { uint32_t t = vals[i]; vals[i] = vals[j]; vals[j] = t; }
    if (k % 2 == 1) return vals[k / 2];
    return (vals[k / 2 - 1] + vals[k / 2]) / 2;
}

static void push_hist(dc_night_t *st, uint32_t len) {
    st->hist[st->hist_head] = len;
    st->hist_head = (st->hist_head + 1) % DC_NIGHT_HIST;
    if (st->hist_n < DC_NIGHT_HIST) st->hist_n++;
}

void dc_night_step(dc_night_t *st, int lum, uint32_t now_s, const dc_night_cfg_t *cfg, dc_night_out_t *out) {
    out->entered = 0;
    out->left = 0;
    out->night_len_s = 0;

    if (!st->in_night) {
        if (lum < cfg->lum_night) st->dark_n++;
        else st->dark_n = 0;

        if (st->dark_n >= cfg->night_confirm_n) {
            /* enter night */
            st->in_night = 1;
            st->night_start_s = now_s;
            st->dark_n = 0;
            st->slept_toward_dawn = 0;
            out->entered = 1;

            uint32_t sleep_s;
            if (st->hist_n > 0) {
                uint32_t predicted = dc_night_predict(st);
                uint32_t long_sleep = predicted > cfg->night_margin_s ? predicted - cfg->night_margin_s : 0;
                if (long_sleep > cfg->night_probe_s) {
                    sleep_s = long_sleep;
                    st->slept_toward_dawn = 1;
                } else {
                    sleep_s = cfg->night_probe_s;
                }
            } else {
                sleep_s = cfg->night_probe_s;
            }
            out->sleep_s = sleep_s;
        } else {
            out->sleep_s = cfg->period_s;
        }
        out->in_night = st->in_night;
        return;
    }

    /* already in night: this wake is a probe */
    if (lum > cfg->lum_day) {
        out->left = 1;
        out->night_len_s = now_s - st->night_start_s;
        push_hist(st, out->night_len_s);
        st->in_night = 0;
        st->dark_n = 0;
        st->slept_toward_dawn = 0;
        out->sleep_s = cfg->period_s;
    } else {
        out->sleep_s = cfg->night_probe_s;
    }
    out->in_night = st->in_night;
}

int dc_night_hist_to_json(const dc_night_t *st, char *buf, size_t n) {
    size_t off = 0;
    off = out_char(buf, off, n, '[');
    int oldest = (int)(((long)st->hist_head - (long)st->hist_n + DC_NIGHT_HIST) % DC_NIGHT_HIST);
    for (int i = 0; i < st->hist_n; i++) {
        int idx = (oldest + i) % DC_NIGHT_HIST;
        if (i > 0) off = out_char(buf, off, n, ',');
        off = out_fmt(buf, off, n, "%u", (unsigned)st->hist[idx]);
    }
    off = out_char(buf, off, n, ']');
    if (off >= n) return -1;
    buf[off] = '\0';
    return (int)off;
}

int dc_night_hist_from_json(dc_night_t *st, const char *json) {
    if (!json) return -1;
    const char *p = json;
    jl_skip_ws(&p);
    if (*p != '[') return -1;
    p++;
    jl_skip_ws(&p);

    uint32_t vals[DC_NIGHT_HIST];
    int count = 0;

    if (*p == ']') {
        p++;
    } else {
        for (;;) {
            jl_val_t v = {0};
            if (jl_parse_value(&p, &v) != 0 || v.type != JL_NUM) return -1;
            if (count < DC_NIGHT_HIST) vals[count] = (uint32_t)(v.num + 0.5);
            else { /* keep the newest DC_NIGHT_HIST: shift the window */
                for (int i = 1; i < DC_NIGHT_HIST; i++) vals[i - 1] = vals[i];
                vals[DC_NIGHT_HIST - 1] = (uint32_t)(v.num + 0.5);
            }
            count++;
            jl_skip_ws(&p);
            if (*p == ',') { p++; continue; }
            if (*p == ']') { p++; break; }
            return -1;
        }
    }

    int keep = count < DC_NIGHT_HIST ? count : DC_NIGHT_HIST;
    for (int i = 0; i < DC_NIGHT_HIST; i++) st->hist[i] = 0;
    for (int i = 0; i < keep; i++) st->hist[i] = vals[i];
    st->hist_n = keep;
    st->hist_head = keep % DC_NIGHT_HIST;
    return keep;
}
