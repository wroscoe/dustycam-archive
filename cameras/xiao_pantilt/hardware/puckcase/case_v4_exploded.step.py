"""puckcase v4 case_v4_exploded — review-only, exploded along Z (v4case.py)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cadgen import step          # noqa: E402
import v4case as C               # noqa: E402


@step(out="case_v4_exploded.step")
def gen_step():
    return C.assembly(explode=18.0)


if __name__ == "__main__":
    gen_step()
