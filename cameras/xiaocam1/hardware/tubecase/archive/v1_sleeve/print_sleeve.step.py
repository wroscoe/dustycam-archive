"""Print-oriented single part: sleeve of tubecase. Standing on its open bottom
rim (as modelled, no flip). Export with scripts/export."""
import tubecase_lib as L
from build123d import Pos


def on_bed(shape):
    bb = shape.bounding_box()
    return Pos(-(bb.min.X + bb.max.X) / 2, -(bb.min.Y + bb.max.Y) / 2, -bb.min.Z) * shape


def gen_step():
    s = on_bed(L.sleeve_zero())
    s.label = "tubecase_sleeve_print"
    return s
