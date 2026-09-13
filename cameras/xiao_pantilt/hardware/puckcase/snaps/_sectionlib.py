"""Shared helper for the review-only section models in this folder."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build123d import Compound          # noqa: E402

import puckcase_lib as L                # noqa: E402


def sectioned(cut, label):
    """Every occurrence with `cut` removed, one labelled child each."""
    parts = []
    for fn in (L.front_plate, L.ring, L.back_plate, L.puck_tube,
               L.lead_mock, L.antenna_mock, L.cable_mock, L.ufl_plug_mock):
        p = fn()
        name = p.label
        p = p - cut
        p.label = name + "_sectioned"
        parts.append(p)
    refs = list(L.xiao_envelope().children) + list(L.header_mock().children) \
        + list(L.screw_mocks())
    for src in refs:
        q = src - cut
        if q.volume > 1e-6:
            q.label = (getattr(src, "label", "part") or "part") + "_sectioned"
            q.color = getattr(src, "color", None)
            parts.append(q)
    asm = Compound(children=parts)
    asm.label = label
    return asm
