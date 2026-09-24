#!/usr/bin/env python3
"""Bench gates for the N6 `game_lowpower` wake cycle (PLAN.md §8). Each
subcommand below is one gate; it drives the board over `mpremote` (board-
side snippets run with `mpremote connect <port> exec/run ...`) and, for
`standby`, opens the USB serial port directly (pyserial, same approach as
monitor.py) to catch the board within about a second of re-enumerating
after a deep-sleep wake — mpremote's own reconnect is not fast or precise
enough for that.

    uv run --offline --no-project --with pyserial python software/host/bench_sleep.py <gate> [--port PATH]

Gates (run one at a time; each prints instructions and results, nothing is
recorded automatically — copy results into sarg by hand):

    standby     RTC wake N s, catch the re-enumeration, print reset cause,
                RTC survival (a deliberately odd date set before sleep) and
                the TAMP backup registers, and wake-to-USB timing.
    button      sleep 60 s; report whether SW woke the board early (needs a
                hand on the button).
    lightsleep  same as `standby` but machine.lightsleep(ms) instead of
                machine.deepsleep() (PLAN §8 gate 2's STOP-mode fallback).
    sd          os.listdir('/'), '/sdcard', statvfs, a 1 MB write/read/
                rename timing, and whether /flash/main.py is still the boot
                script with a card fitted.
    wake_cost   run one wake of the bundled app from RAM (no flash writes)
                with a stubbed board_rest that records the requested sleep
                ms instead of sleeping; prints ms from start to rest.
    longwake    RTC.wakeup(13 h) accepted, then cancelled — no actual sleep.

DO NOT RUN THIS SCRIPT: every gate resets the live board (`mpremote reset`
at the end, deep sleep in between). The owner runs it by hand, one gate at
a time, after confirming nothing else needs the board on USB. Every gate
unmounts /media/wroscoe/PYBFLASH first (udisksctl, device found from
`mount`) — the classic way to corrupt the flash filesystem is the host's
FAT mount and the board's own flash writes racing each other.
"""
import argparse
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import serial
from serial.tools import list_ports

SERIAL_NUMBER = '31001c00025043364d343000'
BY_ID_GLOB = '/dev/serial/by-id/usb-MicroPython_Pyboard_Virtual_Comm_Port_in_FS_Mode_*-if00'
PYBFLASH_MOUNT = '/media/wroscoe/PYBFLASH'
BAUD = 115200


# --------------------------------------------------------------- plumbing ---

def find_port():
    for p in list_ports.comports():
        if (p.serial_number or '').lower() == SERIAL_NUMBER.lower():
            return p.device
    return None


def wait_for_port(timeout_s, absent_first=False):
    """Poll for the board's port. If absent_first, wait for it to
    disappear (the sleep taking effect) before waiting for it to return."""
    end = time.time() + timeout_s
    if absent_first:
        while find_port() and time.time() < end:
            time.sleep(0.02)
    while time.time() < end:
        p = find_port()
        if p:
            return p
        time.sleep(0.02)
    return None


def unmount_pyboard():
    """Find the PYBFLASH block device from `mount` and udisksctl-unmount
    it. A no-op (with a note) if it is not currently mounted."""
    out = subprocess.run(['mount'], capture_output=True, text=True).stdout
    dev = None
    for line in out.splitlines():
        if PYBFLASH_MOUNT in line:
            dev = line.split()[0]
            break
    if not dev:
        print('bench_sleep: %s not mounted, nothing to unmount' % PYBFLASH_MOUNT)
        return
    print('bench_sleep: unmounting %s (%s)' % (dev, PYBFLASH_MOUNT))
    subprocess.run(['udisksctl', 'unmount', '-b', dev], check=True)


def mpremote(port, *args, timeout=20, check=True):
    cmd = ['mpremote', 'connect', port] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def mpremote_exec(port, code, timeout=20):
    r = mpremote(port, 'exec', code, timeout=timeout, check=False)
    if r.stdout:
        print(r.stdout, end='')
    if r.returncode != 0 and r.stderr:
        print(r.stderr, file=sys.stderr, end='')
    return r


def mpremote_reset(port):
    print('bench_sleep: mpremote reset (app resumes)')
    subprocess.run(['mpremote', 'connect', port, 'reset'], timeout=15, check=False)


def raw_repl_exec(ser, code, timeout=8):
    """Send `code` over an already-open serial port using the raw REPL
    protocol (b'\\x01' enter, Ctrl-D run, b'\\x02' exit). Returns stdout."""
    ser.write(b'\r\x03\x03')            # interrupt whatever main.py is doing
    time.sleep(0.2)
    ser.reset_input_buffer()
    ser.write(b'\x01')                  # raw REPL
    time.sleep(0.2)
    ser.reset_input_buffer()
    ser.write(code.encode() + b'\x04')  # code + Ctrl-D (run)
    end = time.time() + timeout
    buf = b''
    while time.time() < end:
        chunk = ser.read(4096)
        if chunk:
            buf += chunk
            if buf.count(b'\x04') >= 2:      # OK<out>\x04<err>\x04
                break
        else:
            time.sleep(0.05)
    ser.write(b'\x02')                  # back to friendly REPL
    m = re.match(rb'OK(.*?)\x04(.*?)\x04', buf, re.S)
    if not m:
        return '', buf.decode('utf-8', 'replace')
    return m.group(1).decode('utf-8', 'replace'), m.group(2).decode('utf-8', 'replace')


# ------------------------------------------------------------------ gates ---

_SET_ODD_STATE = """
import machine, stm
rtc = machine.RTC()
rtc.datetime((2031, 6, 15, 1, 12, 0, 0, 0))
for i in range(2):
    stm.mem32[stm.TAMP_NS + 0x100 + 4 * i] = 0xC0FFEE00 + i
print('state set: rtc', rtc.datetime())
"""

_SLEEP_N = """
import machine, time
time.sleep_ms(50)
machine.RTC().wakeup(%d)
time.sleep_ms(50)
machine.deepsleep()
"""

_READ_STATE = """
import machine, stm, time
print('reset_cause', machine.reset_cause(), 'DEEPSLEEP_RESET', machine.DEEPSLEEP_RESET)
print('rtc', machine.RTC().datetime())
print('backup', [hex(stm.mem32[stm.TAMP_NS + 0x100 + 4 * i]) for i in range(2)])
print('ticks_ms', time.ticks_ms())
"""


def gate_standby(port, sleep_s):
    unmount_pyboard()
    print('bench_sleep: standby — setting RTC + backup registers, sleeping %ds' % sleep_s)
    mpremote_exec(port, _SET_ODD_STATE)
    t_sleep = time.time()
    # deepsleep() never returns a reply; the connection drops when the board
    # goes to standby, so run it fire-and-forget with a short timeout.
    try:
        mpremote_exec(port, _SLEEP_N % (sleep_s * 1000), timeout=3)
    except subprocess.TimeoutExpired:
        pass
    print('bench_sleep: waiting for the board to re-enumerate...')
    p = wait_for_port(sleep_s + 15, absent_first=True)
    if not p:
        print('bench_sleep: FAILED — port never came back')
        return
    t_back = time.time()
    print('bench_sleep: port back after %.2fs (sleep was %ds) — opening to interrupt main.py'
          % (t_back - t_sleep, sleep_s))
    ser = serial.Serial(p, BAUD, timeout=0.2)
    out, err = raw_repl_exec(ser, _READ_STATE)
    ser.close()
    print('--- board state after wake ---')
    print(out or err)
    print('bench_sleep: total wall time sleep-call -> USB back: %.2fs' % (t_back - t_sleep))
    mpremote_reset(p)


def gate_lightsleep(port, sleep_s):
    unmount_pyboard()
    print('bench_sleep: lightsleep — sleeping %ds with machine.lightsleep()' % sleep_s)
    mpremote_exec(port, _SET_ODD_STATE)
    code = """
import machine, time
time.sleep_ms(50)
t0 = time.ticks_ms()
machine.lightsleep(%d)
print('lightsleep returned after', time.ticks_diff(time.ticks_ms(), t0), 'ms')
""" % (sleep_s * 1000)
    r = mpremote_exec(port, code, timeout=sleep_s + 15)
    mpremote_reset(port)


def gate_button(port):
    unmount_pyboard()
    print('bench_sleep: button — sleeping 60s; PRESS SW ANY TIME to test an early wake')
    print('             (needs a hand — this gate cannot be automated)')
    mpremote_exec(port, _SET_ODD_STATE)
    t_sleep = time.time()
    try:
        mpremote_exec(port, _SLEEP_N % 60000, timeout=3)
    except subprocess.TimeoutExpired:
        pass
    p = wait_for_port(75, absent_first=True)
    if not p:
        print('bench_sleep: FAILED — port never came back')
        return
    elapsed = time.time() - t_sleep
    print('bench_sleep: port back after %.1fs' % elapsed)
    if elapsed < 55:
        print('bench_sleep: EARLY WAKE — SW (or something else) woke standby early')
    else:
        print('bench_sleep: no early wake seen — SW likely does not wake standby '
              '(PLAN §8 gate 2: consider SLEEP_MODE = "light")')
    mpremote_reset(p)


def gate_sd(port):
    unmount_pyboard()
    code = """
import os, time
print('listdir /', os.listdir('/'))
try:
    print('listdir /sdcard', os.listdir('/sdcard'))
    print('statvfs /sdcard', os.statvfs('/sdcard'))
    data = bytes(1024) * 1024   # 1 MB
    t0 = time.ticks_ms()
    with open('/sdcard/bench_sleep_tmp.bin', 'wb') as f:
        f.write(data)
    t_write = time.ticks_diff(time.ticks_ms(), t0)
    t0 = time.ticks_ms()
    with open('/sdcard/bench_sleep_tmp.bin', 'rb') as f:
        back = f.read()
    t_read = time.ticks_diff(time.ticks_ms(), t0)
    assert back == data
    t0 = time.ticks_ms()
    os.rename('/sdcard/bench_sleep_tmp.bin', '/sdcard/bench_sleep_tmp2.bin')
    t_rename = time.ticks_diff(time.ticks_ms(), t0)
    os.remove('/sdcard/bench_sleep_tmp2.bin')
    print('1MB write %dms read %dms rename %dms' % (t_write, t_read, t_rename))
except OSError as e:
    print('no /sdcard:', repr(e))
"""
    mpremote_exec(port, code, timeout=30)
    print('bench_sleep: also check the loader output over monitor.py for which main.py ran '
          '(the boot print includes the version) — with a card fitted the firmware may hand '
          'USB mass storage / main.py to the card instead of /flash.')
    mpremote_reset(port)


def gate_wake_cost(port):
    """Runs the bundled app from RAM (software/build/app.py must already be
    current — run tools/dustygen --no-stage first) with board_rest stubbed
    to record its ms argument instead of sleeping, so this gate never
    actually puts the board to sleep."""
    unmount_pyboard()
    app_py = Path(__file__).resolve().parents[1] / 'software' / 'build' / 'app.py'
    if not app_py.is_file():
        sys.exit('bench_sleep: %s not built; run tools/dustygen cameras/n6cam first' % app_py)
    with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as f:
        f.write(app_py.read_text())
        f.write("""
# --- bench_sleep wake_cost harness: stub the sleep call, run one wake ---
_rest_calls = []
def _stub_rest(ms):
    _rest_calls.append(ms)
    raise SystemExit
board_rest = _stub_rest
import time as _time
_t0 = _time.ticks_ms()
try:
    game_run(lambda: None)
except SystemExit:
    pass
print('wake_cost: %dms to rest(%r)' % (_time.ticks_diff(_time.ticks_ms(), _t0), _rest_calls))
""")
        tmp = f.name
    try:
        r = mpremote(port, 'run', tmp, timeout=30, check=False)
        print(r.stdout)
        if r.returncode != 0:
            print(r.stderr, file=sys.stderr)
    finally:
        Path(tmp).unlink(missing_ok=True)
    mpremote_reset(port)


def gate_longwake(port):
    unmount_pyboard()
    code = """
import machine
rtc = machine.RTC()
rtc.wakeup(13 * 3600 * 1000)
print('13h wakeup accepted')
rtc.wakeup(None)
print('cancelled')
"""
    mpremote_exec(port, code, timeout=15)
    mpremote_reset(port)


GATES = {
    'standby': lambda a: gate_standby(a.port, a.secs),
    'lightsleep': lambda a: gate_lightsleep(a.port, a.secs),
    'button': lambda a: gate_button(a.port),
    'sd': lambda a: gate_sd(a.port),
    'wake_cost': lambda a: gate_wake_cost(a.port),
    'longwake': lambda a: gate_longwake(a.port),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('gate', choices=sorted(GATES))
    ap.add_argument('--port', default=None, help='serial device (default: found by serial number)')
    ap.add_argument('--secs', type=int, default=10, help='sleep duration for standby/lightsleep (default 10)')
    a = ap.parse_args()
    a.port = a.port or find_port()
    if not a.port:
        sys.exit('bench_sleep: board not found by serial number %s — pass --port' % SERIAL_NUMBER)
    print('bench_sleep: gate=%s port=%s' % (a.gate, a.port))
    GATES[a.gate](a)


if __name__ == '__main__':
    main()
