"""puckcase v2 — assembled view: the 3 printed parts + the vendor XIAO + the
header mock + the 4 screws, as a labelled Compound.

Not a printable artifact and its .step is NOT written (it is large and only
ever looked at); build it in-process for snapshots and reviews.
"""

from build123d import Compound

import puckcase_lib as L


def gen_step():
    parts = [L.front_plate(), L.ring(), L.back_plate(), L.xiao_vendor(),
             L.header_mock()]
    parts += L.screw_mocks()
    asm = Compound(children=parts)
    asm.label = "puckcase_v2"
    return asm


if __name__ == "__main__":
    a = gen_step()
    print(a.label, len(a.children), a.bounding_box())
