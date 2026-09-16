/* fwver.c: firmware-install decision (camera_standard.md §4, firmware pull). */
#include "dusty_core.h"
#include <string.h>

static const char *safe(const char *s) { return s ? s : ""; }

int dc_fw_should_install(const char *remote, const char *running, const char *bad) {
    const char *r = safe(remote);
    if (r[0] == '\0') return 0;
    if (strcmp(r, safe(running)) == 0) return 0;
    if (strcmp(r, safe(bad)) == 0) return 0;
    return 1;
}
