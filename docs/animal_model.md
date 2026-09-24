# The animal gate: which model, on which board, trained how

**Status: research summary and recommendation, 2026-09-12.** Companion to
[`camera_operation.md`](camera_operation.md) §4.1 (Judge) and §12 item 7.
Sources are web research by three agents on 2026-09-12 plus the lessons
recorded in sarg; anything marked *unverified* has not been run here.

## 1. What the on-device model is for

The camera's model is a **gate**, not the classifier of record. The cloud
does the real work: sensorhub runs a detector over every uploaded frame and
can add a species classifier. The gate has one job: decide keep or discard
after a motion trigger, so that the weekly `upload_cap` of about 1000 frames
is spent on animals and not on wind, shadows and exposure changes, which are
70–75 % of raw camera-trap frames in the public datasets.

That makes the requirements:

- **Recall over precision.** A missed animal is gone for good; a false keep
  costs one slot out of 1000. The recorded lesson (30 % threshold, fail
  open, 1-in-N audit) stands.
- **Reject the real negatives.** The hard negatives are moving vegetation,
  cloud shadows, rain, and the camera's own exposure hunting. COCO crops do
  not contain these; camera-trap empties from the same locations do.
- **Same semantics on both boards.** The `det` list, the label set for
  `keep_labels`, and the meaning of `gate_pct` must be identical so one
  config works for the XIAO and the N6.
- **Budget.** A few hundred ms and a few hundred KB on the XIAO; the N6 has
  an NPU and is not the constraint.

## 2. What already exists here

| Piece | Where | Facts |
|---|---|---|
| On-device gate | `cameras/esp32_s3_cam/software/camlogger/main/gate.cc` + `gate_model_data.cc` | MobileNetV2-0.35, ImageNet weights, 96×96×3 int8, 2-class. On the GOOUUU ESP32-S3: 643 KB model, 224 KB arena, **~0.5 s per inference** |
| Gate trainer | `~/code/sensorhub/tools/train_gate.py` | positives = COCO val2017 animal crops (bird..giraffe); negatives = the camera's own frames + animal-free COCO crops. 96 % val, 97 % animal recall, 2.9 % false alarm **on COCO-derived validation, not camera-trap data** |
| Server analyzer | `~/code/sensorhub/analyzer/analyzer.py` | YOLOv8m, COCO classes, writes `animals` into meta |
| Person data | `/hd2/datasets/wavesharecam` | 125 k 96×96 grayscale frames, YOLO-labelled person/no-person, one indoor scene |
| Lessons | sarg | from-scratch MobileNetV1 flatlines on 4.5 k diverse images, ImageNet transfer works; register every TFLite op the converter emits; arena and op-set traps |

Nothing on disk is camera-trap imagery, and the gate has never been scored
against outdoor empties.

## 3. Board options

### XIAO ESP32S3 Sense (no NPU)

| Approach | Input | Latency on ESP32-S3 | Notes |
|---|---|---|---|
| Binary/3-class MobileNetV2 α0.35, esp-tflite-micro + ESP-NN | 96×96 to 128×128 | tens of ms *if ESP-NN is active and the arena is in internal SRAM*; the stock 96×96 MobileNetV1 person model goes from ~2300 ms without ESP-NN to ~50 ms with it | what we have; the 0.5 s measured on the GOOUUU suggests ESP-NN or arena placement is worth checking |
| FOMO (Edge Impulse), MobileNetV2 α0.35 backbone | 96–160 | 5–10 fps reported on the XIAO | centroid heatmap, no size; weak on small distant subjects; per-cell single object. Not better than a classifier for a gate |
| ESP-DL `cat_detect` / `dog_detect` (espdet-pico) | 224×224 | ~125 ms measured | ready-made, but pets only, not wildlife; ESP-DL has no generic classifier training path |
| Insect camera-trap trigger paper (arXiv 2411.14467) | 96×96×1 to 120×160×3, MobileNetV2 α0.1–0.35, 94–411 k params | 0.3–8 fps, 125–300 mW on ESP32-S3 | closest published match to our problem; field AUROC dropped from 92–96 % to 59–87 %, which is the warning about lab validation |

No public Edge Impulse or Seeed project for wildlife on this board was
found. The classifier route is the evidence-backed one.

### OpenMV N6 (Neural-ART NPU)

| Approach | Input | Latency on STM32N6 | Notes |
|---|---|---|---|
| Shipped `/rom` models (`yolov8n_192`, `yolo_lc_192`, `person_detect`, `fomo_face`) | 192 | whole pipeline 27–30 fps at 640×480, <0.75 W active | **person-only**; no animal model ships |
| ST-YOLO-LC v1 retrained (stm32ai-modelzoo) | 192–256 | 1.9–2.9 ms | smallest detector; zoo checkpoints are COCO-person, retrain needed |
| YOLOv8n retrained (stm32ai-modelzoo) | 192–416 | 16–55 ms; ~9.4 mJ per inference at 256 | better small-object recall; a community attempt at full 80-class COCO hit unresolved quantisation and post-processing bugs; reduced class sets are the tested path |
| Same MobileNetV2 classifier as the XIAO | 96–224 | negligible | zero extra training work; identical semantics |
| Edge Impulse → OpenMV library | any | — | officially supported target; N6-specific friction reported. *Partially verified* |

Conversion is `stedgeai generate --target stm32n6 --st-neural-art`, or the
OpenMV IDE does it when a `.tflite` is loaded (firmware ≥ 4.8.1). INT8 only
on the NPU; unsupported ops fall back silently to the M55. Forum reports of
custom models hard-faulting at `ml.Model()` mean every custom model gets an
on-device load test before it is staged. Deep sleep on the N6 is reported
at ~6 mW, which also answers part of `camera_operation.md` §12 item 4
(*unverified here*).

## 4. Teachers and data for training

**Teacher (cloud, RTX).** MegaDetector: animal / person / vehicle boxes,
built for exactly this imagery. `pip install megadetector` or the
PytorchWildlife package. v5a/v5b are MIT-licensed; MDv1000 (2025) variants
`redwood` (YOLOv5x6, best), `cedar`, `larch`, `sorrel`, `spruce` (edge)
are GPL/AGPL-family, fine for personal use. About 17 img/s on an RTX 4090
for v5a. **SpeciesNet** (Google, Apache 2.0, EfficientNetV2-M, ~2000
taxa) classifies MegaDetector crops when species labels are wanted. Both
run together via PytorchWildlife or AddaxAI. Using MegaDetector rather than
YOLOv8m in the sensorhub analyzer is the first cloud-side improvement to
make, independent of the gate.

**Public data (LILA BC, `lila.science`).** LILA publishes precomputed
MegaDetector boxes for most sets, so no re-detection is needed. Licenses are
mostly CDLA-Permissive-2.0; check each page.

| Dataset | Size | Labels | Why |
|---|---|---|---|
| ENA24-detection | ~10 k | boxes, 23 classes | eastern North America, already boxed |
| Caltech Camera Traps | 243 k, 140 sites | image-level, 21 species, ~70 % empty | empties from real sites |
| NACTI | 3.7 M, 5 US sites | image-level, 28 species | volume; sample it |
| Channel Islands | 247 k | empty/animal + species, 47 % empty | balanced empties |
| Washington Camera Traps | 1.2 M, 637 sites | empty + 26 categories | many sites, generalisation |
| Missouri Camera Traps | 25 k | image-level, 20 species | small, midwestern |
| Snapshot Serengeti, WCS, iWildCam | millions | species | not our fauna; use only for diversity |

**Local data.** Every frame the cameras upload, labelled by MegaDetector in
the cloud: the `keep_all` and audit frames give the gate's own false
negatives and false positives, which is the retraining set that matters
most. This is why `audit_n` and `keep_all` are in the profile.

## 5. Recommendation

**One model, two boards, one training pipeline.** A 3-class softmax
classifier, `animal` / `person` / `empty`, MobileNetV2 α0.35 with ImageNet
weights, trained once and exported int8 at two input sizes: 96×96 (or
128×128 if the XIAO budget allows once ESP-NN is confirmed) for the XIAO and
160×160 or 224×224 for the N6. `det` carries `[{"label": "animal", "conf":
0.83}]`; `keep_labels` and `gate_pct` mean the same thing on both boards.

**Feed it a motion-centred crop, not the whole frame.** At 96 px a distant
animal is a few pixels. The Watch stage already knows where the diff is, so
the gate input is a square crop around the motion mask's bounding box,
padded by 50 %, clamped to the frame, with the full frame as fallback when
the mask is diffuse. Train with the same crop from MegaDetector boxes with
random jitter and scale so the distributions match. This is the single
cheapest recall gain available and costs no inference time.

**Train on camera-trap data, validate by site.** Positives: MegaDetector
animal and person boxes from ENA24, Caltech, Channel Islands, a NACTI
sample. Negatives: the *empty* frames from the same sites (they contain the
vegetation, shadow and exposure changes), plus our own cameras' empties as
they accumulate. Hold out whole sites, never random frames, and report
animal recall at the operating threshold and empty rejection rate. Expect
the field numbers to be well below the lab numbers and set `gate_pct`
from the field curve.

**Acceptance for the gate**, measured on held-out sites and then on a week
of `keep_all` frames from a real deployment: animal recall ≥ 95 % at the
shipped `gate_pct`, empty rejection ≥ 80 %, XIAO inference ≤ 150 ms with the
arena in internal SRAM, N6 inference ≤ 10 ms.

**Phase 2 for the N6 only.** When the classifier gate is proven, retrain
ST-YOLO-LC v1 or YOLOv8n-256 from the ST model zoo on a two-class set
(`animal`, `person`) using the same MegaDetector-labelled data. Boxes give a
better `score` for the drain ranking (size and count) and a crop for a later
species classifier. Keep the `det` format identical so the config does not
change.

## 6. Work items

1. Check the existing gate's 0.5 s: confirm ESP-NN kernels are compiled in
   and the arena is in internal SRAM, not PSRAM. Expected: under 100 ms.
2. Swap the sensorhub analyzer's YOLOv8m for MegaDetector (v5a to start;
   MDv1000-redwood if speed allows) so every frame gets camera-trap-grade
   labels. Keep the `animals` meta key.
3. Build the dataset: download ENA24, Caltech, Channel Islands and a NACTI
   sample with LILA's MegaDetector boxes to `/hd2/datasets/cameratraps/`;
   write the motion-crop sampler; site-wise split. Run inside `claude-box`
   with `/hd2/datasets` mounted (downloads and installs).
4. Retrain `train_gate.py` as the 3-class model, two export sizes, op list
   dumped and checked against both runtimes' resolvers.
5. On-device load and timing test on each board before staging; the N6 needs
   the `stedgeai` conversion and a hard-fault check at `ml.Model()`.
6. Record the outcomes in sarg: N6 custom model conversion, XIAO ESP-NN
   timing, field recall vs lab recall.
