"""2D section drawings of the v3.1 holder + board (with headers) for
sketching corrections on.  Writes review_v31/sec_*.png (300 dpi) and a
multi-page review_v31/sections_v31.pdf (A4 landscape).  Board frame, mm.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Polygon as MplPoly
from build123d import Plane, Vector, Location
import v3lib as L

OUT = Path(__file__).resolve().parents[1] / "review_v31"
OUT.mkdir(exist_ok=True)

FILL = {"holder": ("#c7d2e0", "#1f3350", "////"), "block": ("#ffe1a8", "#7a4b00", "\\\\"),
        "board": ("#e8f5e9", "#1b5e20", None), "hdr": ("#f3e5f5", "#4a148c", None)}


def section_polys(shape, plane, u, v):
    """Section `shape` with `plane`; return list of (outer, [inners]) as 2D
    point lists using axes u, v (functions Vector->float)."""
    res = shape.intersect(plane)
    if res is None:
        return []
    faces = res.faces() if hasattr(res, "faces") else []
    out = []
    for f in faces:
        def wire_pts(w):
            pts = []
            for e in w.edges():
                n = 24 if e.geom_type != "LINE" else 2
                for i in range(n):
                    p = e.position_at(i / (n - 1))
                    pts.append((u(p), v(p)))
            return pts
        out.append((wire_pts(f.outer_wire()), [wire_pts(w) for w in f.inner_wires()]))
    return out


def draw(ax, polys, kind, lw=1.0):
    fc, ec, hatch = FILL[kind]
    for outer, inners in polys:
        ax.add_patch(MplPoly(outer, closed=True, facecolor=fc, edgecolor=ec, lw=lw, hatch=hatch, zorder=2))
        for inn in inners:
            ax.add_patch(MplPoly(inn, closed=True, facecolor="white", edgecolor=ec, lw=lw, zorder=3))


def dim(ax, p0, p1, text, off=1.2, side="v", fs=7):
    """Simple dimension: line between p0,p1 offset perpendicular, label."""
    (x0, y0), (x1, y1) = p0, p1
    if side == "h":   # horizontal measurement, offset in y
        y = y0 + off
        ax.annotate("", (x0, y), (x1, y), arrowprops=dict(arrowstyle="<->", lw=0.6, color="k"))
        ax.plot([x0, x0], [y0, y], "k-", lw=0.4); ax.plot([x1, x1], [y1, y], "k-", lw=0.4)
        ax.text((x0 + x1) / 2, y + 0.25, text, ha="center", va="bottom", fontsize=fs)
    else:             # vertical measurement, offset in x
        x = x0 + off
        ax.annotate("", (x, y0), (x, y1), arrowprops=dict(arrowstyle="<->", lw=0.6, color="k"))
        ax.plot([x0, x], [y0, y0], "k-", lw=0.4); ax.plot([x1, x], [y1, y1], "k-", lw=0.4)
        ax.text(x + 0.25, (y0 + y1) / 2, text, ha="left", va="center", fontsize=fs, rotation=90)


def page(title, subtitle):
    fig, ax = plt.subplots(figsize=(11.69, 8.27))   # A4 landscape
    ax.set_aspect("equal"); ax.grid(True, lw=0.25, color="#bbbbbb", zorder=0)
    ax.set_axisbelow(True)
    fig.suptitle(title, fontsize=12, x=0.02, ha="left")
    ax.set_title(subtitle, fontsize=8, loc="left")
    return fig, ax


def finish(fig, ax, name, pdf, xlim, ylim, xlabel, ylabel, frame="board frame", out=None):
    ax.set_xlim(*xlim); ax.set_ylim(*ylim)
    ax.set_xlabel(xlabel + f"  [mm, {frame}]", fontsize=8); ax.set_ylabel(ylabel, fontsize=8)
    ax.tick_params(labelsize=7)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig((out or OUT) / f"{name}.png", dpi=300); pdf.savefig(fig); plt.close(fig)


def main():
    holder = L.holder()
    mocks = L.board_mocks(headers=True)
    hdr = {k: v for k, v in mocks.items() if k.startswith("header")}
    brd = {k: v for k, v in mocks.items() if not k.startswith("header")}

    pdf = PdfPages(OUT / "sections_v31.pdf")

    # ---- A. cross-section across the channel at x = 5 (looking along +x)
    def cut_x(x, name, title):
        pl = Plane(origin=(x, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
        u, v = (lambda p: p.Y), (lambda p: p.Z)
        fig, ax = page(title, f"section at board x = {x}; viewed along +x (from the open end); y right, z (lens) up")
        for k, s in brd.items(): draw(ax, section_polys(s, pl, u, v), "board", 0.6)
        for k, s in hdr.items(): draw(ax, section_polys(s, pl, u, v), "hdr", 0.6)
        draw(ax, section_polys(holder, pl, u, v), "holder")
        # dims
        lz0, lz1 = L.lip_z("header")
        dim(ax, (L.OUT_Y0, L.FACE_Z1), (L.OUT_Y1, L.FACE_Z1), f"{L.OUT_Y1-L.OUT_Y0:.2f} outer (legs {L.LEG_T})", 1.0, "h")
        dim(ax, (L.CH_Y0, L.FACE_Z0), (L.CH_Y1, L.FACE_Z0), f"{L.CH_Y1-L.CH_Y0:.2f} channel (PCB 17.78 + 2x0.15)", -2.0, "h")
        dim(ax, (L.CH_Y0, lz0), (L.LIP_IN, lz0), f"lip {L.LIP_IN-L.CH_Y0:.2f} in", -1.2, "h")
        dim(ax, (L.OUT_Y1 + L.EAR_OUT, lz0), (L.OUT_Y1 + L.EAR_OUT, L.FACE_Z1), f"{L.FACE_Z1-lz0:.2f} deep", 1.5, "v")
        dim(ax, (L.OUT_Y1 + L.EAR_OUT, L.EAR_Z0), (L.OUT_Y1 + L.EAR_OUT, L.EAR_Z1), f"ear {L.EAR_Z1-L.EAR_Z0:.2f}", 4.5, "v")
        dim(ax, (L.OUT_Y0, 0), (L.OUT_Y0, L.FACE_Z0), f"PCB back -> face inner {L.FACE_Z0:.2f}", -4.5, "v")
        dim(ax, (L.OUT_Y0, lz1), (L.OUT_Y0, 0), f"lip {abs(lz1):.2f} below PCB (0.15 under header)", -7.0, "v")
        ax.text(L.CAM_Y, L.FACE_Z1 + 3.2, f"keyhole {L.KEY_W:.2f} / barrel {L.LENS_D}", ha="center", fontsize=7)
        ax.text(L.OUT_Y0 - 0.6, -9.0, "purple = header body + pins (optional board, flush with the PCB edge)\ngreen = XIAO stack", ha="left", va="top", fontsize=6, color="#4a148c")
        finish(fig, ax, name, pdf, (L.OUT_Y0 - 9, L.OUT_Y1 + 9), (L.HDR_PIN_Z0 - 3, L.FACE_Z1 + 6), "y (across the board)", "z (lens direction)")

    cut_x(5.0, "sec_A_across_x5", "A. Across the channel through the sensor plate and grip ribs (x = 5)")
    cut_x(12.0, "sec_A2_across_x12", "A2. Across the channel through the SD socket / flex (x = 12)")

    # ---- B. longitudinal section along the lens axis, y = 8.25 (looking along -y)
    def cut_y(y, name, title, extra=None):
        pl = Plane(origin=(0, y, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0))
        u, v = (lambda p: p.X), (lambda p: p.Z)
        fig, ax = page(title, f"section at board y = {y}; x (USB end -> far end) right, z (lens) up")
        for k, s in brd.items(): draw(ax, section_polys(s, pl, u, v), "board", 0.6)
        for k, s in hdr.items(): draw(ax, section_polys(s, pl, u, v), "hdr", 0.6)
        draw(ax, section_polys(holder, pl, u, v), "holder")
        lz0, lz1 = L.lip_z("header")
        dim(ax, (L.X_FACE0, L.FACE_Z1), (L.X1, L.FACE_Z1), f"{L.X1-L.X_FACE0:.2f} overall", 1.0, "h")
        dim(ax, (L.X_LEG0, lz0), (L.X_END0, lz0), f"legs / lips {L.X_END0-L.X_LEG0:.2f}", -1.5, "h")
        dim(ax, (L.X1, lz0), (L.X1, L.FACE_Z1), f"{L.FACE_Z1-lz0:.2f}", 1.5, "v")
        dim(ax, (L.X1, 0), (L.X1, L.FACE_Z0), f"{L.FACE_Z0:.2f}", 4.0, "v")
        dim(ax, (L.X_END0, L.FACE_Z1), (L.X1, L.FACE_Z1), f"end {L.END_T}", 3.0, "h")
        if extra: extra(ax)
        finish(fig, ax, name, pdf, (L.X_FACE0 - 8, L.X1 + 8), (L.HDR_PIN_Z0 - 3, L.LENS_Z1 + 5), "x (along the board)", "z (lens direction)")

    def lens_notes(ax):
        ax.text(L.CAM_X, L.LENS_Z1 + 0.6, f"lens tip z {L.LENS_Z1}\nface outer z {L.FACE_Z1}", ha="center", fontsize=7)
        ax.text(L.EXP_X1 - 1.2, 9.2, f"{L.END_CLR} to end wall", fontsize=6, rotation=90, va="bottom")
    cut_y(L.CAM_Y, "sec_B_lens_axis", "B. Along the lens axis (y = 8.25): face, keyhole, sensor plate", lens_notes)
    cut_y(0.40, "sec_C_header_lane", "C. Along the header strip (y = 0.4): leg, ribs, header body, lip under it")
    cut_y(-2.0, "sec_D_leg_ear", "D. Through the -y leg (y = -2.0): coax window, ear")

    # ---- E. plan from the back at z = -5 (looking along +z ... i.e. from behind)
    def cut_z(z, name, title, mirror=True):
        pl = Plane(origin=(0, 0, z), x_dir=(1, 0, 0), z_dir=(0, 0, 1))
        u, v = (lambda p: p.X), (lambda p: p.Y)
        fig, ax = page(title, f"section at board z = {z}; x right, y up; viewed from the lens side (+z)")
        for k, s in brd.items(): draw(ax, section_polys(s, pl, u, v), "board", 0.6)
        for k, s in hdr.items(): draw(ax, section_polys(s, pl, u, v), "hdr", 0.6)
        draw(ax, section_polys(holder, pl, u, v), "holder")
        finish(fig, ax, name, pdf, (L.X_FACE0 - 6, L.X1 + 6), (L.OUT_Y0 - L.EAR_OUT - 5, L.OUT_Y1 + L.EAR_OUT + 5), "x (along the board)", "y (across the board)")

    cut_z(-3.2, "sec_E_plan_lips", "E. Plan through the lips (z = -3.2): lips under the header strips, pins between")
    cut_z(0.8, "sec_F_plan_pcb", "F. Plan through the PCB (z = 0.8): channel, grip ribs, end wall")
    cut_z(11.0, "sec_G_plan_face", "G. Plan through the front face (z = 11): keyhole, ears")
    cut_z(9.0, "sec_H_plan_head", "H. Plan just under the face (z = 9): sensor plate, card, flex, coax window")
    pdf.close()
    print("wrote", OUT / "sections_v31.pdf")


if __name__ == "__main__":
    main()
