"""Bay coupon, print-oriented: the top 33 mm of the ring (Y >= 48) turned so
its back mouth (Z_PLATE) is the bed at z = 0 and the eave points up — the
same way the full ring prints.  Tests the ledges, corner blocks, stop ribs,
hooks and the front-plate lip fit with the real board.  ~15 min.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build123d import Align, Box, Pos, Rot     # noqa: E402

import puckcase_lib as L                       # noqa: E402

COUPON_Y = 48.0


def gen_step():
    keep = Pos(-5.0, COUPON_Y, L.Z_EAVE - 2.0) * Box(
        L.OUT_W + 10.0, L.OUT_H, L.Z_PLATE - L.Z_EAVE + 4.0, align=(Align.MIN,) * 3)
    part = L.ring() & keep
    # flip 180 deg about X: model Z_PLATE (back mouth) -> bed z = 0, eave up
    part = Pos(0, 0, L.Z_PLATE) * Rot(180, 0, 0) * part
    part.label = "coupon_ring_bay"
    return part


if __name__ == "__main__":
    p = gen_step()
    print(p.label, len(p.solids()), p.is_valid, round(p.volume, 2), p.bounding_box())
