"""puckcase v4 back_plate_v4 — drops into the cup's rebate, edge crush ribs, puck lip on the back; prints front face down (v4case.py)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cadgen import step, stl, threemf   # noqa: E402
import v4case as C               # noqa: E402


@step(out="back_plate_v4.step")
def gen_step():
    return C.back_plate()


@stl(out="print/back_plate_v4.stl")
@threemf(out="print/back_plate_v4.3mf")
def back_plate_v4_print():
    from build123d import Pos, Rot
    p = Pos(0, 0, -C.Z_REB0) * C.back_plate()
    p.label = "back_plate_v4_print"
    return p


if __name__ == "__main__":
    gen_step()
    back_plate_v4_print()
