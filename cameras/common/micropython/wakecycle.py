"""wakecycle: one wake of the `game_lowpower` profile. docs/camera_operation.md
§4.1, §7 (storage/ranking), §8 (time); openmv_n6/PLAN.md §3.

Board hooks this module calls (defined in the camera's board.py, bundled
first; resolved with `globals().get(name)` + a sane fallback so this module
also imports cleanly under the host stubs with no board.py at all):

  wake_cause() -> 'deep' | 'cold' | 'soft'   ('cold': power-on, PWR button
                                           off/on, watchdog -- every one runs
                                           a contact, see _one_wake; 'soft'
                                           is mpremote/an OTA reboot and does
                                           not)
  board_rest(ms)                          never returns on the board
  board_lum(img) -> 0..255                mean luminance of a preview
  board_thumb(img) -> image.Image         THUMB_W x THUMB_H GRAYSCALE
  board_thumb_diff(ref_bytes, thumb_img, l_thresh) -> (frac, bbox|None)
                                           bbox = (x, y, w, h) in thumb coords
  board_button_down() -> bool
  board_sensors() -> dict

`game_run(poll)` is what app.run() calls for this profile: it does exactly
one wake (Sense/Night/Watch/Trigger/Judge/Record/Rest) and ends by calling
board_rest(), which deep-sleeps the board; main.py starts over on the next
wake. Any exception in the wake is caught, logged and counted (st['crash_n'])
so a bad wake never becomes a crash loop -- three in a row and the board
just rests without touching the card again.
"""
import gc
import json
import time

import network

from persist import *
from night import *
from gamespool import *
from rank import *
from judge import *
from contact import *
from led import *
from control import *
from camera import *
from config import *
from otapull import *

THUMB_W = 80
THUMB_H = 50
NIGHT_FILE = '/flash/night.json'
BOOT_COUNT_FILE = '/flash/boot_count.txt'
FLAG_THUMB_VALID = 1
FLAG_FIRST_CONTACT_DONE = 2


def _wake_cause():
    fn = globals().get('wake_cause')
    try:
        return fn() if fn else 'cold'
    except Exception:
        return 'cold'


def _rest(ms):
    fn = globals().get('board_rest')
    if fn:
        fn(max(0, int(ms)))
    # no board_rest (host tests, or an incomplete board.py): just return


def _lum(img):
    fn = globals().get('board_lum')
    try:
        return fn(img) if fn else 0
    except Exception:
        return 0


def _thumb(img):
    fn = globals().get('board_thumb')
    try:
        return fn(img) if fn else img
    except Exception:
        return img


def _thumb_diff(ref_bytes, thumb_img, l_thresh):
    fn = globals().get('board_thumb_diff')
    if fn:
        try:
            return fn(ref_bytes, thumb_img, l_thresh)
        except Exception:
            pass
    return (1.0, None)


def _thumb_bytes(thumb_img):
    """The persisted-reference form of a thumbnail: bytes if board_thumb
    already returns them, else whatever .bytearray()/bytes() gives."""
    if isinstance(thumb_img, (bytes, bytearray)):
        return bytes(thumb_img)
    for meth in ('bytearray', 'tobytes'):
        if hasattr(thumb_img, meth):
            return bytes(getattr(thumb_img, meth)())
    return thumb_img


def _button_down():
    fn = globals().get('board_button_down')
    try:
        return bool(fn()) if fn else False
    except Exception:
        return False


def _sensors():
    fn = globals().get('board_sensors')
    try:
        return fn() if fn else {}
    except Exception:
        return {}


def _mem_free():
    try:
        return gc.mem_free()
    except AttributeError:
        return 0


def _game_ip():
    try:
        return network.WLAN(network.STA_IF).ifconfig()[0]
    except OSError:
        return ''


def _rssi():
    try:
        return network.WLAN(network.STA_IF).status('rssi')
    except (OSError, ValueError):
        return None


def _clock_str(clock_state):
    if clock_state == 2:
        return 'set'
    if clock_state == 1:
        return 'est'
    return 'none'


def game_meta(ts, seq, w, h, why, diff, gate, heartbeat, buffered, score, clock, lum, det, night_s=None):
    """Sidecar JSON: every standard key (camera_standard.md §4) plus
    game_lowpower's: score, clock, lum, det, night_s (morning frame only)."""
    m = {
        'ts': ts, 'seq': seq, 'w': w, 'h': h,
        'v': globals().get('APP_VERSION', ''),
        'cfg': CFG.get('cfg', 0),
        'ip': _game_ip(),
        'mode': STATE.get('mode', 'live'),
        'why': why,
        'diff': diff,
        'gate': gate,
        'heartbeat': bool(heartbeat),
        'buffered': bool(buffered),
        'score': score,
        'clock': clock,
        'lum': lum,
        'det': det if det is not None else [],
    }
    if night_s is not None:
        m['night_s'] = night_s
    return json.dumps(m)


def game_telemetry(st, t_boot_ms, lum=None, clock_skew_s=0):
    """Standard telemetry keys (camera_standard.md §4) plus the off-grid
    extras (camera_operation.md §9): night, pending_cold, contact_n,
    clock_skew_s, lum."""
    vals = {
        'uptime_s': time.ticks_diff(time.ticks_ms(), t_boot_ms) // 1000,
        'mem_free': _mem_free(),
        'frames_sent': st.get('sent', 0),
        'frames_skipped': st.get('skipped', 0),
        'upload_failures': st.get('failed', 0),
        'pending_files': gs_count(SPOOL_DIR),
        'mode': MODE_NUM.get(STATE.get('mode', 'live'), 0),
        'cfg': CFG.get('cfg', 0),
        'boot_count': st.get('boot', 0),
        'wake_n': st.get('wake_n', 0),
        'night': st.get('night', 0),
        'pending_cold': st.get('pending_n', 0),
        'contact_n': st.get('contact_n', 0),
        'clock_skew_s': clock_skew_s,
    }
    if lum is not None:
        vals['lum'] = lum
    vals.update(_sensors())
    rssi = _rssi()
    if rssi is not None:
        vals['rssi'] = rssi
    return vals


def _game_boot_count(cause):
    """/flash/boot_count.txt: incremented only on a real boot (not a
    deep-sleep timer wake), so /sdcard/spool/<boot>/ groups one continuous
    off-grid session, independent of persist.py's TAMP-backed counters."""
    n = 0
    try:
        with open(BOOT_COUNT_FILE) as f:
            n = int(f.read().strip() or 0)
    except (OSError, ValueError):
        pass
    if cause != 'deep':
        n += 1
        try:
            with open(BOOT_COUNT_FILE, 'w') as f:
                f.write(str(n))
        except OSError:
            pass
    return n


def _telemetry_fn(st, t_boot_ms):
    def fn(mode_num, extra=None):
        vals = game_telemetry(st, t_boot_ms, clock_skew_s=(extra or {}).get('clock_skew_s', 0))
        if extra:
            vals.update(extra)
        vals['mode'] = mode_num
        try:
            import secrets
            post_json('/telemetry/%s' % secrets.DEVICE, json.dumps(vals))
        except Exception as e:
            print('telemetry failed', repr(e))
    return fn


def _log_fn(line):
    gs_log(line)
    print(line)


def _run_contact(st, cause):
    st['wake_cause'] = cause
    t_boot_ms = time.ticks_ms()
    try:
        # the setup page's stream and /shoot need a running sensor; a contact
        # at the top of a wake happens before Sense has initialised it
        preview_init(CFG.get('preview_settle_ms', 300))
    except Exception as e:
        print('contact: preview_init failed', repr(e))
    contact_run(st, TUNING, _telemetry_fn(st, t_boot_ms), _log_fn)


WAKE_CYCLE_FLAG = '/flash/wake_cycle'     # loader contract: ota_main.py skips WiFi/NTP when present


def _flag_wake_cycle():
    """Written once (cold boot) so the loader knows every later boot is a
    wake; never rewritten per wake (NOR wear)."""
    try:
        import os
        os.stat(WAKE_CYCLE_FLAG)
    except OSError:
        try:
            with open(WAKE_CYCLE_FLAG, 'w') as f:
                f.write('game_lowpower')
        except OSError:
            pass


def _one_wake(st, poll):
    cause = _wake_cause()
    boot = _game_boot_count(cause)
    st['boot'] = boot
    fw_boot_check(globals().get('APP_VERSION', ''))
    cfg_init(TUNING)
    period_s = CFG.get('period_s', 30)
    if cause != 'deep':
        _flag_wake_cycle()

    # --- contact first (the button always works, card or no card): a press
    # held at boot, ANY cold boot (power-on, PWR button off/on -- the field
    # gesture for a contact -- or a watchdog reset; a battery swap costs one
    # search), the first non-cold boot after provisioning, or a firmware
    # install still proving itself (fw_pending) all run a contact attempt.
    # 'soft' resets (mpremote, an OTA install's reboot) are not a deliberate
    # field gesture, so they keep the old first/pending-only rules.
    button = _button_down()
    st['btn'] = 1 if button else 0
    first = cause != 'deep' and not (st.get('flags', 0) & FLAG_FIRST_CONTACT_DONE)
    pending = cause != 'deep' and bool(fw_pending())
    if button or cause == 'cold' or first or pending:
        _run_contact(st, cause)
        st['crash_n'] = 0
        persist_save(st)
        _rest(period_s * 1000)
        return

    if not gs_ready():
        led_pattern('fail')
        gs_log('%d %s no-card' % (st.get('wake_n', 0), cause))
        print('wake %d %s: no card, profile not applicable' % (st.get('wake_n', 0), cause))
        _rest(period_s * 1000)
        return

    # --- bench_contact_n (dev/bench only, 0 disables it): every Nth wake,
    # scan for the home LAN before doing anything else; if it is visible,
    # run a contact so a bench session gets OTA/config over the LAN without
    # holding the button. contact_scan_lan() is the same scan contact.py
    # itself uses to choose LAN vs. hotspot.
    bench_contact_n = CFG.get('bench_contact_n', 0)
    if bench_contact_n and st.get('wake_n', 0) % bench_contact_n == 0:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        lan_visible = contact_scan_lan(wlan)
        gs_log('bench-contact: lan %s' % ('visible' if lan_visible else 'absent'))
        print('bench-contact: lan %s' % ('visible' if lan_visible else 'absent'))
        if lan_visible:
            st['wake_n'] = st.get('wake_n', 0) + 1     # this wake counts, or the next one re-triggers
            _run_contact(st, cause)
            st['crash_n'] = 0
            persist_save(st)
            _rest(period_s * 1000)
            return
        wlan.active(False)

    nst = night_load(NIGHT_FILE)
    if st.get('night'):
        nst['night'] = 1
        nst['start'] = st.get('night_start', nst.get('start', 0))
    nst['dark_n'] = st.get('dark_n', 0)

    # --- Sense
    preview_init(CFG.get('preview_settle_ms', 300))
    import sensor
    img = sensor.snapshot()
    lum = _lum(img)
    now = int(time.time())

    # --- Night
    sleep_s, evt = night_step(nst, lum, now, CFG)
    st['wake_n'] = st.get('wake_n', 0) + 1
    st['dark_n'] = nst.get('dark_n', 0)
    if evt in ('enter', 'probe'):
        if evt == 'enter':
            night_save(NIGHT_FILE, nst)
        st['night'] = nst['night']
        st['night_start'] = nst.get('start', 0)
        st['crash_n'] = 0
        persist_save(st)
        gs_log('%d %s lum=%d night=%s sleep_s=%s' % (st['wake_n'], cause, lum, evt, sleep_s))
        print('wake %d %s lum=%d night=%s sleep_s=%s' % (st['wake_n'], cause, lum, evt, sleep_s))
        led_pattern('off')
        _rest(sleep_s * 1000)
        return

    night_s = None
    if evt == 'exit':
        night_save(NIGHT_FILE, nst)
        st['night'] = 0
        night_s = nst.get('last_len', 0)
        st['night_s_last'] = night_s

    # --- Watch
    thumb = _thumb(img)
    ref = gs_thumb_load() if (st.get('flags', 0) & FLAG_THUMB_VALID) else None
    frac, bbox = _thumb_diff(ref, thumb, CFG.get('diff_l_thresh', 8))

    # --- Trigger (heartbeat counts awake time, like the XIAO: st['awake_ms'])
    interval_n = CFG.get('interval_n', 120)
    heartbeat_s = CFG.get('heartbeat_s', 3600)
    if ref is None:
        why = 'boot'
    elif frac >= CFG.get('diff_min_frac', 0.02):
        why = 'motion'
    elif interval_n and st['wake_n'] % interval_n == 0:
        why = 'interval'
    elif st.get('awake_ms', 0) >= heartbeat_s * 1000:
        why = 'heartbeat'
    else:
        why = 'none'
    if night_s is not None and why == 'none':
        why = 'boot'                     # the morning frame always records

    clock = _clock_str(st.get('clock_state', 0))
    gate_thresh = CFG.get('diff_min_frac', 0.02)
    ts = now + globals().get('EPOCH_OFFSET', 0)

    # --- Judge on the preview (crop in preview coordinates) before the
    # capture: a rejected frame costs no HD capture, and `img` aliases the
    # frame buffer, which capture() overwrites.
    conf = None
    keep, reason = True, 'pass'
    if why == 'motion':
        if gate_init() is not None or LAST_JUDGE[0] == 'ready':
            bx, by, bw, bh = bbox if bbox else (0, 0, 0, 0)
            x, y, side = crop_box(bx, by, bw, bh, THUMB_W, THUMB_H, img.width(), img.height())
            conf = gate_score(img, x, y, side)
        keep, reason = judge_decide(conf, CFG, st.get('seq', 0) + 1)

    # --- Debug frame (the preview; to_jpeg converts the fb image in place,
    # so nothing below may use `img` as a pixel image)
    if CFG.get('debug_frames'):
        try:
            data = img.to_jpeg(quality=60)
            data = data.bytearray() if hasattr(data, 'bytearray') else data
            meta = game_meta(ts, st.get('seq', 0), img.width(), img.height(), 'watch', frac,
                             gate_thresh, False, False, score_for('watch', frac, None, 0.0), clock, lum, [])
            if gs_write_debug(boot, st['wake_n'], data, meta):
                st['debug_n'] = st.get('debug_n', 0) + 1
        except Exception as e:
            print('debug frame failed:', repr(e))

    # --- Capture + Record
    kept = False
    score = 0.0
    if why != 'none' and (keep or reason == 'audit'):
        data, cw, ch = capture()
        try:
            st['seq'] = st.get('seq', 0) + 1
            score = score_for(why, frac, conf, 0.0)
            det = []
            if conf is not None:
                labels = CFG.get('keep_labels') or ['animal']
                det = [{'label': labels[0], 'conf': round(conf, 4)}]
            meta = game_meta(ts, st['seq'], cw, ch, why, frac, gate_thresh,
                             why == 'heartbeat', False, score, clock, lum, det, night_s)
            if gs_write(boot, st['seq'], data, meta):
                st['awake_ms'] = 0
                kept = True
                gs_thumb_save(_thumb_bytes(thumb))
                st['flags'] = st.get('flags', 0) | FLAG_THUMB_VALID
                if CFG.get('led_capture', True):
                    led_pattern('capture')
        finally:
            restore_preview()
    elif why == 'motion':
        # rejected by the gate: the reference still moves on so the same
        # scene change does not re-trigger every wake
        gs_thumb_save(_thumb_bytes(thumb))
        st['flags'] = st.get('flags', 0) | FLAG_THUMB_VALID

    if _button_down():
        _run_contact(st, cause)

    st['awake_ms'] = st.get('awake_ms', 0) + time.ticks_ms()
    st['last_ts'] = now
    st['crash_n'] = 0
    persist_save(st)
    line = ('%d %s btn=%d lum=%d diff=%.4f why=%s kept=%d score=%.3f conf=%s judge=%s awake_ms=%d sleep_s=%d'
            % (st['wake_n'], cause, st.get('btn', 0), lum, frac, why, kept, score,
               '-' if conf is None else '%.2f' % conf, LAST_JUDGE[0].replace(' ', '_') if why == 'motion' else '-',
               st['awake_ms'], period_s))
    gs_log(line)
    print('wake ' + line)
    _rest(period_s * 1000)


def game_run(poll, wakes=0):
    """app.run() lands here for profile game_lowpower. One wake per call
    when board_rest() deep-sleeps (it never returns: main.py reruns); loops
    when it returns (SLEEP_MODE 'light', or a host/bench stub). `wakes`
    caps the loop for tests."""
    n = 0
    while True:
        st = persist_load()
        try:
            _one_wake(st, poll)
        except Exception as e:
            st['crash_n'] = st.get('crash_n', 0) + 1
            try:
                print('game_run crash %d:' % st['crash_n'], repr(e))
                gs_log('crash %d %r' % (st['crash_n'], e))
            except Exception:
                pass
            period_s = CFG.get('period_s', 30) if CFG else 30
            try:
                persist_save(st)
            except Exception:
                pass
            _rest(period_s * (10000 if st['crash_n'] >= 3 else 1000))
        n += 1
        if globals().get('SLEEP_MODE', 'deep') != 'light' or (wakes and n >= wakes):
            return
