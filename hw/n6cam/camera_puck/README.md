# Camera puck v1 — OpenMV Cam N6 camera-only enclosure, 4-part printed

A camera-only enclosure for the OpenMV Cam N6, in the same rounded-rectangle
face as the power puck (`hardware/power_puck/`) so the two stack. It is the
N6 case rev D architecture (`cameras/n6cam/hardware/case/archive/revD/`)
with the puck's 80.80 face height, a plain friction-fit **back plate**
instead of rev D's back cup (no battery bay — a coupling plate that mates to
the power puck is later work, and this back plate is deliberately plain), a
**LOAD-lead slot** through the front cup's bottom wall for the JST-PH power
lead coming from the puck behind it, and the puck's press-in **USB cap**
(deeper here: the port passes through the outer wall *and* the internal
shoulder, 3.60 vs the puck's 2.40). No charger, no jack, no battery — this
puck only frames and cools the camera.

Overall **47.214 × 82.30 × 42.30 mm** (W × H × D) including the 1.5 mm USB
cap head proud of the bottom face; the printed envelope proper (cap
retracted) is 47.214 × 80.80 × 42.30. All mm.

**Frame:** identical to `ref/openmv-n6.py` and `../case/caselib.py` — origin
at the N6 PCB bottom-left corner on the PCB *bottom* face, +X 35.56 across
the board, +Y toward the lens end, +Z the optical axis toward the lens. The
camera's bottom (USB/LOAD/vent) wall is the −Y wall. **Mapping to the power
puck's own frame** (for reference only — geometry in this directory stays
in the board frame above): `x' = x + 4.302`, `y' = y + 13.60`,
`z' = 25.90 − z`. Under this mapping the front cup's OUT rectangle lands
exactly on the puck's OUT rectangle (0..47.214 × 0..80.80) and the front
face (`Z_FRONT_OUT` = 25.90) lands on the puck's own front face (`z' = 0`),
confirming the two enclosures share a face if stacked back-to-back with the
puck's front toward this camera's back.

## Parts

| Part | File | Job | Print orientation | Volume |
|---|---|---|---|---|
| Front cup | `front-cup.step` / `.stl` | Outer shell over the lens/component side. Straight bore, internal shoulder, deeper socket for the back plate's lip. Lens barrel stands proud. LOAD slot + 2 vents + USB port through the −Y wall. | Face down (`Z_FRONT_OUT` on the bed) | 36.4 cm³ |
| Cam plate | `cam-plate.step` / `.stl` | Flat plate the N6 bolts to (2 × M2.5 into Ø5.5 bosses, Ø2.80 mount holes). Sandwiched between the front cup shoulder and the back plate lip. No battery/charger here: no notch, no pilots, no wire slot. | Flat, bosses up (`Z_PLATE_BOT` on the bed) | 9.6 cm³ |
| Back plate | `back-plate.step` / `.stl` | Plain friction-fit plate; 7.5 lip presses into the front cup's socket on 6 crush ribs. Back face is plain — a future coupling plate replaces this part. | Back face down (`Z_BACK_OUT` on the bed) | 11.8 cm³ |
| USB cap | `usb-cap.step` / `.stl` | Press-in plug for the front cup's USB-C port, 2 crush ribs, 18 × 12.5 head outside. Plug is 3.60 deep (wall + shoulder) — deeper than the puck's own cap. | Head down (outer face on the bed) | 0.8 cm³ |

`camera-puck.step` is the assembled view (cap fitted). `fitcheck.step` is a
review-only cutaway, half-sectioned at `x = CX`, with the real N6 board
model, the microSD card, and the LOAD plug/cable mocks in place.
`sketch.png` (from `sketch.py`) is the dimensioned 2D contract sketch.
Snapshots (`snap-v1-*`): `iso` and `lens-face` (the +Z lens face),
`front` (the −Y bottom wall: vents, LOAD slot, USB cap), `bottom` (the −Z
back face, plain back plate), `section` / `back` / `back2` (the fitcheck
cutaway).

No supports on any part.

## Purchased / vendor-modelled parts

| Part | Source | Confidence |
|---|---|---|
| OpenMV Cam N6: board outline, mount/standoff holes, headers, USB-C, microSD socket, LiPo connector, JTAG, buttons, camera daughter-board, M12 lens holder + lens | `ref/openmv-n6.py`, measured from OpenMV's own 3D models (see the docstring/`ref/DIMENSIONS.md` for provenance) | vendor model |
| JST-PH plug envelope (LOAD lead into the N6's LiPo connector) | estimated, same envelope as the case/puck's charger-side JST-PH plugs | estimated |
| USB-C plug overmold up to 12 × 7 | envelope for the port | estimated |
| Header tail length 3.0 below the PCB | assumed (not measured) | assumed |
| 2 × M2.5 × 6 pan head (board → cam plate bosses) | same screw as the N6 case | |

## How it goes together

```
front cup   ── shell over the lens/component side; shoulder for the plate,
               socket for the back plate's lip, LOAD slot + vents + USB
               port through the bottom wall
cam plate   ── N6 bolts here; slides into the front cup's bore, seats on
               the shoulder
back plate  ── lip into the front cup's socket (crush ribs); plain back
               face for now
usb cap     ── press-in plug for the USB-C port, pulled by its head
```

1. microSD card into the N6's socket.
2. N6 board onto the cam plate: **2 × M2.5 × 6** into the Ø5.5 thread-forming
   bosses through the board's Ø2.80 mount holes.
3. LOAD lead (a JST-PH to JST-PH cable from the power puck behind this
   camera): plug one end into the N6's LiPo JST-PH connector **now**, while
   the board is still outside, and feed the other end out through the front
   cup's LOAD slot from inside (the slot passes a 5.9 × 4.5 plug). Once the
   plate seats, the connector is 10 mm behind the wall and only reachable
   through the slot with tweezers.
4. Slide the board + plate into the front cup's bore along +Z, taking up the
   lead's slack through the slot, until the plate seats against the
   internal shoulder.
5. Press the back plate into the front cup's socket (6 crush ribs, 0.15/side
   clearance elsewhere) — pushes the plate up against the shoulder and
   closes the case.
6. Press the USB cap into the port when not charging/flashing over USB;
   pull it by its head to plug in a USB-C cable.

## Layout numbers

- X rectangles unchanged from `../case`: OUT −4.302..42.912 (47.214 wide),
  SOCK −1.902..40.512, CAV −0.702..39.312, PLATE = SOCK ∓ 0.20,
  LIP = SOCK ∓ 0.15, BAY = LIP ∓ 1.60.
- Y re-derived for the puck's 80.80 face height: OUT −13.60..67.20
  (80.80), SOCK −11.20..64.80, CAV −10.00..63.60. `TOP_CH` (headroom above
  the board, `CAV_Y1 − BOARD_Y1`) = **18.52 mm**.
- Z stack: back face −16.40 → seam (front cup rim, back plate inner face)
  −14.00 → back plate lip nose / cam plate back −6.50 → cam plate front face
  (shoulder) −3.50 → front cup ceiling 23.50 → front face 25.90. Overall
  depth **42.30 mm**.
- LOAD slot 7 × 6 (r 1.5) at x = 10.00, z = 3.78, directly under the N6's
  side-entry LiPo JST-PH (housing x 7.00..13.00, z 1.30..6.26).
- USB-C port 15 × 9.5 (r 2.5) at x = 23.67, z = 2.53.
- Vents 2.4 × 12 stadiums at z = 8.00, x = 2.9 and 35.5 — moved clear of the
  LOAD slot and the USB port (all three openings' X×Z footprints are
  asserted non-overlapping at import time in `caselib.py`, and re-checked
  with explicit gaps in `check.py`: closest pair is `load_slot`↔`vent_0` at
  2.40 mm).
- USB cap: plug 14.70 × 9.20 × 3.60 (0.15/side, 3.60 deep — WALL + SHOULDER,
  since the port here passes through both), 2 ribs 3.20 tall, head
  18 × 12.5 × 1.50. Bounding box (from `check-v1.txt`):
  `x 14.67..32.67, y −15.10..−10.00, z −3.72..8.78` — plug spans
  y −13.60..−10.00 (flush with the board cavity face) and the head sits
  outside at y −15.10..−13.60, confirming the rotation puts the head
  outside the wall, not inside it.
- Crush ribs: back plate 6 (4 on the X walls at `yc = CY ± 20`, 2 on the Y
  walls at `x = CX`, rotations as `../case back_cup()` uses them), usb cap 2.
  Rib height 6.40 on the lip, 3.20 on the cap, both 0.25 proud on a 0.15 gap.

## Validated (`check.py`, output in `check-v1.txt`)

Run with the cad skill's venv:
`~/.claude/skills/cad/.venv/bin/python check.py` (`--quick` skips the sweep).

- 25 labelled occurrences (4 printed + 21 reference: the 17-solid N6 model,
  the microSD card, the LOAD JST plug + cable mocks, the USB plug mock),
  **55 bound-overlapping pairs, all intersected**.
- All 4 printed parts are single valid solids: front_cup 36384.76 mm³,
  cam_plate 9630.96 mm³, back_plate 11765.00 mm³, usb_cap 791.76 mm³.
- Designed crush only: front_cup ∩ back_plate **15.440 mm³** (6 ribs,
  expected 12.0–21.0), front_cup ∩ usb_cap **2.816 mm³** (2 ribs, expected
  2.0–4.5). usb_cap ∩ usb_plug_mock is reported as alternate states (never
  both present). Every other overlapping pair is 0 (mated reference-internal
  pairs — board/USB-C shell/spacers, microSD/socket, LOAD plug/cable — are
  reported, not flagged).
- Explicit clearances: plate ∩ front_cup = 0, plate ∩ back_plate = 0; lens
  barrel↔aperture radial clearance 1.00 mm; USB shell↔port margin
  x = 2.71, z = 2.67; opening gaps (vents/LOAD/USB) all ≥ 2.40 mm;
  `TOP_CH` 18.52 mm ≥ 0.6.
- 31-step, 1.0 mm slide-in sweep of the cam plate + all 17 N6 solids + the
  microSD card against the static front cup (LOAD plug/cable and the USB
  plug mock excluded — they're threaded through the slot beforehand and
  don't move with the board): **worst intersection 0.00000 mm³**.
- `camera-puck.step` re-imported after export: 4 solids, bounding box
  matches the source compound to 0.00000 mm (≤ 0.01 required).

Overall assembled bounding box (`camera-puck.step`, cap fitted):
`x −4.302..42.912, y −15.10..67.20, z −16.40..25.90` →
**47.214 × 82.30 × 42.30 mm**.

Completion level: **mechanically plausible prototype**. Not printed, no
slicer pass.

## Known compromises and open items

- Back plate's back face is plain by design — the coupling plate that mates
  this camera to the power puck behind it is later work.
- JST-PH plug and USB-C overmold envelopes are estimated, not measured;
  header tail length (3.0) is assumed, inherited from `ref/openmv-n6.py`.
- No feature retains the LOAD lead outside the slot; the LOAD lead's exit
  is a plain slot, not a grommet — same compromise as the power puck.
- The sweep only exercises the board + plate sliding into the front cup;
  it does not model the back plate's own press-fit travel (that's carried
  by the designed crush-rib bound, same as every other lip/rib enclosure in
  this repo).
- Vents have no filter/mesh; they are plain stadium slots.
- Suggested coupon: a patch of the front cup's −Y wall with the LOAD slot,
  a vent, and the USB port + cap, to confirm all three print round and the
  cap's press fit, at the reduced 3.60 plug depth used here.
