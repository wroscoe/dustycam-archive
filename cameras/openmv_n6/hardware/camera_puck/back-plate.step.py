"""Camera puck back plate — printable part.  Prints back-face-down
(Z_BACK_OUT on the bed).  No supports.  Plain friction-fit plate; a future
coupling plate replaces this part.  See caselib.py back_plate() /
README.md."""

from caselib import back_plate


def gen_step():
    return back_plate()


if __name__ == "__main__":
    print(gen_step().bounding_box())
