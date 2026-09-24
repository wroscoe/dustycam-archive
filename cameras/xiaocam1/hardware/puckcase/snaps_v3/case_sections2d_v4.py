"""2D sections of the v4 case (front cup, holder with rail, back plate, board, plug, puck) — case frame."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from build123d import Plane, Pos
from sections2d import section_polys, draw, dim, page, finish, FILL
import v4case as C
import v3lib as H
import puckcase_lib as P2

OUT = Path(__file__).resolve().parents[1] / "review_v4"
OUT.mkdir(exist_ok=True)
FILL.update({"cup": ("#c7d2e0", "#1f3350", "////"), "bplate": ("#d5dde8", "#1f3350", "xx"),
             "puck": ("#eeeeee", "#777777", None), "plug": ("#fff3e0", "#a05a00", None),
             "cam": ("#ffd9d9", "#a00000", None)})
ORDER = ["puck", "plug", "board", "hdr", "cam", "bplate", "cup", "holder"]


def groups():
    tube = [Pos(0, 0, C.Z_BACK - P2.Z_BACK) * s for s in P2.puck_tube().solids()]
    g = {"cup": [C.front_cup()], "bplate": [C.back_plate()], "holder": [C.holder_in_case()],
         "board": [], "hdr": [], "cam": C.camera_in_case(),
         "plug": [C.place(H.usb_plug_mock())], "puck": tube}
    for b in C.board_in_case(True):
        (g["hdr"] if b.label.startswith("header") else g["board"]).append(b)
    return g


def cut(g, pl, u, v, ax):
    for k in ORDER:
        for s in g[k]:
            draw(ax, section_polys(s, pl, u, v), k, 0.8)


def main():
    g = groups()
    pdf = PdfPages(OUT / "case_sections_v4.pdf")
    legend = ("blue hatch = front cup · cross-hatch = back plate · dark hatch = holder · green = XIAO stack\n"
              "purple = header body/pins · RED = camera module GLUED to the holder plate · orange = USB plug · grey = puck tube")
    # 1. X = CX
    pl = Plane(origin=(P2.CX, 0, 0), x_dir=(0, 0, 1), z_dir=(1, 0, 0)); u, v = (lambda p: p.Z), (lambda p: p.Y)
    fig, ax = page("1. Vertical section at X = 23.6 (lens axis): front cup, glue plate with the module on its front face, dovetail boss, back plate, puck",
                   "case frame; Z (front -> puck) right, Y up.  " + legend)
    cut(g, pl, u, v, ax)
    dim(ax, (0, P2.OUT_H), (C.Z_MOUTH, P2.OUT_H), f"front cup {C.Z_MOUTH:.1f}", 2.0, "h")
    dim(ax, (C.Z_REB0, P2.OUT_H), (C.Z_MOUTH, P2.OUT_H), f"rebate {C.REB_D:.1f}", 5.0, "h")
    dim(ax, (C.Z_BACK, P2.OUT_H), (C.PUCK_LIP_Z1, P2.OUT_H), f"puck lip {P2.LIP_ENG:.1f}", 2.0, "h")
    dim(ax, (-10, C.LENS_YC), (-10, P2.OUT_H), f"lens -> top {P2.OUT_H - C.LENS_YC:.2f}", 0, "v")
    dim(ax, (C.PUCK_LIP_Z1 + 8, C.HOLDER_Y0), (C.PUCK_LIP_Z1 + 8, C.HOLDER_Y1), f"holder {C.HOLDER_Y1 - C.HOLDER_Y0:.2f}", 0, "v")
    dim(ax, (C.PUCK_LIP_Z1 + 12, C.Y_TOP_IN), (C.PUCK_LIP_Z1 + 12, P2.OUT_H), f"top wall + boss {P2.OUT_H - C.Y_TOP_IN:.1f}", 0, "v")
    ax.axhline(C.LENS_YC, color="#c00", lw=0.5, ls="--"); ax.text(-8, C.LENS_YC + 0.4, f"lens axis Y {C.LENS_YC:.2f}", fontsize=7, color="#c00")
    finish(fig, ax, "case4_1_X_lens", pdf, (-14, C.PUCK_LIP_Z1 + 18), (-6, P2.OUT_H + 8), "Z (toward the puck)", "Y (up)", frame="case frame", out=OUT)

    def cut_y(y, name, title):
        pl = Plane(origin=(0, y, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0)); u, v = (lambda p: p.X), (lambda p: -p.Z)
        fig, ax = page(title, f"case frame, section at Y = {y:.2f}; X right, front (Z 0) UP, puck below.  " + legend)
        cut(g, pl, u, v, ax)
        dim(ax, (0, 2), (P2.OUT_W, 2), f"{P2.OUT_W:.2f}", 6.0, "h")
        dim(ax, (P2.OUT_W + 3, 0), (P2.OUT_W + 3, -C.Z_MOUTH), f"{C.Z_MOUTH:.1f}", 0, "v")
        finish(fig, ax, name, pdf, (-8, P2.OUT_W + 12), (-C.PUCK_LIP_Z1 - 6, 12), "X", "-Z (front up)", frame="case frame", out=OUT)
    cut_y(C.LENS_YC, "case4_2_Y_lens", "2. Across at the lens axis: the GLUE PLATE, the module glued to its front face, lens in the hole")
    cut_y(C.Y_B0 + 12.0, "case4_3_Y_mid", "3. Across at mid-board (Y = 64.8): legs, lips, headers, back plate in the rebate")
    cut_y(C.Y_TOP_IN + 1.0, "case4_4_Y_slot", "4. Across through the dovetail (Y = 77.4): rail in the slot, crush ribs on the flanks")
    cut_y(C.Y_B0 - 0.7, "case4_5_Y_end", "5. Across just past the PCB end: clear inner face (posts removed), USB plug envelope")

    def cut_z(z, name, title):
        pl = Plane(origin=(0, 0, z), x_dir=(1, 0, 0), z_dir=(0, 0, 1)); u, v = (lambda p: p.X), (lambda p: p.Y)
        fig, ax = page(title, f"case frame, section at Z = {z:.2f}, viewed from the front; X right, Y up.  " + legend)
        cut(g, pl, u, v, ax)
        finish(fig, ax, name, pdf, (-6, P2.OUT_W + 6), (-4, P2.OUT_H + 4), "X", "Y", frame="case frame", out=OUT)
    cut_z(C.HEAD_Z0C + 1.0, "case4_6_Z_head", "6. Plan through the glued camera head: 8.3 module standing clear inside the cup, slot boss")
    cut_z(C.HOLDER_FACE_Z + 0.8, "case4_7_Z_plate", "7. Plan through the glue plate: solid plate at the camera end, open middle for the flex, rail in the slot")
    cut_z(C.Z_B0 + 0.6, "case4_8_Z_pcb", "8. Plan through the PCB: legs and grip ribs, rail in the slot, empty cup body")
    cut_z(C.Z_REB0 + 1.5, "case4_9_Z_rebate", "9. Plan through the rebate: back plate, edge crush ribs, cord slot below")
    pdf.close()
    print("wrote", OUT / "case_sections_v4.pdf")


if __name__ == "__main__":
    main()
