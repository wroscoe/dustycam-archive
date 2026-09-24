"""2D contract sketch for tubecase v2 (everything inside the 2" tube). Run with the cad venv python.
Numbers mirror DESIGN.md v2; this is a drawing, not the model."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon

# --- numbers (mm) ---
tube_od, tube_id = 50.8, 44.5
floor_t, base_wall = 4.5, 1.6
base_r, base_ir = 22.05, 22.05 - base_wall                      # liner cup inside the tube: 22.05 / 20.45
z_base1 = 43.5                                                   # cup top rim = mid plate seat
spig_r, spig_ir = base_r, base_ir
z_mid0, z_mid1 = 43.5, 47.5
tube_len = 87.5; z_tube0, z_tube1 = 0.0, tube_len               # tube is the whole skin
cap_plug = 8.0; z_cap1 = z_tube1 + 2.0
# charger standing on its USB edge, PCB back face at x=3
ch_x0, ch_t, ch_comp = 3.0, 1.57, 6.37
ch_z0, ch_h, ch_w = 5.7, 25.4, 31.75
plug_h = 12.0
# battery standing on a short end
bat_x0, bat_t, bat_w, bat_h = -6.0, 4.75, 29.0, 36.0
bay_x0, bay_x1, bay_y = -6.0, 0.25, 15.0
# jack, vertical, through the floor
jack_x, jack_hole, jack_cb, jack_cb_d, jack_body, jack_depth = -14.5, 7.5, 10.5, 2.2, 11.0, 13.0
# camera
pcb_x, pcb_t = 4.29, 1.25
z_board_top = 73.15; board_len = 21.25
lens_z = z_board_top - 3.53; lens_tip_x = 18.25
cr_x0, cr_x1, cr_y = 1.29, 10.29, 11.3
rail_z0 = 49.5

fig, axes = plt.subplots(1, 3, figsize=(17, 9), gridspec_kw={"width_ratios": [1.15, 1, 1]})
for ax in axes:
    ax.set_aspect("equal"); ax.grid(True, lw=0.3, alpha=0.4)

# ================= A: section through the axis, looking along -Y =================
ax = axes[0]; ax.set_title("A. Section on the axis (XZ), +X = lens direction")
def box(ax, x0, x1, z0, z1, **kw):
    ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, **kw))
base_kw = dict(fc="#c9d3dc", ec="k", lw=1)
# base cup: floor, walls, cone, spigot (left and right halves)
box(ax, -base_r, base_r, 0, floor_t, **base_kw)
for s in (-1, 1):
    box(ax, s * base_ir, s * base_r, floor_t - 0.01, z_base1, **base_kw)
    ax.plot([s * 22.6, s * 19.5], [10, 10], "k-", lw=1.2)                      # optional M2 through the tube into the base
ax.text(0, 9, "optional 2 x M2 through the tube\ninto the base wall, at ±Y", ha="center", fontsize=7)
# jack: counterbore + hole + envelope
box(ax, jack_x - jack_cb / 2, jack_x + jack_cb / 2, 0, jack_cb_d, fc="white", ec="k", lw=0.8)
box(ax, jack_x - jack_hole / 2, jack_x + jack_hole / 2, 0, floor_t, fc="white", ec="k", lw=0.8)
box(ax, jack_x - 5, jack_x + 5, 0.2, jack_cb_d, fc="#f2d16b", ec="k", lw=0.8)                         # flange
box(ax, jack_x - jack_body / 2, jack_x + jack_body / 2, floor_t, jack_cb_d + jack_depth, fc="#f2d16b", ec="k", lw=0.8, alpha=0.8)  # nut/body
ax.text(jack_x, jack_cb_d + jack_depth + 1, "jack\nlugs", ha="center", fontsize=8)
# battery + swell bay
box(ax, bay_x0, bay_x1, floor_t, floor_t + bat_h, fc="none", ec="k", ls="--", lw=0.8)
box(ax, bat_x0, bat_x0 + bat_t, floor_t, floor_t + bat_h, fc="#9fd39f", ec="k", lw=1)
ax.text(bat_x0 + bat_t / 2, floor_t + bat_h / 2, "BAT\n500\nmAh", ha="center", va="center", fontsize=8)
# charger PCB + components + plug
box(ax, ch_x0, ch_x0 + ch_t, ch_z0, ch_z0 + ch_h, fc="#3a7d44", ec="k", lw=1)
box(ax, ch_x0 + ch_t, ch_x0 + ch_t + ch_comp, ch_z0, ch_z0 + ch_h, fc="#3a7d44", ec="k", lw=0.6, alpha=0.35, hatch="//")
box(ax, ch_x0 + ch_t, ch_x0 + ch_t + 6, ch_z0 + ch_h, ch_z0 + ch_h + plug_h, fc="white", ec="k", ls="--", lw=0.8)
ax.text(ch_x0 + ch_t + 3, ch_z0 + ch_h + plug_h / 2, "JST\nplugs", ha="center", va="center", fontsize=7)
ax.text(ch_x0 + 5, ch_z0 + 10, "bq25185", rotation=90, ha="center", va="center", fontsize=8, color="w")
box(ax, ch_x0 - 0.2, ch_x0 + ch_t + 0.2, floor_t, ch_z0 - 1.0, fc="#dfe6ee", ec="k", lw=0.6)   # USB shell relief
# mid plate + bosses + cradle + board + lens
box(ax, -spig_r, spig_r, z_mid0, z_mid1, fc="#c9d3dc", ec="k", lw=1)
for s in (-1, 1):
    box(ax, s * 18.75 - 2.5, s * 18.75 + 2.5, z_mid0 - 8, z_mid0, fc="#b0bcc8", ec="k", lw=0.6)
    ax.plot([s * 18.75, s * 18.75], [z_mid0 - 6, z_mid1 + 1], "k-", lw=0.8)   # M2 screw axis
box(ax, cr_x0, cr_x0 + 3, z_mid1, z_board_top + 0.5, fc="#c9d3dc", ec="k", lw=1)           # cradle back
box(ax, cr_x0, cr_x1, rail_z0, rail_z0 + 2, fc="#c9d3dc", ec="k", lw=1)                     # rail
box(ax, cr_x0, cr_x1, z_mid1, rail_z0, fc="#c9d3dc", ec="k", lw=1)                          # pedestal
box(ax, pcb_x, pcb_x + pcb_t, z_board_top - board_len, z_board_top, fc="#3a7d44", ec="k", lw=1)
box(ax, pcb_x + pcb_t, pcb_x + 8.2, z_board_top - 14, z_board_top - 2, fc="#3a7d44", ec="k", lw=0.6, alpha=0.35, hatch="//")
box(ax, pcb_x + 8.2, lens_tip_x, lens_z - 3.9, lens_z + 3.9, fc="#222", ec="k")            # camera head + lens
ax.annotate("", xy=(lens_tip_x + 4, lens_z), xytext=(lens_tip_x + 0.5, lens_z), arrowprops=dict(arrowstyle="->"))
box(ax, pcb_x - 3.1, pcb_x, z_board_top - 1, z_board_top + 3.1, fc="#888", ec="k", lw=0.6)   # SD card (sticks up)
ax.text(pcb_x + 1.4, z_board_top - 10, "XIAO", rotation=90, ha="center", va="center", fontsize=7, color="w")
ax.text(pcb_x - 1, z_board_top + 4.5, "USB + SD up", ha="center", fontsize=7)
# tube (two walls) + cap
for s in (-1, 1):
    box(ax, s * tube_id / 2, s * tube_od / 2, z_tube0, z_tube1, fc="#dcefff", ec="#2b6cb0", lw=1)
box(ax, -22.1, 22.1, z_tube1 - cap_plug, z_tube1, **base_kw)
box(ax, -base_r, base_r, z_tube1, z_cap1, **base_kw)
for s in (-1, 1):
    box(ax, s * 20.1, s * 22.1, z_tube1 - 5.6, z_tube1 - 2.3, fc="white", ec="k", lw=0.6)      # O-ring groove
ax.text(0, z_tube1 - 4, "cap plug 8 deep, O-ring 40x2.5", ha="center", fontsize=7)
# dimensions
def hdim(ax, x0, x1, z, txt, off=0):
    ax.annotate("", xy=(x0, z), xytext=(x1, z), arrowprops=dict(arrowstyle="<->", lw=0.8))
    ax.text((x0 + x1) / 2, z + 0.8 + off, txt, ha="center", fontsize=7)
def vdim(ax, x, z0, z1, txt):
    ax.annotate("", xy=(x, z0), xytext=(x, z1), arrowprops=dict(arrowstyle="<->", lw=0.8))
    ax.text(x + 0.8, (z0 + z1) / 2, txt, va="center", fontsize=7, rotation=90)
hdim(ax, -tube_od / 2, tube_od / 2, -4, "Ø50.8 tube OD, nothing outside it")
hdim(ax, -tube_id / 2, tube_id / 2, z_cap1 + 3, "Ø44.5 tube ID")
vdim(ax, 29, 0, z_base1, "base liner 43.5")
vdim(ax, 33, z_tube0, z_tube1, "tube 87.5")
vdim(ax, 36, 0, z_cap1, "overall 89.5")
vdim(ax, -29, floor_t, z_mid0, "compartment 39")
ax.text(-29, lens_z, "lens at\nz 69.6", fontsize=7, ha="center")
ax.set_xlim(-38, 38); ax.set_ylim(-8, 96); ax.set_xlabel("X (mm)"); ax.set_ylabel("Z (mm)")

# ================= B: plan section at Z = 20, looking down =================
ax = axes[1]; ax.set_title("B. Plan section at Z = 20 (looking down)")
ax.add_patch(Circle((0, 0), tube_od / 2, fc="#dcefff", ec="#2b6cb0"))
ax.add_patch(Circle((0, 0), tube_id / 2, fc="white", ec="#2b6cb0"))
ax.add_patch(Circle((0, 0), base_r, fc="#c9d3dc", ec="k"))
ax.add_patch(Circle((0, 0), base_ir, fc="white", ec="k"))
ax.text(0, 18.5, "liner ID Ø40.9", ha="center", fontsize=7)
# wall ribs (card guides): charger slot at x 2.75..4.85, ribs 1.5 thick from the wall to y ±16.3
for sy in (-1, 1):
    for x0, x1 in ((0.25, 2.75), (4.85, 6.35)):
        ax.add_patch(Rectangle((x0, min(sy * 16.3, sy * 20.6)), x1 - x0, abs(20.6 - 16.3), fc="#c9d3dc", ec="k", lw=0.6))
    for x0, x1 in ((-7.5, -6.0),):
        ax.add_patch(Rectangle((x0, min(sy * 15.0, sy * 20.6)), x1 - x0, abs(20.6 - 15.0), fc="#c9d3dc", ec="k", lw=0.6))
# battery + bay
ax.add_patch(Rectangle((bay_x0, -bay_y), bay_x1 - bay_x0, 2 * bay_y, fc="none", ec="k", ls="--", lw=0.8))
ax.add_patch(Rectangle((bat_x0, -bat_w / 2), bat_t, bat_w, fc="#9fd39f", ec="k"))
ax.text(bat_x0 + bat_t / 2, 0, "BAT", rotation=90, ha="center", va="center", fontsize=8)
# charger
ax.add_patch(Rectangle((ch_x0, -ch_w / 2), ch_t, ch_w, fc="#3a7d44", ec="k"))
ax.add_patch(Rectangle((ch_x0 + ch_t, -ch_w / 2), ch_comp, ch_w, fc="#3a7d44", ec="k", lw=0.6, alpha=0.35, hatch="//"))
for y0, y1 in ((0.5, 8.4), (-8.4, -0.5)):
    ax.add_patch(Rectangle((ch_x0 + ch_t, y0), 6.37, y1 - y0, fc="white", ec="k", lw=0.8))
ax.text(ch_x0 + ch_t + 3.2, 4.4, "JST", ha="center", va="center", fontsize=6)
ax.text(ch_x0 + ch_t + 3.2, -4.4, "JST", ha="center", va="center", fontsize=6)
ax.text(ch_x0 + 0.8, -12, "bq25185 PCB", rotation=90, ha="center", va="center", fontsize=6, color="w")
# jack, drain, bosses (above, dashed)
ax.add_patch(Circle((jack_x, 0), jack_body / 2, fc="#f2d16b", ec="k"))
ax.add_patch(Circle((jack_x, 0), jack_hole / 2, fc="white", ec="k", lw=0.6))
ax.text(jack_x, -8, "jack\nØ11 nut", ha="center", fontsize=7)
ax.add_patch(Circle((13, -13), 1, fc="white", ec="k")); ax.text(13, -16.5, "drain Ø2", ha="center", fontsize=6)
for sy in (-1, 1):
    ax.plot([0, 0], [sy * 19.5, sy * 26], "k-", lw=1.2)
ax.text(0, -24, "M2 through tube", ha="center", fontsize=6)
for s in (-1, 1):
    ax.add_patch(Circle((s * 18.75, 0), 2.5, fc="none", ec="k", ls="--", lw=0.8))
ax.text(18.75, 4, "M2 boss\n(above)", ha="center", fontsize=6)
ax.annotate("", xy=(26, 0), xytext=(22, 0), arrowprops=dict(arrowstyle="->")); ax.text(27, 0, "lens", va="center", fontsize=7)
ax.set_xlim(-30, 32); ax.set_ylim(-28, 28); ax.set_xlabel("X (mm)"); ax.set_ylabel("Y (mm)")

# ================= C: bottom view =================
ax = axes[2]; ax.set_title("C. Bottom view (from below, X mirrored)")
ax.add_patch(Circle((0, 0), tube_od / 2, fc="#dcefff", ec="#2b6cb0"))
ax.add_patch(Circle((0, 0), base_r, fc="#c9d3dc", ec="k"))
ax.add_patch(Circle((-jack_x, 0), jack_cb / 2, fc="#e6e6e6", ec="k", lw=0.8))
ax.add_patch(Circle((-jack_x, 0), jack_hole / 2, fc="white", ec="k"))
ax.text(-jack_x, -8, "barrel jack\nØ7.5 hole\nØ10.5 x 2.2 recess", ha="center", fontsize=7)
ax.add_patch(Circle((-13, -13), 1, fc="white", ec="k")); ax.text(-13, -16.5, "drain", ha="center", fontsize=6)
ax.text(0, 18, "tube edge and base floor flush at the bottom;\nno mounting insert, plug hangs below", ha="center", fontsize=7)
ax.set_xlim(-30, 30); ax.set_ylim(-28, 28); ax.set_xlabel("X (mirrored)"); ax.set_ylabel("Y (mm)")

fig.suptitle("tubecase v2 contract sketch: everything inside the 2\" tube, base liner too (base + mid plate + cap, 3 prints)", fontsize=12)
fig.tight_layout()
fig.savefig("sketch_v2.png", dpi=150)
print("wrote sketch_v2.png")
