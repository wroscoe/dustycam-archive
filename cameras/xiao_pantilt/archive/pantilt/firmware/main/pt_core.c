#include "pt_core.h"

#include <math.h>
#include <stddef.h>

const float pt_scan_anchors_deg[PT_SCAN_ANCHOR_COUNT] = {0.0f, 80.0f, 160.0f, 180.0f};

bool pt_scan_plan_is_within(float logical_min_deg, float logical_max_deg)
{
    if (logical_max_deg <= logical_min_deg) return false;
    for (unsigned i = 0; i < PT_SCAN_ANCHOR_COUNT; ++i) {
        if (pt_scan_anchors_deg[i] < logical_min_deg || pt_scan_anchors_deg[i] > logical_max_deg) return false;
    }
    return true;
}

bool pt_scan_plan_is_safe(float horizontal_fov_deg, float min_overlap_deg,
                          float min_scene_coverage_deg)
{
    if (horizontal_fov_deg <= 0.0f || min_overlap_deg < 0.0f || min_scene_coverage_deg <= 0.0f) return false;
    for (unsigned i = 1; i < PT_SCAN_ANCHOR_COUNT; ++i) {
        float spacing = pt_scan_anchors_deg[i] - pt_scan_anchors_deg[i - 1u];
        if (spacing <= 0.0f || horizontal_fov_deg - spacing < min_overlap_deg) return false;
    }
    float coverage = pt_scan_anchors_deg[PT_SCAN_ANCHOR_COUNT - 1u] - pt_scan_anchors_deg[0] + horizontal_fov_deg;
    return coverage >= min_scene_coverage_deg;
}

bool pt_budget_take(pt_budget_t *budget, unsigned max_pulses,
                    unsigned max_motion_ms, unsigned requested_ms)
{
    if (!budget || requested_ms == 0u || budget->pulses >= max_pulses ||
        budget->motion_ms > max_motion_ms || requested_ms > max_motion_ms - budget->motion_ms) return false;
    ++budget->pulses;
    budget->motion_ms += requested_ms;
    return true;
}

static float sample(const uint8_t *values, unsigned width, float x)
{
    unsigned lo = (unsigned)x;
    unsigned hi = lo + 1u < width ? lo + 1u : lo;
    return values[lo] * ((float)hi - x) + values[hi] * (x - (float)lo);
}

static float zncc(const float *a, const float *b, unsigned n)
{
    if (n < 2) return -1.0f;
    float ma = 0.0f, mb = 0.0f;
    for (unsigned i = 0; i < n; ++i) { ma += a[i]; mb += b[i]; }
    ma /= n; mb /= n;
    float va = 0.0f, vb = 0.0f, cross = 0.0f;
    for (unsigned i = 0; i < n; ++i) {
        float da = a[i] - ma, db = b[i] - mb;
        va += da * da; vb += db * db; cross += da * db;
    }
    return (va <= 1e-6f || vb <= 1e-6f) ? -1.0f : cross / sqrtf(va * vb);
}

static float bearing_for_x(float x, unsigned width, float focal)
{
    const float center = ((float)width - 1.0f) * 0.5f;
    return atanf((x - center) / focal);
}

static bool profile_is_repetitive(const pt_profile_t *profile)
{
    const unsigned w = profile->width;
    bool bins[32] = {false};
    unsigned distinct = 0;
    for (unsigned x = 0; x < w; ++x) {
        unsigned bin = profile->value[x] >> 3;
        if (!bins[bin]) { bins[bin] = true; ++distinct; }
    }
    /* A two/three-level stripe is an exact ambiguity, not usable texture. */
    if (distinct < 6u) return true;
    float a[PT_PROFILE_MAX_WIDTH], b[PT_PROFILE_MAX_WIDTH];
    /* Reject a strong repeating spatial period only when it repeats at least
     * three times across the profile. This is deliberately conservative: a
     * single broad landmark does not look periodic to this guard. */
    for (unsigned period = 2; period * 3u <= w; ++period) {
        unsigned n = w - period;
        for (unsigned x = 0; x < n; ++x) {
            a[x] = profile->value[x]; b[x] = profile->value[x + period];
        }
        if (zncc(a, b, n) > 0.96f) return true;
    }
    return false;
}

static float candidate_score(const pt_profile_t *reference, const pt_profile_t *current,
                             const float *grad_a, float focal, float radians)
{
    const unsigned w = reference->width;
    float va[PT_PROFILE_MAX_WIDTH], vb[PT_PROFILE_MAX_WIDTH];
    float ga[PT_PROFILE_MAX_WIDTH], gb[PT_PROFILE_MAX_WIDTH];
    unsigned n = 0;
    for (unsigned x = 1; x + 1u < w; ++x) {
        float other = ((float)w - 1.0f) * 0.5f + focal * tanf(bearing_for_x((float)x, w, focal) - radians);
        if (other >= 1.0f && other < (float)(w - 1u)) {
            va[n] = reference->value[x];
            vb[n] = sample(current->value, w, other);
            ga[n] = grad_a[x];
            gb[n] = fabsf(sample(current->value, w, fminf((float)(w - 1u), other + 1.0f)) -
                           sample(current->value, w, fmaxf(0.0f, other - 1.0f)));
            ++n;
        }
    }
    return n < 28u ? -2.0f : 0.72f * zncc(va, vb, n) + 0.28f * zncc(ga, gb, n);
}

pt_registration_t pt_register_profile(const pt_profile_t *reference,
                                      const pt_profile_t *current,
                                      float horizontal_fov_deg,
                                      float min_delta_deg,
                                      float max_delta_deg)
{
    pt_registration_t out = {0.0f, 0.0f, -1.0f, 0};
    if (!reference || !current || reference->width != current->width || reference->width < 32 ||
        reference->width > PT_PROFILE_MAX_WIDTH || horizontal_fov_deg <= 1.0f ||
        min_delta_deg > max_delta_deg) return out;

    const unsigned w = reference->width;
    float raw[PT_PROFILE_MAX_WIDTH], grad_a[PT_PROFILE_MAX_WIDTH];
    float mean = 0.0f;
    for (unsigned x = 0; x < w; ++x) { raw[x] = reference->value[x]; mean += raw[x]; }
    mean /= w;
    float variance = 0.0f;
    for (unsigned x = 0; x < w; ++x) {
        variance += (raw[x] - mean) * (raw[x] - mean);
        unsigned left = x == 0 ? 0 : x - 1, right = x + 1u < w ? x + 1u : w - 1u;
        grad_a[x] = fabsf((float)reference->value[right] - reference->value[left]);
    }
    if (sqrtf(variance / w) < 5.0f || profile_is_repetitive(reference) || profile_is_repetitive(current))
        return out; /* textureless or repeating views fail closed */

    const float pi = 3.14159265358979323846f;
    const float focal = (float)w / (2.0f * tanf(horizontal_fov_deg * pi / 360.0f));
    const float extent = horizontal_fov_deg * 0.96f;
    float lo = fmaxf(-extent, min_delta_deg), hi = fminf(extent, max_delta_deg);
    if (lo > hi) return out;
    /* Match the reference's fine grid: a 0.5-degree quantization error can
     * accumulate materially over a full outbound/return scan. */
    const float step = fminf(horizontal_fov_deg / (float)w, 0.25f);
    float best = -2.0f, best_delta = 0.0f, rival = -2.0f;

    for (float delta = lo; delta <= hi + step * 0.25f; delta += step) {
        if (delta > hi) delta = hi;
        const float radians = delta * pi / 180.0f;
        float score = candidate_score(reference, current, grad_a, focal, radians);
        if (score > best) { best = score; best_delta = delta; }
        if (delta == hi) break;
    }
    if (best < -1.0f) return out;

    /* Find an independent (>=4 degree separated) competing peak. */
    for (float delta = lo; delta <= hi + step * 0.25f; delta += step) {
        if (delta > hi) delta = hi;
        if (fabsf(delta - best_delta) >= 4.0f) {
            const float radians = delta * pi / 180.0f;
            float score = candidate_score(reference, current, grad_a, focal, radians);
            if (score > rival) rival = score;
        }
        if (delta == hi) break;
    }
    float margin = fmaxf(0.0f, best - rival);
    out.yaw_delta_deg = best_delta;
    out.score = best;
    /* Repeating fences/stripes can have several equally good correlation
     * peaks. They are unsafe for feedback, even if one peak is high. */
    if (rival > -1.1f && margin < 0.08f) return out;
    out.confidence = fminf(1.0f, fmaxf(0.0f, ((best + 1.0f) * 0.5f) * fminf(1.0f, 0.45f + margin * 5.0f)));
    out.pixel_shift = (int)lroundf(focal * tanf(-best_delta * pi / 180.0f));
    return out;
}
