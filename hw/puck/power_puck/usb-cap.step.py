"""USB-C port cap — printable part.  Orientation: head down (outer face on the bed)."""

from caselib import usb_cap


def gen_step():
    return usb_cap()


if __name__ == "__main__":
    print(gen_step().bounding_box())
