"""Labeled N20 worm-drive camera-pan assembly at pan=0 degrees."""
import n20_worm_v8_lib as L


def gen_step():
    return L.build_assembly(0.0)

