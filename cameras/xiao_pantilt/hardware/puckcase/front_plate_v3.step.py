"""puckcase v3 front plate — printable.  v2.4 plate without the head window
boss, lens hole at the v3 lens position.  Prints outer face down.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cadgen import step          # noqa: E402
import v3case as C               # noqa: E402


@step(out="front_plate_v3.step")
def gen_step():
    return C.front_plate()


if __name__ == "__main__":
    gen_step()
