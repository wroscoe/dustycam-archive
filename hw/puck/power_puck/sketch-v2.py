"""2D contract sketch for power puck v2: side section at x = CX and a plan
section through the back cup at z = 30 (looking from the back).  Not CAD —
numbers are the design intent from caselib.py; regenerate with
  ~/.claude/skills/cad/.venv/bin/python sketch-v2.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

OUT_W, OUT_H, WALL = 47.21, 80.8, 2.4
CX = OUT_W / 2
Z_SEAM, LEDGE_T, CHAM, Z_FLOOR, Z_BACK = 18.4, 1.6, 1.75, 36.4, 38.8
JACK_ZC, NUT_D, BODY_D, REACH = 29.075, 12.0, 10.0, 13.0
CHG_Y0, CHG_Y1, CHG_X0, CHG_X1 = 51.0, 76.4, 7.73, 39.48
Z_BARE, Z_COMPS = 33.0, 26.63
USB_ZC = 30.33

fig, (ax, ap) = plt.subplots(1, 2, figsize=(15, 9), gridspec_kw={"width_ratios": [1.15, 1]})
PRINT = dict(fc="#cdd6e0", ec="#1f2a37", lw=1.0)
PART = dict(ec="#1f2a37", lw=0.8)

def r(a, x0, y0, x1, y1, **kw):
    a.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, **kw))

# ---------------- side section (Z right, Y up) ----------------
a = ax
r(a, 0, 0, 2.4, OUT_H, **PRINT)                                  # front plate
for y0, y1 in ((2.55, 4.15), (OUT_H - 4.15, OUT_H - 2.55)):
    r(a, 2.4, y0, 9.9, y1, **PRINT); r(a, 10.9, y0, 18.4, y1, **PRINT)   # lips
for y0, y1 in ((0, 2.4), (OUT_H - 2.4, OUT_H)):
    r(a, 2.4, y0, 18.4, y1, **PRINT)                              # tube walls
    r(a, 21.75, y0, Z_FLOOR, y1, **PRINT)                         # skirt
r(a, 18.4, 0, 20.0, 4.15, **PRINT); r(a, 18.4, OUT_H - 4.15, 20.0, OUT_H, **PRINT)   # seam ring
a.fill([20.0, 21.75, 21.75, 20.0], [4.15, 2.4, 0, 0], fc="#cdd6e0", ec="#1f2a37", lw=1.0)
a.fill([20.0, 21.75, 21.75, 20.0], [OUT_H - 4.15, OUT_H - 2.4, OUT_H, OUT_H], fc="#cdd6e0", ec="#1f2a37", lw=1.0)
r(a, Z_FLOOR, 0, Z_BACK, OUT_H, **PRINT)                         # back wall
# openings (white)
r(a, JACK_ZC - 3.76, -0.6, JACK_ZC + 3.76, 2.4 + 0.6, fc="white", ec="#b3261e", lw=1, ls="--")
r(a, USB_ZC - 4.75, OUT_H - 3.0, USB_ZC + 4.75, OUT_H + 0.6, fc="white", ec="#b3261e", lw=1, ls="--")
# purchased
r(a, 2.4, 8.0, 13.4, 75.0, fc="#efe3bd", **PART)                 # battery
r(a, Z_BARE, CHG_Y0, Z_BARE + 1.57, CHG_Y1, fc="#c9a94a", **PART)     # PCB
r(a, Z_COMPS, CHG_Y0, Z_BARE, CHG_Y1, fc="#f6edd6", ec="#8a7a4a", lw=0.8, ls=":")  # comps
r(a, Z_BARE - 4.77, CHG_Y1, Z_BARE - 0.57, CHG_Y1 + 1.0, fc="#8f9aa6", **PART)     # USB-C shell
r(a, Z_BARE, 53.5, Z_FLOOR, 56.3, fc="#b8c4d0", **PART); r(a, Z_BARE, 73.9, Z_FLOOR, 76.6, fc="#b8c4d0", **PART)
r(a, JACK_ZC - 6, 2.4, JACK_ZC + 6, 4.9, fc="#8f9aa6", **PART)        # nut
r(a, JACK_ZC - 5, 4.9, JACK_ZC + 5, REACH, fc="#8f9aa6", **PART)      # body
r(a, JACK_ZC - 5.5, -2.0, JACK_ZC + 5.5, 0, fc="#8f9aa6", **PART)     # flange
r(a, Z_COMPS + 0.2, 45.0, Z_COMPS + 4.7, 51.0, fc="#d6e4f0", **PART)  # JST plugs
r(a, 26.1, 3.0, 32.1, 47.0, fc="#fbe3e3", ec="#b3261e", lw=0.6, ls=":")  # LOAD lead path (at x=9..15, projected)
# labels
L = dict(fontsize=8, color="#1f2a37")
a.text(0.4, 78.0, "front\nplate", rotation=90, va="top", **L)
a.text(4.5, 78.6, "tube", **L); a.text(23.5, 78.6, "back cup", **L)
a.text(4.0, 40, "battery\n11×36×67", **L); a.text(27.5, 63, "charger", **L)
a.text(27.0, 41, "JST plugs", **L); a.text(20.5, 12, "jack", **L)
a.text(19.0, 22.3, "seam ring 1.6\n+ 45° chamfer", fontsize=7, color="#1f2a37")
a.text(26.5, 20, "LOAD lead\n(x=9…15)", fontsize=7, color="#b3261e")
a.text(Z_BACK + 0.5, OUT_H - 2, "USB-C port\n15×9.5", fontsize=8, color="#b3261e")
# dims
D = dict(color="#b3261e", fontsize=8)
def dh(y, z0, z1, s):
    a.annotate("", (z0, y), (z1, y), arrowprops=dict(arrowstyle="<->", color="#b3261e", lw=0.8))
    a.text((z0 + z1) / 2, y + 0.8, s, ha="center", **D)
def dv(z, y0, y1, s):
    a.annotate("", (z, y0), (z, y1), arrowprops=dict(arrowstyle="<->", color="#b3261e", lw=0.8))
    a.text(z + 0.6, (y0 + y1) / 2, s, va="center", **D)
dh(-7, 0, Z_BACK, "38.80"); dh(85, 0, Z_SEAM, "18.40 to seam"); dh(85, Z_SEAM, Z_FLOOR, "18.00 cup"); dh(85, Z_FLOOR, Z_BACK, "2.4")
dv(43, 0, OUT_H, "80.80"); dv(15.0, 0, REACH, "13.0 reach"); dv(40.5, CHG_Y0, CHG_Y1, "charger\n51.0–76.4")
dv(15.5, 8.0, 75.0, "battery 8–75"); dv(JACK_ZC + 7, 0, 2.4 + NUT_D / 2 + 0, "")
a.text(JACK_ZC - 3.5, -4.5, "Ø7.52 @ z 29.08", fontsize=7, color="#b3261e")
a.set_xlim(-10, 52); a.set_ylim(-10, 92); a.set_aspect("equal"); a.set_xlabel("Z (mm) — front face at 0"); a.set_ylabel("Y (mm) — bottom face at 0")
a.set_title("Power puck v2 — side section at x = CX", fontsize=11)
a.grid(True, lw=0.3, alpha=0.4)

# ---------------- plan section through the cup at z = 30, viewed from the back (X right, Y up) ----------------
a = ap
r(a, 0, 0, OUT_W, OUT_H, **PRINT)
r(a, WALL, WALL, OUT_W - WALL, OUT_H - WALL, fc="white", ec="#1f2a37", lw=1.0)
r(a, CHG_X0, CHG_Y0, CHG_X1, CHG_Y1, fc="#c9a94a", **PART)
for hx, hy in ((2.54, 2.54), (29.21, 2.54), (2.54, 22.86), (29.21, 22.86)):
    a.add_patch(Circle((CHG_X0 + hx, CHG_Y0 + hy), 2.75, fc="#b8c4d0", ec="#1f2a37", lw=0.6))
r(a, CX - 4.47, CHG_Y1, CX + 4.47, CHG_Y1 + 1.0, fc="#8f9aa6", **PART)   # USB-C shell
r(a, CX - 7.5, OUT_H - WALL - 0.3, CX + 7.5, OUT_H + 0.3, fc="white", ec="#b3261e", lw=1, ls="--")  # port
for xc in (CHG_X1 - 20.32, CHG_X1 - 11.43):
    r(a, xc - 2.95, CHG_Y0 - 6.0, xc + 2.95, CHG_Y0, fc="#d6e4f0", **PART)
r(a, CX - 6, 2.4, CX + 6, 4.9, fc="#8f9aa6", **PART)                          # nut (12 wide, 2.5 thick, on the inner wall)
r(a, CX - 5, 4.9, CX + 5, REACH, fc="#8f9aa6", **PART)                          # jack body
r(a, CX - 12 - 3.5, -0.3, CX - 12 + 3.5, WALL + 0.3, fc="white", ec="#b3261e", lw=1, ls="--")  # LOAD slot
r(a, 9, 3.0, 15, 47.0, fc="#fbe3e3", ec="#b3261e", lw=0.6, ls=":")               # LOAD lead
r(a, 26, 40, 30, 47, fc="#fbe3e3", ec="#b3261e", lw=0.6, ls=":")                 # BATT lead
a.text(CHG_X0 + 1, CHG_Y1 - 4, "bq25185 (JST edge down)", fontsize=8)
a.text(CX + 7, 5.5, "jack nut Ø12 / body Ø10", fontsize=8); a.text(2.5, -5, "LOAD slot 7×6 @ x = CX−12", fontsize=8, color="#b3261e")
a.text(CX - 7, OUT_H + 2.5, "USB-C port", fontsize=8, color="#b3261e")
a.text(8.5, 49, "LOAD lead", fontsize=7, color="#b3261e"); a.text(30.5, 42, "BATT lead", fontsize=7, color="#b3261e")
def ph(y, x0, x1, s):
    a.annotate("", (x0, y), (x1, y), arrowprops=dict(arrowstyle="<->", color="#b3261e", lw=0.8)); a.text((x0 + x1) / 2, y + 0.8, s, ha="center", **D)
def pv(x, y0, y1, s):
    a.annotate("", (x, y0), (x, y1), arrowprops=dict(arrowstyle="<->", color="#b3261e", lw=0.8)); a.text(x + 0.6, (y0 + y1) / 2, s, va="center", **D)
ph(-8, 0, OUT_W, "47.21"); ph(85, CHG_X0, CHG_X1, "31.75"); pv(50, 0, OUT_H, "80.80"); pv(42, REACH, CHG_Y0, "32 clear")
a.set_xlim(-6, 58); a.set_ylim(-11, 92); a.set_aspect("equal"); a.set_xlabel("X (mm)"); a.set_ylabel("Y (mm)")
a.set_title("Plan section through the back cup (z ≈ 30), from the back", fontsize=11)
a.grid(True, lw=0.3, alpha=0.4)
fig.suptitle("Power puck v2 — contract sketch (design intent, mm; see caselib.py / check.py for the checked geometry)", fontsize=12)
fig.tight_layout()
fig.savefig("sketch-v2.png", dpi=110)
print("sketch-v2.png written")
