"""Print-oriented single part: lid of xiao_pantilt v7. Export with scripts/export."""
import pantilt_lib as L
from build123d import Axis, Pos

PART = "lid"
FLIP = {"base": True, "lid": False, "pod_base": False, "holder": False, "cap": True}   # top face down on the bed


def on_bed(shape):
    bb = shape.bounding_box()
    return Pos(-(bb.min.X + bb.max.X) / 2, -(bb.min.Y + bb.max.Y) / 2, -bb.min.Z) * shape


def gen_step():
    s = {"base": L.base_zero, "lid": L.lid_zero, "pod_base": L.pod_base_zero, "holder": L.holder_zero, "cap": L.cap_zero}[PART]()
    if FLIP[PART]:
        s = s.rotate(Axis.X, 180)
    s = on_bed(s)
    s.label = f"xiao_pantilt_{PART}_print"
    return s
