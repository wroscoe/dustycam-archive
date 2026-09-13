"""Ring — printable part.  Stands on its back mouth (Z = 26.36 on the bed),
eave up.  Carries the whole v2 board bay: side walls, far-end groove (stop
ribs, hooks, centre ledge), USB-end wall (shell window, bridge band, card
notch, snap tongue), expansion-PCB rails with crush ribs, and the lens collar.
"""

from cadgen import step

from puckcase_lib import ring


@step(out="ring.step")
def gen_step():
    return ring()


if __name__ == "__main__":
    p = gen_step()
