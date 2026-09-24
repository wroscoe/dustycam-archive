"""Host-side stubs so the MicroPython modules import under CPython (import from a test as `boardstubs`).
Board modules (sensor, image, machine, network, secrets) are replaced by
minimal fakes; pure logic (config merge, spool naming, meta building,
bundling) is what the tests exercise."""
import sys
import types
from pathlib import Path

COMMON = Path(__file__).resolve().parents[1] / 'micropython'
sys.path.insert(0, str(COMMON))


def _stub(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m


class _Pin:
    IN = 0
    PULL_UP = 1
    board = types.SimpleNamespace(SW=1, CHG=2)

    def __init__(self, *a, **k):
        pass

    def value(self):
        return 1


class _Img:
    def __init__(self, *a, **k):
        pass


_stub('sensor', RGB565=1, GRAYSCALE=2, JPEG=3, VGA=4, WQXGA2=5,
      reset=lambda: None, set_pixformat=lambda *a: None, set_framesize=lambda *a: None,
      skip_frames=lambda **k: None, width=lambda: 640, height=lambda: 480, snapshot=lambda: _Img(),
      shutdown=lambda *a, **k: None, sleep=lambda *a, **k: None)
_stub('image', Image=_Img)


class _RTC:
    _last_dt = None            # class-level: machine.RTC() gives a fresh instance each call, real RTC state doesn't

    def wakeup(self, *a, **k):
        pass

    def datetime(self, *a):
        """(year, month, day, weekday, hours, minutes, seconds, subseconds).
        Set-only stub (no arg -> returns the last value set, or None)."""
        if a:
            _RTC._last_dt = a[0]
            return None
        return _RTC._last_dt


# reset_cause() values: real STM32 MicroPython numbering (PLAN.md §0: bench-
# verified DEEPSLEEP_RESET == 4). Tests that exercise wake_cause() monkeypatch
# machine.reset_cause directly rather than relying on this default.
_stub('machine', Pin=_Pin, LED=lambda *a: None, reset=lambda: None,
      RTC=_RTC, deepsleep=lambda *a, **k: None, lightsleep=lambda *a, **k: None,
      reset_cause=lambda: 1, PWRON_RESET=1, HARD_RESET=2, WDT_RESET=3,
      DEEPSLEEP_RESET=4, SOFT_RESET=5)
class _WLAN:
    """network.WLAN(...) stub, shared by contact.py's join scan and
    wakecycle.py's bench_contact_n scan. isconnected() stays False (the
    default tests exercise "join fails, no phone" -- there is no `connect`
    method either, so a real join attempt raises and is caught, same as
    before); scan_results is a class attribute (one radio, shared by every
    WLAN() instance, like the board) -- tests set it with
    monkeypatch.setattr(network.WLAN, 'scan_results', [(b'ssid', ...), ...])."""
    scan_results = []

    def __init__(self, *a):
        pass

    def ifconfig(self):
        return ('10.0.0.5',)

    def isconnected(self):
        return False

    def status(self, *a):
        return -50

    def active(self, *a):
        return False

    def deinit(self):
        pass

    def scan(self):
        return list(_WLAN.scan_results)


_stub('network', STA_IF=0, WLAN=_WLAN)
_stub('secrets', DEVICE='testcam', SERVER_HOST='127.0.0.1', SERVER_PORT=1, SERVER_TLS=False,
      BLOB_TOKEN='t', OTA_PORT=8266, OTA_TOKEN='x', WIFI_SSID='s', WIFI_PASS='p')

# time.ticks_* exist only on MicroPython
import time as _time
if not hasattr(_time, 'ticks_ms'):
    _time.ticks_ms = lambda: int(_time.time() * 1000)
    _time.ticks_diff = lambda a, b: a - b
    _time.sleep_ms = lambda ms: None
