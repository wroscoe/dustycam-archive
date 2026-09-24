import n20_worm_v8_lib as L
from build123d import Axis
def gen_step():
    s = L.on_print_bed(L.cap_zero().rotate(Axis.X, 180)); s.label = "printed_n20_worm_v8_cap"; return s
