"""Printable short C-collar for the split pan stop."""
import n20_worm_v8_lib as L


def gen_step():
    part = L.on_print_bed(L.stop_collar_zero())
    part.label = "printed_n20_worm_v8_bottom_stop_collar"
    return part
