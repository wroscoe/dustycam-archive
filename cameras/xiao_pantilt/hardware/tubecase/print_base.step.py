"""Print-oriented single part: base liner cup of tubecase v2. Standing on its
floor (as modelled, no flip). Export with scripts/export."""
import tubecase_lib as L
from build123d import Pos


def on_bed(shape):
    bb = shape.bounding_box()
    return Pos(-(bb.min.X + bb.max.X) / 2, -(bb.min.Y + bb.max.Y) / 2, -bb.min.Z) * shape


def gen_step():
    s = on_bed(L.base_zero())
    s.label = "tubecase_base_print"
    return s
