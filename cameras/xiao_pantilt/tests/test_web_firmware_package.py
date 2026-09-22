"""Tests for the XIAO browser-firmware release packager."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "tools" / "package_xiao_web_firmware.py"
SPEC = importlib.util.spec_from_file_location("package_xiao_web_firmware", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class WebFirmwarePackageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = Path(self.tmp.name) / "app"
        self.build = self.app / "build"
        self.output = Path(self.tmp.name) / "out"
        (self.build / "bootloader").mkdir(parents=True)
        (self.build / "partition_table").mkdir()
        self.app.joinpath("version.txt").write_text("v20260922-000000\n")
        blank = "\n".join(f'{key}=""' for key in MODULE.EMPTY_IDENTITY_KEYS) + "\n"
        self.app.joinpath("sdkconfig.secrets").write_text(blank)
        self.app.joinpath("sdkconfig").write_text(blank)

        self.build.joinpath("bootloader/bootloader.bin").write_bytes(b"\xe9BOOT")
        self.build.joinpath("partition_table/partition-table.bin").write_bytes(b"\xaaPPT")
        self.build.joinpath("ota_data_initial.bin").write_bytes(b"\xff" * 16)
        self.build.joinpath("xiaocam1.bin").write_bytes(b"\xe9APP")
        self.build.joinpath("flasher_args.json").write_text(json.dumps({
            "flash_settings": {"flash_mode": "dio", "flash_size": "8MB", "flash_freq": "80m"},
            "flash_files": MODULE.EXPECTED_FLASH_FILES,
            "extra_esptool_args": {"chip": "esp32s3"},
        }))

        merged = bytearray(b"\xff" * 0x20010)
        merged[0:5] = b"\xe9BOOT"
        merged[0x20000:0x20004] = b"\xe9APP"
        self.merged = self.build / "xiao-wildlife-factory.bin"
        self.merged.write_bytes(merged)

    def test_packages_manifest_checksum_and_release_metadata(self):
        release = MODULE.package(self.app, self.merged, self.output)
        manifest = json.loads(self.output.joinpath("manifest.json").read_text())
        self.assertEqual(manifest["builds"][0]["chipFamily"], "ESP32-S3")
        self.assertEqual(manifest["builds"][0]["serialType"], "cdc")
        self.assertEqual(manifest["builds"][0]["parts"][0]["offset"], 0)
        self.assertTrue(manifest["new_install_prompt_erase"] is False)
        self.assertTrue(release["full_chip_erase"])
        self.assertTrue(self.output.joinpath(release["file"]).is_file())
        self.assertIn(release["sha256"], self.output.joinpath("SHA256SUMS").read_text())

    def test_rejects_identity_bearing_config(self):
        path = self.app / "sdkconfig"
        path.write_text(path.read_text().replace(
            'CONFIG_DUSTY_WIFI_SSID=""', 'CONFIG_DUSTY_WIFI_SSID="private-network"'))
        with self.assertRaisesRegex(ValueError, "must be empty"):
            MODULE.package(self.app, self.merged, self.output)

    def test_rejects_image_that_writes_nvs(self):
        data = bytearray(self.merged.read_bytes())
        data[0xD000] = 0
        self.merged.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "NVS"):
            MODULE.package(self.app, self.merged, self.output)

    def test_rejects_release_credential_canary(self):
        data = bytearray(self.merged.read_bytes())
        data.extend(b"DUSTYCAM_RELEASE_SENTINEL_PASS")
        self.merged.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "credential canary"):
            MODULE.package(self.app, self.merged, self.output)


if __name__ == "__main__":
    unittest.main()
