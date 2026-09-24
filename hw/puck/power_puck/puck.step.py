"""Assembled power puck — the 4 printed parts as a labelled compound.

NOT a printable artifact by itself; print tube.step.py, front-plate.step.py,
back-cup.step.py and usb-cap.step.py separately.
"""

from build123d import Compound

from caselib import back_cup, front_plate, tube, usb_cap


def gen_step():
    parts = [tube(), front_plate(), back_cup(), usb_cap()]
    asm = Compound(children=parts)
    asm.label = "power_puck"
    return asm


if __name__ == "__main__":
    print(gen_step().bounding_box())
