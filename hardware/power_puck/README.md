# Power puck v1 — bq25185 solar charger + 1S LiPo + DC jack, 3-part printed enclosure

A stand-alone power supply in the same rounded-rectangle shape as the
OpenMV N6 case (`cameras/openmv_n6/hardware/case/`), meant to sit behind a
camera and feed it through a JST-PH LOAD lead out of its bottom. Coupling to
the camera (a coupling plate replacing the front plate, or glue) is a later
piece of work; the front plate is deliberately plain.

Overall **47.21 × 80.80 × 34.30 mm** (W × H × D). All mm. **Frame:** X across
from the −X outer face, Y up from the outer bottom face, Z from the outer
front face toward the back. The bottom (−Y) wall carries the DC jack (in the
back cup) and the LOAD-wire slot (in the tube).

## Parts

| Part | File | Job | Print orientation | Volume |
|---|---|---|---|---|
| Tube | `tube.step` / `.stl` | Rounded-rect ring, open both ends, 2.4 walls. LOAD slot in its bottom wall. | Standing on its front mouth | 8.9 cm³ |
| Front plate | `front-plate.step` / `.stl` | Plain flat lid; 7.5 lip presses into the tube's front mouth on crush ribs. Lip notched at the bottom for the LOAD lead. | Outer face down | 11.6 cm³ |
| Back cup | `back-cup.step` / `.stl` | Lid with a 13.5 deep skirt: the charger bolts to its floor, the jack goes through its bottom skirt wall. 7.5 lip presses into the tube's back mouth. | Back face down | 19.6 cm³ |

`puck.step` is the assembled view. `fitcheck.step` is a review-only cutaway
with the vendor charger model, the jack envelope, the battery, the two JST
plugs and both cable mocks in place.

No supports on any part. The jack hole is a horizontal hole in a vertical
wall (slight crown sag expected; the nut clamps through it regardless).

## Purchased parts

| Part | Source | Confidence |
|---|---|---|
| Adafruit 6091 bq25185 charger, 31.75 × 25.4 × 1.57 PCB, 4 × Ø2.5 holes on 26.67 × 20.32, two side-entry JST-PH (BATT, LOAD) on one edge, USB-C on the opposite edge, DC/solar input = two solder pads | `ref/bq25185-part.yaml`; vendor STEP fetched with `sarg cad get sargbench2/adafruit-6091-adafruit-bq25185-usb-dc-solar-lithium-ion-poly` into `ref/` (gitignored; needed by `check.py` and `fitcheck`) | vendor |
| 1S LiPo pouch 11 × 36 × 67, lead from one corner | caliper (Wade, 2026-09-12); 11 taken as nominal | measured |
| Panel-mount DC barrel jack: Ø7.52 hole, 13.0 reach from the outer face | user measurement | measured |
| … its nut Ø12 × 2.5, body Ø10, outside flange Ø11 × 2 | **assumed**, no drawing; sizes the skirt depth and the jack's Z | assumed |
| JST-PH plug envelope 5.9 × 4.5, 6.0 proud of the board edge | estimated | estimated |
| 4 × M2.5 × 6 pan head (charger → back cup bosses) | same screw as the N6 case | |

## How it goes together

```
front plate ── plain lid, lip into the tube's front mouth (z 2.4…9.9)
tube        ── 16 deep; battery lies loose inside it against the front plate
back cup    ── lip into the tube's back mouth (z 10.9…18.4), then a 13.5 deep
               skirt holding the charger (floor bosses) and the jack (bottom wall)
```

1. Jack into the back cup's bottom skirt wall from outside, nut inside. Solder
   its leads to the charger's DC-in pads.
2. Charger onto the four floor bosses, bare side down, components facing the
   open mouth, JST edge toward the bottom: **4 × M2.5 × 6** into the Ø2.10
   pilots (blind at 4.60, 1.20 floor). Board at x 7.73…39.48, y 21.0…46.4.
3. Plug BATT and LOAD leads into the charger (they enter from the bottom side,
   8 mm of room in front of the edge). The USB-C faces up the open interior
   and is reachable whenever the back cup is off.
4. Press the front plate into the tube. Feed the LOAD lead's JST-PH plug out
   through the tube's bottom slot (7 × 6 stadium at x = CX, z 3.4…9.4) — the
   front plate's lip is notched 9 wide behind it.
5. Lay the battery in the tube against the front plate, lead at the
   bottom-back corner, bottom edge 8 mm up from the inner floor so the leads
   pass beneath it. Nothing locates it; tape it.
6. Press the back cup on. Charger, jack and both plugs ride with it, so
   pulling the back cup later exposes everything.

## Layout numbers

- Z stack: front face 0 → front plate inner face / tube mouth 2.40 → front
  lip nose 9.90 → back lip nose 10.90 → seam 18.40 → charger components
  22.13 → charger bare face / boss tops 28.50 → floor 31.90 → back face 34.30.
- Battery zone z 2.40…13.40 (11) with 5.0 of air before the seam; between the
  lip inner faces y 4.15…76.65, battery at y 8.0…75.0.
- Jack at (x 23.605, z 25.15), reaching y 13.0. Nut z 19.15…31.15, 0.75
  clear of both the seam and the floor — no lip notch needed.
- Charger −Y edge at y 21.0 = jack end + 8 for the plugs. USB-C edge at
  y 47.4, 30 mm of interior above it.
- Crush ribs: front plate 7 (bottom pair at CX ± 12 either side of the
  notch), back cup 6. Rib height 6.4 from the lip base, 0.25 proud.

## Validated (`check.py`, output in `check-v1.txt`)

Run with the cad skill's venv:
`~/.claude/skills/cad/.venv/bin/python check.py` (`--quick` skips the sweep).

- 10 labelled occurrences, 22 bound-overlapping pairs, all intersected. The
  56-solid vendor charger is placed per-solid (a `Pos`/`Rot` on a build123d
  `Compound` is ignored by `intersect()` — see the N6 case rev E3 note).
- 0 interference between any printed part and the charger, jack envelope,
  battery, two JST plug mocks, LOAD and BATT cable mocks.
- Tube ∩ front plate = 18.01 mm³ (7 crush ribs), tube ∩ back cup =
  15.44 mm³ (6 ribs); both entirely the designed crush interference.
  Front plate ∩ back cup = 0.
- Jack nut 0.75 clear of the seam and the floor; plugs 2.0 above the jack
  end; battery 8.73 clear of the charger components in Z.
- 21-step, 1.0 mm pull-out sweep of back cup + charger + jack + plugs against
  the tube, front plate and battery: 0 beyond the rib crush, which falls to 0
  once the ribs leave the mouth. The cable mocks stay put (they are unplugged
  from the charger before the cup comes off).
- All three parts are single valid solids.

Completion level: **mechanically plausible prototype**. Not printed, no
slicer pass.

## Known compromises and open items

- Jack nut/body/flange are assumed envelopes. Measure the real nut; a bigger
  nut needs a deeper skirt (`CUP_D`), the Z window is nut + 1.5.
- Battery thickness 11 is nominal; it has 5 mm of air toward the seam and
  1.65 at the top end. Rotate the pack so the lead is at the bottom-back
  corner (3.85 of lead room under it).
- No vents, no USB-C opening: the plates come off for charging by USB.
- No feature retains the battery or the two loose plugs; the LOAD lead's exit
  is a plain slot, not a grommet.
- Front plate is plain (no coupling holes, by request).
- Suggested coupon: the back cup's bottom skirt wall patch with the jack hole,
  to confirm the nut clamps and the hole prints round.
