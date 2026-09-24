#!/bin/bash
# Phase 3 of docs/REPO_PLAN.md: carve dustycam into its component repos.
#
# Runs inside claude-box. Operates on FRESH CLONES only — the source repo is
# never rewritten, so a bad carve costs nothing but a rerun.
#
# The --path-rename map matters: paths moved during phase 2, so keeping only
# `hw/` would capture a single commit. Each pre-move location is mapped to its
# post-move home, which reconstructs the hw/ layout across the whole history.
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"

SRC="$(dirname "$0")/dustycam"
OUT="$(dirname "$0")/carve"
rm -rf "$OUT"; mkdir -p "$OUT"

carve() {
  name=$1; shift
  echo "=== $name ==="
  git clone --no-local -q "$SRC" "$OUT/$name"
  ( cd "$OUT/$name" && git-filter-repo --quiet --force "$@" )
  echo "  commits: $(git -C "$OUT/$name" rev-list --count HEAD)"
  echo "  size:    $(du -sh "$OUT/$name/.git" | cut -f1)"
  echo "  top:     $(ls "$OUT/$name" | tr '\n' ' ')"
}

# ---- dustycam-hardware : all CAD, at the repo root -------------------------
carve hardware \
  --path hw \
  --path cameras/n6cam/hardware      --path cameras/openmv_n6/hardware \
  --path cameras/xiaocam1/hardware   --path cameras/xiao_pantilt/hardware \
  --path cameras/xiaocam1/ref        --path cameras/xiao_pantilt/ref \
  --path cameras/rt1062cam/case      --path cameras/openmv_rt1062/case \
  --path hardware \
  --path cameras/hardware_common \
  --path tools/casereview \
  --path-rename hw/: \
  --path-rename cameras/n6cam/hardware/:n6cam/ \
  --path-rename cameras/openmv_n6/hardware/:n6cam/ \
  --path-rename cameras/xiaocam1/hardware/:xiaocam1/ \
  --path-rename cameras/xiao_pantilt/hardware/:xiaocam1/ \
  --path-rename cameras/xiaocam1/ref/:xiaocam1/ref/ \
  --path-rename cameras/xiao_pantilt/ref/:xiaocam1/ref/ \
  --path-rename cameras/rt1062cam/case/:rt1062cam/case/ \
  --path-rename cameras/openmv_rt1062/case/:rt1062cam/case/ \
  --path-rename hardware/power_puck/:puck/power_puck/ \
  --path-rename hardware/tripod_mount/:puck/tripod_mount/ \
  --path-rename cameras/hardware_common/:common/ \
  --path-rename tools/casereview/:common/casereview/

# ---- dustycli : the `dusty` command ----------------------------------------
carve dustycli \
  --path tools/dustycli \
  --path tools/dustygen \
  --path-rename tools/dustycli/: \
  --path-rename tools/dustygen:dusty.py

# ---- dustycam-phone --------------------------------------------------------
carve phone --subdirectory-filter apps/dustyphone

# ---- dustycam-contracts ----------------------------------------------------
carve contracts \
  --path contracts \
  --path tools/contractgen \
  --path-rename contracts/: \
  --path-rename tools/contractgen:tools/contractgen

echo
echo "=== all carves complete ==="
