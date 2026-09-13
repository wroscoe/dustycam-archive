# Power puck v2 — bq25185 solar charger + 1S LiPo + DC jack, 4-part printed enclosure

A stand-alone power supply in the same rounded-rectangle shape as the
OpenMV N6 case (`cameras/openmv_n6/hardware/case/`), meant to sit behind a
camera and feed it through a JST-PH LOAD lead out of its bottom. Coupling to
the camera (a coupling plate replacing the front plate, or glue) is a later
piece of work; the front plate is deliberately plain.

Overall **47.21 × 80.80 × 38.80 mm** (W × H × D), plus the 1.5 mm USB cap head
on the top face. All mm. **Frame:** X across
from the −X outer face, Y up from the outer bottom face, Z from the outer
front face toward the back. The back cup carries everything that has a wire:
the DC jack and the LOAD-wire slot in its bottom skirt wall, the charger on
its floor, and a capped USB-C port in its top skirt wall.

## Parts

| Part | File | Job | Print orientation | Volume |
|---|---|---|---|---|
| Tube | `tube.step` / `.stl` | Rounded-rect ring, open both ends, 2.4 walls. Holds the battery. | Standing on its front mouth | 9.0 cm³ |
| Front plate | `front-plate.step` / `.stl` | Plain flat lid; 7.5 lip presses into the tube's front mouth on 6 crush ribs. | Outer face down | 11.8 cm³ |
| Back cup | `back-cup.step` / `.stl` | Lid with an 18.0 deep skirt: charger on its floor at the top end, jack and LOAD slot through its bottom skirt wall, USB-C port through its top skirt wall. 7.5 lip on a solid seam ring presses into the tube's back mouth. | Back face down | 22.8 cm³ |
| USB cap | `usb-cap.step` / `.stl` | Press-in plug for the USB-C port, 2 crush ribs, 18 × 12.5 head outside. | Head down | 0.6 cm³ |

`puck.step` is the assembled view (cap fitted). `fitcheck.step` is a
review-only cutaway with the vendor charger model, the jack envelope, the
battery, the two JST plugs and both cable mocks in place. `sketch-v2.png`
(from `sketch-v2.py`) is the dimensioned 2D contract sketch.

No supports on any part. The jack hole and the LOAD slot are horizontal
openings in a vertical wall (slight crown sag expected; the nut clamps
through regardless). The seam ring's inner edge is a 45° chamfer so the
ledge under the lip prints without support.

## Purchased parts

| Part | Source | Confidence |
|---|---|---|
| Adafruit 6091 bq25185 charger, 31.75 × 25.4 × 1.57 PCB, 4 × Ø2.5 holes on 26.67 × 20.32, two side-entry JST-PH (BATT, LOAD) on one edge, USB-C on the opposite edge, DC/solar input = two solder pads | `ref/bq25185-part.yaml`; vendor STEP fetched with `sarg cad get sargbench2/adafruit-6091-adafruit-bq25185-usb-dc-solar-lithium-ion-poly` into `ref/` (gitignored; needed by `check.py` and `fitcheck`) | vendor |
| 1S LiPo pouch 11 × 36 × 67, lead from one corner | caliper (Wade, 2026-09-12); 11 taken as nominal | measured |
| Panel-mount DC barrel jack: Ø7.52 hole, 13.0 reach from the outer face | user measurement | measured |
| … its nut Ø12 × 2.5, body Ø10, outside flange Ø11 × 2 | **assumed**, no drawing; sizes the skirt depth and the jack's Z | assumed |
| JST-PH plug envelope 5.9 × 4.5, 6.0 proud of the board edge | estimated | estimated |
| 4 × M2.5 × 6 pan head (charger → back cup bosses) | same screw as the N6 case | |
| USB-C plug overmold up to 12 × 7 | envelope for the port | estimated |

## How it goes together

```
front plate ── plain lid, lip into the tube's front mouth (z 2.4…9.9)
tube        ── 16 deep; battery lies loose inside it against the front plate
back cup    ── lip into the tube's back mouth (z 10.9…18.4) rooted in a solid
               seam ring, then an 18.0 deep skirt: charger on the floor at the
               top, jack + LOAD slot in the bottom wall, USB-C port in the top wall
usb cap     ── press-in plug for the USB-C port, pulled by its head
```

1. Jack into the back cup's bottom skirt wall from outside, nut inside. Solder
   its leads to the charger's DC-in pads.
2. Charger onto the four floor bosses at the top end of the cup, bare side
   down, components facing the open mouth, JST edge toward the bottom:
   **4 × M2.5 × 6** into the Ø2.10 pilots (blind at 4.60, 1.20 floor). Board
   at x 7.73…39.48, y 51.0…76.4; its USB-C shell ends 1.0 inside the top wall,
   behind the port.
3. Plug the LOAD lead in and run it down the −X side of the cup and out the
   7 × 6 slot beside the jack (x 8.1…15.1). Plug the BATT lead in.
4. Press the front plate into the tube. Lay the battery in the tube against
   it, lead at the top-back corner (it reaches the charger's BATT JST 5 mm
   behind the seam). Nothing locates the battery; tape it.
5. Press the back cup on. Charger, jack, both plugs and the LOAD lead all
   ride with it, so pulling the back cup exposes everything and the LOAD lead
   never has to be unthreaded.
6. Press the USB cap into the port. Pull it by the head to charge over USB
   with the puck closed.

## Layout numbers

- Z stack: front face 0 → front plate inner face / tube mouth 2.40 → front
  lip nose 9.90 → back lip nose 10.90 → seam 18.40 → seam ring to 20.00 →
  45° chamfer to 21.75 → charger components 26.63 → charger bare face /
  boss tops 33.00 → floor 36.40 → back face 38.80.
- Seam ring: solid from the outer face to the lip's inner face (4.15 wide)
  for 1.6 mm behind the seam, then a 1.75 × 45° chamfer back to the 2.4
  skirt wall, so the lip's 1.6 wall roots into a full-perimeter ledge. v1's
  lip was only touching the skirt along a line (it was inset 0.15) and was
  held together by the crush ribs.
- Battery zone z 2.40…13.40 (11) with 5.0 of air before the seam; between the
  lip inner faces y 4.15…76.65, battery at y 8.0…75.0.
- Jack at (x 23.605, z 29.075), reaching y 13.0. Nut z 23.075…35.075, 1.325
  clear of the chamfer top and of the floor.
- LOAD slot 7 × 6 (r 1.5) at x 11.6, z 29.075, 2.5 clear of the nut.
- Charger −Y edge at y 51.0: 38.0 above the jack end, JST plugs 32 above it.
  USB-C port 15 × 9.5 (r 2.5) at x 23.605, z 30.33 through the top wall;
  shell face 1.0 inside.
- USB cap: plug 14.7 × 9.2 × 2.4 (0.15/side, flush with the inner face, 1.0
  short of the shell), two 6-long ribs 0.25 proud, head 18 × 12.5 × 1.5.
- Crush ribs: front plate 6, back cup 6, cap 2. Rib height 6.4 on the lips,
  2.0 on the cap, all 0.25 proud on a 0.15 gap.

## Validated (`check.py`, output in `check-v2.txt`)

Run with the cad skill's venv:
`~/.claude/skills/cad/.venv/bin/python check.py` (`--quick` skips the sweep).

- 12 labelled occurrences, 18 bound-overlapping pairs, all intersected. The
  56-solid vendor charger is placed per-solid (a `Pos`/`Rot` on a build123d
  `Compound` is ignored by `intersect()`).
- 0 interference between any printed part and the charger, jack envelope,
  battery, JST plug mocks, LOAD and BATT cable mocks, USB plug mock.
- Designed crush only: tube ∩ front plate 15.44 mm³ (6 ribs), tube ∩ back
  cup 15.44 mm³ (6 ribs), back cup ∩ cap 1.76 mm³ (2 ribs). Cap ∩ USB plug
  mock is reported as alternate states (never both present).
- Jack nut 1.325 clear of the seam chamfer and the floor; LOAD slot 2.5 from
  the nut; USB shell 1.0 inside the wall; plugs 32 above the jack.
- 23-step, 1.0 mm pull-out sweep of back cup + charger + jack + plugs + LOAD
  lead against the tube, front plate and battery: 0 beyond the rib crush,
  which falls to 0 once the ribs leave the mouth.
- All four parts are single valid solids. An isolated rebuild of the v1
  (no-ring) back cup produced 2 solids, confirming the v1 lip defect.

Completion level: **mechanically plausible prototype**. Not printed, no
slicer pass.

## Known compromises and open items

- Jack nut/body/flange are assumed envelopes. Measure the real nut; the nut
  window between the seam chamfer and the floor is 14.65 (nut Ø12 + 2.65).
- Battery thickness 11 is nominal; it has 5 mm of air toward the seam and
  1.65 at the top end. Rotate the pack so the lead is at the top-back corner,
  nearest the charger's BATT JST.
- No vents. The USB-C port is capped, not sealed.
- No feature retains the battery; the LOAD lead's exit is a plain slot, not
  a grommet. The cap is friction-only, like the lips.
- Front plate is plain (no coupling holes, by request).
- Suggested coupon: the back cup's bottom skirt wall patch with the jack hole
  and LOAD slot, plus the cap in its port, to confirm the nut clamps, the
  openings print round, and the cap's press fit.
