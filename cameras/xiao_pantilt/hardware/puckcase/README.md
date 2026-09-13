# puckcase v1

A sealed, camera-only case for the Seeed XIAO ESP32S3 Sense that presses into
the **power puck**'s front mouth in place of the puck's own front plate. Same
outline as the puck (47.21 × 80.80, R6, 2.4 walls), so the two boxes stack into
one 60.8 mm-deep brick. Lens forward and centred under an 8 mm eave; the puck's
LOAD lead is soldered to the XIAO's BAT pads and leaves through a slot in the
bottom wall. No USB/SD opening, no buttons, no vents, no mounting feature.

Contract: [`DESIGN.md`](DESIGN.md). Sketch: `sketch_v1.png`. Deviations from the
contract are listed at the bottom of this file and commented at their parameter
in `puckcase_lib.py`.

Frame: X 0..47.21, Y 0..80.80 (up), Z 0 at the outer front face, +Z toward the
puck. Everything is modelled in place — no part-local origins.

## Parts

| File | Job | Print orientation | Volume |
|---|---|---|---|
| `front_plate.step.py` → `front_plate.step` | Weather face: 2.4 plate, Ø7.5 lens hole (0.6 × 45° chamfer), 6.0 lip with 6 crush ribs into the ring's front mouth, two posts onto the PCB's USB-end corners | outer face on the bed (Z 0), posts + lip up. No supports | 10 912 mm³ |
| `ring.step.py` → `ring.step` | Body Z 2.4..20.36: 2.4 walls, top wall run 8.0 forward as the eave (drip groove underneath), board bay hanging from the top wall (2 bay walls + ledges, 2 corner blocks, 2 stop ribs with hooks), 4 screw bosses with corner fills, cord slot, tie post | standing on its back mouth (Z 20.36 on the bed), eave up. Hook undersides are 1.30 mm overhangs, the cord slot is a 4.5 mm bridge | 13 344 mm³ |
| `back_plate.step.py` → `back_plate.step` | Coupling plate: 4.0 flat plate, the power puck's own front-plate lip on its back (6 crush ribs, identical geometry), 4 blind Ø1.7 × 3.4 M2 pilots on its front | front face on the bed (Z 20.36), lip up. No supports | 17 787 mm³ |
| 4 × M2 × 8 pan head self-tapping | ring → back plate (4.5 in the boss, 3.4 in the plate) | purchased | — |

Bounding boxes: front_plate (0, 0, 0)–(47.210, 78.500, 16.010); ring
(0, 0, −8.000)–(47.210, 80.800, 20.360); back_plate
(0, 0, 20.360)–(47.210, 80.800, 31.860).

Review-only models (not printable, not exported to `.step` — they embed the
15 MB vendor board):

| File | What |
|---|---|
| `puckcase.step.py` | assembled view: 3 printed parts + the vendor XIAO + 4 screws |
| `fitcheck.step.py` | everything: printed parts, puck tube, vendor XIAO, board envelope, LOAD lead, antenna flag, screws. `check.py` imports its occurrence list |
| `snaps/puckcase_section.step.py` | half model, everything cut away for X > CX |
| `snaps/ring_bay_coupon.step.py` | DESIGN.md's bay coupon — the ring above Y = 48 |

`puckcase_lib.py` holds every parameter, the board→case transform and all the
builders. It **imports** `hardware/power_puck/caselib.py` + `fits.py` rather
than copying them, so the OUT/IN/LIP/BAY rectangles, radii, `LIP_ENG`,
`LIP_RIB_H`, the 6-rib layout and `edge_crush_rib` are literally the puck's.

## Assembly order

1. Solder the LOAD lead's bare end to BAT+ / BAT− under the XIAO. Fit the
   microSD card and the antenna pigtail (the case has no card slot).
2. Screw the ring to the back plate: 4 × M2 × 8 down through the bosses from
   the front mouth.
3. Feed the lead out through the cord slot from inside; one turn round the tie
   post.
4. Board in: tilted ≤ 10°, far edge under the hooks, USB end down between the
   corner blocks. Stick the antenna to the plate face below the bay.
5. Press the front plate on (posts land on the PCB corners, lens in the hole).
6. Puck: pull its back cup, pass the lead in through the puck's bottom LOAD
   slot, plug the JST-PH into the charger's LOAD socket, press the cup back on.
   Remove the puck's plain front plate.
7. Press the camera case's lip into the puck tube's front mouth. Both bottom
   faces flush. Silicone both cord exits.

Service: pull the front plate to reach the board; pull the whole camera case
off the puck to reach the battery.

## Build and check

All commands from this directory, with the CAD skill's interpreter:

```bash
PY=~/.claude/skills/cad/.venv/bin/python
CAD=~/.claude/skills/cad/scripts

# printable STEPs
$PY $CAD/gen front_plate.step.py ring.step.py back_plate.step.py --write

# review models (render packages only — no .step, they embed the vendor board)
$PY $CAD/gen puckcase.step.py fitcheck.step.py \
             snaps/puckcase_section.step.py snaps/ring_bay_coupon.step.py

# geometry soundness
for f in front_plate.step ring.step back_plate.step; do $PY $CAD/inspect validate $f; done

# fit / interference (fail-closed, ~50 s — it loads the 103-solid vendor STEP)
$PY check.py
```

`check.py` output is pasted in [`checks.md`](checks.md). It verifies: one valid
solid and the expected bounds per printed part; every bound-overlapping pair of
the 11 labelled occurrences intersected solid-by-solid (0 except the two
designed crushes and the 4 screws, which are mated into their own bosses and
pilots); the vendor XIAO against all three printed parts at nominal and at 8
pocket extremes; tilt insertion at 6/8/10°; the retention gaps; and the posts'
landing area on the PCB. It prints `CHECK PASSED` only if every group ran and
passed, and never maps an exception to 0.

Headline numbers: `back_plate × puck_tube = 15.4400 mm³`, exactly the puck's own
`front_plate ∩ tube` (the lip is the same part); `front_plate × ring =
11.4800 mm³`, 2.9 % under the height-scaled expectation for the same 6 ribs at
4.9 mm instead of 6.4 mm. Retention: hook 0.200 over the PCB top, post 0.100,
ledge overlap 0.950, play 0.750 along the board / 1.000 across, lens tip 1.000
off the plate's inner face, card tip 0.497 off the top wall, post landing area
2.635 mm² each.

## Snapshots (`snaps/`)

`asm_iso_front`, `asm_iso_back`, `asm_front` (assembly), `section_cx`
(half model at X = CX, showing the board, eave, lip stack, tie post and lead),
`front_plate_print`, `ring_print`, `back_plate_print` (each in print
orientation), `ring_bay` (the bay coupon: ledges, corner blocks, stop ribs,
hooks).

## Completion level

**Geometry builds / mechanically plausible prototype.** The three parts are
single valid solids with the contract's dimensions, they do not interfere with
the real vendor board at nominal or at either pocket extreme, and the board can
be tilted in. Nothing here has been printed or fitted to hardware. The puck lip
is unproven too — the puck's own plates have not been printed either, so this
plate is a third sample of an unvalidated press fit.

Print the **bay coupon** (`snaps/ring_bay_coupon.step.py`, ~15 min) plus the
front plate before committing to a full print: that is where the 0.5/side
pocket, the 0.20 hook gap and the posts are decided.

## Deviations from DESIGN.md

1. **Board y → case −X, not +X.** The contract's triple (x → −Y, y → +X,
   z → −Z) has determinant −1: it is a mirror, not a rigid placement, so it is
   not buildable. With "USB end up" and "lens forward" fixed, handedness forces
   y → −X. The lens is kept on CX (`LENS_HOLE` at (CX, 71.26) and
   `X_B0 = CX − 8.25` are the contract's stated intent), so the board bay ends
   up mirrored about CX: PCB spans X 14.075..31.855 instead of 15.355..33.135,
   bay walls X 11.975..13.575 / 32.355..33.955 instead of 13.255..14.855 /
   33.635..35.235. Every bay feature is symmetric about board y = 8.89, so
   only its case-X position changed.
2. **`POST_BY` 1.80 → 1.36.** At the board-y pocket extreme the contract's post
   width bit 0.14 mm into the RST/BOOT buttons. 1.36 restores DESIGN's own
   "buttons to the blocks/posts ≥ 0.3" at the extreme. Landing area is still
   2.635 mm² per post.
3. **`HOOK_BY` 2.00 → 1.60.** Mirrored, the contract's hook clipped the B2B
   connector (board y to 15.34) by 0.06 mm at the extreme. 1.60 leaves 0.34.
4. **Tie post moved X 13.0 → 18.0 and webbed to the bottom wall.** At X 13.0 it
   sits directly over the cord slot, so the lead cannot both wrap it and exit;
   and a free-standing Ø4 post is a second, unattached solid — the ring would
   not be one printable body. DESIGN's prose says "tie post beside it", which
   is what X 18.0 gives. The web is 2.0 wide, Y 2.40..9.00, same Z as the post.
5. **`CORD_SLOT_R` 1.5 → 1.499.** A 3.00-tall stadium with r = 1.50 exactly is
   rejected by `RectangleRounded` (`width and height must be > 2*radius`).

Contract numbers that the geometry does not reach (reported, not changed):

- **Screw head to front lip nose 5.96, not ≥ 7.** Fixed by `BOSS_Z0 = 15.86`,
  `SCREW_HEAD_T = 1.50` and `FRONT_LIP_Z1 = 8.40` — the contract's own numbers
  give 5.96. Still ample screwdriver access through the front mouth.
- **Eave brow half-angle 32.06°, not ≈ 42°.** Measured from the lens tip
  (CX, 71.26, Z 3.40) to the eave's underside front edge (Y 78.40, Z −8.00).
  32° is below a typical OV3660 vertical half-FOV, so the eave will clip the
  top of the frame; shortening `EAVE` or raising the board would fix it. Left
  as designed, flagged here.
- **Lens tip to hole wall 0.75 nominal, 0.11 at the worst combined extreme**,
  against the contract's "≥ 0.5 laterally at the extremes". The lens never
  enters the hole (it stops 1.0 behind the plate's inner face), so this is a
  sight-line number, not an interference — and at nominal the hole clears a 40°
  half-cone from the lens tip with room to spare.

## Open items

- The vendor XIAO STEP contains one self-intersecting solid (445.4 mm³);
  `inspect validate` flags it on the two assemblies. The three printed parts
  validate clean. Nothing was done to the vendor file.
- LOAD lead and antenna envelopes are estimates. BAT pad positions are not in
  the vendor model (the underside is modelled flat), hence the uniform 3.0 gap
  and the straight-line lead route. The lead mock does **not** model the turn
  round the tie post.
- The two front-plate posts are 2.60 × 1.56 × 13.61 mm columns. They print
  standing off the plate with no support, which is fine, but they are slender —
  worth checking on the coupon before trusting them as hold-downs.
- The bay hangs off the top wall by two 1.6 × 11.36 mm root faces. Strong
  enough in the print direction (everything rises from the bed), but it is the
  one place the ring could flex.
- No 45°-overhang sweep was run; the two known overhangs (1.30 mm hook
  undersides, 4.5 mm slot bridge) come from the geometry, not from a checker.
- Lens hole is open (no window), and there are no vents — condensation is
  expected outdoors.
