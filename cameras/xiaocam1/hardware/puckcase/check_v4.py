"""Fail-closed checks for puckcase v4: front cup, holder with rail, back plate (case frame)."""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build123d import Pos
import v4case as C
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
def overhang(part, bed_z, up=+1):
    """Area of faces steeper than 45 deg facing the bed, off the bed. up=+1: print Z = model Z."""
    tot = 0.0
    for f in part.faces():
        n = f.normal_at().Z * up
        if n < -0.75 and abs(f.center().Z - bed_z) > 0.05:
            tot += f.area
            if f.area > 1.0: print(f"     down-facing {f.area:.2f} mm^2 at Z={f.center().Z:.2f}")
    return tot

cup, bp = C.front_cup(), C.back_plate()
holder = C.holder_in_case()
holder_bare = C.place(H.holder(ribs=False, **C.HOLDER_KW))
board = C.board_in_case(headers=True)
cam = C.camera_in_case()          # module glued to the holder's plate: rides with the holder
print("-- 1. solids")
for n, p in (("front_cup", cup), ("back_plate_v4", bp), ("holder_v4", holder)):
    check(f"{n} solid count", len(list(p.solids())), 1, "==", ""); check(f"{n} valid", 1.0 if p.is_valid else 0.0, 1, "==", "")
    print(f"     {n} volume {p.volume:.0f} mm^3")
print("-- 2. seated interference")
cup_noribs = cup - C._slot_ribs()
check("holder x cup (without the slot ribs)", vol(holder, cup_noribs), 0.0, "==", "mm^3")
check("holder x back plate", vol(holder, bp), 0.0, "==", "mm^3")
check("board+headers x cup", sum(vol(b, cup) for b in board), 0.0, "==", "mm^3")
check("board+headers x back plate", sum(vol(b, bp) for b in board), 0.0, "==", "mm^3")
v_lip = vol(bp, cup); check("back plate x cup = 6 edge crush ribs", v_lip, 3.0, ">="); check("back plate x cup upper", v_lip, 14.0, "<=")
cup_bare = C.front_cup()   # ribs are part of the cup; measure rail crush as holder x (slot ribs only)
ribs = C._slot_ribs(); v_rail = vol(holder, ribs); print(f"     holder x slot ribs {v_rail:.4f} mm^3 (4 ribs, 0.10 crush)")
check("rail x slot ribs, seated (crush)", v_rail, 0.10, ">="); check("rail x slot ribs upper", v_rail, 3.0, "<=")
print("-- 3. holder slide-in along the slot (holder + board moved +Z out of the cup, 12 steps)")
worst = 0.0
for i in range(1, 13):
    dz = i * 1.5
    v = (vol(Pos(0, 0, dz) * holder, cup_noribs)
         + sum(vol(Pos(0, 0, dz) * b, cup_noribs) for b in board + cam))
    worst = max(worst, v)
    if v > 1e-6: print(f"     HIT dz={dz}: {v:.4f}")
check("slide-in sweep max", worst, 0.0, "==", "mm^3")
print("-- 4. back plate press-on sweep (plate moved +Z, 6 steps)")
worst = 0.0
for i in range(1, 7):
    dz = i * 1.5
    p = Pos(0, 0, dz) * bp
    v = vol(p, holder) + sum(vol(p, b) for b in board)
    worst = max(worst, v)
    if v > 1e-6: print(f"     HIT dz={dz}: {v:.4f}")
check("press-on sweep: plate x holder/board max", worst, 0.0, "==", "mm^3")
print("-- 5. clearances and geometry")
check("rail top to slot bottom", (C.Y_TOP_IN + C.SLOT_D) - (C.Y_B0 + H.X1 + H.RAIL_H), 0.30, ">=")
check("rail flank clearance (per side)", (C.SLOT_W0 - H.RAIL_W0) / 2, 0.15, ">=")
check("holder end wall to boss face", C.Y_TOP_IN - (C.Y_B0 + H.X1), 0.15, ">=")
check("slot/boss end before the rebate", C.Z_REB0 - C.SLOT_Z1, 0.30, ">=")
check("holder back to the back plate", C.Z_REB0 - C.HOLDER_Z1, 1.0, ">=")
check("lens tip inside the hole (behind the outer face)", C.LENS_TIP_Z, 0.30, ">=")
print("-- 5b. camera glued to the holder's plate (no keyhole, no dip)")
plate = C.place(H.box_at(H.PLATE_X0, H.OUT_Y0, H.FACE_Z0, H.PLATE_X1, H.OUT_Y1, H.FACE_Z1))
check("glue plate is solid over the head (head x plate)", sum(vol(c, plate) for c in cam), 0.0, "==", "mm^3")
check("glue area under the head", H.HEAD_SQ ** 2, 60.0, ">=", "mm^2")
check("plate margin around the head (-x)", (H.CAM_X - H.HEAD_SQ / 2) - H.PLATE_X0, 0.5, ">=")
check("plate margin around the head (+x)", H.PLATE_X1 - (H.CAM_X + H.HEAD_SQ / 2), 0.5, ">=")
check("head sits in FRONT of the plate (glued back face)", H.HEAD_G_Z0 - H.FACE_Z1, 0.0, "==")
check("head clear of the cup's inner front face", C.HEAD_Z0C - C.FACE_T, 0.50, ">=")
check("glued camera x cup", sum(vol(c, cup) for c in cam), 0.0, "==", "mm^3")
check("glued camera x board", sum(vol(c, b) for c in cam for b in board), 0.0, "==", "mm^3")
check("rail bottoms on the slot's closed end (depth stop)", C.SLOT_Z0 - C.HOLDER_FACE_Z, 0.0, "==")
print("-- 5c. board slides in under the plate (board moved -x in the board frame, 10 steps)")
worst = 0.0
for i in range(1, 11):
    dy = -i * 2.5      # board -x -> case -Y
    v = (sum(vol(Pos(0, dy, 0) * b, holder_bare) for b in board)
         + sum(vol(Pos(0, dy, 0) * b, c) for b in board for c in cam))
    worst = max(worst, v)
    if v > 1e-6: print(f"     HIT dx={-dy}: {v:.4f}")
check("board insertion sweep x holder (no ribs) + camera", worst, 0.0, "==", "mm^3")
plug = C.place(H.usb_plug_mock(g=0.30))
check("USB plug (+0.30) x cup (walls)", vol(plug, cup), 0.0, "==", "mm^3")
check("USB plug (+0.30) x back plate", vol(plug, bp), 0.0, "==", "mm^3")
check("header pin tails to the back plate", C.Z_MOUTH - C.PIN_Z1, 0.50, ">=")
hdr_inf = [C.place(s) for k, s in H.board_mocks(headers=True, inflate=0.3).items() if k.startswith("header")]
check("headers (+0.30) x cup/back plate", sum(vol(h, cup) + vol(h, bp) for h in hdr_inf), 0.0, "==", "mm^3")
card = [b for b in board if b.label == "microsd_card"][0]
check("card x cup", vol(card, cup), 0.0, "==", "mm^3")
brow = math.degrees(math.atan2(P2.IN_Y1 - C.LENS_YC, C.LENS_TIP_Z))
print(f"     lens at Y {C.LENS_YC:.2f}; no eave now (lens tip {C.LENS_TIP_Z:.2f} inside the hole)")
print("-- 6. overhang audits")
check("front cup face-down (+Z faces off the bed)", overhang(cup, 0.0, up=+1), 12.0, "<=", "mm^2")
hp = H.holder_print_oriented(**C.HOLDER_KW)
check("holder face-down", overhang(hp, 0.0, up=+1), 2.0, "<=", "mm^2")
bpp = Pos(0, 0, -C.Z_REB0) * bp
check("back plate front-face-down", overhang(bpp, 0.0, up=+1), 12.0, "<=", "mm^2")
print("-- 7. grip rib variants (board retention is the ribs alone; the posts are gone)")
pcb = [b for b in H.board_mocks(headers=False).values() if b.label == "base_pcb"][0]
for name, want in (("std", 0.10), ("fine", 0.05), ("firm", 0.17)):
    kw = dict(C.HOLDER_KW, ribs=name)
    h = H.holder(**kw)
    check(f"{name}: solid count", len(h.solids()), 1, "==")
    check(f"{name}: valid", 1.0 if h.is_valid else 0.0, 1, "==")
    rs = H.RIB_SETS[name]
    crush = rs["rib_proud"] - H.SIDE_CLR
    check(f"{name}: net crush per side", crush, want, "==")
    n = 2 * len(rs["rib_x"])
    v = vol(h, pcb)
    print(f"     {name}: {n} ribs, {rs['rib_proud']:.2f} proud, crush {crush:.2f}/side, PCB interference {v:.3f} mm^3")
    check(f"{name}: ribs actually bite the PCB", v, 0.05, ">=", "mm^3")
    hph = H.holder_print_oriented(**kw)
    check(f"{name}: face-down overhang", overhang(hph, 0.0, up=+1), 2.0, "<=", "mm^2")
    # the rail/cup interface is untouched by the ribs: same seated fit as holder_v4
    check(f"{name}: x cup (without the slot ribs)", vol(C.place(h), cup_noribs), 0.0, "==", "mm^3")

print()
if FAILS:
    print("CHECK FAILED:", FAILS); sys.exit(1)
print("CHECK PASSED")
