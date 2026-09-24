"""Print-oriented single part: mid plate of tubecase v2 (as modelled, no flip --
the cradle/pedestal print standing up off the disc, underside on the bed).
Export with scripts/export."""
import tubecase_lib as L
from build123d import Pos


def on_bed(shape):
    bb = shape.bounding_box()
    return Pos(-(bb.min.X + bb.max.X) / 2, -(bb.min.Y + bb.max.Y) / 2, -bb.min.Z) * shape


def gen_step():
    s = on_bed(L.mid_plate_zero())
    s.label = "tubecase_midplate_print"
    return s
