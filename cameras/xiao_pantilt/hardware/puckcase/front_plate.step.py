"""Front plate — printable part.  Outer face down (Z = 0 on the bed)."""

from puckcase_lib import front_plate


def gen_step():
    return front_plate()


if __name__ == "__main__":
    p = gen_step()
    print(p.label, len(p.solids()), p.is_valid, round(p.volume, 2), p.bounding_box())
