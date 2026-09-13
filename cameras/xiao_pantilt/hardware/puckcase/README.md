# puckcase v2.3

A sealed, camera-only case for the Seeed XIAO ESP32S3 Sense that presses into
the **power puck**'s front mouth in place of the puck's own front plate. Same
outline as the puck (47.21 × 80.80, R6, 2.4 walls), so the two boxes stack into
one brick. Lens forward and centred under an 8 mm eave; the puck's LOAD lead is
soldered to the XIAO's 5V/GND header pins and leaves through a slot in the
bottom wall. No USB/SD opening, no buttons, no vents, no mounting feature.

**v2** rebuilds the board bay after the v1 coupon print (`DESIGN_v2.md` §1):

- the base PCB carries **pin headers** — a 2.54 × 17.78 × 2.5 body on the back
  of each long edge, overhanging the edge by 1.0, with ~6 mm pin tails. Nothing
  may bear on the PCB's back along the long edges, so v1's ledges, corner
  blocks and front-plate posts are gone and the back gap grows 3.0 → **9.0**.
- the board is now held **by its ends and by the camera head**: hooks + a centre
  ledge at the far end, two pillar snap tongues at the USB end, side rails
  with crush ribs on the **expansion** PCB's edges, and a **collar** that
  captures the 8 × 8 head and the Ø7.84 barrel so lens alignment no longer
  depends on where the PCB sits.
- the board drops 3.5 (`BOARD_DROP`) so the SD card gets a 4.0 roof, and the
  eave brow opens from 32° to 43°.

**v2.1** (DESIGN_v2.md §9 A/B) deletes the bridge band so the microSD card can
be fitted to the board *before* the board is tilted in, and shortens the screw
bosses to 9.0 so M2 × 12 gets 3.0 mm of thread in the back plate.
**v2.2** (§9 D) replaces the single central snap tongue with **two pillar
tongues**, one at each end of the PCB's end edge, because the USB-C shell
sweeps through anything behind the PCB plane inside board y 4.41..13.35. Above
the lip there is now **no wall at all** at the USB end; the collar sheet
bridges wall to wall and the USB end's forward stop is the collar step acting
through the camera head. **v2.3** (§9 E) grows the tongue root strip from 0.2
to 1.5 mm tall and thins the tongues to 0.8 × 7.4 so the blade — not the strip
— is the hinge.

Contract: [`DESIGN_v2.md`](DESIGN_v2.md) (v1 is `DESIGN.md`, superseded).
Deviations are listed at the bottom of this file and commented at their
parameter in `puckcase_lib.py` with `# DEVIATION`.

Frame: X 0..47.21, Y 0..80.80 (up), Z 0 at the outer front face, +Z toward the
puck. Everything is modelled in place — no part-local origins. Board frame →
case frame is `board_to_case()` / `bspan()` in `puckcase_lib.py`.

## Parts

| File | Job | Print orientation | Volume |
|---|---|---|---|
| `front_plate.step.py` → `front_plate.step` | Weather face: 2.4 plate, Ø7.5 lens hole at (23.605, 67.76) with a 0.6 × 45° chamfer, 6.0 lip with 6 crush ribs into the ring's front mouth. **No posts** | outer face on the bed (Z 0), lip up. No supports | 10 801 mm³ |
| `ring.step.py` → `ring.step` | Body Z 2.4..26.36: 2.4 walls, top wall run 8.0 forward as the eave (drip groove underneath), the whole board bay, 4 screw bosses (9.0 long) with corner fills, cord slot, tie post, wire notch | standing on its **back mouth** (Z 26.36 on the bed), eave up | 19 257 mm³ |
| `back_plate.step.py` → `back_plate.step` | Coupling plate: 4.0 flat plate, the power puck's own front-plate lip on its back (6 crush ribs, identical geometry), 4 blind Ø1.7 × 3.4 M2 pilots on its front | front face on the bed (Z 26.36), lip up. No supports | 17 787 mm³ |
| 4 × **M2 × 12** pan head self-tapping | ring → back plate (9.0 through the boss, 3.0 into the plate, tip 0.4 short of the pilot bottom) | purchased | — |
| 1 × microSD, 1 × U.FL antenna pigtail + flag, LOAD lead | as v1 | purchased | — |

Bounding boxes: front_plate (0, 0, 0)–(47.210, 78.500, 8.400); ring
(0, 0, −8.000)–(47.210, 80.800, 26.360); back_plate
(0, 0, 26.360)–(47.210, 80.800, 37.860).

### The bay, feature by feature (all case coordinates)

| Feature | Where | Holds |
|---|---|---|
| side walls | X 10.975..12.575 & 33.355..34.955, Y 48.09..78.40, Z 5.56..26.36 (Z 8.70..26.36 above Y 76.35) | 1.5 clear of the PCB's long edges = 0.5 clear of the header bodies |
| far-end wall | Y 48.09..49.69, Z 11.36..26.36 | 0.35 off the expansion PCB's overhang |
| stop ribs | Y 49.69..50.14, X 28.355..32.355 / 13.575..17.575 | PCB far edge, 0.20 |
| hooks | Y 49.69..51.29, X 30.255..32.355 / 13.575..15.675, Z 13.76..15.96 | PCB top at the far corners, 0.15 over |
| centre ledge | Y 49.69..51.59, X 18.855..26.855, face Z 17.46 | PCB back at the far end, 0.10 under; 0.30 of flat bearing then a 45° entry ramp |
| USB-end opening | the **full bay width**, X 12.575..33.355, Z 8.36..17.46 | nothing above the lip — it is the way in for the board, the USB-C shell and the card |
| tongue root strip | X 12.575..33.355, Y 71.49..72.89, **Z 24.86..26.36** (1.40 thick × **1.50 tall**) | runs wall to wall at the bed; roots both tongues and ties the side walls together. v2.3 grew it from 0.20 so the blade, not the strip, is the hinge |
| **snap tongue A** | X 27.955..32.355 (board y −0.50..3.90), Y 71.49..**72.29** (**0.80** thick), Z 17.46..26.36 (**7.40** free); lip Y 70.89..71.49, Z 17.46..17.96 with a 45° ramp | PCB back at the USB end, 0.10 under, 0.40 of lip over the straight end edge; face at Y 71.49 is the **soft** +Y stop, 0.20 |
| **snap tongue B** | X 13.575..17.975 (board y 13.88..18.28), otherwise as A | mirror; both are ≥ 0.50 clear of the USB-C shell span so they survive the insertion swing |
| side rails | X 31.505 / 14.425 faces, Y 54.29..63.29, Z 11.76..13.16, 45° underside back to Z 15.01 | expansion PCB long edges, 0.15 + 2 crush ribs 0.25 proud (0.10 crush/side) |
| collar | X 12.575..33.355, Y 61.49..72.89 (73.59 front), Z 5.56..8.36; 8.6 window with a 0.6 back chamfer, step at Z 6.86, Ø8.25 bore | the camera head (8 × 8 × 2.1) and the Ø7.84 barrel — and, through the head, the USB end's forward stop |
| wire notch | X 33.355..34.955, Y 52.30..56.80, Z 21.86..26.36 | LOAD lead + U.FL coax out of the bay |

Review-only models (not printable; their `.step` outputs are **not** committed —
they embed the vendor board and run to 15 MB):

| File | What |
|---|---|
| `puckcase.step.py` | assembled view: 3 printed parts + the vendor XIAO + header mock + 4 screws |
| `fitcheck.step.py` | every occurrence, labelled. `check.py` imports its list |
| `snaps/bay_view.step.py` | the ring with the board, headers, lead, antenna and coax in place |
| `snaps/section_cx.step.py` | half model at X = CX (`_sectionlib.py` does the cutting) |
| `snaps/section_tongue.step.py` | detail at X = 30.2, through snap tongue A, clipped to the USB end |
| `snaps/section_rails.step.py` | section at Y = 58, across the side rails |
| `snaps/tilt_insertion.step.py` | the board at −13° with the head 1.3 short of the collar, sectioned at CX |

`puckcase_lib.py` holds every parameter, the board→case transform and all the
builders (`_side_walls`, `_far_end`, `_usb_end_wall`, `_rails`, `_collar`). It
**imports** `hardware/power_puck/caselib.py` + `fits.py` rather than copying
them, so the OUT/IN/LIP/BAY rectangles, radii, `LIP_ENG`, `LIP_RIB_H`, the
6-rib layout and `edge_crush_rib` are literally the puck's.

## Assembly / insertion order

1. Solder the LOAD lead to **5V/GND at the far end of one header row** (the −y
   row); fit the U.FL pigtail **and the microSD card** — the card goes in
   before the board does.
2. Screw the ring to the back plate: 4 × **M2 × 12** down through the bosses
   from the front mouth.
3. Feed the LOAD lead and the coax out through the **wire notch** in the +X
   side wall, then down the corridor and out the cord slot; one turn round the
   tie post. Stick the antenna flag to the plate face below the bay (Y 15..40).
4. **Board in, from the back mouth:** tilt the board ~13° (far end forward),
   slide the far edge into the far-end groove between the hooks and the ledge
   (both chamfered), then swing the USB end forward. The expansion edges ride
   down the rails and crush 0.10/side; the USB-C shell and the card pass
   through the wide-open USB end; the PCB's end corners cam **both** tongues
   back 0.6 and snap behind their lips. Forward travel of the seated board is
   0.155, caught by the far-end hooks; the USB end's forward stop is the
   collar step through the camera head at 0.20. There is no rigid +Y stop —
   Y play is 0.20 to the far-end stop ribs and 0.20 to the tongue faces.
5. **Camera head:** feed it straight back into the collar window by hand — it
   is flex-mounted and does **not** swing in with the PCB. The 0.6 chamfer at
   the window's back edge takes it; the step at Z 6.86 sits 0.2 over the head
   top and the Ø8.25 bore takes the barrel.
6. Press the front plate on (lens through the Ø7.5 hole).
7. Puck: pull its back cup, pass the lead in through the puck's bottom LOAD
   slot, plug the JST-PH into the charger's LOAD socket, press the cup back on.
   Remove the puck's plain front plate.
8. Press the camera case's lip into the puck tube's front mouth. Both bottom
   faces flush. Silicone both cord exits.

Removal: press **both** tongues outward with a fingernail through the back
mouth.

## Build and check

All commands from this directory, with the CAD skill's interpreter:

```bash
PY=~/.claude/skills/cad/.venv/bin/python
CADGEN=~/.claude/skills/cad/.venv/bin/cadgen

# printable STEPs (each model script writes its own .step)
$PY ring.step.py; $PY front_plate.step.py; $PY back_plate.step.py

# geometry soundness
for f in front_plate.step ring.step back_plate.step; do
    $CADGEN step inspect validate $f
done

# coupons -> print/*.stl + print/*.3mf
(cd print && $PY coupon_ring_bay.step.py && $PY coupon_front_plate.step.py)

# review models (scratch .step in snaps/, deleted after snapshotting)
(cd snaps && for m in bay_view section_cx section_tongue section_rails \
                      tilt_insertion; do $PY $m.step.py; done)
$CADGEN snapshot snaps/section_cx.step snaps/section_cx.png \
        --camera '{"direction":[1,0,0],"up":[0,1,0]}' --display '{"mode":"solid"}'

# fit / interference (fail-closed, ~2.5 min — it loads the 103-solid vendor STEP)
$PY check.py
```

`check.py` output is pasted in [`checks.md`](checks.md). Twelve fail-closed
groups: one valid solid and the expected bounds per printed part; every
bound-overlapping pair of the 14 labelled occurrences intersected solid by
solid (0 except the named designed contacts); the PCB assembly **with the card
fitted**, the header mock and the camera head against all three printed parts
at nominal and at all 12 stop-face play extremes; tilt insertion at
0/−2/−4/−8/−13° (board+card, and the card alone) plus the far-edge groove
arithmetic, both tongues' swing split into cam ramp vs tongue body, and a
33-step straight-in sweep of the camera head; 19 named clearances; the board's
forward travel to its stops; five 0.30-clearance proofs by mock inflation; per
tongue the lip bearing, straight-edge overlap, shell clearance, strain and snap
force; brow angle, card roof, the screw stack
and driver access down all four boss axes; a 45° overhang audit; and an
insertion-feasibility section. It prints `CHECK PASSED` only if every group ran
and passed, and never maps an exception to 0.

Headline numbers: `back_plate × puck_tube = 15.4400 mm³`, exactly the puck's
own `front_plate ∩ tube`; `front_plate × ring = 11.4800 mm³`; the 4 rail crush
ribs take `1.1808 mm³` out of the expansion PCB's edges (0.10/side). Retention:
hook 0.150 over the PCB top, ledge 0.100 under it, both tongue lips 0.100
under it with 0.400 of reach and 1.1163 mm² of bearing each (1.994 mm of it on
the straight end edge), collar step 0.200 over the head top (the USB-end
forward stop), rails 0.150 with a 0.100 crush, collar 0.300/side round the head and
0.205 round the barrel. Forward travel of the whole board 0.155 (hooks first).
Brow 43.03°, card roof 4.000, tongue strain 1.315 % at 0.6 of deflection,
snap force 1.67 N per tongue / 3.34 N total as a free cantilever, 0.86 N per
tongue once the root strip's torsion is in series (E = 2000 MPa). Tongue bodies
0.0000 against the swept board at every angle; only the cam ramps engage
(1.36 mm³ at −2°, 1.46 at −4°).
Screws: boss 9.000, engagement 3.000, tip 0.400 short of the pilot bottom,
driver access 0.0000 on all four axes.

## Snapshots (`snaps/`)

| PNG | What |
|---|---|
| `bay_back.png` | into the bay through the back mouth — the board, both header rows, the walls, hooks, tongue, lead and antenna |
| `bay_front.png` | the same model from the front, plate removed |
| `section_cx.png` | half model at X = CX: eave, lip stack, collar, board, headers, back plate, puck lip |
| `section_tongue.png` | detail cut at X = 30.2 through snap tongue A — the lip, its 45° cam ramp, the root strip and the open USB end |
| `section_rails.png` | section at Y = 58, across the side rails and the expansion PCB edges |
| `tilt_insertion.png` | the −13° insertion pose, sectioned at CX, head held 1.3 short of the collar |
| `coupon_ring_bay.png` | the bay coupon in print orientation, seen from under the bed plane so the bay reads |
| `coupon_front_plate.png` | the front-plate coupon in print orientation |

## Coupons (`print/`)

| File | What | Solid | Volume | Bounding box |
|---|---|---|---|---|
| `coupon_ring_bay.step.py` → `.stl` / `.3mf` | `ring ∩ (Y ≥ 44)`, flipped so the back mouth is on the bed | 1 valid | 11 439 mm³ | (0, −80.800, 0)–(47.210, −44.000, 34.360) |
| `coupon_front_plate.step.py` → `.stl` / `.3mf` | `front_plate ∩ (Y ≥ 44)`, outer face down | 1 valid | 4 719 mm³ | (0, 44.000, 0)–(47.210, 78.500, 8.400) |

Print both before committing to a full set: they carry every new feature (side
walls, far-end groove, USB-end wall with the tongue, rails and ribs, collar) and
the lens hole they mate to. `Y ≥ 44` is 36.8 mm of the case, ~35 min on the
ring. Rebuild them with `python coupon_*.step.py --force` — cadgen's staleness
gate does not see `puckcase_lib.py` (it is imported through `sys.path`).

## Overhangs

Faces steeper than 45° from vertical in each part's print orientation, first
layer excluded (from `check.py` group 9):

| Part | Faces | Area | Worst |
|---|---|---|---|
| ring | 14 | 253.4 mm² | collar sheet underside 129.1 mm² (Z 8.36, a 20.8 mm bridge between the side walls, now unsupported along the USB-end edge); front-mouth shoulder 28.5; drip-groove roof 28.2; collar window step 20.5 (8.6 mm bridge); FPC relief roof 16.1; collar front-part underside 14.6; wire-notch roof 7.2 (4.5 mm bridge); cord-slot roof 3.6 (4.5 mm bridge); **hook undersides 1.37 + 1.36** (2.1 × 0.65 each); **rib-crest undersides 0.75 × 4** (0.25 × 4.0 each) |
| front_plate | 1 | 1.3 mm² | the +Y crush rib's underside on the lip |
| back_plate | 4 | 9.1 mm² | the four Ø1.7 pilot bottoms |

Everything above is either a bridge anchored at both ends or a sub-1.4 mm²
unsupported tab; no supports are needed. The rails' undersides are exactly 45°
and the tongue lip's underside is its 45° cam ramp, so neither is flagged.

## Completion level

**v2.3 modelled, checks passed with zero warnings, coupon not yet printed.**
The three parts are single valid solids with the contract's dimensions; they
clear the real vendor board, the header mock, the U.FL plug and coax and the
buttons at nominal and at every reachable play extreme; the board — **with the
microSD card fitted** — tilts in at 13° with zero interference and the two
tongues are touched only on their cam ramps; the camera head feeds straight
into the collar with no interference anywhere along its path; M2 × 12 gets
3.0 mm of thread and the driver reaches every boss. Nothing here has been
printed, and the two things the print has to settle are the snap preload (the
root strip is soft in torsion — see Open items) and the collar's 20.8 mm
bridge. The puck lip is unproven too.

## Deviations from DESIGN_v2.md

Each is also commented at its parameter in `puckcase_lib.py`.

1. **Board y → case −X, not +X** (inherited from v1). The contract's triple
   (x → −Y, y → +X, z → −Z) has determinant −1: a mirror, not a rigid
   placement. With "USB end up" and "lens forward" fixed, handedness forces
   y → −X. The lens stays on CX; the bay is mirrored about CX, and since every
   bay feature is symmetric about board y = 8.89 only its case-X position
   changes.
2. **Side walls split into two Z bands.** §3 gives them one range
   (Z 5.56..26.36) over the whole run Y 48.09..78.40. Above Y 76.65 that is
   inside the front plate's lip band (Z 2.40..8.40) — a hard interference the
   contract does not mention. The walls keep the full forward reach only up to
   Y 76.35 (0.30 clear of the lip band) and start at Z 8.70 for the last
   2.05 mm up to the top wall.
3. **Centre ledge: 0.30 of flat bearing + a 45° entry ramp**, instead of a flat
   face over the full 1.25 reach with a 0.5 entry chamfer. Rotating the board to
   the 13° insertion tilt lifts its back face by reach × sin 13°, so a flat face
   0.10 behind the PCB may only reach 0.444 (measured bite at the tabled reach:
   0.25 mm³). The contract's 0.10 gap is preserved where the ledge actually
   bears, at the PCB's far edge.
4. **The USB end is fully open above the lip** — v2.1 amendment A opened the
   window, v2.2 (§9 D) removed the rest of the wall when the tongue moved to
   the pillars. At 13° the USB-C shell sweeps ~3.6 behind the PCB plane, so
   nothing may stand there inside board y 4.41..13.35. Consequence: the free
   gaps beside the tongues are 1.00 / 2.60 rather than the tabled 0.80 slits
   (the check requires ≥ 0.80), and the collar sheet's 20.8 mm bridge is
   unsupported along its USB-end edge. The v2.0 bridge-relief deviation is
   withdrawn with the bridge itself.
5. **A 4.5 × 4.5 wire notch through the +X side wall** (Y 52.30..56.80,
   Z 21.86..26.36, open onto the back mouth so it prints as a bridged slot).
   §3 calls the far-end wall "low … so the antenna cable can cross it", but low
   in *board* z means case Z 11.36..26.36 — a full barrier. With side walls, a
   far-end wall and a USB-end wall the bay is a closed box and neither the LOAD
   lead nor the coax can reach the cavity below.
6. **`tilt_loc` pivots about the PCB's back-far corner** (board z = 0), not the
   top-far corner as in v1. The v1 pivot drives the PCB's back-far corner
   0.28 further in at 13° and bites the stop ribs (0.06 mm³) for a motion the
   board cannot make — its far edge is already against them.
7. **`CORD_SLOT_R` 1.5 → 1.499** (inherited from v1): `RectangleRounded`
   rejects r = h/2 exactly.
8. **§6.2's symmetric ±0.3 along becomes the true stop faces, −0.20 / +0.40.**
   §2/§3 put the stop ribs 0.20 from the PCB's far edge and the USB-end wall
   0.40 from its end edge — 0.6 of travel, but asymmetric, so −0.30 is a
   position the board physically cannot reach (it is 0.10 inside the stop ribs).
   The sweep uses −0.20 / 0 / +0.20 / +0.40 × −0.15 / 0 / +0.15, a superset of
   the reachable set. Across stays ±0.15 (the rails).
9. **The camera head is a separate occurrence from the PCB assembly** (the
   card is **not**, since v2.1). §1 says the head "is only held by its flex",
   and §2 makes the collar — not the PCB — position the lens, so the head
   cannot travel with the PCB in the play sweep or swing with it on insertion
   (rigidly attached it puts 1.9 mm³ into the collar at −4°, and the Ø8.25
   bore would cap the PCB's play at ±0.205 radial). The head is checked where
   the collar holds it, plus a 33-step straight-in sweep and a rigid
   forward-travel measurement. The card rides with the PCB everywhere.
10. **Bosses are 9.00 long, not the amendment's 8.3.** 8.3 gives 3.7 of thread
    into a 3.4-deep pilot — the screw bottoms out 0.30 past it. 9.00 is the
    value that meets both stated requirements: engagement 3.000 (≥ 3.0) and
    tip 0.400 short of the pilot bottom (≥ 0.3).
11. **`@step(out=…)` model scripts instead of `scripts/gen --write`.** The CAD
    skill no longer ships `scripts/gen`, `scripts/export`, `scripts/inspect` or
    `scripts/snapshot`; cadgen 0.11.1 builds a model by running its script and
    inspects/renders documents through the `cadgen` CLI. Same outputs, same
    file names.

Contract numbers the geometry reports rather than meets:

- **Collar clearances come out larger than §6.3's minimums** because §1 sizes
  the head 8.3 square while the measured vendor STEP says 8.0: the 8.6 window
  gives 0.300/side, not 0.150. Checked as "≥".

## Open items

- **The root strip is soft in torsion** (v2.3 fixed its bending, not its
  twist). The tongue's root moment is about the X axis and the strip runs
  along X, so the strip twists: J = 0.616 mm⁴, G = 741 MPa → 0.542 mm at the
  lip against the blade's own 0.6. The two springs in series give 1.44 N/mm,
  so the snap preload is **0.86 N per tongue** rather than 1.67, and the blade
  sees about half the computed strain. Retention is unaffected — the lip's
  0.4 engagement is geometric and a +Z load on the board is carried by the lip
  in bearing, not by the spring. If more preload is wanted, thickening the
  strip from 1.40 to 2.40 in board x (to x −2.6..−0.2, clear of the whole
  swept board) roughly doubles its torsional rate → ~0.25 mm.
- **There is no rigid +Y stop.** The tongue faces at board x −0.2 are a soft
  stop, so a hard shove on the USB end deflects the tongues rather than
  hitting a wall. Y play is 0.20 / 0.20; the far-end stop ribs are the only
  rigid end stop.
- The collar sheet is a 20.8 mm bridge in the print. It carries the lens
  location, so its sag matters more than most bridges — the coupon is the place
  to find out.
- The header mock is *assumed* geometry (§1): 2.54 pitch, 2.5 body, 6 mm tails.
  If the real headers differ, `BACK_GAP`, `SIDE_CLR` and the ledge/tongue
  windows all move.
- LOAD lead, coax and antenna envelopes are estimates, and the lead mock does
  not model the turn round the tie post.
- The vendor XIAO STEP contains one self-intersecting solid (445.4 mm³);
  `inspect validate` flags it on assemblies. The three printed parts validate
  clean. Nothing was done to the vendor file.
- Lens hole is open (no window), and there are no vents — condensation is
  expected outdoors.
