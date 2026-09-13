"""Review-only: cut at X = 22.9, through the middle of the snap tongue, so the
tongue, its lip and ramp, the bridge band and the card notch read.  Scratch."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from cadgen import step                          # noqa: E402
from build123d import Align, Box, Pos            # noqa: E402

import puckcase_lib as L                         # noqa: E402
from _sectionlib import sectioned                # noqa: E402

X_TONGUE = 22.9


@step(out="section_tongue.step")
def gen_step():
    cut = Pos(X_TONGUE, -20, -20) * Box(60, 130, 90, align=(Align.MIN,) * 3)
    return sectioned(cut, "puckcase_v2_section_tongue")


if __name__ == "__main__":
    gen_step()
