/**
 * Ebyte E22-900M22S (SX1262, 32 MHz TCXO, +22 dBm, 20x14x3 mm castellated
 * module, LCSC C411293). Hand-built footprint from the Ebyte manual pin
 * table + the EasyEDA (JLCPCB) footprint geometry (BUILD.md Phase 1 /
 * PLAN.md §8.2) -- NOT the raw `tsci import` output, which is kept only as
 * a diff reference at imports/ref/E22_900M22S.import.tsx.
 *
 * Pad coordinates: 22 rect pads 1.8 x 0.9 mm, two columns at x = +-7.000.
 * Right column (x=+7.0, pins 1..11) y = -8.50 .. +8.50 in 1.27 mm steps,
 * with a 5.57 mm gap between pin3 (-5.96) and pin4 (-0.39) for the
 * IPEX/ANT keepout. Left column (x=-7.0, pins 12..22) mirrors it, 12 at
 * +8.50 down to 22 at -8.50. Diffed against the `tsci import
 * --jlcpcb C411293 --use-exact-footprint` output: all 22 pads match to
 * 0.000014 mm (see README "Phase 1 footprint checks").
 */
import type { ChipProps } from "@tscircuit/props"

const pinLabels = {
  pin1: ["GND1"],
  pin2: ["GND2"],
  pin3: ["GND3"],
  pin4: ["GND4"],
  pin5: ["GND5"],
  pin6: ["RXEN"],
  pin7: ["TXEN"],
  pin8: ["DIO2"],
  pin9: ["VCC"],
  pin10: ["GND6"],
  pin11: ["GND7"],
  pin12: ["GND8"],
  pin13: ["DIO1"],
  pin14: ["BUSY"],
  pin15: ["NRST"],
  pin16: ["MISO"],
  pin17: ["MOSI"],
  pin18: ["SCK"],
  pin19: ["NSS"],
  pin20: ["GND9"],
  pin21: ["ANT"],
  pin22: ["GND10"],
} as const

const pinAttributes = {
  pin1: { requiresGround: true },
  pin2: { requiresGround: true },
  pin3: { requiresGround: true },
  pin4: { requiresGround: true },
  pin5: { requiresGround: true },
  pin9: { requiresPower: true },
  pin10: { requiresGround: true },
  pin11: { requiresGround: true },
  pin12: { requiresGround: true },
  pin20: { requiresGround: true },
  pin22: { requiresGround: true },
} as const

// Right column (x=+7.0), pins 1..11, y from the Ebyte/EasyEDA table.
const RIGHT_Y = [-8.5, -7.23, -5.96, -0.39, 0.88, 2.15, 3.42, 4.69, 5.96, 7.23, 8.5]
// Left column (x=-7.0), pins 12..22, mirrored (12 at +8.5 .. 22 at -8.5).
const LEFT_Y = [8.5, 7.23, 5.96, 4.69, 3.42, 2.15, 0.88, -0.39, -5.96, -7.23, -8.5]

export const E22_900M22S = (props: ChipProps<typeof pinLabels>) => {
  return (
    <chip
      pinLabels={pinLabels}
      pinAttributes={pinAttributes}
      supplierPartNumbers={{ jlcpcb: ["C411293"] }}
      manufacturerPartNumber="E22-900M22S"
      cadModel={null}
      footprint={
        <footprint>
          {RIGHT_Y.map((y, i) => (
            <smtpad
              key={`pin${i + 1}`}
              portHints={[`pin${i + 1}`]}
              shape="rect"
              width="1.8mm"
              height="0.9mm"
              pcbX={7.0}
              pcbY={y}
            />
          ))}
          {LEFT_Y.map((y, i) => (
            <smtpad
              key={`pin${i + 12}`}
              portHints={[`pin${i + 12}`]}
              shape="rect"
              width="1.8mm"
              height="0.9mm"
              pcbX={-7.0}
              pcbY={y}
            />
          ))}
          {/* Shield rectangle silk, x +-5.08, y -7.375..+9.135, with the
              IPEX notch x -5.08..-1.27, y -7.375..-3.565 (bottom-left). */}
          <silkscreenpath
            route={[
              { x: -5.08, y: 9.135 },
              { x: 5.08, y: 9.135 },
              { x: 5.08, y: -7.375 },
              { x: -1.27, y: -7.375 },
              { x: -1.27, y: -3.565 },
              { x: -5.08, y: -3.565 },
              { x: -5.08, y: 9.135 },
            ]}
          />
          {/* Outline corners, x +-7.0, y -9.5..+10.5, drawn as short stubs
              clear of the pads (matches the EasyEDA reference silk). */}
          <silkscreenpath
            route={[
              { x: -7.0, y: 10.5 },
              { x: 7.0, y: 10.5 },
            ]}
          />
          <silkscreenpath
            route={[
              { x: -7.0, y: -9.5 },
              { x: 7.0, y: -9.5 },
            ]}
          />
          {/* Pin-1 marker dot, bottom-right corner near pin 1. */}
          <silkscreencircle pcbX={6.9} pcbY={-9.0} radius={0.15} />
          {/* ANT label: in the empty IPEX-notch cutout (x -5.08..-1.27,
              y -7.375..-3.565), not on the pin-21 ANT pad itself (review
              item 7 -- the label used to sit directly on the pad's
              copper at local (-7.0,-7.23) = global (11.3,-0.23)). */}
          <silkscreentext text="ANT" pcbX={-3.2} pcbY={-5.5} fontSize={0.8} anchorAlignment="center" />
          {/* REFDES moved to the module's own center (review item 7 --
              used to collide with the board title text at global
              (18.3,18.5)). */}
          <silkscreentext text="{REF}" pcbX={0} pcbY={1.0} anchorAlignment="center" fontSize={1} />
          {/* Tight courtyard = the real 20x14 module body (BUILD.md
              "outline x +-7.0, y -9.5...+10.5"), not the import's padded
              generic-clearance courtyard -- the RF passives (R5/C3/C4/C2)
              sit right up against this body by design. */}
          <courtyardoutline
            outline={[
              { x: -7.0, y: 10.5 },
              { x: 7.0, y: 10.5 },
              { x: 7.0, y: -9.5 },
              { x: -7.0, y: -9.5 },
              { x: -7.0, y: 10.5 },
            ]}
          />
        </footprint>
      }
      {...props}
    />
  )
}
