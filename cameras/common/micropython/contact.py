"""contact: the contact sequence. docs/camera_operation.md §5, §10 (LED).

`contact_run(st, cfg_defaults, telemetry_fn, log_fn)` runs steps 1-8 and
returns True if the join succeeded (whether or not anything useful happened
afterward -- the caller resumes night/live either way). `st` is the
persisted state dict (persist.py fields); this function updates
'clock_state', 'contact_n' and 'flags' in place and leaves saving it to the
caller. `telemetry_fn(mode_num, extra_dict)` sends one telemetry report;
`log_fn(line)` records one wake-log-style line (gs_log + print).

Two networks, chosen by a scan before joining: secrets carries both the
hotspot/public path (WIFI_SSID/WIFI_PASS, SERVER_HOST/PORT/TLS, as before)
and the home LAN path (LAN_SSID/LAN_PASS, LAN_HOST/LAN_PORT/LAN_TLS, added
by tools/dustygen). `contact_scan()`/`contact_scan_lan()` below are shared
with wakecycle.py's `bench_contact_n` path. If LAN_SSID shows up in the
scan, contact joins it and points uplink.py at LAN_HOST/PORT/TLS via
`set_server()`; otherwise it joins the hotspot as before (even if the scan
didn't see it -- scans can miss) and `set_server(None)` keeps the secrets.py
defaults. `set_server(None)` is restored again on the way out (step 8, and
on a failed join) so a LAN choice never outlives one contact.

Needs from the bundle (all earlier in [bundle] order): network, machine,
secrets (board), control_init/control_poll/STATE/BUTTON_NAMES/LED_NAME,
http_get/post_json/LAST_DATE/set_server, CFG/cfg_pull, fw_check/fw_mark_valid,
gs_drain/gs_reclaim/SPOOL_DIR/DEBUG_DIR, led_pattern/LedBlinker.
"""
import time

import machine
import network
import secrets

from control import *
from uplink import *
from config import *
from otapull import *
from gamespool import *
from led import *

_MONTHS = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
           'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
_MDAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _is_leap(y):
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def _epoch_1970(year, month, day, hh, mm, ss):
    days = 0
    for y in range(1970, year):
        days += 366 if _is_leap(y) else 365
    for m in range(1, month):
        days += _MDAYS[m - 1] + (1 if m == 2 and _is_leap(year) else 0)
    days += day - 1
    return days * 86400 + hh * 3600 + mm * 60 + ss


def parse_http_date(s):
    """RFC 1123 'Sun, 06 Nov 1994 08:49:37 GMT' -> 1970-epoch seconds, or
    None. Pure; no libc strptime (MicroPython has none)."""
    try:
        parts = s.strip().split()
        if len(parts) < 5:
            return None
        day = int(parts[1])
        mon = _MONTHS.get(parts[2])
        year = int(parts[3])
        hh, mm, ss = (int(x) for x in parts[4].split(':'))
        if mon is None or not 1 <= day <= 31:
            return None
        return _epoch_1970(year, mon, day, hh, mm, ss)
    except (ValueError, IndexError, TypeError):
        return None


def _set_rtc_from_epoch1970(epoch1970):
    offset = globals().get('EPOCH_OFFSET', 946684800)
    tm = time.gmtime(epoch1970 - offset)
    # MicroPython time.gmtime(): (year, month, mday, hour, minute, second, weekday, yearday)
    try:
        machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))   # weekday 1-7
        return True
    except Exception:
        return False


def contact_scan(wlan):
    """{ssid, ...} seen in a fresh scan (network.WLAN.scan()'s first tuple
    item is the SSID as bytes); empty set on any scan error -- a bad scan
    must never crash the wake or a contact, it just falls back to the
    hotspot."""
    try:
        return {(n[0].decode() if isinstance(n[0], (bytes, bytearray)) else n[0]) for n in wlan.scan()}
    except Exception:
        return set()


def contact_scan_lan(wlan):
    """True if secrets.LAN_SSID is visible in a fresh scan. Shared by
    contact_run's own network choice (below) and wakecycle.py's
    bench_contact_n path, so both agree on what "the LAN is visible" means."""
    lan_ssid = getattr(secrets, 'LAN_SSID', '')
    return bool(lan_ssid) and lan_ssid in contact_scan(wlan)


def contact_run(st, cfg_defaults, telemetry_fn, log_fn):
    log_fn('contact: start')
    STATE['mode'] = 'contact'
    wlan = network.WLAN(network.STA_IF)
    blinker = LedBlinker(1000, 150)         # searching: one blink/s
    joined = False
    t_join = time.ticks_ms()

    # --- Network choice (step 1a): scan before joining -- if the home LAN
    # is in range, join it and point uplink.py at the LAN gate for this
    # contact; otherwise join the hotspot/public path as before.
    join_ssid, join_pass, net_label, nets = secrets.WIFI_SSID, secrets.WIFI_PASS, 'hotspot', set()
    try:
        wlan.active(True)
        nets = contact_scan(wlan)
        lan_ssid = getattr(secrets, 'LAN_SSID', '')
        if lan_ssid and lan_ssid in nets:
            join_ssid, join_pass, net_label = lan_ssid, getattr(secrets, 'LAN_PASS', ''), 'lan'
    except Exception as e:
        log_fn('contact: scan error %r' % e)
    log_fn('contact: network %s (%s), scan saw %d' % (join_ssid, net_label, len(nets)))
    if net_label == 'lan':
        set_server(secrets.LAN_HOST, secrets.LAN_PORT, getattr(secrets, 'LAN_TLS', False))
    else:
        set_server(None)

    try:
        wlan.connect(join_ssid, join_pass)
        end = time.time() + CFG.get('hotspot_join_s', 90)
        while time.time() < end:
            blinker.tick()
            if wlan.isconnected():
                joined = True
                break
            time.sleep_ms(100)
    except Exception as e:
        log_fn('contact: wifi error %r' % e)
    blinker.stop()

    if not joined:
        led_pattern('fail')
        log_fn('contact: hotspot join failed')
        STATE['mode'] = 'live'
        set_server(None)               # restore the defaults on a failed LAN attempt too
        return False

    log_fn('contact: joined in %d ms, ip %s' % (time.ticks_diff(time.ticks_ms(), t_join), wlan.ifconfig()[0]))
    control_init(globals().get('BUTTON_NAMES', ()), globals().get('LED_NAME', 'LED_BLUE'))
    led_pattern('solid')

    # --- Clock (step 3)
    clock_skew_s = 0
    status, _body = http_get('/config/%s' % secrets.DEVICE)
    if status == 200 and LAST_DATE[0]:
        server_epoch = parse_http_date(LAST_DATE[0])
        if server_epoch is not None:
            offset = globals().get('EPOCH_OFFSET', 946684800)
            clock_skew_s = server_epoch - (time.time() + offset)
            if _set_rtc_from_epoch1970(server_epoch):
                st['clock_state'] = 2
    log_fn('contact: config GET %s, clock skew %d s' % (status, clock_skew_s))

    # --- Announce (step 4): mode 3 (contact)
    extra = {'clock_skew_s': clock_skew_s, 'night': st.get('night', 0),
             'pending_cold': st.get('pending_n', 0), 'contact_n': st.get('contact_n', 0),
             'boot': st.get('wake_cause', '')}
    telemetry_fn(3, extra)

    # --- Firmware first, then config (step 5)
    installed = fw_check(globals().get('APP_VERSION', ''))
    log_fn('contact: fw check done (installed=%s)' % installed)
    changed = cfg_pull(cfg_defaults)
    log_fn('contact: cfg %s changed %s' % (CFG.get('cfg'), changed))
    # a contact that joined, synced the clock, announced itself and pulled
    # the config has proven the network path: that is enough to trust a
    # pending install even when there is nothing to drain (off-grid a spool
    # can be empty for days, and a pending install blocks further updates)
    fw_mark_valid()
    if changed:
        led_pattern('updated')
        led_pattern('solid')

    # --- Drain (step 6): telemetry every telemetry_s, control plane polled
    # between files so the setup page works mid-drain.
    last_tele = [time.time()]

    def idle2():
        control_poll()
        if time.time() - last_tele[0] >= CFG.get('telemetry_s', 60):
            telemetry_fn(3, extra)
            last_tele[0] = time.time()

    version = globals().get('APP_VERSION', '')
    t_drain = time.ticks_ms()
    try:
        my_ip = wlan.ifconfig()[0]
    except OSError:
        my_ip = None
    sent1, _failed1 = gs_drain(SPOOL_DIR, CFG.get('upload_cap', 1000), idle2, version, ip=my_ip)
    log_fn('contact: drain sent %d failed %d in %d ms' % (sent1, _failed1, time.ticks_diff(time.ticks_ms(), t_drain)))
    if sent1:
        fw_mark_valid()
    sent2, _failed2 = gs_drain(DEBUG_DIR, CFG.get('debug_max', 500), idle2, version, ip=my_ip)
    if sent2 and not sent1:
        fw_mark_valid()

    # --- Serve (step 7): control_poll until contact_idle_s idle, or GET /live
    last_reqs = STATE.get('reqs', 0)
    last_activity = time.time()
    idle_s = CFG.get('contact_idle_s', 120)
    while True:
        control_poll()
        if STATE.get('reqs', 0) != last_reqs:
            last_reqs = STATE.get('reqs', 0)
            last_activity = time.time()
        if STATE.get('live_req', 0):
            STATE['live_req'] = 0
            break
        if time.time() - last_activity >= idle_s:
            break
        time.sleep_ms(100)

    # --- Leave (step 8)
    telemetry_fn(3, extra)
    try:
        wlan.disconnect()
        wlan.active(False)
    except Exception:
        pass
    set_server(None)               # a LAN choice never outlives one contact
    led_pattern('off')
    st['contact_n'] = st.get('contact_n', 0) + 1
    st['flags'] = (st.get('flags', 0) & ~1) | 2   # thumb ref invalid (bit0); first_contact_done (bit1)
    gs_reclaim(CFG.get('spool_max_frames', 100000))
    STATE['mode'] = 'live'
    log_fn('contact: end (sent %d+%d frames)' % (sent1, sent2))
    return True
