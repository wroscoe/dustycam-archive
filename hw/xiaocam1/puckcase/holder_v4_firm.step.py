"""puckcase v4 holder_v4_firm — as holder_v4 but with 2 larger ribs per leg (0.32 proud -> 0.17 crush/side).

Grip-rib variant for the board fit trial (Wade 2026-09-15).  Geometry is
otherwise identical to holder_v4; only v3lib.RIB_SETS["firm"] differs.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cadgen import step, stl, threemf   # noqa: E402
import v4case as C               # noqa: E402

KW = dict(C.HOLDER_KW, ribs="firm")


@step(out="holder_v4_firm.step")
def gen_step():
    return C.H.holder(label="holder_v4_firm", **KW)


@stl(out="print/holder_v4_firm.stl")
@threemf(out="print/holder_v4_firm.3mf")
def holder_v4_firm_print():
    p = C.H.holder_print_oriented(**KW)
    p.label = "holder_v4_firm_print"
    return p


if __name__ == "__main__":
    gen_step()
    holder_v4_firm_print()
