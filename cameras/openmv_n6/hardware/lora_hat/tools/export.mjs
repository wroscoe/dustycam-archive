#!/usr/bin/env node
/**
 * Runs the three `tsci export` formats BUILD.md Phase 0 lists and unzips
 * the gerbers archive's bom.csv / pick_and_place.csv into dist/jlcpcb/ next
 * to the zip, so they're easy to open without re-unzipping.
 *
 * Usage: node tools/export.mjs
 */
import { execFileSync } from "node:child_process"
import { mkdirSync } from "node:fs"

const ENTRY = "index.circuit.tsx"

mkdirSync("dist/jlcpcb", { recursive: true })

function run(cmd, args) {
  console.log("$", cmd, args.join(" "))
  execFileSync(cmd, args, { stdio: "inherit" })
}

run("tsci", ["export", ENTRY, "-f", "readable-netlist", "-o", "dist/lora_hat.netlist"])
run("tsci", ["export", ENTRY, "-f", "step", "-o", "dist/lora_hat.step"])
run("tsci", ["export", ENTRY, "-f", "gerbers", "-o", "dist/jlcpcb/lora_hat-gerbers.zip"])

// Unzip bom.csv / pick_and_place.csv alongside the archive for convenience
// (plain `unzip`, no extra npm dependency).
try {
  run("unzip", ["-o", "-j", "dist/jlcpcb/lora_hat-gerbers.zip", "bom.csv", "pick_and_place.csv", "-d", "dist/jlcpcb"])
} catch (e) {
  console.log("(unzip failed -- extract dist/jlcpcb/lora_hat-gerbers.zip by hand for bom.csv/pick_and_place.csv)", e.message)
}

console.log("done")
