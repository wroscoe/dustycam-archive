# dustycli — the `dusty` command

One generator and fleet tool for every camera: secrets, tuning, the hub's
config seed and schema, the MicroPython bundle, blank fleet images, and OTA
staging. The full behaviour is documented in `dusty.py`'s module docstring and
in `docs/camera_standard.md` §5.

```
tools/dustycli/dusty.py <camera-dir> [--public|--lan] [--stage] [--no-bundle]
tools/dustycli/dusty.py --phone-json
```

## Why it is a directory

`docs/REPO_PLAN.md` §4 splits this into its own repository, `wroscoe/dustycli`.
That carve is `git filter-repo --subdirectory-filter tools/dustycli`, which
cannot operate on a single file — so the script became a package directory
before the split rather than during it.

## What still ties it to this repo

Three things, each already made overridable so the split is mechanical:

| Coupling | Escape hatch |
|---|---|
| the MicroPython bundler under `runtime/` | `DUSTY_RUNTIME_DIR` |
| `~/.dusty` and `/hd2/sensorhub` locations | `DUSTY_DIR`, `SENSORHUB_DIR` |
| the camera list for `--phone-json` | `[phone] cameras` in `config.toml` |

`REPO` is still used to print paths relative to the checkout and as the
`--phone-json` fallback scan root. Both go away when this is installed as a
command rather than run from a path.

## Installing

```
pip install -e tools/dustycli      # then: dusty <camera-dir>
```

Stdlib only, on purpose: it runs on a workstation with no virtualenv and has to
keep working when every other toolchain is in a container.
