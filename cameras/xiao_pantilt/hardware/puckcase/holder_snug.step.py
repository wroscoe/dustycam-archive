"""puckcase v3.1 camera holder, SNUG variant — for a XIAO that will never get
pin headers: the lip sits 0.15 under the PCB back instead of under the header
body, so a bare board has no z play.  Same factory as holder.step.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cadgen import step, stl, threemf   # noqa: E402

import v3lib as L                       # noqa: E402


@step(out="holder_snug.step")
def gen_step():
    return L.holder(lip_under="pcb", label="holder_snug")


@stl(out="print/holder_snug.stl")
@threemf(out="print/holder_snug.3mf")
def holder_snug_print():
    p = L.holder_print_oriented(lip_under="pcb")
    p.label = "holder_snug_print"
    return p


if __name__ == "__main__":
    gen_step()
    holder_snug_print()
