#!/usr/bin/env python3
"""Capture the XIAO's USB-Serial-JTAG console WITHOUT resetting the chip.

pyserial's open() updates DTR and RTS in two separate steps; the moment
DTR=0 while RTS=1 is the ESP32-S3 USB-Serial-JTAG reset condition, so every
pyserial open rebooted the board (verified 2026-09-16). A raw os.open() lets
the kernel raise DTR and RTS together, which does not reset it."""
import os, sys, time, termios, tty

PORT = "/dev/serial/by-id/usb-Espressif_USB_JTAG_serial_debug_unit_1C:DB:D4:76:AF:3C-if00"
OUT = sys.argv[1]
DUR = int(sys.argv[2]) if len(sys.argv) > 2 else 600

def stamp(f, msg):
    f.write(("\n--- %s %s ---\n" % (msg, time.strftime("%H:%M:%S"))).encode())

end = time.time() + DUR
f = open(OUT, "ab", buffering=0)
stamp(f, "safecap start")
while time.time() < end:
    if not os.path.exists(PORT):
        time.sleep(0.05)
        continue
    try:
        fd = os.open(PORT, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
    except OSError:
        time.sleep(0.05)
        continue
    try:
        tty.setraw(fd)  # line discipline only; does not touch DTR/RTS
    except termios.error:
        pass
    stamp(f, "port opened")
    try:
        while time.time() < end:
            try:
                b = os.read(fd, 4096)
            except BlockingIOError:
                time.sleep(0.02)
                continue
            if not b:
                break
            f.write(b)
    except OSError as e:
        stamp(f, "port lost (%s)" % e.strerror)
    finally:
        os.close(fd)
stamp(f, "safecap end")
