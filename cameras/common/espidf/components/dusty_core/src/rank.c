/* rank.c: dc_score, the drain rank (camera_operation.md §7). */
#include "dusty_core.h"
#include <string.h>

float dc_score(const char *why, float det_conf, float diff, float sharp) {
    float tie = sharp > 1.0f ? 1.0f : sharp;
    if (tie < 0.0f) tie = 0.0f;

    float base;
    if (why && (strcmp(why, "boot") == 0 || strcmp(why, "heartbeat") == 0)) {
        base = 1000.0f;
    } else if (det_conf >= 0.0f) {
        base = 100.0f + 100.0f * det_conf;
    } else {
        base = 100.0f * diff;
    }
    return base + 0.999f * tie;
}
