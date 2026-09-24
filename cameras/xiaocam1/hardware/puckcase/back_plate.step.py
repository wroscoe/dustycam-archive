"""Back plate — printable part.  Front face down (Z = 26.36 on the bed), the
power puck's lip up.  v2: Z shift only (BACK_GAP 3.0 -> 9.0).
"""

from cadgen import step

from puckcase_lib import back_plate


@step(out="back_plate.step")
def gen_step():
    return back_plate()


if __name__ == "__main__":
    p = gen_step()
