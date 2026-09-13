"""Review-only: cut at Y = 58, across the side rails, so the rails, their
45 deg undersides, the crush ribs and the expansion PCB edges read.  Scratch."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from cadgen import step                          # noqa: E402
from build123d import Align, Box, Pos            # noqa: E402

import puckcase_lib as L                         # noqa: E402
from _sectionlib import sectioned                # noqa: E402

Y_RAILS = 58.0


@step(out="section_rails.step")
def gen_step():
    cut = Pos(-10, Y_RAILS, -20) * Box(70, 130, 90, align=(Align.MIN,) * 3)
    return sectioned(cut, "puckcase_v2_section_rails")


if __name__ == "__main__":
    gen_step()
