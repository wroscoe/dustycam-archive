"""Scratch section models for the v3 review images (not committed outputs)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cadgen import step
from build123d import Compound, Box, Pos, Align
import v3lib as L

BIG = 200


def _fit():
    parts = [L.holder(), L.backing_plate()] + list(L.board_mocks(headers=True).values())
    return parts


def _cut(parts, keep):
    out = []
    for p in parts:
        r = p.intersect(keep)
        if r is None:
            continue
        rs = r if isinstance(r, (list, tuple)) else [r]
        for s in rs:
            if s.volume > 1e-6:
                s.label = p.label
                out.append(s)
    return out


@step(out="section_lens.step")
def section_lens():
    # half model: keep y <= CAM_Y, viewed from +y  -> cut along the lens axis
    keep = Pos(-BIG / 2, -BIG, -BIG / 2) * Box(BIG, BIG + L.CAM_Y, BIG, align=(Align.MIN,) * 3)
    return Compound(children=_cut(_fit(), keep), label="section_lens")


@step(out="section_channel.step")
def section_channel():
    # keep x <= 10 : cross-section across the channel through the ribs' zone
    keep = Pos(-BIG, -BIG / 2, -BIG / 2) * Box(BIG + 10.0, BIG, BIG, align=(Align.MIN,) * 3)
    return Compound(children=_cut(_fit(), keep), label="section_channel")


if __name__ == "__main__":
    section_lens()
    section_channel()
