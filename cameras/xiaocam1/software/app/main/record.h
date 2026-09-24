/* record: the one place a frame becomes a spool entry (camera_standard.md
 * §4 Record, camera_operation.md §7). Shared by main.c's live wake cycle
 * and contact.c's `shoot` control hook ("record via the same record path
 * as live" per PLAN.md §5's control-hook table) so the meta layout can't
 * drift between the two callers. Implemented in main.c.
 */
#ifndef XIAOCAM1_RECORD_H
#define XIAOCAM1_RECORD_H

#include <stdint.h>
#include <stddef.h>

#include "esp_camera.h"
#include "dusty_core.h"
#include "judge.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    camera_fb_t *fb;           /* the full-res JPEG to spool */
    const dc_thumb_t *thumb;   /* this wake's 40x30 thumb, or NULL (shoot) */
    int lum;
    float diff;                /* dc_diff_t.frac, 0 when not applicable */
    const judge_result_t *jr;  /* NULL: gate did not run for this frame */
    const char *why;
    const char *mode;          /* "live" | "contact" */
    int64_t night_s;           /* < 0 to omit */
    float sharpness;           /* raw dc_sharpness() (0 if not computed); record_frame
                                 * normalises it (min(sharpness/50, 1)) for dc_score's
                                 * tiebreaker. */
    int update_motion_ref;     /* 1: thumb becomes the new diff reference and
                                 * resets the heartbeat clock (a normal wake
                                 * record); 0: a manual /shoot, which must not
                                 * disturb the motion trigger. */
} record_req_t;

/* Builds dc_meta_t, writes JSON+JPEG to the "spool" tier via dusty_spool
 * (boot = NVS "boot_count", seq = g_state.seq), advances
 * g_state.seq/thumb/awake_ms/pending_n and NVS last_ts on success. Returns
 * 1 on success, 0 on failure (spool not mounted, write failed, or meta
 * didn't fit -- logged either way). seq_out, when non-NULL, gets the seq
 * this frame was written under (contact.c's `shoot` hook needs it to
 * upload the same file right back out). */
int record_frame(const record_req_t *req, uint32_t *seq_out);
/* Build the standard meta JSON for req with sequence number seq (no SD
 * involved). Returns length or -1. Used by record_frame and by contact's
 * shoot hook when the card is unmounted (direct upload). */
int record_build_meta(const record_req_t *req, uint32_t seq, char *buf, size_t n);

#ifdef __cplusplus
}
#endif
#endif
