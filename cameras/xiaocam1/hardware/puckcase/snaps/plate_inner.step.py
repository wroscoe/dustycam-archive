"""Review-only: the v2.4 front plate seen from its INNER side, so the head
window boss reads — the 11.8 square boss on the plate's inner face, its 8.6
window with the 0.6 lead-in at the mouth, the step at Z 6.86, the Ø8.25 bore
down to the plate's own Ø7.5 lens hole, and the FPC relief cut in the boss's
-Y wall.  The boss is the ring's old collar, moved to the part that prints it
as a floor instead of a 129 mm^2 bridge.  Scratch .step, not committed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cadgen import step                          # noqa: E402

import puckcase_lib as L                         # noqa: E402


@step(out="plate_inner.step")
def gen_step():
    p = L.front_plate()
    p.label = "front_plate_inner"
    return p


if __name__ == "__main__":
    gen_step()
