/* cfg.c: tier-2 tuning config apply/serialise (camera_operation.md §4.1). */
#include "dusty_core.h"
#include "json_lite.h"
#include "jsonw.h"
#include <string.h>
#include <stdio.h>
#include <math.h>

static int clampi(int v, int lo, int hi) { return v < lo ? lo : (v > hi ? hi : v); }
static float clampf(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }

static int val_as_double(const jl_val_t *v, double *out) {
    if (v->type == JL_NUM) { *out = v->num; return 0; }
    if (v->type == JL_BOOL) { *out = v->bval; return 0; }
    if (v->type == JL_STR) {
        char tmp[32];
        size_t n = v->slen < sizeof(tmp) - 1 ? v->slen : sizeof(tmp) - 1;
        memcpy(tmp, v->s, n);
        tmp[n] = '\0';
        char *end;
        double d = strtod(tmp, &end);
        if (end == tmp) return -1;
        *out = d;
        return 0;
    }
    return -1;
}

static int val_as_bool(const jl_val_t *v, int *out) {
    if (v->type == JL_BOOL) { *out = v->bval; return 0; }
    if (v->type == JL_NUM) { *out = (v->num != 0.0); return 0; }
    if (v->type == JL_STR) {
        if (v->slen == 4 && memcmp(v->s, "true", 4) == 0) { *out = 1; return 0; }
        if (v->slen == 5 && memcmp(v->s, "false", 5) == 0) { *out = 0; return 0; }
        if (v->slen == 1 && (v->s[0] == '0' || v->s[0] == '1')) { *out = v->s[0] - '0'; return 0; }
    }
    return -1;
}

static void set_str_field(char *field, size_t fieldsz, const jl_val_t *v) {
    if (v->type == JL_STR) {
        jl_unescape(v->s, v->slen, field, fieldsz);
    } else if (v->type == JL_NUM) {
        snprintf(field, fieldsz, "%g", v->num);
    } else if (v->type == JL_BOOL) {
        snprintf(field, fieldsz, "%s", v->bval ? "true" : "false");
    }
}

int dc_cfg_apply_json(dc_cfg_t *c, const char *json) {
    if (!json) return -1;
    const char *p = json;
    jl_skip_ws(&p);
    if (*p != '{') return -1;
    p++;

    int applied = 0;
    const char *k;
    size_t klen;
    jl_val_t v = {0};
    int r;

    while ((r = jl_next_key(&p, &k, &klen, &v)) == 1) {
        double d;
        int b;
#define KEY(lit) (klen == sizeof(lit) - 1 && memcmp(k, lit, klen) == 0)
        if (KEY("cfg")) { if (!val_as_double(&v, &d)) { c->cfg = (int)lround(d); applied++; } }
        else if (KEY("profile")) { set_str_field(c->profile, sizeof(c->profile), &v); applied++; }
        else if (KEY("mode")) { set_str_field(c->mode, sizeof(c->mode), &v); applied++; }
        else if (KEY("period_s")) { if (!val_as_double(&v, &d)) { c->period_s = clampi((int)lround(d), 5, 3600); applied++; } }
        else if (KEY("interval_n")) { if (!val_as_double(&v, &d)) { c->interval_n = clampi((int)lround(d), 1, 100000); applied++; } }
        else if (KEY("heartbeat_s")) { if (!val_as_double(&v, &d)) { c->heartbeat_s = clampi((int)lround(d), 60, 86400); applied++; } }
        else if (KEY("diff_min_frac")) { if (!val_as_double(&v, &d)) { c->diff_min_frac = clampf((float)d, 0.0f, 1.0f); applied++; } }
        else if (KEY("diff_l_thresh")) { if (!val_as_double(&v, &d)) { c->diff_l_thresh = clampi((int)lround(d), 1, 255); applied++; } }
        else if (KEY("gate_pct")) { if (!val_as_double(&v, &d)) { c->gate_pct = clampi((int)lround(d), 0, 100); applied++; } }
        else if (KEY("keep_labels")) {
            if (v.type == JL_ARR) {
                const char *ap = v.s;
                const char *aend = v.s + v.slen;
                int n = 0;
                while (ap < aend) {
                    jl_skip_ws(&ap);
                    if (ap >= aend) break;
                    jl_val_t item;
                    if (jl_parse_value(&ap, &item) != 0) break;
                    if (item.type == JL_STR && n < DC_KEEP_LABELS_MAX) {
                        jl_unescape(item.s, item.slen, c->keep_labels[n], sizeof(c->keep_labels[n]));
                        n++;
                    }
                    jl_skip_ws(&ap);
                    if (ap < aend && *ap == ',') ap++;
                }
                c->keep_labels_n = n;
                applied++;
            }
        }
        else if (KEY("keep_all")) { if (!val_as_bool(&v, &b)) { c->keep_all = b; applied++; } }
        else if (KEY("audit_n")) { if (!val_as_double(&v, &d)) { c->audit_n = clampi((int)lround(d), 1, 10000); applied++; } }
        else if (KEY("debug_frames")) { if (!val_as_bool(&v, &b)) { c->debug_frames = b; applied++; } }
        else if (KEY("debug_max")) { if (!val_as_double(&v, &d)) { c->debug_max = clampi((int)lround(d), 0, 100000); applied++; } }
        else if (KEY("upload_cap")) { if (!val_as_double(&v, &d)) { c->upload_cap = clampi((int)lround(d), 0, 100000); applied++; } }
        else if (KEY("lum_night")) { if (!val_as_double(&v, &d)) { c->lum_night = clampi((int)lround(d), 0, 255); applied++; } }
        else if (KEY("lum_day")) { if (!val_as_double(&v, &d)) { c->lum_day = clampi((int)lround(d), 0, 255); applied++; } }
        else if (KEY("night_confirm_n")) { if (!val_as_double(&v, &d)) { c->night_confirm_n = clampi((int)lround(d), 1, 100); applied++; } }
        else if (KEY("night_margin_s")) { if (!val_as_double(&v, &d)) { c->night_margin_s = clampi((int)lround(d), 0, 43200); applied++; } }
        else if (KEY("night_probe_s")) { if (!val_as_double(&v, &d)) { c->night_probe_s = clampi((int)lround(d), 60, 43200); applied++; } }
        else if (KEY("hotspot_join_s")) { if (!val_as_double(&v, &d)) { c->hotspot_join_s = clampi((int)lround(d), 10, 600); applied++; } }
        else if (KEY("contact_idle_s")) { if (!val_as_double(&v, &d)) { c->contact_idle_s = clampi((int)lround(d), 10, 3600); applied++; } }
        else if (KEY("setup_secs")) { if (!val_as_double(&v, &d)) { c->setup_secs = clampi((int)lround(d), 30, 3600); applied++; } }
        else if (KEY("telemetry_s")) { if (!val_as_double(&v, &d)) { c->telemetry_s = clampi((int)lround(d), 10, 3600); applied++; } }
        else if (KEY("led_capture")) { if (!val_as_bool(&v, &b)) { c->led_capture = b; applied++; } }
        else if (KEY("spool_max_frames")) { if (!val_as_double(&v, &d)) { c->spool_max_frames = clampi((int)lround(d), 100, 1000000); applied++; } }
        /* else: unknown key, ignored */
#undef KEY
    }
    if (r == -1) return -1;
    return applied;
}

int dc_cfg_to_json(const dc_cfg_t *c, char *buf, size_t n) {
    size_t off = 0;
    off = out_char(buf, off, n, '{');
    off = out_fmt(buf, off, n, "\"cfg\":%d", c->cfg);
    off = out_str(buf, off, n, ",\"profile\":\"");
    off = out_escaped(buf, off, n, c->profile);
    off = out_char(buf, off, n, '"');
    off = out_str(buf, off, n, ",\"mode\":\"");
    off = out_escaped(buf, off, n, c->mode);
    off = out_char(buf, off, n, '"');
    off = out_fmt(buf, off, n, ",\"period_s\":%d", c->period_s);
    off = out_fmt(buf, off, n, ",\"interval_n\":%d", c->interval_n);
    off = out_fmt(buf, off, n, ",\"heartbeat_s\":%d", c->heartbeat_s);
    off = out_fmt(buf, off, n, ",\"diff_min_frac\":%.4f", (double)c->diff_min_frac);
    off = out_fmt(buf, off, n, ",\"diff_l_thresh\":%d", c->diff_l_thresh);
    off = out_fmt(buf, off, n, ",\"gate_pct\":%d", c->gate_pct);
    off = out_str(buf, off, n, ",\"keep_labels\":[");
    for (int i = 0; i < c->keep_labels_n && i < DC_KEEP_LABELS_MAX; i++) {
        if (i > 0) off = out_char(buf, off, n, ',');
        off = out_char(buf, off, n, '"');
        off = out_escaped(buf, off, n, c->keep_labels[i]);
        off = out_char(buf, off, n, '"');
    }
    off = out_char(buf, off, n, ']');
    off = out_str(buf, off, n, c->keep_all ? ",\"keep_all\":true" : ",\"keep_all\":false");
    off = out_fmt(buf, off, n, ",\"audit_n\":%d", c->audit_n);
    off = out_str(buf, off, n, c->debug_frames ? ",\"debug_frames\":true" : ",\"debug_frames\":false");
    off = out_fmt(buf, off, n, ",\"debug_max\":%d", c->debug_max);
    off = out_fmt(buf, off, n, ",\"upload_cap\":%d", c->upload_cap);
    off = out_fmt(buf, off, n, ",\"lum_night\":%d", c->lum_night);
    off = out_fmt(buf, off, n, ",\"lum_day\":%d", c->lum_day);
    off = out_fmt(buf, off, n, ",\"night_confirm_n\":%d", c->night_confirm_n);
    off = out_fmt(buf, off, n, ",\"night_margin_s\":%d", c->night_margin_s);
    off = out_fmt(buf, off, n, ",\"night_probe_s\":%d", c->night_probe_s);
    off = out_fmt(buf, off, n, ",\"hotspot_join_s\":%d", c->hotspot_join_s);
    off = out_fmt(buf, off, n, ",\"contact_idle_s\":%d", c->contact_idle_s);
    off = out_fmt(buf, off, n, ",\"setup_secs\":%d", c->setup_secs);
    off = out_fmt(buf, off, n, ",\"telemetry_s\":%d", c->telemetry_s);
    off = out_str(buf, off, n, c->led_capture ? ",\"led_capture\":true" : ",\"led_capture\":false");
    off = out_fmt(buf, off, n, ",\"spool_max_frames\":%d", c->spool_max_frames);
    off = out_char(buf, off, n, '}');
    if (off >= n) return -1;
    buf[off] = '\0';
    return (int)off;
}

int dc_cfg_has_label(const dc_cfg_t *c, const char *label) {
    if (!label) return 0;
    for (int i = 0; i < c->keep_labels_n && i < DC_KEEP_LABELS_MAX; i++) {
        if (strcmp(c->keep_labels[i], label) == 0) return 1;
    }
    return 0;
}
