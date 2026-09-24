#!/usr/bin/env bash
# Convert the camlogger's gate.tflite (MobileNetV2, 96x96x3 int8, output
# [p_not_animal, p_animal]) for the N6's Neural-ART NPU with the tools the
# OpenMV IDE bundles (stedgeai, its python, arm-none-eabi-gcc). Nothing is
# installed: every tool and Python module comes from the IDE directory.
# Recipe proven 2026-09-13 (sarg: sargbench2/convert-a-custom-tflite-for-the-openmv-n6).
#
#   cameras/n6cam/software/host/convert_gate.sh          # -> software/app/gate.tflite
#
# Steps:
#   1. copy the IDE's N6 neural-art profile and memory-pool file next to the
#      output and strip the trailing " %" from the profile's options (the IDE
#      substitutes that placeholder; the CLI rejects it);
#   2. stedgeai generate --target stm32n6 --st-neural-art default@neuralart.json
#      (the report says which epochs run on the NPU; for gate.tflite only
#      the final Softmax falls back to software);
#   3. N6_reloc/npu_driver.py turns network.c into the runtime-loadable
#      network_rel.bin. It needs pyelftools 0.27, colorama, tabulate (all in
#      the IDE's bundled python 3.9) and a Cortex-M55 gcc (the IDE's arm/bin).
#
# The output is NOT a .tflite: it is an "NBIN" relocatable binary, the same
# format as the board's /rom/*.tflite models. It keeps the .tflite name so
# board.py's GATE_MODEL path stays generic. USB-copy it to /flash/gate.tflite;
# it is not bundled or OTA'd. The firmware's STAI runtime must match the
# converter (both report STAI-3.0.0-254 for IDE 4.x / firmware 5.0.0).
set -e

GATE_TFLITE="${GATE_TFLITE:-$HOME/code/sensorhub/data.old/gate_model/gate.tflite}"
IDE_ROOT="${IDE_ROOT:-$HOME/openmvide}"
QT="$IDE_ROOT/share/qtcreator"
STEDGEAI_DIR="$QT/stedgeai"
STEDGEAI="$STEDGEAI_DIR/Utilities/linux/stedgeai"
STPY="$STEDGEAI_DIR/Utilities/linux/python"
RELOC="$STEDGEAI_DIR/scripts/N6_reloc/npu_driver.py"
ARM_BIN="$QT/arm/bin"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAMERA_DIR="$(cd "$HERE/../.." && pwd)"
OUT_DIR="${OUT_DIR:-${TMPDIR:-/tmp}/gate_n6_convert}"
DEST="$CAMERA_DIR/software/app/gate.tflite"

for f in "$GATE_TFLITE" "$STEDGEAI" "$STPY" "$RELOC" "$ARM_BIN/arm-none-eabi-gcc" \
         "$QT/firmware/OPENMV_N6/neuralart.json" "$QT/firmware/OPENMV_N6/stm32n6.mpool"; do
    [ -e "$f" ] || { echo "convert_gate.sh: missing $f" >&2; exit 1; }
done

rm -rf "$OUT_DIR"; mkdir -p "$OUT_DIR"; cd "$OUT_DIR"
cp "$QT/firmware/OPENMV_N6/stm32n6.mpool" .
sed 's/ --enable-epoch-controller %"/ --enable-epoch-controller"/' "$QT/firmware/OPENMV_N6/neuralart.json" > neuralart.json
grep -q ' %"' neuralart.json && { echo "convert_gate.sh: placeholder still in neuralart.json" >&2; exit 1; }

"$STEDGEAI" generate -m "$GATE_TFLITE" --target stm32n6 \
    --st-neural-art default@neuralart.json -o "$OUT_DIR/out" | grep -v '^PASS:' || true
[ -f out/network.c ] || { echo "convert_gate.sh: stedgeai produced no network.c" >&2; exit 1; }
grep -A3 'Epochs details' out/network_generate_report.txt || true
grep -E 'pure software|pure hardware' out/network_generate_report.txt || true

STEDGEAI_CORE_DIR="$STEDGEAI_DIR" PATH="$ARM_BIN:$PATH" \
    "$STPY" "$RELOC" -i out/network.c -o build | tail -5

BIN="$OUT_DIR/build/network_rel.bin"
[ -f "$BIN" ] || { echo "convert_gate.sh: no $BIN" >&2; exit 1; }
[ "$(head -c 4 "$BIN")" = "NBIN" ] || { echo "convert_gate.sh: $BIN has no NBIN header" >&2; exit 1; }
cp "$BIN" "$DEST"
echo "convert_gate.sh: wrote $DEST ($(wc -c < "$DEST") bytes); USB-copy to /flash/gate.tflite"
