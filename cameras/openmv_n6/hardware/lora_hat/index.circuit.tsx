/**
 * N6 LoRa hat -- Ebyte E22-900M22S (SX1262) radio on the OpenMV N6's SPI2
 * shield header. Full placement per BUILD.md Phase 2/3, PLAN.md §2-§4.
 *
 * Frame: N6 board frame (Option A -- confirmed by the calibration build:
 * board center (0,0), outline literal, plated holes at literal N6 x/y).
 * Every part's pcbX/pcbY is the literal N6-frame coordinate; no board
 * pcbX/pcbY is set (it would translate the children -- see BUILD.md).
 *
 * DEVIATIONS from BUILD.md's literal placement table -- see README
 * "Deviations" for the full reasoning:
 *  - J4 (u.FL) uses the real C88373 land pattern (imports/UFL_R_SMT.tsx),
 *    whose signal pad is 0.72 mm off-center from BUILD.md's hand-built
 *    placeholder and 0.45 mm wider. J4 moved from (6.35, -0.23) to
 *    (6.80, -0.229) so its courtyard clears R5's with margin and its GND
 *    pads keep the same ~0.26 mm gap to the J1 header ring BUILD.md
 *    intended.
 *  - R4/C2/R3/C1 (100k pulldown / decoupling around U1) shifted along Y
 *    only (R4 7.0->6.5, C2 14.0->14.3, R3 13.4->14.2, C1 15.6->17.6) to
 *    clear real courtyard-to-courtyard DRC against U1's SOT-23-5
 *    courtyard and each other; BUILD.md's literal numbers left < 0.15 mm
 *    (or, for R3/C1, a small negative) gap once real footprint courtyards
 *    are used instead of point placements. Nets/topology unchanged.
 *  - C3/C4 (DNP RF hedge shunts) DELETED per review: they produced open
 *    stubs on the RF nets (a ~6 mm loop under the module's antenna
 *    corner to C3, a ~7 mm stub to C4) which is worse for RF integrity
 *    than no hedge pads at all. RF_ANT is now exactly U2.ANT<->R5.pin2
 *    and RF_UFL exactly R5.pin1<->J4.SIGNAL, both single straight
 *    top-layer segments (checked in tools/check_hat.mjs).
 *  - J3 (expansion row) pin order changed from "PLAN.md §3 table order"
 *    (interleaved J1/J2 pins) to J1's 4 signals on pins 1-4 and J2's 4
 *    signals on pins 5-8: this was the root cause of 7-8 mm diagonal
 *    bottom-layer crossings of the RF run by EXP_RAW/EXP_WKUP2/EXP_P5.
 *    See README Deviations and PLAN.md/BUILD.md's own tables are now
 *    stale on this point (kept as historical design record, not
 *    re-edited pin-by-pin).
 *  - Fab-blocking / clearance fixes per review: `minViaHoleDiameter` /
 *    `minViaPadDiameter` (JLC 2-layer minimums), `autorouter.
 *    traceClearance`, and two `<keepout>`s to keep routing off the RF
 *    run and out of the module's antenna-end footprint.
 */
import { E22_900M22S } from "./imports/E22_900M22S"
import { N6Header2x8 } from "./imports/N6Header2x8"
import { UFL_R_SMT } from "./imports/UFL_R_SMT"

const Y_MIN = -7.5

export default () => (
  <board
    layers={2}
    thickness="1.6mm"
    minTraceWidth="0.2mm"
    minViaHoleDiameter="0.3mm"
    minViaPadDiameter="0.6mm"
    autorouterEffortLevel="2x"
    minTraceToPadEdgeClearance="0.15mm"
    minViaEdgeToPadEdgeClearance="0.15mm"
    outline={[
      { x: -0.3, y: Y_MIN },
      { x: 35.7, y: Y_MIN },
      { x: 35.7, y: 21.0 },
      { x: -0.3, y: 21.0 },
    ]}
  >
    {/* ---- global nets ---- */}
    <net name="GND" />
    <net name="V3V3" />
    <net name="SPI_MOSI" />
    <net name="SPI_MISO" />
    <net name="SPI_SCK" />
    <net name="SPI_NSS" />
    <net name="RADIO_NRST" />
    <net name="RADIO_BUSY" />
    <net name="RADIO_DIO1" />
    <net name="DIO2_TXEN" />
    <net name="RXEN" />
    <net name="EXP_P4" />
    <net name="EXP_P5" />
    <net name="EXP_P13" />
    <net name="EXP_P14" />
    <net name="EXP_P11" />
    <net name="EXP_WKUP2" />
    <net name="EXP_RAW" />
    <net name="EXP_BOOT0" />

    {/* ---- N6 shield headers (literal N6 coordinates) ---- */}
    <N6Header2x8
      name="J1"
      colA={1.6}
      colB={4.14}
      labelsA={["V3V3_A", "P6", "P5", "P4", "P3_NSS", "P2_SCK", "P1_MISO", "P0_MOSI"]}
      labelsB={["GND_A", "RAW", "WKUP2", "ETH_TXP", "ETH_TXN", "ETH_RXP", "ETH_RXN", "ETH_LED"]}
      pin1="A"
      doNotPlace
    />
    <N6Header2x8
      name="J2"
      colA={31.46}
      colB={34.0}
      labelsA={["V3V3_B", "BOOT0", "P13", "P14", "P15", "P16", "P17", "P18"]}
      labelsB={["GND_B", "VIN", "P7_NRST", "P8_BUSY", "P9_DIO1", "P10", "P11", "RESET"]}
      pin1="B"
      doNotPlace
    />

    {/* ---- radio module ---- */}
    <E22_900M22S name="U2" pcbX={18.3} pcbY={7.0} pcbRotation={0} />

    {/* ---- RF path: ANT pad -> R5 (0 ohm series) -> J4 u.FL ---- */}
    <UFL_R_SMT name="J4" pcbX={6.8} pcbY={-0.229} pcbRotation={180} />
    <resistor name="R5" resistance="0" footprint="0402" pcbX={9.4} pcbY={-0.23} pcbRotation={0} supplierPartNumbers={{ jlcpcb: ["C17168"] }} />


    {/* ---- SPI pull-ups (keep NSS/NRST high while the N6 is in standby) ---- */}
    <resistor name="R1" resistance="10k" footprint="0603" pcbX={8.0} pcbY={4.6} pcbRotation={90} supplierPartNumbers={{ jlcpcb: ["C25804"] }} />
    <resistor name="R2" resistance="10k" footprint="0603" pcbX={8.0} pcbY={13.0} pcbRotation={90} supplierPartNumbers={{ jlcpcb: ["C25804"] }} />

    {/* ---- RXEN/TXEN autonomous RF-switch inverter ---- */}
    <chip
      name="U1"
      footprint="sot23_5"
      pinLabels={{ pin1: "NC", pin2: "A", pin3: "GND", pin4: "Y", pin5: "VCC" }}
      pcbX={28.4}
      pcbY={10.4}
      pcbRotation={270}
      supplierPartNumbers={{ jlcpcb: ["C7827"] }}
      manufacturerPartNumber="SN74LVC1G04DBVR"
    />
    <resistor name="R4" resistance="100k" footprint="0603" pcbX={27.4} pcbY={6.5} pcbRotation={90} supplierPartNumbers={{ jlcpcb: ["C25803"] }} />
    <resistor name="R3" resistance="100k" footprint="0603" pcbX={29.3} pcbY={14.2} pcbRotation={90} supplierPartNumbers={{ jlcpcb: ["C25803"] }} />

    {/* ---- module supply decoupling ---- */}
    <capacitor name="C2" capacitance="100nF" footprint="0603" pcbX={27.0} pcbY={14.3} pcbRotation={90} supplierPartNumbers={{ jlcpcb: ["C14663"] }} />
    <capacitor name="C1" capacitance="10uF" footprint="0805" pcbX={29.3} pcbY={17.6} pcbRotation={90} supplierPartNumbers={{ jlcpcb: ["C15850"] }} />

    {/* ---- expansion row (unpopulated). Pin order per review: J1's 4
         signals on pins 1-4 (short hop from the left header), J2's 4
         signals on pins 5-8 (short hop from the right header) -- this
         keeps every expansion trace off the RF run and out of the
         module footprint instead of the old interleaved order. ---- */}
    <pinheader name="J3" pinCount={10} pitch="2.54mm" pcbX={17.43} pcbY={-5.5} pcbRotation={0} doNotPlace />

    {/* ---- mechanical: future ceiling-standoff holes, -Y overhang ---- */}
    <hole name="H1" diameter="3mm" pcbX={2.2} pcbY={-5.5} />
    <hole name="H2" diameter="3mm" pcbX={33.5} pcbY={-5.5} />

    {/* ---- RF corner protection (u.FL -> R5 -> ANT pad, y -0.23).
        Facts (tscircuit 0.0.2516): a <keepout> blocks EVERY net for the
        router (excludeRefs only affects DRC) and the copper-pour solver
        voids keepouts unconditionally. So: no keepout may cover the RF
        strip itself, and no large bottom keepout may sit under the RF run
        (it would remove the ground the run needs). Instead:
        - top-only keepouts above/below the RF strip between the u.FL and
          the ANT pad column (x 8.0..10.2): same-layer intruders blocked,
          bottom pour untouched;
        - top-only keepout over the module's antenna end (x 12.3..25.3):
          no top traces under the ANT end, ground under the module kept;
        - two thin BOTTOM strips 1.2 mm above/below the RF trace
          (y 1.0..1.5 and -2.0..-1.5): the only pour voids, they stop
          signals diving under the run; the pour directly beneath the run
          stays solid and connected on both sides (J1 GND ring left,
          module body right).
        tools/check_hat.mjs fails on any non-GND bottom copper and any
        non-RF top copper in the critical zone x 6.5..12.5, y -1.5..1.0,
        and on non-U2 top copper at the module's ANT end. */}
    <keepout shape="rect" layers={["top"]} pcbX={9.1} pcbY={1.525} width={2.2} height={2.15} excludeRefs={[".R5", ".J4"]} />
    <keepout shape="rect" layers={["top"]} pcbX={9.1} pcbY={-1.75} width={2.2} height={1.7} excludeRefs={[".R5", ".J4"]} />
    <keepout shape="rect" layers={["top"]} pcbX={18.8} pcbY={-0.5} width={13.0} height={4.0} excludeRefs={[".U2"]} />
    <keepout shape="rect" layers={["bottom"]} pcbX={9.5} pcbY={1.25} width={6.0} height={0.5} excludeRefs={[".U2", ".J4"]} />
    <keepout shape="rect" layers={["bottom"]} pcbX={9.5} pcbY={-1.75} width={6.0} height={0.5} excludeRefs={[".U2", ".J4"]} />

    {/* ================= nets ================= */}

    {/* GND */}
    <trace from=".J1 > .GND_A" to="net.GND" />
    <trace from=".J2 > .GND_B" to="net.GND" />
    <trace from=".U2 > .GND1" to="net.GND" />
    <trace from=".U2 > .GND2" to="net.GND" />
    <trace from=".U2 > .GND3" to="net.GND" />
    <trace from=".U2 > .GND4" to="net.GND" />
    <trace from=".U2 > .GND5" to="net.GND" />
    <trace from=".U2 > .GND6" to="net.GND" />
    <trace from=".U2 > .GND7" to="net.GND" />
    <trace from=".U2 > .GND8" to="net.GND" />
    <trace from=".U2 > .GND9" to="net.GND" />
    <trace from=".U2 > .GND10" to="net.GND" />
    <trace from=".U1 > .GND" to="net.GND" />
    <trace from=".C1 > .pin2" to="net.GND" />
    <trace from=".C2 > .pin2" to="net.GND" />
    <trace from=".R3 > .pin2" to="net.GND" />
    <trace from=".R4 > .pin1" to="net.GND" />
    <trace from=".J4 > .pin2" to="net.GND" />
    <trace from=".J3 > .pin10" to="net.GND" />

    {/* V3V3 */}
    <trace from=".J1 > .V3V3_A" to="net.V3V3" />
    <trace from=".J2 > .V3V3_B" to="net.V3V3" />
    <trace from=".U2 > .VCC" to="net.V3V3" />
    <trace from=".U1 > .VCC" to="net.V3V3" />
    <trace from=".C1 > .pin1" to="net.V3V3" />
    <trace from=".C2 > .pin1" to="net.V3V3" />
    <trace from=".R1 > .pin1" to="net.V3V3" />
    <trace from=".R2 > .pin1" to="net.V3V3" />
    <trace from=".J3 > .pin9" to="net.V3V3" />

    {/* SPI2 */}
    <trace from=".J1 > .P0_MOSI" to="net.SPI_MOSI" />
    <trace from=".U2 > .MOSI" to="net.SPI_MOSI" />
    <trace from=".J1 > .P1_MISO" to="net.SPI_MISO" />
    <trace from=".U2 > .MISO" to="net.SPI_MISO" />
    <trace from=".J1 > .P2_SCK" to="net.SPI_SCK" />
    <trace from=".U2 > .SCK" to="net.SPI_SCK" />
    <trace from=".J1 > .P3_NSS" to="net.SPI_NSS" />
    <trace from=".U2 > .NSS" to="net.SPI_NSS" />
    <trace from=".R1 > .pin2" to="net.SPI_NSS" />

    {/* radio control */}
    <trace from=".J2 > .P7_NRST" to="net.RADIO_NRST" />
    <trace from=".U2 > .NRST" to="net.RADIO_NRST" />
    <trace from=".R2 > .pin2" to="net.RADIO_NRST" />
    <trace from=".J2 > .P8_BUSY" to="net.RADIO_BUSY" />
    <trace from=".U2 > .BUSY" to="net.RADIO_BUSY" />
    <trace from=".J2 > .P9_DIO1" to="net.RADIO_DIO1" />
    <trace from=".U2 > .DIO1" to="net.RADIO_DIO1" />

    {/* RF switch: DIO2 -> TXEN (direct) and DIO2 -> U1 -> RXEN (inverted) */}
    <trace from=".U2 > .DIO2" to="net.DIO2_TXEN" />
    <trace from=".U2 > .TXEN" to="net.DIO2_TXEN" />
    <trace from=".U1 > .A" to="net.DIO2_TXEN" />
    <trace from=".R3 > .pin1" to="net.DIO2_TXEN" />
    <trace from=".U1 > .Y" to="net.RXEN" />
    <trace from=".U2 > .RXEN" to="net.RXEN" />
    <trace from=".R4 > .pin2" to="net.RXEN" />

    {/* RF path: direct point-to-point traces, no shared net node and no
        DNP hedge stubs (deleted per review) -- one straight top-layer
        segment per hop. */}
    <trace from=".U2 > .ANT" to=".R5 > .pin2" thickness="0.5mm" />
    <trace from=".R5 > .pin1" to=".J4 > .pin1" thickness="0.5mm" />

    {/* expansion row passthroughs -- J1's 4 signals on pins 1-4, J2's 4
        signals on pins 5-8 (review item 4). */}
    <trace from=".J1 > .P4" to="net.EXP_P4" />
    <trace from=".J3 > .pin1" to="net.EXP_P4" />
    <trace from=".J1 > .P5" to="net.EXP_P5" />
    <trace from=".J3 > .pin2" to="net.EXP_P5" />
    <trace from=".J1 > .WKUP2" to="net.EXP_WKUP2" />
    <trace from=".J3 > .pin3" to="net.EXP_WKUP2" />
    <trace from=".J1 > .RAW" to="net.EXP_RAW" />
    <trace from=".J3 > .pin4" to="net.EXP_RAW" />
    <trace from=".J2 > .P13" to="net.EXP_P13" />
    <trace from=".J3 > .pin5" to="net.EXP_P13" />
    <trace from=".J2 > .P14" to="net.EXP_P14" />
    <trace from=".J3 > .pin6" to="net.EXP_P14" />
    <trace from=".J2 > .P11" to="net.EXP_P11" />
    <trace from=".J3 > .pin7" to="net.EXP_P11" />
    <trace from=".J2 > .BOOT0" to="net.EXP_BOOT0" />
    <trace from=".J3 > .pin8" to="net.EXP_BOOT0" />

    {/* ================= routing phases ================= */}
    <autoroutingphase phaseIndex={0} name="rf" connections={[".U2 > .ANT", ".R5 > .pin2", ".R5 > .pin1", ".J4 > .pin1"]} />
    <autoroutingphase
      phaseIndex={1}
      name="spi"
      connections={[
        ".J1 > .P0_MOSI", ".U2 > .MOSI",
        ".J1 > .P1_MISO", ".U2 > .MISO",
        ".J1 > .P2_SCK", ".U2 > .SCK",
        ".J1 > .P3_NSS", ".U2 > .NSS",
        ".J2 > .P7_NRST", ".U2 > .NRST",
        ".J2 > .P8_BUSY", ".U2 > .BUSY",
        ".J2 > .P9_DIO1", ".U2 > .DIO1",
      ]}
    />

    {/* ================= copper pour (Phase 3) ================= */}
    <copperpour layer="bottom" connectsTo="net.GND" boardEdgeMargin="0.3mm" padMargin="0.25mm" useThermalReliefs />

    {/* ================= silkscreen ================= */}
    {/* Title moved off U2's REFDES text (was colliding at ~(18.3,18.5)). */}
    <silkscreentext pcbX={9.0} pcbY={18.6} text="N6 LORA HAT v1" fontSize={1} anchorAlignment="center" layer="top" />
    <silkscreentext pcbX={17.8} pcbY={19.9} text="LENS UP" fontSize={1} anchorAlignment="center" layer="top" />
    <silkscreentext pcbX={17.8} pcbY={-6.6} text="USB DOWN" fontSize={0.8} anchorAlignment="center" layer="top" />
    {/* J3 expansion-row pin labels, pins 1-10 left-to-right (new order). */}
    <silkscreentext pcbX={6.0} pcbY={-4.4} text="P4" fontSize={0.6} anchorAlignment="center" layer="top" />
    <silkscreentext pcbX={8.54} pcbY={-4.4} text="P5" fontSize={0.6} anchorAlignment="center" layer="top" />
    <silkscreentext pcbX={11.08} pcbY={-4.4} text="WKUP2" fontSize={0.5} anchorAlignment="center" layer="top" />
    <silkscreentext pcbX={13.62} pcbY={-4.4} text="RAW" fontSize={0.6} anchorAlignment="center" layer="top" />
    <silkscreentext pcbX={16.16} pcbY={-4.4} text="P13" fontSize={0.6} anchorAlignment="center" layer="top" />
    <silkscreentext pcbX={18.7} pcbY={-4.4} text="P14" fontSize={0.6} anchorAlignment="center" layer="top" />
    <silkscreentext pcbX={21.24} pcbY={-4.4} text="P11" fontSize={0.6} anchorAlignment="center" layer="top" />
    <silkscreentext pcbX={23.78} pcbY={-4.4} text="BOOT0" fontSize={0.5} anchorAlignment="center" layer="top" />
    <silkscreentext pcbX={26.32} pcbY={-4.4} text="3V3" fontSize={0.6} anchorAlignment="center" layer="top" />
    <silkscreentext pcbX={28.86} pcbY={-4.4} text="GND" fontSize={0.6} anchorAlignment="center" layer="top" />
  </board>
)
