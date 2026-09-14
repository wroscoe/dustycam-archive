"""Ring — printable part.  Stands on its back mouth (Z = 26.36 on the bed),
eave up.  Carries the whole v2 board bay: side walls, far-end groove (stop
ribs, hooks, centre ledge), the USB end's root strip and two snap tongues, and
the expansion-PCB rails with crush ribs.  v2.4: the lens collar is gone — it is
now the front plate's head window boss.
"""

from cadgen import step

from puckcase_lib import ring


@step(out="ring.step")
def gen_step():
    return ring()


if __name__ == "__main__":
    p = gen_step()
