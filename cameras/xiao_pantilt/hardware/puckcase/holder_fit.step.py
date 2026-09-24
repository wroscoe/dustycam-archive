"""Review-only: holder + the board envelope WITH pin headers,
seated, in the board frame.  Not printable; check_v3.py builds the same
occurrences itself.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cadgen import step                 # noqa: E402
from build123d import Compound          # noqa: E402

import v3lib as L                       # noqa: E402


@step(out="holder_fit.step")
def gen_step():
    parts = [L.holder()]
    parts += list(L.board_mocks(headers=True).values())
    return Compound(children=parts, label="holder_fit")


if __name__ == "__main__":
    gen_step()
