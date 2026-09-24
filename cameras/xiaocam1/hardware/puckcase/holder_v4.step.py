"""puckcase v4 holder_v4 — C-channel with the dovetail rail, board frame; prints face down (v4case.py)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cadgen import step, stl, threemf   # noqa: E402
import v4case as C               # noqa: E402


@step(out="holder_v4.step")
def gen_step():
    return C.H.holder(**C.HOLDER_KW)


@stl(out="print/holder_v4.stl")
@threemf(out="print/holder_v4.3mf")
def holder_v4_print():
    p = C.H.holder_print_oriented(**C.HOLDER_KW)
    p.label = "holder_v4_print"
    return p


if __name__ == "__main__":
    gen_step()
    holder_v4_print()
