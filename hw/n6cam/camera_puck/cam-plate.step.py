"""Camera puck cam plate — printable part.  Prints flat, bosses up
(Z_PLATE_BOT on the bed).  No supports.  See caselib.py cam_plate() /
README.md."""

from caselib import cam_plate


def gen_step():
    return cam_plate()


if __name__ == "__main__":
    print(gen_step().bounding_box())
