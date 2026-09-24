"""Print-oriented single part: cap of tubecase, rotated 180 deg about X so the
top disc is down on the bed (skirt and plug print upward). Export with
scripts/export."""
import tubecase_lib as L
from build123d import Axis, Pos


def on_bed(shape):
    bb = shape.bounding_box()
    return Pos(-(bb.min.X + bb.max.X) / 2, -(bb.min.Y + bb.max.Y) / 2, -bb.min.Z) * shape


def gen_step():
    s = L.cap_zero().rotate(Axis.X, 180)
    s = on_bed(s)
    s.label = "tubecase_cap_print"
    return s
