"""Assembled power puck — the 3 printed parts as a labelled compound.

NOT a printable artifact by itself; print tube.step.py, front-plate.step.py,
and back-cup.step.py separately.
"""

from build123d import Compound

from caselib import back_cup, front_plate, tube


def gen_step():
    parts = [tube(), front_plate(), back_cup()]
    asm = Compound(children=parts)
    asm.label = "power_puck"
    return asm


if __name__ == "__main__":
    print(gen_step().bounding_box())
