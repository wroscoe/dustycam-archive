"""Printable straight pan-stop finger, keyed and M2-fastened to the stop collar."""
import n20_worm_v8_lib as L


def gen_step():
    part = L.on_print_bed(L.stop_finger_zero())
    part.label = "printed_n20_worm_v8_bottom_stop_finger"
    return part
