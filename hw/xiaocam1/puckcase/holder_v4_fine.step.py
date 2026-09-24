"""puckcase v4 holder_v4_fine — as holder_v4 but with 4 small ribs per leg (0.20 proud -> 0.05 crush/side).

Grip-rib variant for the board fit trial (Wade 2026-09-15).  Geometry is
otherwise identical to holder_v4; only v3lib.RIB_SETS["fine"] differs.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cadgen import step, stl, threemf   # noqa: E402
import v4case as C               # noqa: E402

KW = dict(C.HOLDER_KW, ribs="fine")


@step(out="holder_v4_fine.step")
def gen_step():
    return C.H.holder(label="holder_v4_fine", **KW)


@stl(out="print/holder_v4_fine.stl")
@threemf(out="print/holder_v4_fine.3mf")
def holder_v4_fine_print():
    p = C.H.holder_print_oriented(**KW)
    p.label = "holder_v4_fine_print"
    return p


if __name__ == "__main__":
    gen_step()
    holder_v4_fine_print()
