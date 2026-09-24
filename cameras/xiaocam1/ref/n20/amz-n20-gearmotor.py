"""N20 (GA12-N20) micro metal gearmotor — envelope.

Frame: X=0 at the gearbox front (mounting) face; shaft overhangs to
x=-10. Gearbox x=0..9, motor can x=9..24 (total body 24, overall 34
with shaft). Y across the 12 width, Z up the 10 height; shaft axis at
(y=6, z=5). Face M1.6 holes NOT modeled (drawing ambiguous - see yaml).
Source: Handsontec GA12-N20 datasheet drawing.
"""
from build123d import *

W, H = 12.0, 10.0        # face
GEARBOX_L = 9.0
MOTOR_L = 15.0
SHAFT_D, SHAFT_L = 3.0, 10.0
AX_Y, AX_Z = 6.0, 5.0

with BuildPart() as p:
    # gearbox block
    with BuildSketch(Plane.YZ):
        with Locations((AX_Y, AX_Z)):
            Rectangle(W, H)
    extrude(amount=GEARBOX_L)
    # motor can: 12 dia cylinder flattened to 10 tall
    with BuildSketch(Plane.YZ.offset(GEARBOX_L)):
        with Locations((AX_Y, AX_Z)):
            Circle(W / 2)
            Rectangle(W, H, mode=Mode.INTERSECT)
    extrude(amount=MOTOR_L)
    # shaft with D-flat (flat 0.5 off a 3.0 shaft => 2.5 across)
    with BuildSketch(Plane.YZ):
        with Locations((AX_Y, AX_Z)):
            Circle(SHAFT_D / 2)
            with Locations((0, -(SHAFT_D / 2 - 0.25))):
                Rectangle(SHAFT_D + 1, 0.5, mode=Mode.SUBTRACT)
    extrude(amount=-SHAFT_L)

p.part.label = "n20-gearmotor-envelope"


def gen_step():
    return p.part
