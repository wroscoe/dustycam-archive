"""Review-only cutaway: the four printed parts (half-sectioned at x = CX)
with the real N6 board model, the microSD card, and the LOAD-lead plug and
cable mocks in place.

NOT a printable artifact — it exists so the fit can be inspected visually and
so interference can be re-checked (check.py) after any parameter change.
"""

import importlib.util

from build123d import Align, Box, Compound, Pos

import caselib as C

_spec = importlib.util.spec_from_file_location(
    "openmv_n6", str(__import__("pathlib").Path(__file__).resolve().parent / "ref" / "openmv-n6.py")
)
_n6 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_n6)

_hat_spec = importlib.util.spec_from_file_location(
    "lora_hat_mock",
    str(__import__("pathlib").Path(__file__).resolve().parent.parent / "lora_hat" / "fit" / "lora_hat_mock.py"),
)
_hat = importlib.util.module_from_spec(_hat_spec)
_hat_spec.loader.exec_module(_hat)


def reference_parts():
    """Every non-printed occurrence in the fit-check, labelled."""
    parts = list(_n6.gen_step().children)
    parts.append(C.sd_card_mock())
    parts.append(C.load_jst_plug_mock())
    parts.append(C.load_cable_mock())
    parts.append(C.usb_plug_mock())
    # N6 LoRa hat (../lora_hat/): plugs onto the N6's SPI2 shield header, so
    # it rides along with the N6 in the slide-in sweep automatically -- no
    # MATED additions needed (the male header insulator only touches the
    # female header top at z 9.80, zero volume; see lora_hat/BUILD.md
    # Phase 5).
    parts.append(_hat.hat_parts())
    return parts


def gen_step():
    cut = Pos(C.CX, -40, -40) * Box(60, 100, 100, align=(Align.MIN,) * 3)

    parts = []
    for fn in (C.front_cup, C.cam_plate, C.back_plate, C.usb_cap):
        p = fn()
        label = p.label
        p = p - cut
        p.label = label + "_sectioned"
        parts.append(p)

    parts.extend(reference_parts())

    asm = Compound(children=parts)
    asm.label = "camera_puck_fitcheck"
    return asm


if __name__ == "__main__":
    print(gen_step().bounding_box())
