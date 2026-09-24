# puckcase v3 — drop-in camera holder

Status: **v4 built and checked** (§16, `v4case.py`, `check_v4.py`, 2026-09-15) —
Wade's simplification of the v3 case. §15 (ring + notched walls), §13, §4–§5 superseded.
Nothing in `puckcase_lib.py` reflects v3 yet. v2.4
(`DESIGN_v2.md`, `README.md`) is the last built revision. Sources for this
plan: the user's sketch and bench photos of 2026-09-15
(`/hd2/temp_data/v4kshot/v4k-20260915-14{3510,3523,4221,4844}-preview.jpg`),
the measured board envelope `ref/tripodcase/xiao_board_ref.py` (vendor STEP),
and the v2.4 numbers in `puckcase_lib.py`.

## 1. What changed on the bench

1. **The board has no pin headers** (photo 144221: bare castellated pads on
   the back). Everything that made the v2 bay complicated — the 9.0 back gap,
   "nothing may bear on the back along the long edges", the hooks, centre
   ledge, pillar snap tongues, expansion-edge rails, the tilt-in insertion —
   was there for headers this board does not have. The PCB back is flat again.
2. **The v2.4 bay cannot be loaded.** The head + rolled flex + card stack has
   to swing in at 13° past features on three sides; the user could not get the
   camera in.
3. **The board is now USB-end DOWN.** The USB-C shell (and the microSD card,
   which pokes out past the USB end) point into the empty lower body of the
   cup. Because the camera head sits at the USB end of the XIAO Sense
   (board x −0.47..7.53, lens axis x 3.53), the lens moves down the case with
   it — see §4.

## 2. Concept (the user's sketch)

Five printed parts instead of three. The board no longer touches the ring.

| Part | Job | Sketch label |
|---|---|---|
| **holder** (new) | C-channel the board slides into from its open bottom end, far end first. Front face carries the lens window; two side legs with grip ribs; two small rear **lips** at the open side of the C; closed **top end wall** is the board's +Y stop. Two outward **ears** hang it in the ring. | "camera holder", "lips", "ribs to grip", "lense" |
| **backing plate** (new) | 1.2 sheet slid up behind the PCB, between the PCB back and the lips, with crush ribs on its back so the board is pressed forward against the holder's lens datum. | "plate" |
| **ring** (simplified) | The puck outline, eave, screw bosses, cord slot, tie post as v2.4. Two plain internal walls, each with a **notch** at its front end that the holder's ears drop into, and a small **ledge** under each bottom corner of the PCB as the positive −Y stop. Everything else in the v2.4 bay is deleted. | "back cup", "slot to fit camera holder" |
| **front plate** | As v2.4 minus the head window boss; gains two short posts that land on the ears so the holder cannot lift. | — |
| **back plate** | Unchanged (puck coupling). | — |

Assembly direction: board **+Y** into the holder, plate **+Y** behind it,
holder **+Z** (front to back) into the ring's notches, front plate **+Z** on.

### Why (A) "holder drops into the cup" and not (B) "holder slides into a front cup"

A one-piece front cup (front face + walls) cannot be printed: with the front
face on the bed the 8 mm eave would be below the bed, and standing on the back
mouth the 42 × 76 front face is an unsupported roof. The printable form of (B)
is "the front plate carries rails and the holder slides into the plate" — it
buys ~0.2 of lens-to-hole alignment but puts 8 mm-tall rails on the plate,
forces the holder to be mated to the plate outside the ring, and leaves no
part to carry a positive stop under the board's open end. Under (A) the lens
tip has 0.75 radial allowance in the plate's Ø7.5 hole and the location stack
(§6) uses ~0.45 of it. (A) is the sketch; recommended.

## 3. Frame and board placement

Case frame unchanged: X 0..47.21, Y 0..80.80 (up), Z 0 outer front face, +Z
toward the puck. Board frame unchanged (x from the USB end, z = 0 PCB bottom,
lens +z).

Board → case is a proper rotation (det +1): **x̂ → +Y, ŷ → +X, ẑ → −Z**, so
`case = (X_B0 + y, Y_B0 + x, Z_B0 − z)`. Note ŷ → **+X** now (v2 had −X); the
bay is mirrored about CX relative to v2.

| Parameter | Value | Why |
|---|---|---|
| X_B0 | CX − 8.25 = **15.355** | lens axis (board y 8.25) stays on CX. PCB X 15.355..33.135 |
| Y_B0 | **53.45** | holder top end outer face at Y 76.50, 0.15 inside the front plate's lip prism (BAY_Y1 76.65) at every Z, so no stepped end. If the user wants the lens higher, the part of the holder behind Z 8.7 may run to Y 78.2 (Y_B0 55.15, lens 58.68) at the cost of a stepped end wall |
| Z_B0 | 2.40 + 1.00 + 13.96 = **17.36** | as v2: 1.0 lens gap behind the plate |
| BACK_GAP | 9.00 → **3.00** | plate 1.2 + lips 1.2 + 0.45 + fit. No pins to clear |
| Z_PLATE | 26.36 → **20.36** | ring 6 mm shorter |
| Z_BACK | **24.36**, puck lip to 31.86 | |
| BOARD_DROP | deleted | the card roof no longer exists (card is in the cup body) |

Resulting landmarks: lens (23.605, **56.98**); PCB Y 53.45..74.40; expansion
PCB far end Y 74.70; USB-C shell mouth Y 51.92; card tip Y 50.34; USB shell
Z 12.90..17.10; U.FL jack at X 17.97..21.07, Y 71.18..74.18, Z 14.86..16.11
(cable exits −X).

Eave/brow: `atan2(78.40 − 56.98, 3.40 + 8.00)` = **62°** (v2.4: 43°, check
floor 40°). The eave shades a narrower rain cone (20° from vertical vs 37°).
Option: EAVE 8 → 12 gives 54° / 29°; it prints standing, same as now.

## 4. The holder (board frame; case via the transform)

| Feature | Board frame | Case frame | Rationale |
|---|---|---|---|
| channel clear width | y −0.15..17.93 (18.08) | X 15.205..33.285 | 0.15/side on the 17.78 PCB, as `fits.LIP_GAP` |
| legs | 1.60 thick, y −1.75..−0.15 and 17.93..19.53; x **0.30..23.05**; z −2.55..12.05 | X 13.605..15.205 / 33.285..34.885, Y 53.75..76.50, Z 5.31..19.91 | legs stop 0.3 above the PCB's end edge so the ring ledges pass under them |
| grip ribs | 2 per leg on the inner face, 0.25 proud, at x 5 and x 18, z 0..1.25 only | | 0.10 crush/side, `fits.LIP_RIB_PROUD`; only over the base PCB edge (the expansion PCB is narrower, 0.5..17.28) |
| front face | x −1.00..23.05, y −1.75..19.53, 1.60 thick | Z 5.31..6.91 (option S: 3.41..5.01, see lens datum) | full length ties the legs; extends 0.53 past the head's overhang at the USB end |
| lens datum, **option S (recommended)** | face inner at z 12.35 bears on the **barrel shoulder** (barrel Ø7.84 → tip Ø6.0 at z 12.20), 0.15 sliding clearance; bore Ø6.40; **keyhole** 6.40 wide from the bore to the bottom edge | face Z 3.41..5.01, lens tip flush with the face outer, 1.0 to the plate | a round datum centred on the lens axis, ~12 mm² of bearing, 0.20 radial location of the lens to the holder. Depends on the vendor step at z 12.2 being a real shoulder — **measure with calipers first** |
| lens datum, option H (fallback) | face inner at z 10.45 over the 8 × 8 head top; bore Ø8.25; keyhole 8.25 wide | face Z 5.31..6.91 | only the head's two top corners bear (the keyhole removes the bottom two); location 0.20 via the barrel in the bore. Use if the shoulder isn't there |
| rear lips | 1.20 thick, z −2.55..−1.35, reaching 1.50 in (y −0.15..1.35 and 16.43..17.93), full leg length, 0.6 × 45° entry chamfer at x 0.30 | Z 18.71..19.91 | the "small lip at the unjoined part" |
| top end wall | x 21.45..23.05, full C profile | Y 74.90..76.50 | +Y stop on the expansion PCB overhang (x 21.25): 0.20; base PCB 0.50. Ø2.0 push-out hole at z −0.75 behind the plate |
| ears | 2, one per leg outer face: 2.10 out (x-width 6.00 at x 0.50..6.50), from the face outer to z 5.06 | X 11.50..13.605 / 34.885..36.99, Y 53.95..59.95, Z (face outer)..10.30 | hang in the ring notches; seat face at Z 10.30; sit beside the lens so the datum and the seat are 3 mm apart |
| coax notch | through the −y leg, x 17.20..21.30, z 1.00..4.50 | Y 70.65..74.75, Z 12.86..16.36 | U.FL plug + cable out of the channel |
| print | **front face on the bed** (outer face down). Legs, ears, end wall vertical; the lips are 1.5 inward overhangs at the top → 45° under-chamfer; keyhole and bore are vertical cuts | | no supports, no brim; the datum face is the top of the first solid layers — flat |

Bounding box (option S): X 11.50..36.99, Y 52.45..76.50, Z 3.41..19.91.
Volume ≈ 5 cm³.

Insertion into the holder (straight +x slide, no tilt): the stack under the
face is z ≤ 10.30 everywhere except the barrel/tip, which ride in the
keyhole; card z 6.85..8.50, flex roll 8.75, FPC socket 7.43 all clear the face
by ≥ 1.5 (S) / ≥ 1.55 (H). USB-C shell y 4.41..13.35 and buttons clear the
legs. The lips are behind the PCB plane (z < −1.35) so nothing on the board
meets them.

## 5. Backing plate

| Item | Value |
|---|---|
| size | 17.90 (y 0.09..17.87) × 1.20 (z −1.30..−0.10 nominal) × 19.50 (x 1.00..20.50) |
| ribs | 2 on the back face along x, 0.25 proud, at y 3 and y 15 (over the lips) |
| fit | lips inner face at z −1.35; plate back at −1.30 → 0.05 gap, ribs give 0.20 net crush **and** the forward preload that seats the shoulder/head on the face |
| stack tolerance | the vendor stack z 0 → 12.20 (shoulder) may be off by ±0.3 on the real part. The ribs absorb +0.3 (fully flattened, legs spring the rest); −0.3 leaves 0.25 play in z, acceptable (lens gap 1.0 ± 0.25). Coupon-verified |
| entry | 0.6 × 45° chamfer on the leading edge; no finger tab — removal via the Ø2 hole in the end wall |
| print | flat, back face (ribs) up |

Deletion option (II): give the legs a front lip too (y 0..1.0, z 1.40..3.50,
under the expansion PCB overhang, clear of the buttons at y ≥ 2.16) and the
holder becomes a card guide; the plate goes away, but the board is then
located by its PCB, not by the lens, and nothing presses the sensor forward.
Not recommended; listed because it is one part fewer.

## 6. Ring changes

| Feature | Case frame | Notes |
|---|---|---|
| internal walls | X 11.905..13.505 and 34.985..36.585, Y 50.00..78.40, Z 8.70..20.36 | 0.10 clear of the holder legs; tied to the top wall; start 0.30 behind the plate lip nose as v2.4 |
| ear notches | through each wall, Y 53.85..60.05 (6.20), Z 8.70..10.30 | 0.10/side on the ears in Y; floor at 10.30 is the holder's Z datum |
| ledges | from each wall inward to X 17.355 / from 31.135, Y 52.25..53.25, Z 16.11..18.96 | under the PCB's bottom corners (board y 0..2.0 and 15.78..17.78, z −1.6..1.25): stop the PCB **and** the plate from sliding out, 0.20 below the PCB end at nominal. Stay outside the USB plug overmold (assumed ≤ 12.5 wide, y 2.6..15.1) and the card (y ≥ 2.48). 45° gable on the underside or accept 2 × 3.9 mm² of overhang |
| deleted | far-end wall, stop ribs, hooks, centre ledge, tongue root strip, both snap tongues, side rails, wire notch (the bay is open to the cup body now), BOARD_DROP | |
| kept | outline, eave + drip groove, front-mouth lead-in, 4 bosses (9.0) + M2 × 12, cord slot, tie post | ring is 6 mm shorter: Z 2.40..20.36 |
| print | on the back mouth as before; the notches open upward, the ledges are the only new overhang | |

Front plate: delete `_head_window_boss`; add two posts X 11.60..13.50 /
35.00..36.90, Y 54.45..59.45, Z 2.40..(ear top − 0.10). Lens hole Ø7.5 moves
to Y 56.98. Back plate: no change.

## 7. Location stack, lens tip to plate hole (radial)

| Link | Allowance |
|---|---|
| lens in holder bore (S) | 0.20 |
| holder ear in notch (Y) / leg between walls (X) | 0.10 / 0.10 |
| plate lip in ring mouth (crush ribs) | 0.10 |
| **total** | **0.45** of the 0.75 available in the Ø7.5 hole |

## 8. Power, card, antenna

- **Power (assumption A1, recommended):** JST-PH LOAD lead → USB-C pigtail
  plugged into the board inside the cup. Plug envelope assumed 12.5 × 6.5 ×
  20 overmold: Y 39..52, Z 11.7..18.3, inside the ring, 2.0 clear of the back
  plate. The user must confirm the plug width and length they will use.
- **Power (alternative A2):** solder the LOAD lead to the 5V/GND castellations
  on the **back** at the USB end, notch the backing plate's corner (x 1..7,
  y 15..17.9) and run the wire down between the PCB back and the lip
  (1.35 mm of room — 26 AWG only).
- **microSD:** fitted before the board goes into the holder; reachable
  afterwards only by pulling the front plate and unplugging USB.
- **Antenna:** flag on the back plate face at Y 15..40 as v2 (the plug sits
  in front of it, Z ≤ 18.3 vs the plate at 20.36). Coax leaves the holder
  through the −X leg notch at Y 70.65..74.75 and runs down the −X corridor.

## 9. Assembly order

1. Card in. U.FL pigtail on. (A2 only: solder the lead now.)
2. Board into the holder from the bottom, far end first, straight slide until
   the expansion PCB meets the end wall.
3. Backing plate up behind the board until flush with the ledge line (its
   bottom edge at board x 1.0).
4. Ring screwed to the back plate (4 × M2 × 12, as v2).
5. Holder into the ring from the front: ears into the two notches, legs
   between the walls, the board's bottom corners landing 0.2 above the
   ledges. Coax out through the leg notch and down the −X corridor; flag on
   the back plate.
6. USB-C pigtail in from below; lead down to the cord slot, one turn round
   the tie post.
7. Front plate on: lens through the Ø7.5 hole, posts land on the ears.
8. Puck coupling as v2 (steps 6–7 of the v2.4 order).

Removal: front plate off, holder lifts straight out.

## 10. Verification

Carried over from `check.py`: valid single solids + bounds per printed part
(now 5); bound-overlapping pair intersections of every labelled occurrence;
board/head/card against all printed parts at nominal and at every stop-face
play extreme; the front-plate fitting sweep (posts and lens hole now);
brow angle, screw stack, driver access; 45° overhang audit against a **new
v3 baseline per part**; 0.30-clearance proofs by mock inflation.

New groups (all fail-closed):

1. **Straight-slide insertion sweep**: the full board stack (PCB, expansion,
   head, barrel, tip, card, USB shell, buttons, jack) stepped along +x from
   x −25 to seated in ≥ 12 steps against the holder — 0 mm³ at every step.
2. **Plate sweep**: the backing plate stepped +x from below against the
   holder and board — contact only at the ribs (report the crush volume).
3. **Holder drop-in sweep**: holder + board + plate stepped +Z into the
   ring — 0 except the ear/notch floor landing; ledges pass 0.5 under the
   legs.
4. **Positive-retention audit**: for board, plate and holder, name the
   feature that blocks each of ±X, ±Y, ±Z. Friction does not count.
5. **USB plug envelope** (assumed 12.5 × 6.5 × 20) vs ring, holder, ledges,
   antenna flag, back plate.
6. **Lens location arithmetic** (§7) recomputed from the built parameters,
   must be ≤ 0.75.
7. **Lens datum bearing area** (S: annulus minus keyhole; H: two corner
   triangles) ≥ 6 mm².

Deleted groups: tilt insertion (all angles), tongue cam/strain/snap force,
card roof, far-edge groove arithmetic, head-window-boss siting.

### Coupons (print before the full set)

1. **Holder + backing plate** — the whole holder is 25 × 24 × 16, ~15 min.
   Tests: channel width/ribs, keyhole clearance on the real barrel, shoulder
   (S) or head (H) seating, lip/plate crush, plate insertion force, coax
   notch. Measure lens tip protrusion vs the design value.
2. **Ring bay coupon** — a 2.4 slab carrying the two internal walls with
   notches and ledges, plus a front-plate slab with the two posts and the
   lens hole; drop the holder from coupon 1 in. Tests: ear/notch fit,
   Z seat, post landing, lens-hole concentricity.

## 11. Open questions for the user

1. **Lens datum**: does the real barrel have a shoulder where the vendor
   model steps from Ø7.84 to Ø6.0 at z 12.2? Caliper the barrel and tip
   diameters and the step height on the bench board. S vs H follows from
   that.
2. **Headers**: confirm no headers will ever be fitted to this board (the
   plate needs the flat back).
3. **Power**: USB-C pigtail inside the cup (A1) or soldered LOAD lead (A2)?
   If A1, which plug — its overmold width and length set the ledge and the
   free length below the holder.
4. **Lens height**: 56.98 (simple holder) or 58.68 (stepped end wall), or
   something else? Both are ~10 mm lower than v2.4; is a longer eave wanted?
5. **Backing plate**: keep it (sensor pressed forward, the sketch) or take
   option II and drop it?
6. Is the holder meant to come out again in service (yes as planned), or may
   it be glued into the ring once the fit is proven?

## 12. Confidence

Board envelope: vendor STEP, corroborated by the v2 coupon print except for
the lens tip/shoulder (unverified). Holder and plate fits: assumed from
`fits.py` values that the puck lip and the v2 rails were built with, not yet
printed. USB plug: assumed. Completion level of this document: **plan**; no
geometry exists.

## 13. As built, 2026-09-15 — holder + backing block (`v3lib.py`)

User decisions that changed §4–§5: **one holder must fit the XIAO with or
without pin headers**, and the lens has **no shoulder** — its largest round
part is Ø6.95, then the square sensor plate. So option H is the datum, and
the header lanes (board y −1.0..1.54 / 16.24..18.78, z −8.5..0) must be
empty at every x the headers travel through while the board slides in.
That kills the corner lips / rear bars of §4: anything behind the PCB in a
header lane below x 19.365 is hit during insertion (`check_v3.py` group 2
caught it at 3.6–5.0 mm³ per body). Built geometry, board frame:

| Feature | Value | Why |
|---|---|---|
| legs, front zone | inner face y −0.15 / 17.93 from z **0.35** to the face; 2 grip ribs per leg at x 5 and 17, z 0.35..1.30, 0.25 proud, 45° lead-in on the −x end | 0.15 off the PCB edge, 0.10 crush/side; zone starts 0.35 above the header body top |
| legs, rear zone | inner face y −1.35 / 19.13 from z −10.05 to 0.35; outer face y −2.95 / 20.73 throughout | 0.35 off the header body; legs are 2.8 thick in the front zone, 1.6 in the rear |
| **rear lips** | full length x 0..21.45, y −1.35..2.59 (mirror), z **−10.05..−8.85** | 0.35 **below the pin tails** (z −8.5); reach 0.70 under the block's edges |
| front face | x −1.0..23.05, z 10.45..12.05; keyhole Ø7.35 at (3.53, 8.25) slotted to the open end | bears on the 8.3 sq sensor plate with 0.15 slide clearance; 17.2 mm² of bearing; barrel 0.20 radial |
| end wall | x 21.45..23.05, full profile, Ø2.5 push-out hole at (8.89, −4.35) | 0.20 to the expansion PCB; the bed face, 0.40 elephant-foot chamfer |
| ears | x 0.5..6.5 (+45° gable to 8.6), 2.10 out, z 7.06..14.86 | seat = case Z 10.30, top = case Z 2.50 (0.10 under the front plate, so the plate needs **no posts**); ring notch must be ≥ 8.3 long |
| coax window | −y leg, x 17.2..21.3, z 1.0..4.5, gabled to a ridge at x 15.45 | U.FL plug + cable |
| **backing block** | x 0..21.20, y 1.89..15.89, z **−8.70..0**; pocket from the back leaving 1.6 walls; 2 ribs on the rims at y 2.69 / 15.09, **x 0.5..8.0 only**, 0.25 proud; 0.6 lead-in on the leading edge | between the header lanes (0.35); spans PCB back to lips; ribs sit under the sensor plate and crush only over the last 8 mm of travel |
| holder bbox / volume | (−1.0, −5.05, −10.05)–(23.05, 22.83, 14.86); 3.9 cm³ | |
| block bbox / volume | (0, 1.89, −8.95)–(21.20, 15.89, 0); 1.2 cm³ | |
| print | holder **standing on its end wall** (x 23.05 on the bed, open end up), no supports; block flat, ribs up | every fin vertical; only 45° faces off the bed |

Consequence for the ring (§6 still to build): the holder is 23.68 wide
(X 12.6..36.3 with X_B0 15.355), its ears reach X 10.5 / 38.4, and it is
22.1 deep — Z 5.31..27.41 — so **BACK_GAP stays ≈ 9–10 and Z_PLATE ≈ 27.5**,
not the 20.36 of §3 (the pin tails needed that depth anyway). The ledge under
the PCB's bottom corners must sit in front of the header body (z 0.15..1.25
only) and outside the plug overmold: board y 0..1.8 at x −1.2..−0.2.

`check_v3.py` (38 assertions, `checks_v3.md`): valid single solids and
bounds; straight-slide insertion sweep of the full stack with and without
headers, 14 steps, 0 mm³ against the rib-less holder; rib crush 0.63 mm³ on
the PCB, 0 on anything else; block sweep 0 mm³, rib crush 0.12 mm³ on the
lips; inflation proofs for the sensor plate (0.14), barrel (0.19),
expansion end (0.19), header bodies (0.33), pins (0.30), USB shell / card /
flex roll (0.50), U.FL jack (0.30), a 12.5 × 6.5 × 20 USB plug (0.30);
bearing area 17.2 mm²; lens 1.91 proud of the face; retention audit (the
board's −x stop and the block's −x stop are **not on the holder** — friction
0.10 crush until the ring ledge exists); overhang audit 0 mm² steeper than
45° off the bed in both print orientations.

Completion level: **print-ready candidate**, unprinted. Coupon = these two
parts as they are (holder ≈ 15 min).

## 14. v3.1 — the C-channel as Wade drew it (2026-09-15, `review_v3/*_rev1.png`)

Wade marked up sections A, A2 and E of §13: "the camera holder is just a
C shaped unclosed ring ... what you drew was too complex and the friction
fit with ribs is going to be fine. Also the outside of the header lines up
with the outside of the board so we can make the holder more snug." So:

| Feature | Value (board frame) | Change from §13 |
|---|---|---|
| header envelope | body y **0..2.54** (flush with the PCB edge), pins at y 1.27, tails to z −8.5 | was overhanging 1.0 |
| legs | 2.0 thick, inner face y −0.15 / 17.93 **straight from the face to the lip**; outer y −2.15 / 19.93 (22.08 wide) | no rear zone, no step |
| grip ribs | 2 per leg, x 5 and 17, z **0.20..1.30**, 0.25 proud, 45° ramps both ends | lifted 0.2 so a flush header body clears their underside |
| lips | at the bottom of each leg, full length x 0..21.45, reach **0.75 in** (y −0.15..0.75), z **−3.85..−2.65** = 0.15 under the header body, 0.20 off the pin tails | were below the pin tails at −8.85 |
| backing block | **deleted** | |
| end wall | x 21.45..23.05, full C profile, no push-out hole | |
| face, keyhole, ears, coax window | unchanged | |
| depth / volume | 15.90 (z −3.85..12.05) / 2.7 cm³ | was 22.10 / 3.9 |
| `holder_snug.step.py` | same factory with the lip 0.15 under the PCB back (z −1.35..−0.15), 13.40 deep — for a board that will never get headers | new |

Retention: +x end wall; ±y legs and ribs; +z face on the sensor plate; −z
lips (header board 0.15 play, bare board 2.65 play held by the ribs' grip, or
use the snug variant); −x still nothing on the holder (ring ledge later).

`check_v3.py` (53 assertions, both variants): single valid solid and bounds;
straight-slide insertion sweep with and without headers, 14 steps, 0 mm³;
rib crush 0.5–0.6 mm³ on the PCB only; inflation proofs — sensor plate 0.14,
barrel 0.19, expansion end 0.19, USB shell / card / flex roll 0.50, U.FL and
buttons 0.30, header bodies 0.14, pins 0.19, USB plug 0.30; bearing 17 mm²;
lens 1.91 proud; 0 mm² steeper than 45° off the bed standing on the end wall.

Ring consequence: holder 22.08 wide (X 13.2..35.3 with X_B0 15.355), ears
to X 11.1 / 37.4, 15.9 deep (Z 5.31..21.21); a header board's pin tails
still reach Z 25.86, so BACK_GAP stays ≈ 9 if headers are to be supported.

## 15. Case around the holder, as built (`v3case.py`, 2026-09-15)

Board → case: `Plane(origin=(15.355, 53.45, 17.36), x_dir=(0,1,0), z_dir=(0,0,-1))`
(x̂ → +Y, ŷ → +X, ẑ → −Z). Lens at (23.605, 56.98); brow 62°. **Z_PLATE stays
26.36** (header pin tails reach Z 25.86, 0.5 off the back plate), so the
bosses, M2 × 12, cord slot, tie post and the whole back plate are v2.4's.

| Ring feature | Case frame | Notes |
|---|---|---|
| internal walls | X 11.455..13.055 and 35.435..37.035, Y 50.0..78.4, Z 8.70..26.36 | 0.15 off the holder's legs (X 13.205 / 35.285); tied to the top wall |
| ear notches | through each wall, Y 53.85..62.15, Z 8.70..10.30 | ears Y 53.95..62.05 (incl. the 45° gable); floor at 10.30 = ear seat; ear top at Z 2.50 sits 0.10 under the plate — **no plate posts** |
| ledges | from each wall in to X 17.355 / 31.135, Y 52.25..53.25, Z 16.11..17.21 | under the PCB's bottom corners (board y 0..2 / 15.78..17.78, z 0.15..1.25): 0.20 below the PCB end, 0.15 in front of a flush header body, 0.6 clear of a 12.5 wide USB plug; 4.3 mm² overhang each |
| deleted | every v2.4 bay feature and the wire notch | the holder's bottom is open into the cup body |
| front plate | v2.4 lip + ribs; lens hole Ø7.5 at Y 56.98; **no head window boss** | |

`check_v3case.py` (CHECK PASSED): both new parts single valid solids; holder,
board and headers vs ring / front plate / back plate all 0 mm³; front plate ×
ring 11.72 mm³ = the six lip crush ribs, identical to v2.4; holder + board
drop-in sweep 10 × 1.5 mm forward, 0 mm³; holder's forward band inside the
lip prism (0.15 in Y); USB plug +0.30 clear of ledges and plate; PCB-to-ledge
0.20; lens tip to plate 1.00; pin tails 0.50 off the back plate; ring +Z-facing
area off the bed 12.2 mm² (v2.4 9.3; the two ledges add 8.6).

Review models: `case_v3.step` (all parts in place), `case_v3_exploded.step`
(plate 20 forward, holder + board 10 forward, back plate 12 back), both as
GLBs in `review_v31/` for imgmark's 3D viewer.

## 16. v4 — Wade's simplification (2026-09-15, `review_v31/*_rev*.png`)

His markups: merge the front plate and the ring into one **front cup**, drop
the drip lip so it prints face-down; the holder's top end slides into an
**angle slot** at the top of the front cup; the internal walls ("fork") go;
the **back cup just slides onto the front cup**; the holder prints from its
camera-plate face. Built as `v4case.py` + `v3lib.holder(ears=False, rail=True,
print_face="face")`:

| Part | What | Print |
|---|---|---|
| **front_cup** | outline 47.21 × 80.80, 2.4 face + 2.4 walls, 28.0 deep, Ø7.5 lens hole at (23.605, **56.33**), no eave; a 2.0 boss under the top wall (X 12.2..36.2, Z 2.4..23.0) carrying a **45° dovetail slot** (6.72 at the mouth, 12.02 at 2.65 deep) with 2 crush ribs per flank (0.10 net); **no posts** (removed 2026-09-15, §16.1); **rebate** 1.2 × 4.5 at the back rim; cord slot 4.5 × 3 in the bottom wall at Z 20..23 | face down, 0 mm² overhang off the bed (cord-slot roof 3.6 mm² bridge) |
| **holder_v4** | v3.1 C-channel without ears; **dovetail rail** on the end wall: 6.0 root, 2.3 tall, 10.6 top, Z 2.4..15.8; lips with a 45° underside; face lands ON the cup's inner face (Z_B0 14.45, lens tip 0.49 inside the hole) | face down, 1.1 mm² |
| **back_plate_v4** | 4.5 thick, outline inset 1.35 (R 4.65), 6 edge crush ribs, drops into the rebate flush with the rim; puck lip on the back as v2.4; no screws, no bosses | front face down, lip up, 0 mm² |

Deviation from the sketch: the "back cup that slides on" is a plate in a
rebate, not a lip on both faces — a plate with lips on both faces cannot be
printed flat. The holder is held in the dovetail by friction (ribs), as Wade
asked; nothing else stops it sliding back.

Unresolved reading: "add a little connector plate on the camera holder
directly behind the camera sensor. This is where it will stick to" — the
region behind the sensor plate is occupied by the SD card and socket, and any
fixed plate there would block the board sliding in. Built as: the holder's
face IS the plate that sits on the cup; if a glue pad or something else was
meant, say so.

Board → case: `Plane(origin=(15.355, 52.80, 14.45), x_dir=(0,1,0), z_dir=(0,0,-1))`.
`check_v4.py` (58 assertions, CHECK PASSED): single valid solids; holder /
board / headers vs cup and plate 0 mm³ (slot ribs measured apart: 2.24 mm³ =
4 × 0.10 crush); plate × cup = edge ribs only; holder slide-in along the slot
12 × 1.5 mm and plate press-on 6 × 1.5 mm, 0 mm³; rail-slot gaps (0.15 flank,
0.50 top, 0.15 end wall); USB plug +0.30 and
headers +0.30 clear; pin tails 0.55 off the plate; overhang audits above.



### 16.1 Posts removed; three grip-rib variants (2026-09-15)

Wade, on `review_v4/front_cup.glb` (comments 1 and 2): *"remove these posts"*
/ *"remove this post too"* — the two 2 × 1 board-stop posts on the cup's
inner front face are gone, and with them the notches they needed at the
holder face's bottom corners (`v3lib._front_face` no longer takes
`post_notches`). The cup's inner front face is now clear except the lens hole
and the slot boss, and **the holder's channel ribs are the board's only
retention**: nothing stops the board sliding back out of the channel but
friction, which is what Wade asked for ("the friction fit with ribs is going
to be fine"). Front cup 76 faces, one valid solid, 22 772 mm³.

Three rib sets for a fit trial, `v3lib.RIB_SETS`, selected by
`holder(ribs=...)`. Ribs sit on the leg inner faces over the PCB thickness
only (Z 0.20..1.30), 45° ramps both ends; all centres stay inside the base
PCB's straight edge (x 1.91..19.04, corner R 1.906). Channel is nominal
(SIDE_CLR 0.15 per side), so net crush = proud − 0.15.

| set | ribs | centres (board x) | length | proud | net crush / side | PCB interference | part |
|---|---|---|---|---|---|---|---|
| `std` | 2 per leg (4) | 5.0, 17.0 | 1.50 | 0.25 | **0.10** | 0.447 mm³ | `holder_v4` |
| `fine` | 4 per leg (8) | 4.0, 8.5, 13.0, 17.5 | 1.20 | 0.20 | **0.05** | 0.335 mm³ | `holder_v4_fine` |
| `firm` | 2 per leg (4) | 5.0, 17.0 | 1.50 | 0.32 | **0.17** | 0.713 mm³ | `holder_v4_firm` |

The rail, face, lips, end wall and coax window are identical across the
three, so all three seat in the same cup slot (checked: 0 mm³ against the cup
without its slot ribs) and all three print face down under 1.5 mm² overhang.


### 16.2 Camera glue plate — the module comes off the board (2026-09-15)

Wade: *"you didn't implement the camera backplate and instead you still have
the plate on the front holder that rests the camera lens in a dip … the
holder should be shaped so the camera sensor gets stuck to a plate on the
holder."* His drawings:

* `review_v31/v4k-20260915-202416-preview_rev1.png` — a photo of the real
  assembly with *"The plate for the camera. This is also the face that the
  holder will be printed from"* arrowed at the module's flat BACK, and a
  top view of the holder sketched as a rectangular FRAME whose one short side
  is hatched solid (*"top view of holder: camera plate"*), the opposite side
  carrying the *"angle to attach to front cup"*.
* `review_v31/case_2_Y_lens_rev1.png` — *"add a little connector plate on the
  camera holder directly behind the camera sensor. This is where it will
  stick to"*, drawn as a solid band spanning the holder.

The photo settles what the earlier note could not: **the camera is a flying
module on its flex, not a fixture on the board.** So it does not have to poke
through anything — its flat back is glued (VHB) to a plate on the holder and
the whole module stands in front of it.

| was (v4.0) | now (v4.2) |
|---|---|
| full-length face, board z 10.45..12.05, Ø7.35 keyhole + open lens slot | plate over the camera's footprint only, x −1.25..8.50, **solid** |
| head pressed against the face's underside (0.15 slide gap) | head's back **glued** to the plate's outer face at z 12.05, 68.9 mm² of glue area, ≥0.6 margin all round |
| lens through the keyhole, tip z 13.96 | head z 12.05..14.15, lens tip z **17.81** |
| rest of the holder's top closed by the face | **open** — the flex drops through to the FPC socket |
| legs to z 10.45, carried by the face | legs to z 12.05, so the frame's whole perimeter reaches the bed (no islands when printing plate-down) |

`v3lib`: `_front_face(plate=True)`, `PLATE_X0/PLATE_X1`, `GLUE_Z`,
`HEAD_G_Z0/Z1`, `LENS_G_Z1`, `camera_on_plate()`, and `board_mocks(head=False)`
— the head is no longer part of the board. `holder(rail=False)` still builds
the v3.1 keyhole face, so `check_v3.py` is untouched.

**Cost: the case is 3.85 mm deeper.** The lens now reaches 17.81 above the
board instead of 13.96, so with the tip still 0.49 inside the front wall the
board sits at `Z_B0` 18.30 (was 14.45) and everything behind it follows:
mouth 28.00 → **31.85**, rebate 23.50 → **27.35**, pin tails 26.80 (0.55 off
the plate). The dovetail slot is now **closed at Z 6.25** so the rail bottoms
out there — that hard stop, not the cup's front face, is what sets lens depth.
1.65 mm of that is recoverable: the plate no longer has to clear the camera
head, only the microSD card (top z 8.50), so `FACE_Z0` could drop 10.45 → 8.80.
Not done — it would change every v3.1 holder dimension too.

New checks: plate solid over the head; glue area and margins; head in front of
the plate; head clear of the cup's inner face (1.75) and of the board; rail
bottoms on the slot's closed end; and a 10-step board-insertion sweep under
the plate (0 mm³ against the ribless holder and the glued module).
