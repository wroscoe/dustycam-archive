# N6 LoRa hat — tscircuit build plan (2026-09-13)

Companion to `PLAN.md` (design intent). This is the executable plan for turning
§2–§5 of PLAN.md into a JLCPCB-orderable tscircuit project. Frame throughout:
N6 board frame (`../camera_puck/ref/DIMENSIONS.md`). All mm. Toolchain:
`tsci` 0.0.2516 global; `tsci export` formats include `step`, `gerbers` (zip
**contains `bom.csv` + `pick_and_place.csv`**, JLCPCB flavour),
`readable-netlist`; `tsci check netlist|placement|shorts|trace-length` exist;
`tsci build --pcb-png --3d-png` writes PNGs without a dev server.

## Facts established (sources) — do not re-derive

| Fact | Value | Source |
|---|---|---|
| E22-900M22S pin table | 1–5 GND, 6 RXEN (in, high=RX), 7 TXEN (in, high=TX, "MCU IO **or DIO2**"), 8 DIO2, 9 VCC 1.8–3.7 V, 10–12 GND, 13 DIO1, 14 BUSY, 15 NRST, 16 MISO, 17 MOSI, 18 SCK, 19 NSS, 20 GND, 21 ANT (stamp, 50 Ω), 22 GND | Ebyte manual v1.0 and v1.3 (`pdf-down.aspx?id=1822`, rcscomponents v1_3), identical tables. **12 = GND, 15 = NRST.** |
| Size / pitch / currents | 20 × 14 × 3.0 mm, 1.27 mm stamp pitch, TX 119 mA, RX 6.8 mA, sleep 2 µA, "DIO3 is powered by a 32 MHz TCXO" — **voltage not stated** | manual §2.2, §4.1 |
| TCXO voltage used by working designs | 1.8 V (`SX126X_DIO3_TCXO_VOLTAGE 1.8 // E22 series TCXO reference voltage is 1.8V`) | MeshCore `variants/generic-e22/variant.h`; Meshtastic `variants/nrf52840/diy/nrf52_promicro_diy_tcxo/variant.h` (same, plus `DIO2_AS_RF_SWITCH`, `TXEN = NC` "assuming DIO2 is connected to TXEN", RXEN from MCU) |
| EasyEDA footprint C411293 (`WIRELM-SMD_E22-900M22S`, 3D model H3.0) | 22 rect pads 1.800 × 0.900, two columns at x = ±7.000; y (y-up, mm): pins 1..11 at −8.50, −7.23, −5.96, −0.39, +0.88, +2.15, +3.42, +4.69, +5.96, +7.23, +8.50; pins 12..22 mirror (12 at +8.50 … 22 at −8.50). Pin 1 = right column, −Y end; pin 21 ANT = left column, y −7.23. Outline x ±7.0, y −9.5…+10.5. Shield silk x ±5.08, y −7.375…+9.135 with IPEX notch x −5.08…−1.27, y −7.375…−3.565 | `easyeda.com/api/products/C411293/components?version=6.4.19.5`, raw PAD/TRACK strings; 10 mil units × 0.254, y negated |
| N6 header map | right outer x 34.0: RESET, P11, P10, **P9, P8, P7**, VIN, GND (n = 7…0); left outer x 1.6: P0…P6, 3V3; right inner: P18…P15, P14, P13, BOOT0, 3V3; left inner: LED, RX−, RX+, TX−, TX+, WKUP2, **RAW (PNG) / GND (JSON)**, GND | `openmv-n6-pinout` PNG (local copy `~/.config/OpenMV/openmvide/html/_images/pinout-openmv-n6-pag7936.png`) and `openmv-boards/pinouts/OPENMV_N6.json` (`R_2-6 P7 PG13`, `R_2-5 P8 PD13`, `R_2-4 P9 PG12`, but `L_2-7 = GND`). PLAN §3 matches the PNG. |
| Parts | U1 SN74LVC1G04DBVR = **C7827**; J4 U.FL-R-SMT-1(10) = **C88373** (U.FL-R-SMT(10) = C434808, same land); E22 = C411293, **Extended** | JLCPCB/LCSC pages |
| footprinter `sot23_5` pin order | pin1 (−w/2,+p) top-left, 2 mid-left, 3 bottom-left, 4 bottom-right, 5 top-right — same as KiCad SOT-23-5 → SN74LVC1G04: 1 NC, 2 A, 3 GND, 4 Y, 5 VCC | footprinter `getCcwSot235Coords`, `/usr/share/kicad/footprints/Package_TO_SOT_SMD.pretty/SOT-23-5.kicad_mod` |
| Hirose u.FL land | pin1 (signal) 1.05 × 1.00 at (−1.525, 0); pin2 GND 2.20 × 1.05 at (0, ±1.475) | `/usr/share/kicad/footprints/Connector_Coaxial.pretty/U.FL_Hirose_U.FL-R-SMT-1_Vertical.kicad_mod` (Y sign irrelevant, symmetric) |
| tscircuit core behaviour | `outline` points are used as-is (not recentred unless inside a `<panel>`); board `center` = board pcbX/pcbY (+outlineOffset), default (0,0); a board's own `pcbX/pcbY` **also translates its children**; trace-outside-board and pour bounds use the outline polygon; STEP export uses the outline polygon, PCB spans z ±thickness/2; copper pours are rendered after routing and absorb GND trace segments inside them | `@tscircuit/core/dist/index.js` (Board autosize, `isRouteOutsideBoard`, `markTraceSegmentsInsideCopperPour`), `@tscircuit/cli` `circuitJsonToStep` |

## PLAN.md corrections (applied 2026-09-13)

1. **§3 "Ø3 hole at each +Y corner" is impossible** — the +Y corners are the header bodies and the P0/RESET pins (1.6, 19.379)/(34.0, 19.379). Holes go in the −Y overhang corners (numbers below).
2. **§3 outline lets the hat plug in rotated 180°.** Rotation about the header centre (17.80, 10.489): the −6.0 edge lands at y = 26.98, which clears the M12 holder (starts y 27.75). Reversed insertion swaps 3V3↔GND and puts VIN on MISO → dead module. Fix: extend the overhang to **y = −7.5** (rotated edge at 28.48 sits on the holder, z 5.95…20.25, so the pins cannot reach the sockets: hat bottom ≥ 20.25 → pin tips ≥ 11.7 > 9.80 socket top). Cavity is y ≥ −10.0, nothing else there at z 12…14. Hat becomes 36.0 × 28.5. Plus a silkscreen "LENS ↑" arrow.
3. **§4 "three 0603 hedge pads, ≤ 3 mm"** cannot coexist: ANT pad edge to u.FL signal pad with a series 0603 is ≥ 4.5 mm. Use **0402** (R5 series 0 Ω fitted, C3/C4 shunts DNP) → 3.05 mm pad-edge to pad-edge.
4. **§2/§8 "12/15 NRST"** → 12 = GND, 15 = NRST (both manual revisions).
5. **§3 RAW at (4.140, 4.139)** conflicts with `OPENMV_N6.json` (GND). Only J3's label depends on it; gate 1 resolves it with a meter (≈5 V on USB → RAW; continuity to shell → GND).
6. §5: BOM/CPL are not a separate `tsci export` format — they are inside the gerbers zip.

## Phase 0 — project skeleton (files, no dev server)

Directory `cameras/openmv_n6/hardware/lora_hat/`:

| File | Content |
|---|---|
| `package.json` | `{"name":"n6-lora-hat","private":true,"type":"module","devDependencies":{"tscircuit":"0.0.2516"},"scripts":{"build":"tsci build index.circuit.tsx --pcb-png --schematic-png --3d-png","check":"tsci check netlist index.circuit.tsx && tsci check placement index.circuit.tsx && tsci check shorts index.circuit.tsx","snap":"tsci snapshot index.circuit.tsx --pcb-only --update && tsci snapshot index.circuit.tsx --layer bottom --update && tsci snapshot index.circuit.tsx --camera-preset top-down --update && tsci snapshot index.circuit.tsx --camera-preset right-sideview --update","export":"node tools/export.mjs"}}` |
| `tscircuit.config.json` | `{"mainEntrypoint":"index.circuit.tsx","snapshotsDir":"__snapshots__","build":{"circuitJson":true,"previewImages":true,"step":true}}` |
| `.gitignore` | `node_modules/`, `.tscircuit/`, `manual-edits.json`, `dist/index/` (keep `dist/jlcpcb/`, `dist/*.step`, `dist/*.png`) |
| `index.circuit.tsx` | the board (Phase 2) |
| `imports/E22_900M22S.tsx` | hand-built footprint (Phase 1) |
| `imports/N6Header2x8.tsx` | J1/J2 generator (Phase 1) |
| `imports/UFL_R_SMT.tsx` | J4 (Phase 1) |
| `tools/check_hat.mjs` | circuit.json verifier (Phase 4) |
| `tools/export.mjs` | runs `tsci export` ×3 and unzips bom/cpl into `dist/jlcpcb/` |
| `nets.expected.txt` | the net table below, for diffing |
| `fit/lora_hat_mock.py` | build123d envelope for the puck fitcheck (Phase 5) |
| `README.md` | what it is, pin map, order notes, verification results |

Commands (run in the directory; hand-written files above are enough, then
`npm install` so `@tscircuit/props` types resolve):

```
cd ~/code/dustycam/cameras/openmv_n6/hardware/lora_hat
npm install
tsci import --jlcpcb C411293 --use-exact-footprint    # reference only; see Phase 1
tsci import --jlcpcb C7827 --use-exact-footprint       # U1 reference
tsci import --jlcpcb C88373 --use-exact-footprint      # J4 reference
rm -rf .tscircuit/cache && npm run build               # -> dist/index/circuit.json (+ PNGs)
npm run check && npm run snap
tsci export index.circuit.tsx -f readable-netlist -o dist/lora_hat.netlist
tsci export index.circuit.tsx -f step -o dist/lora_hat.step
tsci export index.circuit.tsx -f gerbers -o dist/jlcpcb/lora_hat-gerbers.zip
node tools/check_hat.mjs dist/index/circuit.json
```

Always `rm -rf .tscircuit/cache` before a rebuild after routing-related edits (sarg: cached routes).

## Phase 1 — footprints

**E22 (`imports/E22_900M22S.tsx`)**: hand-build from the EasyEDA numbers above
(do not trust the import's silkscreen; the import is kept only to diff pad
coordinates: every pad in the import's circuit JSON must match the table to
0.01 mm, else stop). `<chip name="U2" footprint={<footprint>…</footprint>}
pinLabels={…} supplierPartNumbers={{jlcpcb:["C411293"]}}
manufacturerPartNumber="E22-900M22S" cadModel={{size:{x:14,y:20,z:3}}}>` — 22
`<smtpad shape="rect" width="1.8mm" height="0.9mm" portHints={["pinN"]} pcbX pcbY>`
at the listed coordinates; silkscreen path for the shield rectangle + IPEX
notch; a silkscreen dot at (6.9, −9.0) for pin 1; text "ANT" near (−7, −7.23).
pinLabels: `pin6:"RXEN", pin7:"TXEN", pin8:"DIO2", pin9:"VCC", pin13:"DIO1",
pin14:"BUSY", pin15:"NRST", pin16:"MISO", pin17:"MOSI", pin18:"SCK",
pin19:"NSS", pin21:"ANT"`, all others `GNDn`. Antenna end = footprint −Y.

**Headers (`imports/N6Header2x8.tsx`)**: one component taking `cols:[xA,xB]`
and 16 labels; emits `<footprint insertionDirection="from_below">` with
`<platedhole shape="circle" holeDiameter="1.0mm" outerDiameter="1.7mm">` at the
**literal N6 coordinates** (component placed at pcbX=0, pcbY=0, pads absolute)
— or centred at (2.870, 10.489)/(32.730, 10.489) with pads at x ±1.27,
y = −8.89 + 2.54 n; either way the check in Phase 4 is the same. Pin 1 (n = 7,
outer column) gets `shape="circular_hole_with_rect_pad"` for the silk mark.
Alias generation is by position so the two sources can be swapped by editing
one table:

| n | y | J1 outer 1.600 | J1 inner 4.140 | J2 inner 31.460 | J2 outer 34.000 |
|---|---|---|---|---|---|
| 7 | 19.379 | P0_MOSI | ETH_LED | P18 | RESET |
| 6 | 16.839 | P1_MISO | ETH_RXN | P17 | P11 |
| 5 | 14.299 | P2_SCK | ETH_RXP | P16 | P10 |
| 4 | 11.759 | P3_NSS | ETH_TXN | P15 | P9_DIO1 |
| 3 | 9.219 | P4 | ETH_TXP | P14 | P8_BUSY |
| 2 | 6.679 | P5 | WKUP2 | P13 | P7_NRST |
| 1 | 4.139 | P6 | RAW | BOOT0 | VIN |
| 0 | 1.599 | V3V3_A | GND_A | V3V3_B | GND_B |

**u.FL (`imports/UFL_R_SMT.tsx`)**: 3 smtpads from the KiCad numbers (pin1
signal at (−1.525, 0) 1.05 × 1.0; pin2 ×2 at (0, ±1.475) 2.2 × 1.05),
`insertionDirection="from_above"`, `supplierPartNumbers={{jlcpcb:["C88373"]}}`.
Compare with the C88373 import: same 3-pad topology, signal pad on one side; if
the import's signal pad is offset differently by > 0.1 mm, use the import's
numbers (JLC assembles to their footprint) and re-place J4 by the same delta.

**U1**: `<chip footprint="sot23_5" pinLabels={{pin1:"NC",pin2:"A",pin3:"GND",pin4:"Y",pin5:"VCC"}} supplierPartNumbers={{jlcpcb:["C7827"]}}>`.
Passives: footprinter `0603`/`0805`/`0402` strings with LCSC numbers (expected
basics — confirm in JLC search: 10 k 0603 C25804, 100 k 0603 C25803, 100 nF
0603 C14663, 10 µF 0805 C15850, 0 Ω 0402 C17168; shunt 0402 pads DNP, no part
number). J3: `<pinheader pinCount={10} pitch="2.54mm">` (unpopulated; exclude
from BOM by omitting supplier number).

## Phase 2 — board, frame, placement

**Frame (Option A, primary)**: `<board layers={2} thickness="1.6mm"
outline={[{x:-0.3,y:Y_MIN},{x:35.7,y:Y_MIN},{x:35.7,y:21.0},{x:-0.3,y:21.0}]}>`
with `const Y_MIN = -7.5`; no board pcbX/pcbY; every part's `pcbX/pcbY` = N6
x/y literally. Calibration build first (board + J1 + J2 only): in
`dist/index/circuit.json` expect `pcb_board.center = (0,0)`,
`pcb_board.outline` = the four points, `pcb_plated_hole` at (1.600, 1.599)
etc. to 0.001, and zero `pcb_placement_error`/`pcb_trace_error`. If any
"outside board" error appears for J2 (x > 18), switch to **Option B**:
board-centred outline (x −18…18, y −(28.5/2)…) and a helper
`const at = (x,y) => ({pcbX: x - 17.7, pcbY: y - (21 + Y_MIN)/2})` used for
every part; the STEP/gerber then carry offset (−17.7, −6.75) which Phase 5 adds
back. Do not set `pcbX` on the board (it moves the children).

**Render sign check**: in `__snapshots__/index.circuit-pcb.snap.svg` /
`dist/…pcb.png`, +Y is up. Expect: header columns at the left and right edges
with pins from y 1.6 to 19.4 (a 1.6 mm empty strip above them), the overhang
with J3/holes at the **bottom**, module ANT end and J4 at the bottom-left of
the module, "P0" silk top-left. The 3D `top-down` preset must show the same
(top face up, no mirroring — the N6 pinout PNG is also a top view).

**Placement (first pass, rotation CCW, module frame origin = footprint origin, Y_MIN = −7.5)**:

| Ref | pcbX, pcbY | rot | Notes |
|---|---|---|---|
| J1 | pads literal | 0 | x 1.600/4.140 |
| J2 | pads literal | 0 | x 31.460/34.000 |
| U2 E22 | 18.30, 7.00 | 0 | outline x 11.3…25.3, y −2.5…17.5; pad columns x 11.3 / 25.3; ANT (21) at (11.3, −0.23); NSS 6.61, SCK 7.88, MOSI 9.15, MISO 10.42, NRST 11.69, BUSY 12.96, DIO1 14.23 on the left; RXEN 9.15, TXEN 10.42, DIO2 11.69, VCC 12.96 on the right; overhangs the N6 edge by 2.5 (nothing there) |
| J4 u.FL | 6.35, −0.23 | 180 | signal pad at (7.875, −0.23), GND pads x 5.25…7.45 (clears the (4.14,1.599) ring edge 4.99 by 0.26) |
| R5 0402 0 Ω | 9.40, −0.23 | 0 | pads 8.6…9.2 / 9.6…10.2; ANT pad edge at 10.4 |
| C3 0402 DNP | 9.90, 1.00 | 90 | pad1 (lower) stubs to the ANT node, pad2 → GND |
| C4 0402 DNP | 8.50, 1.00 | 90 | pad1 → u.FL node, pad2 → GND |
| GND vias Ø0.3/0.6 | (6.35,−2.6) (9.4,−2.4) (8.4,2.3) (10.0,2.4) | | `<via connectsTo="net.GND">` fence around the RF run |
| R1 10k NSS↑ | 8.00, 4.60 | 90 | pad2 (upper) → NSS |
| R2 10k NRST↑ | 8.00, 13.00 | 90 | pad1 (lower) → NRST |
| U1 74LVC1G04 | 28.40, 10.40 | 270 | gives A (pin2) at (28.4, 11.7) facing DIO2, Y (pin4) at (27.45, 9.1) facing RXEN, VCC (29.35, 9.1), GND (27.45, 11.7) — verify in the snapshot |
| R4 100k RXEN↓ | 27.40, 7.00 | 90 | pad2 → RXEN |
| R3 100k TXEN/DIO2↓ | 29.30, 13.40 | 90 | pad1 → DIO2 node |
| C2 100 nF | 27.00, 14.00 | 90 | pad1 → VCC (2.1 mm from pad 9) |
| C1 10 µF 0805 | 29.30, 15.60 | 90 | |
| J3 1×10 | pin1 (6.00, −5.50), centre (17.43, −5.50) | 0 | rings y −6.35…−4.65 |
| H1, H2 `<hole diameter="3mm">` | (2.20, −5.50), (33.50, −5.50) | | ≥ 0.7 mm web to the edges |
| Silk | "N6 LORA HAT v1", "LENS ↑" at (17.8, 19.9), "USB ↓" on the overhang, J3 labels P4 P5 P13 P14 P11 WKUP2 RAW BOOT0 3V3 GND, "ANT" arrow | | |

Free zones by construction: left strip x 4.99…10.4, right strip 26.2…30.61,
corridor y 17.5…20.7 (for P7/P8/P9 crossing to the left column), overhang
y < 0.75 full width. Nothing SMD at x < 5.0 or > 30.6 for y > 0.75 (pin tips).

**Nets** (`nets.expected.txt`, also the `<trace>`/`connections` list):

| Net | Members |
|---|---|
| GND | J1.GND_A, J2.GND_B, U2.1,2,3,4,5,10,11,12,20,22, U1.GND, C1.2, C2.2, R3.2, R4.1, C3.2, C4.2, J4.pin2, J3.10, 4 vias, bottom pour |
| V3V3 | J1.V3V3_A, J2.V3V3_B, U2.VCC, U1.VCC, C1.1, C2.1, R1.1, R2.1, J3.9 |
| SPI_MOSI | J1.P0_MOSI, U2.MOSI |
| SPI_MISO | J1.P1_MISO, U2.MISO |
| SPI_SCK | J1.P2_SCK, U2.SCK |
| SPI_NSS | J1.P3_NSS, U2.NSS, R1.2 |
| RADIO_NRST | J2.P7_NRST, U2.NRST, R2.2 |
| RADIO_BUSY | J2.P8_BUSY, U2.BUSY |
| RADIO_DIO1 | J2.P9_DIO1, U2.DIO1 |
| DIO2_TXEN | U2.DIO2, U2.TXEN, U1.A, R3.1 |
| RXEN | U1.Y, U2.RXEN, R4.2 |
| RF_ANT | U2.ANT, R5.2, C3.1 |
| RF_UFL | R5.1, J4.pin1, C4.1 |
| EXP_P4/P5/P13/P14/P11/WKUP2/RAW/BOOT0 | J1.P4↔J3.1, J1.P5↔J3.2, J2.P13↔J3.3, J2.P14↔J3.4, J2.P11↔J3.5, J1.WKUP2↔J3.6, J1.RAW↔J3.7, J2.BOOT0↔J3.8 |
| no-connect | J1.P6, ETH_LED/RXN/RXP/TXN/TXP, J2.P15…P18, RESET, P10, VIN (expect "not connected" warnings for these only) |

## Phase 3 — copper and routing

- `<copperpour layer="bottom" connectsTo="net.GND" boardEdgeMargin="0.3mm" padMargin="0.25mm" useThermalReliefs />`.
  Start **without** `unbroken`; the autorouter will use bottom segments and the
  pour absorbs GND ones. Add a second `<copperpour layer="top" connectsTo="net.GND">`
  only after the board routes clean (Ebyte wants grounded copper under the
  module; tscircuit routes first, pours after, so it is safe to add last).
- RF: `<trace from="U2.ANT" to="R5.pin2" thickness="0.5mm" pcbPath={[{x:10.4,y:-0.23},{x:9.9,y:-0.23}]} />`
  and `<trace from="R5.pin1" to="J4.pin1" thickness="0.5mm" pcbPath={[{x:8.4,y:-0.23},{x:8.2,y:-0.23}]} />`;
  if `pcbPath` errors on this version, drop it and put both connections in
  `<autoroutingphase phaseIndex={0} name="rf" connections={["U2.ANT","R5.pin2","R5.pin1","J4.pin1"]} />`
  — a straight 1 mm run is what the router does anyway.
- `<autoroutingphase phaseIndex={1} name="spi" connections={[SPI + NRST/BUSY/DIO1 ports]} />`;
  supply/expansion route last. `minTraceWidth="0.2mm"` on the board; supply
  traces `thickness="0.4mm"`.
- Known limit: router clearance ≈ 0.10 mm and ignores clearance props; the
  only tight spots are the 0.84 mm gaps between header rings (one 0.2 trace
  each). After build, run `tsci export -f kicad_pcb` and eyeball spacing in
  the gerber viewer at order time (JLC 2-layer min 0.127); this board is
  sparse enough that only ring gaps matter.
- What to check in `circuit.json` (script below): no `pcb_trace` segment with
  `layer:"bottom"` inside the RF/ANT rectangle x 5.0…13.0, y −3.0…2.5; no
  top-layer trace inside the module outline (x 11.3…25.3, y −2.5…17.5) other
  than those ending on U2 pads; via count (expect < 15); RF path length
  ≤ 3.5 mm (`tsci check trace-length U2.ANT`).

## Phase 4 — verification checklist (each item → an artifact)

| # | Check | How | Pass |
|---|---|---|---|
| 1 | Build clean | `rm -rf .tscircuit/cache && npm run build` | no `pcb_autorouting_error`, no `pcb_trace_error`, "not connected" only for the NC list |
| 2 | Netlist | `tsci check netlist`; `tsci export -f readable-netlist` diffed against `nets.expected.txt` (normalise order) | identical membership |
| 3 | Pin map | `tools/check_hat.mjs`: for each `pcb_plated_hole` whose port belongs to J1/J2, compare (x,y) to `x∈{1.6,4.14,31.46,34.0}`, `y=1.599+2.54n` | max abs Δ ≤ 0.01 mm, 32 holes |
| 4 | Pads inside outline | same script: every `pcb_smtpad`/`pcb_plated_hole` bbox inside the outline polygon inset 0.3 | 0 violations |
| 5 | Placement DRC | `tsci check placement` | 0 errors (insertionDirection declared on J1/J2/J4; add courtyards if it complains) |
| 6 | Shorts | `tsci check shorts` | 0 |
| 7 | Copper zones | script rules from Phase 3 | 0 violations |
| 8 | Silkscreen / orientation | snapshots (top, bottom layer, 3D top-down, right-sideview) | "LENS ↑" at +Y, J3/J4 at −Y, module ANT at −Y, no silk over pads, headers hang below in side view |
| 9 | Mechanical | Phase 5 `check.py` | CHECK PASSED |
| 10 | Fab files | `dist/jlcpcb/lora_hat-gerbers.zip` unzipped: gerbers + `bom.csv` (LCSC column filled for U1, U2, J4, R1–R5, C1, C2; C3/C4/J1/J2/J3 absent or DNP) + `pick_and_place.csv` (Designator, Mid X/Y, Layer=Top, Rotation) | all 12 assembled refs present, all `Top` |

`tools/check_hat.mjs` reads circuit.json; joins `pcb_port → source_port →
source_component` to name pads; prints the 32-hole diff table and the rules
above; exits 1 on any failure.

## Phase 5 — mechanical fitcheck

1. `tsci export -f step -o dist/lora_hat.step`. The STEP PCB is the outline
   polygon extruded z −0.8…+0.8 in the hat frame (= N6 frame under Option A).
2. `fit/lora_hat_mock.py` (build123d): `hat_parts()` returns **one fused
   solid** labelled `lora_hat`: the largest solid of
   `import_step(dist/lora_hat.step)` moved by `Pos(0,0,13.14)` (Option B:
   `Pos(17.7, 6.75, 13.14)`), plus explicit boxes: male header bodies
   x 0.33…5.41 and 30.19…35.27, y 0.33…20.65, z 9.80…12.34; pin tips 0.64 sq
   at the 32 positions z 13.94…16.94; module x 11.3…25.3, y −2.5…17.5,
   z 13.94…16.94; u.FL + plug Ø3.0 at (6.35, −0.23) z 13.94…19.5 plus a cable
   box 1.2 sq from there to y −7.5 at z 18…19.5. Assert the imported PCB bbox
   = x −0.30…35.70, y Y_MIN…21.0, z 12.34…13.94 (±0.01) before fusing.
3. `camera_puck/fitcheck.step.py::reference_parts()` appends `hat_parts()`
   (import via `importlib` from `../lora_hat/fit/`). The hat is then in
   `refs`, so the slide-in sweep moves it with the N6 automatically. No
   `MATED` additions needed (male insulator touches the female top at
   z 9.80, zero volume) unless the STEP includes its own header boxes — that
   is why only the largest solid is kept.
4. `python check.py` → must print `CHECK PASSED` with the hat in the pair
   list (expect `lora_hat x front_cup 0.0000`). Expected margins: −X wall
   0.40 (hat −0.30 vs cavity −0.702), −Y wall 2.5, ceiling 23.5 − 19.5 = 4.0.

## Phase 6 — order

5 × 2-layer 1.6 mm, assembly top side only ("Economic"), 10 placed parts (U1,
U2, J4, R1–R5, C1, C2; J1/J2/J3 hand-soldered). C3/C4 (DNP hedge shunts)
were deleted per review — see README Deviations. E22 is Extended (≈$3 fee);
note in README. Buy J1/J2 (2×8 male 2.54, ≥6 mm mating pins) separately.

## Risks, ranked (cheapest discriminating check first)

1. **Header pin map / row-to-x mapping (gate 1).** PNG and JSON agree on
   P7/P8/P9 = right outer x 34.0 at n 2/3/4 and 3V3/GND corners; they disagree
   on (4.14, 4.139) RAW vs GND. Check: meter on the real board — continuity
   from USB shell to the four n = 0 pins (expect GND at x 4.14 and 34.0 only)
   and voltage at (4.14, 4.139) on USB. 5 minutes, before ordering.
2. **Reverse insertion** (PLAN outline). Check: arithmetic above; fix is the
   −7.5 edge. Zero cost.
3. **E22 pad numbering direction** (EasyEDA vs Ebyte drawing). Check: render
   page 3 of the Ebyte manual and confirm pin 1 is at the corner opposite the
   IPEX/ANT corner on the same long side as pins 6–9 — matches EasyEDA (pin 1
   bottom-right, ANT bottom-left, IPEX notch bottom-left). Also verify on a
   physical module before soldering: continuity pad 12 ↔ pad 1 (both GND).
4. **RXEN/TXEN via inverter.** Manual: RXEN high = RX, TXEN high = TX, TXEN
   may be DIO2; Meshtastic/MeshCore E22 designs do exactly DIO2→TXEN with RXEN
   from an MCU pin. The inverter is electrically equivalent except RXEN stays
   high in sleep. Check: gate 3 sleep-current meter (spec 2 µA; PE42xx-class
   switch control draws < 1 µA, U1 ≈ 1 µA); if > 10 µA, v2 drives RXEN from
   P10/P6 instead.
5. **TCXO voltage.** Not in the manual; 1.8 V in both reference firmwares.
   Firmware-only: set `SetDIO3AsTCXOCtrl(1.8 V)` and read `GetDeviceErrors`
   for `XOSC_START_ERR`; step up to 2.2/3.3 V if set. Hardware unaffected.
6. **tscircuit frame handling** (board centre ≠ outline centroid). Check:
   calibration build (Phase 2); fallback Option B.
7. **3V3 in standby.** Unknown; if it drops, the radio just loses power
   (firmware re-inits each wake; pull-ups are harmless). Check: meter at
   (31.46, 1.599) during `machine.deepsleep()`.
8. **Autorouter GND handling with the pour** (may leave stray GND traces or
   fail to reach boxed-in pads). Check: build log + snapshot; mitigation: the
   four explicit vias, then add vias next to U2 pads 1/3/20/22 and C1/C2 GND
   ends.
9. **Router clearance 0.10 mm vs JLC 0.127.** Check: gerber viewer at the ring
   gaps; mitigation: `outerDiameter="1.6mm"` on the header rings (gap 0.94).
10. **Extended-part stock / u.FL footprint variant.** Check JLC page at order
    time; C88373 vs C434808 share the land.
11. **LED window** (gate 1). Unknown position; the pinout photo suggests the
    RGB LED sits at ≈ (2.0, 23.6), outside the hat. Only cut a hole if it
    measures inside x 5…30, y 0.75…17 and not under U2.

## Addendum 2026-09-13 (evening) — what the router actually honours

Verified against `@tscircuit/core` and `@tscircuit/capacity-autorouter`
0.0.900 bundled with tscircuit 0.0.2516 (see README "Clearance: how it
was closed"):

- `autorouter={{ traceClearance }}` is stored, never read. Use
  `minTraceToPadEdgeClearance="0.15mm"` + `minViaEdgeToPadEdgeClearance="0.15mm"`
  on `<board>`; they feed the router's obstacle margins, DRC engine and
  repair pass. Result here: min gap 0.142 mm (JLC 0.127).
- `autorouterEffortLevel` is not monotonic: 1x left one unrepaired via,
  2x routed clean, 5x was worse. Pin the value that passes.
- `<keepout>` blocks every net (excludeRefs is DRC-only) **and is voided
  from copper pours**. Never put one under an RF run or a module you want
  ground beneath. Top-only keepouts + thin bottom entrance strips protect
  an RF corner without losing the pour.
- Explicit `<via connectsTo="net.GND">` elements become routing targets;
  a via fence built that way inflated the via count and did not stop the
  planner. Don't.
- Phase 3's "router clearance ≈ 0.10 mm, eyeball at order time" is
  superseded by the above; Phase 4 check #6e in `tools/check_hat.mjs` is a
  real all-pairs clearance check.
