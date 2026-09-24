# Seeed XIAO ESP32S3 Sense tripod case (body + lid)

Printable two-part case for the **Seeed Studio XIAO ESP32S3 Sense** (base board + Sense
expansion board with OV2640/OV3660 camera, microSD, PDM mic). 32.1 x 22.6 x 19.5 mm outside
plus a 1/4"-20 tripod boss on one long wall. Designed 2026-08-21 by sargbench2 from the vendor
STEP that sargineer.com serves for `seeed-xiao-esp32s3-sense`; not yet printed.

Files: `xiao_sense_case_common.py` (all parameters + body/lid builders), `xiao_board_ref.py`
(board envelope, every number measured off the vendor STEP), `*.step.py` generator entries,
`verify.py` (interference/probe checks, optionally against the vendor STEP), `stl/` meshes,
`snaps/sheet.png` review sheet. Frame = board frame: origin base-PCB plan bottom-left, +X along
the long edge, USB-C on the X=0 end, Z=0 base-PCB bottom, lens looks +Z.

## What the board actually looks like (vendor STEP + Seeed wiki)

| item | where (mm) |
|---|---|
| base PCB | 20.95 x 17.78 x 1.25, corners r 1.906, no mounting holes |
| expansion PCB | x 6.57..21.25, y 0.5..17.28, Z 4.18..5.43 (on the B2B) |
| camera head | x -0.47..7.53, y 4.25..12.25, Z 8.2..10.3; lens barrel dia 7.84 to Z 12.2, tip dia 6 to **Z 13.96**; axis (3.53, 8.25) |
| **microSD** | socket on **top** of the expansion board (x 6.67..12.17), under the camera head; card inserted from the **USB end**, tip at **x -3.11**, Z 6.85..8.5 |
| USB-C shell | x -1.53..5.77, y 4.41..13.35, Z 0.26..4.46 (centre y 8.88, Z 2.36) |
| camera FPC socket | x 15.12..20.37 (pins to 21.12), y 0.82..17.02, Z 5.43..7.43 |
| B2B | x 17.53..20.47, y 6.74..15.34, Z 1.28..4.13 |
| U.FL antenna jack | x 17.73..20.73, y 2.61..5.71 on the base PCB, under the expansion board; pigtail leaves between the boards |
| RST / BOOT | x 0.3..2.9, y 2.2..3.8 (R, -Y) / 14.0..15.6 (B, +Y), top Z 1.98 |

## Case

* Pocket x -3.61..22.5, y -0.4..18.18; PCB sits flat on the inner floor (Z 0). Walls 2.0, the +X
  end wall 4.0 (carries two screws), floor 2.5, lid 2.0; lid underside Z 14.96 (1.0 over the lens).
* **Retention without screws through the board**: +X stop rib (x 21.3..22.5, Z 0..3.63, under
  the expansion board) + two hooks over the PCB top corners (x 20.0..22.5, y -0.4..2.0 and
  16.0..18.18, Z 1.45..3.63, i.e. 0.95 over the edge, 0.2 above the PCB); USB end: two
  full-height corner blocks (x -3.61..-0.4, y -0.4..1.9 mirrored) stop the X=0 edge and host the
  lid screws; two lid posts (x -0.2..2.0, y -0.2..1.6 mirrored) land on the PCB corners at Z 1.35.
  Insertion: nose-first under the hooks, tilted <= 10 deg, edge ~0.3 short of the rib; drop the
  USB end between the blocks; lid on. X play 0.75, Y play 0.8.
* **One opening on the USB end** (y 2.2..15.6, Z -1.5..9.2, floor relieved to x -1.0): the USB-C
  plug overmold (12.3 x 6.5 probe passes to the receptacle face) and the microSD card above it
  (card tip 2.5 mm inside the outer face: fingernail/tweezers to pull).
* Lens window dia 9 at (3.53, 8.25), 1 mm chamfer.
* Antenna notch 3.5 x 2.6 in the -Y wall at x 17..20.5, Z 1.4..4.0 for the U.FL pigtail; the flex
  antenna goes outside (the cavity is far too small for it). Alternative: route the pigtail
  forward under the expansion board and out the USB opening, and fill the notch.
* Lid: 1.2 x 1.5 lip (0.2 gap) cut back around the blocks; 4 x M2 x 8 self-tap into 1.7 x 8 pilots
  at (-2.01, 0.6), (-2.01, 17.18), (24.5, 2.5), (24.5, 15.28); 4.2 x 1.5 counterbores.
* Tripod: dia 14 x 12.5 boss on the -Y wall at x 8.5, Z 6.23, dia 8 x 13.5 hole for a ruthex
  RX-1/4-20 heat-set insert (1.0 mm left to the cavity). Lens then looks sideways.
* Not exposed: RST/BOOT (RST is under the card; BOOT would need a 13 mm pin hole at (1.59,
  14.81) - easy to add), PDM mic (not in the vendor model), battery pads (drill the floor).

## Verification (verify.py, 2026-08-21)

Zero interference body/lid vs board at nominal and at every in-pocket extreme (X -0.4 / +0.35,
Y +/-0.4) - against **both** the box envelope and the real vendor STEP (103 solids); body & lid 0;
USB overmold probe 0; card pulled 6 mm out 0; hook gaps open; tilted insertion 6/8/10 deg 0
(12 deg touches: 0.74 mm3); lens column clear; `inspect validate` ok for body and lid.
Things the first print should check: pocket width after FDM shrink, the 0.2 hook gap, the
13.6 mm lid posts, and whether the card is comfortable to pull.

## Print

Body floor-down (side boss wants support), lid top-down; 0.4 nozzle / 0.2 layer, PLA or PETG,
>= 3 perimeters. Hardware: 4 x M2 x 8 self-tapping pan head, optional 1/4"-20 heat-set insert.
