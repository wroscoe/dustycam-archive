/* meta.c: dc_meta_build, the per-frame sidecar JSON (camera_standard.md §4). */
#include "dusty_core.h"
#include "jsonw.h"

int dc_meta_build(char *buf, size_t n, const dc_meta_t *m) {
    size_t off = 0;
    off = out_char(buf, off, n, '{');
    off = out_fmt(buf, off, n, "\"ts\":%lld", (long long)m->ts);
    off = out_fmt(buf, off, n, ",\"seq\":%u", (unsigned)m->seq);
    off = out_fmt(buf, off, n, ",\"w\":%d", m->w);
    off = out_fmt(buf, off, n, ",\"h\":%d", m->h);
    off = out_str(buf, off, n, ",\"v\":\"");
    off = out_escaped(buf, off, n, m->v);
    off = out_char(buf, off, n, '"');
    off = out_fmt(buf, off, n, ",\"cfg\":%d", m->cfg);
    off = out_str(buf, off, n, ",\"ip\":\"");
    off = out_escaped(buf, off, n, m->ip);
    off = out_char(buf, off, n, '"');
    off = out_str(buf, off, n, ",\"mode\":\"");
    off = out_escaped(buf, off, n, m->mode);
    off = out_char(buf, off, n, '"');
    off = out_str(buf, off, n, ",\"why\":\"");
    off = out_escaped(buf, off, n, m->why);
    off = out_char(buf, off, n, '"');
    off = out_fmt(buf, off, n, ",\"diff\":%.3f", (double)m->diff);
    off = out_fmt(buf, off, n, ",\"gate\":%.3f", (double)m->gate);
    off = out_str(buf, off, n, m->heartbeat ? ",\"heartbeat\":true" : ",\"heartbeat\":false");
    off = out_str(buf, off, n, m->buffered ? ",\"buffered\":true" : ",\"buffered\":false");
    off = out_fmt(buf, off, n, ",\"lum\":%d", m->lum);
    off = out_str(buf, off, n, ",\"clock\":\"");
    off = out_escaped(buf, off, n, m->clock);
    off = out_char(buf, off, n, '"');
    off = out_fmt(buf, off, n, ",\"score\":%.2f", (double)m->score);

    if (m->has_det) {
        off = out_str(buf, off, n, ",\"det\":[{\"label\":\"");
        off = out_escaped(buf, off, n, m->det_label);
        off = out_str(buf, off, n, "\",\"conf\":");
        off = out_fmt(buf, off, n, "%.2f", (double)m->det_conf);
        off = out_str(buf, off, n, "}]");
    }
    if (m->audit) {
        off = out_str(buf, off, n, ",\"audit\":true");
    }
    if (m->night_s >= 0) {
        off = out_fmt(buf, off, n, ",\"night_s\":%lld", (long long)m->night_s);
    }

    off = out_char(buf, off, n, '}');
    if (off >= n) return -1;
    buf[off] = '\0';
    return (int)off;
}
