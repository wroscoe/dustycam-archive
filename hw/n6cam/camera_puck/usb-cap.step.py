"""Camera puck USB cap — printable part.  Press-in plug for the front cup's
USB-C port.  Prints head-down (outer face on the bed).  No supports.  See
caselib.py usb_cap() / README.md."""

from caselib import usb_cap


def gen_step():
    return usb_cap()


if __name__ == "__main__":
    part = gen_step()
    bb = part.bounding_box()
    print(bb)
    if bb.min.Y >= -13.60 - 1e-6:
        print("WARNING: cap head does not extend outside OUT_Y0 -- check rotation")
