#pragma once

#include <stdbool.h>
#include <stdint.h>

/* Portable core: it deliberately has no ESP-IDF includes. */
#define PT_PROFILE_MAX_WIDTH 128
#define PT_SCAN_ANCHOR_COUNT 4

typedef struct {
    uint16_t width;
    uint8_t value[PT_PROFILE_MAX_WIDTH];
} pt_profile_t;

typedef struct {
    float yaw_delta_deg;
    float confidence;       /* 0..1, combines correlation and peak uniqueness */
    float score;            /* combined raw/gradient ZNCC, -1..1 */
    int pixel_shift;
} pt_registration_t;

/* The commanded headings cover about 290 degrees with a 110-degree FOV. */
extern const float pt_scan_anchors_deg[PT_SCAN_ANCHOR_COUNT];

bool pt_scan_plan_is_within(float logical_min_deg, float logical_max_deg);

/* The fixed headings are legal only if every adjacent pair overlaps and the
 * full visible arc reaches the requested coverage. */
bool pt_scan_plan_is_safe(float horizontal_fov_deg, float min_overlap_deg,
                          float min_scene_coverage_deg);

typedef struct {
    unsigned pulses;
    unsigned motion_ms;
} pt_budget_t;

/* Reserve a motor pulse before it is issued. This has no hardware side
 * effects and makes bounds deterministic and host-testable. */
bool pt_budget_take(pt_budget_t *budget, unsigned max_pulses,
                    unsigned max_motion_ms, unsigned requested_ms);

/*
 * Register horizontal luminance profiles under a rectilinear/pinhole model.
 * `reference` is the earlier view and `current` is the later view; a positive
 * result means the camera turned toward increasing logical pan. Candidates
 * are restricted to the signed, physically plausible window supplied by the
 * caller. The function never estimates an absolute angle or encoder value.
 */
pt_registration_t pt_register_profile(const pt_profile_t *reference,
                                      const pt_profile_t *current,
                                      float horizontal_fov_deg,
                                      float min_delta_deg,
                                      float max_delta_deg);
