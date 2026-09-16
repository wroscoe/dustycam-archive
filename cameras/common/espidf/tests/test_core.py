"""Host tests for dusty_core: builds libdusty_core.so via the host Makefile
and drives it through ctypes. stdlib unittest only (pytest is not installed
on this host, and doesn't need to be: unittest discovery finds this file).

Run from the repo root:
    python3 -m unittest discover -s cameras/common/espidf/tests -v
"""
import ctypes
import math
import os
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
COMPONENT_DIR = os.path.normpath(os.path.join(HERE, "..", "components", "dusty_core"))
HOST_DIR = os.path.join(COMPONENT_DIR, "host")
SO_PATH = os.path.join(HOST_DIR, "libdusty_core.so")

DC_TH_W = 40
DC_TH_H = 30
DC_TH_N = DC_TH_W * DC_TH_H
DC_NIGHT_HIST = 7
DC_KEEP_LABELS_MAX = 4


# ---------- ctypes structures mirroring dusty_core.h ----------

class DcThumb(ctypes.Structure):
    _fields_ = [("px", ctypes.c_uint8 * DC_TH_N)]


class DcDiff(ctypes.Structure):
    _fields_ = [
        ("frac", ctypes.c_float),
        ("x0", ctypes.c_int), ("y0", ctypes.c_int),
        ("x1", ctypes.c_int), ("y1", ctypes.c_int),
        ("n", ctypes.c_int),
    ]


class DcNightCfg(ctypes.Structure):
    _fields_ = [
        ("lum_night", ctypes.c_int),
        ("lum_day", ctypes.c_int),
        ("night_confirm_n", ctypes.c_int),
        ("night_margin_s", ctypes.c_uint32),
        ("night_probe_s", ctypes.c_uint32),
        ("period_s", ctypes.c_uint32),
    ]


class DcNight(ctypes.Structure):
    _fields_ = [
        ("dark_n", ctypes.c_int),
        ("in_night", ctypes.c_int),
        ("night_start_s", ctypes.c_uint32),
        ("hist_n", ctypes.c_int),
        ("hist", ctypes.c_uint32 * DC_NIGHT_HIST),
        ("hist_head", ctypes.c_int),
        ("slept_toward_dawn", ctypes.c_int),
    ]


class DcNightOut(ctypes.Structure):
    _fields_ = [
        ("entered", ctypes.c_int),
        ("left", ctypes.c_int),
        ("night_len_s", ctypes.c_uint32),
        ("sleep_s", ctypes.c_uint32),
        ("in_night", ctypes.c_int),
    ]


class DcCfg(ctypes.Structure):
    _fields_ = [
        ("cfg", ctypes.c_int),
        ("profile", ctypes.c_char * 16),
        ("mode", ctypes.c_char * 10),
        ("period_s", ctypes.c_int),
        ("interval_n", ctypes.c_int),
        ("heartbeat_s", ctypes.c_int),
        ("diff_min_frac", ctypes.c_float),
        ("diff_l_thresh", ctypes.c_int),
        ("gate_pct", ctypes.c_int),
        ("keep_labels", (ctypes.c_char * 12) * DC_KEEP_LABELS_MAX),
        ("keep_labels_n", ctypes.c_int),
        ("keep_all", ctypes.c_int),
        ("audit_n", ctypes.c_int),
        ("debug_frames", ctypes.c_int),
        ("debug_max", ctypes.c_int),
        ("upload_cap", ctypes.c_int),
        ("lum_night", ctypes.c_int),
        ("lum_day", ctypes.c_int),
        ("night_confirm_n", ctypes.c_int),
        ("night_margin_s", ctypes.c_int),
        ("night_probe_s", ctypes.c_int),
        ("hotspot_join_s", ctypes.c_int),
        ("contact_idle_s", ctypes.c_int),
        ("setup_secs", ctypes.c_int),
        ("telemetry_s", ctypes.c_int),
        ("led_capture", ctypes.c_int),
        ("spool_max_frames", ctypes.c_int),
    ]


class DcCfgSrc(ctypes.Structure):
    _fields_ = [
        ("cfg_src_is_ble", ctypes.c_int),
        ("cfg_base", ctypes.c_int),
    ]


class DcMeta(ctypes.Structure):
    _fields_ = [
        ("ts", ctypes.c_int64),
        ("seq", ctypes.c_uint32),
        ("w", ctypes.c_int),
        ("h", ctypes.c_int),
        ("v", ctypes.c_char_p),
        ("cfg", ctypes.c_int),
        ("ip", ctypes.c_char_p),
        ("mode", ctypes.c_char_p),
        ("why", ctypes.c_char_p),
        ("diff", ctypes.c_float),
        ("gate", ctypes.c_float),
        ("heartbeat", ctypes.c_int),
        ("buffered", ctypes.c_int),
        ("lum", ctypes.c_int),
        ("clock", ctypes.c_char_p),
        ("score", ctypes.c_float),
        ("has_det", ctypes.c_int),
        ("det_label", ctypes.c_char_p),
        ("det_conf", ctypes.c_float),
        ("audit", ctypes.c_int),
        ("night_s", ctypes.c_int64),
    ]


def _load_lib():
    lib = ctypes.CDLL(SO_PATH)

    lib.dc_thumb_from_rgb565.argtypes = [ctypes.POINTER(ctypes.c_uint16), ctypes.c_int, ctypes.c_int, ctypes.POINTER(DcThumb)]
    lib.dc_thumb_from_rgb565.restype = None

    lib.dc_thumb_from_gray.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_int, ctypes.c_int, ctypes.POINTER(DcThumb)]
    lib.dc_thumb_from_gray.restype = None

    lib.dc_thumb_lum.argtypes = [ctypes.POINTER(DcThumb)]
    lib.dc_thumb_lum.restype = ctypes.c_int

    lib.dc_thumb_diff.argtypes = [ctypes.POINTER(DcThumb), ctypes.POINTER(DcThumb), ctypes.c_int, ctypes.POINTER(DcDiff)]
    lib.dc_thumb_diff.restype = None

    lib.dc_crop_box.argtypes = [
        ctypes.POINTER(DcDiff), ctypes.c_int, ctypes.c_int, ctypes.c_float, ctypes.c_float,
        ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
    ]
    lib.dc_crop_box.restype = ctypes.c_int

    lib.dc_sharpness.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
    lib.dc_sharpness.restype = ctypes.c_float

    lib.dc_score.argtypes = [ctypes.c_char_p, ctypes.c_float, ctypes.c_float, ctypes.c_float]
    lib.dc_score.restype = ctypes.c_float

    lib.dc_night_predict.argtypes = [ctypes.POINTER(DcNight)]
    lib.dc_night_predict.restype = ctypes.c_uint32

    lib.dc_night_step.argtypes = [ctypes.POINTER(DcNight), ctypes.c_int, ctypes.c_uint32, ctypes.POINTER(DcNightCfg), ctypes.POINTER(DcNightOut)]
    lib.dc_night_step.restype = None

    lib.dc_night_hist_to_json.argtypes = [ctypes.POINTER(DcNight), ctypes.c_char_p, ctypes.c_size_t]
    lib.dc_night_hist_to_json.restype = ctypes.c_int

    lib.dc_night_hist_from_json.argtypes = [ctypes.POINTER(DcNight), ctypes.c_char_p]
    lib.dc_night_hist_from_json.restype = ctypes.c_int

    lib.dc_cfg_apply_json.argtypes = [ctypes.POINTER(DcCfg), ctypes.c_char_p]
    lib.dc_cfg_apply_json.restype = ctypes.c_int

    lib.dc_cfg_to_json.argtypes = [ctypes.POINTER(DcCfg), ctypes.c_char_p, ctypes.c_size_t]
    lib.dc_cfg_to_json.restype = ctypes.c_int

    lib.dc_cfg_has_label.argtypes = [ctypes.POINTER(DcCfg), ctypes.c_char_p]
    lib.dc_cfg_has_label.restype = ctypes.c_int

    lib.dc_meta_build.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.POINTER(DcMeta)]
    lib.dc_meta_build.restype = ctypes.c_int

    lib.dc_spool_path.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_char_p]
    lib.dc_spool_path.restype = ctypes.c_int

    lib.dc_spool_parse.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32)]
    lib.dc_spool_parse.restype = ctypes.c_int

    lib.dc_sidecar_score.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_float), ctypes.c_char_p, ctypes.c_size_t]
    lib.dc_sidecar_score.restype = ctypes.c_int

    lib.dc_parse_http_date.argtypes = [ctypes.c_char_p]
    lib.dc_parse_http_date.restype = ctypes.c_int64

    lib.dc_fw_should_install.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
    lib.dc_fw_should_install.restype = ctypes.c_int

    lib.dc_cfg_src_on_local_edit.argtypes = [ctypes.POINTER(DcCfgSrc), ctypes.c_int]
    lib.dc_cfg_src_on_local_edit.restype = None

    lib.dc_cfg_src_on_server_sync.argtypes = [ctypes.POINTER(DcCfgSrc), ctypes.c_int]
    lib.dc_cfg_src_on_server_sync.restype = None

    return lib


def rgb565_to_gray_py(v):
    r5 = (v >> 11) & 0x1F
    g6 = (v >> 5) & 0x3F
    b5 = v & 0x1F
    r8 = (r5 << 3) | (r5 >> 2)
    g8 = (g6 << 2) | (g6 >> 4)
    b8 = (b5 << 3) | (b5 >> 2)
    y = (r8 * 77 + g8 * 150 + b8 * 29) >> 8
    return max(0, min(255, y))


def gray_to_rgb565(g):
    r5 = g >> 3
    g6 = g >> 2
    b5 = g >> 3
    return (r5 << 11) | (g6 << 5) | b5


class DustyCoreTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        r = subprocess.run(["make", "-C", HOST_DIR, "clean", "all"], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("host build failed:\n%s\n%s" % (r.stdout, r.stderr))
        cls.lib = _load_lib()

    def make_thumb(self, values):
        t = DcThumb()
        for i, v in enumerate(values):
            t.px[i] = v
        return t

    def uniform_thumb(self, v):
        return self.make_thumb([v] * DC_TH_N)


class ThumbTests(DustyCoreTestCase):
    def test_thumb_from_rgb565_gradient_lum(self):
        w, h = 80, 60  # exact 2x2 box multiple of the 40x30 thumb
        grays = [[min(255, (x * 255) // (w - 1)) for x in range(w)] for _ in range(h)]
        buf = (ctypes.c_uint16 * (w * h))()
        for y in range(h):
            for x in range(w):
                buf[y * w + x] = gray_to_rgb565(grays[y][x])

        thumb = DcThumb()
        self.lib.dc_thumb_from_rgb565(buf, w, h, ctypes.byref(thumb))
        lum = self.lib.dc_thumb_lum(ctypes.byref(thumb))

        # Expected: replicate the exact per-cell box average (2x2 -> 1
        # here), then its mean, matching dc_thumb_lum's own integer
        # truncation -- "within 1" covers any remaining rounding slack.
        decoded = [[rgb565_to_gray_py(gray_to_rgb565(grays[y][x])) for x in range(w)] for y in range(h)]
        cell_vals = []
        for oy in range(DC_TH_H):
            y0, y1 = oy * h // DC_TH_H, (oy + 1) * h // DC_TH_H
            for ox in range(DC_TH_W):
                x0, x1 = ox * w // DC_TH_W, (ox + 1) * w // DC_TH_W
                vals = [decoded[y][x] for y in range(y0, y1) for x in range(x0, x1)]
                cell_vals.append(sum(vals) // len(vals))
        expected = sum(cell_vals) // len(cell_vals)
        self.assertLessEqual(abs(lum - expected), 1)

    def test_thumb_from_gray_box_average(self):
        w, h = 40, 30  # 1:1 mapping, trivial to predict exactly
        buf = (ctypes.c_uint8 * (w * h))()
        for i in range(w * h):
            buf[i] = i % 256
        thumb = DcThumb()
        self.lib.dc_thumb_from_gray(buf, w, h, ctypes.byref(thumb))
        for i in range(w * h):
            self.assertEqual(thumb.px[i], i % 256)

    def test_diff_identical_frames_is_zero(self):
        a = self.make_thumb([(i * 7) % 256 for i in range(DC_TH_N)])
        b = self.make_thumb([(i * 7) % 256 for i in range(DC_TH_N)])
        d = DcDiff()
        self.lib.dc_thumb_diff(ctypes.byref(a), ctypes.byref(b), 8, ctypes.byref(d))
        self.assertEqual(d.n, 0)
        self.assertEqual(d.frac, 0.0)
        self.assertEqual((d.x0, d.y0, d.x1, d.y1), (-1, -1, -1, -1))

    def test_diff_shifted_block_bbox_and_fraction(self):
        ref = self.uniform_thumb(50)
        cur_vals = [50] * DC_TH_N
        # A bright 4x4 block at (10,10)..(13,13) in a thumb otherwise equal
        # to ref: after mean-normalisation this block alone differs.
        x0, y0, x1, y1 = 10, 10, 13, 13
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                cur_vals[yy * DC_TH_W + xx] = 200
        cur = self.make_thumb(cur_vals)
        d = DcDiff()
        self.lib.dc_thumb_diff(ctypes.byref(cur), ctypes.byref(ref), 8, ctypes.byref(d))
        self.assertEqual(d.n, 16)
        self.assertEqual((d.x0, d.y0, d.x1, d.y1), (x0, y0, x1, y1))
        self.assertAlmostEqual(d.frac, 16.0 / DC_TH_N, places=5)

    def test_diff_mean_normalisation_cancels_uniform_brightness_change(self):
        ref = self.uniform_thumb(50)
        cur = self.uniform_thumb(90)  # every pixel brighter by a constant
        d = DcDiff()
        self.lib.dc_thumb_diff(ctypes.byref(cur), ctypes.byref(ref), 8, ctypes.byref(d))
        self.assertEqual(d.n, 0)
        self.assertEqual(d.frac, 0.0)


class CropBoxTests(DustyCoreTestCase):
    def _diff(self, x0, y0, x1, y1, n=None):
        d = DcDiff()
        d.x0, d.y0, d.x1, d.y1 = x0, y0, x1, y1
        d.n = n if n is not None else (x1 - x0 + 1) * (y1 - y0 + 1)
        d.frac = d.n / DC_TH_N
        return d

    def test_no_motion_returns_zero(self):
        d = self._diff(-1, -1, -1, -1, n=0)
        cx = ctypes.c_int(); cy = ctypes.c_int(); side = ctypes.c_int()
        r = self.lib.dc_crop_box(ctypes.byref(d), 800, 600, 0.5, 0.5, 32, ctypes.byref(cx), ctypes.byref(cy), ctypes.byref(side))
        self.assertEqual(r, 0)

    def test_diffuse_fallback(self):
        # Bbox spans almost the whole thumb -> diffuse, full frame fallback.
        d = self._diff(0, 0, DC_TH_W - 1, DC_TH_H - 1)
        cx = ctypes.c_int(); cy = ctypes.c_int(); side = ctypes.c_int()
        r = self.lib.dc_crop_box(ctypes.byref(d), 800, 600, 0.5, 0.5, 32, ctypes.byref(cx), ctypes.byref(cy), ctypes.byref(side))
        self.assertEqual(r, 0)

    def test_padding_and_min_side_and_clamp(self):
        frame_w, frame_h = 800, 600
        # Small bbox near a corner: padding should grow it, min_side floors
        # it, and clamping should keep it fully inside the frame.
        d = self._diff(0, 0, 1, 1)
        cx = ctypes.c_int(); cy = ctypes.c_int(); side = ctypes.c_int()
        r = self.lib.dc_crop_box(ctypes.byref(d), frame_w, frame_h, 0.5, 0.9, 64, ctypes.byref(cx), ctypes.byref(cy), ctypes.byref(side))
        self.assertEqual(r, 1)
        self.assertGreaterEqual(side.value, 64)
        self.assertGreaterEqual(cx.value, 0)
        self.assertGreaterEqual(cy.value, 0)
        self.assertLessEqual(cx.value + side.value, frame_w)
        self.assertLessEqual(cy.value + side.value, frame_h)

    def test_clamp_shrinks_when_frame_too_small(self):
        # A bbox that, once padded/squared, would exceed a tiny frame: side
        # must shrink to fit, never exceeding the smaller frame dimension.
        d = self._diff(15, 10, 25, 20)
        cx = ctypes.c_int(); cy = ctypes.c_int(); side = ctypes.c_int()
        r = self.lib.dc_crop_box(ctypes.byref(d), 50, 40, 0.5, 0.9, 8, ctypes.byref(cx), ctypes.byref(cy), ctypes.byref(side))
        self.assertEqual(r, 1)
        self.assertLessEqual(side.value, 40)
        self.assertGreaterEqual(cx.value, 0)
        self.assertGreaterEqual(cy.value, 0)
        self.assertLessEqual(cx.value + side.value, 50)
        self.assertLessEqual(cy.value + side.value, 40)


class ScoreTests(DustyCoreTestCase):
    def test_boot_and_heartbeat_outrank_detection_and_diff(self):
        boot = self.lib.dc_score(b"boot", -1.0, 0.0, 0.0)
        heartbeat = self.lib.dc_score(b"heartbeat", -1.0, 0.0, 0.0)
        det = self.lib.dc_score(b"motion", 0.9, 0.5, 0.0)
        diff_only = self.lib.dc_score(b"motion", -1.0, 0.9, 0.0)
        self.assertGreater(boot, det)
        self.assertGreater(heartbeat, det)
        self.assertGreater(det, diff_only)

    def test_sharpness_only_breaks_ties(self):
        low_sharp = self.lib.dc_score(b"motion", 0.5, 0.0, 0.0)
        high_sharp = self.lib.dc_score(b"motion", 0.5, 0.0, 1.0)
        self.assertGreater(high_sharp, low_sharp)
        # Sharpness difference must never overtake a real conf/diff gap.
        higher_conf_low_sharp = self.lib.dc_score(b"motion", 0.51, 0.0, 0.0)
        self.assertGreater(higher_conf_low_sharp, high_sharp)

    def test_sharp_above_one_clamped(self):
        at_one = self.lib.dc_score(b"motion", -1.0, 0.5, 1.0)
        above_one = self.lib.dc_score(b"motion", -1.0, 0.5, 5.0)
        self.assertAlmostEqual(at_one, above_one, places=4)


class NightTests(DustyCoreTestCase):
    def _cfg(self, lum_night=12, lum_day=25, confirm=3, margin=2700, probe=1200, period=30):
        c = DcNightCfg()
        c.lum_night = lum_night
        c.lum_day = lum_day
        c.night_confirm_n = confirm
        c.night_margin_s = margin
        c.night_probe_s = probe
        c.period_s = period
        return c

    def test_three_dark_wakes_enter_night(self):
        st = DcNight()
        cfg = self._cfg()
        out = DcNightOut()
        now = 1000
        for i in range(2):
            self.lib.dc_night_step(ctypes.byref(st), 5, now, ctypes.byref(cfg), ctypes.byref(out))
            self.assertEqual(out.entered, 0)
            self.assertEqual(out.in_night, 0)
            self.assertEqual(out.sleep_s, cfg.period_s)
            now += cfg.period_s
        self.lib.dc_night_step(ctypes.byref(st), 5, now, ctypes.byref(cfg), ctypes.byref(out))
        self.assertEqual(out.entered, 1)
        self.assertEqual(out.in_night, 1)
        self.assertEqual(st.in_night, 1)

    def test_first_night_no_history_probes_every_probe_s(self):
        st = DcNight()
        cfg = self._cfg()
        out = DcNightOut()
        now = 0
        for _ in range(3):
            self.lib.dc_night_step(ctypes.byref(st), 5, now, ctypes.byref(cfg), ctypes.byref(out))
            now += cfg.period_s
        # entry (no history)
        self.assertEqual(out.entered, 1)
        self.assertEqual(out.sleep_s, cfg.night_probe_s)
        self.assertEqual(st.slept_toward_dawn, 0)
        now += out.sleep_s
        # subsequent probes, still dark
        for _ in range(3):
            self.lib.dc_night_step(ctypes.byref(st), 5, now, ctypes.byref(cfg), ctypes.byref(out))
            self.assertEqual(out.entered, 0)
            self.assertEqual(out.left, 0)
            self.assertEqual(out.sleep_s, cfg.night_probe_s)
            now += out.sleep_s

    def test_with_history_sleeps_predicted_margin_once_then_probes(self):
        st = DcNight()
        st.hist_n = 3
        st.hist[0] = 36000
        st.hist[1] = 36000
        st.hist[2] = 36000
        st.hist_head = 3
        cfg = self._cfg(margin=2700, probe=1200)
        out = DcNightOut()
        now = 0
        for _ in range(3):
            self.lib.dc_night_step(ctypes.byref(st), 5, now, ctypes.byref(cfg), ctypes.byref(out))
            now += cfg.period_s
        self.assertEqual(out.entered, 1)
        expected_long_sleep = 36000 - 2700
        self.assertEqual(out.sleep_s, expected_long_sleep)
        self.assertEqual(st.slept_toward_dawn, 1)
        now += out.sleep_s
        # next wake: still a single probe at night_probe_s (never the long
        # sleep twice), even though still dark
        self.lib.dc_night_step(ctypes.byref(st), 5, now, ctypes.byref(cfg), ctypes.byref(out))
        self.assertEqual(out.entered, 0)
        self.assertEqual(out.left, 0)
        self.assertEqual(out.sleep_s, cfg.night_probe_s)

    def test_light_on_probe_leaves_with_night_len_and_pushes_history(self):
        st = DcNight()
        cfg = self._cfg()
        out = DcNightOut()
        now = 0
        for _ in range(3):
            self.lib.dc_night_step(ctypes.byref(st), 5, now, ctypes.byref(cfg), ctypes.byref(out))
            now += cfg.period_s
        self.assertEqual(out.entered, 1)
        night_start = st.night_start_s
        now += out.sleep_s
        # still dark for a couple of probes
        for _ in range(2):
            self.lib.dc_night_step(ctypes.byref(st), 5, now, ctypes.byref(cfg), ctypes.byref(out))
            now += out.sleep_s
        # now light
        self.lib.dc_night_step(ctypes.byref(st), 40, now, ctypes.byref(cfg), ctypes.byref(out))
        self.assertEqual(out.left, 1)
        self.assertEqual(out.in_night, 0)
        self.assertEqual(st.in_night, 0)
        self.assertEqual(out.night_len_s, now - night_start)
        self.assertEqual(out.sleep_s, cfg.period_s)
        self.assertEqual(st.hist_n, 1)
        self.assertEqual(st.hist[0], out.night_len_s)

    def test_ring_keeps_seven_and_median_of_last_three(self):
        st = DcNight()
        lengths = [10, 20, 30, 40, 50, 60, 70, 80, 90]  # 9 pushed, ring holds 7
        for L in lengths:
            st.night_start_s = 0
            # Force entry into night then a light wake with a controlled
            # elapsed time by driving the struct directly (this test targets
            # dc_night_predict/ring bookkeeping, exercised through repeated
            # pushes via dc_night_step).
            st.in_night = 1
            cfg = self._cfg()
            out = DcNightOut()
            self.lib.dc_night_step(ctypes.byref(st), 40, L, ctypes.byref(cfg), ctypes.byref(out))
            self.assertEqual(out.left, 1)
            self.assertEqual(out.night_len_s, L)

        self.assertEqual(st.hist_n, DC_NIGHT_HIST)
        last7 = lengths[-7:]
        got = [st.hist[i] for i in range(DC_NIGHT_HIST)]
        # oldest-to-newest order starting at hist_head (ring wrapped)
        oldest_idx = st.hist_head % DC_NIGHT_HIST
        ordered = [got[(oldest_idx + i) % DC_NIGHT_HIST] for i in range(DC_NIGHT_HIST)]
        self.assertEqual(ordered, last7)

        last3 = last7[-3:]
        expected_median = sorted(last3)[1]
        predicted = self.lib.dc_night_predict(ctypes.byref(st))
        self.assertEqual(predicted, expected_median)

    def test_night_hist_json_round_trip(self):
        st = DcNight()
        for v in (100, 200, 300, 400):
            st.hist[st.hist_head] = v
            st.hist_head = (st.hist_head + 1) % DC_NIGHT_HIST
            st.hist_n += 1
        buf = ctypes.create_string_buffer(256)
        r = self.lib.dc_night_hist_to_json(ctypes.byref(st), buf, len(buf))
        self.assertGreater(r, 0)
        js = buf.value.decode()
        self.assertEqual(js, "[100,200,300,400]")

        st2 = DcNight()
        r2 = self.lib.dc_night_hist_from_json(ctypes.byref(st2), js.encode())
        self.assertEqual(r2, 4)
        self.assertEqual(st2.hist_n, 4)
        self.assertEqual([st2.hist[i] for i in range(4)], [100, 200, 300, 400])

        buf2 = ctypes.create_string_buffer(256)
        self.lib.dc_night_hist_to_json(ctypes.byref(st2), buf2, len(buf2))
        self.assertEqual(buf2.value, buf.value)

    def test_night_hist_from_json_parse_error(self):
        st = DcNight()
        r = self.lib.dc_night_hist_from_json(ctypes.byref(st), b"not json")
        self.assertEqual(r, -1)


class CfgTests(DustyCoreTestCase):
    def test_unknown_key_ignored(self):
        c = DcCfg()
        n = self.lib.dc_cfg_apply_json(ctypes.byref(c), b'{"totally_unknown": 5}')
        self.assertEqual(n, 0)

    def test_string_to_int_coercion(self):
        c = DcCfg()
        n = self.lib.dc_cfg_apply_json(ctypes.byref(c), b'{"period_s": "45"}')
        self.assertEqual(n, 1)
        self.assertEqual(c.period_s, 45)

    def test_clamps(self):
        c = DcCfg()
        n = self.lib.dc_cfg_apply_json(
            ctypes.byref(c),
            b'{"gate_pct": 150, "period_s": 1, "night_probe_s": 5}',
        )
        self.assertEqual(n, 3)
        self.assertEqual(c.gate_pct, 100)
        self.assertEqual(c.period_s, 5)
        self.assertEqual(c.night_probe_s, 60)

        c2 = DcCfg()
        n2 = self.lib.dc_cfg_apply_json(ctypes.byref(c2), b'{"gate_pct": -10}')
        self.assertEqual(n2, 1)
        self.assertEqual(c2.gate_pct, 0)

    def test_keep_labels_array(self):
        c = DcCfg()
        n = self.lib.dc_cfg_apply_json(ctypes.byref(c), b'{"keep_labels": ["animal", "person"]}')
        self.assertEqual(n, 1)
        self.assertEqual(c.keep_labels_n, 2)
        self.assertEqual(c.keep_labels[0].value, b"animal")
        self.assertEqual(c.keep_labels[1].value, b"person")
        self.assertEqual(self.lib.dc_cfg_has_label(ctypes.byref(c), b"animal"), 1)
        self.assertEqual(self.lib.dc_cfg_has_label(ctypes.byref(c), b"vehicle"), 0)

    def test_cfg_version_and_return_count(self):
        c = DcCfg()
        n = self.lib.dc_cfg_apply_json(ctypes.byref(c), b'{"cfg": 7, "gate_pct": 50, "unknown": 1}')
        self.assertEqual(n, 2)
        self.assertEqual(c.cfg, 7)
        self.assertEqual(c.gate_pct, 50)

    def test_parse_error_returns_minus_one(self):
        c = DcCfg()
        n = self.lib.dc_cfg_apply_json(ctypes.byref(c), b'{not valid json')
        self.assertEqual(n, -1)
        n2 = self.lib.dc_cfg_apply_json(ctypes.byref(c), b'not even an object')
        self.assertEqual(n2, -1)

    def test_cfg_to_json_round_trips_through_apply(self):
        c = DcCfg()
        js_in = (
            b'{"cfg": 3, "profile": "game_lowpower", "mode": "live", "period_s": 45, '
            b'"interval_n": 90, "heartbeat_s": 1800, "diff_min_frac": 0.05, '
            b'"diff_l_thresh": 10, "gate_pct": 70, "keep_labels": ["animal", "person"], '
            b'"keep_all": false, "audit_n": 15, "debug_frames": true, "debug_max": 250, '
            b'"upload_cap": 500, "lum_night": 15, "lum_day": 30, "night_confirm_n": 4, '
            b'"night_margin_s": 1800, "night_probe_s": 900, "hotspot_join_s": 60, '
            b'"contact_idle_s": 90, "setup_secs": 200, "telemetry_s": 30, '
            b'"led_capture": true, "spool_max_frames": 5000}'
        )
        n = self.lib.dc_cfg_apply_json(ctypes.byref(c), js_in)
        self.assertGreater(n, 0)

        buf = ctypes.create_string_buffer(2048)
        r = self.lib.dc_cfg_to_json(ctypes.byref(c), buf, len(buf))
        self.assertGreater(r, 0)

        c2 = DcCfg()
        n2 = self.lib.dc_cfg_apply_json(ctypes.byref(c2), buf.value)
        self.assertGreater(n2, 0)

        for field in (
            "cfg", "period_s", "interval_n", "heartbeat_s", "diff_l_thresh", "gate_pct",
            "keep_labels_n", "keep_all", "audit_n", "debug_frames", "debug_max", "upload_cap",
            "lum_night", "lum_day", "night_confirm_n", "night_margin_s", "night_probe_s",
            "hotspot_join_s", "contact_idle_s", "setup_secs", "telemetry_s", "led_capture",
            "spool_max_frames",
        ):
            self.assertEqual(getattr(c, field), getattr(c2, field), field)
        self.assertEqual(c.profile, c2.profile)
        self.assertEqual(c.mode, c2.mode)
        self.assertAlmostEqual(c.diff_min_frac, c2.diff_min_frac, places=3)
        for i in range(c.keep_labels_n):
            self.assertEqual(c.keep_labels[i].value, c2.keep_labels[i].value)


class CfgSrcTests(DustyCoreTestCase):
    """docs/phone_app_plan.md §3: the cfg_src/cfg_base state machine
    dusty_config's dusty_config_set_local()/dusty_config_mark_server() are
    built on. Pure logic (no NVS), so it's tested here rather than via a
    hardware/emulated-NVS harness."""

    def test_first_local_edit_from_server_sets_base(self):
        s = DcCfgSrc(cfg_src_is_ble=0, cfg_base=0)
        self.lib.dc_cfg_src_on_local_edit(ctypes.byref(s), 7)  # cfg was 7, about to become 8
        self.assertEqual(s.cfg_src_is_ble, 1)
        self.assertEqual(s.cfg_base, 7)

    def test_second_local_edit_keeps_original_base(self):
        s = DcCfgSrc(cfg_src_is_ble=0, cfg_base=0)
        self.lib.dc_cfg_src_on_local_edit(ctypes.byref(s), 7)  # 7 -> 8, base=7
        self.lib.dc_cfg_src_on_local_edit(ctypes.byref(s), 8)  # 8 -> 9, base stays 7
        self.assertEqual(s.cfg_src_is_ble, 1)
        self.assertEqual(s.cfg_base, 7)

    def test_server_sync_resets_source_and_base(self):
        s = DcCfgSrc(cfg_src_is_ble=1, cfg_base=7)
        self.lib.dc_cfg_src_on_server_sync(ctypes.byref(s), 9)
        self.assertEqual(s.cfg_src_is_ble, 0)
        self.assertEqual(s.cfg_base, 9)

    def test_local_edit_after_a_server_sync_rebases(self):
        s = DcCfgSrc(cfg_src_is_ble=1, cfg_base=7)
        self.lib.dc_cfg_src_on_server_sync(ctypes.byref(s), 9)  # server accepted the push at cfg=9
        self.lib.dc_cfg_src_on_local_edit(ctypes.byref(s), 9)   # a fresh BLE edit: 9 -> 10
        self.assertEqual(s.cfg_src_is_ble, 1)
        self.assertEqual(s.cfg_base, 9)


class MetaTests(DustyCoreTestCase):
    def _base_meta(self):
        m = DcMeta()
        m.ts = 1234567890
        m.seq = 42
        m.w = 1600
        m.h = 1200
        m.v = b"1.0.0"
        m.cfg = 3
        m.ip = b"0.0.0.0"
        m.mode = b"live"
        m.why = b"motion"
        m.diff = 0.125
        m.gate = 0.6
        m.heartbeat = 0
        m.buffered = 1
        m.lum = 55
        m.clock = b"set"
        m.score = 12.5
        m.has_det = 0
        m.det_label = None
        m.det_conf = 0.0
        m.audit = 0
        m.night_s = -1
        return m

    def test_all_standard_keys_present(self):
        m = self._base_meta()
        buf = ctypes.create_string_buffer(1024)
        r = self.lib.dc_meta_build(buf, len(buf), ctypes.byref(m))
        self.assertGreater(r, 0)
        js = buf.value.decode()
        import json
        obj = json.loads(js)
        for key in ("ts", "seq", "w", "h", "v", "cfg", "ip", "mode", "why",
                    "diff", "gate", "heartbeat", "buffered", "lum", "clock", "score"):
            self.assertIn(key, obj)
        self.assertNotIn("det", obj)
        self.assertNotIn("audit", obj)
        self.assertNotIn("night_s", obj)

    def test_det_only_when_has_det(self):
        m = self._base_meta()
        m.has_det = 1
        m.det_label = b"animal"
        m.det_conf = 0.83
        buf = ctypes.create_string_buffer(1024)
        self.lib.dc_meta_build(buf, len(buf), ctypes.byref(m))
        import json
        obj = json.loads(buf.value.decode())
        self.assertEqual(obj["det"], [{"label": "animal", "conf": 0.83}])

    def test_night_s_only_when_nonnegative(self):
        m = self._base_meta()
        m.night_s = 36000
        buf = ctypes.create_string_buffer(1024)
        self.lib.dc_meta_build(buf, len(buf), ctypes.byref(m))
        import json
        obj = json.loads(buf.value.decode())
        self.assertEqual(obj["night_s"], 36000)

    def test_audit_only_when_set(self):
        m = self._base_meta()
        m.audit = 1
        buf = ctypes.create_string_buffer(1024)
        self.lib.dc_meta_build(buf, len(buf), ctypes.byref(m))
        import json
        obj = json.loads(buf.value.decode())
        self.assertTrue(obj["audit"])

    def test_returns_minus_one_when_buffer_too_small(self):
        m = self._base_meta()
        buf = ctypes.create_string_buffer(8)
        r = self.lib.dc_meta_build(buf, len(buf), ctypes.byref(m))
        self.assertEqual(r, -1)


class SpoolNameTests(DustyCoreTestCase):
    def test_spool_path_format_and_parse_round_trip(self):
        buf = ctypes.create_string_buffer(128)
        r = self.lib.dc_spool_path(buf, len(buf), b"/sd", b"spool", 17, 42, b"jpg")
        self.assertGreater(r, 0)
        self.assertEqual(buf.value, b"/sd/spool/17/000042.jpg")

        boot = ctypes.c_uint32()
        seq = ctypes.c_uint32()
        rel = b"17/000042.jpg"
        ok = self.lib.dc_spool_parse(rel, ctypes.byref(boot), ctypes.byref(seq))
        self.assertEqual(ok, 1)
        self.assertEqual(boot.value, 17)
        self.assertEqual(seq.value, 42)

    def test_spool_parse_rejects_garbage(self):
        boot = ctypes.c_uint32()
        seq = ctypes.c_uint32()
        self.assertEqual(self.lib.dc_spool_parse(b"garbage", ctypes.byref(boot), ctypes.byref(seq)), 0)
        self.assertEqual(self.lib.dc_spool_parse(b"", ctypes.byref(boot), ctypes.byref(seq)), 0)

    def test_sidecar_score_extraction(self):
        score = ctypes.c_float()
        why = ctypes.create_string_buffer(32)
        js = b'{"ts":1,"seq":2,"why":"motion","score":12.34}'
        r = self.lib.dc_sidecar_score(js, ctypes.byref(score), why, len(why))
        self.assertEqual(r, 1)
        self.assertAlmostEqual(score.value, 12.34, places=2)
        self.assertEqual(why.value, b"motion")

    def test_sidecar_score_missing(self):
        score = ctypes.c_float()
        js = b'{"ts":1,"why":"motion"}'
        r = self.lib.dc_sidecar_score(js, ctypes.byref(score), None, 0)
        self.assertEqual(r, 0)


class HttpDateTests(DustyCoreTestCase):
    def test_rfc1123_example(self):
        r = self.lib.dc_parse_http_date(b"Sun, 06 Nov 1994 08:49:37 GMT")
        self.assertEqual(r, 784111777)

    def test_failure_returns_minus_one(self):
        self.assertEqual(self.lib.dc_parse_http_date(b"not a date"), -1)
        self.assertEqual(self.lib.dc_parse_http_date(b""), -1)
        self.assertEqual(self.lib.dc_parse_http_date(None), -1)


class FwVerTests(DustyCoreTestCase):
    def test_should_install_matrix(self):
        L = self.lib.dc_fw_should_install
        self.assertEqual(L(b"1.2.0", b"1.1.0", b""), 1)          # newer than running
        self.assertEqual(L(b"1.1.0", b"1.1.0", b""), 0)          # same as running
        self.assertEqual(L(b"1.2.0", b"1.1.0", b"1.2.0"), 0)     # known bad
        self.assertEqual(L(b"", b"1.1.0", b""), 0)               # empty remote
        self.assertEqual(L(None, b"1.1.0", b""), 0)              # null remote
        self.assertEqual(L(b"1.2.0", b"1.1.0", None), 1)         # null bad, still installable


if __name__ == "__main__":
    unittest.main()
