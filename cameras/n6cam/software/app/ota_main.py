"""OTA bootstrap. Deployed as /flash/main.py — tiny and NEVER updated OTA;
only app.py changes over the air, so a bad push can't brick the update loop.
This loader change needs a USB copy to take effect (see README "Deploy").

Boot: WiFi -> NTP -> start OTA listener -> run app.run(ota.poll) — UNLESS
this boot is a game_lowpower wake, in which case none of that runs here:
the app (wakecycle.py, package A) owns WiFi, the clock and the OTA/control
listener itself, once per CONTACT (docs/camera_operation.md §5), not once
per wake. `skip_contact` below decides that.

On app crash: restore app_prev.py (keeping the bad file as app_bad.py) and
reboot; if there is nothing to restore, sit in recovery mode polling OTA so
a fixed app.py can be pushed. Recovery mode ALWAYS brings WiFi up and starts
the OTA listener itself, even when the normal boot path skipped them, so a
broken app.py is always reachable over the hotspot to fix.

Wake-cycle contract (/flash/wake_cycle): wakecycle.py writes this empty
flag file when TUNING['profile'] == 'game_lowpower' and removes it for any
other profile (a profile switch back to 'monitor' takes effect at the next
contact). reset_cause() == DEEPSLEEP_RESET alone would cover every
game_lowpower wake but the very first cold boot after flashing; the flag
file is the signal for that first boot (and any other non-deepsleep reboot,
e.g. a watchdog reset, that happens while the flag is still set).
"""
import os
import sys
import time

import machine

import ota
import secrets

WAKE_CYCLE_FLAG = '/flash/wake_cycle'


def _flag_set(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


skip_contact = (machine.reset_cause() == machine.DEEPSLEEP_RESET) or _flag_set(WAKE_CYCLE_FLAG)

if not skip_contact:
    wlan = ota.wifi_connect(secrets.WIFI_SSID, secrets.WIFI_PASS)
    print('wifi:', wlan.ifconfig()[0] if wlan else 'FAILED')
    try:
        import ntptime
        ntptime.settime()
        print('ntp: synced')
    except Exception:
        print('ntp: skipped')
    ota.start(getattr(secrets, 'OTA_PORT', 8266), getattr(secrets, 'OTA_TOKEN', ''))
else:
    print('boot: game_lowpower wake (%s), skipping WiFi/NTP/OTA listener' %
          ('deepsleep' if machine.reset_cause() == machine.DEEPSLEEP_RESET else 'wake_cycle flag'))

try:
    import app
    ota.state['version'] = getattr(app, 'APP_VERSION', '?')
    print('app version:', ota.state['version'])
    app.run(ota.poll)
except Exception as e:
    sys.print_exception(e)
    try:
        os.stat('/flash/app_prev.py')       # anything to roll back to?
        try:
            os.remove('/flash/app_bad.py')
        except OSError:
            pass
        os.rename('/flash/app.py', '/flash/app_bad.py')
        os.rename('/flash/app_prev.py', '/flash/app.py')
        print('ota: app crashed, reverted to previous version, rebooting')
        time.sleep(1)
        machine.reset()
    except OSError:
        pass                                # no fallback available

print('ota: RECOVERY MODE — push a fixed app.py to /update')
ota.state['version'] = 'recovery'
if skip_contact:
    # nothing brought WiFi/OTA up above; a broken app must still be fixable
    wlan = ota.wifi_connect(secrets.WIFI_SSID, secrets.WIFI_PASS)
    print('wifi:', wlan.ifconfig()[0] if wlan else 'FAILED')
    ota.start(getattr(secrets, 'OTA_PORT', 8266), getattr(secrets, 'OTA_TOKEN', ''))
while True:
    ota.poll()
    time.sleep_ms(100)
