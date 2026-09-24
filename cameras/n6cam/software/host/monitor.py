#!/usr/bin/env python3
"""Reconnecting USB serial monitor for the N6.

    uv run --offline --no-project --with pyserial python software/host/monitor.py [--log FILE] [--secs N] [--interrupt]

pyserial is not a project dependency; it comes from mpremote's own
environment (`mpremote` vendors pyserial), or `uv run --with pyserial` as
above pulls it into an ephemeral venv without installing anything on the
host. Do NOT run this with the project's own interpreter unless pyserial is
already importable there.

Why this exists (not xiao_pantilt's monitor.py): the N6's USB CDC port
drops and RE-ENUMERATES on every reset AND on every deep-sleep wake
(board.py's game_lowpower board_rest() -> machine.deepsleep(); PLAN.md §0
bench facts: USB drops ~1.1 s after deepsleep(), back ~2 s after the wake).
So this monitor finds the port by its fixed serial number (not a bare
/dev/ttyACM* path, which moves), and reopens on every loss instead of
exiting — a plain-usage session sits through however many wake cycles
happen while it's running.

Sends NOTHING to the board unless --interrupt is passed (then only after
the port reopens, once, the same Ctrl-C + Ctrl-C + raw-REPL bytes
bench_sleep.py uses to catch a wake). Without --interrupt this is pure
listen-only: safe to leave running across the board's own deep-sleep cycle.
"""
import argparse
import sys
import time

import serial
from serial.tools import list_ports

SERIAL_NUMBER = '31001c00025043364d343000'
BAUD = 115200
INTERRUPT_BYTES = b'\r\x03\x03'    # two Ctrl-C (stop any running program)


def find_port():
    for p in list_ports.comports():
        if (p.serial_number or '').lower() == SERIAL_NUMBER.lower():
            return p.device
    return None


def open_port(port, interrupt):
    s = serial.Serial(port, BAUD, timeout=0.2)
    if interrupt:
        s.write(INTERRUPT_BYTES)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--log', default=None, help='append timestamped lines to FILE')
    ap.add_argument('--secs', type=float, default=0, help='exit after N seconds (default: run until Ctrl-C)')
    ap.add_argument('--interrupt', action='store_true',
                     help='send Ctrl-C x2 once after each (re)connect — off by default; NEVER sent otherwise')
    a = ap.parse_args()
    log = open(a.log, 'a') if a.log else None
    t0 = time.time()
    s = None
    buf = b''
    port = None
    try:
        while True:
            if s is None:
                port = find_port()
                if port is None:
                    if a.secs and time.time() - t0 > a.secs:
                        break
                    time.sleep(0.3)
                    continue
                try:
                    s = open_port(port, a.interrupt)
                except (serial.SerialException, OSError):
                    if a.secs and time.time() - t0 > a.secs:
                        break
                    time.sleep(0.3)
                    continue
                print('%s monitor: %s open%s' %
                      (time.strftime('%H:%M:%S'), port, ' (interrupt sent)' if a.interrupt else ''),
                      file=sys.stderr)
            try:
                chunk = s.read(4096)
            except (serial.SerialException, OSError):
                print('%s monitor: %s gone (reset or deep-sleep wake?)' % (time.strftime('%H:%M:%S'), port),
                      file=sys.stderr)
                try:
                    s.close()
                except Exception:
                    pass
                s = None
                continue
            if chunk:
                buf += chunk
                while b'\n' in buf:
                    line, buf = buf.split(b'\n', 1)
                    out = '%s %s' % (time.strftime('%H:%M:%S'), line.decode('utf-8', 'replace').rstrip('\r'))
                    print(out, flush=True)
                    if log:
                        log.write(out + '\n')
                        log.flush()
            if a.secs and time.time() - t0 > a.secs:
                break
    except KeyboardInterrupt:
        pass
    finally:
        if s is not None:
            try:
                s.close()
            except Exception:
                pass
        if log:
            log.close()


if __name__ == '__main__':
    main()
