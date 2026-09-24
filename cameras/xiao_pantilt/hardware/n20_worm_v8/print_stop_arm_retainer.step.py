"""Printable lower C-clip retaining the side-installed stop arm."""
import n20_worm_v8_lib as L


def gen_step():
    part = L.on_print_bed(L.stop_arm_retainer_zero())
    part.label = "printed_n20_worm_v8_bottom_stop_arm_axial_c_clip"
    return part
