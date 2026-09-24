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
| side walls | y −1.5..−3.1 and 19.28..20.88; x −7.11..23.2 | X 10.975..12.575 & 33.355..34.955; Y 48.09..78.40; Z 5.56..26.36 | hang from the ring's top wall as in v1; full height to the collar face. **v2.4 (§10): Z 8.70..26.36 in one band** — the collar has gone, so nothing needs them forward of the front lip |
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

### Collar — **moved to the front plate in v2.4 (§10)**
Every row below is built, with its numbers unchanged, as the **head window
boss** on the front plate instead of as a sheet on the ring. The "plate" row's
sheet and its extended front part are gone; the boss is an 11.80 square tower
growing from the plate's inner face (Z 2.40) to the mouth (Z 8.36).

| Name | Board | Case | v2.4 |
|---|---|---|---|
| plate | x −1.6..9.8 (front part z 10.5..11.8 extends to x −2.3), wall to wall in y, z 9.0..11.8 | Y 61.49..72.89 (73.59 front); X 12.575..33.355; Z 5.56..8.36 | **deleted** → boss X 17.705..29.505, Y 61.86..73.66, Z 2.40..8.36 |
| FPC relief | back face raised to z 9.5 over x 7.83..9.8 | Z 7.86 | same, in the boss's −Y wall |
| window | 8.6 square centred on CAM_C (3.53, 8.25): x −0.77..7.83, y 3.95..12.55, z 9.0..10.5; 0.6 × 45° chamfer at the back edge | X 19.305..27.905; Y 63.46..72.06; Z 6.86..8.36 | same; the chamfer is now the lead-in the head is pressed onto |
| step | z 10.5 = head top 10.3 + 0.2 | Z 6.86 | same |
| bore | Ø8.25 (barrel 7.84 + 0.4), z 10.5..11.8 | Z 5.56..6.86 | Z **2.40**..6.86, down onto the plate's own Ø7.5 hole |
| clearances | card top 8.5 → 0.5; SD socket 8.03 → 0.97; FPC roll 8.75 → 0.75 (relief) | | unchanged |

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

## 9. v2.1 amendments (2026-09-13) — the contract as built

Two amendments from the design owner, plus the deviations the build forced.
Everything above stands except where a line below overrides it.

### A. The bridge band is deleted; the USB-end window is one opening
The v2.0 bridge (§3 "BRIDGE", the wall band at z 4.56..6.5) made the microSD
card unfittable: it swept 8 mm³ through the band at any tilt beyond ~1°, and
it could not be fitted afterwards either (5.28 mm of straight travel needed
past the socket mouth, 4.00 mm of roof). So:

- the USB-end wall becomes **two side pillars**, board y −0.5..2.2 and
  13.9..18.28, full height to the collar (z −9.0..9.0), plus the strip at
  z −9.0..−8.8 that roots the snap tongue;
- the shell window and the card notch **merge into one opening**, board
  y 2.2..13.9 (the wider notch width), z −8.8..9.0 — tongue root to the
  collar's back face;
- §2's insertion order returns to "**SD card in**, then tilt the board in";
- the USB end's **forward stop is now the collar step** (z 10.5, 0.20 over the
  head top), acting through camera head → microSD socket → expansion PCB →
  B2B connector → base PCB. The far-end hooks (0.15 over the PCB top) catch
  first, so measured forward travel of the whole board is 0.155;
- the two pillars are the PCB's rigid +Y stop (0.40) and are clear of the
  entire swept board;
- §6.3's "bridge–shell 0.10" is replaced by "collar step – head top 0.20";
- the v2.0 bridge-relief deviation is withdrawn (there is no bridge).

### B. Shorter bosses so M2 × 12 actually holds
v2.0's 10.5 boss left only 1.5 mm of thread in the back plate.
**BOSS_LEN = 9.00, BOSS_Z0 = Z_PLATE − 9.00 = 17.36**, Ø5.5 unchanged: M2 × 12
engages the plate by 3.00 with the tip 0.40 short of the 3.4 pilot bottom.
(The amendment proposed 8.3; that gives 3.7 of engagement into a 3.4 pilot,
i.e. the screw bottoms out 0.30 past it. 9.00 is the value that satisfies both
"engagement ≥ 3.0" and "tip ≥ 0.3 short".) Driver access down all four boss
axes is clear from the front mouth (Ø5.5 column, Z 2.40..17.36, 0 mm³).

### C. Deviations the build forced (each is `# DEVIATION`-commented in code)
1. **Board y → case −X** — §3's mapping triple has determinant −1: a mirror,
   not a rigid placement. Handedness forces it; the lens stays on CX.
2. **Side walls in two Z bands** — one Z range over the whole run puts them
   inside the front plate's lip band (Z 2.40..8.40). Full reach only to
   Y 76.35; Z 8.70..26.36 above that.
3. **Centre ledge: 0.30 flat bearing + a 45° entry ramp** — at 13° the PCB's
   back face lifts reach·sin 13°, so a flat face 0.10 behind it may only reach
   0.444. The 0.10 gap is kept where the ledge bears, at the PCB's far edge.
4. *(withdrawn — was the bridge relief)*
5. **A 4.5 × 4.5 wire notch through the +X side wall** (Y 52.30..56.80,
   Z 21.86..26.36) — §3's "low" far-end wall is low in *board* z, i.e. case
   Z 11.36..26.36, a full barrier; without the notch the bay is a closed box
   and neither the LOAD lead nor the U.FL coax can reach the cavity below.
6. **`tilt_loc` pivots about the PCB's back-far corner** — the v1 top-corner
   pivot drives the far edge 0.28 further in and bites the stop ribs for a
   motion the board cannot make.
7. **`CORD_SLOT_R` 1.499** — `RectangleRounded` rejects r = h/2 exactly.
8. **§6.2's ±0.3 along becomes the true stop faces, −0.20 / +0.40** — §2/§3
   give 0.20 to the stop ribs and 0.40 to the USB-end pillars, so −0.30 is a
   position the board cannot reach. Across stays ±0.15 (the rails).
9. **The camera head is a separate occurrence from the PCB in the play and
   tilt sweeps** — §1 says it is held only by its flex and §2 makes the collar
   position the lens, so it is fed into the collar by hand rather than swung
   in with the board (rigidly attached it puts 1.9 mm³ into the collar at
   −4°). The **card is not** separate any more: since amendment A it is fitted
   before insertion and rides with the PCB through every sweep.

### D. v2.2 — the snap tongue moves to the pillars (2026-09-13)
v2.1's single central tongue could not survive insertion: the USB-C shell
stands 1.53 proud of the PCB's end edge and is 4.2 tall, so once the USB end
is lifted ~2 mm its rear corner is behind the PCB's back plane at case
Y 72.6..73.3 — past the tongue's back face. Measured tongue-body interference
was 0.98 mm³ at −2° rising to 6.66 at −13°, needing ~1.8 mm of deflection
against 0.6 of design travel. Any tongue inside the shell's board-y span
(4.41..13.35) has this problem. So:

- **the central tongue and its slits are deleted**;
- **each USB-end pillar becomes a tongue over its whole width** and extends
  1.7 into the opening so its lip lands on the *straight* part of the PCB's end
  edge (the R1.906 corners leave straight edge only for board y 1.906..15.874):
  **tongue A board y −0.50..3.90** (case X 27.955..32.355), **tongue B
  y 13.88..18.28** (case X 13.575..17.975), both 4.40 wide, both ≥ 0.50 clear
  of the shell span (0.510 and 0.530);
- thickness 0.9 at board x −1.1..−0.2, root in the z −9.0..−8.8 strip (which
  now runs wall to wall and ties the side walls together at the bed), top =
  the lip at z −0.6..−0.1 reaching x +0.4 with the 45° ramp behind it;
- **above board z −0.1 there is no wall at the USB end at all**: the opening is
  the full bay width from the lip level to the collar's back face (z 9.0), and
  the collar sheet bridges wall to wall, 20.8 mm, as in v2.0 before the
  pillars;
- **there is no rigid +Y stop any more.** The tongues' faces at board x −0.2
  are a soft +Y stop, so the board's Y play is **0.20 to the far-end stop ribs
  and 0.20 to the tongue faces**;
- removal: press **both** tongues outward through the back mouth.

Measured: tongue bodies 0.0000 mm³ against the full swept board at
0/−2/−4/−8/−13°; only the cam ramps engage (1.36 mm³ at −2°, 1.46 at −4°,
0 elsewhere). Lip bearing on the PCB back 1.1163 mm² per tongue (2.791
effective length), of which 1.994 mm is on the straight end edge. Strain
1.070 % at 0.6 of deflection; snap force 1.46 N per tongue, 2.92 N total
(E = 2000 MPa, PETG).

### E. v2.3 — the tongues must not hinge on the root strip (2026-09-13)
v2.2 rooted both tongues in a 0.2 mm ligament: I ≈ 0.001 mm⁴ per mm of width,
which would have taken the whole hinge rotation instead of the tongue blade.

- **root strip z −9.0..−7.5** (1.50 tall, unchanged 1.40 thick at board
  x −1.6..−0.2, still wall to wall and still tying the side walls together);
- **tongue thickness 0.8** (board x −1.0..−0.2), **free length 7.4**
  (z −7.5..−0.1);
- lip unchanged: 0.4 reach, z −0.6..−0.1, 45° ramp behind it.

Measured: strain **1.315 %** at 0.6 of deflection (≤ 1.5); snap force
**1.67 N per tongue**, 3.34 N total, treating each tongue as a free cantilever
(E = 2000 MPa, ν = 0.35, PETG).

Strip compliance, tongue A's root at a = 3.20 from the +X wall, b = 17.58,
free span 20.78:
- **bending** under the root shear 1.67 N (fixed-fixed, I = 0.343 mm⁴):
  **0.0161 mm** at the lip — negligible, as expected (< 0.05);
- **torsion** under the root moment 12.34 N·mm is the *governing* mode, because
  the tongue's root moment is about the X axis and the strip runs along X:
  J = 0.616 mm⁴, G = 741 MPa → **0.542 mm** at the lip.

So the strip and the blade are comparable springs in series (2.78 and
2.99 N/mm): total rate 1.44 N/mm, i.e. **0.86 N per tongue** at 0.6 of travel
rather than 1.67, and the blade sees only ~half the computed strain. This
lowers the *preload*, not the retention: the lip's 0.4 engagement is geometric
and a +Z load on the board is carried by the lip in bearing, not by the spring.
If more preload is wanted, thickening the strip from 1.40 to 2.40 in board x
(to x −2.6..−0.2, a region that is clear of the whole swept board) roughly
doubles its torsional rate and brings the torsional term to ~0.25 mm.

### F. Open against this contract
Nothing fails. `check.py` passes with no warnings. Remaining process risks:
the strip's torsional softness above (preload only), ~~the collar's 20.8 mm
bridge~~ (withdrawn in §10 — there is no collar), and the assumed header
geometry — see README "Open items".

## 10. v2.4 amendments (2026-09-13) — print cleanup

Everything above stands except where a line below overrides it — in particular
§2's "the head enters the collar window over the last ~4°" (it now rides in
with the board and the *plate* is pressed over it), §3's Collar table (moved,
see above) and §4's "collar sheet 20.8 mm between the side walls" (there is no
such bridge any more).

v2.3 audited **253.4 mm² of overhang on the ring across 14 faces**, 180 of it
the lens collar and 129 of that a single 20.8 mm unsupported bridge carrying
the lens location. The ring prints standing on its back mouth (bed at
Z_PLATE 26.36, **+Z is down**) and the front plate prints outer-face down (bed
at Z 0, **+Z is up**), so a horizontal face whose normal is +Z is an overhang
on one part and a floor on the other. v2.4 moves the offending faces to the
part that supports them and trims what is left.

| Change | Was | Is | Effect |
|---|---|---|---|
| **head window boss** on the front plate | `_collar()`: a sheet across the ring's bay, case Z 5.56..8.36, wall to wall (X 12.575..33.355) with an extended front part to Y 73.59 | `_head_window_boss()`: an 11.80 square (COLLAR_WIN + 2·**HEADWIN_WALL 1.60**) tower on the plate's inner face, X 17.705..29.505, Y 61.86..73.66, Z **PLATE_T 2.40**..8.36. Ø8.25 bore 2.40..6.86 onto the plate's Ø7.5 hole, 8.60 window 6.86..8.36 with the 0.60 × 45° lead-in at the mouth, FPC relief cutting the −Y wall to Z 7.86 over Y 61.49..63.46 | **−180 mm²** of ring overhang (the sheet's underside 129.07, the window step 20.50, the FPC relief roof 16.08, the front part's underside 14.55). The boss adds **0 mm²** to the plate: in its print orientation the bore annulus at 2.40, the step at 6.86, the relief at 7.86 and the mouth at 8.36 all face away from the bed |
| **side walls: one Z band** | two boxes — Z 8.70..26.36 over Y 48.09..78.40 plus a forward band Z 5.56..8.70 over Y 48.09..76.35 "to the collar's front face" (`SIDE_BZ[1]` = 11.80 board z) | one box per wall, Z **SIDE_BACK_Z0 8.70**..26.36 over the full run Y 48.09..78.40; `SIDE_BZ = (−9.00, 8.66)`, `SIDE_FWD_Y1` deleted | nothing needs the walls forward of the front lip band once the collar has gone. The rails (Z 11.76..13.16, 45° underside back to 15.01) are the deepest thing they carry and are still fully rooted. −480 mm³ of ring |
| **front-mouth lead-in clipped at the eave root** | `flare_down(IN_*, PLATE_T, LEADIN)` all the way round | the same tool, intersected with Y ≤ `Y_SHOULDER` 74.80 | forward of Z 2.40 the eave continues the inner wall at Y = IN_Y1, so the oversize there was not a lead-in but a 0.6 step whose roof (**28.48 mm²** at Z 2.40, X 1.80..45.41, Y 74.80..79.00) faced the bed. Side and bottom lead-ins unchanged. Side effect: the +Y crush rib now bears over its whole 4.9, so `front_plate × ring` goes 11.4800 → **11.7227 mm³** (expected 11.8213 ± 10 %) |
| **drip groove: a V, not a rectangle** | `box_at(..., DRIP_Z0, ..., DRIP_D 0.80, DRIP_W 1.00)` — a 0.8-deep slot in the eave's underside, roof at Z −6.50 | `prism_x([(IN_Y1, DRIP_Z0), (IN_Y1, DRIP_Z1), (IN_Y1 + DRIP_D, DRIP_Z1)], …)` — the tip-side face is a ramp (0.8 in Y over 1.0 in Z, 51.3° from horizontal), the back face at DRIP_Z1 −5.50 stays flat and its mouth corner stays sharp | **−28.17 mm²**. The drip edge is the back edge, nearest the case, and it is unchanged |
| **wire notch: a 45° gable** | a plain box, flat roof at Z 21.86 over Y 52.30..56.80 — a 4.5 mm bridge | `prism_x` with a ridge at Z 21.86 − 2.25 = **19.61** centred at Y 54.55 | **−7.20 mm²**. The ridge is 4.6 deeper than the rails' 45° underside root (Z 15.01) and the aperture the LOAD lead and the coax pass through (Z 23.51..25.21) is untouched |

**Result:** ring **9.3 mm² over 7 faces** (hook undersides 1.37 + 1.36, four
rail rib crests 0.75 each, the cord slot's 1.5 mm flat 3.60 — all accepted, all
sub-4 mm² tabs or short double-anchored bridges), front plate **1.3 mm²**
(unchanged, the +Y crush rib's underside), back plate **9.1 mm²** (unchanged,
the four Ø1.7 pilot bottoms). No part needs supports.

### Consequences for assembly and for the checks

- **Assembly order changes.** §2's "feed the head into the collar by hand" is
  gone: the head rides in rigidly with the PCB (0.0000 mm³ against the ring at
  0/−2/−4/−8/−13°, where v2.3 put 1.89 mm³ into the collar at −4°), and the
  **front plate's head window drops over the head** as the plate is pressed on.
  The 0.60 × 45° lead-in at the mouth is what guides it.
- **The USB end's forward stop only exists once the plate is fitted.** It is
  still the window step, 0.20 over the head top, acting through head → SD
  socket → expansion PCB → B2B → PCB; the ring's far-end hooks (0.150) still
  catch first, so forward travel of the whole board is still **0.155**.
- **`check.py` group 5 is new — the plate fitting sweep.** The plate, boss and
  all, is stepped from 8.0 mm short of its seat to seated (8/6/4/2/1/0.5/0)
  against the pcb, head, card, FPC roll and header mocks at nominal and at all
  nine board play positions: 63 configurations, 0.0000 mm³ at nominal
  everywhere. The head's footprint stays inside the chamfer mouth aperture
  (COLLAR_WIN + 2·COLLAR_WIN_CHAMFER = 9.80) at every play position, margin
  ≥ 0.700. The only non-zero cells are the Ø7.84 barrel against the Ø8.25
  bore's 0.205 radial when the head is *carried rigidly* to a Y ± 0.20,
  X ± 0.15 extreme (0.250 diagonal): ≤ 0.32 mm³, and per §9 C.9 the head is
  not carried rigidly — it hangs on its flex and the bore recentres it.

### Open against this contract
Nothing fails; `check.py` passes with no warnings. The collar's 20.8 mm bridge
is no longer a process risk (there is no bridge), so the remaining ones are the
root strip's torsional softness (preload only) and the assumed header geometry.
