"""Bay coupon, print-oriented: the top 36.8 mm of the v2 ring (Y >= 44, so
the far-end wall, stop ribs, hooks and centre ledge come with it) turned so
its back mouth (Z_PLATE) is the bed at z = 0 and the eave points up — the same
way the full ring prints.

Tests everything the v1 coupon could not: the header-clearing side walls, the
far-end groove, the USB-end wall's shell window / bridge / card notch / snap
tongue, the expansion-PCB rails with their crush ribs, and the lens collar.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cadgen import stl, threemf              # noqa: E402
from build123d import Align, Box, Pos, Rot   # noqa: E402

import puckcase_lib as L                     # noqa: E402

COUPON_Y = 44.0


@stl(out="coupon_ring_bay.stl")
@threemf(out="coupon_ring_bay.3mf")
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
