"""Host tests for the N6 app: board facts, meta builder, tuning keys, and
the game_lowpower additions to board.py (wake_cause, board_lum, board_thumb_
diff, SLEEP_MODE/THUMB dims). Runs the shared stubs from
runtime/tests/boardstubs.py.

Note: app.py's `from board import *` etc. still work under the monitor
profile's test path (test_meta_has_every_standard_key); the bundle itself
(camera.toml [bundle] order, tested in test_bundle_order_is_sane below) also
needs package A's common modules (night/rank/gamespool/persist/led/judge/
contact/wakecycle), which this file does not import directly.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'runtime' / 'tests'))
import boardstubs  # noqa: E402  (installs the board stubs)
sys.path.insert(0, str(HERE.parent / 'software' / 'app'))
sys.path.insert(0, str(HERE.parents[2] / 'runtime' / 'micropython'))

for _m in ('board', 'app'):            # per-camera modules: never reuse another camera's
    sys.modules.pop(_m, None)
import board  # noqa: E402
import config  # noqa: E402
import app  # noqa: E402

STANDARD_META = {'ts', 'seq', 'w', 'h', 'v', 'cfg', 'ip', 'mode', 'why', 'diff', 'gate', 'heartbeat', 'buffered'}


def test_board_facts():
    assert board.CAPTURE_MODE == 'rgb565'            # the N6 CSI rejects JPEG output
    assert board.TUNING['capture_framesize'] == 'HD'  # 1280x800 native
    assert board.APP_VERSION.endswith('-n6')


def test_meta_has_every_standard_key(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'CFG_FILE', str(tmp_path / 'c.json'))
    config.cfg_init(board.TUNING)
    m = json.loads(app.build_meta(1700000000, 2, 1280, 800, 'motion', 0.0071, False))
    assert set(m) == STANDARD_META and m['v'] == board.APP_VERSION and m['gate'] == board.TUNING['diff_min_frac']


def test_tuning_keys_match_manifest():
    import tomllib
    manifest = tomllib.loads((HERE.parent / 'camera.toml').read_text())
    assert set(manifest['tuning']) == set(board.TUNING)


def test_capabilities_include_game_lowpower_set():
    import tomllib
    manifest = tomllib.loads((HERE.parent / 'camera.toml').read_text())
    caps = set(manifest['capabilities'])
    assert {'deep_sleep', 'sd', 'light', 'model', 'button', 'hotspot'} <= caps
    # existing capabilities are kept, not replaced
    assert {'preview', 'focus_score', 'motion', 'full_res', 'spool',
            'pull_config', 'pull_firmware', 'push_firmware', 'setup_mode', 'shoot'} <= caps


def test_bundle_order_is_sane():
    import tomllib
    manifest = tomllib.loads((HERE.parent / 'camera.toml').read_text())
    order = manifest['bundle']['order']
    assert order[0] == 'board.py'
    assert order[-1] == 'common:app'
    idx = {e: i for i, e in enumerate(order)}
    # night.py/rank.py are pure (a state dict in, a result out) so they need
    # nothing bundled before them; persist.py (the backup-register state) and
    # led.py (the LED language) are read/driven directly by judge, contact
    # and wakecycle, so must precede those.
    for earlier in ('common:persist', 'common:led'):
        for later in ('common:judge', 'common:contact', 'common:wakecycle'):
            assert idx[earlier] < idx[later], (earlier, later)
    # wakecycle.py orchestrates one wake of night/rank/gamespool/judge/contact
    for earlier in ('common:night', 'common:rank', 'common:gamespool', 'common:persist',
                     'common:led', 'common:judge', 'common:contact'):
        assert idx[earlier] < idx['common:wakecycle'], earlier
    assert idx['common:wakecycle'] < idx['common:app']


# --- game_lowpower board.py additions ---------------------------------------

def test_sleep_mode_and_thumb_dims():
    assert board.SLEEP_MODE in ('deep', 'light')
    assert board.SLEEP_MODE == 'deep'          # the bench-proven default (PLAN §0)
    assert (board.THUMB_W, board.THUMB_H) == (80, 50)
    assert board.GATE_MODEL == '/flash/gate.tflite'


def test_wake_cause_maps_reset_cause(monkeypatch):
    import machine

    monkeypatch.setattr(machine, 'reset_cause', lambda: machine.DEEPSLEEP_RESET)
    assert board.wake_cause() == 'deep'
    monkeypatch.setattr(machine, 'reset_cause', lambda: machine.SOFT_RESET)
    assert board.wake_cause() == 'soft'
    for cause_name in ('PWRON_RESET', 'HARD_RESET', 'WDT_RESET'):
        monkeypatch.setattr(machine, 'reset_cause', lambda cn=cause_name: getattr(machine, cn))
        assert board.wake_cause() == 'cold'


class _StatsInt:
    def __init__(self, l_mean):
        self.l_mean = l_mean


class _StatsMethod:
    def __init__(self, l_mean):
        self._l_mean = l_mean

    def l_mean(self):
        return self._l_mean


class _FakeImg:
    def __init__(self, stats):
        self._stats = stats

    def get_statistics(self):
        return self._stats


def test_board_lum_scales_int_field_0_100_to_0_255():
    # OpenMV LAB stats: L is 0-100 on the N6; board_lum scales x2.55.
    assert board.board_lum(_FakeImg(_StatsInt(0))) == 0
    assert board.board_lum(_FakeImg(_StatsInt(100))) == 255
    assert board.board_lum(_FakeImg(_StatsInt(50))) == round(50 * 2.55)


def test_board_lum_handles_callable_field():
    assert board.board_lum(_FakeImg(_StatsMethod(40))) == round(40 * 2.55)


def test_board_lum_fails_open_to_zero():
    class _Bad:
        def get_statistics(self):
            raise OSError('sensor busy')
    assert board.board_lum(_Bad()) == 0


class _FakeHist:
    def __init__(self, bins):
        self._bins = bins

    def l_bins(self):
        return self._bins


class _FakeBlob:
    def __init__(self, rect):
        self._rect = rect

    def rect(self):
        return self._rect


class _FakeWork:
    """The result of thumb.copy() after .difference(ref) — get_histogram()
    and find_blobs() are what board_thumb_diff reads from it."""
    def __init__(self, bins, blobs):
        self._bins = bins
        self._blobs = blobs

    def difference(self, other):
        pass

    def get_histogram(self):
        return _FakeHist(self._bins)

    def find_blobs(self, thresholds, merge=True, pixels_threshold=2):
        return self._blobs


class _FakeThumb:
    def __init__(self, work):
        self._work = work

    def copy(self):
        return self._work


def test_board_thumb_diff_no_ref_is_full_frac_no_bbox():
    frac, bbox = board.board_thumb_diff(None, object(), 8)
    assert frac == 1.0 and bbox is None


def test_board_thumb_diff_frac_and_largest_bbox():
    # 10 bins (0..9 luminance-delta buckets); l_thresh=8 sums bins[8:] = 0.01+0.02
    bins = [0.5, 0.1, 0.1, 0.1, 0.1, 0.05, 0.02, 0.01, 0.01, 0.02]
    blobs = [_FakeBlob((5, 5, 4, 4)), _FakeBlob((10, 10, 20, 20)), _FakeBlob((1, 1, 2, 2))]
    work = _FakeWork(bins, blobs)
    ref_bytes = bytes(board.THUMB_W * board.THUMB_H)   # persisted reference, as gs_thumb_load() returns
    frac, bbox = board.board_thumb_diff(ref_bytes, _FakeThumb(work), 8)
    assert abs(frac - 0.03) < 1e-9
    assert bbox == (10, 10, 20, 20)     # the largest-area blob's rect()


def test_board_thumb_diff_no_blobs_gives_none_bbox():
    work = _FakeWork([1.0] + [0.0] * 9, [])
    ref_bytes = bytes(board.THUMB_W * board.THUMB_H)
    frac, bbox = board.board_thumb_diff(ref_bytes, _FakeThumb(work), 8)
    assert bbox is None


def test_board_thumb_diff_fails_open():
    class _Bad:
        def copy(self):
            raise OSError('fb busy')
    ref_bytes = bytes(board.THUMB_W * board.THUMB_H)
    frac, bbox = board.board_thumb_diff(ref_bytes, _Bad(), 8)
    assert frac == 1.0 and bbox is None


def test_board_button_down_reads_sw_active_low():
    # boardstubs' _Pin.value() always returns 1 (released, active-low idle)
    assert board.board_button_down() is False
