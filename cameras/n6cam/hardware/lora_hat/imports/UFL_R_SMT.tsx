/**
 * Hirose U.FL-R-SMT-1(10) u.FL jack (LCSC C88373, land-compatible with
 * C434808). Topology check (BUILD.md Phase 1) against
 * `tsci import --jlcpcb C88373 --use-exact-footprint`
 * (kept at imports/ref/U_FL_R_SMT_1_10_.import.tsx):
 *
 *   BUILD.md hand numbers:  pin1 (signal) (-1.525, 0)   1.05 x 1.00
 *                           pin2 (GND x2) (0, +-1.475)  2.20 x 1.05
 *   C88373 import:          SIN (signal)  (-0.800, 0.001) 1.50 x 1.10
 *                           GND1/GND2     (0.450, +-1.500) 2.20 x 1.10
 *
 * Same 3-pad topology (signal on one side, two bonded GND pads straddling
 * y=0 on the other), but the signal pad is offset by 0.725 mm in x, more
 * than the 0.1 mm tolerance -> per BUILD.md Phase 1, use the import's
 * numbers (JLC assembles to their footprint), not the hand-built ones.
 * J4 is then placed (index.circuit.tsx) so the signal pad lands at the
 * same intended global position used by the rest of the RF chain, with a
 * small extra shift for the wider signal pad -- see README "Deviations".
 */
import type { ChipProps } from "@tscircuit/props"

const pinLabels = {
  pin1: ["SIGNAL"],
  pin2: ["GND"],
} as const

const pinAttributes = {
  pin2: { requiresGround: true },
} as const

export const UFL_R_SMT = (props: ChipProps<typeof pinLabels>) => {
  return (
    <chip
      pinLabels={pinLabels}
      pinAttributes={pinAttributes}
      supplierPartNumbers={{ jlcpcb: ["C88373"] }}
      manufacturerPartNumber="U.FL-R-SMT-1(10)"
      footprint={
        <footprint>
          <smtpad portHints={["pin1"]} shape="rect" width="1.499997mm" height="1.0999978mm" pcbX="-0.79996665mm" pcbY="0.001143mm" />
          <smtpad portHints={["pin2"]} shape="rect" width="2.1999956mm" height="1.0999978mm" pcbX="0.44996735mm" pcbY="1.499997mm" />
          <smtpad portHints={["pin2"]} shape="rect" width="2.1999956mm" height="1.0999978mm" pcbX="0.44996735mm" pcbY="-1.499997mm" />
          <silkscreenpath
            route={[
              { x: -0.8248586499999959, y: -1.300099 },
              { x: -1.02501065, y: -1.300099 },
              { x: -1.02501065, y: -0.699897 },
            ]}
          />
          <silkscreenpath
            route={[
              { x: -1.024985249999986, y: 0.6999986 },
              { x: -1.024985249999986, y: 1.2999974 },
              { x: -0.8249856499999879, y: 1.2999974 },
            ]}
          />
          <silkscreenpath
            route={[
              { x: 1.77500915, y: 1.2999974 },
              { x: 1.77500915, y: -1.2999974 },
            ]}
          />
          <silkscreentext text="{REF}" pcbX={0.196} pcbY={3.054} anchorAlignment="center" fontSize={1} />
          {/* Tight courtyard = the actual pad bbox (signal x -1.55..-0.05,
              GND pads x -0.65..1.55, y -2.05..2.05), not the import's
              padded generic-clearance courtyard -- R5 sits right next to
              this connector by design. */}
          <courtyardoutline
            outline={[
              { x: -1.6, y: 2.1 },
              { x: 1.6, y: 2.1 },
              { x: 1.6, y: -2.1 },
              { x: -1.6, y: -2.1 },
              { x: -1.6, y: 2.1 },
            ]}
          />
        </footprint>
      }
      {...props}
    />
  )
}
