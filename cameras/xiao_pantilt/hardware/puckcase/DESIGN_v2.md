# XIAO puckcase v2 — bay redesign after the coupon print (2026-09-13)

Status: **plan / contract, not built**. v1 is `DESIGN.md` + `puckcase_lib.py`
(commit af3478e, coupons c8c0f10). Everything outside the board bay (ring
outline, eave, drip groove, front lip, puck lip on the back plate, bosses,
cord slot, tie post) is unchanged except for the depth numbers in §3.

## 1. What the coupon print showed (deskcam 2026-09-13 11:58–12:10)

| Finding | Consequence |
|---|---|
| The board has **pin headers**: body on the back of the PCB, pins ~5–6 mm proud behind it. The body overhangs the PCB long edge by ~1.0 mm (castellated pads). The user wants the case to work **with or without headers**. | Nothing may bear on the back face of the board along its long edges (the v1 ledges), and nothing may sit within 1.0 mm outside the long edges behind the PCB. The back gap grows from 3.0 to 9.0. |
| Lens sits ~0.5 mm high in the front-plate hole. The camera head is only held by its flex ("floppy"). | The ring gets a **collar** that captures the 8.3 × 8.3 × 2.1 square head and the Ø7.84 barrel. Hole and collar reference the same lens axis, so the hole alignment no longer depends on where the PCB sits. |
| SD card tip is 0.5 mm from the top wall. | Board moves down 3.5 mm → 4.0 mm roof over the card. |
| User: front-plate posts are unnecessary if the bay holds the board. | Posts deleted. The front plate is a plain plate: hole + chamfer + lip + ribs. |

Header geometry assumed (not in the vendor STEP): 2 × 7 pins at
x = 2.855 + 2.54·i, body 2.54 × 17.78 × 2.5 on the PCB back (board z −2.5..0),
centred on the pad row so it spans y −1.0..1.54 and mirror; pins 0.64 square to
z −8.5. Every check in §6 runs with and without this header mock.

## 2. Retention concept ("hold it by the ends and the head")

The long edges are off-limits (headers), so the board is located by its two
header-free ends, by the expansion PCB's edges, and by the camera head:

| DOF | Feature | Where it bears |
|---|---|---|
| Z forward (toward lens), far end | **hooks** (v1, kept) | PCB top face at the far corners, 0.15 over |
| Z forward, USB end | **bridge** = a band of the new USB-end wall | USB-C shell top (rigid metal, z 4.46), 0.10 over |
| Z back, far end | **centre ledge** (new) | PCB back face at the far end, y 5..13 (no headers there), 0.10 under |
| Z back, USB end | **snap tongue** (new, the one flexing feature) | PCB back face at the USB end edge, y 6..12, lip 0.4 over the edge |
| Y (along the board) | far-end **stop ribs** (v1, kept) 0.20 gap; USB-end wall face 0.40 gap | PCB end edges; 0.6 total play |
| X (across) | **side rails with crush ribs** (new; "the small ribs on the side clamps") | the **expansion PCB's** long edges (y 0.5 / 17.28, z 4.18..5.43) — the only long-edge surface that is clear of header bodies, buttons and the antenna plug. 0.15 clearance, ribs 0.25 proud → 0.10 nominal crush per side |
| Lens | **collar** (new) | square window 8.6 around the head, Ø8.25 bore around the barrel, step 0.2 over the head top |

Insertion (from the back mouth, before the back plate goes on): SD card in;
tilt the board ~13° (far end forward), slide the far edge into the far-end
groove (between hooks and ledge, chamfered entry); swing the USB end forward.
The expansion edges ride down the rails, the head enters the collar window
over the last ~4° (0.6 chamfer), the USB-C shell lands under the bridge and
the PCB end edge cams the tongue back 0.6 and snaps behind its lip. Remove by
pressing the tongue outward with a fingernail through the back mouth.

Why not simpler: any feature touching the base PCB's long edges has to reach
1.5 mm inward from a wall that must clear the header body; in the ring's
print orientation (standing on its back mouth) its underside would be a
1.5 mm horizontal overhang directly above the header body, which cannot be
chamfered away. The expansion-PCB rails have a free 45° underside instead.

## 3. Parameters (board frame unless stated; case = (X_B0 − y, Y_B0 − x, Z_B0 − z))

Frame unchanged from v1: board origin PCB bottom-left, +x along the length
from the USB-C end, +z toward the lens; `board_to_case` as in `puckcase_lib.py`.

### Placement and depth
| Name | Value | Note |
|---|---|---|
| BOARD_DROP | 3.50 | new |
| Y_B0 | 71.29 | 74.79 − 3.5; PCB Y 50.34..71.29 |
| X_B0 | 31.855 | unchanged; PCB X 14.075..31.855 |
| Z_B0 | 17.36 | unchanged (PLATE_T 2.4 + LENS_GAP 1.0 + stack 13.96) |
| LENS (XC, YC) | (23.605, 67.76) | hole and collar share it |
| CARD_TIP_Y | 74.40 | roof to the top wall inner face (78.40) = 4.0 |
| BACK_GAP | 9.00 | was WIRE_GAP 3.0: header body 2.5 + pins 6.0 + 0.5 clearance to the plate. Trim pins to 4 → 7.0 |
| Z_PLATE | 26.36 | ring back mouth / plate front (was 20.36) |
| Z_BACK | 30.36 | puck lip 30.36..37.86 |
| BOSS_Z0 | 15.86 | bosses now 10.5 long → **M2 × 12** screws (or counterbore Ø4.4 × 4.5 with BOSS_D 6.5 to keep M2 × 8) |
| CORD_SLOT_Z | Z_PLATE − 3.5 .. Z_PLATE − 0.5 | follow the mouth |
| TIE_POST_Z0 | Z_PLATE − 6.0 | follow the mouth |
| eave brow angle | 43° above the axis | was 32°; tip Z 3.4, eave edge Z −8, lens 10.64 below the wall inner face |

### Bay walls
| Name | Board | Case | Note |
|---|---|---|---|
| SIDE_CLR | 1.50 | | wall inner face from the PCB long edge (header body 1.0 + 0.5) |
| side walls | y −1.5..−3.1 and 19.28..20.88; x −7.11..23.2 | X 10.975..12.575 & 33.355..34.955; Y 48.09..78.40; Z 5.56..26.36 | hang from the ring's top wall as in v1; full height to the collar face |
| far-end wall | x 21.6..23.2; z ≤ 6.0 | Y 48.09..49.69; Z 11.36..26.36 | inner face 0.35 clear of the expansion PCB overhang (x 21.25). Low so the antenna cable can cross it |
| USB-end wall | x −1.6..−0.4; z −9.0..9.0 | Y 71.69..72.89; Z 8.36..26.36 | spans wall to wall, merges into the collar above |

### Far-end groove
| Name | Board | Case |
|---|---|---|
| STOP ribs | x 21.15..21.6, y −0.5..3.5 (+ mirror 14.28..18.28), z ≤ 3.6 | Y 49.69..50.14; X 28.355..32.355 / 13.575..17.575; Z 13.76..26.36 |
| HOOKS | x 20.0..21.6, y −0.5..1.6 (+ mirror), z 1.40..3.6 | Y 49.69..51.29; X 30.255..32.355 / 13.575..15.675; Z 13.76..15.96 |
| LEDGE | x 19.7..21.6, y 5..13, z −0.10 down to −9.0 | Y 49.69..51.59; X 18.855..26.855; Z 17.46..26.36 |
| entry chamfers | 0.5 on the hook's back-inner edge and the ledge's front-inner edge | |

### USB-end wall features
| Name | Board | Case |
|---|---|---|
| shell window | y 3.9..13.85, z −0.1..4.56 | X 18.005..27.955; Z 12.80..17.46 |
| BRIDGE (front stop) | the wall band z 4.56..6.5 over the window; face on the shell top (4.46) with 0.10 | Z 10.86..12.80 |
| card notch | y 2.2..13.9, z 6.5 up to the collar (9.0) | X 17.955..29.655; Z 8.36..10.86 |
| TONGUE | y 6..12, thickness 0.9 at x −1.1..−0.2, slits 0.8 wide at y 5.2..6.0 / 12.0..12.8 from z −8.8 up to the window | X 19.855..25.855; Y 71.49..72.39; Z 17.46..26.16 |
| tongue lip | z −0.6..−0.1, x −0.2..+0.4 (0.4 over the PCB back edge); 45° ramp on its back side down to x −0.2 at z −1.2 | Z 17.46..17.96; Y 70.89..71.49 |
| tongue mechanics | deflection 0.6 at the lip, L 8.7, t 0.9 → ~1.1 % strain, ~2.5 N (PETG ok; PLA marginal) | |

### Side rails (on the expansion PCB edges)
| Name | Board | Case |
|---|---|---|
| RAIL | x 8..17, z 4.2..5.6, face at y 0.35 (+ mirror 17.43), root on the side wall | Y 54.29..63.29; Z 11.76..13.16; X 14.425 / 31.505 |
| rail underside | 45° chamfer from the tip (z 4.2) back to the wall (z 2.35) | printable, and 2.35 above any front-side header body |
| RIBS | 2 per rail, x 8.5..12.5 and 13.0..17.0, 0.25 proud (`fits.edge_crush_rib` shape, 1.4 tall) | 0.10 nominal crush; ends 0.22 clear of the FPC socket (y 0.82) |
| −y rail end at x 17 | | leaves x 17..20 at the −y edge free for the U.FL cable to leave the board |

### Collar
| Name | Board | Case |
|---|---|---|
| plate | x −1.6..9.8 (front part z 10.5..11.8 extends to x −2.3), wall to wall in y, z 9.0..11.8 | Y 61.49..72.89 (73.59 front); X 12.575..33.355; Z 5.56..8.36 |
| FPC relief | back face raised to z 9.5 over x 7.83..9.8 | Z 7.86 |
| window | 8.6 square centred on CAM_C (3.53, 8.25): x −0.77..7.83, y 3.95..12.55, z 9.0..10.5; 0.6 × 45° chamfer at the back edge | X 19.305..27.905; Y 63.46..72.06; Z 6.86..8.36 |
| step | z 10.5 = head top 10.3 + 0.2 | Z 6.86 |
| bore | Ø8.25 (barrel 7.84 + 0.4), z 10.5..11.8 | Z 5.56..6.86 |
| clearances | card top 8.5 → 0.5; SD socket 8.03 → 0.97; FPC roll 8.75 → 0.75 (relief) | |

### Front plate
Unchanged outline, lip, ribs, chamfered Ø7.5 hole at (23.605, 67.76). **No posts.**

### Antenna
Behind the board between the header rows (y 3..15, z −3..−4.5) or, better,
below the bay against the back plate (Y 15..40). Cable leaves the U.FL plug
toward −y at x 17..20 (clear of the −y rail and the hooks), crosses the low
far-end wall at the corner, drops into the cavity.

## 4. Print orientation (unchanged rule: one flat face per part)
- Front plate: outer face down. Nothing on it but the lip.
- Ring: standing on its back mouth, eave up. New bridges: shell window
  9.95 mm, card notch 11.7 mm, collar sheet 20.8 mm between the side walls
  (supported along one edge by the USB-end wall). Rails have 45°
  undersides. The tongue and ledge are walls standing on the bed. Hooks
  are 1.6 mm overhangs as in v1.
- Back plate: front face down, puck lip up. Unchanged.

## 5. Parts
| Part | Change |
|---|---|
| 4 × M2 × 12 pan head (was M2 × 8) | bosses are 10.5 long now |
| everything else | as v1 |

## 6. Checks (fail-closed, `check.py`)
1. Ring / front plate / back plate: 1 solid each, valid, volumes reported.
2. Interference = 0 between every printed part and the vendor board + header
   mock, at nominal and at the four Y/X play extremes (±0.3 along, ±0.15
   across).
3. Clearances ≥ stated: collar–head 0.15 per side, collar–card 0.5,
   collar–FPC roll 0.5, bridge–shell 0.10, hook–PCB top 0.15, ledge–PCB back
   0.10, tongue lip–PCB back 0.10, rails–expansion edge 0.15 (rib −0.10),
   buttons–anything 0.3, U.FL plug (+1.3 z) and a Ø1.2 cable path at
   x 17..20 over the −y edge–anything 0.3, header body/pins–anything 0.3.
4. Tilt insertion: the vendor board rotated −13° about its far edge (and
   −4° with the head 1.3 short of the window) has no interference with the
   ring; the far edge fits the groove at 13° (slot 1.5 vs 1.25 + 0.8·sin 13°).
5. Tongue: lip reach 0.4, slit width 0.8, strain ≤ 1.5 %.
6. Eave brow angle ≥ 40°; card roof ≥ 3.5.
7. Every mating face plane printable: overhang faces > 45° from vertical
   listed and justified (hooks, tongue lip, collar step corners).
8. Screws: boss bore Ø2.2, pilot Ø1.7 × 3.4, screw tip 0.3 short of the pilot
   bottom with M2 × 12.

## 7. Build order
1. `puckcase_lib.py`: BOARD_DROP, BACK_GAP, delete LEDGE/BLOCK/POST params,
   add the tables above as parameters; new builders `_rails()`, `_collar()`,
   `_usb_end_wall()` (window, notch, tongue), `_far_end()`; `header_mock()`.
2. `ring.step.py`, `front_plate.step.py` (posts gone), `back_plate.step.py`
   (Z shift only). Regenerate `puckcase.step.py`, `fitcheck.step.py`.
3. `check.py` per §6; `checks.md`.
4. Snapshots: front view into the bay, section at X = CX, section at the
   tongue (X 22.9), section across the rails (Y 58), tilt-insertion frame.
5. `print/coupon_ring_bay.step.py` → `ring & (Y ≥ 44)` (includes the far-end
   wall), same flip; `print/coupon_front_plate.step.py` → hole only. STL/3MF.
6. README, STATUS, memory; commit.

## 8. Open items for the user
- BACK_GAP 9.0 = header body 2.5 + 6 mm pin tails + 0.5 to the plate; 7.0 if you trim the pins to 4 mm.
- The rails bear on the expansion PCB's edges (0.5 inboard of the base PCB).
  If that board's edge has a component I don't know about, the rails move
  to x 8..14.
- M2 × 12 screws, or keep M2 × 8 with counterbored Ø6.5 bosses.
