"""Assembled camera puck — the 4 printed parts as a labelled compound.

NOT a printable artifact by itself; print front-cup.step.py, cam-plate.
step.py, back-plate.step.py and usb-cap.step.py separately.
"""

from build123d import Compound

from caselib import back_plate, cam_plate, front_cup, usb_cap


def gen_step():
    parts = [front_cup(), cam_plate(), back_plate(), usb_cap()]
    asm = Compound(children=parts)
    asm.label = "camera_puck"
    return asm


if __name__ == "__main__":
    print(gen_step().bounding_box())
