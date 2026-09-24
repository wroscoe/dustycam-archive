# puckcase v1 — XIAO ESP32S3 Sense camera case that plugs into the power puck

Contract 2026-09-13 (awaiting approval). Sketch: `sketch_v1.png` / `sketch_v1.py`
(drawing only, not the model).

A camera-only box with the power puck's face (47.21 × 80.80, R 6 corners, 2.4
walls) and a puck front-plate lip on its back, so it presses into the puck
tube's front mouth in place of the puck's plain front plate — no glue. The
XIAO sits at the top of the face, lens forward and centred, under an eave
that the ring's top wall forms by running 8 mm past the front plate. The
puck's LOAD lead is soldered bare to the XIAO's BAT pads, runs under the
board and out a slot in the bottom wall, loops under the two boxes and
enters the puck through its own bottom LOAD slot to the charger's JST-PH.
Sealed: no USB/SD opening, no buttons, no vents, no mounting feature.

## Frame

mm. Puck-local convention: X 0 at the −X outer face → 47.21; Y 0 at the
bottom outer face → 80.80 (up); Z 0 at the camera case's outer FRONT face,
+Z toward the puck. The puck tube's front mouth face sits at Z_BACK; the
puck's own frame is ours shifted by Z_BACK − 2.40.

Board frame (vendor STEP, `../../ref/xiao/`): origin base-PCB bottom-left,
+x along the long edge from the USB-C end, z = 0 PCB bottom, lens +z.
Placed: board x → case −Y (USB end UP), board y → case +X, board z → case
−Z (lens forward). Board origin at case (15.355, 74.79, 17.36).

## Purchased parts

| Part | Geometry | Confidence |
|---|---|---|
| Seeed XIAO ESP32S3 Sense | `../../ref/xiao/amz-xiao-esp32s3-sense.step`; PCB 20.95 × 17.78 × 1.25 r1.906; stack top 13.96; lens axis (3.53, 8.25), barrel Ø7.84 to z 12.2 then Ø6.0; card tip x −3.11 at z 6.85..8.5; USB shell x −1.53..5.77; RST/BOOT at y 2.16..3.76 / 14.01..15.61 z < 1.98; U.FL (17.73..20.73, 2.61..5.71); BAT +/− pads on the flat underside near the USB end | vendor (sarg part `seeed-xiao-esp32s3-sense`) |
| Board-pocket fit | 0.5/side lateral: the case Wade printed (`~/Downloads/xiao-sense-case-v48-petg-*.stl`, walls 1.6) has an 18.80 pocket for the 17.78 PCB and "fits really well"; X play 0.75 (tripod-case recipe, verified vs the vendor STEP with tilt insertion) | measured from the printed STL / family |
| Power puck tube + front lip | `hardware/power_puck/caselib.py`: OUT 47.21 × 80.80 R6, WALL 2.4, LIP_WALL 1.6, LIP_GAP 0.15, LIP_ENG 7.5, 6 crush ribs 0.25 proud × 6.4 tall, LEADIN 0.6 | same source, imported |
| LOAD lead | 2 × 26–28 AWG, pair envelope 3.4 × 1.7; JST-PH plug at the puck end, bare at the XIAO end; ≥ 150 long | estimated |
| Flex antenna (XIAO kit) | 25 × 12 × 1.5 flag on a Ø1.1 pigtail, adhesive back | estimated (photo) |
| 4 × M2 × 8 pan-head self-tapping | head Ø4 × 1.5 | catalogue |

## Parameters

```
OUT_W, OUT_H, WALL, R_OUT = 47.21, 80.80, 2.40, 6.00      # power_puck/caselib
CX = 23.605
PLATE_T = 2.40                # front plate, Z 0..2.40  (outer face on the bed)
LENS_GAP = 1.00               # plate inner face to the lens tip
Z_B0 = 2.40 + 1.00 + 13.96 = 17.36      # PCB bottom (board z = 0)
X_B0 = CX - 8.25 = 15.355     # lens axis on CX
Y_B0 = 78.40 - 3.61 = 74.79   # card tip 0.50 off the top wall's inner face
POCKET_GAP = 0.50             # per side, lateral (board y)
WIRE_GAP = 3.00               # PCB underside to the back plate: solder + lead
Z_PLATE = 20.36               # back plate front face = ring back mouth
BACK_T = 4.00 ; Z_BACK = 24.36                          # puck tube mouth face
PUCK_LIP: Z 24.36..31.86, LIP rect, 6 ribs — identical to puck front_plate()
EAVE = 8.00                   # top wall runs Z -8.00..2.40 ; drip groove 1.0 w × 0.8 d, 1.5 behind the edge
FRONT_LIP = 6.00              # Z 2.40..8.40, LIP_WALL 1.6, gap 0.15, 6 ribs 4.9 tall, 0.6 lead-in
BAY_T, BAY_Z0 = 1.60, 9.00    # bay walls, Z 9.00..20.36, faces at board y -0.50 / 18.28
LEDGE_REACH = 1.45            # from the bay wall face (0.95 under the PCB edge), Z 17.36..20.36
BLOCKS: board x -3.61..-0.40, y -0.50..1.90 (mirror 17.78), Z 12.00..20.36
STOP_RIB: board x 21.30..22.50, y -0.50..3.50 (mirror), Z 13.73..20.36
HOOKS:    board x 20.00..22.50, y -0.50..2.00 (mirror), Z 13.73..15.91  (0.20 over the PCB top)
POSTS (front plate): board x -0.10..2.50, y -0.20..1.80 (mirror), Z 2.40..16.01 (0.10 over the PCB top)
LENS_HOLE = Ø7.50 at (CX, 71.26), 0.6 × 45° chamfer on the outer face
BOSS_D, BOSS_Z0, BOSS_BORE = 5.50, 15.86, 2.20 ; centres 6.50 in from both outer faces, corner-filled
PILOT_D, PILOT_DEPTH = 1.70, 3.40                          # blind, from the back plate's front face
CORD_SLOT = 4.50 × 3.00 r1.5, X 13.0, Z 16.86..19.86, through the bottom wall
TIE_POST = Ø4.0 at (13.0, 9.0), Z 14.36..20.36
EFOOT = 0.40                  # elephant-foot chamfer on every bed perimeter
```

Derived: PCB spans X 15.355..33.135, Y 53.84..74.79; PCB top Z 16.11;
expansion board Z 11.93..13.18; camera head front Z 7.06; lens tip Z 3.40.
Bay walls X 13.255..14.855 and 33.635..35.235, Y 52.29..78.40. Overall
camera case body 47.21 × 80.80 × 24.36 plus the 8.0 eave in front and the
7.5 lip behind; puck + case = 60.8 deep.

## Parts (3 printed, 4 screws)

| Part | Job | Support / locate / retain | Print |
|---|---|---|---|
| **front_plate** | Weather face: flat 2.4 plate, Ø7.5 lens hole, 6.0 lip with 6 crush ribs into the ring's front mouth, two 13.6-tall posts that land on the PCB's USB-end corners. Top edge follows the ring's inner outline (it sits inside the eave), sides and bottom overlap the ring's mouth face. | Located by the lip; retained by rib crush (friction, like the puck). | outer face down, posts + lip up. No supports. |
| **ring** | Body: 2.4 walls, Z 2.4..20.36. Top wall continues 8 forward as the eave (drip groove underneath). Board bay hanging from the top wall: two bay walls with ledges (PCB rests on them 3.0 above the plate), two corner blocks (stop the USB edge), two stop-rib segments with hooks at the far end. Four screw bosses with corner fills. Cord slot in the bottom wall, tie post beside it. | Screwed to the back plate (4 × M2 from the front mouth); its bay locates the board in X/Y and holds it down at the far end. | standing on its back mouth, eave up. Bay walls, blocks, ribs, bosses, post all rise from the bed; hook undersides are 1.35 mm overhangs; the slot is a 4.5 bridge. |
| **back_plate** | Coupling plate: 4.0 flat plate, puck front-plate lip on its back (identical to `power_puck.front_plate`'s lip, 6 ribs), 4 blind M2 pilots on its front. Its front face is the floor the lead runs along; its back face is the puck battery's stop, as the puck's plate was. | Pressed into the puck tube (friction, puck recipe); carries the ring by 4 screws. | front face down, lip up. No supports. |
| 4 × M2 × 8 | ring → back plate | 4.5 in the boss + 3.4 in the plate | |

Per component: **XIAO** — supported by the ledges (PCB long edges) and stopped by the corner blocks (USB edge) and the stop ribs (far edge); located 0.5/side, 0.75 along; retained toward the front by the two far-end hooks (0.2 over) and the two front-plate posts (0.1 over). In: tilt ≤ 10°, far edge under the hooks, drop the USB end between the blocks. Out: reverse, with the front plate off. **Lead** — soldered to BAT pads, lies in the 3.0 gap under the PCB, runs down the plate face, one turn round the tie post (or a zip tie to it), out the cord slot; sealed with silicone by hand. **Antenna** — sticks to the plate face below the bay (free zone ≈ 40 × 45 × 15). **Card** — inserted before the board goes in (sealed case).

## Assembly order

1. Solder the LOAD lead's bare end to BAT+ / BAT− under the XIAO. Fit the microSD and the antenna pigtail.
2. Screw the ring to the back plate: 4 × M2 × 8 down through the bosses from the front mouth.
3. Feed the lead out through the cord slot from inside; one turn round the tie post.
4. Board in: tilted, far edge under the hooks, USB end down between the corner blocks. Stick the antenna to the plate face below the bay.
5. Press the front plate on (posts land on the PCB corners, lens in the hole).
6. Puck: pull its back cup, pass the lead in through the puck's bottom LOAD slot, plug the JST-PH into the charger's LOAD socket, press the back cup on. Remove the puck's plain front plate.
7. Press the camera case's lip into the puck tube's front mouth. Both bottom faces flush; the lead loops under the seam. Silicone both cord exits.

Service: pull the front plate to reach the board; pull the whole camera case off the puck to reach the battery. Nothing needs the back plate unscrewed.

## Checks (`check.py`, fail-closed, all pairs from labelled occurrences)

- Printable parts: exactly one valid solid each; bounds as above.
- Interference: front_plate / ring / back_plate vs the vendor XIAO STEP (per-solid placement) = 0 at nominal and at the pocket extremes (X ±0.5, Y +0.35/−0.4); vs the lead and antenna envelopes = 0; ring vs back_plate = 0 (screws are the only contact).
- Designed crush only: front_plate ∩ ring = 6 ribs; back_plate ∩ puck tube (imported from `power_puck/caselib.tube()`) = 6 ribs, same volume as puck front_plate ∩ tube (15.44 mm³).
- Board retention: hook gap 0.20 over the PCB top, post gap 0.10, ledge overlap 0.95, X play 0.75; tilt insertion 6/8/10° = 0; posts' landing area on the PCB > 1 mm² each.
- Clearances: lens tip to the plate inner face 1.0; lens barrel to the hole wall ≥ 0.5 laterally at the extremes; card tip to the top wall 0.5; buttons to the blocks/posts ≥ 0.3; expansion board to the stop ribs ≥ 0.5; screw head to the front lip nose ≥ 7.
- Eave: 8.0 proud, brow angle from the lens axis ≈ 42° (> OV3660 half-FOV, report).
- Print: no face below 45° except the listed 1.35 hook overhang and the 4.5 slot bridge; min wall 1.6.

## Hardest interface / coupon

The board bay (ledges + hooks + posts at 0.5/side). Offer a **bay coupon**:
the ring cut at Y = 48 (top 33 mm of the ring, ~15 min) plus the front plate
cut the same way, to test tilt insertion, the 0.2 hook gap and the posts
with the real board before the full print. The puck lip is the puck's own
unprinted fit — when the puck's plates get printed, this plate is a third
sample of the same lip.

## Assumptions and open items

- Lens hole is open (no window). Water reaching the lens is only kept off by the eave; an acrylic disc recess can be added to the front plate later.
- No vents: expect condensation outdoors; a Gore-type patch on the back plate is the usual fix.
- Antenna and lead envelopes are estimates; BAT pad positions are not in the vendor STEP (underside is modelled flat), hence the uniform 3.0 gap.
- Friction lips both ends (puck recipe): the case-to-puck joint is rib crush only, like the puck's own plates.
