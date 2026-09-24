"""Review-only: the insertion frame, sectioned at X = CX so the tilt reads —
the ring with the WHOLE board tilted -13 deg about its far-edge back corner,
card fitted and the camera head riding in with it.

v2.4: the collar is gone from the ring, so the head no longer has to be fed
separately into a window on the way in — it swings in rigidly with the PCB at
0.0000 mm^3 against the ring at every angle (check.py group 6), and the front
plate's head window boss drops over it afterwards.  Scratch .step, not
committed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cadgen import step                          # noqa: E402
from build123d import Align, Box, Compound, Pos  # noqa: E402

import puckcase_lib as L                         # noqa: E402

ANGLE = -13.0


@step(out="tilt_insertion.step")
def gen_step():
    board = L.xiao_envelope(pre=L.tilt_loc(ANGLE), label="board_tilted")
    cut = Pos(L.CX, -20, -20) * Box(60, 130, 90, align=(Align.MIN,) * 3)
    parts = []
    for src in [L.ring()] + list(board.children):
        q = src - cut
        if q.volume > 1e-6:
            q.label = (getattr(src, "label", "part") or "part") + "_sectioned"
            q.color = getattr(src, "color", None)
            parts.append(q)
    asm = Compound(children=parts)
    asm.label = "puckcase_v24_tilt_insertion"
    return asm


if __name__ == "__main__":
    gen_step()
