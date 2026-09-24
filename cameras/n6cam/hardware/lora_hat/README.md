# N6 LoRa hat

A plug-on hat for the OpenMV Cam N6 that adds a MeshCore-capable LoRa radio
(Ebyte E22-900M22S, SX1262 + 32 MHz TCXO, +22 dBm) on the N6's SPI2 shield
header, so `n6cam` can post detections/status to the existing mesh
(`CornsnowBase`) and receive short commands without a phone or WiFi in
range. Radio-only design (no second MCU) — see `PLAN.md` §0 for why. Fits
inside the camera puck (`../camera_puck/`) unchanged.

Built in tscircuit (`tsci` 0.0.2516) per the executable plan in `BUILD.md`,
then revised after a design review (fab-blocking via sizes, clearance,
open RF stubs, a routing-quality root cause in the expansion header, and
some cosmetic fixes — see "Deviations").
Status: **designed and verified in software (netlist, DRC, mechanical
fitcheck). Clearance was then closed on 2026-09-13 evening (see "Clearance: how it was
closed"); the earlier text "one real, unresolved finding remains (same-layer clearance,
see "Verification results" #6e) — this determines whether the board is
ordered as-is or finished in KiCad. Nothing ordered.** Gate 1 (header pin
map / RAW-vs-GND / LED position, PLAN.md §8) must also be confirmed on a
physical board before ordering — see "Open gates" below.

## What's on it

One SX1262 module, a 74LVC1G04 inverter that derives RXEN from DIO2 (no N6
pin spent on the RF switch), pull-up/pull-down housekeeping, a u.FL jack
for an external antenna, and an unpopulated 1x10 expansion row exposing
I2C2/UART3/UART7/WKUP pins for a future PIR experiment. Two 2x8 male
headers mate to the N6's female shield sockets; a 1.6 mm, 2-layer, 36.0 x
28.5 mm board with a bottom-layer GND pour.

## Pin map

| N6 pin | Hat net | Function |
|---|---|---|
| P0 (SPI2 MOSI) | SPI_MOSI | radio MOSI |
| P1 (SPI2 MISO) | SPI_MISO | radio MISO |
| P2 (SPI2 SCK) | SPI_SCK | radio SCK |
| P3 (SPI2 NSS) | SPI_NSS | radio NSS, 10k pull-up to 3V3 |
| P7 | RADIO_NRST | radio NRESET, 10k pull-up to 3V3 |
| P8 | RADIO_BUSY | radio BUSY (in) |
| P9 | RADIO_DIO1 | radio DIO1 / IRQ (in) |
| P4, P5 | EXP_P4, EXP_P5 | expansion row (I2C2/UART3), unpopulated |
| P11, P13, P14 | EXP_P11/P13/P14 | expansion row (WKUP3/UART7), unpopulated |
| WKUP2, RAW, BOOT0 | EXP_WKUP2/RAW/BOOT0 | expansion row, unpopulated |
| 3V3, GND (both headers) | V3V3, GND | power |
| P6, ETH_*, P10, P15-P18, RESET, VIN | — | not connected (reserved/N6-only) |

Radio-internal: `U2.DIO2` drives `TXEN` directly and `U1` (inverter) derives
`RXEN = NOT DIO2`, so the RF switch runs with no N6 GPIO. `U2.ANT` (50 ohm
stamp pad) -> `R5` (0 ohm series, 0402) -> `J4` (u.FL): a single straight
top-layer trace per hop, 2.68 mm total (BUILD.md's original DNP hedge pads
C3/C4 were **deleted per review** — see Deviations).

**J3 expansion row, pin order** (changed per review from PLAN.md's table
order — see Deviations): pins 1-4 are J1's four signals (P4, P5, WKUP2,
RAW), pins 5-8 are J2's four signals (P13, P14, P11, BOOT0), pins 9-10 are
3V3/GND. Grouping by which header a signal comes from keeps every
expansion trace short and off the RF run.

| J3 pin | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Signal | P4 | P5 | WKUP2 | RAW | P13 | P14 | P11 | BOOT0 | 3V3 | GND |
| From | J1 | J1 | J1 | J1 | J2 | J2 | J2 | J2 | — | — |

## BOM (v1, JLCPCB assembly)

| Ref | Part | Package | LCSC | Assembled |
|---|---|---|---|---|
| U2 | Ebyte E22-900M22S (SX1262, TCXO, +22 dBm) | 20x14mm castellated | C411293 | yes (Extended, ~$3 fee) |
| U1 | SN74LVC1G04DBVR inverter | SOT-23-5 | C7827 | yes |
| J4 | Hirose U.FL-R-SMT-1(10) | SMD | C88373 | yes |
| R1, R2 | 10k | 0603 | C25804 | yes |
| R3, R4 | 100k | 0603 | C25803 | yes |
| R5 | 0 ohm | 0402 | C17168 | yes |
| C1 | 10uF | 0805 | C15850 | yes |
| C2 | 100nF | 0603 | C14663 | yes |
| J1, J2 | 2x8 male header, 2.54mm, >=6mm mating pins | THT | — | **no (hand-solder)** |
| J3 | 1x10 pin header, 2.54mm | THT | — | **no (unpopulated)** |
| — | Molex 211140-0100 flex antenna (v1) | — | DigiKey/Mouser | off-board |

10 SMD/SOT/THT-castellated refs go through JLCPCB assembly (all on the top
side); J1/J2/J3 are bought separately and hand-soldered. (v1 had DNP hedge
pads C3/C4 for a future antenna matching network; they were **deleted per
review** — see Deviations.) `dist/jlcpcb/bom.csv` and `pick_and_place.csv`
reflect exactly this split (see "Verification results" below).

## Files

```
index.circuit.tsx          the board: headers, module, RF chain, nets, routing, pour, silk
imports/E22_900M22S.tsx    hand-built E22 footprint (22 castellated pads)
imports/UFL_R_SMT.tsx      u.FL footprint, built from the real C88373 land (see Deviations)
imports/N6Header2x8.tsx    J1/J2 generator: literal N6 header coordinates + net aliases
imports/ref/*.import.tsx   raw `tsci import` output, kept only for the Phase 1 pad diff
fit/lora_hat_mock.py       build123d envelope appended to the camera_puck fitcheck
tools/check_hat.mjs        circuit.json verifier (netlist, hole map, outline, copper zones,
                           via size/count, RF path length, same-layer clearance)
tools/export.mjs           tsci export x3 (netlist/step/gerbers) + unzip bom/cpl
nets.expected.txt          expected net membership, diffed by tools/check_hat.mjs
dist/lora_hat.step         STEP export (also consumed by fit/lora_hat_mock.py)
dist/lora_hat.netlist      readable-netlist export
dist/jlcpcb/               gerbers zip + unzipped bom.csv / pick_and_place.csv
__snapshots__/             PCB/schematic/3D snapshots (tsci snapshot --update)
```

## Verification results

All commands run from this directory, global `tsci` 0.0.2516, no
`node_modules` installed (per the task's toolchain constraint).

### Phase 1 — footprint diffs

- **E22-900M22S vs `tsci import --jlcpcb C411293 --use-exact-footprint`**
  (kept at `imports/ref/E22_900M22S.import.tsx`): all 22 pads match to
  **0.000014 mm** (floating-point noise on the import's own inch->mm
  conversion). Hand-built footprint used as-is.
- **U.FL vs `tsci import --jlcpcb C88373 --use-exact-footprint`** (kept at
  `imports/ref/U_FL_R_SMT_1_10_.import.tsx`): same 3-pad topology (signal
  pad on one side, two bonded GND pads straddling y=0 on the other), but
  the import's signal pad is **0.725 mm off-center and 0.45 mm wider**
  than BUILD.md's hand-built placeholder (`-0.800` vs `-1.525` local x;
  `1.50x1.10` vs `1.05x1.00`). Per BUILD.md Phase 1 ("if the import's
  signal pad is offset differently by > 0.1 mm, use the import's
  numbers"), `imports/UFL_R_SMT.tsx` uses the import's exact pad
  coordinates; J4 was re-placed to compensate (see Deviations).
- **SOT-23-5 (U1)**: the `tsci import --jlcpcb C7827` pin order/labels
  (`pin1=NC, pin2=A, pin3=GND, pin4=Y, pin5=VCC`) match the footprinter
  `sot23_5` string used in `index.circuit.tsx` exactly — no substitution
  needed.

### Phase 2 — frame calibration

Calibration build (board + J1 + J2 only) confirmed **Option A**: from
`dist/index/circuit.json`, `pcb_board.center = (0, 0)`, `pcb_board.outline`
matches the four literal points, and all 32 header holes land at their
literal N6 coordinates with **0 error / 0 placement error**. No Option B
offset needed.

### Phase 4 — the verification checklist (updated after the design review)

| # | Check | Command | Result |
|---|---|---|---|
| 1 | Build clean | `rm -rf .tscircuit/cache && tsci build index.circuit.tsx` | **0 errors.** Only cosmetic warnings (naming-convention nags, missing schematic refdes text, one `pcb_connector_not_in_accessible_orientation_warning` for J4 -- expected, u.FL is not edge-mounted) |
| 2 | Netlist | `tsci check netlist` (clean) + `tools/check_hat.mjs` net-membership diff vs `nets.expected.txt` | **All 19 declared nets match membership exactly; all 13 NC pins confirmed not connected.** |
| 3 | Pin map | `tools/check_hat.mjs`: 32 `pcb_plated_hole` vs the literal table | **32/32 holes, max \|delta\| = 0.000000 mm** |
| 4 | Pads inside outline | `tools/check_hat.mjs`, inset 0.3 mm | **88/88 pads and holes inside, 0 violations** |
| 5 | Placement DRC | `tsci check placement` | **Errors: 0.** Same 1 warning as #1. |
| 6 | Shorts | `tsci check shorts` | **No shorts detected.** |
| 6a | Copper zones (segment/rect **clipping**, not endpoint-in-rect) | `tools/check_hat.mjs` | **0.000 mm** of bottom-layer copper clipped inside the RF rectangle (x 5..13, y -3..2.5); **0.000 mm** of non-U2 top-layer copper clipped inside the module ANT-end rectangle (x 11.3..25.3, y -2.5..1.5). Both **fail-on-nonzero** now (previously informational). |
| 6b | Via size | `tools/check_hat.mjs` + `unzip -p dist/jlcpcb/lora_hat-gerbers.zip '*.drl' \| grep '^T.*C'` | **0 undersized vias**; drill tool list is exactly `1.0` (header/mount holes), `0.3` (vias), `3.0` (H1/H2) -- no 0.2 mm tools remain. |
| 6c | Via count | `tools/check_hat.mjs` | **20** (was 40; fails at >= 25). |
| 6d | RF path length, computed from circuit.json | `tools/check_hat.mjs` | `U2.ANT -> R5.pin2`: 1.390 mm, straight (routed length == point-to-point distance). `R5.pin1 -> J4.SIGNAL`: 1.290 mm, straight. **Total 2.680 mm <= 3 mm.** No stub traces (C3/C4 deleted). |
| 6e | Same-layer clearance (`tools/check_hat.mjs`, all pad/via/ring/trace pairs) | `tools/check_hat.mjs` | **PASS: minimum same-layer, different-net gap 0.142 mm** (JLC min 0.127), 0 pairs below. Achieved with `minTraceToPadEdgeClearance` + `minViaEdgeToPadEdgeClearance` = 0.15 mm and `autorouterEffortLevel="2x"` — see "Clearance: how it was closed". |
| 6f | Pour coverage under the RF run (informational) | `tools/check_hat.mjs` | **100.0%** coverage under x 7.6..11.3, y -1..0.5 (target >= 90%). |
| 7 | Silkscreen / orientation | `tsci snapshot` (pcb, bottom, top-down, right-sideview) rasterized and inspected | **Confirmed**: +Y is up, header pins span y 1.6..19.4 with the expected empty strip above, "LENS UP" at +Y, J3 + "USB DOWN" at the -Y overhang, module ANT end / J4 at the bottom-left of the module, no mirroring in the 3D top-down view. "ANT" silk moved off the ANT pad's copper into the module's empty IPEX-notch area; "N6 LORA HAT v1" moved off U2's REFDES text (was colliding at ~(18.3,18.5)). The black-triangle 2D-render artifact seen in the pre-review build is **gone** in the current render (root cause never identified; not present in gerbers either way -- `grep -c "G36\|G37" F_SilkScreen.gbr` still returns 0). |
| 8 | Mechanical | `../camera_puck/check.py` | **CHECK PASSED** (re-run after all review fixes; J4/module positions unchanged so the result is identical to before -- see below). |
| 9 | Fab files | `dist/jlcpcb/lora_hat-gerbers.zip` unzipped | `bom.csv`: LCSC filled for exactly U1, U2, J4, R1-R5, C1, C2 (10 rows); J1/J2/J3 **absent** (marked `doNotPlace`; C3/C4 no longer exist). `pick_and_place.csv`: same 10 designators, all `Layer=top`. |

`tools/check_hat.mjs` full output: **`CHECK PASSED`** (second pass; the
first pass failed only on #6e, see "Clearance: how it was closed").

## Clearance: how it was closed (2026-09-13, second pass)

The earlier state had 32 same-layer gaps at 0.115 mm (the autorouter's
default floor). Reading `@tscircuit/core` + `@tscircuit/capacity-autorouter`
0.0.900 showed what the router actually consumes:

- `autorouter={{ traceClearance }}` is **stored only** (goes into
  `pcb_group.autorouter_configuration`) and never reaches the router.
- `minTraceToPadEdgeClearance` and `minViaEdgeToPadEdgeClearance` on
  `<board>` **do** reach it (obstacle margins, the routing DRC engine, the
  repair solver). Setting both to 0.15 mm lifted the floor to ~0.145 mm.
- `autorouterEffortLevel`: 1x left one via the repair pass could not fix
  (0.023 mm to a MISO trace); **2x** routes clean (0 DRC errors, 22 vias,
  min gap 0.142 mm, reproducible from a cold cache); 5x is *worse* (9
  gaps) — the router is not monotonic in effort, so the value is pinned.
- `<keepout>` is voided by the copper-pour solver unconditionally and
  blocks *every* net for the router (`excludeRefs` only affects DRC).
  With real clearances the router needs the bottom layer to bridge U2's
  two GND pads around the ANT pad, so the previous big bottom keepout and
  the both-layer module-ANT-end keepout were either violated (GND vias in
  the keepout) or, when trimmed, cost the ground under the RF run
  (`dist/pour_map.png` showed 3.5 % pour coverage there). A GND via fence
  was tried and rejected: `connectsTo="net.GND"` vias become routing
  targets (55 vias) and the planner still crossed one.
- Final protection of the RF corner: **top-only** keepouts above/below
  the RF strip (x 8.0…10.2) and over the module's ANT end (x 12.3…25.3),
  plus two **thin bottom strips** 1.2 mm above/below the RF trace
  (y 1.0…1.5, −2.0…−1.5). The pour directly under the run is solid and
  connected on both sides (100 % coverage in the checker), and
  `tools/check_hat.mjs` fails on any non-GND bottom copper or non-RF top
  copper in the critical zone x 6.5…12.5, y −1.5…1.0 (segment clipping,
  not endpoint tests).

Result: `tsci build` 0 errors, `tsci check netlist/placement/shorts`
clean, `node tools/check_hat.mjs` **CHECK PASSED** (22 vias all 0.3/0.6,
RF run 2.68 mm straight on top, min clearance 0.142 mm), drill tools
1.0 / 3.0 / 0.3 only, `../camera_puck/check.py` **CHECK PASSED**.
`dist/pour_map.png` = bottom pour + traces + keepouts + RF zone, rendered
from circuit.json.

## Deviations from BUILD.md

1. **J4 (u.FL) placement moved 0.45 mm** from BUILD.md's literal
   `(6.35, -0.23)` to `(6.80, -0.229)`. Cause: BUILD.md's hand-built u.FL
   footprint (1.05 mm signal pad) was a placeholder; Phase 1's own
   diff-and-substitute rule says to use the real C88373 land (1.50 mm
   signal pad) once the offset exceeds 0.1 mm. With the wider real pad at
   BUILD.md's literal position, the signal pad's courtyard overlapped R5's
   by ~5 um (a real `tsci check placement` error). The move keeps the same
   ~0.26 mm gap from J4's GND pads to the J1 header ring that BUILD.md's
   numbers implied, and keeps a clean gap to R5. `fit/lora_hat_mock.py`
   uses this same real coordinate for the u.FL/plug mechanical envelope.
2. **R4/C2/R3/C1 shifted along Y only** (100k RXEN pulldown / decoupling
   cluster near U1): R4 7.0->6.5, C2 14.0->14.3, R3 13.4->14.2, C1
   15.6->17.6. Cause: BUILD.md's literal coordinates were computed from
   part *centers* without accounting for real footprint courtyards; once
   U1's real SOT-23-5 courtyard (a stepped ~3.4x4.1 mm clearance halo, not
   a plain rectangle) and R3/C1's own courtyard rects are in the picture,
   the literal numbers left < 0.15 mm (R4/C2 vs U1) or a small negative
   gap (R3 vs C1) -- both real `tsci check placement` errors. Topology and
   X positions unchanged.
3. **C3/C4 (DNP RF hedge shunts) deleted per review — stubs.** The v1
   design (both BUILD.md's literal placement and this project's first
   pass) had C3/C4 as DNP 0402 hedge pads, wired as side-stubs off the
   RF_ANT/RF_UFL nets. Review found this produced real open copper stubs:
   the ANT net carried a ~6 mm loop under the module's antenna corner out
   to C3, and the u.FL net carried a ~7 mm stub out to C4 -- both are
   unterminated antenna-like stubs sitting right on the RF path, which is
   worse for RF integrity than having no hedge pads at all. Deleted C3,
   C4, their traces, and `imports/Shunt0402DNP.tsx` entirely. `RF_ANT` is
   now exactly `U2.ANT<->R5.pin2` and `RF_UFL` exactly
   `R5.pin1<->J4.SIGNAL`, each a single straight top-layer segment (see
   Phase 4 check 6d) -- if a matching-network hedge is wanted later it
   should be added back as an actual in-line series/shunt at the same
   spot, not a dangling side pad.
4. **J1, J2, J3 marked `doNotPlace`.** Without it the JLCPCB parts engine
   auto-matched a real LCSC part (`C492422`) to J3's footprint and
   included J1/J2/J3 in `bom.csv` with blank LCSC fields, which would
   confuse a JLC assembly order (BUILD.md Phase 4 check #10 wants them
   "absent or DNP"). Not a topology change -- these were always
   hand-solder/unpopulated per BUILD.md's own BOM.
5. **J3 (expansion row) pin order changed** from PLAN.md §3 / BUILD.md's
   table order (interleaved: pins 3/4/5 = J2's P13/P14/P11, pins 6/7 =
   J1's WKUP2/RAW, pin 8 = J2's BOOT0) to **J1's four signals on pins
   1-4 (P4, P5, WKUP2, RAW), J2's four signals on pins 5-8 (P13, P14,
   P11, BOOT0)**. Cause: the interleaved order forced `EXP_RAW`,
   `EXP_WKUP2` and `EXP_P5` to run 7-8 mm diagonally on the bottom layer,
   directly under the ANT->R5->J4 run, before the review. Grouping by
   source header keeps every expansion trace a short, direct hop from its
   own header edge to J3 and off the RF run entirely (Phase 4 check 6a:
   0.000 mm of bottom-layer copper under the RF run, down from 15
   segments before). Silk labels and `nets.expected.txt` updated to
   match; PLAN.md's own §3 table is not re-edited pin-by-pin (kept as the
   original design record) but is stale on this one point.
6. **Fab-blocking / clearance fixes** (first pass; the clearance item was
   closed in the second pass, see "Clearance: how it was closed" — the
   keepout arrangement described below was replaced there too).
   - `minViaHoleDiameter="0.3mm"` / `minViaPadDiameter="0.6mm"` added to
     `<board>`: **confirmed honored** by the router -- every via is now
     >= 0.3 mm hole / 0.6 mm pad (was 36/40 undersized at 0.2/0.3 mm),
     confirmed both in `circuit.json` and in the actual drill file
     (`unzip -p ... '*.drl' | grep '^T.*C'` -> only `1.0`, `0.3`, `3.0`
     tools). Via count dropped from 40 to a stable **20** as a side
     effect (fewer, bigger vias fit fewer places, so the router found
     more direct paths) -- comfortably inside the ~18-25 target and under
     the checker's fail threshold of 25.
   - `autorouter={{traceClearance:"0.15mm"}}` added to `<board>`:
     **confirmed NOT honored.** The minimum same-layer, different-net gap
     is 0.115 mm whether or not `traceClearance` is set (tested both
     ways, same result to 3 decimal places), and 32 pairs sit below the
     0.127 mm JLC 2-layer minimum (full list: Phase 4 check 6e / `tools/
     check_hat.mjs` output). This is a real, unfixed finding -- per the
     review's own framing, **this decides whether the board is finished
     in KiCad** before ordering rather than ordered straight from this
     tscircuit output. Things tried and rejected because they made
     placement worse, not better (the router does not appear to use
     these as routing-time constraints, only as post-hoc DRC
     thresholds -- so they moved the violation boundary without finding a
     better path): `minTraceToPadEdgeClearance="0.15mm"` alone (3 new
     placement errors, via count up to 24); together with
     `minViaEdgeToPadEdgeClearance="0.15mm"` (7 new errors, via count up
     to 20 but different failures). Both were reverted.
   - Two `<keepout>` elements added (bottom-layer over the RF rectangle
     x 4.5..13.5/y -3.2..3.2 with `excludeRefs={[".J1",".J4"]}` so J1's
     own GND ring and J4 aren't blocked; both-layer over the module's
     antenna end x 11.3..25.3/y -2.5..1.5 with `excludeRefs={[".U2"]}`
     so U2's own pads still route). Both **confirmed honored** -- routing
     visibly detours around them (see the hatched regions in
     `dist/index/pcb.png`) and the copper-zone check (6a) reads 0.000 mm
     in both rectangles. The GND via fence (4 manually placed vias, V1-4)
     that pre-existed inside the same footprint as the new bottom keepout
     was **removed**: `excludeRefs` only worked for named components
     (`.J1`, `.J4`), not for bare `<via>` elements, and the keepout
     already gives the GND-under-RF isolation those vias were for (6f:
     100% pour coverage under the ANT->u.FL span without them).
   - A third, small, both-layer keepout was added at
     `(10.0, 11.05)`, 0.8 x 1.7 mm, `excludeRefs={[".U2"]}`: after the via
     resize, the router kept jamming an oversized (0.6 mm pad) via into
     the ~0.37 mm pocket between U2's adjacent left-column pads (MISO at
     y=10.42, NRST at y=11.69), producing a genuine
     `pcb_pad_pad_clearance_error` (0.021-0.094 mm, below the 0.1 mm
     baseline minimum). A first attempt at a bigger keepout spanning the
     whole left column (1.5 x 16 mm) over-corrected and caused *worse*
     regressions -- 11 errors including accidental-contact shorts between
     U2's own GND pins -- and was reverted; the small, targeted keepout
     fixed exactly the one pinch point with 0 new errors.
7. **Copper-pour islands**: still 2 (main pour ~976 mm^2, one isolated
   ~6.5 mm^2 sliver elsewhere on the board), not 1. Not the RF-run area
   specifically -- that reads 100% covered (6f) -- so this is unrelated to
   the review's RF-integrity concern. BUILD.md's Phase 4 check #7 doesn't
   name pour-island count as a pass/fail criterion; isolated GND-shaped
   copper is electrically harmless (same net, not a different one) and
   JLC will not reject it. Bump `padMargin`/`boardEdgeMargin` on the
   `<copperpour>` if a single unbroken pour is wanted.
8. **Cosmetic silkscreen fixes**: the E22 footprint's "ANT" label used to
   sit directly on the ANT pad's own copper (local `(-7.0,-7.23)` = global
   `(11.3,-0.23)`, exactly the pad center) -- moved into the empty
   IPEX-notch cutout at local `(-3.2,-5.5)`. The board title "N6 LORA HAT
   v1" used to collide with U2's REFDES silk text (both landed at
   ~`(18.3,18.5)`) -- moved the title to `(9.0, 18.6)`. Both are silk-only
   changes with no copper/DRC effect.
9. **A previously-reported cosmetic-only rendering artifact (a filled
   black triangle over the module footprint in the 2D PCB PNG/SVG
   preview) is no longer present** after the review's changes. Root cause
   was never identified (it persisted through courtyard/cadModel/supplier-
   info removal in the earlier round), so this is reported as an
   observation, not a fix -- it may return with unrelated future edits.
   Confirmed absent from the actual gerbers either way
   (`grep -c "G36\|G37" F_SilkScreen.gbr` -> 0, no filled silkscreen
   region was ever emitted). The bottom-layer 2D snapshot still doesn't
   visually fill the GND copper pour (shows only routed traces), while
   `B_Cu.gbr` is far larger than `F_Cu.gbr` -- consistent with the pour
   being present in the real gerber but not rendered by the 2D preview.
10. **BUILD.md Phase 6 and PLAN.md §5 step 3 corrected**: "12 placed
    parts" -> "10 placed parts" (BUILD.md never named more than 10:
    U1, U2, J4, R1-R5, C1, C2 -- the same list Phase 4 check #10 uses);
    "36 x 27" -> "36 x 28.5" (matching the board's actual outline and
    PLAN.md §3's own "Hat outline 36.0 x 28.5 mm").

None of these deviations change a net or a pin's electrical function.
Deviations #1, #2, #4, #8, #9 are placement/silk nudges or `doNotPlace`
flags with no topology change. #3 and #5 are real design corrections from
the review (an open RF stub removed, a routing root cause fixed). #6 is
the substantive fab-readiness work: two of its three sub-fixes are
confirmed working (via size, keepouts); the third (`traceClearance`) is a
stored-only prop — closed in the second pass with the props the router
actually reads (`minTraceToPadEdgeClearance`, `minViaEdgeToPadEdgeClearance`)
and `autorouterEffortLevel="2x"`.

## Open gates (PLAN.md §8) -- do these before ordering

1. **Pin map on the real board** (5 min, no parts needed): read the
   silkscreen next to both N6 headers and confirm P0..P6 on the left outer
   column, P7..P11 on the right outer column, RAW/WKUP2 on the left inner
   column. Meter the four n=0 pins for GND (expect x 4.14 and 34.0 only)
   and check voltage at (4.14, 4.139) on USB power -- PLAN.md §3 flags a
   conflict between the pinout PNG (RAW, 3.6-5V) and `OPENMV_N6.json`
   (GND) at that exact position. Also locate the status LEDs; cut a
   silkscreen/board window only if one falls inside the hat's footprint.
2. **E22 pad-numbering direction**: confirm pin 1 is the corner opposite
   the IPEX/ANT corner, on the same long side as pins 6-9 (matches
   EasyEDA), and check continuity pad 12 <-> pad 1 (both GND) on a
   physical module before soldering.
3. **TCXO voltage / RXEN-TXEN-via-inverter choice**: firmware-only checks
   (`SetDIO3AsTCXOCtrl`, `GetDeviceErrors` for `XOSC_START_ERR`; sleep
   current vs the inverter's ~1 uA draw) -- no hardware change expected.
4. **Standby / SPI2 bring-up / RX window / TX current / range /
   coexistence** -- PLAN.md §8 items 3-8, all bench work with the
   assembled hat plugged into a live N6.
5. **Before ordering:** the clearance item is closed (min gap 0.142 mm).
   Also eyeball the header ring gaps (0.84 mm, BUILD.md risk #9) in the
   same pass.

## Regulatory note

The module runs under its own grant at the mesh's preset and power, like
every other node on this mesh; this is a one-off hobby device, not a
product.
