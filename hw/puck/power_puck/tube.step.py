"""Tube — printable part.  Straight rounded-rect sleeve, prints front-mouth
down (Z_TUBE0 on the bed)."""

from caselib import tube


def gen_step():
    return tube()


if __name__ == "__main__":
    print(gen_step().bounding_box())
