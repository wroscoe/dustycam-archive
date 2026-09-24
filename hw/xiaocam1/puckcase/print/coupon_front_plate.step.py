"""Front-plate coupon, print-oriented: the top 36.8 mm of the v2 front plate
(Y >= 44) — the lens hole at the new LENS_YC, its chamfer and the top part of
the lip — outer face on the bed exactly as the full plate prints.  v2 has no
posts.  Pairs with coupon_ring_bay.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cadgen import stl, threemf          # noqa: E402
from build123d import Align, Box, Pos    # noqa: E402

import puckcase_lib as L                 # noqa: E402

COUPON_Y = 44.0


@stl(out="coupon_front_plate.stl")
@threemf(out="coupon_front_plate.3mf")
def gen_step():
    keep = Pos(-5.0, COUPON_Y, -2.0) * Box(
        L.OUT_W + 10.0, L.OUT_H, L.Z_PLATE, align=(Align.MIN,) * 3)
    part = L.front_plate() & keep
    part.label = "coupon_front_plate"
    return part


if __name__ == "__main__":
    p = gen_step()
