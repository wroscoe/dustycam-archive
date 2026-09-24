"""2D sections of the whole v3 case (front plate, ring, back plate, holder,
board with headers, USB plug envelope, the power puck's tube behind) in the
CASE frame, for sketching corrections on.  Writes review_v31/case_*.png and
review_v31/case_sections_v3.pdf (A4 landscape).  mm.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from build123d import Plane
from sections2d import section_polys, draw, dim, page, finish, FILL
import v3case as C
import v3lib as H
import puckcase_lib as P2

OUT = Path(__file__).resolve().parents[1] / "review_v31"
FILL.update({"ring": ("#c7d2e0", "#1f3350", "////"), "fplate": ("#dfe6f0", "#1f3350", "...."),
             "bplate": ("#d5dde8", "#1f3350", "xx"), "puck": ("#eeeeee", "#777777", None),
             "plug": ("#fff3e0", "#a05a00", None)})


def groups():
    g = {"fplate": [C.front_plate()], "ring": [C.ring()], "bplate": [C.back_plate()],
         "holder": [C.holder_in_case()], "board": [], "hdr": [],
         "plug": [C.place(H.usb_plug_mock())], "puck": list(P2.puck_tube().solids())}
    for b in C.board_in_case(True):
        (g["hdr"] if b.label.startswith("header") else g["board"]).append(b)
    return g


ORDER = ["puck", "plug", "board", "hdr", "bplate", "ring", "holder", "fplate"]


def cut(g, pl, u, v, ax, lw=0.8):
    for k in ORDER:
        for s in g[k]:
            draw(ax, section_polys(s, pl, u, v), k, lw)


def main():
    g = groups()
    pdf = PdfPages(OUT / "case_sections_v3.pdf")
    legend = ("blue hatch = ring · dotted = front plate · cross-hatch = back plate · dark hatch = holder\n"
              "green = XIAO stack · purple = header body/pins · orange = USB plug envelope (assumed) · grey = power puck tube")

    # 1. X = CX vertical section through the lens axis (Y up, Z to the right = toward the puck)
    pl = Plane(origin=(P2.CX, 0, 0), x_dir=(0, 0, 1), z_dir=(1, 0, 0))
    u, v = (lambda p: p.Z), (lambda p: p.Y)
    fig, ax = page("1. Vertical section at X = 23.6 (lens axis): eave, front plate, holder, board, back plate, puck",
                   "case frame; Z (front -> puck) right, Y (up) up.  " + legend)
    cut(g, pl, u, v, ax)
    dim(ax, (0, P2.OUT_H), (P2.Z_PLATE, P2.OUT_H), f"ring {P2.Z_PLATE:.2f}", 2.0, "h")
    dim(ax, (P2.Z_EAVE, P2.OUT_H), (0, P2.OUT_H), f"eave {P2.EAVE:.1f}", 5.0, "h")
    dim(ax, (P2.Z_PLATE, P2.OUT_H), (P2.Z_BACK, P2.OUT_H), f"{P2.BACK_T:.1f}", 5.0, "h")
    dim(ax, (P2.Z_BACK, P2.OUT_H), (P2.PUCK_LIP_Z1, P2.OUT_H), f"puck lip {P2.LIP_ENG:.1f}", 2.0, "h")
    dim(ax, (-14, 0), (-14, P2.OUT_H), f"{P2.OUT_H:.2f}", 0, "v")
    dim(ax, (-11, C.LENS_YC), (-11, P2.IN_Y1), f"lens -> eave root {P2.IN_Y1 - C.LENS_YC:.2f}", 0, "v")
    dim(ax, (P2.Z_BACK + 12, C.HOLDER_Y0), (P2.Z_BACK + 12, C.HOLDER_Y1), f"holder {C.HOLDER_Y1 - C.HOLDER_Y0:.2f}", 0, "v")
    ax.axhline(C.LENS_YC, color="#c00", lw=0.5, ls="--"); ax.text(-9.5, C.LENS_YC + 0.4, f"lens axis Y {C.LENS_YC:.2f}", fontsize=7, color="#c00")
    ax.text(P2.Z_PLATE / 2, 20, "cup body: USB plug, cable,\nantenna flag, cord slot below", ha="center", fontsize=7, color="#456")
    finish(fig, ax, "case_1_X_lens", pdf, (P2.Z_EAVE - 16, P2.PUCK_LIP_Z1 + 18), (-6, P2.OUT_H + 8), "Z (toward the puck)", "Y (up)", frame="case frame")

    # 2. Y = lens axis: horizontal section across the case (X right, Z down toward the puck, viewed from above)
    def cut_y(y, name, title, ylim=None):
        pl = Plane(origin=(0, y, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0))
        u, v = (lambda p: p.X), (lambda p: -p.Z)
        fig, ax = page(title, f"case frame, section at Y = {y:.2f}; X right, front (Z 0) UP, puck below.  " + legend)
        cut(g, pl, u, v, ax)
        dim(ax, (0, 2), (P2.OUT_W, 2), f"{P2.OUT_W:.2f}", 10.0, "h")
        dim(ax, (C.HOLDER_X0, 0), (C.HOLDER_X1, 0), f"holder {C.HOLDER_X1 - C.HOLDER_X0:.2f}", 4.0, "h")
        dim(ax, (C.WALL_XA[1], 0), (C.WALL_XB[0], 0), f"between walls {C.WALL_XB[0] - C.WALL_XA[1]:.2f}", 7.0, "h")
        dim(ax, (P2.OUT_W + 3, 0), (P2.OUT_W + 3, -P2.Z_PLATE), f"{P2.Z_PLATE:.2f}", 0, "v")
        dim(ax, (P2.OUT_W + 7, 0), (P2.OUT_W + 7, -C.EAR_SEAT_Z), f"ear seat {C.EAR_SEAT_Z:.2f}", 0, "v")
        finish(fig, ax, name, pdf, (-8, P2.OUT_W + 14), (-P2.PUCK_LIP_Z1 - 6, P2.EAVE + 14), "X", "-Z (front up)", frame="case frame")

    cut_y(C.LENS_YC, "case_2_Y_lens", "2. Across the case at the lens axis (Y = 56.98): walls, notches with the ears, holder, board, plate lip")
    cut_y(C.Y_B0 + 12.0, "case_3_Y_mid", "3. Across the case through the board's middle (Y = 65.45): walls, holder legs + lips, headers, plate lip")
    cut_y(C.Y_B0 + C.LEDGE_BX[0] + 0.5, "case_4_Y_ledges", "4. Across the case through the ledges (Y = 52.75): ledges under the PCB corners, USB plug envelope")

    # plans (X-Y) at several depths, viewed from the front
    def cut_z(z, name, title):
        pl = Plane(origin=(0, 0, z), x_dir=(1, 0, 0), z_dir=(0, 0, 1))
        u, v = (lambda p: p.X), (lambda p: p.Y)
        fig, ax = page(title, f"case frame, section at Z = {z:.2f}, viewed from the front; X right, Y up.  " + legend)
        cut(g, pl, u, v, ax)
        finish(fig, ax, name, pdf, (-6, P2.OUT_W + 6), (-4, P2.OUT_H + 4), "X", "Y", frame="case frame")

    cut_z(9.5, "case_5_Z_notches", "5. Plan at Z = 9.5: the ears sitting in the wall notches, front plate lip band above")
    cut_z(16.7, "case_6_Z_pcb", "6. Plan at Z = 16.7: through the PCB — holder legs, ledges under the bottom corners, walls, cup body")
    cut_z(21.0, "case_7_Z_lips", "7. Plan at Z = 21.0: through the holder lips and header bodies")
    pdf.close()
    print("wrote", OUT / "case_sections_v3.pdf")


if __name__ == "__main__":
    main()
