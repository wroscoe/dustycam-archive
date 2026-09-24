/**
 * OpenMV N6 2x8 female header footprint generator (J1 left, J2 right).
 * Literal N6-frame coordinates (BUILD.md Phase 1 / PLAN.md §3): plated
 * holes 1.0 mm drill / 1.7 mm pad, x in {1.600, 4.140, 31.460, 34.000},
 * y = 1.599 + 2.54*n, n = 0..7. Placed at pcbX=0, pcbY=0 so the pads sit
 * at their literal board coordinates. `insertionDirection="from_below"`
 * (the N6 plugs in from below the hat, same as any shield).
 *
 * `colA`/`colB` give the two x positions of this connector (left-to-right
 * as drawn), `labelsA`/`labelsB` the 8 net-name aliases for n=0..7 in each
 * column (from PLAN.md §3 / BUILD.md's alias table), and `pin1` says
 * which column carries the header's physical pin 1 (n=7, the outer
 * column) -- that hole gets the silk pin-1 pad shape.
 */
import type { ChipProps } from "@tscircuit/props"

export type N6Header2x8Props = {
  colA: number
  colB: number
  labelsA: readonly [string, string, string, string, string, string, string, string]
  labelsB: readonly [string, string, string, string, string, string, string, string]
  pin1: "A" | "B"
}

const Y0 = 1.599
const STEP = 2.54

export const N6Header2x8 = (
  props: N6Header2x8Props & Omit<ChipProps<Record<string, [string]>>, "pinLabels" | "footprint">,
) => {
  const { colA, colB, labelsA, labelsB, pin1, ...rest } = props

  const pinLabels: Record<string, [string]> = {}
  labelsA.forEach((label, n) => {
    pinLabels[`pin${n + 1}`] = [label]
  })
  labelsB.forEach((label, n) => {
    pinLabels[`pin${n + 9}`] = [label]
  })

  const holes: any[] = []
  labelsA.forEach((_, n) => {
    const isPin1 = pin1 === "A" && n === 7
    holes.push(
      <platedhole
        key={`a${n}`}
        portHints={[`pin${n + 1}`]}
        shape={isPin1 ? "circular_hole_with_rect_pad" : "circle"}
        holeDiameter="1.0mm"
        outerDiameter="1.7mm"
        {...(isPin1 ? { rectPadWidth: "1.7mm", rectPadHeight: "2.2mm" } : {})}
        pcbX={colA}
        pcbY={Y0 + STEP * n}
      />,
    )
  })
  labelsB.forEach((_, n) => {
    const isPin1 = pin1 === "B" && n === 7
    holes.push(
      <platedhole
        key={`b${n}`}
        portHints={[`pin${n + 9}`]}
        shape={isPin1 ? "circular_hole_with_rect_pad" : "circle"}
        holeDiameter="1.0mm"
        outerDiameter="1.7mm"
        {...(isPin1 ? { rectPadWidth: "1.7mm", rectPadHeight: "2.2mm" } : {})}
        pcbX={colB}
        pcbY={Y0 + STEP * n}
      />,
    )
  })

  return (
    <chip
      pinLabels={pinLabels}
      footprint={<footprint insertionDirection="from_below">{holes}</footprint>}
      pcbX={0}
      pcbY={0}
      {...rest}
    />
  )
}
