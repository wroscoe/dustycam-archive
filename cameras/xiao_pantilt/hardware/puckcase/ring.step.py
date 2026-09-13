"""Ring — printable part.  Stands on its back mouth (Z = 20.36 on the bed), eave up."""

from puckcase_lib import ring


def gen_step():
    return ring()


if __name__ == "__main__":
    p = gen_step()
    print(p.label, len(p.solids()), p.is_valid, round(p.volume, 2), p.bounding_box())
