"""board: facts and stamped defaults for the OpenMV N6 (STM32N657).
Bundled first (see camera.toml [bundle]); the shared modules read these
names at call time.

Firmware 5.0.0 / MicroPython 1.28 (v1.28.0-49): the legacy `sensor` API
still works; `machine.LED`, `ssl.SSLContext`, `json` present; pins
`SW` (user button, active-low), `CHG` (active-low charging), `BAT_ADC`,
`LED_RED/GREEN/BLUE`, `ONOFF` (PA2, WKUP2). Sensor: CSI camera, native HD
1280x800 (VGA is 640x400, QVGA 320x200 — 16:10, not 4:3); the CSI
**rejects JPEG and YUV422 pixformats**, so captures are RGB565 at HD +
software JPEG (CAPTURE_MODE = 'rgb565'; a 1280x800 RGB565 frame is 2 MB in
the fb). Framebuffer pool 32 MB (20 MiB usable), fb cost = w*h*2 for every
format (sarg: sargbench1 lessons, 2026-08).

Bench facts for `game_lowpower` (PLAN.md §0, proven 2026-09-13):
`machine.deepsleep()` is STM32 standby; `machine.RTC().wakeup(ms)` wakes it
with `reset_cause() == machine.DEEPSLEEP_RESET`; the RTC and the TAMP
backup registers survive standby; `wakeup(43200000)` (12 h) accepted; USB
drops ~1.1 s after `deepsleep()` and re-enumerates ~2 s after the wake;
`ticks_ms()` ~= 1.07 s when main.py starts; `ml.Model()` loads a ROM model;
`sensor.shutdown()`/`sensor.sleep()` and `network.WLAN.deinit()` exist; no
SD card fitted (`/sdcard` absent, `pyb.SDCard` present). Open (needs the
bench, PLAN §8): standby current, whether `SW` wakes standby (not a
documented WKUP pin — `ONOFF`/PA2 is WKUP2, `SW` is not), what the firmware
does with `main.py`/USB mass storage once a card is fitted, RTC drift.

Deny list (hard-hangs the MCU, bypasses rollback): pyb.ADCAll /
read_core_temp while streaming; sensor.set_frame_callback(); cpufreq
unproven — none of these are called.
BATT_DIVIDER 1.5 is inferred, not measured: batt_v is indicative only.
"""
import machine
import network
import sensor
import time

try:
    import image
except ImportError:                          # not present in the host test stub
    image = None

APP_VERSION = '2.2.2-n6'

# --- tuning: stamped by tools/dustygen from camera.toml [tuning] overridden by
# ~/.dusty/config.toml [camera.openmv_n6]; served at /config/n6cam and pulled
# at runtime (config.py).
TUNING = {'profile': 'game_lowpower', 'period_s': 10, 'interval_n': 120, 'heartbeat_s': 300, 'diff_min_frac': 0.02, 'diff_l_thresh': 24, 'gate_pct': 60, 'keep_labels': ['animal', 'person'], 'keep_all': False, 'audit_n': 20, 'debug_frames': True, 'debug_max': 500, 'upload_cap': 1000, 'lum_night': 12, 'lum_day': 25, 'night_confirm_n': 3, 'night_margin_s': 2700, 'night_probe_s': 1200, 'hotspot_join_s': 90, 'contact_idle_s': 120, 'setup_secs': 240, 'telemetry_s': 60, 'led_capture': True, 'spool_max_frames': 20000, 'preview_settle_ms': 500, 'capture_framesize': 'HD', 'capture_settle_ms': 400, 'wifi_linger_s': 0, 'bench_contact_n': 20}
# --- end tuning

PREVIEW_FRAMESIZE = 'VGA'         # 640x400 on this sensor
PREVIEW_PIXFORMAT = 'GRAYSCALE'   # game_lowpower's Watch stage (wakecycle.py) samples
                                   # GRAYSCALE at PREVIEW_FRAMESIZE directly — cheaper for
                                   # board_lum()/board_thumb() than RGB565; the monitor
                                   # profile's live preview (camera.py: preview_init())
                                   # still sets RGB565 for the setup-mode stream.
JPEG_QUALITY = 85
CAPTURE_MODE = 'rgb565'           # CSI has no JPEG output: RGB565 at HD + to_jpeg
BUTTON_NAMES = ('SW',)
LED_NAME = 'LED_BLUE'
MAX_PENDING = 2000
WIFI_RETRY_S = 30
BATT_DIVIDER = 1.5                # inferred; verify against a real pack

SLEEP_MODE = 'deep'               # keep 'deep': bench 2026-09-13 showed 'light' (machine.lightsleep) never returns on fw 5.0.0
                                  # 'deep' = RTC wakeup + machine.deepsleep (STM32 standby,
                                   # never returns); 'light' = machine.lightsleep(ms) fallback
                                   # (STOP, RAM kept) if the bench (PLAN §8 gate 2) shows SW
                                   # cannot wake standby and a button wake is required.
THUMB_W, THUMB_H = 80, 50         # game_lowpower motion-diff thumbnail (wakecycle.py Watch)
GATE_MODEL = '/flash/gate.tflite'  # USB-copied, not OTA'd (software/host/convert_gate.sh)

try:
    _bat_adc = machine.ADC(machine.Pin.board.BAT_ADC)
except (AttributeError, ValueError, OSError):
    _bat_adc = None
try:
    _chg_pin = machine.Pin(machine.Pin.board.CHG, machine.Pin.IN, machine.Pin.PULL_UP)
except (AttributeError, ValueError, OSError):
    _chg_pin = None
try:
    _sw_pin = machine.Pin(machine.Pin.board.SW, machine.Pin.IN, machine.Pin.PULL_UP)
except (AttributeError, ValueError, OSError):
    _sw_pin = None


def board_sensors():
    """Sense stage for this board: battery volts (8-sample mean) + charging."""
    vals = {}
    if _bat_adc is not None:
        try:
            # BAT_ADC reads ~550 or the real value (~55000) in alternating bursts a
            # few hundred ms long (the divider is switched under the ADC, REPL-verified
            # 2026-09-03): take the max of samples spread over ~0.6 s.
            import time
            raw = 0
            for _ in range(5):
                raw = max(raw, _bat_adc.read_u16())
                time.sleep_ms(120)
            vals['batt_v'] = round(raw / 65535 * 3.3 * BATT_DIVIDER, 3)
        except (OSError, ValueError):
            pass
    if _chg_pin is not None:
        try:
            vals['charging'] = 0 if _chg_pin.value() else 1
        except (OSError, ValueError):
            pass
    return vals


# --- game_lowpower: wake, sleep and the motion-diff thumbnail --------------
# wakecycle.py (runtime/micropython, package A) calls these by name;
# it never touches machine/sensor/image directly so a second board can swap
# in different hardware behind the same contract.

_RESET_CAUSE_NAMES = {
    'DEEPSLEEP_RESET': 'deep',
    'SOFT_RESET': 'soft',
}   # PWRON_RESET, HARD_RESET, WDT_RESET (and anything unrecognised) -> 'cold'


def wake_cause():
    """'deep' (RTC-wakeup from board_rest's machine.deepsleep()), 'soft'
    (a soft reset, e.g. after fw_boot_check's rollback reboot), or 'cold'
    (power-on, hard reset, watchdog — treated as a fresh boot)."""
    try:
        cause = machine.reset_cause()
    except AttributeError:
        return 'cold'
    for name, tag in _RESET_CAUSE_NAMES.items():
        if cause == getattr(machine, name, object()):
            return tag
    return 'cold'


def board_rest(ms):
    """Rest stage (wakecycle.py): sensor + radio down, then sleep for `ms`.
    SLEEP_MODE == 'deep' (default): RTC wakeup + machine.deepsleep() — STM32
    standby, RAM lost, this call never returns; main.py reruns from the top
    on wake with reset_cause() == DEEPSLEEP_RESET. SLEEP_MODE == 'light':
    machine.lightsleep(ms) (STOP, RAM kept) and this call returns — the
    fallback if the bench (PLAN §8 gate 2) shows SW cannot wake standby."""
    try:
        sensor.shutdown(True)
    except Exception as e:
        print('board_rest: sensor.shutdown failed', repr(e))
    try:
        wlan = network.WLAN(network.STA_IF)
        if wlan.active():
            wlan.deinit()
    except Exception as e:
        print('board_rest: wlan deinit failed', repr(e))
    ms = int(ms)
    if SLEEP_MODE == 'light':
        time.sleep_ms(50)
        machine.lightsleep(ms)
        return
    try:
        machine.RTC().wakeup(ms)
    except Exception as e:
        print('board_rest: RTC.wakeup failed', repr(e))
    time.sleep_ms(50)
    machine.deepsleep()               # never returns


def board_lum(img):
    """Sense stage: mean luminance 0-255 from a GRAYSCALE/RGB565 preview.
    OpenMV's LAB stats report L as 0-100 on the N6 (unlike some boards'
    0-255), so scale by 2.55 to keep lum_night/lum_day meaning the same
    fraction of full brightness as on the XIAO."""
    try:
        st = img.get_statistics()
        v = st.l_mean
        v = v() if callable(v) else v
        return max(0, min(255, int(round(v * 2.55))))
    except Exception as e:
        print('board_lum failed', repr(e))
        return 0


def board_thumb(img):
    """80x50 GRAYSCALE copy of `img` for board_thumb_diff / the persisted
    motion reference. Primary path: scale-copy off the frame buffer, then
    convert if the copy isn't already grayscale. Fallback (older/odd image
    objects): draw scaled onto a fresh GRAYSCALE canvas."""
    try:
        t = img.copy(x_scale=THUMB_W / img.width(), y_scale=THUMB_H / img.height(),
                      copy_to_fb=False)
        if hasattr(t, 'to_grayscale'):
            try:
                t = t.to_grayscale()
            except Exception:
                pass
        return t
    except Exception as e:
        try:
            t = image.Image(THUMB_W, THUMB_H, sensor.GRAYSCALE)
            t.draw_image(img, 0, 0, x_scale=THUMB_W / img.width(), y_scale=THUMB_H / img.height())
            return t
        except Exception:
            print('board_thumb failed', repr(e))
            return None


def board_thumb_bytes(thumb):
    """80x50 grayscale thumbnail -> raw bytes, for persist.py to write to
    /flash as the cross-sleep motion reference (RAM is lost in standby)."""
    return bytes(thumb.bytearray())


def board_thumb_from_bytes(b):
    """The inverse of board_thumb_bytes: raw bytes -> an image.Image usable
    by board_thumb_diff as `ref_img`. Defensive about the MicroPython 1.28 /
    OpenMV 5 constructor keyword (`buffer=` vs `buf=`)."""
    try:
        return image.Image(THUMB_W, THUMB_H, sensor.GRAYSCALE, buffer=b)
    except TypeError:
        try:
            return image.Image(THUMB_W, THUMB_H, sensor.GRAYSCALE, buf=b)
        except Exception as e:
            print('board_thumb_from_bytes failed', repr(e))
            return None
    except Exception as e:
        print('board_thumb_from_bytes failed', repr(e))
        return None


def board_thumb_diff(ref_bytes, thumb_img, l_thresh):
    """(frac, bbox): frac = fraction of thumb pixels whose luminance changed
    by >= l_thresh since `ref_bytes` (motion.py's contract, at thumb
    resolution; 1.0 when there is no reference yet). `ref_bytes` is the
    persisted THUMB_W*THUMB_H grayscale reference as returned by
    board_thumb_bytes() — wakecycle.py persists it as raw bytes (gamespool.
    gs_thumb_save/gs_thumb_load), not an image object, across the deep sleep
    that loses RAM — or None on the first wake. bbox = the largest changed
    region's rect() (x, y, w, h) in thumb coordinates, or None."""
    if ref_bytes is None:
        return 1.0, None
    try:
        ref_img = board_thumb_from_bytes(ref_bytes)
        work = thumb_img.copy()
        work.difference(ref_img)
        bins = work.get_histogram().l_bins
        bins = bins() if callable(bins) else bins        # fw 5.0: tuple attribute, not a method
        frac = sum(bins[l_thresh:])
        bbox = None
        blobs = work.find_blobs([(l_thresh, 255)], merge=True, pixels_threshold=2)
        if blobs:
            best = blobs[0]
            best_area = -1
            for b in blobs:
                r = b.rect
                r = r() if callable(r) else r          # fw 5.0: tuple attribute
                area = r[2] * r[3]
                if area > best_area:
                    best_area = area
                    best = b
            bbox = best.rect
            bbox = bbox() if callable(bbox) else bbox
        return frac, bbox
    except Exception as e:
        print('board_thumb_diff failed', repr(e))
        return 1.0, None


def board_button_down():
    """SW, active-low. A fresh Pin object per call, a short settle and two
    samples: at a deep-sleep wake the import-time Pin read 1 while the
    button was held (bench 2026-09-13), a REPL-created one read 0."""
    try:
        pin = machine.Pin(machine.Pin.board.SW, machine.Pin.IN, machine.Pin.PULL_UP)
        time.sleep_ms(20)
        a = pin.value()
        time.sleep_ms(10)
        b = pin.value()
        return a == 0 or b == 0
    except (AttributeError, OSError, ValueError):
        if _sw_pin is None:
            return False
        try:
            return _sw_pin.value() == 0
        except (OSError, ValueError):
            return False