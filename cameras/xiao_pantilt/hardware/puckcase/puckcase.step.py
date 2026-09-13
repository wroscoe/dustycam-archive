"""puckcase v1 — assembled view: the 3 printed parts + the vendor XIAO + the
4 screws, as a labelled Compound.  Not a printable artifact."""

from build123d import Compound

import puckcase_lib as L


def gen_step():
    parts = [L.front_plate(), L.ring(), L.back_plate(), L.xiao_vendor()]
    parts += L.screw_mocks()
    asm = Compound(children=parts)
    asm.label = "puckcase_v1"
    return asm


if __name__ == "__main__":
    a = gen_step()
    print(a.label, len(a.children), a.bounding_box())
