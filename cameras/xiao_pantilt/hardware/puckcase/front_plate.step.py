"""Front plate — printable part.  Outer face down (Z = 0 on the bed), lip up.
v2: no posts; hole + chamfer at the new LENS_YC 67.76.
"""

from cadgen import step

from puckcase_lib import front_plate


@step(out="front_plate.step")
def gen_step():
    return front_plate()


if __name__ == "__main__":
    p = gen_step()
