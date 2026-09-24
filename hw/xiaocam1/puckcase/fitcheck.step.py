"""Review-only fit check: every occurrence in place — the 3 printed parts, the
puck tube the back plate presses into, the vendor XIAO, the header mock
DESIGN_v2 §1 assumes, the measured board envelope, the U.FL plug and cable,
the LOAD lead, the antenna flag and the 4 screws.

NOT a printable artifact, and its .step is not written (it is large and only
ever looked at).  check.py imports printed_parts() / reference_parts() from
here so the checked occurrence list and the reviewed picture are one list.
"""

from build123d import Compound

import puckcase_lib as L


def printed_parts():
    return [L.front_plate(), L.ring(), L.back_plate()]


def reference_parts():
    """Every non-printed occurrence, labelled."""
    parts = [L.puck_tube(), L.xiao_vendor(), L.header_mock(),
             L.ufl_plug_mock(), L.cable_mock(), L.lead_mock(),
             L.antenna_mock()]
    parts += L.screw_mocks()
    return parts


def gen_step():
    asm = Compound(children=printed_parts() + reference_parts())
    asm.label = "puckcase_v2_fitcheck"
    return asm


if __name__ == "__main__":
    a = gen_step()
    print(a.label, len(a.children), a.bounding_box())
