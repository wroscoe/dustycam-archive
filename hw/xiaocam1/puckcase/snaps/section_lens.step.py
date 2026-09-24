"""Review-only detail: the lens stack cut along Y at X = LENS_XC (= CX) and
clipped to the head's neighbourhood so it fills the frame.  Shows the v2.4
stack front to back: the front plate with its head window boss, the 8.6 window
holding the 8 x 8 camera head, the Ø8.25 bore round the barrel, the plate's
Ø7.5 lens hole with the lens tip 1.0 behind it, the eave overhead, the SD card
and its 4.0 roof, and the fact that the ring's bay is now empty forward of the
side walls' Z 8.70.  Scratch .step, not committed."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from cadgen import step                          # noqa: E402
from build123d import Align, Box, Compound, Pos  # noqa: E402

import puckcase_lib as L                         # noqa: E402

KEEP = (8.0, L.LENS_XC, 55.0, 80.80, -9.0, 20.0)   # X0 X1 Y0 Y1 Z0 Z1


@step(out="section_lens.step")
def gen_step():
    x0, x1, y0, y1, z0, z1 = KEEP
    keep = Pos(x0, y0, z0) * Box(x1 - x0, y1 - y0, z1 - z0,
                                 align=(Align.MIN,) * 3)
    parts = []
    for src in [L.front_plate(), L.ring()] + list(L.xiao_envelope().children):
        q = src & keep
        if q is None or q.volume <= 1e-6:
            continue
        q.label = (getattr(src, "label", "part") or "part") + "_lens"
        q.color = getattr(src, "color", None)
        parts.append(q)
    asm = Compound(children=parts)
    asm.label = "puckcase_v24_lens_section"
    return asm


if __name__ == "__main__":
    gen_step()
