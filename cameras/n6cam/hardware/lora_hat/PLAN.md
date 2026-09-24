# N6 LoRa hat — plan (2026-09-13)

A plug-on hat for the OpenMV N6 that gives `n6cam` the `mesh` capability of
`docs/camera_operation.md` §2: a MeshCore radio the camera can use to post
detections and status to the existing mesh (`CornsnowBase` Heltec V4 on the
sensorhub, `DuckBisonRepeater`), and to receive short commands, without a
phone or WiFi in range. Designed in tscircuit, fabbed and assembled at
JLCPCB, and it fits inside the camera puck (`../camera_puck/`) unchanged.

Status: **designed on paper, nothing ordered.** Verification gates in §8.
Build plan (tscircuit, footprints, placement, checks): `BUILD.md`.

## 0. The decision: a bare SX1262 module on the N6's SPI, no second MCU

Two ways to put a camera on the mesh:

| | **A. Radio-only hat** (chosen) | B. Companion-MCU hat |
|---|---|---|
| What is on the hat | One SX1262 module (Ebyte E22-900M22S), 2 headers, a handful of passives | nRF52840/ESP32 module running MeshCore companion firmware + SX1262 module, UART to the N6 |
| Firmware | The N6's own MicroPython bundle: `meshcore.py` (already written and host-tested against the MeshCore source) + a ~300-line SX1262 driver | Second firmware to flash and update (needs its own USB/SWD on the hat), plus a MeshCore companion serial-protocol client on the N6 |
| Identity / config | One device, configured through the existing config pull; PSK in `secrets.py` from `dustygen` | Two mesh identities to set up and keep in step |
| Power in standby | Radio in sleep ≈ 2 µA; nothing to manage | Companion idles at 6–9 mA unless power-switched, and a power-switched companion reboots (seconds) every wake |
| Build | ~10 placed parts, all JLCPCB-assemblable except the two pin headers | 2 modules, USB-C, regulator, level of a small dev board |
| What you give up | Direct messages with ACKs, adverts, repeating, remote telemetry (all MeshCore-node features). We only need channel (group) messages, which are flood-only anyway | — |

A wins on both axes the brief asked for. Group-text packets are what
`runtime/micropython/meshcore.py` already builds and parses
(`mc_group_text`, `mc_parse`), and the base station stores every channel
message with its `Name:` prefix (`~/code/sensorhub/basestation/basestation.py`,
`kind='CHAN'`), so a message from the camera shows on `/p/mesh` with **zero
server changes** on day one.

Rejected variants: (1) a PCB-trace antenna (needs RF tuning, poor on a
36 mm ground plane; a u.FL pigtail to a stock antenna is the easy path);
(2) a bare SX1262 IC (RF matching design, QFN, no JLCPCB stock);
(3) RAK3172 / STM32WL AT-command module (a second MCU in disguise, no
MeshCore on it); (4) SPI4 on P15–P18 (shared with the Ethernet PHY, needs a
0 Ω rework on the N6).

## 1. What the camera does with it (software contract)

Group-text messages on a **private MeshCore channel** ("dusty", 16-byte
PSK in `secrets.py`), radio preset identical to the rest of the mesh:
910.525 MHz, BW 62.5 kHz, SF7, CR 4/5, +22 dBm max.

MeshCore PHY facts extracted 2026-09-13 from `meshcore-dev/MeshCore` main
(`src/helpers/radiolib/CustomSX1262.h`, `RadioLibWrappers.{h,cpp}`):
sync word `RADIOLIB_SX126X_SYNC_WORD_PRIVATE` (0x12 → SX126x regs
0x0740/0x0741 = 0x14 0x24), preamble **32 symbols for SF ≤ 8** (16 above),
CRC on (`setCRC(1)`), explicit header, DC-DC regulator mode, TCXO on DIO3
(1.6 V default, retried at 0 V; **the E22 wants 1.8 V**, see §8),
`setDio2AsRfSwitch` per board, packets are the raw bytes with no framing,
and a transmit is preceded by an RSSI-vs-noise-floor check (optionally
hardware CAD). Packet format: `meshcore.py` docstring. MeshCore caps a
payload at 146 bytes (sarg, 2026-08-20) — one line of text.

Uplink (camera → mesh), all rate-limited, all one line, `n6cam: ` prefix
added by the encoder:

| when | text (example) | default rate |
|---|---|---|
| a frame is **kept** by the judge (`why: motion`, gate ≥ `gate_pct`) | `det animal 0.87 x=41 y=22 seq=118` | at most one per `mesh_det_min_s` (300 s) |
| status | `st b=3.91 n=36 wake=1204 night=0 clk=set` | every `mesh_status_s` (3600 s) of awake-time, and once per contact |
| first boot / after a contact | `boot 2.1.7-n6 cfg=8` | once |
| night enter / exit | `night 1 lum=9` | at the transition |

Airtime at the preset for ~60 bytes ≈ 0.25 s, at +22 dBm ≈ 120 mA →
< 0.01 mAh per message. 30 messages/day is nothing next to the camera's
own wake cost.

Downlink (mesh → camera): after **every** uplink the camera listens for
`mesh_rx_window_ms` (1500 ms). The base station answers inside that window
with a channel message `@n6cam <cmd>` from a per-device command queue
(sensorhub, phase 3). Commands: `contact` (join the hotspot/LAN now, i.e.
the button without the button), `shoot`, `period <s>`, `status`. Anything
else is ignored. A listen window costs ~5 mA × 1.5 s, so it is also run on
the hourly status — a queued command reaches the camera within an hour, or
immediately after the next detection.

Not done here: adverts (the camera stays invisible to strangers), DMs,
repeating, images over LoRa.

## 2. Hardware — schematic

```
N6 header (3.3 V logic, 20 mA/pin)             hat
  P0  SPI2 MOSI ─────────────────────────────► MOSI  ┐
  P1  SPI2 MISO ◄───────────────────────────── MISO  │
  P2  SPI2 SCK  ─────────────────────────────► SCK   │ E22-900M22S (SX1262, TCXO,
  P3  SPI2 NSS  ──┬──────────────────────────► NSS   │ +22 dBm, IPEX + ANT pad)
                  └ R 10k ─ 3V3 (deselected while the N6 floats)
  P7  ───────────┬──────────────────────────► NRESET │
                 └ R 10k ─ 3V3                       │
  P8  ◄─────────────────────────────────────── BUSY  │
  P9  ◄─────────────────────────────────────── DIO1  │  (IRQ: TX done / RX done / timeout)
                        DIO2 ──┬────────────► TXEN   │  (Ebyte: "MCU IO or DIO2", active high)
                               └ U1 74LVC1G04 ─► RXEN │  (Ebyte: "connecting external MCU IO", active high)
  3V3 ── C 10 µF + 100 nF at the module ─────► VCC   │
  GND ───────────────────────────────────────► GND   ┘
                        ANT (50 Ω stamp pad) ── ≤ 3 mm 50 Ω trace ── J4 u.FL ── pigtail ── antenna (§4)

  Expansion row (unpopulated 0.1" pads, labelled): P4 P5 (I2C2/UART3)
  P13 P14 (UART7) P11 (WKUP3) WKUP2 RAW BOOT0 3V3 GND — for a PIR/sensor
  experiment without a new board (§7).
```

Pin choice: SPI2 is the N6's documented shield bus (`machine.SPI(2)`,
official examples run it at 15 MHz). P4/P5 stay free (I2C2/UART3), P13/P14
stay free (UART7), P10 is the camera frame-sync line (avoid), P11 is the
wake pin (reserve). P6 (the one buffered ADC input) stays free. P7/P8/P9
have no second job. No load switch: the SX1262's sleep is ≈ 2 µA and
NRESET gives a hardware reset; the pull-ups on NSS and NRESET keep the
radio deselected and out of reset when the N6 is in standby and its GPIOs
are high-Z. RXEN/TXEN get 100 k pull-downs so the switch is defined.
Nothing on the hat touches BOOT0, RESET, RAW, VIN or the Ethernet pins.

Power: the 3.3 V rail is rated "1 A supply max" on the pinout diagram
(TPS62826 buck); the radio's 120 mA TX burst is fine. The rail is assumed
to stay up in standby (the STM32 needs VDD for RTC/backup registers) —
measured in §8.

Bill of materials (v1):

| ref | part | pkg | JLCPCB | notes |
|---|---|---|---|---|
| U2 | Ebyte **E22-900M22S** (SX1262, 32 MHz TCXO, +22 dBm, ANT stamp pad) | 14 × 20 mm castellated, 22 pads | LCSC **C411293**, extended | `generic-e22` is a MeshCore variant, so the same settings are known-good |
| U1 | 74LVC1G04 inverter | SOT-23-5 | basic | RXEN = NOT DIO2, so the RF switch is autonomous and no N6 pin is spent on it |
| J4 | Hirose U.FL-R-SMT(10) u.FL | SMD | basic/extended | 50 Ω coplanar trace from the ANT pad, ≤ 3 mm |
| R1, R2 | 10 k | 0603 | basic | NSS, NRESET pull-ups |
| R3, R4 | 100 k | 0603 | basic | RXEN/TXEN pull-downs |
| C1 | 10 µF | 0805 | basic | module supply |
| C2 | 100 nF | 0603 | basic | module supply |
| J1, J2 | 2×8 male header, 2.54 mm | THT | hand-solder (or JLC THT) | mate to the N6's 2×8 females |
| J3 | expansion row 1×10 | THT pads | unpopulated | |
| — | Molex **211140-0100** flex antenna, 868/915 MHz, 38 × 10 × 0.1 mm, 100 mm u.FL lead | — | DigiKey/Mouser | v1 antenna, inside the puck |
| — | u.FL–SMA bulkhead pigtail + 915 MHz stub whip | — | — | option, §4 |

Alternative module (same schematic minus U1): Seeed **Wio-SX1262**
(TCXO, internal RF switch on DIO2, IPEX, 1.6 µA sleep, sold bare; not on
LCSC → hand-solder). Use it if the E22's TCXO/RF-switch facts in §8 come
back wrong.

## 3. Hardware — mechanical

Frame = the N6 board frame of `../camera_puck/ref/DIMENSIONS.md` (origin at
the PCB bottom-left corner on the PCB bottom face, +X across, +Y toward
the lens, +Z along the optical axis, ZT = 1.30 = PCB top). Header pins:
x ∈ {1.600, 4.140, 31.460, 34.000}, y = 1.599 + 2.54·n, n = 0…7, Ø1.02.
Pin names by position, read from `openmv-n6-pinout-v2.png` (top view,
lens up; the diagram's row r from the top is n = 8 − r) — **gate 1 in §8
is to confirm this against the physical silkscreen before ordering**:

| n | y | left outer x 1.600 | left inner x 4.140 | right inner x 31.460 | right outer x 34.000 |
|---|---|---|---|---|---|
| 7 | 19.379 | P0 SPI2 MOSI | ETH LED | ETH DC P | RESET |
| 6 | 16.839 | P1 SPI2 MISO | ETH RX− | ETH DC N | P11 WKUP3 |
| 5 | 14.299 | P2 SPI2 SCK | ETH RX+ | ETH DD P | P10 frame sync |
| 4 | 11.759 | P3 SPI2 NSS | ETH TX− | ETH DD N | P9 |
| 3 | 9.219 | P4 I2C2 SCL / UART3 TX | ETH TX+ | P14 UART7 TX | P8 |
| 2 | 6.679 | P5 I2C2 SDA / UART3 RX | SW2 / WKUP2 | P13 UART7 RX | P7 |
| 1 | 4.139 | P6 ADC | RAW (3.6–5 V, always on) — pinout PNG; `OPENMV_N6.json` says GND, meter it (gate 1) | BOOT0 | VIN (4.7–5.7 V in) |
| 0 | 1.599 | 3V3 | GND | 3V3 | GND |

Hat outline **36.0 × 28.5 mm**, x −0.30…35.70, y −7.5…21.0, 1.6 mm FR-4,
2 layers, all SMD on the top (+Z) face, headers through-hole. Why those
edges: the puck cavity is x −0.702…39.312, y −10.00…63.60; the 2×8 header
bodies span y 0.32…20.64; the BOOT1 switch (x 32.75…35.25, y 21.5…29.5)
stays reachable past the hat's +Y edge; the M12 lens holder starts at
y 27.75 and the camera daughter board at y 28.0, both clear. The −Y
overhang (to −7.5) is above the USB-C plug (z ≤ ~7.5) and inside the wall
(cavity y ≥ −10.0). **Why −7.5 and not −6.0: keying.** Rotated 180° about the
header centre (17.80, 10.489) a −6.0 edge lands at y 26.98 and clears the M12
holder (y 27.75), so the hat could be plugged in backwards (3V3↔GND swapped,
VIN on MISO). With −7.5 the rotated edge (y 28.48) sits on the holder
(z 5.95…20.25) and the pins cannot reach the sockets. Plus a "LENS ↑" silk arrow.

Z stack: N6 female header top at ZT + 8.50 = **9.80**; male header
insulator 2.54 → hat PCB **12.34…13.94**; E22 module ≈ 3.0 → 16.9; u.FL
plug + cable bend ≈ 3 → ~20; front-cup ceiling **23.50**. ≈ 3.5 mm to
spare. Put J4 at the −Y edge (away from the lens) and route the pigtail
along the +X wall.

Camera puck: **no change for the flex antenna** (it sticks to the inside
of the +X wall of the front cup, z 10…23, y 0…40, away from the N6
ground plane). The optional SMA bulkhead is a later puck rev (Ø6.5 hole +
nut relief in the −Y bottom wall next to the vents, which keeps the lens
face and the back plate untouched).

Retention: 32 pins of friction; no screws (the N6's mount holes are at
y 41.4, outside the hat). Add a 3.0 mm hole at each **−Y overhang** corner
((2.20, −5.50) and (33.50, −5.50)) for a future ceiling standoff — the +Y
corners are the header bodies and the P0/RESET pins.

LEDs: the N6's status LEDs (the LED language of §10 of the operation
spec) may sit under the hat — locate them on the physical board (gate 1)
and cut a Ø3 window if so.

## 4. Antenna

1. **v1: Molex 211140-0100 flex** (1 dBi, 38 × 10 mm, peel-and-stick,
   100 mm u.FL lead) on the inside of the puck's +X wall. No case change,
   no hole, sealed. Expect a few dB less than a whip; the mesh has a
   repeater on a hill and the camera only needs one hop.
2. **Range option: u.FL → SMA bulkhead pigtail** through the puck's
   bottom wall and a 915 MHz stub whip outside. Same hat. Do this if the
   range test in §8 says so.

Both plug into the hat's u.FL (J4). The E22-900M22S's ANT is a 50 Ω
stamp pad (Ebyte pin 21), so the hat carries the only RF trace: ANT pad →
J4, ≤ 3 mm, coplanar waveguide with ground on both sides and a solid
ground under it — electrically tiny at 915 MHz (λ/4 ≈ 82 mm), so no
matching network is needed; leave three 0603 pads (series + two shunts,
series fitted 0 Ω) as the customary hedge — **0402**, not 0603: with 0603 the
ANT-pad-to-u.FL run cannot stay ≤ 3 mm (BUILD.md correction 3).

## 5. Design flow (tscircuit)

Project: `cameras/n6cam/hardware/lora_hat/` — `index.circuit.tsx`,
`package.json`, `tscircuit.config.json`, `README.md`, `dist/` (gerbers,
BOM, CPL, pcb/schematic PNGs, STEP). Conventions from
`~/code/mycircuits/CLAUDE.md`: **placement as `pcbX`/`pcbY` in code**, no
`manual-edits.json`, sanity-check every imported JLCPCB footprint (silk
centred on the pads, inside the courtyard), `npx tsci build` clean, then
snapshots.

1. `tsci init`, pin the CLI (`tscircuit@0.0.2516` is installed globally).
2. Module footprint: `jlcpcb:C411293`; if the EasyEDA import is mangled,
   hand-build `<footprint>` from `<smtpad>`s using the Ebyte drawing
   (castellation pitch/size from the datasheet, not from memory).
   Headers: two `platedhole` 2×8 arrays at the coordinates in §3
   (hat frame = board frame, so they are literal). Passives: `0603`/`0805`,
   inverter `sot23_5`.
3. Nets exactly as §2; `<board>` outline 36 × 28.5 with the origin mapped so
   pcbX/pcbY = board-frame x/y. GND pour on the bottom layer, signals on
   top, no traces under the module's antenna end.
4. `npx tsci build` → no unconnected / no autorouter error;
   `tsci check netlist`; `tsci snapshot --3d`.
5. Mechanical: export STEP (`tsci export --format step`), drop it into
   `../camera_puck/fitcheck.step.py` as a reference solid at z 12.34 with
   the module box and a 3 mm antenna-plug box, and run `check.py` — the
   same fail-closed interference check the puck already uses.
6. Export gerbers (`tsci export -f gerbers`; the zip already contains
   `bom.csv` + `pick_and_place.csv` — there is no separate BOM/CPL format),
   order at JLCPCB: 5 boards, assembly of U1/U2/R/C on top,
   headers hand-soldered. Budget ≈ $40–60 incl. the extended-part fee,
   plus antennas.

## 6. Firmware and server phases

1. **`runtime/micropython/sx1262.py`** — minimal SX1262 driver on
   `machine.SPI(2)` + `machine.Pin`: reset, standby, LoRa packet type,
   frequency, modulation (SF/BW/CR/LDRO), packet params (preamble 32,
   explicit header, CRC on), sync word 0x1424, TCXO via DIO3, DIO2 as RF
   switch, DC-DC, PA config + OCP for +22 dBm, `send(bytes)` blocking on
   DIO1 with a timeout, `recv(timeout_ms)`, `rssi()` (for the
   noise-floor check), `sleep()`. Start from micropySX126X
   (github.com/ehong-tl/micropySX126X, MIT, pure Python) to prove the
   link on the bench, then trim to the subset the bundle needs. Host
   test: register/command byte sequences against a recorded transcript.
2. **`mesh.py`** — policy glue: `init(cfg, secrets)`, `notify(kind,
   fields)` with the rate limits of §1, `listen(ms)` → parsed
   `@n6cam` commands, `rest()`. Uses `meshcore.mc_channel`,
   `mc_group_text`, `mc_parse`. Pure policy is host-tested with a fake
   radio (`boardstubs.py`).
3. **Hooks** in `wakecycle.py`: after Record when the frame was kept
   (`det`), on night transitions, on the awake-time status clock, once
   in `contact.run` after the config pull (`boot`/`st`), and the listen
   window + command dispatch after every send. `board.py`: `MESH_PINS`,
   `mesh_spi()`. `camera.toml`: capability `mesh`, `[tuning]` keys
   `mesh_det_min_s`, `mesh_status_s`, `mesh_rx_window_ms`, `mesh_tx_dbm`,
   `mesh_freq_mhz`, `mesh_bw_khz`, `mesh_sf`, `mesh_cr`; `dustygen`
   writes `MESH_PSK` to `secrets.py` from `[mesh] channel_psk`. Bundle
   order gains `common:sx1262`, `common:meshcore`, `common:mesh`.
4. **Server**: the base station already stores the messages. Add to
   sensorhub: (a) map `n6cam:` channel messages onto the device page
   (events + battery), (b) a per-device command queue that replies
   `@n6cam <cmd>` within the listen window when a message from that
   device arrives, (c) the private channel configured on `CornsnowBase`
   (`meshcore-cli`). Keep the public channel as a fallback for field
   debugging with the phone app.

## 7. Later (not v1, but the hat leaves the door open)

- **PIR wake.** The header carries RAW (always on) and two active-low
  wake pins (SW2/WKUP2, P11/WKUP3). A PIR (e.g. AM312, 2.7–12 V) powered
  from RAW with its output inverted onto P11 would wake the N6 from
  standby on motion instead of polling every `period_s` — the biggest
  possible power win for the game profile. It needs the standby-wake
  behaviour of P11 proven on the bench first and the puck to get a PIR
  window. The expansion row exposes exactly these pins so it can be tried
  with wires before a hat v2 adds the connector and inverter.
- SMA bulkhead puck rev (§4).
- The `pir` capability in `camera_operation.md` §2 flips from "no" if the
  above works.

## 8. Gates (record each in sarg)

1. **Pin map on the real board**: read the silkscreen next to both
   headers and confirm §3's table (P0…P6 on the left outer column, P7…P11
   on the right outer column, RAW / WKUP2 on the left inner column).
   Also locate the LEDs.
2. **E22-900M22S facts from the datasheet** before ordering. Confirmed
   from Ebyte's product page 2026-09-13: 32 MHz TCXO; 14 × 20 mm;
   pins 6 RXEN ("connecting external MCU IO, valid in high level"),
   7 TXEN ("external MCU IO or DIO2"), 8 DIO2, 9 VCC 1.8–3.7 V, 15 NRST (12 is
   GND — both manual revisions),
   13 DIO1, 14 BUSY, 16 MISO, 17 MOSI, 18 SCK, 19 NSS, 21 ANT ("stamp
   hole, 50 ohm"), rest GND. Read 2026-09-13 (BUILD.md): 1.27 mm castellation pitch, 1.8 × 0.9 pads
   (EasyEDA C411293), TX 119 mA, RX 6.8 mA, sleep 2 µA. The TCXO voltage is
   **not stated** in the manual; MeshCore `generic-e22` and Meshtastic use
   1.8 V — confirm in firmware via `GetDeviceErrors` (XOSC_START_ERR).
3. **Standby**: N6 3V3 rail present in `machine.deepsleep()`? Hat adds
   < 5 µA to the pack current (meter, hat on/off).
4. **SPI2 bring-up**: write/read the sync-word registers through
   `machine.SPI(2)` at 8 MHz, then TX a `mc_group_text` on the public
   channel and see it in the phone app and on `/p/mesh`; then the private
   channel.
5. **RX**: the base station's reply lands inside the 1500 ms window
   ≥ 95 % of the time; tune the window.
6. **TX current** on the 3V3 rail at +22 dBm (scope for sag); `tx_dbm`
   default stays at 22 only if the rail is clean.
7. **Range**: flex antenna inside the puck vs the SMA whip, from the
   field positions to the repeater; pick the v1 antenna for real.
8. **Coexistence**: a mesh TX/RX inside a wake adds < 2 s awake-time; no
   effect on the SD spool or the hotspot join (WiFi off during LoRa).

Regulatory note: the module runs under its own grant at the mesh's
preset and power, like every other node on this mesh; this is a
one-off hobby device, not a product.

## 9. Sources

- Pinout diagram: `https://openmv.io/cdn/shop/files/openmv-n6-pinout-v2.png`
  (and `openmv-boards/pinouts/OPENMV_N6.json`); N6 quickref
  `https://docs.openmv.io/dev/openmvcam/quickref/openmv-n6.html`
  (SPI2/SPI4/UART/I2C ids, WKUP3, RAW, "1 A available for shields",
  SPI4 shared with the PHY).
- Board geometry: `../camera_puck/ref/DIMENSIONS.md`, puck cavity numbers
  in `../camera_puck/README.md`.
- MeshCore PHY: `meshcore-dev/MeshCore` `src/helpers/radiolib/` (see §1);
  packet format: `runtime/micropython/meshcore.py`.
- Module: JLCPCB/LCSC C411293 (E22-900M22S), Seeed Wio-SX1262 wiki
  `https://wiki.seeedstudio.com/wio_sx1262/`.
- Antenna: Molex 2111400100 drawing (38 × 10 × 0.1 mm, 100 mm lead).
- Driver: `https://github.com/ehong-tl/micropySX126X`.
- tscircuit: `~/code/mycircuits/CLAUDE.md` (placement rules),
  `https://docs.tscircuit.com/footprints/jlcpcb-footprints`,
  `https://docs.tscircuit.com/command-line/tsci-export`.
