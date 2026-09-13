"""2D contract sketch for puckcase v1: side section at X = CX (Z right, Y up,
puck to the right) and a front view looking into the ring with the front
plate removed.  Drawing only — numbers are the design intent from DESIGN.md.
  ~/.claude/skills/cad/.venv/bin/python sketch_v1.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch

OUT_W, OUT_H, WALL, R = 47.21, 80.8, 2.4, 6.0
CX = OUT_W / 2
Z_R0, Z_PLATE, Z_BACK, Z_LIP1 = 2.4, 20.36, 24.36, 31.86
EAVE = 8.0
XB0, YB0, ZB0 = 15.355, 74.79, 17.36          # board origin in case frame
LENS_Y = YB0 - 3.53

PRINT = dict(fc="#cdd6e0", ec="#1f2a37", lw=1.0)
PUCK = dict(fc="#e6e0d0", ec="#6b6250", lw=0.8, hatch="//")
PART = dict(ec="#1f2a37", lw=0.8)
L = dict(fontsize=8, color="#1f2a37")
RED = dict(fontsize=7.5, color="#b3261e")

def r(a, x0, y0, x1, y1, **kw):
    a.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, **kw))

def dim(a, x0, y0, x1, y1, text, off=0.0, vertical=False, **kw):
    kw = dict(dict(fontsize=7, color="#1f2a37"), **kw)
    if vertical:
        a.annotate("", (x0 + off, y0), (x0 + off, y1), arrowprops=dict(arrowstyle="<->", lw=0.6))
        a.text(x0 + off + 0.4, (y0 + y1) / 2, text, va="center", rotation=90, **kw)
    else:
        a.annotate("", (x0, y0 + off), (x1, y0 + off), arrowprops=dict(arrowstyle="<->", lw=0.6))
        a.text((x0 + x1) / 2, y0 + off + 0.4, text, ha="center", **kw)

fig, (ax, af) = plt.subplots(1, 2, figsize=(16, 9.5), gridspec_kw={"width_ratios": [1.25, 1]})

# ------------------------------------------------------------- side section
a = ax
# front plate (top edge inside the eave: plate only to y 78.25 there)
r(a, 0, 0, 2.4, OUT_H - 2.55, **PRINT)
# front lip 2.4..8.4 (bottom + top)
r(a, 2.4, 2.55, 8.4, 4.15, **PRINT); r(a, 0, OUT_H - 4.15, 8.4, OUT_H - 2.55, **PRINT)
# ring walls bottom/top, top wall runs forward as the eave
r(a, 2.4, 0, Z_PLATE, 2.4, **PRINT)
r(a, -EAVE, OUT_H - 2.4, Z_PLATE, OUT_H, **PRINT)
r(a, -EAVE + 1.5, OUT_H - 2.4, -EAVE + 2.5, OUT_H - 1.6, fc="white", ec="#1f2a37", lw=0.6)   # drip groove
# back plate + puck lip
r(a, Z_PLATE, 0, Z_BACK, OUT_H, **PRINT)
r(a, Z_BACK, 2.55, Z_LIP1, 4.15, **PRINT); r(a, Z_BACK, OUT_H - 4.15, Z_LIP1, OUT_H - 2.55, **PRINT)
# puck tube (context)
r(a, Z_BACK, 0, Z_BACK + 16, 2.4, **PUCK); r(a, Z_BACK, OUT_H - 2.4, Z_BACK + 16, OUT_H, **PUCK)
r(a, Z_BACK, 8.0, Z_BACK + 11, 75.0, fc="#efe3bd", ec="#8a7a4a", lw=0.6, ls=":")   # puck battery
# bay features at the section plane: corner blocks / stop rib are off-plane; show ledge/hook zone dashed
r(a, 12.0, YB0 + 0.4, Z_PLATE, OUT_H - 2.4, fc="#cdd6e0", ec="#1f2a37", lw=0.8, ls="--")       # corner block (off-plane)
r(a, 13.73, YB0 - 22.5, Z_PLATE, YB0 - 21.3, fc="#cdd6e0", ec="#1f2a37", lw=0.8, ls="--")       # stop rib (off-plane)
r(a, 13.73, YB0 - 22.5, 15.91, YB0 - 20.0, fc="#cdd6e0", ec="#1f2a37", lw=0.8, ls="--")         # hook (off-plane)
r(a, 2.4, YB0 - 2.5, 16.01, YB0 + 0.1, fc="#cdd6e0", ec="#1f2a37", lw=0.8, ls="--")             # post (off-plane)
# board
r(a, ZB0 - 1.25, YB0 - 20.95, ZB0, YB0, fc="#2f7d4f", **PART)                       # base PCB
r(a, ZB0 - 5.43, YB0 - 21.25, ZB0 - 4.18, YB0 - 6.57, fc="#2f7d4f", **PART)         # expansion PCB
r(a, ZB0 - 4.46, YB0 + 1.53, ZB0 - 0.26, YB0 - 5.77, fc="#8f9aa6", **PART)          # USB-C shell
r(a, ZB0 - 8.5, YB0 + 3.11, ZB0 - 6.85, YB0 - 11.95, fc="#222", **PART)             # microSD card
r(a, ZB0 - 10.3, YB0 + 0.47, ZB0 - 8.2, YB0 - 7.53, fc="#333", **PART)              # camera head
r(a, ZB0 - 12.2, LENS_Y - 3.92, ZB0 - 10.3, LENS_Y + 3.92, fc="#333", **PART)       # barrel
r(a, ZB0 - 13.96, LENS_Y - 3.0, ZB0 - 12.2, LENS_Y + 3.0, fc="#333", **PART)        # tip
r(a, -0.6, LENS_Y - 3.75, 2.4 + 0.6, LENS_Y + 3.75, fc="white", ec="#b3261e", lw=1, ls="--")   # lens hole
# lead: under the board, down the plate, out the slot
r(a, ZB0 + 0.6, 3.0, ZB0 + 2.3, YB0 - 4, fc="#fbe3e3", ec="#b3261e", lw=0.6, ls=":")
r(a, 16.86, -0.6, 19.86, 3.0, fc="white", ec="#b3261e", lw=1, ls="--")                # cord slot
r(a, 14.36, 7.0, Z_PLATE, 11.0, fc="#cdd6e0", ec="#1f2a37", lw=0.8)                   # tie post
r(a, 15.86, 3.75, Z_PLATE, 9.25, fc="#cdd6e0", ec="#1f2a37", lw=0.8, ls="--")         # boss (off-plane)
r(a, Z_PLATE + 1.0, 20, Z_PLATE + 2.5, 45, fc="#f6edd6", ec="#8a7a4a", lw=0.8, ls=":")   # antenna flag
# lead loop under both boxes (schematic)
a.plot([18.4, 18.4, Z_BACK - 2.4 + 29.075, Z_BACK - 2.4 + 29.075], [0, -7, -7, 0], color="#b3261e", lw=1.2, ls=":")
# labels
a.text(-7.6, OUT_H + 0.8, "eave 8 (top wall runs forward), drip groove under", **L)
a.text(-1.9, 35, "front plate 2.4, outer face flat", rotation=90, va="center", **L)
a.text(3.6, 30, "ring (prints standing on its back mouth)", rotation=90, va="center", **L)
a.text(20.9, 60, "back plate 4.0", rotation=90, va="center", **L)
a.text(Z_BACK + 0.4, 79.0, "puck tube", fontsize=7, color="#6b6250")
a.text(Z_BACK + 2, 40, "puck battery", rotation=90, va="center", fontsize=7, color="#8a7a4a")
a.text(Z_BACK + 8.5, 5.4, "puck lip 7.5\n(= puck front plate)", fontsize=7, color="#1f2a37")
a.text(9.2, 46, "XIAO: USB end up,\nlens forward", rotation=90, va="center", **L)
a.text(4.0, 27, "posts 13.6 tall\nland on PCB corners\n(dashed = off the\nsection plane)", fontsize=7, color="#1f2a37")
a.text(21.0, 12, "lead", **RED); a.text(20.9, -9.4, "lead loop: puck slot → case slot", **RED)
a.text(-7, LENS_Y - 8, "lens hole Ø7.5", **RED)
a.text(Z_PLATE + 3.2, 32, "antenna flag on\nthe plate face", rotation=90, va="center", fontsize=7, color="#8a7a4a")
dim(a, 0, -3.5, Z_BACK, -3.5, "24.36 body", off=0)
dim(a, -EAVE, -6.5, 0, -6.5, "8", off=0)
dim(a, Z_BACK, -3.5, Z_LIP1, -3.5, "7.5", off=0)
dim(a, ZB0, 46, ZB0 + 3.0, 46, "3.0 lead gap", off=0)
dim(a, 2.4, LENS_Y - 6.5, 3.4, LENS_Y - 6.5, "1.0 lens gap", off=0)
dim(a, -11, 0, -11, OUT_H, "80.80", vertical=True)
dim(a, -EAVE + 0.5, LENS_Y, -EAVE + 0.5, OUT_H, "9.5 lens axis\nto top", vertical=True)
a.set_xlim(-16, Z_BACK + 30); a.set_ylim(-11, 84); a.set_aspect("equal"); a.axis("off")
a.set_title("Side section at X = CX  (Z →, Y ↑; puck to the right, hatched)", fontsize=10)

# ------------------------------------------------------------- front view
a = af
def rr(a, x0, y0, x1, y1, rad, **kw):
    a.add_patch(FancyBboxPatch((x0 + rad, y0 + rad), x1 - x0 - 2 * rad, y1 - y0 - 2 * rad,
                               boxstyle=f"round,pad={rad}", **kw))
rr(a, 0, 0, OUT_W, OUT_H, R, **PRINT)
rr(a, WALL, WALL, OUT_W - WALL, OUT_H - WALL, R - WALL, fc="white", ec="#1f2a37", lw=0.8)
r(a, 0, OUT_H - R, OUT_W, OUT_H, fc="#b7c3d2", ec="none")            # eave footprint (full width above y 74.8)
rr(a, WALL, OUT_H - R, OUT_W - WALL, OUT_H - WALL, 0.01, fc="white", ec="none")
a.text(CX, OUT_H - 1.9, "eave: top wall + corners, 8 forward", ha="center", fontsize=7, color="#1f2a37")
# bay walls with ledges
for x0 in (XB0 - 0.5 - 1.6, XB0 + 17.78 + 0.5):
    r(a, x0, YB0 - 22.5, x0 + 1.6, OUT_H - WALL, **PRINT)
r(a, XB0 - 0.5, YB0 - 22.5, XB0 + 0.95, OUT_H - WALL, fc="#9fb0c4", ec="#1f2a37", lw=0.5)       # ledge
r(a, XB0 + 17.78 - 0.95, YB0 - 22.5, XB0 + 17.78 + 0.5, OUT_H - WALL, fc="#9fb0c4", ec="#1f2a37", lw=0.5)
# corner blocks, stop ribs, hooks
for (bx0, bx1) in ((XB0 - 0.5, XB0 + 1.9), (XB0 + 17.78 - 1.9, XB0 + 17.78 + 0.5)):
    r(a, bx0, YB0 + 0.4, bx1, OUT_H - WALL, **PRINT)
for (bx0, bx1) in ((XB0 - 0.5, XB0 + 3.5), (XB0 + 17.78 - 3.5, XB0 + 17.78 + 0.5)):
    r(a, bx0, YB0 - 22.5, bx1, YB0 - 21.3, **PRINT)
for (bx0, bx1) in ((XB0 - 0.5, XB0 + 2.0), (XB0 + 17.78 - 2.0, XB0 + 17.78 + 0.5)):
    r(a, bx0, YB0 - 22.5, bx1, YB0 - 20.0, fc="#7f93ab", ec="#1f2a37", lw=0.6)
# board outline, lens, USB, card
rr(a, XB0, YB0 - 20.95, XB0 + 17.78, YB0, 1.9, fc="#2f7d4f", ec="#1f2a37", lw=0.8, alpha=0.55)
a.add_patch(Circle((CX, LENS_Y), 3.92, fc="#222", ec="#111")); a.add_patch(Circle((CX, LENS_Y), 3.75, fc="none", ec="#b3261e", lw=1, ls="--"))
r(a, XB0 + 4.41, YB0 - 5.77, XB0 + 13.35, YB0 + 1.53, fc="#8f9aa6", **PART)
r(a, XB0 + 2.48, YB0 - 11.95, XB0 + 13.66, YB0 + 3.11, fc="none", ec="#222", lw=0.6, ls=":")
# posts (front plate) on the corners
for (bx0, bx1) in ((XB0 - 0.2, XB0 + 1.8), (XB0 + 17.78 - 1.8, XB0 + 17.78 + 0.2)):
    r(a, bx0, YB0 - 2.5, bx1, YB0 + 0.1, fc="#f4c06a", ec="#1f2a37", lw=0.6)
# bosses, slot, post, antenna, lead
for bx, by in ((6.5, 6.5), (OUT_W - 6.5, 6.5), (6.5, OUT_H - 6.5), (OUT_W - 6.5, OUT_H - 6.5)):
    a.add_patch(Circle((bx, by), 2.75, **PRINT)); a.add_patch(Circle((bx, by), 1.1, fc="white", ec="#1f2a37", lw=0.6))
r(a, 13.0 - 2.25, -0.6, 13.0 + 2.25, 3.0, fc="white", ec="#b3261e", lw=1, ls="--")
a.add_patch(Circle((13.0, 9.0), 2.0, **PRINT))
r(a, CX - 12.5, 20, CX + 12.5, 45, fc="#f6edd6", ec="#8a7a4a", lw=0.8, ls=":")
a.plot([XB0 + 8, XB0 + 8, 13.0, 13.0, 14.5, 13.0], [YB0 - 4, 48, 48, 12, 9, 2], color="#b3261e", lw=1.2, ls=":")
# labels
a.text(XB0 + 8.9, YB0 - 26.5, "stop ribs + hooks (far end)", ha="center", fontsize=7, color="#1f2a37")
a.text(XB0 - 2.5, 60, "bay wall\n+ ledge", ha="right", fontsize=7, color="#1f2a37")
a.text(XB0 + 8.9, YB0 + 2.9, "corner blocks stop the USB edge; card tip 0.5 off the top wall", ha="center", fontsize=6.5, color="#1f2a37")
a.text(XB0 + 8.9, YB0 - 15, "XIAO\n(USB end up)", ha="center", fontsize=7, color="white")
a.text(CX, 32, "antenna flag\n(estimate 25×12)", ha="center", fontsize=7, color="#8a7a4a")
a.text(8.0, 12, "tie post", fontsize=7); a.text(13.0, -3.6, "cord slot 4.5×3", ha="center", **RED)
a.text(4, 10.5, "M2 boss\n×4", fontsize=6.5, ha="center")
a.text(XB0 + 17.78 + 3, YB0 - 1.5, "posts\n(front plate)", fontsize=6.5, color="#7a5a10")
dim(a, XB0, YB0 - 24.5, XB0 + 17.78, YB0 - 24.5, "17.78 PCB, 0.5/side play", off=-4.5)
dim(a, 0, -8, OUT_W, -8, "47.21", off=0)
dim(a, OUT_W + 3, LENS_Y, OUT_W + 3, OUT_H, "9.5", vertical=True)
dim(a, OUT_W + 6, 0, OUT_W + 6, OUT_H, "80.80", vertical=True)
a.set_xlim(-6, OUT_W + 12); a.set_ylim(-12, 84); a.set_aspect("equal"); a.axis("off")
a.set_title("Front view, front plate removed (looking +Z; posts shown where they land)", fontsize=10)

fig.suptitle("puckcase v1 — XIAO ESP32S3 Sense case on the power puck: 3 printed parts (front plate, ring, back/coupling plate) + 4 × M2", fontsize=11)
fig.tight_layout()
fig.savefig("sketch_v1.png", dpi=130)
print("ok")
