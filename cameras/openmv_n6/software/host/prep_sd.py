#!/usr/bin/env python3
"""Prepare the microSD card in the N6 for the game_lowpower spool, over USB.

With a card inserted the firmware makes /sdcard the boot filesystem and
runs main.py from THERE; an empty card boots to a bare REPL and the app
never starts (sarg: sarg/openmv-n6-silently-skips-flash-main-py-autorun).
This writes the 2-line chain loader /sdcard/main.py that execs
/flash/main.py, creates /sdcard/spool and /sdcard/debug, reports the
card's size/free space and a 1 MB write/read timing, then resets the board
so the loader runs.

    prep_sd.py [--port PORT] [--no-reset]

Run it with the card already in the board. The board's own USB mass
storage may now show the card instead of PYBFLASH; unmount whatever the
board exposes before this runs (it does so itself with udisksctl).
"""
import argparse
import glob
import subprocess
import sys
import time

DEFAULT_PORT = glob.glob('/dev/serial/by-id/usb-MicroPython_Pyboard_Virtual_Comm_Port_in_FS_Mode_*-if00')

CHAIN = '# Chain to the real bootstrap on internal flash (the SD card is data only).\nexec(open("/flash/main.py").read())\n'

PROBE = r'''
import os, time
try:
    print("cwd", os.getcwd())
except Exception as e:
    print("cwd ?", repr(e))
print("root", os.listdir("/"))
try:
    st = os.statvfs("/sdcard")
    print("sdcard total_MB=%d free_MB=%d" % (st[0]*st[2] >> 20, st[0]*st[3] >> 20))
except OSError as e:
    print("NO_CARD", repr(e)); raise SystemExit
for d in ("/sdcard/spool", "/sdcard/debug"):
    try:
        os.mkdir(d)
    except OSError:
        pass
with open("/sdcard/main.py", "w") as f:
    f.write(__CHAIN__)
print("main.py", repr(open("/sdcard/main.py").read()))
buf = bytearray(65536)
t = time.ticks_ms()
with open("/sdcard/_speed.tmp", "wb") as f:
    for _ in range(16):
        f.write(buf)
os.sync() if hasattr(os, "sync") else None
tw = time.ticks_diff(time.ticks_ms(), t)
t = time.ticks_ms()
with open("/sdcard/_speed.tmp", "rb") as f:
    while f.readinto(buf):
        pass
tr = time.ticks_diff(time.ticks_ms(), t)
os.rename("/sdcard/_speed.tmp", "/sdcard/_speed2.tmp"); os.remove("/sdcard/_speed2.tmp")
print("1MB write %d ms, read %d ms" % (tw, tr))
print("sdcard", os.listdir("/sdcard"))
'''.replace('__CHAIN__', repr(CHAIN))


def unmount_board_drives():
    out = subprocess.run(['lsblk', '-rno', 'NAME,RM,MOUNTPOINT'], capture_output=True, text=True).stdout
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3 and parts[1] == '1' and parts[2].startswith('/media/'):
            subprocess.run(['udisksctl', 'unmount', '-b', '/dev/' + parts[0]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', default=DEFAULT_PORT[0] if DEFAULT_PORT else None)
    ap.add_argument('--no-reset', action='store_true')
    a = ap.parse_args()
    if not a.port:
        sys.exit('prep_sd: no N6 on USB')
    unmount_board_drives()
    r = subprocess.run(['mpremote', 'connect', a.port, 'exec', PROBE], capture_output=True, text=True)
    print(r.stdout, r.stderr[-800:] if r.returncode else '', sep='')
    if 'NO_CARD' in r.stdout or r.returncode:
        sys.exit('prep_sd: no card mounted at /sdcard (is it inserted? power-cycle the board with the card in)')
    if not a.no_reset:
        time.sleep(0.5)
        subprocess.run(['mpremote', 'connect', a.port, 'reset'])
        print('prep_sd: reset; the loader should now run from /flash via /sdcard/main.py')


if __name__ == '__main__':
    main()
