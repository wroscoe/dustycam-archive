"""Front-plate coupon, print-oriented: the top 33 mm of the front plate
(Y >= 48) — lens hole, posts and the top part of the lip — outer face on the
bed exactly as the full plate prints.  Pairs with coupon_ring_bay.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build123d import Align, Box, Pos          # noqa: E402

import puckcase_lib as L                       # noqa: E402

COUPON_Y = 48.0


def gen_step():
    keep = Pos(-5.0, COUPON_Y, -2.0) * Box(
        L.OUT_W + 10.0, L.OUT_H, L.Z_PLATE, align=(Align.MIN,) * 3)
    part = L.front_plate() & keep
    part.label = "coupon_front_plate"
    return part


if __name__ == "__main__":
    p = gen_step()
    print(p.label, len(p.solids()), p.is_valid, round(p.volume, 2), p.bounding_box())
