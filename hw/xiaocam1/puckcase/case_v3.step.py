"""Review-only: the whole v3 case assembled — front plate, ring, back plate,
holder and the board envelope (with headers) in place.  Not printable.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cadgen import step          # noqa: E402
import v3case as C               # noqa: E402


@step(out="case_v3.step")
def gen_step():
    return C.assembly()


if __name__ == "__main__":
    gen_step()
