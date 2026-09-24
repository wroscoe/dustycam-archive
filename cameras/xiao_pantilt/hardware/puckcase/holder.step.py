"""puckcase v3.1 camera holder — printable part, BOARD frame (v3lib.py).
Universal: the lip sits under the header body, so it takes a XIAO with or
without pin headers.  STEP in the design frame; STL/3MF print-oriented
(standing on the end wall, open end up).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cadgen import step, stl, threemf   # noqa: E402

import v3lib as L                       # noqa: E402


@step(out="holder.step")
def gen_step():
    return L.holder(lip_under="header")


@stl(out="print/holder.stl")
@threemf(out="print/holder.3mf")
def holder_print():
    p = L.holder_print_oriented(lip_under="header")
    p.label = "holder_print"
    return p


if __name__ == "__main__":
    gen_step()
    holder_print()
