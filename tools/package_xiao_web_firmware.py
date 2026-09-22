#!/usr/bin/env python3
"""Package a verified XIAO wildlife-camera build for ESP Web Tools."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


EMPTY_IDENTITY_KEYS = (
    "CONFIG_DUSTY_DEVICE",
    "CONFIG_DUSTY_WIFI_SSID",
    "CONFIG_DUSTY_WIFI_PASS",
    "CONFIG_DUSTY_SERVER_HOST",
    "CONFIG_DUSTY_BLOB_TOKEN",
    "CONFIG_DUSTY_BLE_KEY",
)
EXPECTED_FLASH_FILES = {
    "0x0": "bootloader/bootloader.bin",
    "0xc000": "partition_table/partition-table.bin",
    "0x13000": "ota_data_initial.bin",
    "0x20000": "xiaocam1.bin",
}
VERSION_RE = re.compile(r"^v[0-9]{8}-[0-9]{6}$")


def sdkconfig_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("CONFIG_") and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def require_blank_identity(path: Path) -> None:
    if not path.is_file():
        raise ValueError(f"missing generated config: {path}")
    values = sdkconfig_values(path)
    for key in EMPTY_IDENTITY_KEYS:
        if values.get(key) != '""':
            raise ValueError(f"{path}: {key} must be empty for a public fleet image")


def package(app_dir: Path, merged: Path, output_dir: Path) -> dict[str, object]:
    app_dir = app_dir.resolve()
    build_dir = app_dir / "build"
    merged = merged.resolve()

    require_blank_identity(app_dir / "sdkconfig.secrets")
    require_blank_identity(app_dir / "sdkconfig")

    args = json.loads((build_dir / "flasher_args.json").read_text(encoding="utf-8"))
    if args.get("flash_files") != EXPECTED_FLASH_FILES:
        raise ValueError(f"unexpected flash map: {args.get('flash_files')!r}")
    if args.get("extra_esptool_args", {}).get("chip") != "esp32s3":
        raise ValueError("browser image must target esp32s3")
    expected_settings = {"flash_mode": "dio", "flash_size": "8MB", "flash_freq": "80m"}
    if args.get("flash_settings") != expected_settings:
        raise ValueError(f"unexpected flash settings: {args.get('flash_settings')!r}")

    for offset, relative in EXPECTED_FLASH_FILES.items():
        part = build_dir / relative
        if not part.is_file() or part.stat().st_size == 0:
            raise ValueError(f"missing flash part at {offset}: {part}")

    data = merged.read_bytes()
    if not data or len(data) > 8 * 1024 * 1024:
        raise ValueError("merged image is empty or larger than the XIAO's 8 MB flash")
    if data[0] != 0xE9 or data[0x20000] != 0xE9:
        raise ValueError("merged image is missing an ESP bootloader or app image")
    if any(byte != 0xFF for byte in data[0xD000:0x13000]):
        raise ValueError("merged image writes into the NVS identity partition")
    if b"DUSTYCAM_RELEASE_SENTINEL" in data:
        raise ValueError("merged image contains a release-build credential canary")

    version = (app_dir / "version.txt").read_text(encoding="utf-8").strip()
    if not VERSION_RE.fullmatch(version):
        raise ValueError(f"unexpected firmware version: {version!r}")

    output_dir.mkdir(parents=True, exist_ok=True)
    asset_name = f"xiao-wildlife-{version}.bin"
    asset = output_dir / asset_name
    shutil.copyfile(merged, asset)
    digest = hashlib.sha256(data).hexdigest()

    manifest = {
        "name": "DustyCam XIAO Wildlife Camera",
        "version": version,
        "new_install_prompt_erase": False,
        "new_install_improv_wait_time": 0,
        "builds": [
            {
                "chipFamily": "ESP32-S3",
                "serialType": "cdc",
                "parts": [{"path": asset_name, "offset": 0}],
            }
        ],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    release = {
        "schema": 1,
        "board": "Seeed Studio XIAO ESP32S3 Sense",
        "firmware": "DustyCam wildlife camera",
        "version": version,
        "file": asset_name,
        "bytes": len(data),
        "sha256": digest,
        "full_chip_erase": True,
        "provision_after_flash": "DustyCam Android app over BLE",
        "source_flash_map": EXPECTED_FLASH_FILES,
    }
    (output_dir / "release.json").write_text(
        json.dumps(release, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "SHA256SUMS").write_text(f"{digest}  {asset_name}\n", encoding="utf-8")
    return release


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-dir", type=Path, required=True)
    parser.add_argument("--merged", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    release = package(args.app_dir, args.merged, args.output_dir)
    print(
        f"web firmware -> {args.output_dir} "
        f"({release['bytes']} bytes, sha256 {release['sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
