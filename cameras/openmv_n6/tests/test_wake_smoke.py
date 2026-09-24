"""Host smoke run of the bundled N6 app's game_lowpower wake cycle.

Builds software/build/app.py-equivalent with bundle.py, execs it under the
shared board stubs plus a fake sensor/image just rich enough for board.py,
and runs several wakes end to end: first cold boot (contact attempt that
fails fast, no phone), boot frame, quiet wake, motion wake with debug
frames. No board needed. Everything the wake touches on disk (spool,
persist file, night file, flag file) is redirected into tmp_path.
"""
import json
import os
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMMON = HERE.parents[1] / 'common'
sys.path.insert(0, str(COMMON / 'tests'))
import boardstubs  # noqa: E402,F401
sys.path.insert(0, str(COMMON / 'micropython'))
from bundle import bundle  # noqa: E402


class FakeStats:
    def __init__(self, l):
        self.l_mean = l            # fw 5.0: int field, not a method


class FakeHist:
    def __init__(self, changed_frac):
        self._f = changed_frac

    def l_bins(self):
        bins = [0.0] * 256
        bins[0] = 1.0 - self._f
        bins[40] = self._f
        return bins


class FakeImg:
    """Just what board.py / wakecycle.py call on a preview image."""
    def __init__(self, w=640, h=400, lum=60, level=100):
        self._w, self._h, self._lum, self.level = w, h, lum, level
        self.changed = 0.0

    def width(self):
        return self._w

    def height(self):
        return self._h

    def get_statistics(self):
        return FakeStats(self._lum)

    def copy(self, x_scale=1.0, y_scale=1.0, copy_to_fb=False, roi=None):
        t = FakeImg(int(self._w * x_scale), int(self._h * y_scale), self._lum, self.level)
        t.changed = self.changed
        return t

    def to_grayscale(self):
        return self

    def bytearray(self):
        return bytes([self.level & 0xFF]) * (self._w * self._h)

    def difference(self, other):
        self.changed = 0.0 if other.level == self.level else 0.3
        return self

    def get_histogram(self):
        return FakeHist(self.changed)

    def find_blobs(self, *a, **k):
        if not self.changed:
            return []
        r = (10, 5, 20, 15)
        return [types.SimpleNamespace(rect=lambda r=r: r)]

    def to_jpeg(self, quality=85):
        return FakeImg(self._w, self._h, self._lum, self.level)

    def crop(self, roi=None, copy=True):
        return self

    def scale(self, x_size=96, y_size=96):
        return self


def _install_fakes(tmp_path):
    scene = {'level': 100, 'lum': 60, 'reset_cause': 1}
    sensor = sys.modules['sensor']
    sensor.snapshot = lambda: FakeImg(lum=scene['lum'], level=scene['level'])
    sensor.shutdown = lambda *a: None
    sensor.reset = lambda: None
    sensor.width = lambda: 640
    sensor.height = lambda: 400
    sensor.HD = 9
    image = sys.modules['image']
    image.Image = lambda w=80, h=50, fmt=None, buffer=None, buf=None: _from_bytes(w, h, buffer or buf)
    image.RGB565 = 1
    machine = sys.modules['machine']
    machine.DEEPSLEEP_RESET, machine.PWRON_RESET, machine.SOFT_RESET = 4, 1, 0
    machine.reset_cause = lambda: scene['reset_cause']
    machine.deepsleep = lambda *a: None
    machine.lightsleep = lambda *a: None
    import time
    time.ticks_ms = lambda: 1000            # ms since boot on the board; awake time per wake
    time.ticks_diff = lambda a, b: a - b
    return scene


def _from_bytes(w, h, b):
    img = FakeImg(w, h)
    img.level = b[0] if b else 0
    return img


def _load_bundle(tmp_path):
    src = bundle(HERE.parent)
    for m in ('board', 'app', 'secrets'):
        sys.modules.pop(m, None)
    sys.modules['secrets'] = types.SimpleNamespace(DEVICE='n6test', SERVER_HOST='127.0.0.1', SERVER_PORT=1,
                                                   SERVER_TLS=False, BLOB_TOKEN='t', OTA_PORT=8266,
                                                   OTA_TOKEN='x', WIFI_SSID='s', WIFI_PASS='p')
    g = {'__name__': 'n6bundle'}
    exec(compile(src, 'app.py', 'exec'), g)
    root = tmp_path
    g['SPOOL_DIR'] = str(root / 'spool')
    g['DEBUG_DIR'] = str(root / 'debug')
    g['THUMB_FILE'] = str(root / 'spool' / 'thumb.bin')
    g['WAKELOG'] = str(root / 'wakelog.txt')
    g['WAKELOG_ROTATED'] = str(root / 'wakelog.1.txt')
    g['PERSIST_FILE'] = str(root / 'persist.json')
    g['NIGHT_FILE'] = str(root / 'night.json')
    g['BOOT_COUNT_FILE'] = str(root / 'boot_count.txt')
    g['WAKE_CYCLE_FLAG'] = str(root / 'wake_cycle')
    g['CFG_FILE'] = str(root / 'config.json')
    g['FW_PENDING'] = str(root / 'fw_pending.txt')
    g['FW_BAD'] = str(root / 'fw_bad.txt')
    g['MODEL_PENDING'] = str(root / 'model_pending.txt')
    g['MODEL_BAD'] = str(root / 'model_bad.txt')
    g['GATE_MODEL'] = str(root / 'gate.tflite')      # absent: gate fails open
    g['TUNING']['hotspot_join_s'] = 1
    g['TUNING']['contact_idle_s'] = 1
    g['TUNING']['preview_settle_ms'] = 0
    g['TUNING']['debug_frames'] = False           # the stamped default may be on for tuning; the test turns it on itself
    g['TUNING']['keep_all'] = False
    g['capture'] = lambda: (b'\xff\xd8' + b'x' * 5000, 1280, 800)
    g['restore_preview'] = lambda: None
    g['board_button_down'] = lambda: False
    return g


def test_wake_cycle_end_to_end(tmp_path):
    scene = _install_fakes(tmp_path)
    g = _load_bundle(tmp_path)
    rests = []
    g['board_rest'] = lambda ms: rests.append(ms)
    spool = tmp_path / 'spool'

    # wake 1: cold boot -> first contact attempt (no phone: join fails fast), flag written;
    # the sensor is initialised before the contact so the setup page can stream
    inits = []
    real_init = g['preview_init']
    g['preview_init'] = lambda settle=1500: inits.append(settle) or real_init(settle)
    scene['reset_cause'] = 1
    g['game_run'](lambda: None)
    assert inits, 'preview_init must run before a contact'
    assert rests == [g['TUNING']['period_s'] * 1000]
    assert (tmp_path / 'wake_cycle').exists()
    st = json.loads((tmp_path / 'persist.json').read_text())
    assert st['flags'] & 2 == 0                      # join failed: first contact not done
    assert (tmp_path / 'boot_count.txt').read_text() == '1'

    # wake 2: deep-sleep wake, no reference -> boot frame recorded
    scene['reset_cause'] = 4
    g['game_run'](lambda: None)
    frames = sorted(spool.glob('*/*.jpg'))
    assert len(frames) == 1 and frames[0].parent.name == '1'
    meta = json.loads(frames[0].with_suffix('.json').read_text())
    for k in ('ts', 'seq', 'w', 'h', 'v', 'cfg', 'ip', 'mode', 'why', 'diff', 'gate',
              'heartbeat', 'buffered', 'score', 'clock', 'lum', 'det'):
        assert k in meta, k
    assert meta['why'] == 'boot' and meta['clock'] == 'none' and meta['w'] == 1280
    assert (spool / 'thumb.bin').exists()
    assert (tmp_path / 'boot_count.txt').read_text() == '1'   # deep wakes do not count as boots

    # wake 3: same scene -> nothing recorded
    g['game_run'](lambda: None)
    assert len(list(spool.glob('*/*.jpg'))) == 1
    st = json.loads((tmp_path / 'persist.json').read_text())
    assert st['wake_n'] == 2 and st['awake_ms'] > 0 and st['crash_n'] == 0

    # wake 4: scene changed + debug frames on -> motion frame (gate open: no model) + debug preview
    scene['level'] = 200
    g['CFG']['debug_frames'] = True
    (tmp_path / 'config.json').write_text(json.dumps({'cfg': 1, 'debug_frames': True}))
    g['game_run'](lambda: None)
    frames = sorted(spool.glob('*/*.jpg'))
    assert len(frames) == 2
    meta = json.loads(frames[1].with_suffix('.json').read_text())
    assert meta['why'] == 'motion' and meta['diff'] > 0.02 and meta['det'] == []
    debug = list((tmp_path / 'debug').glob('*/*.json'))
    assert len(debug) == 1 and json.loads(debug[0].read_text())['why'] == 'watch'
    log = [l for l in (tmp_path / 'wakelog.txt').read_text().splitlines() if 'why=' in l]
    assert len(log) == 3 and 'why=motion' in log[-1]     # plus the contact lines


def test_night_wake_sleeps_without_recording(tmp_path):
    scene = _install_fakes(tmp_path)
    g = _load_bundle(tmp_path)
    rests = []
    g['board_rest'] = lambda ms: rests.append(ms)
    scene['reset_cause'] = 4
    scene['lum'] = 2                                  # 2 * 2.55 -> 5 < lum_night 12
    for _ in range(3):                                # night_confirm_n = 3
        g['game_run'](lambda: None)
    assert rests[-1] == 1200 * 1000                   # night_probe_s: no history yet
    assert len(list((tmp_path / 'spool').glob('*/*.jpg'))) == 1   # only the boot frame before night was confirmed
    assert json.loads((tmp_path / 'persist.json').read_text())['night'] == 1
    scene['lum'] = 40                                 # 102 >= lum_day 25 -> morning frame
    g['game_run'](lambda: None)
    frames = sorted((tmp_path / 'spool').glob('*/*.json'))
    assert len(frames) == 2 and 'night_s' in json.loads(frames[1].read_text())


# --- cold boot = contact (wakecycle._one_wake); bench_contact_n ------------

def test_cold_boot_after_first_contact_done_still_runs_a_contact(tmp_path):
    """PWR button off/on (or any power-on/watchdog reset) is the field
    gesture for a contact -- it must fire even long after the first-ever
    contact, unlike 'soft' resets (mpremote, an OTA reboot)."""
    scene = _install_fakes(tmp_path)
    g = _load_bundle(tmp_path)
    g['board_rest'] = lambda ms: None
    calls = []
    g['_run_contact'] = lambda st, cause: calls.append(cause)
    g['persist_save']({'wake_n': 40, 'flags': 2})   # FLAG_FIRST_CONTACT_DONE already set
    scene['reset_cause'] = 1                        # PWRON_RESET -> 'cold'
    g['game_run'](lambda: None)
    assert calls == ['cold']


def test_soft_boot_after_first_contact_done_does_not_run_a_contact(tmp_path):
    scene = _install_fakes(tmp_path)
    g = _load_bundle(tmp_path)
    g['board_rest'] = lambda ms: None
    calls = []
    g['_run_contact'] = lambda st, cause: calls.append(cause)
    g['persist_save']({'wake_n': 40, 'flags': 2})   # FLAG_FIRST_CONTACT_DONE already set
    scene['reset_cause'] = 0                        # SOFT_RESET -> 'soft'
    g['game_run'](lambda: None)
    assert calls == []


def test_bench_contact_n_runs_a_contact_when_the_lan_is_visible(tmp_path, monkeypatch):
    import network
    scene = _install_fakes(tmp_path)
    g = _load_bundle(tmp_path)
    g['board_rest'] = lambda ms: None
    calls = []
    g['_run_contact'] = lambda st, cause: calls.append(cause)
    g['TUNING']['bench_contact_n'] = 3
    g['persist_save']({'wake_n': 3, 'flags': 2})    # first contact done, cause 'deep' below
    monkeypatch.setattr(sys.modules['secrets'], 'LAN_SSID', 'homenet', raising=False)
    monkeypatch.setattr(network.WLAN, 'scan_results', [(b'homenet', b'', 1, -50, 3, 0)])
    scene['reset_cause'] = 4                        # 'deep': no other trigger fires
    g['game_run'](lambda: None)
    assert calls == ['deep']
    log = (tmp_path / 'wakelog.txt').read_text()
    assert 'bench-contact: lan visible' in log
    g['game_run'](lambda: None)                     # the very next wake must NOT contact again
    assert calls == ['deep']
    assert json.loads((tmp_path / 'persist.json').read_text())['wake_n'] == 5


def test_bench_contact_n_skips_when_the_lan_is_absent(tmp_path, monkeypatch):
    import network
    scene = _install_fakes(tmp_path)
    g = _load_bundle(tmp_path)
    g['board_rest'] = lambda ms: None
    calls = []
    g['_run_contact'] = lambda st, cause: calls.append(cause)
    g['TUNING']['bench_contact_n'] = 3
    g['persist_save']({'wake_n': 3, 'flags': 2})
    monkeypatch.setattr(sys.modules['secrets'], 'LAN_SSID', 'homenet', raising=False)
    monkeypatch.setattr(network.WLAN, 'scan_results', [])   # no LAN in range
    scene['reset_cause'] = 4
    g['game_run'](lambda: None)
    assert calls == []
    log = (tmp_path / 'wakelog.txt').read_text()
    assert 'bench-contact: lan absent' in log


def test_bench_contact_n_disabled_by_default_does_nothing(tmp_path):
    """bench_contact_n = 0 (the stamped default): no scan, no contact, even
    on a wake_n that would otherwise match."""
    scene = _install_fakes(tmp_path)
    g = _load_bundle(tmp_path)
    g['board_rest'] = lambda ms: None
    calls = []
    g['_run_contact'] = lambda st, cause: calls.append(cause)
    g['TUNING']['bench_contact_n'] = 0            # the stamped default may be >0 at the bench; the test wants it off
    g['persist_save']({'wake_n': 3, 'flags': 2})
    scene['reset_cause'] = 4
    g['game_run'](lambda: None)
    assert calls == []
    log = (tmp_path / 'wakelog.txt').read_text()
    assert 'bench-contact' not in log
