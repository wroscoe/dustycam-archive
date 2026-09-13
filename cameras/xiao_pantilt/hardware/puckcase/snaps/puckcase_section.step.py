"""Review-only half model: everything cut away for X > CX, so the wall/bay/lip
stack can be read in one image.  Uses the measured board envelope rather than
the 103-solid vendor STEP (faster, and the section reads more clearly).

Not a printable artifact.  Regenerate with
  python ~/.claude/skills/cad/scripts/gen snaps/puckcase_section.step.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build123d import Align, Box, Compound, Pos      # noqa: E402

import puckcase_lib as L                             # noqa: E402


def gen_step():
    cut = Pos(L.CX, -20, -20) * Box(60, 130, 90, align=(Align.MIN,) * 3)
    parts = []
    for fn in (L.front_plate, L.ring, L.back_plate, L.puck_tube,
               L.lead_mock, L.antenna_mock):
        p = fn()
        label = p.label
        p = p - cut
        p.label = label + "_sectioned"
        parts.append(p)
    for s in L.xiao_envelope().children:
        q = s - cut
        if q.volume > 1e-6:
            q.label = s.label + "_sectioned"
            q.color = getattr(s, "color", None)
            parts.append(q)
    for s in L.screw_mocks():
        q = s - cut
        if q.volume > 1e-6:
            q.label = s.label + "_sectioned"
            parts.append(q)
    asm = Compound(children=parts)
    asm.label = "puckcase_section_CX"
    return asm


if __name__ == "__main__":
    a = gen_step()
    print(a.label, len(a.children), a.bounding_box())
