"""Print-oriented single part: deck of tubecase (as modelled, no flip -- the
cradle/pedestal print standing up off the disc). Export with scripts/export."""
import tubecase_lib as L
from build123d import Pos


def on_bed(shape):
    bb = shape.bounding_box()
    return Pos(-(bb.min.X + bb.max.X) / 2, -(bb.min.Y + bb.max.Y) / 2, -bb.min.Z) * shape


def gen_step():
    s = on_bed(L.deck_zero())
    s.label = "tubecase_deck_print"
    return s
