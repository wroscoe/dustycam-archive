"""2D contract sketch for puckcase v2 bay redesign: side section at X = CX,
front view into the ring (front plate removed), and a detail section through
the USB-end wall / tongue.  Drawing only -- numbers are the design intent
from DESIGN_v2.md sec 3.  Style/helpers reused from sketch_v1.py (not
modified): r(), dim(), colours, figure setup philosophy.
  ~/.claude/skills/cad/.venv/bin/python sketch_v2.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch, Polygon
import numpy as np

# --------------------------------------------------------------- geometry
OUT_W, OUT_H, WALL, R = 47.21, 80.8, 2.4, 6.0
CX = 23.605
Z_PLATE, Z_BACK = 26.36, 30.36
Z_LIP1 = Z_BACK + 7.5           # 37.86, puck lip
EAVE = 8.0
Y_B0, Z_B0, X_B0 = 71.29, 17.36, 31.855
LENS_X, LENS_Y = CX, 67.76

# board stack, case frame (Z0,Z1, Y0,Y1)
BASE_PCB = (16.11, 17.36, 50.34, 71.29)
EXP_PCB = (11.93, 13.18, 50.04, 64.72)
USB_SHELL = (12.90, 17.10, 65.52, 72.82)
SD_CARD = (8.86, 10.51, 59.34, 74.40)
CAM_HEAD = (7.06, 9.16, 63.76, 71.76)
BARREL = (5.16, 7.06, LENS_Y - 3.92, LENS_Y + 3.92)
TIP = (3.40, 5.16, LENS_Y - 3.0, LENS_Y + 3.0)
OLD_PCB_TOP_Y = 74.79            # v1 PCB top edge, pre BOARD_DROP

# header mock
HDR_BODY_Z = (17.36, 19.86)
HDR_PIN_Z = (19.86, 25.86)

# new ring features (case frame)
COLLAR_FRONT = dict(z=(5.56, 6.86), y=(61.49, 73.59))   # extends further +Y
COLLAR_BACK = dict(z=(6.86, 8.36), y=(61.49, 72.89))
COLLAR_WINDOW = dict(z=(6.86, 8.36), y=(63.46, 72.06))
COLLAR_BORE = dict(z=(5.56, 6.86), y=(LENS_Y - 4.125, LENS_Y + 4.125))
FPC_RELIEF = dict(z=(7.86, 8.36), y=(61.49, 63.46))

USB_WALL = dict(z=(8.36, 26.36), y=(71.69, 72.89))
SHELL_WINDOW = dict(z=(12.80, 17.46), y=(71.69, 72.89))
CARD_NOTCH = dict(z=(8.36, 10.86), y=(71.69, 72.89))
BRIDGE = dict(z=(10.86, 12.80), y=(71.69, 72.89))

TONGUE = dict(z=(17.46, 26.16), y=(71.49, 72.39))
LIP = dict(z=(17.46, 17.96), y=(70.89, 71.49))
LIP_RAMP_TOP = (18.56, 71.49)     # z, y -- back-top corner of the 45 deg ramp

FAR_WALL = dict(z=(11.36, 26.36), y=(48.09, 49.69))
LEDGE = dict(z=(17.46, 26.36), y=(49.69, 51.59))
HOOKS = dict(z=(13.76, 15.96), y=(49.69, 51.29))
STOP_RIBS = dict(z=(13.76, 26.36), y=(49.69, 50.14))
RAILS_A = dict(z=(11.76, 13.16), y=(54.29, 63.29))

BOSS = dict(z=(15.86, 26.36))

# --------------------------------------------------------------- styles
PRINT = dict(fc="#cdd6e0", ec="#1f2a37", lw=1.0)
PUCK = dict(fc="#e6e0d0", ec="#6b6250", lw=0.8, hatch="//")
PART = dict(ec="#1f2a37", lw=0.8)
NEW = dict(fc="#a9c6e8", ec="#14508a", lw=0.9)          # new v2 ring feature
CUT = dict(fc="white", ec="#14508a", lw=0.6, ls="--")    # material removed
DASH = dict(fc="#cdd6e0", ec="#1f2a37", lw=0.8, ls="--")  # off-plane
L = dict(fontsize=7.5, color="#1f2a37")
RED = dict(fontsize=7.5, color="#b3261e")
CALL_C = "#0d3a63"


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


def callout(a, num, x, y, rad=1.15, fontsize=6.6):
    a.add_patch(Circle((x, y), rad, fc="white", ec=CALL_C, lw=0.9, zorder=6))
    a.text(x, y, str(num), ha="center", va="center", fontsize=fontsize, color=CALL_C, zorder=7)


def leader(a, lx, ly, tx, ty, text, ha="left", va="center", fontsize=7, color="#1f2a37"):
    a.plot([lx, tx], [ly, ty], color=color, lw=0.5, ls="-", alpha=0.6, zorder=3)
    a.text(lx, ly, text, ha=ha, va=va, fontsize=fontsize, color=color, zorder=4)


# --------------------------------------------------------------- figure
FIGW, FIGH = 17.0, 10.2
fig = plt.figure(figsize=(FIGW, FIGH))


def axes_rect(x0, y0, w, h):
    return [x0 / FIGW, y0 / FIGH, w / FIGW, h / FIGH]


XLIM_A, YLIM_A = (-16, 46), (-11, 88)
XLIM_B, YLIM_B = (-24, 66), (-14, 88)
XLIM_C, YLIM_C = (3, 28), (54, 83)

H_ROW = 8.1
W_A = H_ROW * (XLIM_A[1] - XLIM_A[0]) / (YLIM_A[1] - YLIM_A[0])
W_B = H_ROW * (XLIM_B[1] - XLIM_B[0]) / (YLIM_B[1] - YLIM_B[0])
H_C = 4.2
W_C = H_C * (XLIM_C[1] - XLIM_C[0]) / (YLIM_C[1] - YLIM_C[0])

xA0 = 0.15
xB0 = xA0 + W_A + 0.25
xC0 = xB0 + W_B + 0.25
Y0_ROW = 0.2

ax = fig.add_axes(axes_rect(xA0, Y0_ROW, W_A, H_ROW))
af = fig.add_axes(axes_rect(xB0, Y0_ROW, W_B, H_ROW))
ac = fig.add_axes(axes_rect(xC0, Y0_ROW + H_ROW - H_C, W_C, H_C))
an = fig.add_axes(axes_rect(xC0, Y0_ROW, W_C, H_ROW - H_C - 0.4))   # notes/legend panel

# =================================================================
# PANEL A -- side section at X = CX  (Z horizontal, Y vertical)
# =================================================================
a = ax
# front plate (no posts), unchanged lip
r(a, 0, 0, 2.4, OUT_H - 2.55, **PRINT)
r(a, 2.4, 2.55, 8.4, 4.15, **PRINT); r(a, 0, OUT_H - 4.15, 8.4, OUT_H - 2.55, **PRINT)
# ring bottom wall (full depth) + top wall/eave band
r(a, 2.4, 0, Z_PLATE, 2.4, **PRINT)
r(a, -EAVE, OUT_H - 2.4, Z_PLATE, OUT_H, **PRINT)
# back plate + puck lip + puck context
r(a, Z_PLATE, 0, Z_BACK, OUT_H, **PRINT)
r(a, Z_BACK, 2.55, Z_LIP1, 4.15, **PRINT); r(a, Z_BACK, OUT_H - 4.15, Z_LIP1, OUT_H - 2.55, **PRINT)
r(a, Z_BACK, 0, Z_BACK + 10, 2.4, **PUCK); r(a, Z_BACK, OUT_H - 2.4, Z_BACK + 10, OUT_H, **PUCK)

# off-plane dashed context: boss, hooks, stop ribs, rails
r(a, BOSS["z"][0], 3.75, BOSS["z"][1], 9.25, **DASH)
r(a, HOOKS["z"][0], HOOKS["y"][0], HOOKS["z"][1], HOOKS["y"][1], **DASH)
r(a, STOP_RIBS["z"][0], STOP_RIBS["y"][0], STOP_RIBS["z"][1], STOP_RIBS["y"][1], **DASH)
r(a, RAILS_A["z"][0], RAILS_A["y"][0], RAILS_A["z"][1], RAILS_A["y"][1], **DASH)

# header mock (dashed -- header rows sit near the board's Y edges, not at CX)
r(a, HDR_BODY_Z[0], BASE_PCB[2], HDR_BODY_Z[1], BASE_PCB[3], fc="none", ec="#6b6250", lw=0.8, ls="--")
r(a, HDR_PIN_Z[0], BASE_PCB[2] + 3, HDR_PIN_Z[1], BASE_PCB[3] - 3, fc="none", ec="#6b6250", lw=0.6, ls="--")

# far-end wall, ledge (drawn before board so board sits in front)
r(a, FAR_WALL["z"][0], FAR_WALL["y"][0], FAR_WALL["z"][1], FAR_WALL["y"][1], **NEW)
r(a, LEDGE["z"][0], LEDGE["y"][0], LEDGE["z"][1], LEDGE["y"][1], **NEW)

# board stack
r(a, BASE_PCB[0], BASE_PCB[2], BASE_PCB[1], BASE_PCB[3], fc="#2f7d4f", **PART)
r(a, EXP_PCB[0], EXP_PCB[2], EXP_PCB[1], EXP_PCB[3], fc="#2f7d4f", **PART)
r(a, USB_SHELL[0], USB_SHELL[2], USB_SHELL[1], USB_SHELL[3], fc="#8f9aa6", **PART)
r(a, SD_CARD[0], SD_CARD[2], SD_CARD[1], SD_CARD[3], fc="#222", **PART)
r(a, CAM_HEAD[0], CAM_HEAD[2], CAM_HEAD[1], CAM_HEAD[3], fc="#333", **PART)
r(a, BARREL[0], BARREL[2], BARREL[1], BARREL[3], fc="#333", **PART)
r(a, TIP[0], TIP[2], TIP[1], TIP[3], fc="#333", **PART)

# old (pre BOARD_DROP) PCB top edge for reference
a.plot([BASE_PCB[0], BASE_PCB[1]], [OLD_PCB_TOP_Y, OLD_PCB_TOP_Y], color="#888", lw=1.0, ls="-")
a.text(BASE_PCB[1] + 0.4, OLD_PCB_TOP_Y, "old PCB top", ha="left", va="center",
       fontsize=6.5, color="#888")

# collar (front part extends further in Y; back part narrower) with window/bore cut, FPC relief
r(a, COLLAR_FRONT["z"][0], COLLAR_FRONT["y"][0], COLLAR_FRONT["z"][1], COLLAR_FRONT["y"][1], **NEW)
r(a, COLLAR_BACK["z"][0], COLLAR_BACK["y"][0], COLLAR_BACK["z"][1], COLLAR_BACK["y"][1], **NEW)
r(a, COLLAR_BORE["z"][0], COLLAR_BORE["y"][0], COLLAR_BORE["z"][1], COLLAR_BORE["y"][1], **CUT)
r(a, COLLAR_WINDOW["z"][0], COLLAR_WINDOW["y"][0], COLLAR_WINDOW["z"][1], COLLAR_WINDOW["y"][1], **CUT)
r(a, FPC_RELIEF["z"][0], FPC_RELIEF["y"][0], FPC_RELIEF["z"][1], FPC_RELIEF["y"][1], fc="white", ec="none")

# USB-end wall with shell window + card notch cut, bridge band solid
r(a, USB_WALL["z"][0], USB_WALL["y"][0], USB_WALL["z"][1], USB_WALL["y"][1], **NEW)
r(a, SHELL_WINDOW["z"][0], SHELL_WINDOW["y"][0], SHELL_WINDOW["z"][1], SHELL_WINDOW["y"][1], **CUT)
r(a, CARD_NOTCH["z"][0], CARD_NOTCH["y"][0], CARD_NOTCH["z"][1], CARD_NOTCH["y"][1], **CUT)
r(a, BRIDGE["z"][0], BRIDGE["y"][0], BRIDGE["z"][1], BRIDGE["y"][1], **NEW)

# tongue + lip with 45 deg ramp
r(a, TONGUE["z"][0], TONGUE["y"][0], TONGUE["z"][1], TONGUE["y"][1], **NEW)
lip_poly = Polygon([(LIP["z"][0], LIP["y"][0]), (LIP["z"][1], LIP["y"][0]),
                     (LIP_RAMP_TOP[0], LIP_RAMP_TOP[1]), (LIP["z"][0], LIP["y"][1])],
                    closed=True, fc="#a9c6e8", ec="#14508a", lw=0.9)
a.add_patch(lip_poly)

# lens hole (front plate)
r(a, -0.6, LENS_Y - 3.75, 3.0, LENS_Y + 3.75, fc="white", ec="#b3261e", lw=1, ls="--")

# brow angle line: lens tip -> eave edge
a.plot([TIP[0], -EAVE], [LENS_Y, OUT_H - 2.4], color="#b3261e", lw=1.0, ls=":")
a.text(-3.2, 74.2, "43°", **RED)

# dimensions
dim(a, 0, -3.5, Z_PLATE, -3.5, "Z_PLATE 26.36", off=0)
dim(a, -EAVE, -6.5, 0, -6.5, "eave 8", off=0)
dim(a, BASE_PCB[1], 42.5, Z_PLATE, 42.5, "BACK_GAP 9.0", off=0)
dim(a, -13.2, SD_CARD[3], -13.2, OUT_H - 2.4, "card roof 4.0", vertical=True)
dim(a, 29.0, BASE_PCB[3], 29.0, OLD_PCB_TOP_Y, "BOARD_DROP 3.5", vertical=True, off=0)

# context labels (structural, low clutter)
a.text(-7.6, OUT_H + 0.8, "eave 8 (top wall runs forward)", **L)
a.text(-1.9, 40, "front plate 2.4, no posts", rotation=90, va="center", **L)
a.text(3.6, 55, "ring", rotation=90, va="center", **L)
a.text(27.86, 40, "back plate 4.0", rotation=90, va="center", ha="center", **L)
a.text(Z_BACK + 0.4, 79.0, "puck", fontsize=7, color="#6b6250")
a.text(Z_BACK + 5.6, 5.4, "puck lip 7.5", fontsize=7, color="#1f2a37")
a.text(9.2, 44, "XIAO: USB end up,\nlens forward", rotation=90, va="center", **L)
a.text(-8, LENS_Y - 8, "lens hole\nØ7.5", **RED)

# numbered callouts (see legend in panel D / notes)
callout(a, 1, 1.2, 20)
callout(a, 2, 15, 1.2)
callout(a, 3, 27.86, 34)
callout(a, 4, 33, 3.3)
callout(a, 5, -3, LENS_Y)
callout(a, 6, 18.6, 60)
callout(a, 7, 10, 73.5)
callout(a, 8, 7, LENS_Y)
callout(a, 9, 8.1, 62.5)
callout(a, 10, 17, 72.3)
callout(a, 11, 21.5, 71.9)
callout(a, 12, 18, 48.9)
callout(a, 13, 21.5, 50.6)
callout(a, 14, 14.8, 50.9)
callout(a, 14, 12.4, 58)
callout(a, 15, 20, 6.5)

a.set_xlim(*XLIM_A); a.set_ylim(*YLIM_A); a.set_aspect("equal"); a.axis("off")
a.set_title("A: side section at X = CX = 23.605  (Z →, Y ↑; puck right)", fontsize=10)

# legend + colour key, drawn inside panel A's own empty puck-side area
legend_txt = (
    "1  front plate 2.4, no posts\n"
    "2  ring / bay walls\n"
    "3  back plate 4.0\n"
    "4  puck lip 7.5\n"
    "5  lens hole Ø7.5\n"
    "6  header mock (dashed)\n"
    "7  board: PCB/shell/\n"
    "    SD/camera (by colour)\n"
    "8  collar: window+bore\n"
    "9  FPC relief\n"
    "10 USB-end wall: window/\n"
    "    notch/bridge\n"
    "11 tongue+lip, 45° ramp\n"
    "12 far-end wall\n"
    "13 ledge\n"
    "14 hooks/ribs/rails\n"
    "    (off-plane, dashed)\n"
    "15 boss ×4 (off-plane)"
)
a.text(33, 76, legend_txt, fontsize=6.9, va="top", ha="left", color="#1f2a37", linespacing=1.45)

key_items = [
    ("#a9c6e8", "new v2 ring feature"),
    ("#cdd6e0", "unchanged printed body"),
    ("white", "material cut (window/notch)"),
    ("#2f7d4f", "PCB / expansion PCB"),
    ("#8f9aa6", "USB-C shell"),
    ("#333333", "card / camera / lens"),
]
ky = 30
for fc, txt in key_items:
    r(a, 33, ky - 0.7, 34.4, ky + 0.7, fc=fc, ec="#1f2a37", lw=0.6)
    a.text(35, ky, txt, fontsize=6.7, va="center", ha="left", color="#1f2a37")
    ky -= 2.6

# =================================================================
# PANEL B -- front view, front plate removed (X horizontal, Y vertical)
# =================================================================
a = af


def rr(a, x0, y0, x1, y1, rad, **kw):
    a.add_patch(FancyBboxPatch((x0 + rad, y0 + rad), x1 - x0 - 2 * rad, y1 - y0 - 2 * rad,
                                boxstyle=f"round,pad={rad}", **kw))


rr(a, 0, 0, OUT_W, OUT_H, R, **PRINT)
rr(a, WALL, WALL, OUT_W - WALL, OUT_H - WALL, R - WALL, fc="white", ec="#1f2a37", lw=0.8)
r(a, 0, OUT_H - R, OUT_W, OUT_H, fc="#b7c3d2", ec="none")
rr(a, WALL, OUT_H - R, OUT_W - WALL, OUT_H - WALL, 0.01, fc="white", ec="none")

# ledge (behind PCB, hatched) -- draw first
r(a, 18.855, 49.69, 26.855, 51.59, fc="#dbe6f2", ec="#14508a", lw=0.6, hatch="///")

# side bay walls
r(a, 10.975, 48.09, 12.575, 78.40, **PRINT)
r(a, 33.355, 48.09, 34.955, 78.40, **PRINT)
# far-end wall
r(a, 12.575, 48.09, 33.355, 49.69, **NEW)
# rails + rib marks
for x0, x1 in ((12.575, 14.425), (31.505, 33.355)):
    r(a, x0, 54.29, x1, 63.29, **NEW)
    r(a, x0, 58.79, x1, 62.79, fc="#7fa8d6", ec="#14508a", lw=0.5)
    r(a, x0, 54.29, x1, 58.29, fc="#7fa8d6", ec="#14508a", lw=0.5)
# hooks + stop ribs
for x0, x1 in ((30.255, 32.355), (13.575, 15.675)):
    r(a, x0, 49.69, x1, 51.29, **NEW)
for x0, x1 in ((28.355, 32.355), (13.575, 17.575)):
    r(a, x0, 49.69, x1, 50.14, fc="#5c86b8", ec="#14508a", lw=0.6)

# collar plate + window + bore + lens (drawn first: it is the front-most,
# lowest-Z layer in this view, so it sits behind the USB-end wall band)
r(a, 12.575, 61.49, 33.355, 73.59, fc="#dbe6f2", ec="#14508a", lw=0.7)
r(a, 19.305, 63.46, 27.905, 72.06, fc="white", ec="#14508a", lw=0.7)
a.add_patch(Circle((LENS_X, LENS_Y), 4.125, fc="none", ec="#14508a", lw=0.9))
a.add_patch(Circle((LENS_X, LENS_Y), 3.75, fc="none", ec="#b3261e", lw=1, ls="--"))
a.add_patch(Circle((LENS_X, LENS_Y), 3.0, fc="#333", ec="#111"))

# USB-end wall + card notch + shell window (deeper in Z than the collar, but
# drawn on top here so its own window/notch bands stay legible)
r(a, 12.575, 71.69, 33.355, 72.89, **NEW)
r(a, 17.955, 71.69, 29.655, 72.89, fc="#c6d6e8", ec="#14508a", lw=0.5)
r(a, 18.005, 71.69, 27.955, 72.89, fc="#eef3f8", ec="#14508a", lw=0.5)

# tongue + slits
r(a, 19.855, 71.49, 25.855, 72.39, **NEW)
r(a, 19.855 - 0.8, 71.49, 19.855, 72.39, fc="white", ec="none")
r(a, 25.855, 71.49, 25.855 + 0.8, 72.39, fc="white", ec="none")

# PCB outline (thin, green, behind everything)
rr(a, 14.075, 50.34, 31.855, 71.29, 1.9, fc="#2f7d4f", ec="#1f2a37", lw=0.8, alpha=0.30)
r(a, 14.575, 50.04, 31.355, 64.72, fc="none", ec="#1f2a37", lw=0.6, ls=":")
# microSD card
r(a, 18.195, 59.34, 29.375, 74.40, fc="#222", ec="#111", lw=0.6, alpha=0.55)

# bosses
for bx, by in ((6.5, 6.5), (OUT_W - 6.5, 6.5), (6.5, OUT_H - 6.5), (OUT_W - 6.5, OUT_H - 6.5)):
    a.add_patch(Circle((bx, by), 2.75, **PRINT)); a.add_patch(Circle((bx, by), 1.1, fc="white", ec="#1f2a37", lw=0.6))
# cord slot + tie post
r(a, 13.0 - 2.25, -0.6, 13.0 + 2.25, 3.0, fc="white", ec="#b3261e", lw=1, ls="--")
a.add_patch(Circle((18, 9), 2.0, **PRINT))

# margin labels with leader lines
leader(a, 23.605, 83, 23.605, 79.5, "eave (top wall + 4 corners)", ha="center", va="bottom")
leader(a, -8, 68, 14.6, 66, "PCB outline\n(green, thin, behind)", ha="right")
leader(a, -8, 58, 16, 58, "expansion PCB\n(dotted)", ha="right")
leader(a, -8, 48, 11.8, 60, "bay side wall (×2)", ha="right")
leader(a, -8, 38, 13.5, 58.8, "rails + crush ribs", ha="right")
leader(a, -8, 28, 20, 66, "microSD card", ha="right")
leader(a, 55, 74, 33.355, 68, "collar plate\n(window + bore)", ha="left")
leader(a, 55, 60, 33.355, 72.3, "USB-end wall + tongue\n(shell window, card\nnotch, bridge; snap)", ha="left")
leader(a, 55, 45, 27.9, 67.76, "lens: plate hole Ø7.5,\nbore Ø8.25, tip Ø6", ha="left")
leader(a, 55, 34, 30.3, 50.5, "hooks / stop ribs\n(far-end group)", ha="left")
leader(a, 55, 22, 23, 49.5, "far-end wall + ledge", ha="left")
a.text(4, 12.2, "M2 boss ×4", fontsize=6.5, ha="center")
a.text(13.0, -3.4, "cord slot 4.5×3", ha="center", **RED)
a.text(20.5, 9.3, "tie post Ø4", fontsize=6.5)

dim(a, 0, -8, OUT_W, -8, "47.21", off=0)
dim(a, OUT_W + 3, 0, OUT_W + 3, OUT_H, "80.80", vertical=True)
dim(a, 10.975, 46.2, 34.955, 46.2, "bay X 10.975..34.955")

a.set_xlim(*XLIM_B); a.set_ylim(*YLIM_B); a.set_aspect("equal"); a.axis("off")
a.set_title("B: front view, front plate removed (looking +Z)", fontsize=10)

# =================================================================
# PANEL C -- detail section at X = 22.9 (through the tongue), zoomed
# =================================================================
a = ac
# top wall
r(a, 3, OUT_H - 2.4, 28, OUT_H, **PRINT)
# collar (context, above the notch)
r(a, COLLAR_FRONT["z"][0], COLLAR_FRONT["y"][0], COLLAR_FRONT["z"][1], COLLAR_FRONT["y"][1], **NEW)
r(a, COLLAR_BACK["z"][0], COLLAR_BACK["y"][0], COLLAR_BACK["z"][1], COLLAR_BACK["y"][1], **NEW)

# USB-end wall with shell window + card notch cut, bridge solid
r(a, USB_WALL["z"][0], USB_WALL["y"][0], USB_WALL["z"][1], USB_WALL["y"][1], **NEW)
r(a, SHELL_WINDOW["z"][0], SHELL_WINDOW["y"][0], SHELL_WINDOW["z"][1], SHELL_WINDOW["y"][1], **CUT)
r(a, CARD_NOTCH["z"][0], CARD_NOTCH["y"][0], CARD_NOTCH["z"][1], CARD_NOTCH["y"][1], **CUT)
r(a, BRIDGE["z"][0], BRIDGE["y"][0], BRIDGE["z"][1], BRIDGE["y"][1], **NEW)

# PCB end + USB-C shell + card
r(a, BASE_PCB[0], 60, BASE_PCB[1], BASE_PCB[3], fc="#2f7d4f", **PART)
r(a, USB_SHELL[0], USB_SHELL[2], USB_SHELL[1], USB_SHELL[3], fc="#8f9aa6", **PART)
r(a, SD_CARD[0], 61, SD_CARD[1], SD_CARD[3], fc="#222", **PART)

# tongue + lip + ramp
r(a, TONGUE["z"][0], TONGUE["y"][0], TONGUE["z"][1], TONGUE["y"][1], **NEW)
lip_poly2 = Polygon([(LIP["z"][0], LIP["y"][0]), (LIP["z"][1], LIP["y"][0]),
                      (LIP_RAMP_TOP[0], LIP_RAMP_TOP[1]), (LIP["z"][0], LIP["y"][1])],
                     closed=True, fc="#a9c6e8", ec="#14508a", lw=0.9)
a.add_patch(lip_poly2)

# swing-in arc: PCB USB-end corner easing into the seated position (schematic)
pivot = (14.36, 70.29)
r0 = ((BASE_PCB[1] - pivot[0]) ** 2 + (BASE_PCB[3] - pivot[1]) ** 2) ** 0.5
th0 = np.degrees(np.arctan2(BASE_PCB[3] - pivot[1], BASE_PCB[1] - pivot[0]))
th = np.linspace(th0, th0 + 13, 30)
xs = pivot[0] + r0 * np.cos(np.radians(th))
ys = pivot[1] + r0 * np.sin(np.radians(th))
a.plot(xs, ys, color="#b3261e", lw=1.0, ls=":")
a.annotate("", xy=(xs[0], ys[0]), xytext=(xs[4], ys[4]),
           arrowprops=dict(arrowstyle="-|>", color="#b3261e", lw=1.0))

# labels via short leaders into the margins of the zoom
leader(a, 15, 81.7, 15, 80.4, "top wall", ha="center", va="bottom", fontsize=6.8)
leader(a, 4, 68, 6.3, 67, "collar", ha="left", fontsize=6.8, color=CALL_C)
leader(a, 20, 78.5, 15, 72.8, "USB-C shell", ha="left", fontsize=6.8)
leader(a, 5, 76, 11.5, 72.8, "front stop:\n0.10 over the shell", ha="left", fontsize=6.6, color=CALL_C)
leader(a, 12, 59, 16.7, 65, "PCB end", ha="center", va="top", fontsize=6.8)
leader(a, 23, 59, 24, 71.9, "tongue", ha="center", va="top", fontsize=6.8, color=CALL_C)
leader(a, 4.5, 55.5, 9.5, 61.3, "card", ha="center", va="top", fontsize=6.8)
leader(a, 17, 55.5, 17.7, 71.1, "snap: lip 0.4 over PCB\nedge; 0.6 mm deflection", ha="center", va="top",
       fontsize=6.5, color=CALL_C)
a.text(19, 74.2, "insertion\nswing", fontsize=6.3, color="#b3261e")

a.set_xlim(*XLIM_C); a.set_ylim(*YLIM_C); a.set_aspect("equal"); a.axis("off")
a.set_title("C: detail at X = 22.9 (tongue)", fontsize=9.5)

# =================================================================
# PANEL D (notes) -- shared style key
# =================================================================
a = an
a.axis("off")
a.set_xlim(0, 10); a.set_ylim(0, 10)
a.text(0.2, 9.6, "Style key (all panels)", fontsize=8.5, va="top", fontweight="bold", color="#1f2a37")
note_items = [
    ("#a9c6e8", "solid", "new v2 ring feature"),
    ("#cdd6e0", "solid", "unchanged printed body"),
    ("white", "dashed", "material cut (window,\nnotch, bore, relief)"),
    ("#cdd6e0", "dashed", "off-plane (shown for\nref., not at this X)"),
    ("#b3261e", "dashed", "hole / axis / play"),
]
yy = 8.6
for fc, style, txt in note_items:
    ls = "--" if style == "dashed" else "-"
    ec = "#b3261e" if fc == "#b3261e" else "#1f2a37"
    a.add_patch(Rectangle((0.2, yy - 0.35), 1.1, 0.6, fc=fc if fc != "#b3261e" else "white",
                           ec=ec, lw=0.8, ls=ls))
    a.text(1.6, yy - 0.05, txt, fontsize=6.8, va="center", ha="left", color="#1f2a37")
    yy -= 1.55
a.text(0.2, yy - 0.1, "Panel A legend numbers 1-15\napply to that panel only.", fontsize=6.6,
       va="top", color="#555")

fig.suptitle("XIAO puckcase v2 — bay redesign contract (2026-09-13)", fontsize=13, y=0.985)
fig.savefig("review_v2/sketch_v2.png", dpi=150)
print("ok")
