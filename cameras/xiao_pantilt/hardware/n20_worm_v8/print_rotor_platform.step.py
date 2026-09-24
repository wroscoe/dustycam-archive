import n20_worm_v8_lib as L
def gen_step():
    s = L.on_print_bed(L.rotor_platform_zero()); s.label = "printed_n20_worm_v8_rotor_platform"; return s
