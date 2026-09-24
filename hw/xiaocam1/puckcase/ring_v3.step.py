"""puckcase v3 ring — printable.  v2.4 shell/eave/bosses/cord slot with the
board bay replaced by two notched walls and two ledges for the v3.1 holder.
Prints standing on its back mouth (Z 26.36 on the bed), eave up.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cadgen import step          # noqa: E402
import v3case as C               # noqa: E402


@step(out="ring_v3.step")
def gen_step():
    return C.ring()


if __name__ == "__main__":
    gen_step()
