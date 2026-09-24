import type { ChipProps } from "@tscircuit/props"

const pinLabels = {
  pin1: ["GND1"],
  pin2: ["SIN"],
  pin3: ["GND2"]
} as const

const pinAttributes = {
  pin1: {requiresGround: true},
  pin3: {requiresGround: true}
} as const

export const U_FL_R_SMT_1_10_ = (props: ChipProps<typeof pinLabels>) => {
  return (
    <chip
      pinLabels={pinLabels}
      pinAttributes={pinAttributes}
      supplierPartNumbers={{
  "jlcpcb": [
    "C88373"
  ]
}}
      manufacturerPartNumber="U.FL-R-SMT-1(10)"
      footprint={<footprint>
        <smtpad portHints={["pin1"]} pcbX="0.44996735mm" pcbY="1.499997mm" width="2.1999956mm" height="1.0999978mm" shape="rect" />
<smtpad portHints={["pin2"]} pcbX="-0.79996665mm" pcbY="0.001143mm" width="1.499997mm" height="1.0999978mm" shape="rect" />
<smtpad portHints={["pin3"]} pcbX="0.44996735mm" pcbY="-1.499997mm" width="2.1999956mm" height="1.0999978mm" shape="rect" />
<silkscreenpath route={[{"x":-0.8248586499999959,"y":-1.300099000000003},{"x":-1.025010650000013,"y":-1.300099000000003},{"x":-1.025010650000013,"y":-0.6998970000000071}]} />
<silkscreenpath route={[{"x":-1.024985249999986,"y":0.6999986000000007},{"x":-1.024985249999986,"y":1.2999973999999952},{"x":-0.8249856499999879,"y":1.2999973999999952}]} />
<silkscreenpath route={[{"x":1.7750091500000025,"y":1.2999973999999952},{"x":1.7750091500000025,"y":-1.2999973999999952}]} />
<silkscreentext text="{NAME}" pcbX="0.19647535mm" pcbY="3.053717mm" anchorAlignment="center" fontSize="1mm" />
<fabricationnotepath route={[{"x":1.9010185500000034,"y":0.3119881999999876},{"x":1.9010185500000034,"y":-0.29999940000000436},{"x":1.9010185500000034,"y":0.3119881999999876}]} strokeWidth="0.254mm" />
<fabricationnotepath route={[{"x":-1.2198032499999982,"y":-0.29999940000000436},{"x":-1.2198032499999982,"y":0.29999939999999015},{"x":-0.024987249999995242,"y":0.29999939999999015},{"x":-0.024987249999995242,"y":-0.29999940000000436},{"x":-1.2198032499999982,"y":-0.29999940000000436}]} strokeWidth="0.254mm" />
<courtyardoutline outline={[{"x":-1.806124650000001,"y":2.303716999999992},{"x":2.199075350000001,"y":2.303716999999992},{"x":2.199075350000001,"y":-2.285683000000006},{"x":-1.806124650000001,"y":-2.285683000000006},{"x":-1.806124650000001,"y":2.303716999999992}]} />
      </footprint>}
      cadModel={{
        objUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C88373.obj?uuid=3c28daac95f94888aeb9654b3f0a92c4",
        stepUrl: "https://modelcdn.tscircuit.com/easyeda_models/assets/C88373.step?uuid=3c28daac95f94888aeb9654b3f0a92c4",
        pcbRotationOffset: 90,
        modelOriginPosition: { x: 0, y: 0.4570031500000056, z: -0.01 },
      }}
      {...props}
    />
  )
}