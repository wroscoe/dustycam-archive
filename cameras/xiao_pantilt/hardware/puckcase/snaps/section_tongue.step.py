"""Review-only detail: the USB end cut at X = 30.2, through the middle of snap
tongue A, and clipped to the tongue's neighbourhood so it fills the frame.
Shows the tongue, its lip and 45 deg cam ramp, the root strip at the bed, the
PCB's end edge and the fact that there is no wall left above the lip.
Scratch .step, not committed."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from cadgen import step                          # noqa: E402
from build123d import Align, Box, Compound, Pos  # noqa: E402

import puckcase_lib as L                         # noqa: E402

X_TONGUE = 30.2
KEEP = (11.0, X_TONGUE, 62.0, 79.0, 12.0, 27.0)   # X0 X1 Y0 Y1 Z0 Z1


@step(out="section_tongue.step")
def gen_step():
    x0, x1, y0, y1, z0, z1 = KEEP
    keep = Pos(x0, y0, z0) * Box(x1 - x0, y1 - y0, z1 - z0,
                                 align=(Align.MIN,) * 3)
    parts = []
    for src in [L.ring()] + list(L.xiao_envelope().children) \
            + list(L.header_mock().children):
        q = src & keep
        if q is None or q.volume <= 1e-6:
            continue
        q.label = (getattr(src, "label", "part") or "part") + "_detail"
        q.color = getattr(src, "color", None)
        parts.append(q)
    asm = Compound(children=parts)
    asm.label = "puckcase_v2_tongue_detail"
    return asm


if __name__ == "__main__":
    gen_step()
