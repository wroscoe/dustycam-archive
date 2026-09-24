"""Scratch: ring + seated holder + board, no front plate (looking in from the front)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cadgen import step
from build123d import Compound
import v3case as C

@step(out="ring_holder_view.step")
def gen_step():
    parts = [C.ring(), C.holder_in_case()] + C.board_in_case(True)
    return Compound(children=parts, label="ring_holder_view")

if __name__ == "__main__":
    gen_step()
