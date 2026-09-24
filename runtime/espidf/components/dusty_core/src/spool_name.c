/* spool_name.c: SD spool path naming/parsing and sidecar score extraction
 * (camera_operation.md §7). */
#include "dusty_core.h"
#include "json_lite.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int dc_spool_path(char *buf, size_t n, const char *root, const char *tier, uint32_t boot, uint32_t seq, const char *ext) {
    int r = snprintf(buf, n, "%s/%s/%u/%06u.%s", root, tier, (unsigned)boot, (unsigned)seq, ext);
    if (r < 0 || (size_t)r >= n) return -1;
    return r;
}

int dc_spool_parse(const char *rel, uint32_t *boot, uint32_t *seq) {
    if (!rel || *rel == '\0') return 0;
    char *end;
    unsigned long b = strtoul(rel, &end, 10);
    if (end == rel || *end != '/') return 0;
    const char *seqstart = end + 1;
    char *end2;
    unsigned long s = strtoul(seqstart, &end2, 10);
    if (end2 == seqstart) return 0;
    if (*end2 != '.' && *end2 != '\0') return 0;
    if (boot) *boot = (uint32_t)b;
    if (seq) *seq = (uint32_t)s;
    return 1;
}

int dc_sidecar_score(const char *json, float *score, char *why_out, size_t why_n) {
    if (!json) return 0;
    if (why_out && why_n > 0) why_out[0] = '\0';

    const char *p = json;
    jl_skip_ws(&p);
    if (*p != '{') return 0;
    p++;

    int found = 0;
    const char *k;
    size_t klen;
    jl_val_t v = {0};
    int r;
    while ((r = jl_next_key(&p, &k, &klen, &v)) == 1) {
        if (klen == 5 && memcmp(k, "score", 5) == 0 && v.type == JL_NUM) {
            if (score) *score = (float)v.num;
            found = 1;
        } else if (klen == 3 && memcmp(k, "why", 3) == 0 && v.type == JL_STR) {
            if (why_out && why_n > 0) jl_unescape(v.s, v.slen, why_out, why_n);
        }
    }
    (void)r;
    return found;
}
