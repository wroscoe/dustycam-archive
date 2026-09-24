import n20_worm_v8_lib as L
from build123d import Axis
def gen_step():
    s = L.on_print_bed(L.worm_zero().rotate(Axis.Y, -90)); s.label = "printed_n20_worm_v8_single_start_worm"; return s
