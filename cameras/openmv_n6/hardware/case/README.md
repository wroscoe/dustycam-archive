# OpenMV Cam N6 + bq25185 solar charger + 1S LiPo — 3-part printed case

Overall **47.21 × 60.88 × 50.67 mm** (rev E; rev D was 42.30 deep), lens
barrel stands **5.35 mm proud** of the front face. All mm. Frame is the N6
board frame from `ref/DIMENSIONS.md` (origin = PCB bottom-left corner on the
PCB bottom face, +Y toward the lens, +Z along the optical axis). The bottom
of the camera is the −Y wall: USB-C, vents and the DC jack all come through
it.

## Parts

| Part | File | Print orientation | Volume |
|---|---|---|---|
| Front cup | `front-cup.step` / `.stl` | **Face down** (lens face on the bed) | 33.3 cm³ |
| Cam plate | `cam-plate.step` / `.stl` | **Flat, bosses up** (back face on the bed) | 10.8 cm³ |
| Back cup | `back-cup.step` / `.stl` | **Back face down** | 10.6 cm³ |

`n6-case.step` is the assembled view. `fitcheck.step` is a review-only
cutaway with the real N6 model, the vendor bq25185 model, the jack envelope,
the battery, the plugs and the cable mocks inside it.

No supports on any part. The deep socket in the front cup and the 13.9 mm
lip on the back cup are plain vertical walls; the Ø7.52 jack hole is a
horizontal hole in a vertical wall (expect the usual slight sag at its
crown — the panel nut clamps through it regardless).

## Purchased parts

| Part | Source | Confidence |
|---|---|---|
| OpenMV Cam N6 | `ref/openmv-n6.py`, measured from OpenMV's GLB | vendor |
| Adafruit 6091 bq25185 charger, 31.75 × 25.4 × 1.57 PCB, 4 × Ø2.5 holes on 26.67 × 20.32 | `ref/adafruit-6091-…step` (Adafruit CAD, via `sarg cad get sargbench2/adafruit-6091-adafruit-bq25185-usb-dc-solar-lithium-ion-poly`) — not committed, fetch it before running `check.py`/`fitcheck` | vendor |
| Panel-mount DC barrel jack: Ø7.52 hole, 13.0 reach from the outer face | user measurement | measured |
| … its nut Ø12 × 2.5, body Ø10, outside flange Ø11 × 2 | **assumed** — no drawing; drives `NOTCH_W` and `JACK_ZC` | assumed |
| 2 × M2.5 × 6 pan head (N6 → plate) | | |
| 4 × M2.5 × 5 pan head (charger → plate) — **not ×6**, the pilot is blind at 3.8 | | |
| 30 × 40 × 6 1S LiPo pouch | assumed size, see `hardware/batteries.md` | assumed |

## How it goes together

```
front cup  ── straight bore over the board, 1.20 internal shoulder at z = -3.50,
              deep socket below it; DC jack through its -Y wall at z = -15.5
cam plate  ── 5.00 thick, seats on that shoulder; N6 bolts to its front with
              2 × M2.5 × 6, bq25185 bolts to its back with 4 × M2.5 × 5
back cup   ── 13.9 lip presses into the socket and pushes the plate up
              against the shoulder; encloses charger + battery
```

1. Fit the jack into the front cup from outside, nut on the inside. Solder its
   two leads (they go to the charger's DC-in pads) before or after — the nut
   zone is reachable through the open back until the back cup goes on.
2. Bolt the N6 to the plate front: **2 × M2.5 × 6** through the board's Ø2.80
   holes at (3.048, 41.402) and (32.512, 41.402) into the Ø2.10 pilots in the
   bosses (blind at 5.30).
3. Bolt the bq25185 to the plate back, bare side against the plate,
   components facing away, JST edge toward −Y: **4 × M2.5 × 5** into the four
   Ø2.10 pilots (blind at 3.80, 1.20 floor). Board sits at x 3.43…35.18,
   y 9.40…34.80.
4. Plug the LOAD lead into the charger, run it −X under the plate and up
   through the wire slot (x 3–11, y −7.5…−2) to the N6's LiPo connector. Plug
   the BATT lead in; it drops straight down to the pouch. Solder the jack
   leads to the DC-in pads.
5. Slide board + plate + charger into the front cup. The 13 × 11.9 notch in
   the plate's −Y edge passes the installed jack; validated over the full
   insertion travel.
6. Seat the pouch on the back cup floor at the +Y end (y ≥ 4.6 keeps it clear
   of the jack) and press the back cup on. The gap in its −Y lip wall passes
   the jack nut. Friction fit on crush ribs — firm thumb pressure, no tools.

Disassembly: pull the back cup, lift the pouch, then board + plate + charger
come straight out past the jack. The jack never has to come out.

## Rev E (2026-09-12) — solar charger + DC jack

Requirement: carry the Adafruit 6091 bq25185 charger on the back of the cam
plate, put a panel-mount barrel jack up through the bottom directly under it,
keep the battery in the back part, make the case deeper to suit.

- **Plate 3.00 → 5.00.** The charger needs four threaded pilots from the back.
  Bosses on the back face would have put proud features on both faces of the
  plate, which cannot print flat without supporting the whole underside; a
  thicker flat plate with blind pilots keeps the current print orientation.
  Cost: +2.0 depth, +4.7 cm³.
- **Charger bare-side against the plate, components toward the battery.**
  JST plugs go in from the −Y side with the board mounted; the plugs need
  ~8 mm in front of the edge, which sets `CHG_Y0 = 9.40` (jack end + 8).
  The USB-C is enclosed against the +Y end of the bay. The DC/solar input on
  this board is a pair of solder pads, not a connector.
- **Jack** at (x = 19.31, z = −15.50) through the 2.40 socket-zone wall,
  Ø7.52, reaching y = 1.40. Its centre is the middle of the window between
  the plate back (nut 1.00 clear) and the bay floor (0.87 clear).
- **Notches** 13.0 wide (nut Ø12 + 0.5/side) in the plate's −Y edge (to
  y = 2.90) and through the full height of the back cup's −Y lip wall. The
  −Y crush rib became a pair at x = CX ± 12; 7 ribs total.
- **Wire slot** moved to x 3–11 so the LOAD lead passes clear of the nut.
- **Battery** on the bay floor at the +Y end, behind the charger's component
  plane with the same 1.50 swell room as before; 3.2 mm from the jack end.
- Z stack: plate back −8.50 → charger PCB −10.07 → components −14.87 →
  bay floor / seam −22.37 → back face −24.77.

## Rev D (2026-09-02)

The rev C microSD through-slot only worked for inserting the card AFTER
assembly; sliding the board in with a card seated still collided with the
socket-bore wall. Requirement clarified: the card goes in once, before the
camera does, and needs no outside access. So the slot is gone and the +X bore
side now runs **3.60 wide for its full height** (`CARD_CH`, vs 0.60
`BOARD_CLR`) — a card channel like the wire channel. Case is 3.0 wider:
47.21 × 60.88. The wall is fully closed again on that side. Validated with a
40-step slide-in sweep of board + plate + seated card: zero contact over the
full 20 mm of insertion travel.

## Rev C (2026-09-02)

Three usability fixes after review:

- **microSD slot** through the +X wall (13.0 × 3.6) — superseded by rev D.
- **Battery-cable room**: the -Y wire channel doubled 4.0 → 8.0 mm
  (`WIRE_CH`), case grows 4 mm in Y. The plate wire slot grew to 11 × 5.5 and
  passes a mated JST-PH plug.
- **USB-C port** through the -Y wall: 15.0 × 9.5 (r 2.5), centred on the
  receptacle, sized to pass a plug overmold up to 12 × 7. Three of the five
  vents made way for it.

## Rev B (2026-09-02)

Lens aperture opened **Ø15.00 → Ø16.00** (`LENS_HOLE_D`): print 1 of the
RT1062 case (same M12 lens family) bound on the knurled focus ring, ~Ø15.5
actual vs the Ø14.0 barrel in OpenMV's GLB. Fit constants and
`edge_crush_rib()` live in the project-local `fits.py`.

## Fits (from project-local `fits.py`)

| Interface | Value |
|---|---|
| Back cup lip → front cup socket | 0.15/side clearance |
| Crush ribs on the lip | 7 × 6.4 tall × 6.0 long at the seam, 0.25 proud → 0.10/side net crush (18.01 mm³ total) |
| Lip engagement | 13.87 (ribs engage over the last 6.4) |
| Cam plate → socket | 0.20/side |
| Plate bearing on the shoulder | 1.00/side |
| Board → front cup bore | 0.60/side (0.70 at the PCB corners) |
| Lens barrel Ø14.00 → aperture Ø16.00 | 1.00/side (0.25/side on the ~Ø15.5 focus knurl) |
| Jack bushing → Ø7.52 hole | user's number; nut and flange clamp the 2.40 wall |
| Jack nut → plate / lip / plate notch | 1.00 above, 0.5/side in both notches |
| Lead-in chamfers | 0.60 × 45° on the socket mouth and the lip nose |
| Elephant-foot chamfer | 0.40 × 45° on every bed-contact perimeter |

Walls 2.40 (6 perimeters); lip wall 1.60 (4 perimeters); plate 5.00.

## Battery bay

**38.91 × 52.58** in plan, **7.50** deep behind the charger's component plane
(6.00 pouch + 1.50 swell/wire room). The pouch sits on the back cup floor at
the +Y end. Nothing rigid bears on it at nominal thickness; if it swells past
1.5 mm it meets the flat tops of the charger's JST housings, not an edge.
Change `BAT_T` in `caselib.py` if the real pack is thicker — the case depth
follows it 1:1.

## Vents and openings

Two 2.40 × 12.00 stadium slots through the bottom (−Y) wall of the front cup
at z = 8.00, the 15.0 × 9.5 USB-C port, and the Ø7.52 jack hole at
z = −15.5. The microSD, the charger's USB-C, the USER/PWR buttons and JTAG
are enclosed. Focus can be adjusted with the case shut (barrel proud, lock
ring captive behind the Ø16.00 aperture).

## Validated (`check.py`, output in `check-revE.txt`)

Run with the cad skill's venv:
`~/.claude/skills/cad/.venv/bin/python check.py` (`--quick` skips the sweep).

- 29 labelled occurrences, 74 bound-overlapping pairs, all intersected.
- 0 interference between any case part and any of the 17 N6 solids, the
  56-solid vendor charger model, the jack envelope, the battery, the two JST
  plug mocks, the LOAD and BATT cable mocks, the seated SD card, the seated
  USB plug.
- Front cup ∩ back cup = 18.01 mm³, entirely the designed crush-rib
  interference (7 ribs). Front cup ∩ plate and back cup ∩ plate both 0.
- 31-step, 1.0 mm slide-in sweep of plate + N6 + charger + plugs + cables +
  card against the front cup and the installed jack: 0.00000 mm³ worst case.
- All three parts are single valid solids.
- The seven non-zero pairs *inside* the reference set (N6 PCB vs its own
  mid-mount USB-C / press-in spacers, plug-in-socket, card-in-socket,
  cable-in-plug) are declared as mated pairs in `check.py`, not ignored.

Completion level: **mechanically plausible prototype**. Not printed, no
slicer pass yet.

## Known compromises and open items

- **Jack envelope is assumed.** Hole and reach are measured; nut Ø12,
  body Ø10 and flange Ø11 are guesses that size both notches and the jack's Z.
  Measure the real nut across corners before printing; a bigger nut widens
  `NOTCH_W` and pushes `JACK_ZC` (the window is only 12.9 tall for a Ø12 nut).
- **JST-PH plug envelope** (5.9 × 4.5, 6.0 proud) is estimated.
- M2.5 × 5 into a 3.80 blind pilot gives 3.43 of thread — adequate for a
  10 g board, but ×6 will bottom out / break through the 1.20 floor.
- Battery is assumed 30 × 40 × 6 and is not located in plan; tape it to the
  back cup floor.
- The front cup ceiling is still set by the M12 lens holder; ~13 mm of dead
  air above the board at the USB end remains.
- Board is held by 2 screws at the lens end only; the two anti-bow pads have
  not been checked against unmodelled bottom-side passives.
- PCB thickness 1.30 and header-tail length 3.00 come from the vendor model /
  assumption, not a caliper.
- Suggested coupon before a full print: the front cup's −Y wall (jack hole +
  USB port + vents, ~12 × 30 mm patch, 2.4 thick) to confirm the jack nut
  clamps and the hole crown prints clean.

Rev D source and exports are archived in `archive/revD/`.
