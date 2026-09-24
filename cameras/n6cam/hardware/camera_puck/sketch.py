"""2D contract sketch for the camera puck v1: side section at x = LOAD_XC
and a plan section through the cam plate at z = -5.  Not CAD — numbers are
the design intent from caselib.py; regenerate with
  ~/.claude/skills/cad/.venv/bin/python sketch.py

Like hardware/power_puck/sketch-v2.py, this is a composite documentation
diagram: the wall bands are true extrusion cross-sections (constant across
the section plane), while purchased/reference features (board, lens
barrel, ports) are drawn at their real Y/Z or X/Y extents as elevation
overlays even where the literal cut plane does not pass through them —
the goal is a to-scale, dimensioned contract, not a CAD re-derivation.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

import caselib as C

fig, (ax, ap) = plt.subplots(1, 2, figsize=(16, 9), gridspec_kw={"width_ratios": [1.3, 1]})
PRINT = dict(fc="#cdd6e0", ec="#1f2a37", lw=1.0)
PART = dict(ec="#1f2a37", lw=0.8)


def r(a, x0, y0, x1, y1, **kw):
    a.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, **kw))


# ---------------- side section (Z right, Y up) at x = LOAD_XC ----------------
a = ax

# back plate: outer shell Z_BACK_OUT..Z_SEAM, lip Z_SEAM..Z_PLATE_BOT
for y0, y1 in ((C.OUT_Y0, C.OUT_Y0 + C.WALL), (C.OUT_Y1 - C.WALL, C.OUT_Y1)):
    r(a, C.Z_BACK_OUT, y0, C.Z_SEAM, y1, **PRINT)
for y0, y1 in ((C.LIP_Y0, C.LIP_Y0 + C.LIP_WALL), (C.LIP_Y1 - C.LIP_WALL, C.LIP_Y1)):
    r(a, C.Z_SEAM, y0, C.Z_PLATE_BOT, y1, **PRINT)

# front cup: SOCK-thickness wall Z_SEAM..Z_SHOULDER, CAV-thickness wall
# Z_SHOULDER..Z_CEIL, solid ceiling cap Z_CEIL..Z_FRONT_OUT
for y0, y1 in ((C.OUT_Y0, C.OUT_Y0 + C.WALL), (C.OUT_Y1 - C.WALL, C.OUT_Y1)):
    r(a, C.Z_SEAM, y0, C.Z_SHOULDER, y1, **PRINT)
for y0, y1 in ((C.OUT_Y0, C.OUT_Y0 + C.WALL + C.SHOULDER),
               (C.OUT_Y1 - C.WALL - C.SHOULDER, C.OUT_Y1)):
    r(a, C.Z_SHOULDER, y0, C.Z_CEIL, y1, **PRINT)
r(a, C.Z_CEIL, C.OUT_Y0, C.Z_FRONT_OUT, C.OUT_Y1, **PRINT)

# cam plate, sandwiched between the front cup shoulder and the back plate lip
r(a, C.Z_PLATE_BOT, C.PLATE_Y0, C.Z_SHOULDER, C.PLATE_Y1, **PRINT)

# openings in the front cup's -Y wall (LOAD slot at this x; USB port and
# vent shown for reference at their own x — see the plan view)
r(a, C.LOAD_ZC - C.LOAD_H / 2, C.OUT_Y0 - 0.6, C.LOAD_ZC + C.LOAD_H / 2,
  C.OUT_Y0 + C.WALL + C.SHOULDER + 0.6, fc="white", ec="#b3261e", lw=1, ls="--")
r(a, C.USB_ZC - C.USB_H / 2, C.OUT_Y0 - 0.6, C.USB_ZC + C.USB_H / 2,
  C.OUT_Y0 + C.WALL + C.SHOULDER + 0.6, fc="white", ec="#8a7a4a", lw=0.8, ls=":")

# USB cap, press-in from outside the -Y wall (schematic, this x)
cap_z0, cap_z1 = C.USB_ZC - C.CAP_H / 2, C.USB_ZC + C.CAP_H / 2
r(a, cap_z0, C.OUT_Y0 - C.CAP_HEAD_T, cap_z1, C.OUT_Y0, fc="#8f9aa6", **PART)
r(a, cap_z0, C.OUT_Y0, cap_z1, C.OUT_Y0 + C.CAP_DEPTH, fc="#d6e4f0", **PART)

# board outline (thin, Z ~ 0..1.30, full board Y span)
r(a, 0.0, C.BOARD_Y0, 1.30, C.BOARD_Y1, fc="#c9a94a", **PART)

# M12 lens barrel (schematic — barrel axis is at x=17.81, off this x=10
# section; shown for reference, per spec)
BARREL_Z0, BARREL_Z1 = 1.30 + 13.25, 1.30 + 29.95
r(a, BARREL_Z0, C.LENS_AXIS[1] - C.LENS_BARREL_D / 2, BARREL_Z1,
  C.LENS_AXIS[1] + C.LENS_BARREL_D / 2, fc="#b8c4d0", **PART)
r(a, C.Z_CEIL - 1.0, C.LENS_AXIS[1] - C.LENS_HOLE_D / 2, C.Z_FRONT_OUT + 0.4,
  C.LENS_AXIS[1] + C.LENS_HOLE_D / 2, fc="white", ec="#8a7a4a", lw=0.8, ls=":")

# LOAD lead mocks (JST plug + cable), for reference
r(a, 1.53, -6.0, 6.03, 0.0, fc="#d6e4f0", **PART)
r(a, 2.28, C.OUT_Y0 - 15.0, 5.28, -5.0, fc="#fbe3e3", ec="#b3261e", lw=0.6, ls=":")

L = dict(fontsize=8, color="#1f2a37")
a.text(C.Z_BACK_OUT - 5.5, C.OUT_Y1 + 3, "back\nplate", ha="center", **L)
a.text((C.Z_SEAM + C.Z_FRONT_OUT) / 2, C.OUT_Y1 + 3, "front cup", ha="center", **L)
a.text(C.Z_PLATE_BOT - 0.2, C.PLATE_Y1 + 2.5, "cam\nplate", ha="right", fontsize=7.5, color="#1f2a37")
a.text(2.0, C.BOARD_Y1 + 1.5, "N6 PCB", **L)
a.text(BARREL_Z0 - 1, C.LENS_AXIS[1] + C.LENS_BARREL_D / 2 + 6,
       "M12 lens barrel\n(axis x=17.81, off this\nx-slice, for reference)",
       fontsize=7, color="#1f2a37", ha="center")
a.text(C.LOAD_ZC, C.OUT_Y0 - 6.0, "LOAD slot\n7x6 @ x=10.0, z=3.78", fontsize=7,
       color="#b3261e", ha="center")
a.text(C.USB_ZC + 6, C.OUT_Y0 - 6.0, "USB port + cap\n(x=23.67, off this\nx-slice, for reference)",
       fontsize=7, color="#8a7a4a", ha="left")

D = dict(color="#b3261e", fontsize=8)


def dh(y, z0, z1, s):
    a.annotate("", (z0, y), (z1, y), arrowprops=dict(arrowstyle="<->", color="#b3261e", lw=0.8))
    a.text((z0 + z1) / 2, y + 0.8, s, ha="center", **D)


def dv(z, y0, y1, s):
    a.annotate("", (z, y0), (z, y1), arrowprops=dict(arrowstyle="<->", color="#b3261e", lw=0.8))
    a.text(z + 0.6, (y0 + y1) / 2, s, va="center", **D)


dh(C.OUT_Y0 - 9, C.Z_BACK_OUT, C.Z_FRONT_OUT, f"{C.Z_FRONT_OUT - C.Z_BACK_OUT:.2f} depth")
dh(C.OUT_Y1 + 8, C.Z_BACK_OUT, C.Z_SEAM, f"{C.Z_SEAM - C.Z_BACK_OUT:.1f}")
dh(C.OUT_Y1 + 8, C.Z_SEAM, C.Z_SHOULDER, f"{C.Z_SHOULDER - C.Z_SEAM:.1f}")
dh(C.OUT_Y1 + 8, C.Z_SHOULDER, C.Z_CEIL, f"{C.Z_CEIL - C.Z_SHOULDER:.1f}")
dh(C.OUT_Y1 + 8, C.Z_CEIL, C.Z_FRONT_OUT, f"{C.Z_FRONT_OUT - C.Z_CEIL:.1f}")
dv(C.Z_FRONT_OUT + 6, C.OUT_Y0, C.OUT_Y1, f"OUT_H {C.OUT_H:.2f}")
dv(C.Z_FRONT_OUT + 6, C.BOARD_Y1, C.CAV_Y1, f"TOP_CH {C.TOP_CH:.2f}")

a.set_xlim(C.Z_BACK_OUT - 6, C.Z_FRONT_OUT + 14)
a.set_ylim(C.OUT_Y0 - 20, C.OUT_Y1 + 16)
a.set_aspect("equal")
a.set_xlabel("Z (mm) — optical axis, lens at +Z")
a.set_ylabel("Y (mm) — board frame, 0 at the PCB -Y edge")
a.set_title("Camera puck v1 — side section at x = LOAD_XC = 10.0", fontsize=11)
a.grid(True, lw=0.3, alpha=0.4)

# ---------------- plan section through the cam plate at z = -5 ----------------
a = ap
r(a, C.OUT_X0, C.OUT_Y0, C.OUT_X1, C.OUT_Y1, **PRINT)
r(a, C.SOCK_X0, C.SOCK_Y0, C.SOCK_X1, C.SOCK_Y1, fc="white", ec="#1f2a37", lw=1.0)
r(a, C.PLATE_X0, C.PLATE_Y0, C.PLATE_X1, C.PLATE_Y1, fc="#cdd6e0", ec="#1f2a37", lw=0.8)
r(a, C.CAV_X0, C.CAV_Y0, C.CAV_X1, C.CAV_Y1, fc="none", ec="#8a7a4a", lw=0.8, ls=":")
r(a, C.BOARD_X0, C.BOARD_Y0, C.BOARD_X1, C.BOARD_Y1, fc="#c9a94a", ec="#1f2a37", lw=0.6, alpha=0.5)

for cx, cy in C.MOUNT_HOLES:
    a.add_patch(Circle((cx, cy), C.BOSS_D / 2, fc="#b8c4d0", ec="#1f2a37", lw=0.6))
    a.add_patch(Circle((cx, cy), C.BOSS_PILOT_D / 2, fc="white", ec="#1f2a37", lw=0.4))

a.add_patch(Circle(C.LENS_AXIS, C.LENS_HOLE_D / 2, fc="none", ec="#8a7a4a", lw=0.8, ls=":"))
a.add_patch(Circle(C.LENS_AXIS, C.LENS_BARREL_D / 2, fc="none", ec="#1f2a37", lw=0.6))

r(a, C.LOAD_XC - C.LOAD_W / 2, C.OUT_Y0 - 0.3, C.LOAD_XC + C.LOAD_W / 2,
  C.OUT_Y0 + C.WALL + 0.3, fc="white", ec="#b3261e", lw=1, ls="--")
r(a, C.USB_XC - C.USB_W / 2, C.OUT_Y0 - 0.3, C.USB_XC + C.USB_W / 2,
  C.OUT_Y0 + C.WALL + 0.3, fc="white", ec="#8a7a4a", lw=0.8, ls=":")
for vxc in C.VENT_XC:
    r(a, vxc - C.VENT_W / 2, C.OUT_Y0 - 0.3, vxc + C.VENT_W / 2,
      C.OUT_Y0 + C.WALL + 0.3, fc="white", ec="#1f2a37", lw=0.6, ls="--")

a.add_patch(Circle((C.CX, C.CY), 0.6, fc="#b3261e", ec="none"))
a.text(C.CX + 1, C.CY, "CX,CY", fontsize=7, color="#b3261e")

a.text(C.OUT_X0 + 1, C.OUT_Y1 - 3, "OUT (front cup outer)", fontsize=7.5)
a.text(C.SOCK_X0 + 1, C.SOCK_Y1 - 3, "SOCK (back plate lip pocket)", fontsize=7.5)
a.text(C.CAV_X0 + 1, C.CAV_Y0 + 1, "CAV (board cavity, z Z_SHOULDER..Z_CEIL)", fontsize=6.5, color="#8a7a4a")
a.text(C.PLATE_X0 + 1, C.PLATE_Y0 - 3.0, "PLATE (cam plate, this z)", fontsize=7.5)
a.text(C.LOAD_XC - 3, C.OUT_Y0 - 4.5, "LOAD slot", fontsize=7, color="#b3261e")
a.text(C.USB_XC - 3, C.OUT_Y0 - 4.5, "USB port", fontsize=7, color="#8a7a4a")
a.text(C.VENT_XC[0] - 4, C.OUT_Y0 - 8, "vents", fontsize=7)

D2 = dict(color="#b3261e", fontsize=8)


def ph(y, x0, x1, s):
    a.annotate("", (x0, y), (x1, y), arrowprops=dict(arrowstyle="<->", color="#b3261e", lw=0.8))
    a.text((x0 + x1) / 2, y + 0.8, s, ha="center", **D2)


def pv(x, y0, y1, s):
    a.annotate("", (x, y0), (x, y1), arrowprops=dict(arrowstyle="<->", color="#b3261e", lw=0.8))
    a.text(x + 0.6, (y0 + y1) / 2, s, va="center", **D2)


ph(C.OUT_Y0 - 12, C.OUT_X0, C.OUT_X1, f"{C.OUT_X1 - C.OUT_X0:.2f} width")
pv(C.OUT_X1 + 4, C.OUT_Y0, C.OUT_Y1, f"OUT_H {C.OUT_H:.2f}")

a.set_xlim(C.OUT_X0 - 6, C.OUT_X1 + 12)
a.set_ylim(C.OUT_Y0 - 16, C.OUT_Y1 + 6)
a.set_aspect("equal")
a.set_xlabel("X (mm) — board frame")
a.set_ylabel("Y (mm) — board frame")
a.set_title("Plan section through the cam plate (z = -5)", fontsize=11)
a.grid(True, lw=0.3, alpha=0.4)

fig.suptitle("Camera puck v1 — contract sketch (design intent, mm; see caselib.py / check.py for the checked geometry)", fontsize=12)
fig.tight_layout()
fig.savefig("sketch.png", dpi=110)
print("sketch.png written")
