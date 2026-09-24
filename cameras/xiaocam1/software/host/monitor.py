#!/usr/bin/env python3
"""Serial monitor for the XIAO over its native USB-Serial-JTAG console.

    software/host/monitor.py [PORT] [--reset] [--log FILE] [--send TEXT] [--secs N]

Opening the port resets the board only when --reset is given (DTR/RTS are
held low otherwise, so a deep-sleeping camera is not disturbed). Lines are
timestamped and optionally appended to --log. --send writes TEXT + newline
after opening; --secs exits after N seconds (default: run until Ctrl-C).
The XIAO enumerates as 303a:1001 "USB JTAG/serial debug unit". The port
disappears while the board deep-sleeps and re-enumerates on every wake, so
the monitor reconnects (polling every 0.5 s) instead of exiting.
"""
import argparse
import sys
import time

import serial


def find_port():
    try:
        from serial.tools import list_ports
    except ImportError:
        return '/dev/ttyACM1'
    for p in list_ports.comports():
        if p.vid == 0x303a and p.pid == 0x1001:
            return p.device
    return '/dev/ttyACM1'


def open_port(port, reset):
    s = serial.Serial(port, 115200, timeout=0.2, dsrdtr=False, rtscts=False)
    if reset:
        s.dtr = False; s.rts = True; time.sleep(0.1); s.rts = False
    else:
        s.dtr = False; s.rts = False
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('port', nargs='?', default=None)
    ap.add_argument('--reset', action='store_true', help='pulse DTR/RTS to reset the board on open')
    ap.add_argument('--log', default=None)
    ap.add_argument('--send', default=None)
    ap.add_argument('--secs', type=float, default=0)
    a = ap.parse_args()
    log = open(a.log, 'a') if a.log else None
    t0 = time.time()
    port = a.port or find_port()
    s = None
    buf = b''
    first = True
    try:
        while True:
            if s is None:
                try:
                    s = open_port(port, a.reset and first)
                except (serial.SerialException, OSError):
                    if a.secs and time.time() - t0 > a.secs:
                        break
                    time.sleep(0.5)
                    port = a.port or find_port()
                    continue
                print('%s monitor: %s open%s' % (time.strftime('%H:%M:%S'), port, ' (reset)' if a.reset and first else ''), file=sys.stderr)
                first = False
                if a.send:
                    s.write(a.send.encode() + b'\n')
            try:
                chunk = s.read(4096)
            except (serial.SerialException, OSError):
                print('%s monitor: %s gone (board asleep?)' % (time.strftime('%H:%M:%S'), port), file=sys.stderr)
                s.close(); s = None
                continue
            if chunk:
                buf += chunk
                while b'\n' in buf:
                    line, buf = buf.split(b'\n', 1)
                    out = '%s %s' % (time.strftime('%H:%M:%S'), line.decode('utf-8', 'replace').rstrip('\r'))
                    print(out, flush=True)
                    if log:
                        log.write(out + '\n'); log.flush()
            if a.secs and time.time() - t0 > a.secs:
                break
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
