"""Front plate — printable part.  Outer-face down (z = 0 on the bed)."""

from caselib import front_plate


def gen_step():
    return front_plate()


if __name__ == "__main__":
    print(gen_step().bounding_box())
