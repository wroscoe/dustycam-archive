/* jsonw.h: tiny malloc-free JSON writing helpers shared by cfg.c, meta.c and
 * night.c. Every helper takes (buf, off, n) and returns the new offset. The
 * offset is always the *true* length that would have been written, even
 * past the end of `buf` (mirroring snprintf's return convention), so a
 * caller can chain calls and, at the end, tell whether it fit by comparing
 * the final offset against n. Not part of the public API.
 */
#ifndef DUSTY_JSONW_H
#define DUSTY_JSONW_H
#include <stddef.h>
#include <stdio.h>
#include <stdarg.h>

static size_t __attribute__((unused)) out_char(char *buf, size_t off, size_t n, char c) {
    if (off + 1 < n) buf[off] = c;
    return off + 1;
}

static size_t __attribute__((unused)) out_str(char *buf, size_t off, size_t n, const char *s) {
    if (!s) return off;
    while (*s) off = out_char(buf, off, n, *s++);
    return off;
}

/* Append s with minimal JSON escaping (quote, backslash, \n, \t; other
 * control characters are dropped). No surrounding quotes are added. */
static size_t __attribute__((unused)) out_escaped(char *buf, size_t off, size_t n, const char *s) {
    if (!s) return off;
    for (; *s; s++) {
        unsigned char c = (unsigned char)*s;
        if (c == '"' || c == '\\') {
            off = out_char(buf, off, n, '\\');
            off = out_char(buf, off, n, (char)c);
        } else if (c == '\n') {
            off = out_char(buf, off, n, '\\');
            off = out_char(buf, off, n, 'n');
        } else if (c == '\t') {
            off = out_char(buf, off, n, '\\');
            off = out_char(buf, off, n, 't');
        } else if (c < 0x20) {
            /* drop other control characters: minimal escaping */
        } else {
            off = out_char(buf, off, n, (char)c);
        }
    }
    return off;
}

static size_t __attribute__((unused)) out_fmt(char *buf, size_t off, size_t n, const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    int r = vsnprintf(off < n ? buf + off : NULL, off < n ? n - off : 0, fmt, ap);
    va_end(ap);
    if (r < 0) r = 0;
    return off + (size_t)r;
}

#endif
