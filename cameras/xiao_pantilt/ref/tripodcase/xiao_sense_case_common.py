"""Seeed XIAO ESP32S3 Sense case: shared parameters + part builders (body + lid).

Units mm. Frame = the board's frame (xiao_board_ref.py): origin base-PCB plan bottom-left,
+X along the long edge, USB-C on the X=0 end, Z=0 base-PCB bottom, lens looks +Z.

The board has no mounting holes (XIAO form factor), so it is trapped, not screwed:
  * the base PCB drops into a pocket 0.4 mm wider than the board (Y location) and sits flat
    on the inner floor (Z=0);
  * at the +X end a stop rib (below the expansion board) butts the PCB edge and two short
    hooks reach 0.95 mm over the PCB's top corners (0.2 mm above it) - the board goes in
    nose-first under the hooks, then the USB end drops;
  * at the USB end two full-height corner blocks stop the PCB's X=0 edge, carry the lid
    screws, and two lid posts land on the PCB corners (0.1 mm gap) next to them;
  * lid -> body: 4 x M2 x 8 self-tapping screws (two USB-end blocks, two in the thick +X wall).
USB plug AND the microSD card (which sticks out past the USB-C under the camera head) share
one opening in the X=0 wall; the antenna pigtail leaves through a notch in the -Y wall by the
U.FL jack; a 1/4"-20 tripod boss sits on the -Y wall (lens then looks sideways).
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1])]
from pcbkit import *
from build123d import *
import xiao_board_ref as B

PCB_L, PCB_W, PCB_T = B.PCB_L, B.PCB_W, B.PCB_T
STACK_TOP = B.STACK_TOP                      # 13.96 lens top
CAM_C = B.CAM_C
SD_X0, SD_Y0, SD_Y1, SD_Z0, SD_Z1 = B.SD_CARD[0], B.SD_CARD[1], B.SD_CARD[3], B.SD_CARD[4], B.SD_CARD[5]
USB_YC, USB_ZC = B.USB_YC, B.USB_ZC
EXP_X1, EXP_Z0 = B.EXP[2], B.EXP[4]          # 21.25, 4.18

# --- case parameters --------------------------------------------------------------------
WALL = 2.0
END_WALL_X1 = 4.0                            # +X wall is thick: it carries two lid screws
FLOOR_T = 2.5                                # 1.0 left under the USB relief
LID_T = 2.0
CLR_Y = 0.4                                  # PCB long edge -> pocket wall (each side)
CLR_X0 = 0.5                                 # card tip (x -3.11) -> USB-end inner wall
CLR_X1 = 1.25                                # expansion PCB edge (21.25) -> +X inner wall
TOP_CLR = 1.0                                # lens top -> lid underside
CORNER_R = 3.0
# USB-end corner blocks (X stop + screw bosses), full height
BLOCK_Y = 1.9                                # blocks span y -0.4..1.9 (card starts at y 2.48, may sit 0.4 lower)
PILOT_D, PILOT_DEPTH = 1.7, 8.0              # M2 self-tap
SCREW_THRU_D, CBORE_D, CBORE_DEPTH = 2.3, 4.2, 1.5
# +X end stop rib + hooks over the base PCB top corners
RIB_TOP = EXP_Z0 - 0.55                      # 3.63 (expansion PCB underside 4.18)
HOOK_X0 = 20.0                               # hook reaches 0.95 over the PCB edge (20.95)
HOOK_Z0 = PCB_T + 0.2                        # 1.45
HOOK_Y = [(-0.4, 2.0), (16.0, 18.18)]        # clear of the U.FL jack (y 2.61+) and the B2B (y 6.74..15.34) at +/-0.4 Y
# lid
LIP_H, LIP_T, LIP_GAP = 1.5, 1.2, 0.2
POST = (-0.2, -0.2, 2.0, 1.6)                # x0,y0,x1,y1 lid post on the PCB corner (mirrored at +Y); RST/BOOT start at y 2.16
POST_GAP = 0.1
WINDOW_D, WINDOW_CHAMFER = 9.0, 1.0
# openings
OPEN_Y0, OPEN_Y1 = 2.2, 15.6                 # USB overmold 12.3 wide on y 8.88 + the 11.2 card on y 8.07
OPEN_Z0, OPEN_Z1 = -1.5, 9.2                 # overmold 6.5 tall on z 2.36; card 6.85..8.5 + finger room
RELIEF_X1 = -1.0                             # floor relief (to OPEN_Z0) inside the wall for the overmold, reaching x -1.0
ANT_NOTCH = (17.0, 20.5, 1.4, 4.0)           # x0, x1, z0, z1 through the -Y wall (pigtail dia 1.13)
# tripod
TRIPOD = True
TRIPOD_BOSS_D, TRIPOD_BOSS_L = 14.0, 12.5
TRIPOD_HOLE_D, TRIPOD_HOLE_DEPTH = 8.0, 13.5  # ruthex RX-1/4-20 (12.7 long); 1.0 left to the cavity
TRIPOD_X = 8.5

# --- derived ----------------------------------------------------------------------------
XI0 = SD_X0 - CLR_X0                         # -3.61
XI1 = EXP_X1 + CLR_X1                        # 22.5
YI0, YI1 = -CLR_Y, PCB_W + CLR_Y             # -0.4 .. 18.18
X0, Y0 = XI0 - WALL, YI0 - WALL              # -5.61, -2.4
OUT_X = (XI1 - XI0) + WALL + END_WALL_X1     # 32.11
OUT_Y = (YI1 - YI0) + 2 * WALL               # 22.58
Z_IN_FLOOR = 0.0
Z_BOT = -FLOOR_T
Z_CEIL = STACK_TOP + TOP_CLR                 # 14.96 wall top / lid underside
Z_TOP = Z_CEIL + LID_T                       # 16.96
BODY_H = Z_CEIL - Z_BOT
BLOCK_PILOT_XY = [(XI0 + 1.6, 0.6), (XI0 + 1.6, PCB_W - 0.6)]          # (-2.01, 0.6 / 17.18)
END_PILOT_XY = [(XI1 + END_WALL_X1 / 2, 2.5), (XI1 + END_WALL_X1 / 2, PCB_W - 2.5)]   # (24.5, 2.5 / 15.28)
SCREW_XY = BLOCK_PILOT_XY + END_PILOT_XY
CASE_COLOR = Color(0.25, 0.45, 0.75)
TRIPOD_Z = (Z_BOT + Z_CEIL) / 2


def body():
    b = slab(OUT_X, OUT_Y, BODY_H, r=CORNER_R, at=(X0, Y0, Z_BOT))
    b = b - box((XI0, YI0, Z_IN_FLOOR), (XI1 - XI0, YI1 - YI0, BODY_H))
    # USB-end corner blocks (X stop + screw bosses)
    for (y0, y1) in ((YI0, BLOCK_Y), (PCB_W - BLOCK_Y, YI1)):
        b = b + box((XI0, y0, Z_IN_FLOOR), (-0.4 - XI0, y1 - y0, Z_CEIL - Z_IN_FLOOR))
    # +X stop rib under the expansion board + hooks over the PCB corners
    b = b + box((PCB_L + 0.35, YI0, Z_IN_FLOOR), (XI1 - PCB_L - 0.35, YI1 - YI0, RIB_TOP))
    for (y0, y1) in HOOK_Y:
        b = b + box((HOOK_X0, y0, HOOK_Z0), (XI1 - HOOK_X0, y1 - y0, RIB_TOP - HOOK_Z0))
    # screw pilots
    for (x, y) in SCREW_XY:
        b = b - cyl((x, y), Z_CEIL - PILOT_DEPTH, PILOT_D, PILOT_DEPTH + 1)
    # USB-C plug + microSD card opening in the X=0 end wall
    b = b - box((X0 - 1, OPEN_Y0, OPEN_Z0), (WALL + 2, OPEN_Y1 - OPEN_Y0, OPEN_Z1 - OPEN_Z0))
    b = b - box((X0 - 1, OPEN_Y0, OPEN_Z0), (RELIEF_X1 - X0 + 1, OPEN_Y1 - OPEN_Y0, Z_IN_FLOOR - OPEN_Z0 + 0.01))
    # antenna pigtail notch in the -Y wall
    ax0, ax1, az0, az1 = ANT_NOTCH
    b = b - box((ax0, Y0 - 1, az0), (ax1 - ax0, WALL + 2, az1 - az0))
    if TRIPOD:
        boss = Pos(TRIPOD_X, Y0 - TRIPOD_BOSS_L / 2, TRIPOD_Z) * Rot(90, 0, 0) * Cylinder(TRIPOD_BOSS_D / 2, TRIPOD_BOSS_L)
        hole = Pos(TRIPOD_X, Y0 - TRIPOD_BOSS_L + TRIPOD_HOLE_DEPTH / 2 - 0.01, TRIPOD_Z) * Rot(90, 0, 0) * Cylinder(TRIPOD_HOLE_D / 2, TRIPOD_HOLE_DEPTH)
        b = b + boss - hole
    b.label, b.color = "xiao_sense_case_body", CASE_COLOR
    return b


def lid():
    l = slab(OUT_X, OUT_Y, LID_T, r=CORNER_R, at=(X0, Y0, Z_CEIL))
    # locating lip inside the pocket, cut back around the USB-end blocks
    lip = box((XI0 + LIP_GAP, YI0 + LIP_GAP, Z_CEIL - LIP_H), (XI1 - XI0 - 2 * LIP_GAP, YI1 - YI0 - 2 * LIP_GAP, LIP_H)) \
        - box((XI0 + LIP_GAP + LIP_T, YI0 + LIP_GAP + LIP_T, Z_CEIL - LIP_H - 1), (XI1 - XI0 - 2 * (LIP_GAP + LIP_T), YI1 - YI0 - 2 * (LIP_GAP + LIP_T), LIP_H + 2))
    for (y0, y1) in ((YI0 - 1, BLOCK_Y + LIP_GAP), (PCB_W - BLOCK_Y - LIP_GAP, YI1 + 1)):
        lip = lip - box((XI0 - 1, y0, Z_CEIL - LIP_H - 1), (-0.4 - XI0 + 1 + LIP_GAP, y1 - y0, LIP_H + 2))
    l = l + lip
    # posts down onto the base PCB corners at the USB end
    px0, py0, px1, py1 = POST
    for y0 in (py0, PCB_W - py1):
        l = l + box((px0, y0, PCB_T + POST_GAP), (px1 - px0, py1 - py0, Z_CEIL - PCB_T - POST_GAP))
    # screw holes + counterbores
    for (x, y) in SCREW_XY:
        l = l - cyl((x, y), Z_CEIL - LIP_H - 1, SCREW_THRU_D, LID_T + LIP_H + 2)
        l = l - cyl((x, y), Z_TOP - CBORE_DEPTH, CBORE_D, CBORE_DEPTH + 1)
    # lens window
    l = l - cyl(CAM_C, Z_CEIL - 1, WINDOW_D, LID_T + 2)
    try:
        def _win_top(e):
            c = e.center()
            return abs(c.Z - Z_TOP) < 1e-3 and abs(((c.X - CAM_C[0]) ** 2 + (c.Y - CAM_C[1]) ** 2) ** 0.5 - WINDOW_D / 2) < 0.05
        l = chamfer(l.edges().filter_by(_win_top), WINDOW_CHAMFER)
    except Exception:
        pass
    l.label, l.color = "xiao_sense_case_lid", CASE_COLOR
    return l


def board_ref():
    b = B.gen_step()
    b.label = "xiao_esp32s3_sense_board"
    return b
