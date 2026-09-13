"""Review-only close-up: the top 33 mm of the ring (Y >= 48) — DESIGN.md's
"bay coupon" — so the ledges, corner blocks, stop ribs and hooks can be read.
Not a printable artifact as-is (it is also the coupon geometry to test-print).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build123d import Align, Box, Pos          # noqa: E402

import puckcase_lib as L                       # noqa: E402

COUPON_Y = 48.0


def gen_step():
    keep = Pos(-5.0, COUPON_Y, L.Z_EAVE - 2.0) * Box(
        L.OUT_W + 10.0, L.OUT_H, L.Z_PLATE - L.Z_EAVE + 4.0, align=(Align.MIN,) * 3)
    part = L.ring() & keep
    part.label = "ring_bay_coupon"
    return part


if __name__ == "__main__":
    p = gen_step()
    print(p.label, len(p.solids()), p.is_valid, round(p.volume, 2), p.bounding_box())
