"""Host tests for `tools/dustygen`'s espidf runtime (xiaocam1).

Runs dustygen as a real subprocess against a temp DUSTY_DIR, a temp
SENSORHUB_DIR and a temp copy of the camera dir (env vars DUSTY_DIR /
SENSORHUB_DIR override the real ~/.dusty and /hd2/sensorhub — see
tools/dustygen). No board, no network, no real secrets are read or written.

    python3 -m unittest discover -s cameras/xiaocam1/tests -v
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                      # .../tests -> xiaocam1 -> cameras -> repo root
DUSTYGEN = REPO / 'tools' / 'dustygen'
REAL_MANIFEST = REPO / 'cameras' / 'xiaocam1' / 'camera.toml'

CONFIG_TOML = """
[server]
host = "192.168.1.50"
public_host = "pub.example.test"
public_port = 10000
gate_port = 8089

[camera.xiaocam1]
"""

SECRETS_TOML_WITH_HOTSPOT = """
[hotspot]
ssid = "PhoneHotspot"
password = "hunter22222"

[wifi]
ssid = "LabWifi"
password = "labpass123"

[sensorhub]
blob_token = "BLOBTOK123"
"""

SECRETS_TOML_NO_HOTSPOT = """
[wifi]
ssid = "LabWifi"
password = "labpass123"

[sensorhub]
blob_token = "BLOBTOK123"
"""


class DustygenEspidfTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.dusty_dir = root / 'dusty'
        self.sensorhub_dir = root / 'sensorhub'
        self.dusty_dir.mkdir()
        self.sensorhub_dir.mkdir()

        # A temp copy of the camera dir: just camera.toml (the real,
        # generated manifest) + an empty software/app/, which is all
        # dustygen touches. Avoids copying the hardware/ CAD tree.
        self.camera_dir = root / 'xiao_pantilt'
        (self.camera_dir / 'software' / 'app').mkdir(parents=True)
        shutil.copy(REAL_MANIFEST, self.camera_dir / 'camera.toml')

        self._write_config(CONFIG_TOML)
        self._write_secrets(SECRETS_TOML_WITH_HOTSPOT)

    def _write_config(self, text):
        (self.dusty_dir / 'config.toml').write_text(text)

    def _write_secrets(self, text):
        (self.dusty_dir / 'secrets.toml').write_text(text)

    def run_dustygen(self, *args):
        env = dict(os.environ)
        env['DUSTY_DIR'] = str(self.dusty_dir)
        env['SENSORHUB_DIR'] = str(self.sensorhub_dir)
        return subprocess.run(
            [sys.executable, str(DUSTYGEN), str(self.camera_dir), *args],
            env=env, capture_output=True, text=True,
        )

    # ---- sdkconfig.secrets ------------------------------------------------

    def test_sdkconfig_secrets_uses_hotspot_and_defaults_public(self):
        p = self.run_dustygen()
        self.assertEqual(p.returncode, 0, p.stderr)
        secrets = (self.camera_dir / 'software' / 'app' / 'sdkconfig.secrets').read_text()
        self.assertIn('CONFIG_DUSTY_DEVICE="xiaocam1"', secrets)
        # hotspot capability -> [hotspot] creds, not [wifi]
        self.assertIn('CONFIG_DUSTY_WIFI_SSID="PhoneHotspot"', secrets)
        self.assertIn('CONFIG_DUSTY_WIFI_PASS="hunter22222"', secrets)
        self.assertNotIn('LabWifi', secrets)
        # hotspot capability -> --public is the default
        self.assertIn('CONFIG_DUSTY_SERVER_HOST="pub.example.test"', secrets)
        self.assertIn('CONFIG_DUSTY_SERVER_PORT=10000', secrets)
        self.assertIn('CONFIG_DUSTY_SERVER_TLS=y', secrets)
        self.assertIn('CONFIG_DUSTY_BLOB_TOKEN="BLOBTOK123"', secrets)

    def test_lan_flag_forces_lan_gate(self):
        p = self.run_dustygen('--lan')
        self.assertEqual(p.returncode, 0, p.stderr)
        secrets = (self.camera_dir / 'software' / 'app' / 'sdkconfig.secrets').read_text()
        self.assertIn('CONFIG_DUSTY_SERVER_HOST="192.168.1.50"', secrets)
        self.assertIn('CONFIG_DUSTY_SERVER_PORT=8089', secrets)
        self.assertIn('CONFIG_DUSTY_SERVER_TLS=n', secrets)

    def test_public_and_lan_mutually_exclusive(self):
        p = self.run_dustygen('--public', '--lan')
        self.assertNotEqual(p.returncode, 0)

    # ---- tuning_defaults.h --------------------------------------------------

    def test_tuning_defaults_header(self):
        p = self.run_dustygen()
        self.assertEqual(p.returncode, 0, p.stderr)
        h = (self.camera_dir / 'software' / 'app' / 'main' / 'tuning_defaults.h').read_text()
        self.assertIn('#ifndef DUSTY_TUNING_DEFAULTS_H', h)
        self.assertIn('#define DUSTY_TUNING_DEFAULTS_H', h)
        self.assertIn('#endif', h)
        # string
        self.assertIn('#define DUSTY_DEF_PROFILE "game_lowpower"', h)
        self.assertIn('#define DUSTY_DEF_MODE "live"', h)
        # int
        self.assertIn('#define DUSTY_DEF_PERIOD_S 30', h)
        self.assertIn('#define DUSTY_DEF_SPOOL_MAX_FRAMES 20000', h)
        # float, decimal point present
        self.assertIn('#define DUSTY_DEF_DIFF_MIN_FRAC 0.02', h)
        # bool -> 0/1
        self.assertIn('#define DUSTY_DEF_KEEP_ALL 0', h)
        self.assertIn('#define DUSTY_DEF_LED_CAPTURE 1', h)
        # keep_labels -> brace list + _N count
        self.assertIn('#define DUSTY_DEF_KEEP_LABELS {"animal","person"}', h)
        self.assertIn('#define DUSTY_DEF_KEEP_LABELS_N 2', h)

    # ---- server config json -------------------------------------------------

    def test_server_config_cfg_increments_only_on_change(self):
        p1 = self.run_dustygen()
        self.assertEqual(p1.returncode, 0, p1.stderr)
        cfg_path = self.sensorhub_dir / 'config' / 'xiaocam1.json'
        body1 = json.loads(cfg_path.read_text())
        self.assertEqual(body1['cfg'], 1)
        self.assertEqual(body1['period_s'], 30)

        # rerun, nothing changed -> cfg stays put
        p2 = self.run_dustygen()
        self.assertEqual(p2.returncode, 0, p2.stderr)
        body2 = json.loads(cfg_path.read_text())
        self.assertEqual(body2['cfg'], 1)

        # a workstation tuning override only SEEDS a key that isn't on the
        # server yet; period_s is already there, so it is left alone (the
        # device page's settings form is the live source of truth) -> no bump
        self._write_config(CONFIG_TOML.replace(
            '[camera.xiaocam1]', '[camera.xiaocam1]\nperiod_s = 45'))
        p3 = self.run_dustygen()
        self.assertEqual(p3.returncode, 0, p3.stderr)
        self.assertIn('drift', p3.stdout)
        body3 = json.loads(cfg_path.read_text())
        self.assertEqual(body3['period_s'], 30)
        self.assertEqual(body3['cfg'], 1)

        # --reset-config restores today's overwrite behaviour
        p4 = self.run_dustygen('--reset-config')
        self.assertEqual(p4.returncode, 0, p4.stderr)
        body4 = json.loads(cfg_path.read_text())
        self.assertEqual(body4['period_s'], 45)
        self.assertEqual(body4['cfg'], 2)

    def test_operator_edit_on_server_survives_a_rerun(self):
        p1 = self.run_dustygen()
        self.assertEqual(p1.returncode, 0, p1.stderr)
        cfg_path = self.sensorhub_dir / 'config' / 'xiaocam1.json'
        body1 = json.loads(cfg_path.read_text())
        body1['period_s'] = 45
        cfg_path.write_text(json.dumps(body1) + '\n')

        p2 = self.run_dustygen()
        self.assertEqual(p2.returncode, 0, p2.stderr)
        body2 = json.loads(cfg_path.read_text())
        self.assertEqual(body2['period_s'], 45)
        self.assertEqual(body2['cfg'], 1)

    def test_key_removed_from_camera_toml_disappears(self):
        p1 = self.run_dustygen()
        self.assertEqual(p1.returncode, 0, p1.stderr)
        cfg_path = self.sensorhub_dir / 'config' / 'xiaocam1.json'
        body1 = json.loads(cfg_path.read_text())
        self.assertIn('spool_max_frames', body1)

        manifest_path = self.camera_dir / 'camera.toml'
        lines = manifest_path.read_text().splitlines()
        manifest_path.write_text(
            '\n'.join(l for l in lines if not l.startswith('spool_max_frames')) + '\n')

        p2 = self.run_dustygen()
        self.assertEqual(p2.returncode, 0, p2.stderr)
        body2 = json.loads(cfg_path.read_text())
        self.assertNotIn('spool_max_frames', body2)
        self.assertEqual(body2['cfg'], 2)

    # ---- schema ---------------------------------------------------------------

    def test_schema_written_with_types_defaults_help(self):
        p = self.run_dustygen()
        self.assertEqual(p.returncode, 0, p.stderr)
        schema = json.loads((self.sensorhub_dir / 'config' / 'xiaocam1.schema.json').read_text())
        self.assertEqual(schema['id'], 'xiaocam1')
        self.assertEqual(schema['camera'], 'xiaocam1')
        by_name = {k['name']: k for k in schema['keys']}
        self.assertEqual(by_name['period_s'],
                          {'name': 'period_s', 'type': 'int', 'default': 30, 'help': 'wake interval'})
        self.assertEqual(by_name['mode'],
                          {'name': 'mode', 'type': 'str', 'default': 'live', 'help': 'live | setup'})
        self.assertEqual(by_name['keep_labels']['type'], 'list')
        self.assertEqual(by_name['keep_labels']['default'], ['animal', 'person'])
        self.assertEqual(by_name['night_confirm_n']['help'], '')

    # ---- missing [hotspot] ---------------------------------------------------

    def test_missing_hotspot_section_fails_with_hint(self):
        self._write_secrets(SECRETS_TOML_NO_HOTSPOT)
        p = self.run_dustygen()
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('[hotspot]', p.stderr)
        self.assertIn('ssid', p.stderr)
        self.assertIn('password', p.stderr)
        self.assertIn('secrets.toml', p.stderr)
        # and it must not have silently used the LAN wifi creds
        secrets_path = self.camera_dir / 'software' / 'app' / 'sdkconfig.secrets'
        self.assertFalse(secrets_path.exists())

    def test_lan_flag_does_not_need_hotspot(self):
        # --lan only forces the server host/port/tls choice; the wifi
        # creds still come from [hotspot] because the manifest lists the
        # capability regardless of --lan/--public. So missing [hotspot]
        # must still fail even with --lan.
        self._write_secrets(SECRETS_TOML_NO_HOTSPOT)
        p = self.run_dustygen('--lan')
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('[hotspot]', p.stderr)

    # ---- --stage --------------------------------------------------------------

    def test_stage_without_bin_fails_clearly(self):
        p = self.run_dustygen('--stage')
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('.bin', p.stderr)
        self.assertFalse((self.sensorhub_dir / 'firmware' / 'xiaocam1.bin').exists())

    def test_stage_with_bin_copies_and_writes_version(self):
        (self.camera_dir / 'software' / 'app' / 'version.txt').write_text('9.9.9-test\n')
        build_dir = self.camera_dir / 'software' / 'app' / 'build'
        build_dir.mkdir(parents=True)
        fake_bin = b'\x00\x01FAKEFIRMWAREBYTES\xff'
        (build_dir / 'xiaocam1.bin').write_bytes(fake_bin)

        p = self.run_dustygen('--stage')
        self.assertEqual(p.returncode, 0, p.stderr)

        staged_bin = self.sensorhub_dir / 'firmware' / 'xiaocam1.bin'
        staged_version = self.sensorhub_dir / 'firmware' / 'xiaocam1.version'
        self.assertEqual(staged_bin.read_bytes(), fake_bin)
        self.assertEqual(staged_version.read_text().strip(), '9.9.9-test')

    def test_missing_version_txt_is_created_with_default(self):
        p = self.run_dustygen()
        self.assertEqual(p.returncode, 0, p.stderr)
        version_path = self.camera_dir / 'software' / 'app' / 'version.txt'
        self.assertTrue(version_path.exists())
        self.assertEqual(version_path.read_text().strip(), '0.1.0-xiao')

    # ---- tuning_schema.h (phone_app_plan.md decision 8) ----------------------

    @staticmethod
    def _c_unescape(s):
        # inverse of dustygen's _c_escape: only \\ and \" are ever produced
        out = []
        i = 0
        while i < len(s):
            if s[i] == '\\' and i + 1 < len(s):
                out.append(s[i + 1])
                i += 2
            else:
                out.append(s[i])
                i += 1
        return ''.join(out)

    def test_schema_header_round_trips_to_the_same_json(self):
        p = self.run_dustygen()
        self.assertEqual(p.returncode, 0, p.stderr)
        h_path = self.camera_dir / 'software' / 'app' / 'main' / 'tuning_schema.h'
        h = h_path.read_text()
        self.assertIn('#ifndef DUSTY_TUNING_SCHEMA_H', h)
        self.assertIn('#define DUSTY_TUNING_SCHEMA_H', h)
        self.assertIn('#endif', h)
        self.assertLessEqual(h_path.stat().st_size, 4096)
        # no cfg/version key in today's schema -> no TUNING_SCHEMA_CFG
        self.assertNotIn('TUNING_SCHEMA_CFG', h)

        m = re.search(r'TUNING_SCHEMA_JSON\[\]\s*=\s*"(.*)";', h)
        self.assertIsNotNone(m, h)
        embedded = json.loads(self._c_unescape(m.group(1)))
        schema = json.loads((self.sensorhub_dir / 'config' / 'xiaocam1.schema.json').read_text())
        self.assertEqual(embedded, schema)
        self.assertEqual(embedded['id'], 'xiaocam1')
        by_name = {k['name']: k for k in embedded['keys']}
        self.assertEqual(by_name['period_s']['default'], 30)

    # ---- --blank fleet image (phone_app_plan.md decision 7) -------------------

    def test_blank_yields_empty_identity_but_keeps_port_and_tls(self):
        p = self.run_dustygen('--blank')
        self.assertEqual(p.returncode, 0, p.stderr)
        secrets_text = (self.camera_dir / 'software' / 'app' / 'sdkconfig.secrets').read_text()
        self.assertIn('CONFIG_DUSTY_DEVICE=""', secrets_text)
        self.assertIn('CONFIG_DUSTY_WIFI_SSID=""', secrets_text)
        self.assertIn('CONFIG_DUSTY_WIFI_PASS=""', secrets_text)
        self.assertIn('CONFIG_DUSTY_SERVER_HOST=""', secrets_text)
        self.assertIn('CONFIG_DUSTY_BLOB_TOKEN=""', secrets_text)
        self.assertIn('CONFIG_DUSTY_BLE_KEY=""', secrets_text)
        # port/tls are not identity: unaffected by --blank (hotspot capability -> public default)
        self.assertIn('CONFIG_DUSTY_SERVER_PORT=10000', secrets_text)
        self.assertIn('CONFIG_DUSTY_SERVER_TLS=y', secrets_text)
        self.assertNotIn('PhoneHotspot', secrets_text)
        self.assertNotIn('hunter22222', secrets_text)

    def test_blank_does_not_require_hotspot_secrets(self):
        self._write_secrets(SECRETS_TOML_NO_HOTSPOT)
        before = (self.dusty_dir / 'secrets.toml').read_text()
        p = self.run_dustygen('--blank')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual((self.dusty_dir / 'secrets.toml').read_text(), before)
        self.assertNotIn('generated new [ble] key', p.stdout)

    # ---- ble_key (phone_app_plan.md decisions 5, 7) ----------------------------

    def test_ble_key_generated_once_and_reused(self):
        p1 = self.run_dustygen()
        self.assertEqual(p1.returncode, 0, p1.stderr)
        self.assertIn('generated new [ble] key', p1.stdout)
        secrets_text = (self.dusty_dir / 'secrets.toml').read_text()
        m = re.search(r'\[ble\]\s*\nkey\s*=\s*"([0-9a-f]{64})"', secrets_text)
        self.assertIsNotNone(m, secrets_text)
        key1 = m.group(1)
        sdkconfig = (self.camera_dir / 'software' / 'app' / 'sdkconfig.secrets').read_text()
        self.assertIn('CONFIG_DUSTY_BLE_KEY="%s"' % key1, sdkconfig)

        # rerun: the same key is reused, not regenerated
        p2 = self.run_dustygen()
        self.assertEqual(p2.returncode, 0, p2.stderr)
        self.assertNotIn('generated new [ble] key', p2.stdout)
        secrets_text2 = (self.dusty_dir / 'secrets.toml').read_text()
        self.assertEqual(secrets_text2.count('[ble]'), 1)
        m2 = re.search(r'\[ble\]\s*\nkey\s*=\s*"([0-9a-f]{64})"', secrets_text2)
        self.assertEqual(m2.group(1), key1)

    # ---- stale sdkconfig removal (review finding: kconfgen loads an existing
    # sdkconfig with replace=False, so it WINS over a freshly generated
    # sdkconfig.secrets -- a --blank build could otherwise ship the last
    # real sdkconfig's identity/ble_key) --------------------------------------

    def test_blank_removes_stale_sdkconfig_with_identity(self):
        app_dir = self.camera_dir / 'software' / 'app'
        (app_dir / 'sdkconfig').write_text(
            'CONFIG_DUSTY_DEVICE="xiaocam1"\nCONFIG_DUSTY_BLE_KEY="deadbeef"\n')
        (app_dir / 'sdkconfig.old').write_text('CONFIG_DUSTY_DEVICE="xiaocam1"\n')
        p = self.run_dustygen('--blank')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse((app_dir / 'sdkconfig').exists())
        self.assertFalse((app_dir / 'sdkconfig.old').exists())
        self.assertIn('removed stale', p.stdout)
        self.assertIn('sdkconfig', p.stdout)

    def test_normal_run_also_removes_stale_sdkconfig(self):
        # requirement 1 says "blank OR normal": a stale sdkconfig is just
        # as much a hazard on a normal (identity-bearing) rebuild, since
        # kconfgen's replace=False means it silently keeps old values.
        app_dir = self.camera_dir / 'software' / 'app'
        (app_dir / 'sdkconfig').write_text('CONFIG_DUSTY_DEVICE="some-other-old-id"\n')
        p = self.run_dustygen()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse((app_dir / 'sdkconfig').exists())
        self.assertIn('removed stale', p.stdout)

    def test_no_stale_sdkconfig_means_no_removal_line_printed(self):
        p = self.run_dustygen()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn('removed stale', p.stdout)

    # ---- --verify-blank (review finding) ---------------------------------------

    def test_verify_blank_missing_bin_fails_clearly(self):
        p = self.run_dustygen('--verify-blank')
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('.bin', p.stderr)

    def test_verify_blank_passes_on_clean_bin(self):
        self._write_secrets(SECRETS_TOML_WITH_HOTSPOT + '\n[ble]\nkey = "%s"\n' % ('cd' * 32))
        build_dir = self.camera_dir / 'software' / 'app' / 'build'
        build_dir.mkdir(parents=True)
        (build_dir / 'xiaocam1.bin').write_bytes(b'\x00\xffJUNK_NO_SECRETS_HERE\xff\x00')
        p = self.run_dustygen('--verify-blank')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('OK', p.stdout)

    def test_verify_blank_detects_each_secret_kind_and_never_prints_the_value(self):
        ble_key = 'cd' * 32
        self._write_secrets(SECRETS_TOML_WITH_HOTSPOT + '\n[ble]\nkey = "%s"\n' % ble_key)
        build_dir = self.camera_dir / 'software' / 'app' / 'build'
        build_dir.mkdir(parents=True)
        bin_path = build_dir / 'xiaocam1.bin'
        cases = {
            'ble_key': ble_key.encode(),
            'wifi_pass': b'hunter22222',   # SECRETS_TOML_WITH_HOTSPOT [hotspot] password
            'token': b'BLOBTOK123',        # [sensorhub] blob_token
            'ssid': b'PhoneHotspot',       # [hotspot] ssid
        }
        for name, needle in cases.items():
            with self.subTest(name=name):
                bin_path.write_bytes(b'JUNKHEADER' + needle + b'JUNKTRAILER')
                p = self.run_dustygen('--verify-blank')
                self.assertNotEqual(p.returncode, 0)
                self.assertIn(name, p.stderr)
                # the offending item is named, but its value is never printed
                self.assertNotIn(needle.decode(), p.stderr)
                self.assertNotIn(needle.decode(), p.stdout)


class DustygenPhoneJsonTestCase(unittest.TestCase):
    """--phone-json takes no camera argument: it scans the real repo's
    cameras/*/camera.toml (runtime == espidf) and reads ~/.dusty via
    DUSTY_DIR, so only DUSTY_DIR needs to be a temp dir here."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dusty_dir = Path(self.tmp.name) / 'dusty'
        self.dusty_dir.mkdir()
        (self.dusty_dir / 'config.toml').write_text(CONFIG_TOML)
        (self.dusty_dir / 'secrets.toml').write_text(SECRETS_TOML_WITH_HOTSPOT)

    def run_dustygen(self, *args):
        env = dict(os.environ)
        env['DUSTY_DIR'] = str(self.dusty_dir)
        env['SENSORHUB_DIR'] = str(Path(self.tmp.name) / 'sensorhub')
        return subprocess.run(
            [sys.executable, str(DUSTYGEN), '--phone-json', *args],
            env=env, capture_output=True, text=True,
        )

    def test_phone_json_shape_and_permissions(self):
        p = self.run_dustygen()
        self.assertEqual(p.returncode, 0, p.stderr)
        out_path = Path(p.stdout.strip())
        self.assertEqual(out_path, self.dusty_dir / 'dusty_phone.json')
        self.assertTrue(out_path.is_file())
        self.assertEqual(oct(out_path.stat().st_mode)[-3:], '600')

        doc = json.loads(out_path.read_text())
        self.assertEqual(doc['v'], 1)
        self.assertEqual(doc['server'],
                          {'host': 'pub.example.test', 'port': 10000, 'tls': True, 'token': 'BLOBTOK123'})
        self.assertEqual(doc['hotspot'], {'ssid': 'PhoneHotspot', 'pass': 'hunter22222'})
        self.assertRegex(doc['ble_key'], r'^[0-9a-f]{64}$')
        ids = {c['id'] for c in doc['cameras']}
        # xiaocam1 (xiao_pantilt) is runtime=espidf and must be listed; a
        # micropython camera (e.g. n6cam) must not be.
        self.assertIn('xiaocam1', ids)
        self.assertNotIn('n6cam', ids)
        self.assertNotIn('rt1062cam', ids)

    def test_phone_json_missing_hotspot_fails_with_hint(self):
        (self.dusty_dir / 'secrets.toml').write_text(SECRETS_TOML_NO_HOTSPOT)
        p = self.run_dustygen()
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('[hotspot]', p.stderr)

    def test_phone_json_reuses_existing_ble_key(self):
        (self.dusty_dir / 'secrets.toml').write_text(
            SECRETS_TOML_WITH_HOTSPOT + '\n[ble]\nkey = "%s"\n' % ('ab' * 32))
        p = self.run_dustygen()
        self.assertEqual(p.returncode, 0, p.stderr)
        doc = json.loads(Path(p.stdout.strip()).read_text())
        self.assertEqual(doc['ble_key'], 'ab' * 32)


if __name__ == '__main__':
    unittest.main()
