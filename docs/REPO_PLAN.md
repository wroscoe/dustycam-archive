# DustyCam repository plan

Status: **agreed, not yet executed.** Written 2026-09-24.

This is the plan of record for splitting the current `dustycam` tree into
several repositories. It supersedes ad-hoc structure notes elsewhere. Nothing
in it has been carried out yet; the tree is still one repo.

## 1. The shape

Six repositories, all under the GitHub user **`wroscoe`**.

| Repo | Holds | Rough size after carve |
|---|---|---|
| `dustycam-contracts` | wire formats: JSON Schema, TOML enums, golden vectors, the constant generator | tiny |
| `dustycam-firmware` | camera firmware, the shared runtimes, `camera.toml` manifests, docs/standard | ~5 MB |
| `dustycam-hardware` | CAD and PCB **sources**; exports are release artifacts, not commits | ~50 MB |
| `dustycam-phone` | the Android app (`apps/dustyphone` today) | small |
| `dustycam-site` | the splash site (`dustycamsplash` today, renamed) | ~3 MB |
| `dustycli` | the `dusty` workstation/ops CLI (`tools/dustycli/dusty.py` today) | tiny |

Plus, unchanged and separate:

- `sensorhub` — the hub (MQTT, ingest, blobgate, basestation). Stays **private**,
  keeps its current scope, gains a `meshdet` service and the `mesh/` radio notes.
- `slugsense`, `plantlogger` — the non-camera device projects currently parked
  under `sensors/`.

And a workspace directory that is **not** a repo:

```
~/code/dustycam-ws/      CLAUDE.md (repo map + merge order), Makefile (clone-all, sync-contracts-all, test-all)
  contracts/  firmware/  hardware/  phone/  site/  cli/      sibling clones
```

This is what gives an agent one tree when a change spans repos, without a
monorepo. `~/code/dusty/` and the `~/code/dustycam` symlink go away.

### Why not a monorepo, and why not one repo per camera

A monorepo was the first proposal and was rejected: CAD, firmware and the phone
app in one tree grows past what one person or one agent session can hold.

One repo per camera (firmware + hardware together) was considered seriously and
rejected on evidence from this repo:

- The MicroPython bundles are **96.9 %** (rt1062) and **91.2 %** (n6) shared
  code; the ESP-IDF camera is **64 %** shared. What is genuinely per-camera is
  `camera.toml` + `board.py`/`main.c` + a README — a directory's worth, not a
  repo's. A per-camera repo forces `runtime/` into a cross-repo pin, and the
  dominant recent activity has been exactly that: 9 new common modules
  (1,891 lines) added over ~10 days, each landing in the same session as the
  `board.py` hook that calls it.
- Hardware is not per-camera either. `hardware/power_puck` is the shared
  enclosure that both `openmv_n6/hardware/camera_puck` and
  `xiao_pantilt/hardware/puckcase` press into (`caselib.py:102`:
  `OUT_H = 80.80  # matches the power puck face`), and `caseskit`/`pcbkit` is
  imported by three cameras.
- Firmware and hardware for the same camera move on **independent cadences**.
  There is not one feature commit since the `cameras/` layout that touches both
  a camera's `hardware/` and its `software/`. 14 consecutive hardware-only
  commits (2026-09-12 17:03 → 09-13 18:50) touched zero firmware files. The
  case rev-E work that added the bq25185 charger and DC jack shipped with no
  `board.py` change — `board_sensors()` already read `CHG`/`BAT_ADC`.
- The one cross-cutting feature in flight, the N6 LoRa hat, puts its hardware in
  `cameras/n6cam/hardware/lora_hat/` and its firmware (`meshcore.py`) in
  `runtime/micropython/` — it would straddle two repos under any split.

What the per-camera idea got right, and what is adopted: **the camera id is the
unit**. sensorhub keys `config/<id>.json` and `firmware/<id>.bin` by it, STATUS
rows are per id, CI is per camera, the phone lists cameras by id.

### Keeping a camera discoverable as one unit

Directories are named by **camera id** in both repos, and the manifest links
them:

```toml
# dustycam-firmware/cameras/n6cam/camera.toml
manifest = 1
id = "n6cam"

[hardware]
repo = "wroscoe/dustycam-hardware"
path = "n6cam"
```

The hardware README links back. Release tags are `<id>-v*` in both repos.

## 2. Contracts

`dustycam-contracts` is the single source of truth for every wire format. Today
each of these is defined in prose in `docs/*.md` and then re-typed by hand in
MicroPython, C, Java and Python — the `STANDARD_META` key set is copied across
four test files, and `DustyLink.java:41-48` hand-mirrors `ble_frame.h`.

Contents:

```
schema/     meta, telemetry, camera_manifest, tuning_schema, ident,
            phone_profile, release            (JSON Schema 2020-12)
ble/        gatt.toml  PROTOCOL.md            UUIDs, frame header, flags, limits, ops
mesh/       lines.toml LINES.md               det/st/boot/night uplink grammar, @<id> downlink
firmware/   OTA.md                            version rules, flash map
hub_api.md                                    routes, the /config 409 rule, device-id regex
vectors/    golden inputs/outputs every language replays
gen/        {python,c,java}/ COMMITTED generated constants
tools/contractgen                             the generator; --check in CI
```

Consumers **vendor by tag** with a `sync-contracts.sh <tag>` script, which
fetches the generated files and stamps `CONTRACTS_VERSION` (e.g. `v7 3f9c1e2`).
Raw-file vendoring is the only mechanism that works for all four consumers:
sensorhub is stdlib-only in a bind-mounted `python:3.12-slim`, MicroPython
inlines source via `bundle.py`, and the Android app has no dependency manager.

| Consumer | Vendors |
|---|---|
| `dustycam-firmware` | `gen/python/` → `runtime/micropython/contract.py` (bundled via `common:contract`); `gen/c/` → `runtime/espidf/components/dusty_core/include/`; `vectors/` |
| `dustycam-phone` | `gen/java/Contract.java`; `vectors/ble_frames.json`, `prov_env.json` |
| `sensorhub` | `gen/python/`; `schema/`, `vectors/` |
| `dustycam-site` | `schema/release.schema.json` for `check_firmware.py` |

Since atomic cross-repo changes are impossible, two rules replace them:

1. **Receivers before senders; every receiver tolerates N-1.** Merge order:
   contracts (tag) → sensorhub → firmware → phone → site. Field cameras update
   slowly over OTA, so the hub must accept old and new shapes.
2. **Additive by default.** Adding a key bumps `contracts/VERSION` only.
   Removing or renaming bumps that surface's own integer (`info.proto`,
   `release.json.schema`, `dusty_phone.json.v`), which `contractgen` asserts
   against the recorded values.

Each consumer's CI *warns* when behind the newest contracts tag (legitimate
under rule 1) but *fails* if a vendored generated file was hand-edited.
Telemetry gains an optional `contract` key so a device page shows which contract
each camera is running.

## 3. Build artifacts: nothing binary is committed

The same rule for firmware and CAD: **sources in git, built products in
releases.**

### Firmware

```
dustycam-firmware   tag <id>-v20261001-120000
  CI (espressif/idf for ESP-IDF; bundle + compile-check for MicroPython)
  → GitHub Release holds: merged factory .bin (blank identity), app-only OTA .bin
    or bundled .py, manifest.json, release.json, SHA256SUMS

dustycam-site       make pin CAMERA=<id> TAG=<tag>
  writes firmware/<artifact>/release.json  (version, sha256, asset URLs) — a PIN ONLY
  Dockerfile fetches the asset at image build and sha256sum -c's it (build fails on mismatch)
  → served same-origin by Caddy, so the flasher never depends on GitHub CORS

OTA                 dusty stage-release <id> <ver>
  downloads the OTA asset, verifies sha, writes /hd2/sensorhub/firmware/<id>.{bin,py} + .version
  (`dusty stage` remains the LAN fast path from a local build)
```

### CAD

Tracked: the `*.step.py` / `*.dxf.py` scripts, `caselib.py`, `check.py`, READMEs.
Not tracked: STEP, STL, 3MF, GLB, and review renders — these become release
assets on a `<part>/vN` tag, built by CI running each script's `gen_step()`.

Verified feasible: `cadgen[snapshot]==0.5.1` installs from a public index
(deps `build123d`, `cadquery-ocp`, `ezdxf`, `shapely`; `playwright` only for
snapshots). Three caveats to design around:

- `cadquery-ocp` is a very large wheel — CI needs a pip cache or a prebuilt
  image, or every tag build spends minutes on OCCT.
- Playwright renders need a browser install in CI. Decide whether `casereview`
  PNGs are release assets or stay local-only.
- STEP output is **not** guaranteed byte-identical across OCCT versions, so a
  committed STEP could never be "verified" by rebuilding. This is fine because
  they are artifacts, but the hardware repo must pin `cadgen==0.5.1` so a tag
  rebuilds what was shipped.

This directly fixes the worst history offender: `fitcheck.step` was committed
three times in one week (6.3 + 6.3 + 4.7 MB) purely as a review-only export.

## 4. `dustycli`

`tools/dustycli/dusty.py` becomes the `dusty` command in its own repo, `dustycli`. The
name change is overdue: it stages firmware for OTA, builds blank fleet images,
seeds and drift-checks the hub's config, and writes the phone's profile JSON —
operations, not generation.

**Decouple first, split second.** The split is nearly free once these land, and
doing them in place avoids discovering the couplings the hard way:

1. Installed CLI (`pyproject.toml`, `pip install -e`), dropping the
   `REPO = Path(__file__).parents[1]` assumption (`dustygen:107-108`).
2. `manifest = 1` required in `camera.toml`, with the manifest schema living in
   `dustycam-contracts`; every generated-file path becomes part of that schema.
3. Tuning keyed by `manifest['id']`, not the camera **directory name**
   (`tuning_for()`, ~line 160). This is what removes the rename hazard below.
4. `--phone-json` builds its fleet list from `~/.dusty/config.toml [camera.*]`
   instead of globbing `REPO/cameras/*/camera.toml` (~line 561).
5. dustygen's tests move with it, using fixture manifests rather than the real
   camera trees.

The shared runtimes do **not** move into `dustycli`: they ship to the device and
are versioned by `APP_VERSION`, while the CLI is a workstation program with its
own release cadence. Bundling them would mean bumping a firmware dependency
every time a CLI flag changes.

## 5. Ownership

All repositories are **`wroscoe`** going forward. `owlmoshpit` is a different
user; the `upstream` remote and every reference to it is to be removed, not
redirected. 28 references across 6 files:

- `dustycam/README.md`, `dustycam/cameras/pi5cam/pyproject.toml`
- `dustycamsplash/{README.md, index.html, flash/index.html, docs/phone-app.html}`
- the `upstream` git remote on `dustycam`

## 6. Migration

Each phase leaves the system working. The order is chosen so that the
irreversible step (history rewriting) happens last and on throwaway clones.

### Phase 0 — land the dirty trees

Blocking prerequisite. `dustycam` is on `dustyphone-p1-crashfix` with 17
unpushed commits and a large uncommitted set; `sensorhub` is also dirty with a
pending `pump/` deletion and has **no git remote** at all.

1. **Fix `.gitignore:111` first.** It reads `*.png    yolov8n.onnx` — two globs
   on one line form a single literal pattern, so *neither* is ignored. This is
   why 124 PNGs are tracked (`git check-ignore` matches no rule for them). Split
   the lines; add `**/fitcheck*.step`, `**/dist/`, `**/__snapshots__/`,
   `**/review_clearance/`. Without this, `git add -A` sweeps in ~1.5 MB of new
   exports (`lora_hat/dist/lora_hat.step`, `__snapshots__/`, untracked
   `hardware/tripod_mount/`).
2. Commit in groups: (a) `common/micropython` + tests; (b) `openmv_n6`
   game_lowpower (`board.py`, `camera.toml`, docs, tests, host tools);
   (c) `lora_hat` plan + fit mock; (d) `apps/dustyphone` branding;
   (e) `xiao_pantilt` puckcase note; (f) `hardware/tripod_mount`.
3. Merge the branch to `main` and push. Land the splash repo too.
4. Give `sensorhub` a private remote, after auditing untracked secrets
   (`.env`, `mosquitto/passwd`, `basestation/data`, `*.db`).

### Phase 1 — in-place fixes, no moves

Each independently testable, no structural change:

1. The five `dustycli` decoupling changes in §4. Rename
   `~/.dusty/config.toml` `[camera.openmv_rt1062]` / `[camera.openmv_n6]` /
   `[camera.xiao_pantilt]` → `[camera.rt1062cam]` / `[camera.n6cam]` /
   `[camera.xiaocam1]` **in the same change** — dustygen keys tuning by
   directory name today, so a rename on either side alone silently stamps
   `camera.toml` defaults over the workstation tuning. Run
   `test_dustygen_n6.py` and `xiao_pantilt/tests/test_dustygen.py`.
2. Remove from HEAD (history is dealt with in phase 3): `fitcheck.step` ×4
   (3.6–6.3 MB each), `sensors/plantlogger/project_photos/Photos-1-001.zip`
   (13.3 MB), `sensors/plantlogger/enclosure/ref/FeatherS3D.STEP` (4.1 MB),
   `mesh/firmware/RAK_4631_repeater-*.zip`, and
   `cameras/esp32_s3_cam/software/camlogger/main/gate_model_data.cc` (3.9 MB of
   model weights as a C array — generate at build from `/hd2/models` or fetch by
   sha, as was already done for `yolov8n_saved_model/` in `6c91f3b`).
3. Scaffold `contracts/` in-repo and write `contractgen`.
4. Fold `n6_speedcam/hardware/case/ref/openmv_n6_ref.py` into a single board
   reference under `hardware_common/boards/`.
5. Fix `apps/dustyphone/Makefile:8` — `REPO := $(HOME)/code/dustycam`, which
   only resolves through the symlink that is about to be deleted.

### Phase 2 — restructure inside the existing repo

Nothing is carved yet; this proves the whole layout in one tree where it can
still be tested end to end.

- `git mv runtime runtime`
- `git mv cameras/n6cam cameras/n6cam` (and the other id renames)
- `git mv cameras/*/hardware hw/<id>/`, `cameras/rt1062cam/case
  hw/rt1062cam/case`, `hardware/{power_puck,tripod_mount} hw/puck/`,
  `cameras/hardware_common hw/common`, `tools/casereview hw/common/casereview`
- Re-point the path couplings: `xiao .../CMakeLists.txt:8`
  `EXTRA_COMPONENT_DIRS`, the app `Makefile`'s `ROOT`/`CAMERA_DIR`,
  `ble_spike/Makefile`, `tests/*.py` `parents[n]` and `sys.path` lines, the CAD
  `sys.path[:0] = [... "hardware_common"]` hacks, `casereview/serve.py`'s render
  glob, the CI workflow paths, `docs/camera_standard.md §6`.

**Prove it builds before carving:** `pytest runtime/tests cameras/*/tests`;
`python3 -m unittest discover -s runtime/espidf/tests`;
`make -C cameras/xiaocam1/software/app build`; `dusty cameras/n6cam --no-bundle`
into a temp dir with `/hd2/sensorhub/config/n6cam.json` unchanged; regenerate one
case and confirm `casereview` finds its renders; `make -C apps/dustyphone build`.
Commit and tag `pre-split`.

### Phase 3 — carve on fresh clones

`git filter-repo` on throwaway clones, so the original repo is never rewritten
and a bad carve costs nothing.

- `dustycam-hardware`: `--subdirectory-filter hw`, then a second pass
  `--path-glob '**/fitcheck*.step' --path-glob '**/project_photos/**'
  --path-glob '**/*.glb' --invert-paths`. Target ~50 MB.
- `dustycam-firmware`: `--path hw --path apps/dustyphone --path
  yolov8n_saved_model --path mesh/firmware --invert-paths`, then
  `--strip-blobs-bigger-than 2M`. Target ~5 MB.
- `dustycam-phone`: `--subdirectory-filter apps/dustyphone`.
- `dustycli`: `--subdirectory-filter tools/dustycli/dusty.py`.

Diff each carved HEAD against the `pre-split` checkout (`diff -r`) to confirm
content identity.

### Phase 3 results (carved 2026-09-24, nothing published)

Carved in `claude-box` with `git-filter-repo` 2.47.0, from fresh clones, into
`~/code/dusty/carve/`. The source repo was not rewritten.

| Repo | Commits | `.git` | Verified against `pre-split` |
|---|---|---|---|
| `hardware` | 25 | 29 MB | identical to `hw/` |
| `firmware` | 39 | **1.5 MB** (from 117 MB) | — |
| `dustycli` | 7 | 228 KB | identical to `tools/dustycli/` |
| `phone` | 4 | 320 KB | identical to `apps/dustyphone/` |
| `contracts` | 2 | 212 KB | identical, plus `tools/contractgen` by design |

The `--path-rename` map is what makes this work. Paths moved in phase 2, so
filtering on `hw/` alone captures a single commit; each pre-move location
(`cameras/openmv_n6/hardware/`, `cameras/xiao_pantilt/ref/`, `hardware/`,
`cameras/hardware_common/`, …) is mapped to its post-move home, which
reconstructs the layout across all 25 commits of CAD history. `git subtree
split` cannot do this — it does not follow renames, and was tried first.

**What the carve proved about the split's cost.** In the carved firmware repo,
98 pytest and all 63 ESP-IDF host tests pass, but **46 tests fail**, every one
of them a cross-repo path failure rather than a logic failure:

- 39 dustygen tests (24 xiaocam1 + 15 n6cam) invoke `tools/dustycli/dusty.py`,
  which is now a different repository.
- 3 contract tests read `apps/dustyphone/.../Framer.java` and `DustyLink.java`
  to prove the C and Java copies of the BLE constants agree — and those two
  files are now in two different repositories.

This is the predicted loss of atomicity, made concrete on day one. It defines
the phase 4 work:

1. **dustycli becomes a dependency, not a path.** The camera test suites should
   resolve `dusty` from `PATH` (installed via `pip install -e`), skipping with a
   clear message when it is absent, instead of reaching across the tree.
2. **The contract cross-check splits three ways.** The C-side check stays in
   firmware, the Java-side check moves to the phone repo, and each runs against
   its *vendored* `contracts/gen/` rather than the other language's source. The
   "C and Java agree with each other" test cannot survive the split in its
   current form — the contract replaces it, which is the point.

Until then the combined checkout (`~/code/dustycam-ws/`) is the only place the
full suite runs green.

### Phase 4 — publish

Rename `wroscoe/dustycam` → `wroscoe/dustycam-archive` on GitHub (the redirect
keeps old links alive and the original history stays intact), then push the
carved repos under their new names. Rename `dustycamsplash` →
`dustycam-site`. Remove the `owlmoshpit` upstream remote and the 28 references.
Create `~/code/dustycam-ws/`, re-clone into it, delete `~/code/dusty/` and the
`~/code/dustycam` symlink.

Two local things break on the move and must be fixed the same day:
`docker rm dustybuild && make container` (it was created with a mount through
the symlink), and the sensorhub references at `README.md:196`, `MERGE_PLAN.md:8`
and `blobgate/blobgate.py:22`.

### Phase 5 — contracts, releases, and the leftovers

- Vendor `contracts/` at a tag into firmware, phone and sensorhub in merge
  order. Bump `APP_VERSION` and prove OTA-with-rollback on rt1062 **before**
  n6, since the bundle grows a module.
- Per-camera release workflows on `<id>-v*` tags; generalize
  `package_xiao_web_firmware.py` with the flash map read from `camera.toml`;
  add the site's `pin_firmware.py` and build-time fetch; delete the committed
  bins from the site tree.
- CAD release workflow on `<part>/vN` tags.
- `mesh/` → `sensorhub/basestation/radio/`; add the `meshdet` service (parses
  the `contracts/mesh` line grammar off `home/mesh/#` into `<device>/<key>`
  readings, so LoRa telemetry lands on the same device page as WiFi).
- `sensors/{miclogger,espnowbridge,espnowmeter}` → `~/code/slugsense/devices/`.
  Check `systemctl --user cat espnowbridge` for source-path references first.
- `sensors/plantlogger` → its own repo. Note the plant page at
  `:8088/v/plant` is **live** and served by sensorhub
  (`ingest/pages/plant.json`, channels `home/plant/{dev}/…`); only the orphaned
  standalone server in `sensors/plantlogger/server/` is dead and should be
  deleted rather than moved.

### Phase 6 — public-repo hygiene

LAN IPs, tailnet hostnames and USB serials out of docs and READMEs into
`~/.dusty/config.toml`-driven placeholders; confirm `Prefs.DEV_BLE_KEY_HEX` is
not the owner key.

## 7. Open question

**Which three cameras.** The plan above assumes `rt1062cam`, `n6cam` and
`xiaocam1` — the only three that have run the shared runtimes, and the N6 is
what the LoRa hat is designed for. That leaves `esp32_s3_cam`, `pi5cam` and
`n6_speedcam` to be archived (tarball to `~/.sargineer/attic/`, then removed
from HEAD; history keeps them). **Changing this choice changes only the archive
list**, nothing else in the plan.

## 8. If the split is later regretted

Merge `dustycam-phone` back into `dustycam-firmware` first: the phone and
`dusty_ble` moved in lockstep through P0/P1, and `phone_app_plan.md` decisions
are really firmware decisions. The criterion: if more than one in three firmware
changes also touches the phone, merge them. `dustycam-contracts` folds into
firmware second. `dustycam-hardware` and `dustycam-site` stay separate
regardless — different toolchains, different binary churn, independent deploys.
