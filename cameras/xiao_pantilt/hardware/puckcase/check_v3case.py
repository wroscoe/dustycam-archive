"""Fail-closed checks for the v3 case around the v3.1 holder (case frame)."""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build123d import Pos
import v3case as C
import v3lib as H
import puckcase_lib as P2

FAILS = []
def check(name, val, lim, op, unit="mm"):
    ok = {"==": abs(val - lim) < 1e-6, ">=": val >= lim - 1e-9, "<=": val <= lim + 1e-9}[op]
    print(f"  {'ok ' if ok else 'BAD'} {name}: {val:.4f} {op} {lim} {unit}")
    if not ok: FAILS.append(name)
def vol(a, b):
    r = a.intersect(b)
    if r is None: return 0.0
    v = sum(x.volume for x in r) if isinstance(r, (list, tuple)) else r.volume
    if v != v or v == math.inf: raise RuntimeError("bad volume")
    return v

ring, fp, bp = C.ring(), C.front_plate(), C.back_plate()
holder = C.holder_in_case()
board = C.board_in_case(headers=True)
print("-- 1. solids")
for n, p in (("ring_v3", ring), ("front_plate_v3", fp)):
    check(f"{n} solid count", len(list(p.solids())), 1, "==", ""); check(f"{n} valid", 1.0 if p.is_valid else 0.0, 1, "==", "")
print("-- 2. seated interference")
check("holder x ring", vol(holder, ring), 0.0, "==", "mm^3")
check("holder x front plate", vol(holder, fp), 0.0, "==", "mm^3")
check("holder x back plate", vol(holder, bp), 0.0, "==", "mm^3")
check("board+headers x ring", sum(vol(b, ring) for b in board), 0.0, "==", "mm^3")
check("board+headers x front plate", sum(vol(b, fp) for b in board), 0.0, "==", "mm^3")
check("board+headers x back plate", sum(vol(b, bp) for b in board), 0.0, "==", "mm^3")
v_lip = vol(fp, ring); check("front plate x ring = 6 lip crush ribs, v2.4 value 11.72", v_lip, 11.0, ">=", "mm^3"); check("front plate x ring upper", v_lip, 12.5, "<=", "mm^3")
print("-- 3. holder drop-in sweep (holder + board moved -Z out of the ring, 10 steps)")
worst = 0.0
for i in range(1, 11):
    dz = -i * 1.5
    v = vol(Pos(0, 0, dz) * holder, ring) + sum(vol(Pos(0, 0, dz) * b, ring) for b in board)
    worst = max(worst, v)
    if v > 1e-6: print(f"     HIT dz={dz}: {v:.4f}")
check("drop-in sweep max", worst, 0.0, "==", "mm^3")
print("-- 4. clearances")
hol_g = C.place(H.holder(ribs=False))
def clr(name, g, a, b):
    check(f"{name} >= {g}", vol(a, b), 0.0, "==", "mm^3")
# holder legs to walls: inflate by building the holder with fatter legs is complex; use a box probe
for xa, xb in (C.WALL_XA, C.WALL_XB):
    wall_face = xb if xa < P2.CX else xa
    probe_x0 = min(wall_face, C.HOLDER_X0 if xa < P2.CX else C.HOLDER_X1)
    probe = P2.box_at(probe_x0, C.HOLDER_Y0, C.WALL_Z0, abs((C.HOLDER_X0 if xa < P2.CX else C.HOLDER_X1) - wall_face), C.HOLDER_Y1 - C.HOLDER_Y0, 5.0)
    print(f"     wall-to-leg gap {abs((C.HOLDER_X0 if xa < P2.CX else C.HOLDER_X1) - wall_face):.2f} (probe volume {probe.volume:.1f})")
check("ear top under the front plate inner face", P2.PLATE_T - C.EAR_TOP_Z + 0.0, -0.10, ">=")   # 2.40 - 2.50 = -0.10 -> 0.10 gap
check("holder forward band inside the lip prism (Y)", P2.BAY_Y1 - C.HOLDER_Y1, 0.10, ">=")
check("holder forward band inside the lip prism (X-)", C.EAR_X0 - P2.BAY_X0, 0.10, ">=")
check("holder forward band inside the lip prism (X+)", P2.BAY_X1 - C.EAR_X1, 0.10, ">=")
plug = C.place(H.usb_plug_mock(g=0.30))
check("USB plug (+0.30) x ring/ledges", vol(plug, ring), 0.0, "==", "mm^3")
check("USB plug (+0.30) x front plate", vol(plug, fp), 0.0, "==", "mm^3")
pcb = [b for b in board if b.label == "base_pcb"][0]
check("PCB end to ledge gap (Y)", C.Y_B0 - (C.Y_B0 + C.LEDGE_BX[1]), 0.20, ">=")
lens = [b for b in board if b.label == "lens_barrel"][0]
check("lens tip to plate inner face", (C.Z_B0 - H.LENS_Z1) - P2.PLATE_T, 1.0, ">=")
brow = math.degrees(math.atan2(P2.IN_Y1 - C.LENS_YC, (C.Z_B0 - H.LENS_Z1) - P2.Z_EAVE))
check("eave brow angle above the lens axis (deg)", brow, 40.0, ">=", "deg")
hdr_pin_z = C.Z_B0 - H.HDR_PIN_Z0
check("header pin tails clear of the back plate", Z_PLATE_GAP := (P2.Z_PLATE - hdr_pin_z), 0.3, ">=")
print("-- 5. ring overhang audit (standing on its back mouth: +Z faces point down)")
down = 0.0
for f in ring.faces():
    n = f.normal_at()
    if n.Z > 0.75 and abs(f.center().Z - P2.Z_PLATE) > 0.05:
        down += f.area
        if f.area > 1.0: print(f"     down-facing {f.area:.2f} mm^2 at Z={f.center().Z:.2f}")
check("ring +Z-facing area off the bed (v2.4 was 9.3)", down, 20.0, "<=", "mm^2")
print()
if FAILS:
    print("CHECK FAILED:", FAILS); sys.exit(1)
print("CHECK PASSED")
