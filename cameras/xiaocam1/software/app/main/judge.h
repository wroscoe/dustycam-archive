/* judge: wiring the animal gate (gate.h/gate.cc) into the wake cycle.
 * Contract: PLAN.md §9, docs/animal_model.md §5. Fail-open: any failure
 * (gate never loaded, or an Invoke() failure) keeps the frame with
 * has_det = 0, exactly as if no model were configured.
 */
#ifndef XIAOCAM1_JUDGE_H
#define XIAOCAM1_JUDGE_H

#include <stdint.h>

#include "dusty_core.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    int has_det;
    char det_label[12];
    float det_conf;
    int keep;
    int audit;
    int ms; /* inference wall time */
} judge_result_t;

/* gate_init(); remembers success so judge_run() fail-opens for the rest of
 * this boot if it failed. Safe to call once at boot (or once per contact
 * if the caller prefers -- gate.cc's static state is idempotent). */
void judge_init(void);

/* rgb400x300: RGB565, 400x300 (cam_decode with JPG_SCALE_4X of a UXGA
 * frame). d: the thumb diff this wake produced (for the motion-centred
 * crop). cfg: live tuning. Never NULL. */
void judge_run(const uint16_t *rgb400x300, const dc_diff_t *d, const dc_cfg_t *cfg, judge_result_t *out);

/* Logs arena bytes used / capacity and where the arena lives (bench §8
 * gate 6). Call any time after judge_init(). */
void judge_arena_info(void);

#ifdef __cplusplus
}
#endif
#endif
