"""Review-only: the v3 case exploded along Z — front plate 20 forward, holder
+ board 10 forward (ears out of the notches), back plate 12 back.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cadgen import step          # noqa: E402
import v3case as C               # noqa: E402


@step(out="case_v3_exploded.step")
def gen_step():
    return C.assembly(explode=20.0)


if __name__ == "__main__":
    gen_step()
