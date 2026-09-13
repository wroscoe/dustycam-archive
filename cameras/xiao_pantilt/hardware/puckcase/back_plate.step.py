"""Back plate — printable part.  Front face down (Z = 20.36 on the bed), lip up."""

from puckcase_lib import back_plate


def gen_step():
    return back_plate()


if __name__ == "__main__":
    p = gen_step()
    print(p.label, len(p.solids()), p.is_valid, round(p.volume, 2), p.bounding_box())
