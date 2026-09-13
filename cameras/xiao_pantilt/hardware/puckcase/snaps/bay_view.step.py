"""Review-only: the v2 ring with the board and header mock in place and the
front plate removed, so the bay reads from the front.  Writes bay_view.step
beside itself; that .step is a scratch artifact and is not committed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cadgen import step                  # noqa: E402
from build123d import Compound           # noqa: E402

import puckcase_lib as L                 # noqa: E402


@step(out="bay_view.step")
def gen_step():
    asm = Compound(children=[L.ring(), L.xiao_envelope(), L.header_mock(),
                             L.lead_mock(), L.antenna_mock(),
                             L.cable_mock(), L.ufl_plug_mock()])
    asm.label = "puckcase_v2_bay"
    return asm


if __name__ == "__main__":
    gen_step()
