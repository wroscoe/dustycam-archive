/* json_lite.h: a tiny, malloc-free JSON scanner used internally by dusty_core
 * (cfg.c, night.c, spool_name.c). Not part of the public API. Handles just
 * enough JSON to read the small, flat objects/arrays this component deals
 * with: no malloc, no dynamic containers, everything is slices into the
 * caller's buffer. All functions are `static` so each translation unit that
 * includes this header gets its own private copy (no ODR concerns).
 */
#ifndef DUSTY_JSON_LITE_H
#define DUSTY_JSON_LITE_H
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

typedef enum { JL_STR, JL_NUM, JL_BOOL, JL_NULL, JL_ARR, JL_OBJ } jl_type_t;

typedef struct {
    jl_type_t type;
    const char *s;   /* STR: raw (still-escaped) chars between the quotes;
                       * ARR/OBJ: raw chars between the brackets/braces */
    size_t slen;
    double num;       /* NUM */
    int bval;         /* BOOL */
} jl_val_t;

static void __attribute__((unused)) jl_skip_ws(const char **p) {
    while (**p == ' ' || **p == '\t' || **p == '\n' || **p == '\r') (*p)++;
}

/* *p points at '[' or '{'. Advance *p to just past the matching close,
 * respecting (and not being confused by brackets inside) strings. */
static int __attribute__((unused)) jl_skip_balanced(const char **p) {
    char open = **p;
    char close = (open == '[') ? ']' : '}';
    int depth = 0;
    const char *q = *p;
    for (;;) {
        if (*q == '\0') return -1;
        if (*q == '"') {
            q++;
            while (*q != '\0' && *q != '"') {
                if (*q == '\\' && q[1] != '\0') q++;
                q++;
            }
            if (*q != '"') return -1;
            q++;
            continue;
        }
        if (*q == open) { depth++; q++; continue; }
        if (*q == close) { depth--; q++; if (depth == 0) break; continue; }
        q++;
    }
    *p = q;
    return 0;
}

/* Parse one JSON value at **p, advancing *p past it. Returns 0 ok, -1 on a
 * malformed value. */
static int __attribute__((unused)) jl_parse_value(const char **p, jl_val_t *v) {
    jl_skip_ws(p);
    const char *q = *p;
    if (*q == '"') {
        q++;
        const char *start = q;
        while (*q != '\0' && *q != '"') {
            if (*q == '\\' && q[1] != '\0') q++;
            q++;
        }
        if (*q != '"') return -1;
        v->type = JL_STR; v->s = start; v->slen = (size_t)(q - start);
        *p = q + 1;
        return 0;
    }
    if (*q == '[') {
        const char *start = q + 1;
        if (jl_skip_balanced(&q) != 0) return -1;
        v->type = JL_ARR; v->s = start; v->slen = (size_t)((q - 1) - start);
        *p = q;
        return 0;
    }
    if (*q == '{') {
        const char *start = q + 1;
        if (jl_skip_balanced(&q) != 0) return -1;
        v->type = JL_OBJ; v->s = start; v->slen = (size_t)((q - 1) - start);
        *p = q;
        return 0;
    }
    if (*q == 't' && strncmp(q, "true", 4) == 0) {
        v->type = JL_BOOL; v->bval = 1; *p = q + 4; return 0;
    }
    if (*q == 'f' && strncmp(q, "false", 5) == 0) {
        v->type = JL_BOOL; v->bval = 0; *p = q + 5; return 0;
    }
    if (*q == 'n' && strncmp(q, "null", 4) == 0) {
        v->type = JL_NULL; *p = q + 4; return 0;
    }
    if (*q == '-' || (*q >= '0' && *q <= '9')) {
        char *end;
        double d = strtod(q, &end);
        if (end == q) return -1;
        v->type = JL_NUM; v->num = d;
        *p = end;
        return 0;
    }
    return -1;
}

/* Object member iterator. *p must point just past the object's opening '{'
 * (the caller consumes that itself so it can reject non-objects cleanly).
 * Returns 1 with key (kstart,klen) and val filled in -- *p is left just
 * after the value, on top of either ',' or '}' (neither is consumed here);
 * returns 0 once '}' has been consumed (end of object); returns -1 on a
 * malformed object. */
static int __attribute__((unused)) jl_next_key(const char **p, const char **kstart, size_t *klen, jl_val_t *val) {
    jl_skip_ws(p);
    if (**p == '}') { (*p)++; return 0; }
    if (**p == ',') { (*p)++; jl_skip_ws(p); }
    if (**p != '"') return -1;
    (*p)++;
    const char *start = *p;
    while (**p != '\0' && **p != '"') {
        if (**p == '\\' && (*p)[1] != '\0') (*p)++;
        (*p)++;
    }
    if (**p != '"') return -1;
    *kstart = start; *klen = (size_t)(*p - start);
    (*p)++;
    jl_skip_ws(p);
    if (**p != ':') return -1;
    (*p)++;
    if (jl_parse_value(p, val) != 0) return -1;
    jl_skip_ws(p);
    if (**p == ',' || **p == '}') return 1;
    return -1;
}

/* Unescape a raw JSON string slice (as returned in jl_val_t.s/.slen) into
 * `out`, NUL-terminated, truncated to fit outn. Handles the escapes JSON
 * defines for plain text (\" \\ \/ \n \t \r); anything else after a
 * backslash is copied verbatim. Returns the number of bytes written
 * (excluding the NUL). */
static size_t __attribute__((unused)) jl_unescape(const char *s, size_t slen, char *out, size_t outn) {
    size_t oi = 0;
    if (outn == 0) return 0;
    for (size_t i = 0; i < slen && oi + 1 < outn; i++) {
        char c = s[i];
        if (c == '\\' && i + 1 < slen) {
            char e = s[++i];
            switch (e) {
                case 'n': c = '\n'; break;
                case 't': c = '\t'; break;
                case 'r': c = '\r'; break;
                case '"': c = '"'; break;
                case '\\': c = '\\'; break;
                case '/': c = '/'; break;
                default: c = e; break;
            }
        }
        out[oi++] = c;
    }
    out[oi] = '\0';
    return oi;
}

#endif
