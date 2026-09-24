"""Seeed XIAO ESP32S3 Sense - board envelope for the case design (boxes, not the vendor model).

Every figure below is MEASURED off the vendor STEP that sargineer.com serves for
seeed-xiao-esp32s3-sense (/m/sarg/seeed-xiao-esp32s3-sense/f/amz-xiao-esp32s3-sense.step,
Seeed wiki 3D model rebased by sarg; bounding boxes of the solids, 2026-08-21).
Frame: origin base-PCB plan bottom-left, +X along the long edge, USB-C on the X=0 end,
Z=0 base-PCB bottom, lens looks +Z.

What the vendor model shows (and Seeed's wiki photo 66.jpg confirms): the microSD socket is
on TOP of the Sense expansion board, under the camera head; the card (modelled inserted)
sticks out past the USB-C end to x -3.11 at Z 6.85..8.5.  The U.FL antenna jack sits on the
base PCB under the expansion board at the -Y/+X corner; its cable leaves between the boards.
Not in the vendor model: the PDM mic (tiny, top of the expansion board near the FPC socket).
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[2] / 'common')]   # hw/common: caseskit, pcbkit
from pcbkit import *
from build123d import *

PCB_L, PCB_W, PCB_T, PCB_R = 20.95, 17.78, 1.25, 1.906       # base PCB
EXP = (6.57, 0.50, 21.25, 17.28, 4.18, 5.43)                # expansion PCB x0 y0 x1 y1 z0 z1
CAM_HEAD = (-0.47, 4.25, 7.53, 12.25, 8.20, 13.96)           # OV3660 head (8 x 8) incl. lens top
CAM_C = (3.53, 8.25)                                        # lens axis
HEAD_TOP = 10.3                                             # square head top; barrel above
LENS_D, LENS_TOP_D, LENS_STEP_Z = 7.84, 6.0, 12.2           # barrel dia to Z 12.2, then 6.0 to 13.96
SD_CARD = (-3.11, 2.48, 11.95, 13.66, 6.85, 8.50)            # microSD inserted; pull -X to remove
SD_SOCKET = (6.67, 2.92, 12.17, 14.32, 5.38, 8.03)
FPC_CONN = (15.12, 0.82, 20.37, 17.02, 5.43, 7.43)           # camera FPC socket (pins to x 21.12, Z 7.18)
FPC_PINS = (16.26, 3.07, 21.12, 14.77, 5.42, 7.18)
FPC_ROLL = (7.49, 5.25, 14.48, 11.25, 5.85, 8.75)            # rolled flex between socket and head
USB = (-1.53, 4.41, 5.77, 13.35, 0.26, 4.46)                 # USB-C shell (centre y 8.88, z 2.36)
USB_YC, USB_ZC = 8.88, 2.36
B2B = (17.53, 6.74, 20.47, 15.34, 1.28, 4.13)
SHIELD = (6.71, 2.59, 17.30, 15.19, 1.25, 3.25)              # ESP32-S3R8 can
UFL = (17.73, 2.61, 20.73, 5.71, 1.25, 2.50)                 # antenna jack (plug adds ~1.3 on top; cable exits -Y)
BUTTONS = {"RST": (0.27, 2.16, 2.87, 3.76, 1.35, 1.98),      # R at -Y, B at +Y (Seeed front pinout)
           "BOOT": (0.29, 14.01, 2.89, 15.61, 1.35, 1.98)}
CASTELL_X = [2.855 + 2.54 * i for i in range(7)]             # 7+7 half-holes along both long edges
STACK_TOP = 13.96
BBOX = (-3.11, 0.0, 0.0, 21.25, 17.78, 13.96)


def _b(t, label, color=None):
    x0, y0, x1, y1, z0, z1 = t
    return box((x0, y0, z0), (x1 - x0, y1 - y0, z1 - z0), label=label, color=color)


def gen_step():
    base = slab(PCB_L, PCB_W, PCB_T, r=PCB_R, label="base_pcb", color=PCB_COLOR)
    exp = _b(EXP, "sense_expansion_pcb", PCB_COLOR)
    parts = [base, exp,
             _b(USB, "usb_c_shell", METAL), _b(SHIELD, "esp32s3_can", METAL), _b(B2B, "b2b_connector", BLACK),
             _b(UFL, "ufl_antenna_jack", METAL),
             _b(SD_SOCKET, "microsd_socket", METAL), _b(SD_CARD, "microsd_card_inserted", BLACK),
             _b(FPC_CONN, "camera_fpc_socket", WHITE), _b(FPC_PINS, "camera_fpc_pins", METAL),
             _b(FPC_ROLL, "camera_fpc_roll", COPPER)]
    hx0, hy0, hx1, hy1, hz0, hz1 = CAM_HEAD
    head = box((hx0, hy0, hz0), (hx1 - hx0, hy1 - hy0, HEAD_TOP - hz0), label="camera_head", color=BLACK)
    barrel = cyl(CAM_C, HEAD_TOP, LENS_D, LENS_STEP_Z - HEAD_TOP, label="lens_barrel", color=BLACK)
    tip = cyl(CAM_C, LENS_STEP_Z, LENS_TOP_D, hz1 - LENS_STEP_Z, label="lens_tip", color=BLACK)
    parts += [head, barrel, tip]
    for k, t in BUTTONS.items():
        parts.append(_b(t, f"button_{k.lower()}", WHITE))
    return assembly("xiao_esp32s3_sense_board_envelope", parts)
