#include <assert.h>
#include <math.h>
#include <stdio.h>

#include "pt_core.h"

static float scene(float radians)
{
    /* Deliberately non-periodic enough over a camera view to make one peak. */
    return 122.0f + 47.0f * sinf(3.7f * radians) + 28.0f * sinf(11.3f * radians + .4f) +
           18.0f * sinf(23.9f * radians + 1.1f) + 13.0f * sinf(47.0f * radians + .2f);
}

static void render_profile(pt_profile_t *out, float yaw_deg)
{
    const float pi = 3.14159265358979323846f, fov = 110.0f;
    const unsigned w = 100;
    const float focal = w / (2.0f * tanf(fov * pi / 360.0f));
    out->width = w;
    for (unsigned x = 0; x < w; ++x) {
        float bearing = atanf(((float)x - ((float)w - 1.0f) / 2.0f) / focal);
        float value = scene(yaw_deg * pi / 180.0f + bearing);
        out->value[x] = (uint8_t)lroundf(fmaxf(0.0f, fminf(255.0f, value)));
    }
}

static void render_periodic(pt_profile_t *out, float yaw_deg)
{
    const float pi = 3.14159265358979323846f, fov = 110.0f;
    const unsigned w = 100; const float focal = w / (2.0f * tanf(fov * pi / 360.0f));
    out->width = w;
    for (unsigned x = 0; x < w; ++x) {
        float bearing = atanf(((float)x - ((float)w - 1.0f) / 2.0f) / focal);
        out->value[x] = (uint8_t)lroundf(127.0f + 80.0f * sinf(36.0f * (yaw_deg * pi / 180.0f + bearing)));
    }
}

static void affine_lighting(pt_profile_t *profile)
{
    for (unsigned x = 0; x < profile->width; ++x)
        profile->value[x] = (uint8_t)lroundf(18.0f + 0.72f * profile->value[x]);
}

static void test_plan(void)
{
    assert(pt_scan_anchors_deg[0] == 0.0f && pt_scan_anchors_deg[1] == 80.0f &&
           pt_scan_anchors_deg[2] == 160.0f && pt_scan_anchors_deg[3] == 180.0f);
    assert(pt_scan_plan_is_within(0, 180));
    assert(!pt_scan_plan_is_within(1, 180));
    assert(!pt_scan_plan_is_within(0, 179));
    assert(pt_scan_plan_is_safe(110, 30, 290));
    assert(!pt_scan_plan_is_safe(109, 30, 290));
    assert(!pt_scan_plan_is_safe(110, 31, 290));
    pt_budget_t budget = {0};
    assert(pt_budget_take(&budget, 2, 400, 200));
    assert(pt_budget_take(&budget, 2, 400, 200));
    assert(!pt_budget_take(&budget, 2, 400, 1));
}

static void test_pinhole_registration(void)
{
    pt_profile_t reference, current;
    render_profile(&reference, 17.0f);
    render_profile(&current, 25.0f);
    pt_registration_t r = pt_register_profile(&reference, &current, 110.0f, -3.0f, 13.0f);
    printf("known turn: delta=%.3f confidence=%.3f score=%.3f\n", r.yaw_delta_deg, r.confidence, r.score);
    assert(fabsf(r.yaw_delta_deg - 8.0f) < 1.5f);
    assert(r.confidence >= .40f);
    /* A physical window is a safety constraint, not a hint. */
    r = pt_register_profile(&reference, &current, 110.0f, -3.0f, 3.0f);
    assert(fabsf(r.yaw_delta_deg) <= 3.001f);
}

/* These are Python-reference-compatible vectors: scene yaw is projected
 * through the same rectilinear focal model as xiao_pantilt.registration. */
static void test_python_compatible_vectors(void)
{
    pt_profile_t reference, current;
    render_profile(&reference, 41.0f);
    render_profile(&current, 34.0f);
    pt_registration_t r = pt_register_profile(&reference, &current, 110.0f, -12.0f, 4.0f);
    printf("negative vector: delta=%.3f confidence=%.3f\n", r.yaw_delta_deg, r.confidence);
    assert(fabsf(r.yaw_delta_deg + 7.0f) < 1.5f && r.confidence >= .40f);
    render_profile(&current, 41.0f);
    r = pt_register_profile(&reference, &current, 110.0f, -8.0f, 8.0f);
    assert(fabsf(r.yaw_delta_deg) < 1.2f && r.confidence >= .40f);
    affine_lighting(&current);
    r = pt_register_profile(&reference, &current, 110.0f, -8.0f, 8.0f);
    assert(fabsf(r.yaw_delta_deg) < 1.2f && r.confidence >= .40f);
}

static void test_textureless_fails_closed(void)
{
    pt_profile_t a = {.width = 100}, b = {.width = 100};
    for (unsigned i = 0; i < 100; ++i) a.value[i] = b.value[i] = 112;
    pt_registration_t r = pt_register_profile(&a, &b, 110.0f, -8.0f, 8.0f);
    assert(r.confidence == 0.0f);
    assert(r.score == -1.0f);
}

static void test_periodic_ambiguity_fails_closed(void)
{
    pt_profile_t a, b;
    render_periodic(&a, 0.0f); render_periodic(&b, 10.0f);
    pt_registration_t r = pt_register_profile(&a, &b, 110.0f, -15.0f, 15.0f);
    printf("periodic vector: delta=%.3f confidence=%.3f score=%.3f\n", r.yaw_delta_deg, r.confidence, r.score);
    assert(r.confidence == 0.0f);
}

static void test_exact_two_level_stripes_fail_closed(void)
{
    pt_profile_t a = {.width = 100}, b = {.width = 100};
    for (unsigned x = 0; x < 100; ++x) {
        a.value[x] = (x % 2u) ? 224 : 32;
        b.value[x] = ((x + 1u) % 2u) ? 224 : 32;
    }
    pt_registration_t r = pt_register_profile(&a, &b, 110.0f, -15.0f, 15.0f);
    printf("two-level stripes: delta=%.3f confidence=%.3f score=%.3f\n", r.yaw_delta_deg, r.confidence, r.score);
    assert(r.confidence == 0.0f && r.score == -1.0f);
}

int main(void)
{
    test_plan();
    test_pinhole_registration();
    test_python_compatible_vectors();
    test_textureless_fails_closed();
    test_periodic_ambiguity_fails_closed();
    test_exact_two_level_stripes_fail_closed();
    puts("pt_core host tests passed");
    return 0;
}
