"""Review-only half model: everything cut away for X > CX, so the wall / bay /
collar / lip stack reads in one image.  Scratch .step, not committed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cadgen import step                                  # noqa: E402
from build123d import Align, Box, Pos                    # noqa: E402

import puckcase_lib as L                                 # noqa: E402
from _sectionlib import sectioned                        # noqa: E402


@step(out="section_cx.step")
def gen_step():
    cut = Pos(L.CX, -20, -20) * Box(60, 130, 90, align=(Align.MIN,) * 3)
    return sectioned(cut, "puckcase_v2_section_CX")


if __name__ == "__main__":
    gen_step()
