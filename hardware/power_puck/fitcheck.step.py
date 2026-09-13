"""Review-only cutaway: the three printed parts (half-sectioned at x > CX)
with the charger, jack, plugs, cables, and battery mocks in place.

NOT a printable artifact — it exists so the fit can be inspected visually and
so interference can be re-checked (check.py) after any parameter change.
"""

from build123d import Align, Box, Compound, Pos

import caselib as C


def reference_parts():
    """Every non-printed occurrence in the fit-check, labelled."""
    parts = [C.charger_mock(), C.jack_mock()]
    parts.extend(C.charger_plug_mocks())
    parts.append(C.load_cable_mock())
    parts.append(C.batt_cable_mock())
    parts.append(C.battery_mock())
    return parts


def gen_step():
    # big box from x = CX outward, covering the full Y/Z envelope with margin
    cut = Pos(C.CX, -20, -20) * Box(60, 120, 80, align=(Align.MIN,) * 3)

    parts = []
    for fn in (C.tube, C.front_plate, C.back_cup):
        p = fn()
        label = p.label
        p = p - cut
        p.label = label + "_sectioned"
        parts.append(p)

    parts.extend(reference_parts())

    asm = Compound(children=parts)
    asm.label = "power_puck_fitcheck"
    return asm


if __name__ == "__main__":
    print(gen_step().bounding_box())
