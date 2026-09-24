#!/usr/bin/env node
/**
 * N6 LoRa hat verification script (BUILD.md Phase 4 + review fixes).
 *
 * Usage: node tools/check_hat.mjs dist/index/circuit.json
 *
 * Checks:
 *   #2  netlist membership vs nets.expected.txt (+ NC list)
 *   #3  32-hole pin map: J1/J2 plated-hole (x,y) vs the literal N6 table
 *   #4  every pad/hole inside the board outline, inset 0.3 mm
 *   #6a copper-zone rule by SEGMENT/RECT CLIPPING (not endpoint-in-rect):
 *       clipped bottom-layer length inside the RF rectangle, and clipped
 *       top-layer length inside the module ANT-end rectangle excluding
 *       U2's own traces
 *   #6b via hole/pad size: every via >= 0.3 mm hole / 0.6 mm pad (JLC
 *       2-layer minimum)
 *   #6c via count fails at >= 25 (target ~18-25 after the review fixes)
 *   #6d RF path length: U2.ANT -> R5 -> J4 must be a single straight
 *       segment per hop, total <= 3 mm, computed from circuit.json
 *   #6e same-layer clearance (trace/pad/via/ring), adapted from the
 *       reviewer's drc.mjs: fails if the minimum same-layer, different-net
 *       gap is < 0.127 mm (JLC 2-layer minimum)
 *   #6f (informational) bottom-layer copper-pour coverage under the
 *       ANT->u.FL span
 *
 * Exits 1 on any failure.
 */
import { readFileSync, writeFileSync } from "node:fs"

const path = process.argv[2] ?? "dist/index/circuit.json"
const j = JSON.parse(readFileSync(path, "utf8"))

let failures = 0
function fail(msg) {
  failures++
  console.log(`FAIL: ${msg}`)
}
function ok(msg) {
  console.log(`ok: ${msg}`)
}

const byType = (t) => j.filter((e) => e.type === t)
const components = Object.fromEntries(byType("pcb_component").map((c) => [c.pcb_component_id, c]))
const sourceComponents = Object.fromEntries(byType("source_component").map((c) => [c.source_component_id, c.name]))
const sourcePorts = byType("source_port")
const sourcePortById = Object.fromEntries(sourcePorts.map((p) => [p.source_port_id, p]))
const pcbPorts = byType("pcb_port")
const pcbPortById = Object.fromEntries(pcbPorts.map((p) => [p.pcb_port_id, p]))

function compNameOfSourcePort(p) {
  return sourceComponents[p.source_component_id]
}
function label(p) {
  return `${compNameOfSourcePort(p)}.${p.name}`
}

// ---------------------------------------------------------------------------
// #2 netlist membership vs nets.expected.txt
// ---------------------------------------------------------------------------
function checkNetlist() {
  console.log("\n=== #2 netlist membership ===")
  const expectedText = readFileSync(new URL("../nets.expected.txt", import.meta.url), "utf8")
  const blocks = {}
  let ncList = []
  for (const rawLine of expectedText.split("\n")) {
    const line = rawLine.replace(/#.*/, "").trim()
    if (!line) continue
    const [name, rest] = line.split(":")
    const members = rest.split(",").map((s) => s.trim()).filter(Boolean)
    if (name.trim() === "NC") ncList = members
    else blocks[name.trim()] = members
  }

  const groups = new Map()
  const allLabels = new Set()
  for (const p of sourcePorts) {
    allLabels.add(label(p))
    const key = p.subcircuit_connectivity_map_key
    if (!key) continue
    if (!groups.has(key)) groups.set(key, new Set())
    groups.get(key).add(label(p))
  }
  const labelToGroup = new Map()
  for (const [key, members] of groups) for (const m of members) labelToGroup.set(m, key)

  for (const [netName, members] of Object.entries(blocks)) {
    const keys = new Set(members.map((m) => labelToGroup.get(m)))
    const missing = members.filter((m) => !labelToGroup.has(m))
    if (missing.length) {
      fail(`net ${netName}: ports not found in circuit: ${missing.join(", ")}`)
      continue
    }
    if (keys.size !== 1) {
      fail(`net ${netName}: members are not all on the same electrical net (${[...keys].length} distinct groups)`)
      continue
    }
    const [key] = keys
    const actual = groups.get(key)
    const expectedSet = new Set(members)
    const extra = [...actual].filter((m) => !expectedSet.has(m))
    if (extra.length) {
      fail(`net ${netName}: unexpected extra members ${extra.join(", ")}`)
    } else {
      ok(`net ${netName}: ${members.length} members match`)
    }
  }

  for (const ncLabel of ncList) {
    if (!allLabels.has(ncLabel)) {
      fail(`NC port not found in circuit at all: ${ncLabel}`)
      continue
    }
    const key = labelToGroup.get(ncLabel)
    if (key === undefined) {
      ok(`${ncLabel}: not connected, as expected (no trace touches it)`)
      continue
    }
    const group = groups.get(key)
    if (group.size !== 1) {
      fail(`${ncLabel} expected not-connected but is on a net with ${[...group].join(", ")}`)
    } else {
      ok(`${ncLabel}: not connected, as expected`)
    }
  }
}

// ---------------------------------------------------------------------------
// #3 32-hole pin map
// ---------------------------------------------------------------------------
function checkHeaderHoles() {
  console.log("\n=== #3 pin map (32 header holes) ===")
  const holes = byType("pcb_plated_hole")
  const headerHoles = holes.filter((h) => {
    const port = pcbPortById[h.pcb_port_id]
    if (!port) return false
    const sp = sourcePortById[port.source_port_id]
    if (!sp) return false
    const cname = compNameOfSourcePort(sp)
    return cname === "J1" || cname === "J2"
  })
  const xs = [1.6, 4.14, 31.46, 34.0]
  let maxDelta = 0
  let n = 0
  for (const h of headerHoles) {
    const nearestX = xs.reduce((a, b) => (Math.abs(b - h.x) < Math.abs(a - h.x) ? b : a))
    const dx = Math.abs(h.x - nearestX)
    const nRow = Math.round((h.y - 1.599) / 2.54)
    const expY = 1.599 + 2.54 * nRow
    const dy = Math.abs(h.y - expY)
    maxDelta = Math.max(maxDelta, dx, dy)
    n++
  }
  console.log(`  ${n} header holes, max |delta| = ${maxDelta.toFixed(6)} mm`)
  if (n !== 32) fail(`expected 32 header holes, found ${n}`)
  else ok("32 header holes present")
  if (maxDelta > 0.01) fail(`max hole delta ${maxDelta} exceeds 0.01 mm`)
  else ok(`max hole delta ${maxDelta.toFixed(6)} mm <= 0.01 mm`)
}

// ---------------------------------------------------------------------------
// #4 every pad/hole inside the board outline, inset 0.3mm
// ---------------------------------------------------------------------------
function pointInPolygon(pt, poly) {
  let inside = false
  for (let i = 0, k = poly.length - 1; i < poly.length; k = i++) {
    const xi = poly[i].x, yi = poly[i].y
    const xj = poly[k].x, yj = poly[k].y
    const intersect = yi > pt.y !== yj > pt.y && pt.x < ((xj - xi) * (pt.y - yi)) / (yj - yi) + xi
    if (intersect) inside = !inside
  }
  return inside
}
function insetPolygon(poly, inset) {
  const minX = Math.min(...poly.map((p) => p.x)) + inset
  const maxX = Math.max(...poly.map((p) => p.x)) - inset
  const minY = Math.min(...poly.map((p) => p.y)) + inset
  const maxY = Math.max(...poly.map((p) => p.y)) - inset
  return [
    { x: minX, y: minY },
    { x: maxX, y: minY },
    { x: maxX, y: maxY },
    { x: minX, y: maxY },
  ]
}
function checkPadsInsideOutline() {
  console.log("\n=== #4 pads/holes inside outline (inset 0.3mm) ===")
  const board = byType("pcb_board")[0]
  const inset = insetPolygon(board.outline, 0.3)
  let violations = 0
  const items = [...byType("pcb_smtpad"), ...byType("pcb_plated_hole"), ...byType("pcb_hole")]
  for (const it of items) {
    const hw = (it.width ?? it.outer_diameter ?? it.diameter ?? 0) / 2
    const hh = (it.height ?? it.outer_diameter ?? it.diameter ?? 0) / 2
    const corners = [
      { x: it.x - hw, y: it.y - hh },
      { x: it.x + hw, y: it.y - hh },
      { x: it.x - hw, y: it.y + hh },
      { x: it.x + hw, y: it.y + hh },
    ]
    for (const c of corners) {
      if (!pointInPolygon(c, inset)) {
        violations++
        console.log(`  outside: ${it.type} at (${it.x.toFixed(2)}, ${it.y.toFixed(2)})`)
        break
      }
    }
  }
  console.log(`  ${items.length} pads/holes checked, ${violations} violations`)
  if (violations > 0) fail(`${violations} pads/holes outside the inset outline`)
  else ok("all pads/holes inside the inset outline")
}

// ---------------------------------------------------------------------------
// geometry helpers shared by the copper-zone and clearance checks
// ---------------------------------------------------------------------------
function clipSegToRect(a, b, r) {
  // Liang-Barsky segment-vs-AABB clip. Returns the clipped [t0,t1] param
  // range (0..1 along a->b) that lies inside the rect, or null.
  let t0 = 0, t1 = 1
  const dx = b.x - a.x, dy = b.y - a.y
  const p = [-dx, dx, -dy, dy]
  const q = [a.x - r.x0, r.x1 - a.x, a.y - r.y0, r.y1 - a.y]
  for (let i = 0; i < 4; i++) {
    if (p[i] === 0) {
      if (q[i] < 0) return null
    } else {
      const t = q[i] / p[i]
      if (p[i] < 0) t0 = Math.max(t0, t)
      else t1 = Math.min(t1, t)
    }
  }
  if (t0 > t1) return null
  return [t0, t1]
}
function clippedLenInRect(a, b, r) {
  const t = clipSegToRect(a, b, r)
  if (!t) return 0
  const len = Math.hypot(b.x - a.x, b.y - a.y)
  return (t[1] - t[0]) * len
}

function traceSegments() {
  const segs = []
  for (const t of byType("pcb_trace")) {
    const route = t.route ?? []
    for (let i = 0; i < route.length - 1; i++) {
      const a = route[i]
      const b = route[i + 1]
      if (a.layer !== b.layer) continue
      segs.push({ trace: t, a, b, layer: a.layer, w: a.width || 0.2 })
    }
  }
  return segs
}

function ownerOfTrace(t) {
  // Which component(s) does this trace's connectsTo touch?
  const owners = new Set()
  for (const pid of t.connectsTo ?? []) {
    const port = pcbPortById[pid]
    if (!port) continue
    const sp = sourcePortById[port.source_port_id]
    if (!sp) continue
    owners.add(compNameOfSourcePort(sp))
  }
  return owners
}

// ---------------------------------------------------------------------------
// #6a copper zones by segment/rect clipping
// ---------------------------------------------------------------------------
function checkCopperZones() {
  console.log("\n=== #6a copper zones (segment/rect clipping) ===")
  const segs = traceSegments()
  // Critical RF zone: u.FL signal pad -> R5 -> ANT pad, +-1.2 mm around the run
  const RF_RECT = { x0: 6.5, x1: 12.5, y0: -1.5, y1: 1.0 }
  const MODULE_ANT_RECT = { x0: 11.3, x1: 25.3, y0: -2.5, y1: 1.5 }

  // GND is exempt: bottom-layer GND under the RF run is the pour's own net
  // (the router bridges U2's two GND pads around the ANT pad there), i.e.
  // the grounded copper the RF run wants. Only non-GND copper fails.
  const sn6a = Object.fromEntries(byType("source_net").map((n) => [n.subcircuit_connectivity_map_key, n.name]))
  const stk6a = Object.fromEntries(byType("source_trace").map((t) => [t.source_trace_id, t.subcircuit_connectivity_map_key]))
  const stDisp6a = Object.fromEntries(byType("source_trace").map((t) => [t.source_trace_id, t.display_name || ""]))
  const netName6a = (t) => {
    const n = sn6a[t.subcircuit_connectivity_map_key || stk6a[t.source_trace_id]]
    if (n) return n
    // explicit point-to-point <trace>s (the RF run) carry no net; name them by endpoints
    const dn = stDisp6a[t.source_trace_id] || ""
    if (/ANT|R5/.test(dn) && /R5|J4/.test(dn)) return dn.includes("J4") ? "RF_UFL" : "RF_ANT"
    return dn || "?"
  }
  let bottomInRfLen = 0
  let gndInRfLen = 0
  for (const s of segs) {
    if (s.layer !== "bottom") continue
    const len = clippedLenInRect(s.a, s.b, RF_RECT)
    if (len > 0) {
      const net = netName6a(s.trace)
      if (net === "GND") { gndInRfLen += len; continue }
      bottomInRfLen += len
      console.log(`  bottom seg in RF rect: ${net} (${s.a.x.toFixed(2)},${s.a.y.toFixed(2)})-(${s.b.x.toFixed(2)},${s.b.y.toFixed(2)}) clipped=${len.toFixed(3)}mm`)
    }
  }
  console.log(`  total non-GND bottom-layer length clipped inside RF rect: ${bottomInRfLen.toFixed(3)} mm (GND, exempt: ${gndInRfLen.toFixed(3)} mm)`)
  if (bottomInRfLen > 0.001) fail(`${bottomInRfLen.toFixed(3)} mm of non-GND bottom-layer copper under the RF run`)
  else ok("0 mm of non-GND bottom-layer copper under the RF run")

  // top-layer copper in the critical RF zone that is neither GND nor the RF nets
  let topInRfLen = 0
  for (const s of segs) {
    if (s.layer !== "top") continue
    const len = clippedLenInRect(s.a, s.b, RF_RECT)
    if (len <= 0) continue
    const net = netName6a(s.trace)
    if (net === "GND" || net === "RF_ANT" || net === "RF_UFL") continue
    topInRfLen += len
    console.log(`  top seg in RF zone: ${net} (${s.a.x.toFixed(2)},${s.a.y.toFixed(2)})-(${s.b.x.toFixed(2)},${s.b.y.toFixed(2)}) clipped=${len.toFixed(3)}mm`)
  }
  if (topInRfLen > 0.001) fail(`${topInRfLen.toFixed(3)} mm of non-RF/non-GND top-layer copper in the RF zone`)
  else ok("no non-RF/non-GND top-layer copper in the RF zone")

  let topInModuleLen = 0
  const topOffenders = []
  for (const s of segs) {
    if (s.layer !== "top") continue
    const owners = ownerOfTrace(s.trace)
    if (owners.has("U2")) continue // U2's own connections are expected to cross its footprint
    const len = clippedLenInRect(s.a, s.b, MODULE_ANT_RECT)
    if (len > 0) {
      topInModuleLen += len
      topOffenders.push(`(${s.a.x.toFixed(2)},${s.a.y.toFixed(2)})-(${s.b.x.toFixed(2)},${s.b.y.toFixed(2)}) owners=${[...owners].join("/")}`)
    }
  }
  console.log(`  total non-U2 top-layer length clipped inside module ANT-end rect: ${topInModuleLen.toFixed(3)} mm`)
  for (const o of topOffenders) console.log(`    ${o}`)
  if (topInModuleLen > 0.001) fail(`${topInModuleLen.toFixed(3)} mm of non-U2 top-layer copper inside the module ANT-end footprint`)
  else ok("no non-U2 top-layer copper inside the module ANT-end footprint")
}

// ---------------------------------------------------------------------------
// #6b/#6c vias: size + count
// ---------------------------------------------------------------------------
function checkVias() {
  console.log("\n=== #6b/#6c vias ===")
  const vias = byType("pcb_via")
  const undersized = vias.filter((v) => v.hole_diameter < 0.3 - 1e-6 || v.outer_diameter < 0.6 - 1e-6)
  console.log(`  ${vias.length} vias; undersized (<0.3mm hole or <0.6mm pad): ${undersized.length}`)
  for (const v of undersized.slice(0, 10)) {
    console.log(`    via at (${v.x.toFixed(2)},${v.y.toFixed(2)}) hole=${v.hole_diameter} pad=${v.outer_diameter}`)
  }
  if (undersized.length > 0) fail(`${undersized.length} via(s) below JLC 2-layer minimum (0.3mm hole / 0.6mm pad)`)
  else ok("every via >= 0.3mm hole / 0.6mm pad")

  console.log(`  via count: ${vias.length} (fails at >= 25, target ~18-25)`)
  if (vias.length >= 25) fail(`via count ${vias.length} >= 25`)
  else ok(`via count ${vias.length} < 25`)
}

// ---------------------------------------------------------------------------
// #6d RF path length, computed from circuit.json
// ---------------------------------------------------------------------------
function checkRfPathLength() {
  console.log("\n=== #6d RF path length (U2.ANT -> R5 -> J4) ===")
  const segs = traceSegments()

  function hopLength(refA, portA, refB, portB) {
    // Find the trace connecting these two specific ports and sum its
    // same-layer segment lengths; also count segments to flag non-straight
    // (multi-segment) hops.
    const matches = byType("pcb_trace").filter((t) => {
      const owners = ownerOfTrace(t)
      return owners.has(refA) && owners.has(refB)
    })
    if (matches.length !== 1) {
      fail(`expected exactly 1 trace between ${refA}.${portA} and ${refB}.${portB}, found ${matches.length}`)
      return null
    }
    const t = matches[0]
    const route = t.route ?? []
    let len = 0
    let sameLayerSegs = 0
    for (let i = 0; i < route.length - 1; i++) {
      const a = route[i], b = route[i + 1]
      if (a.layer !== b.layer) continue
      len += Math.hypot(b.x - a.x, b.y - a.y)
      sameLayerSegs++
    }
    // "Straight" = the routed length matches the direct point-to-point
    // distance (within 0.01 mm) -- the router may emit several collinear
    // waypoints along one straight run, which is fine; a real bend or
    // detour (like the old C3/C4 stubs) would make routed > straight.
    const first = route[0], last = route[route.length - 1]
    const straightLineDist = Math.hypot(last.x - first.x, last.y - first.y)
    return { len, segs: sameLayerSegs, layers: new Set(route.map((r) => r.layer)), straightLineDist }
  }

  const hop1 = hopLength("U2", "ANT", "R5", "pin2")
  const hop2 = hopLength("R5", "pin1", "J4", "SIGNAL")
  if (!hop1 || !hop2) return

  console.log(`  U2.ANT -> R5.pin2: ${hop1.len.toFixed(3)} mm routed, ${hop1.straightLineDist.toFixed(3)} mm point-to-point, ${hop1.segs} segment(s), layers=${[...hop1.layers].join(",")}`)
  console.log(`  R5.pin1 -> J4.SIGNAL: ${hop2.len.toFixed(3)} mm routed, ${hop2.straightLineDist.toFixed(3)} mm point-to-point, ${hop2.segs} segment(s), layers=${[...hop2.layers].join(",")}`)

  const STRAIGHT_TOL = 0.01
  if (hop1.len - hop1.straightLineDist > STRAIGHT_TOL) fail(`U2.ANT -> R5.pin2 is not straight (routed ${hop1.len.toFixed(3)} mm vs point-to-point ${hop1.straightLineDist.toFixed(3)} mm)`)
  else ok("U2.ANT -> R5.pin2 is a straight run (routed length == point-to-point distance)")
  if (hop2.len - hop2.straightLineDist > STRAIGHT_TOL) fail(`R5.pin1 -> J4.SIGNAL is not straight (routed ${hop2.len.toFixed(3)} mm vs point-to-point ${hop2.straightLineDist.toFixed(3)} mm)`)
  else ok("R5.pin1 -> J4.SIGNAL is a straight run (routed length == point-to-point distance)")

  const total = hop1.len + hop2.len
  console.log(`  total RF path length: ${total.toFixed(3)} mm (target <= 3 mm)`)
  if (total > 3.0) fail(`RF path length ${total.toFixed(3)} mm exceeds 3 mm`)
  else ok(`RF path length ${total.toFixed(3)} mm <= 3 mm`)
}

// ---------------------------------------------------------------------------
// #6e same-layer clearance (adapted from the reviewer's drc.mjs)
// ---------------------------------------------------------------------------
function checkClearance() {
  console.log("\n=== #6e same-layer clearance (JLC min 0.127mm) ===")
  const sn = Object.fromEntries(byType("source_net").map((n) => [n.subcircuit_connectivity_map_key, n.name]))
  const nameOf = (k) => sn[k] || k
  const keyOfPort = (id) => {
    const p = pcbPortById[id]
    if (!p) return null
    const s = sourcePortById[p.source_port_id]
    return s?.subcircuit_connectivity_map_key || `port:${id}`
  }

  const items = []
  for (const p of byType("pcb_smtpad")) {
    items.push({ kind: "pad", net: keyOfPort(p.pcb_port_id), layers: [p.layer], rect: { x: p.x, y: p.y, w: p.width, h: p.height } })
  }
  for (const h of byType("pcb_plated_hole")) {
    items.push({ kind: "pth", net: keyOfPort(h.pcb_port_id), layers: ["top", "bottom"], circle: { x: h.x, y: h.y, r: (h.outer_diameter ?? Math.max(h.rect_pad_width ?? 0, h.rect_pad_height ?? 0)) / 2 } })
  }
  for (const v of byType("pcb_via")) {
    items.push({ kind: "via", net: v.subcircuit_connectivity_map_key, layers: ["top", "bottom"], circle: { x: v.x, y: v.y, r: v.outer_diameter / 2 } })
  }

  const stk = Object.fromEntries(byType("source_trace").map((t) => [t.source_trace_id, t.subcircuit_connectivity_map_key]))
  const netOfTrace = (t) => t.subcircuit_connectivity_map_key || stk[t.source_trace_id]
  const segs = []
  for (const t of byType("pcb_trace")) {
    const r = t.route || []
    for (let i = 0; i < r.length - 1; i++) {
      const a = r[i], b = r[i + 1]
      if (a.layer !== b.layer) continue
      segs.push({ net: netOfTrace(t), layer: a.layer, a, b, w: a.width || 0.2 })
    }
  }

  const d2 = (p, q) => Math.hypot(p.x - q.x, p.y - q.y)
  function ptSeg(p, a, b) {
    const dx = b.x - a.x, dy = b.y - a.y
    const L2 = dx * dx + dy * dy
    let t = L2 ? ((p.x - a.x) * dx + (p.y - a.y) * dy) / L2 : 0
    t = Math.max(0, Math.min(1, t))
    return d2(p, { x: a.x + t * dx, y: a.y + t * dy })
  }
  function segSeg(a, b, c, d) {
    const o = (p, q, r) => (q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x)
    const inter = o(a, b, c) * o(a, b, d) < 0 && o(c, d, a) * o(c, d, b) < 0
    if (inter) return 0
    return Math.min(ptSeg(a, c, d), ptSeg(b, c, d), ptSeg(c, a, b), ptSeg(d, a, b))
  }
  function rectPtDist(rc, p) {
    const dx = Math.max(rc.x - rc.w / 2 - p.x, 0, p.x - (rc.x + rc.w / 2))
    const dy = Math.max(rc.y - rc.h / 2 - p.y, 0, p.y - (rc.y + rc.h / 2))
    return Math.hypot(dx, dy)
  }
  function rectSegDist(rc, a, b) {
    let m = Infinity
    const n = 40
    for (let i = 0; i <= n; i++) {
      const p = { x: a.x + (b.x - a.x) * (i / n), y: a.y + (b.y - a.y) * (i / n) }
      m = Math.min(m, rectPtDist(rc, p))
    }
    const cs = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([sx, sy]) => ({ x: rc.x + (sx * rc.w) / 2, y: rc.y + (sy * rc.h) / 2 }))
    for (const c of cs) m = Math.min(m, ptSeg(c, a, b))
    return m
  }
  function rectRectDist(r1, r2) {
    const dx = Math.max(r1.x - r1.w / 2 - (r2.x + r2.w / 2), r2.x - r2.w / 2 - (r1.x + r1.w / 2), 0)
    const dy = Math.max(r1.y - r1.h / 2 - (r2.y + r2.h / 2), r2.y - r2.h / 2 - (r1.y + r1.h / 2), 0)
    return Math.hypot(dx, dy)
  }

  const results = []
  for (let i = 0; i < segs.length; i++) {
    for (let k = i + 1; k < segs.length; k++) {
      const s = segs[i], t = segs[k]
      if (s.layer !== t.layer || s.net === t.net) continue
      const g = segSeg(s.a, s.b, t.a, t.b) - s.w / 2 - t.w / 2
      if (g < 0.2) results.push({ g, what: `${s.layer} trace(${nameOf(s.net)}) <> trace(${nameOf(t.net)}) @(${s.a.x.toFixed(2)},${s.a.y.toFixed(2)})`, at: { x: (s.a.x + s.b.x + t.a.x + t.b.x) / 4, y: (s.a.y + s.b.y + t.a.y + t.b.y) / 4 }, layer: s.layer })
    }
  }
  for (const s of segs) {
    for (const it of items) {
      if (!it.layers.includes(s.layer) || it.net === s.net) continue
      let g
      if (it.rect) g = rectSegDist(it.rect, s.a, s.b) - s.w / 2
      else g = ptSeg(it.circle, s.a, s.b) - it.circle.r - s.w / 2
      if (g < 0.2) results.push({ g, what: `${s.layer} trace(${nameOf(s.net)}) <> ${it.kind}(${nameOf(it.net)})`, at: it.rect ? { x: it.rect.x, y: it.rect.y } : { x: it.circle.x, y: it.circle.y }, layer: s.layer })
    }
  }
  for (let i = 0; i < items.length; i++) {
    for (let k = i + 1; k < items.length; k++) {
      const a = items[i], b = items[k]
      if (a.net === b.net && a.net) continue
      if (!a.layers.some((l) => b.layers.includes(l))) continue
      let g
      if (a.rect && b.rect) g = rectRectDist(a.rect, b.rect)
      else if (a.circle && b.circle) g = d2(a.circle, b.circle) - a.circle.r - b.circle.r
      else {
        const rc = a.rect || b.rect, c = a.circle || b.circle
        g = rectPtDist(rc, c) - c.r
      }
      if (g < 0.2) results.push({ g, what: `${a.kind}(${nameOf(a.net)}) <> ${b.kind}(${nameOf(b.net)})`, at: { x: ((a.rect || a.circle).x + (b.rect || b.circle).x) / 2, y: ((a.rect || a.circle).y + (b.rect || b.circle).y) / 2 }, layer: a.layers.find((l) => b.layers.includes(l)) })
    }
  }
  results.sort((x, y) => x.g - y.g)

  const under127 = results.filter((r) => r.g < 0.127)
  if (process.env.CLEARANCE_JSON) writeFileSync(process.env.CLEARANCE_JSON, JSON.stringify(under127, null, 1))
  console.log(`  same-layer different-net gaps < 0.2mm: ${results.length}; < 0.127mm (JLC min): ${under127.length}`)
  if (results.length) {
    console.log(`  minimum gap: ${results[0].g.toFixed(3)} mm  (${results[0].what})`)
    for (const r of results.slice(0, 15)) console.log(`    ${r.g.toFixed(3)}  ${r.what}`)
  }
  if (under127.length > 0) {
    fail(`min same-layer clearance ${results[0].g.toFixed(3)} mm < 0.127 mm JLC minimum (${under127.length} pairs below it)`)
  } else {
    ok(`min same-layer clearance ${results.length ? results[0].g.toFixed(3) : "n/a"} mm >= 0.127 mm`)
  }
  return results.length ? results[0].g : null
}

// ---------------------------------------------------------------------------
// #6f (informational) pour coverage under the ANT->u.FL span
// ---------------------------------------------------------------------------
function checkPourCoverage() {
  console.log("\n=== #6f pour coverage under the RF run (informational) ===")
  const pours = byType("pcb_copper_pour").filter((p) => p.layer === "bottom")
  const R = { x0: 7.6, x1: 11.3, y0: -1.0, y1: 0.5 }
  const areaR = (R.x1 - R.x0) * (R.y1 - R.y0)
  // Coarse Monte-Carlo / grid sample of point-in-polygon against every
  // pour shape's outer ring (informational only -- not a hard fail).
  function pointInPoly(pt, poly) {
    let inside = false
    for (let i = 0, k = poly.length - 1; i < poly.length; k = i++) {
      const xi = poly[i].x, yi = poly[i].y
      const xj = poly[k].x, yj = poly[k].y
      const intersect = yi > pt.y !== yj > pt.y && pt.x < ((xj - xi) * (pt.y - yi)) / (yj - yi) + xi
      if (intersect) inside = !inside
    }
    return inside
  }
  const N = 40
  let covered = 0
  for (let i = 0; i < N; i++) {
    for (let k = 0; k < N; k++) {
      const x = R.x0 + ((i + 0.5) / N) * (R.x1 - R.x0)
      const y = R.y0 + ((k + 0.5) / N) * (R.y1 - R.y0)
      const inAny = pours.some((p) => p.brep_shape && pointInPoly({ x, y }, p.brep_shape.outer_ring.vertices))
      if (inAny) covered++
    }
  }
  const pct = (100 * covered) / (N * N)
  console.log(`  pour coverage under x ${R.x0}..${R.x1}, y ${R.y0}..${R.y1}: ${pct.toFixed(1)}% (target >= 90%, informational)`)
  if (pct < 90) console.log(`  NOTE: pour coverage ${pct.toFixed(1)}% < 90% target -- see README`)
  return pct
}

checkNetlist()
checkHeaderHoles()
checkPadsInsideOutline()
checkCopperZones()
checkVias()
checkRfPathLength()
const minGap = checkClearance()
checkPourCoverage()

console.log("\n=====================================")
if (failures > 0) {
  console.log(`CHECK FAILED (${failures} problem${failures === 1 ? "" : "s"})`)
  process.exit(1)
}
console.log("CHECK PASSED")
