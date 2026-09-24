"""Universal glue-on 1/4-20 tripod pad.

Coordinate convention: the origin is centered on the glue face; the glue
face is XY at z=0 and the tripod/insert side is +Z.
"""

from build123d import Align, Box, Cylinder, Pos


# All dimensions are millimetres.  The insert pocket is sized for the
# Ruthex RX-1/4-20 heat-set insert specified in the design brief.
PAD_WIDTH = 40.0
PAD_DEPTH = 32.0
PAD_THICKNESS = 3.0
PAD_CORNER_RADIUS = 4.0
BOSS_DIAMETER = 16.0
BOSS_HEIGHT = 11.5
INSERT_POCKET_DIAMETER = 8.0
INSERT_POCKET_DEPTH = 13.5
INSERT_FLOOR = 1.0
POCKET_CUT_OVERSHOOT = 0.1


def rounded_pad():
    """Return a 40 x 32 x 3 rounded rectangle with 4 mm outside corners."""
    r = PAD_CORNER_RADIUS
    base_align = (Align.CENTER, Align.CENTER, Align.MIN)
    # The union of two rectangles and four corner cylinders produces an exact
    # rounded rectangle without depending on selected sketch edges.
    pad = Box(PAD_WIDTH - 2 * r, PAD_DEPTH, PAD_THICKNESS, align=base_align)
    pad = pad.fuse(Box(PAD_WIDTH, PAD_DEPTH - 2 * r, PAD_THICKNESS, align=base_align))
    for x in (-PAD_WIDTH / 2 + r, PAD_WIDTH / 2 - r):
        for y in (-PAD_DEPTH / 2 + r, PAD_DEPTH / 2 - r):
            pad = pad.fuse(Pos(x, y, 0) * Cylinder(r, PAD_THICKNESS, align=base_align))
    return pad


def gen_step():
    """Build the single printable tripod pad solid."""
    base_align = (Align.CENTER, Align.CENTER, Align.MIN)
    pad = rounded_pad()
    boss = Pos(0, 0, PAD_THICKNESS) * Cylinder(
        BOSS_DIAMETER / 2, BOSS_HEIGHT, align=base_align
    )
    pocket = Pos(0, 0, INSERT_FLOOR) * Cylinder(
        INSERT_POCKET_DIAMETER / 2,
        INSERT_POCKET_DEPTH + POCKET_CUT_OVERSHOOT,
        align=base_align,
    )
    part = pad.fuse(boss).cut(pocket)
    part.label = "universal_glue_on_tripod_pad"
    return part


if __name__ == "__main__":
    print(gen_step().bounding_box())
