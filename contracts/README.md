# dustycam-contracts

The single source of truth for every format that crosses a boundary in the
DustyCam system: camera ↔ hub, camera ↔ phone, camera ↔ mesh, build ↔ flasher.

Today this directory lives inside the firmware repo. It becomes its own
repository (`wroscoe/dustycam-contracts`) in phase 3 of
[`docs/REPO_PLAN.md`](../docs/REPO_PLAN.md), at which point consumers vendor
the generated files at a tag instead of reading them from a sibling directory.

## Why this exists

Every one of these formats is currently defined in prose in `docs/*.md` and
then re-typed by hand in each language. Verified duplications at the time of
writing:

| Contract | Hand-copied in |
|---|---|
| frame meta keys | `STANDARD_META` in three test files, `app.py` `build_meta()`'s format string, `dc_meta_t` in C, sensorhub's `ingest.py` reader |
| BLE frame header, flags, size limits | `ble_frame.h` (`BLE_FRAME_*`) and `Framer.java` (`HEADER_LEN`, `FLAG_*`, `REQ_MAX`/`RSP_MAX`/`DATA_MAX`) — byte for byte the same numbers |
| GATT UUIDs | `dusty_ble.c` (a comment) and `DustyLink.java` (`BASE_FMT`) |
| mesh line grammar | `cameras/openmv_n6/hardware/lora_hat/PLAN.md` only — nothing parses it yet |

`build_meta()` does not even use a JSON library: it formats the frame meta with
`'{"ts": %d, "seq": %d, ...}' % (...)`. Nothing checks that the result matches
what the hub expects to read.

## Layout

```
VERSION              one integer, bumped on any change here
meta.toml            frame meta keys, their types and who sets them
ble/gatt.toml        UUIDs, frame header, flags, size limits, protocol version
mesh/lines.toml      LoRa uplink line grammar and the downlink command set
vectors/             golden data every language replays in its own tests
gen/                 GENERATED constants — do not edit
  python/dusty_contract.py
  c/dusty_contract.h
  java/Contract.java
```

## Regenerating

```
tools/contractgen            # rewrite gen/
tools/contractgen --check    # fail if gen/ is stale (CI)
```

`gen/` is committed so that a firmware or APK build never needs the generator.

## Rules

1. **Receivers before senders.** When a contract changes, the merge order is
   contracts → sensorhub → firmware → phone → site. Field cameras update slowly
   over OTA, so the hub must accept both the old and the new shape.
2. **Additive by default.** Adding a key bumps `VERSION` only. Removing or
   renaming one also bumps that surface's own protocol integer (`ble.proto`
   here, `release.json`'s `schema`, `dusty_phone.json`'s `v`).
