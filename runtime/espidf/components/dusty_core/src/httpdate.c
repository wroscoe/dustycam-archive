/* httpdate.c: RFC 1123 HTTP Date parsing, self-contained (no libc timegm,
 * whose behaviour/availability isn't guaranteed under ESP-IDF's newlib). */
#include "dusty_core.h"
#include <stdio.h>
#include <string.h>

/* Howard Hinnant's days-from-civil-date algorithm: days since 1970-01-01
 * for the given proleptic-Gregorian civil date. m is 1..12. */
static int64_t days_from_civil(long y, int m, int d) {
    y -= (m <= 2);
    long era = (y >= 0 ? y : y - 399) / 400;
    unsigned yoe = (unsigned)(y - era * 400);                 /* 0..399 */
    unsigned doy = (unsigned)((153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1); /* 0..365 */
    unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;      /* 0..146096 */
    return (int64_t)era * 146097 + (int64_t)doe - 719468;
}

static int month_num(const char *mon) {
    static const char *names[12] = {
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    };
    for (int i = 0; i < 12; i++) {
        if (strncmp(mon, names[i], 3) == 0) return i + 1;
    }
    return -1;
}

int64_t dc_parse_http_date(const char *s) {
    if (!s) return -1;
    char wd[8], mon[8], tz[8];
    int day, year, hh, mm, ss;

    int r = sscanf(s, "%7[^,], %d %7s %d %d:%d:%d %7s", wd, &day, mon, &year, &hh, &mm, &ss, tz);
    if (r != 8) return -1;
    if (strcmp(tz, "GMT") != 0) return -1;

    int mo = month_num(mon);
    if (mo < 0) return -1;
    if (day < 1 || day > 31) return -1;
    if (hh < 0 || hh > 23 || mm < 0 || mm > 59 || ss < 0 || ss > 60) return -1;

    int64_t days = days_from_civil(year, mo, day);
    return days * 86400 + hh * 3600 + mm * 60 + ss;
}
