"""Fail-closed checks for the v3.1 holder (DESIGN_v3.md §14), both variants.

Every group must run and pass for CHECK PASSED; an exception anywhere fails
the run (never mapped to 0).  Board frame throughout.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build123d import Pos   # noqa: E402

import v3lib as L           # noqa: E402

FAILS = []
GROUPS_RUN = set()


def note(g):
    GROUPS_RUN.add(g)


def check(name, val, lim, op, unit="mm"):
    ok = {"==": abs(val - lim) < 1e-6, ">=": val >= lim - 1e-9, "<=": val <= lim + 1e-9}[op]
    print(f"  {'ok ' if ok else 'BAD'} {name}: {val:.4f} {op} {lim} {unit}")
    if not ok:
        FAILS.append(name)


def vol(a, b):
    r = a.intersect(b)
    if r is None:
        return 0.0
    v = sum(x.volume for x in r) if isinstance(r, (list, tuple)) else r.volume
    if v != v or v == math.inf:
        raise RuntimeError(f"bad volume {v}")
    return v


def moved(shape, dx):
    return Pos(dx, 0, 0) * shape


def run_variant(variant, boards):
    tag = f"[{variant}]"
    holder = L.holder(lip_under=variant)
    bare = L.holder(lip_under=variant, ribs=False)
    ribs = list((holder - bare).solids())
    lz0, lz1 = L.lip_z(variant)

    print(f"-- 1{tag} solid and bounds")
    check(f"{tag} solid count", len(list(holder.solids())), 1, "==", "")
    check(f"{tag} valid", 1.0 if holder.is_valid else 0.0, 1, "==", "")
    bb = holder.bounding_box()
    exp = ((-1.0, L.OUT_Y0 - L.EAR_OUT, lz0), (L.X1, L.OUT_Y1 + L.EAR_OUT, L.EAR_Z1))
    for ax, lo, hi in zip("xyz", exp[0], exp[1]):
        check(f"{tag} bound {ax} min", getattr(bb.min, ax.upper()), lo, "==")
        check(f"{tag} bound {ax} max", getattr(bb.max, ax.upper()), hi, "==")
    print(f"     volume {holder.volume:.0f} mm^3, depth {L.FACE_Z1 - lz0:.2f}, width {L.OUT_Y1 - L.OUT_Y0:.2f}")
    note(1)

    print(f"-- 2{tag} board insertion sweep (rib-less holder; ribs reported apart)")
    worst = 0.0
    for hdr in boards:
        mocks = L.board_mocks(headers=hdr)
        for dx in [-26 + 2 * i for i in range(14)]:
            for k, s in mocks.items():
                v = vol(moved(s, dx), bare)
                worst = max(worst, v)
                if v > 1e-6:
                    print(f"     HIT headers={hdr} dx={dx} {k}: {v:.4f}")
    check(f"{tag} board stack x holder over the sweep, max", worst, 0.0, "==", "mm^3")
    seated = L.board_mocks(headers=boards[-1])
    v_rib = sum(vol(seated["base_pcb"], r) for r in ribs)
    check(f"{tag} grip ribs x PCB, seated (0.10 crush x 4)", v_rib, 0.30, ">=", "mm^3")
    check(f"{tag} grip ribs x PCB, seated, upper", v_rib, 1.20, "<=", "mm^3")
    v_other = sum(vol(s, r) for k, s in seated.items() if k != "base_pcb" for r in ribs)
    check(f"{tag} grip ribs x everything else", v_other, 0.0, "==", "mm^3")
    note(2)

    print(f"-- 3{tag} clearances (mock inflated by g must not touch)")
    def clear(name, key, g, hdr):
        m = L.board_mocks(headers=hdr)[key] if g == 0 else L.board_mocks(headers=hdr, inflate=g)[key]
        check(f"{tag} {name} >= {g}", vol(m, holder), 0.0, "==", "mm^3")
    clear("sensor plate to face", "sensor_plate", L.HEAD_SLIDE_CLR - 0.01, False)
    clear("lens barrel in keyhole", "lens_barrel", L.LENS_CLR - 0.01, False)
    clear("expansion PCB to end wall", "expansion_pcb", L.END_CLR - 0.01, False)
    clear("USB shell to holder", "usb_c_shell", 0.50, False)
    clear("card to holder", "microsd_card", 0.50, False)
    clear("fpc roll to face", "camera_fpc_roll", 0.50, False)
    clear("ufl jack to leg", "ufl_jack", 0.30, False)
    clear("buttons to leg (rst)", "button_rst", 0.30, False)
    if True in boards:
        clear("header body 0 to lip/leg", "header_body_0", L.LIP_CLR - 0.01, True)
        clear("header body 1 to lip/leg", "header_body_1", L.LIP_CLR - 0.01, True)
        pins = [s for k, s in L.board_mocks(headers=True, inflate=L.PIN_CLR - 0.01).items() if k.startswith("header_pin")]
        check(f"{tag} header pins (+{L.PIN_CLR - 0.01:.2f}) x holder", sum(vol(p, holder) for p in pins), 0.0, "==", "mm^3")
    plug = L.usb_plug_mock(g=0.30)
    check(f"{tag} USB plug overmold (+0.30) x holder", vol(plug, holder), 0.0, "==", "mm^3")
    note(3)

    print(f"-- 4{tag} lens datum and retention")
    slab = L.box_at(L.CAM_X - L.HEAD_SQ / 2, L.CAM_Y - L.HEAD_SQ / 2, L.FACE_Z0,
                    L.CAM_X + L.HEAD_SQ / 2, L.CAM_Y + L.HEAD_SQ / 2, L.FACE_Z0 + 0.10)
    check(f"{tag} sensor plate bearing area on the face", vol(slab, holder) / 0.10, 6.0, ">=", "mm^2")
    check(f"{tag} lens top proud of the face outer", L.LENS_Z1 - L.FACE_Z1, 1.0, ">=")
    check(f"{tag} lip reach under the header strip", L.LIP_IN, 0.5, ">=")
    z_play_hdr = L.HDR_BZ[0] - lz1
    z_play_pcb = 0.0 - lz1
    print(f"     z play: header board {z_play_hdr:.2f}, bare board {z_play_pcb:.2f} (ribs grip the PCB edge)")
    print("     +x: end wall | +/-y: legs + ribs | +z: face on the sensor plate | -z: lips"
          " | -x: NONE on the holder — ring ledge / friction")
    note(4)

    print(f"-- 5{tag} overhangs, standing on the end wall")
    hp = L.holder_print_oriented(holder)
    down = 0.0
    for f in hp.faces():
        if f.normal_at().Z < -0.75 and f.center().Z > 0.05:
            down += f.area
            print(f"     down-facing {f.area:.2f} mm^2 at z={f.center().Z:.2f}")
    check(f"{tag} faces steeper than 45 deg facing the bed, off the bed", down, 0.0, "==", "mm^2")
    note(5)


def main():
    run_variant("header", [False, True])
    run_variant("pcb", [False])
    print()
    if FAILS or GROUPS_RUN != set(range(1, 6)):
        print("CHECK FAILED:", FAILS, "groups run:", sorted(GROUPS_RUN))
        sys.exit(1)
    print("CHECK PASSED")


if __name__ == "__main__":
    main()
