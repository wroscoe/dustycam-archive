"""Camera puck front cup — printable part.  Prints face-down (Z_FRONT_OUT
on the bed).  No supports.  See caselib.py front_cup() / README.md."""

from caselib import front_cup


def gen_step():
    return front_cup()


if __name__ == "__main__":
    print(gen_step().bounding_box())
