#!/bin/bash
# Phase 3, part 2: carve the firmware repo, then verify every carve against the
# pre-split tree. Runs inside claude-box, on fresh clones only.
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/dustycam"
OUT="$HERE/carve"

echo "=== firmware ==="
rm -rf "$OUT/firmware"
git clone --no-local -q "$SRC" "$OUT/firmware"
(
  cd "$OUT/firmware"
  # Everything that now lives in another repo, at both its pre- and post-move
  # paths, plus the archived cameras and the heavy dead weight. The original
  # repo keeps all of it (it becomes dustycam-archive).
  git-filter-repo --quiet --force --invert-paths \
    --path hw \
    --path apps/dustyphone \
    --path tools/dustycli --path tools/dustygen \
    --path tools/casereview --path tools/configurator \
    --path cameras/hardware_common \
    --path hardware \
    --path cameras/n6cam/hardware     --path cameras/openmv_n6/hardware \
    --path cameras/xiaocam1/hardware  --path cameras/xiao_pantilt/hardware \
    --path cameras/xiaocam1/ref       --path cameras/xiao_pantilt/ref \
    --path cameras/rt1062cam/case     --path cameras/openmv_rt1062/case \
    --path cameras/esp32_s3_cam --path cameras/pi5cam --path cameras/n6_speedcam \
    --path yolov8n_saved_model \
    --path calibration_image_sample_data_20x128x128x3_float32.npy \
    --path mesh/firmware \
    --path sensors/plantlogger
  # Nothing at HEAD is over 2 MB any more; this only reaches dead history.
  git-filter-repo --quiet --force --strip-blobs-bigger-than 2M
)
echo "  commits: $(git -C "$OUT/firmware" rev-list --count HEAD)"
echo "  size:    $(du -sh "$OUT/firmware/.git" | cut -f1)"
echo "  top:     $(ls "$OUT/firmware" | tr '\n' ' ')"

echo
echo "=== verify: carved HEAD == the matching subtree of pre-split ==="
REF="$HERE/carve/_ref"
rm -rf "$REF"; git clone --no-local -q "$SRC" "$REF"; git -C "$REF" checkout -q pre-split

check() {           # name  path-in-ref
  name=$1; sub=$2
  if diff -r -q --exclude=.git "$OUT/$name" "$REF/$sub" >/dev/null 2>&1; then
    echo "  OK    $name == pre-split:$sub"
  else
    echo "  DIFF  $name vs pre-split:$sub"
    diff -r -q --exclude=.git "$OUT/$name" "$REF/$sub" 2>&1 | head -8 | sed 's/^/        /'
  fi
}
check hardware  hw
check dustycli  tools/dustycli
check phone     apps/dustyphone
check contracts contracts

echo
echo "=== firmware: what survived ==="
git -C "$OUT/firmware" ls-files | wc -l
echo "  largest tracked blobs:"
git -C "$OUT/firmware" ls-files -z | xargs -0 du -b 2>/dev/null | sort -rn | head -5 | awk '{printf "    %6.2f MB  %s\n", $1/1048576, $2}'
