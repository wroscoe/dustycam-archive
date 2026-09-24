"""Fit checks for the XIAO ESP32S3 Sense case: interference volumes + probes.

Usage: python verify.py [path/to/vendor amz-xiao-esp32s3-sense.step]
With the vendor STEP path the checks also run against the real Seeed model (15 MB, ~30 s).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from xiao_sense_case_common import *
from build123d import *

b, l, brd = body(), lid(), board_ref()


def vol(s):
    try:
        return round(s.volume, 3)
    except Exception:
        return 0.0


def ivol(part, shape, loc=None):
    """Interference volume, summed per solid (a Compound with children does not intersect as a whole)."""
    tot = 0.0
    for s in shape.solids():
        if loc is not None:
            s = loc * s
        tot += vol(part & s)
    return round(tot, 3)


def report(brd, tag):
    print(f"[{tag}] board bbox", brd.bounding_box().min, brd.bounding_box().max, f"({len(brd.solids())} solids)")
    print(f"[{tag}] body & board :", ivol(b, brd), "mm3 (expect 0)")
    print(f"[{tag}] lid  & board :", ivol(l, brd), "mm3 (expect 0)")
    # the board pushed to its X extremes inside the pocket (stop blocks at -0.4, rib at 21.3) and Y extremes (+/-0.4)
    for dx in (-0.4, +0.35):
        print(f"[{tag}] board shifted {dx:+} X: body", ivol(b, brd, Pos(dx, 0, 0)), " lid", ivol(l, brd, Pos(dx, 0, 0)), "(expect 0)")
    for dy in (-0.4, +0.4):
        print(f"[{tag}] board shifted {dy:+} Y: body", ivol(b, brd, Pos(0, dy, 0)), " lid", ivol(l, brd, Pos(0, dy, 0)), "(expect 0)")


print("body bbox", b.bounding_box().min, b.bounding_box().max, "vol", round(b.volume))
print("lid  bbox", l.bounding_box().min, l.bounding_box().max, "vol", round(l.volume))
print("body & lid :", vol(b & l), "mm3 (expect 0)")
report(brd, "envelope")
for (x, y) in SCREW_XY:
    rod = Pos(x, y, (Z_TOP + Z_CEIL - PILOT_DEPTH) / 2) * Cylinder(0.8, Z_TOP - Z_CEIL + PILOT_DEPTH + 0.01)
    print(f"screw rod {x:.2f},{y:.2f}: body {vol(b & rod)} lid {vol(l & rod)} board {ivol(rod, brd)} (1.6 rod: expect 0)")
# lens column clear of the lid
col = cyl(CAM_C, PCB_T, WINDOW_D - 0.02, Z_TOP - PCB_T)
print("lens column & lid:", vol(l & col), "(expect 0)")
# USB-C plug probe: 12.3 x 6.5 overmold pushed through the X=0 wall up to the receptacle face (x -1.53)
plug = box((X0 - 5, USB_YC - 6.15, USB_ZC - 3.25), (5 + (B.USB[0] - X0) + 0.3, 12.3, 6.5))
print("usb plug probe: body", vol(b & plug), "(expect 0)")
# microSD card pulled 6 mm out (-X) must pass the wall opening
card = Pos(-6, 0, 0) * box((SD_X0, SD_Y0, SD_Z0), (15.06, SD_Y1 - SD_Y0, SD_Z1 - SD_Z0))
print("card pulled 6 mm: body", vol(b & card), "(expect 0)")
# hooks really overhang the PCB: the PCB top corners under the hooks
for (y0, y1) in HOOK_Y:
    probe = box((HOOK_X0, max(y0, 0), PCB_T + 0.01), (PCB_L - HOOK_X0, min(y1, PCB_W) - max(y0, 0), HOOK_Z0 - PCB_T - 0.02))
    print(f"hook gap probe y {y0}..{y1}: body", vol(b & probe), "(expect 0: 0.2 gap stays open)")
# insertion: board tilted nose-down about its +X bottom edge, that edge 0.3 mm short of the rib
# (the PCB tip passes under the hooks; the USB end then drops between the corner blocks)
for ang in (6, 8, 10, 12):
    tilt = Pos(PCB_L + 0.05, 0, 0) * Rot(0, ang, 0) * Pos(-PCB_L, 0, 0) * brd
    print(f"board tilted {ang} deg nose-down, edge at x {PCB_L + 0.05:.2f}: body", ivol(b, tilt), "(expect 0)")
print("case outer", round(OUT_X, 2), "x", round(OUT_Y, 2), "x", round(Z_TOP - Z_BOT, 2), " lid top Z", round(Z_TOP, 2),
      " screw length needed ~", round(LID_T - CBORE_DEPTH + PILOT_DEPTH, 1))
if len(sys.argv) > 1:
    v = import_step(sys.argv[1])
    report(v, "vendor STEP")
