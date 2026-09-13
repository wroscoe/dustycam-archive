"""Review-only: the insertion frame, sectioned at X = CX so the tilt reads —
the ring with the PCB assembly tilted -13 deg about its far-edge back corner,
the head held 1.3 short of the collar window and the card left out (it cannot
swing in; see checks.md).  Scratch .step, not committed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cadgen import step                          # noqa: E402
from build123d import Align, Box, Compound, Pos  # noqa: E402

import puckcase_lib as L                         # noqa: E402

ANGLE = -13.0
SHORT = 1.30


@step(out="tilt_insertion.step")
def gen_step():
    board = L.xiao_envelope(pre=L.tilt_loc(ANGLE), label="board_tilted",
                            skip=("camera_head", "lens_", "microsd_card"))
    z_nom = L.bZ(L.B.CAM_HEAD[5])
    dz = (L.bZ(L.COLLAR_BZ[0]) + SHORT) - z_nom
    head = L.xiao_envelope(post=Pos(0, 0, dz), label="head_entering",
                           skip=("pcb", "usb", "can", "b2b", "ufl", "microsd",
                                 "fpc", "button"))
    cut = Pos(L.CX, -20, -20) * Box(60, 130, 90, align=(Align.MIN,) * 3)
    parts = []
    for src in [L.ring()] + list(board.children) + list(head.children):
        q = src - cut
        if q.volume > 1e-6:
            q.label = (getattr(src, "label", "part") or "part") + "_sectioned"
            q.color = getattr(src, "color", None)
            parts.append(q)
    asm = Compound(children=parts)
    asm.label = "puckcase_v2_tilt_insertion"
    return asm


if __name__ == "__main__":
    gen_step()
