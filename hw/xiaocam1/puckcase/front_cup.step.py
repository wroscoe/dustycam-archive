"""puckcase v4 front_cup — prints face down (Z 0 on the bed), open back mouth up (v4case.py)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cadgen import step, stl, threemf   # noqa: E402
import v4case as C               # noqa: E402


@step(out="front_cup.step")
def gen_step():
    return C.front_cup()


@stl(out="print/front_cup.stl")
@threemf(out="print/front_cup.3mf")
def front_cup_print():
    p = C.front_cup()
    p.label = "front_cup_print"
    return p


if __name__ == "__main__":
    gen_step()
    front_cup_print()
