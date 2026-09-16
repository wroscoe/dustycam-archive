/* dusty_core: the portable, host-testable logic of a dustycam camera on
 * ESP-IDF. No IDF headers, no heap, no I/O. Everything here is driven from
 * cameras/common/espidf/tests/test_core.py through ctypes, so keep the ABI
 * plain C: fixed-size structs, int/float/char* parameters, no callbacks.
 * Contract: docs/camera_standard.md §4, docs/camera_operation.md §4.1, §6, §7, §8.
 */
#ifndef DUSTY_CORE_H
#define DUSTY_CORE_H
#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ---------- thumbnail / motion / light ---------- */
#define DC_TH_W 40
#define DC_TH_H 30
#define DC_TH_N (DC_TH_W * DC_TH_H)

typedef struct { uint8_t px[DC_TH_N]; } dc_thumb_t;

/* Box-average an RGB565 (little-endian, as esp32-camera's jpg2rgb565 emits)
 * w x h image down to DC_TH_W x DC_TH_H gray. w >= DC_TH_W, h >= DC_TH_H. */
void dc_thumb_from_rgb565(const uint16_t *rgb, int w, int h, dc_thumb_t *out);
/* Same from 8-bit gray. */
void dc_thumb_from_gray(const uint8_t *gray, int w, int h, dc_thumb_t *out);
/* Mean luma 0..255: this is `lum`. */
int dc_thumb_lum(const dc_thumb_t *t);

typedef struct {
    float frac;              /* fraction of thumb pixels whose mean-normalised |delta| >= l_thresh: `diff` */
    int x0, y0, x1, y1;      /* inclusive bbox of those pixels in thumb coords; all -1 when frac == 0 */
    int n;                   /* count of changed pixels */
} dc_diff_t;

/* Both thumbs are mean-normalised first (exposure drift cancels), then the
 * per-pixel |delta| is compared with l_thresh (0..255). */
void dc_thumb_diff(const dc_thumb_t *cur, const dc_thumb_t *ref, int l_thresh, dc_diff_t *out);

/* Motion-centred square crop for the gate (animal_model.md §5). Maps the
 * thumb bbox to a frame_w x frame_h image, pads by `pad` (0.5 = 50 %), makes
 * it square, clamps to the frame. Returns 1 and fills cx,cy,side (top-left +
 * side) or returns 0 for "use the full frame" when d->n == 0 or the bbox
 * covers more than diffuse_frac of the thumb area. side >= min_side. */
int dc_crop_box(const dc_diff_t *d, int frame_w, int frame_h, float pad, float diffuse_frac,
                int min_side, int *cx, int *cy, int *side);

/* Sharpness = stdev of a 4x Laplacian over a gray region (focus score, as
 * common/micropython/focus.py). Region clamped to the image. */
float dc_sharpness(const uint8_t *gray, int w, int h, int x0, int y0, int cw, int ch);

/* ---------- drain rank (camera_operation.md §7) ---------- */
/* why: "boot"/"heartbeat" rank above everything (>= 1000), then detection
 * confidence (0..1 → 100..200), else diff (0..1 → 0..100), sharpness as a
 * small tiebreaker (0..1 added). det_conf < 0 means no detection ran. */
float dc_score(const char *why, float det_conf, float diff, float sharp);

/* ---------- night policy (camera_operation.md §6) ---------- */
#define DC_NIGHT_HIST 7
typedef struct {
    int lum_night, lum_day, night_confirm_n;
    uint32_t night_margin_s, night_probe_s, period_s;
} dc_night_cfg_t;

typedef struct {
    int dark_n;              /* consecutive dark wakes while not in night */
    int in_night;
    uint32_t night_start_s;  /* board clock at entry */
    int hist_n;              /* number of valid entries in hist (<= DC_NIGHT_HIST) */
    uint32_t hist[DC_NIGHT_HIST]; /* ring, newest at (hist_head-1) */
    int hist_head;
    int slept_toward_dawn;   /* 1 once the long sleep has been taken this night */
} dc_night_t;

typedef struct {
    int entered;             /* this step entered night */
    int left;                /* this step left night: record the morning frame */
    uint32_t night_len_s;    /* valid when left */
    uint32_t sleep_s;        /* how long to deep-sleep now (period_s when not in night) */
    int in_night;            /* state after the step */
} dc_night_out_t;

/* Median of the last 3 lengths, 0 when hist_n == 0. */
uint32_t dc_night_predict(const dc_night_t *st);
void dc_night_step(dc_night_t *st, int lum, uint32_t now_s, const dc_night_cfg_t *cfg, dc_night_out_t *out);
/* Serialise / restore the history for /night.json ("[len,len,...]" newest last). */
int  dc_night_hist_to_json(const dc_night_t *st, char *buf, size_t n);
int  dc_night_hist_from_json(dc_night_t *st, const char *json);

/* ---------- config (tier 2 tuning, camera_operation.md §4.1) ---------- */
#define DC_KEEP_LABELS_MAX 4
typedef struct {
    int cfg;                 /* server config version, 0 = defaults */
    char profile[16];
    char mode[10];           /* "live" | "setup" */
    int period_s, interval_n, heartbeat_s;
    float diff_min_frac;
    int diff_l_thresh, gate_pct;
    char keep_labels[DC_KEEP_LABELS_MAX][12];
    int keep_labels_n;
    int keep_all, audit_n, debug_frames, debug_max, upload_cap;
    int lum_night, lum_day, night_confirm_n, night_margin_s, night_probe_s;
    int hotspot_join_s, contact_idle_s, setup_secs, telemetry_s, led_capture;
    int spool_max_frames;
} dc_cfg_t;

/* Apply known keys from a JSON object (unknown keys ignored, types coerced
 * to the field's type, out-of-range values clamped). Returns the number of
 * keys applied, -1 on a parse error. `cfg` is applied like any key. */
int dc_cfg_apply_json(dc_cfg_t *c, const char *json);
/* Full JSON object of the struct (what /status and the NVS blob carry). */
int dc_cfg_to_json(const dc_cfg_t *c, char *buf, size_t n);
int dc_cfg_has_label(const dc_cfg_t *c, const char *label);

/* ---------- config source/base tracking (docs/phone_app_plan.md §3,
 * decision 6: the phone app may edit tier 2 over BLE; the board pushes
 * the result to sensorhub at its next contact, base-checked) ---------- */
typedef struct {
    int cfg_src_is_ble; /* 0 = "server" (last synced with sensorhub), 1 = "ble" (local edit(s) not yet pushed) */
    int cfg_base;        /* the server's cfg this diverged from (source="server") when pushed */
} dc_cfg_src_t;

/* Called when a local (BLE) edit bumps `cfg`. `cfg_before` is the version
 * number immediately before the bump. If the source was already "server"
 * this is a fresh divergence, so cfg_base becomes cfg_before; if it was
 * already "ble" (an earlier local edit hasn't been pushed yet), the
 * existing base is kept -- the chain still started at the same server
 * version. */
void dc_cfg_src_on_local_edit(dc_cfg_src_t *s, int cfg_before);
/* Called after a successful pull/push with the server: source becomes
 * "server" and cfg_base becomes the now-agreed version. */
void dc_cfg_src_on_server_sync(dc_cfg_src_t *s, int cfg);

/* ---------- meta (camera_standard.md §4) ---------- */
typedef struct {
    int64_t ts; uint32_t seq; int w, h;
    const char *v; int cfg; const char *ip; const char *mode; const char *why;
    float diff; float gate; int heartbeat; int buffered;
    int lum; const char *clock;          /* "set" | "est" | "none" */
    float score;
    int has_det; const char *det_label; float det_conf;
    int audit;
    int64_t night_s;                     /* < 0: omit */
} dc_meta_t;
/* Writes a JSON object, returns length or -1 if it did not fit. */
int dc_meta_build(char *buf, size_t n, const dc_meta_t *m);

/* ---------- spool naming (camera_operation.md §7) ---------- */
/* "<root>/spool/<boot>/<seq>.<ext>", e.g. /sd/spool/17/000042.jpg; returns
 * length or -1 if it does not fit. seq zero-padded to 6. */
int dc_spool_path(char *buf, size_t n, const char *root, const char *tier, uint32_t boot, uint32_t seq, const char *ext);
/* Parse "<boot>/<seq>.jpg" style relative names back; returns 1 on success. */
int dc_spool_parse(const char *rel, uint32_t *boot, uint32_t *seq);
/* Pull `score` (and `why`) out of a sidecar without a full parser. Returns
 * 1 when score was found. why_out may be NULL. */
int dc_sidecar_score(const char *json, float *score, char *why_out, size_t why_n);

/* ---------- time ---------- */
/* RFC 1123 "Sun, 06 Nov 1994 08:49:37 GMT" → epoch seconds, -1 on failure. */
int64_t dc_parse_http_date(const char *s);

/* ---------- version ---------- */
/* Strings: returns nonzero when `remote` names a different, installable
 * version: not empty, != running, != bad. */
int dc_fw_should_install(const char *remote, const char *running, const char *bad);

#ifdef __cplusplus
}
#endif
#endif
