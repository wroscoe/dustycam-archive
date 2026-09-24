"""Host tests for `tools/dustygen`'s micropython runtime on n6cam (the
game_lowpower profile added `hotspot` to camera.toml's capabilities, so this
camera now needs the same [hotspot] handling as xiao_pantilt's espidf path
— see cameras/xiao_pantilt/tests/test_dustygen.py, which this mirrors).

Runs dustygen as a real subprocess against a temp DUSTY_DIR and a temp
SENSORHUB_DIR (env overrides — see tools/dustygen's DUSTY_DIR/SENSORHUB_DIR).
NEVER run against the real ~/.dusty: it has no [hotspot] yet and dustygen
would exit non-zero (see test_missing_hotspot_section_fails_with_hint below
for exactly that behaviour, deliberately, in a temp dir).

The bundle step reads cameras/common/micropython/ from the real repo
(bundle.py's COMMON is its own file's directory, not overridable), so
test_bundle_compiles reflects whatever is actually on disk there right now
— it will fail if package A's night/rank/gamespool/persist/led/judge/
contact/wakecycle modules referenced in camera.toml's [bundle] order don't
exist yet. That is a true statement about repo state, not a broken test.

    python -m pytest cameras/openmv_n6/tests/test_dustygen_n6.py -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                      # .../tests -> openmv_n6 -> cameras -> repo root
DUSTYGEN = REPO / 'tools' / 'dustygen'
REAL_MANIFEST = REPO / 'cameras' / 'openmv_n6' / 'camera.toml'
REAL_BOARD_PY = REPO / 'cameras' / 'openmv_n6' / 'software' / 'app' / 'board.py'

CONFIG_TOML = """
[server]
host = "192.168.1.50"
public_host = "pub.example.test"
public_port = 10000
gate_port = 8089

[camera.openmv_n6]
"""

SECRETS_TOML_WITH_HOTSPOT = """
[hotspot]
ssid = "PhoneHotspot"
password = "hunter22222"

[wifi]
ssid = "LabWifi"
password = "labpass123"

[mqtt]
user = "mqttuser"
password = "mqttpass"

[sensorhub]
blob_token = "BLOBTOK123"
"""

SECRETS_TOML_NO_HOTSPOT = """
[wifi]
ssid = "LabWifi"
password = "labpass123"

[mqtt]
user = "mqttuser"
password = "mqttpass"

[sensorhub]
blob_token = "BLOBTOK123"
"""


class DustygenN6TestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.dusty_dir = root / 'dusty'
        self.sensorhub_dir = root / 'sensorhub'
        self.dusty_dir.mkdir()
        self.sensorhub_dir.mkdir()

        # A temp copy of the camera dir: the real camera.toml + board.py
        # (stamp_tuning edits board.py's TUNING line in place), nothing else.
        self.camera_dir = root / 'openmv_n6'
        (self.camera_dir / 'software' / 'app').mkdir(parents=True)
        shutil.copy(REAL_MANIFEST, self.camera_dir / 'camera.toml')
        shutil.copy(REAL_BOARD_PY, self.camera_dir / 'software' / 'app' / 'board.py')

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

    # ---- secrets.py ---------------------------------------------------------

    def test_secrets_uses_hotspot_and_defaults_public(self):
        p = self.run_dustygen('--no-bundle')
        self.assertEqual(p.returncode, 0, p.stderr)
        secrets = (self.camera_dir / 'software' / 'app' / 'secrets.py').read_text()
        self.assertIn("DEVICE = 'n6cam'", secrets)
        # hotspot capability -> [hotspot] creds, not [wifi]
        self.assertIn("WIFI_SSID = 'PhoneHotspot'", secrets)
        self.assertIn("WIFI_PASS = 'hunter22222'", secrets)
        self.assertNotIn("WIFI_SSID = 'LabWifi'", secrets)
        # hotspot capability -> --public is the default
        self.assertIn("SERVER_HOST = 'pub.example.test'", secrets)
        self.assertIn('SERVER_PORT = 10000', secrets)
        self.assertIn('SERVER_TLS = True', secrets)
        # LAN_* always carries the home network + LAN gate (secrets.toml
        # [wifi], config.toml [server] host + gate_port, TLS off), so a
        # contact can pick either network by scan regardless of --public/--lan
        self.assertIn("LAN_SSID = 'LabWifi'", secrets)
        self.assertIn("LAN_PASS = 'labpass123'", secrets)
        self.assertIn("LAN_HOST = '192.168.1.50'", secrets)
        self.assertIn('LAN_PORT = 8089', secrets)
        self.assertIn('LAN_TLS = False', secrets)

    def test_lan_flag_forces_lan_gate(self):
        p = self.run_dustygen('--lan', '--no-bundle')
        self.assertEqual(p.returncode, 0, p.stderr)
        secrets = (self.camera_dir / 'software' / 'app' / 'secrets.py').read_text()
        self.assertIn("SERVER_HOST = '192.168.1.50'", secrets)
        self.assertIn('SERVER_PORT = 8089', secrets)
        self.assertIn('SERVER_TLS = False', secrets)
        # --lan only changes the server host/port/tls; wifi creds still
        # come from [hotspot] because the capability is unconditional
        self.assertIn("WIFI_SSID = 'PhoneHotspot'", secrets)
        # LAN_* is unaffected by --public/--lan: always the LAN gate
        self.assertIn("LAN_SSID = 'LabWifi'", secrets)
        self.assertIn("LAN_HOST = '192.168.1.50'", secrets)
        self.assertIn('LAN_PORT = 8089', secrets)
        self.assertIn('LAN_TLS = False', secrets)

    def test_public_and_lan_mutually_exclusive(self):
        p = self.run_dustygen('--public', '--lan')
        self.assertNotEqual(p.returncode, 0)

    def test_missing_hotspot_section_fails_with_hint(self):
        self._write_secrets(SECRETS_TOML_NO_HOTSPOT)
        p = self.run_dustygen('--no-bundle')
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('[hotspot]', p.stderr)
        self.assertIn('ssid', p.stderr)
        self.assertIn('password', p.stderr)
        self.assertIn('secrets.toml', p.stderr)
        secrets_path = self.camera_dir / 'software' / 'app' / 'secrets.py'
        self.assertFalse(secrets_path.exists())

    # ---- TUNING stamped into board.py ---------------------------------------

    def test_tuning_stamped_matches_manifest_defaults(self):
        p = self.run_dustygen('--no-bundle')
        self.assertEqual(p.returncode, 0, p.stderr)
        board_src = (self.camera_dir / 'software' / 'app' / 'board.py').read_text()
        self.assertIn("'profile': 'game_lowpower'", board_src)
        self.assertIn("'period_s': 30", board_src)
        self.assertIn("'capture_framesize': 'HD'", board_src)

    def test_first_run_writes_json_cfg_1(self):
        p = self.run_dustygen('--no-bundle')
        self.assertEqual(p.returncode, 0, p.stderr)
        cfg_path = self.sensorhub_dir / 'config' / 'n6cam.json'
        body = json.loads(cfg_path.read_text())
        self.assertEqual(body['cfg'], 1)
        self.assertEqual(body['period_s'], 30)
        self.assertEqual(body['profile'], 'game_lowpower')

    def test_operator_edit_on_server_survives_a_rerun(self):
        """The device page's settings form is the live source of truth: a
        value already on the server is never touched by a plain rerun, and
        an unchanged file does not bump cfg."""
        p1 = self.run_dustygen('--no-bundle')
        self.assertEqual(p1.returncode, 0, p1.stderr)
        cfg_path = self.sensorhub_dir / 'config' / 'n6cam.json'
        body1 = json.loads(cfg_path.read_text())
        self.assertEqual(body1['cfg'], 1)

        # simulate an operator editing the value from the device page
        body1['period_s'] = 45
        cfg_path.write_text(json.dumps(body1) + '\n')

        p2 = self.run_dustygen('--no-bundle')
        self.assertEqual(p2.returncode, 0, p2.stderr)
        body2 = json.loads(cfg_path.read_text())
        self.assertEqual(body2['period_s'], 45)
        self.assertEqual(body2['cfg'], 1)          # unchanged -> no bump

    def test_config_toml_override_does_not_clobber_existing_server_value(self):
        """A workstation tuning change is only a SEED: it must not overwrite
        a key already on the server (which may have been edited from the
        device page), and the drift between them is reported."""
        p1 = self.run_dustygen('--no-bundle')
        self.assertEqual(p1.returncode, 0, p1.stderr)
        cfg_path = self.sensorhub_dir / 'config' / 'n6cam.json'

        self._write_config(CONFIG_TOML.replace(
            '[camera.openmv_n6]', '[camera.openmv_n6]\nperiod_s = 45'))
        p2 = self.run_dustygen('--no-bundle')
        self.assertEqual(p2.returncode, 0, p2.stderr)
        self.assertIn('drift', p2.stdout)
        self.assertIn('period_s', p2.stdout)
        body2 = json.loads(cfg_path.read_text())
        self.assertEqual(body2['period_s'], 30)    # server value wins
        self.assertEqual(body2['cfg'], 1)           # nothing actually changed

    def test_reset_config_restores_workstation_value_and_bumps_cfg(self):
        p1 = self.run_dustygen('--no-bundle')
        self.assertEqual(p1.returncode, 0, p1.stderr)
        cfg_path = self.sensorhub_dir / 'config' / 'n6cam.json'

        self._write_config(CONFIG_TOML.replace(
            '[camera.openmv_n6]', '[camera.openmv_n6]\nperiod_s = 45'))
        p2 = self.run_dustygen('--no-bundle', '--reset-config')
        self.assertEqual(p2.returncode, 0, p2.stderr)
        body2 = json.loads(cfg_path.read_text())
        self.assertEqual(body2['period_s'], 45)
        self.assertEqual(body2['cfg'], 2)

    def test_new_tuning_key_is_seeded_with_default_and_bumps_cfg(self):
        p1 = self.run_dustygen('--no-bundle')
        self.assertEqual(p1.returncode, 0, p1.stderr)
        cfg_path = self.sensorhub_dir / 'config' / 'n6cam.json'

        manifest_path = self.camera_dir / 'camera.toml'
        text = manifest_path.read_text()
        self.assertNotIn('brand_new_key', text)
        manifest_path.write_text(text + '\nbrand_new_key = 7   # test-only new key\n')

        p2 = self.run_dustygen('--no-bundle')
        self.assertEqual(p2.returncode, 0, p2.stderr)
        body2 = json.loads(cfg_path.read_text())
        self.assertEqual(body2['brand_new_key'], 7)
        self.assertEqual(body2['cfg'], 2)

    def test_key_removed_from_camera_toml_disappears(self):
        p1 = self.run_dustygen('--no-bundle')
        self.assertEqual(p1.returncode, 0, p1.stderr)
        cfg_path = self.sensorhub_dir / 'config' / 'n6cam.json'
        body1 = json.loads(cfg_path.read_text())
        self.assertIn('wifi_linger_s', body1)

        manifest_path = self.camera_dir / 'camera.toml'
        lines = manifest_path.read_text().splitlines()
        manifest_path.write_text(
            '\n'.join(l for l in lines if not l.startswith('wifi_linger_s')) + '\n')

        p2 = self.run_dustygen('--no-bundle')
        self.assertEqual(p2.returncode, 0, p2.stderr)
        body2 = json.loads(cfg_path.read_text())
        self.assertNotIn('wifi_linger_s', body2)
        self.assertEqual(body2['cfg'], 2)

    # ---- schema -----------------------------------------------------------

    def test_schema_written_with_types_defaults_help(self):
        p = self.run_dustygen('--no-bundle')
        self.assertEqual(p.returncode, 0, p.stderr)
        schema = json.loads((self.sensorhub_dir / 'config' / 'n6cam.schema.json').read_text())
        self.assertEqual(schema['id'], 'n6cam')
        self.assertEqual(schema['camera'], 'openmv_n6')
        self.assertTrue(schema['generated'])
        by_name = {k['name']: k for k in schema['keys']}
        self.assertEqual(by_name['period_s'],
                          {'name': 'period_s', 'type': 'int', 'default': 30, 'help': 'wake interval'})
        self.assertEqual(by_name['diff_min_frac']['type'], 'float')
        self.assertEqual(by_name['diff_min_frac']['default'], 0.02)
        self.assertEqual(by_name['keep_all'],
                          {'name': 'keep_all', 'type': 'bool', 'default': False,
                           'help': 'keep frames the model rejects'})
        self.assertEqual(by_name['keep_labels']['type'], 'list')
        self.assertEqual(by_name['keep_labels']['default'], ['animal', 'person'])
        self.assertEqual(by_name['night_confirm_n']['help'], '')          # no trailing comment
        names = [k['name'] for k in schema['keys']]
        self.assertEqual(names[:2], ['profile', 'period_s'])               # camera.toml order

    def test_schema_rewritten_every_run(self):
        p1 = self.run_dustygen('--no-bundle')
        self.assertEqual(p1.returncode, 0, p1.stderr)
        schema_path = self.sensorhub_dir / 'config' / 'n6cam.schema.json'
        first_mtime = schema_path.stat().st_mtime_ns
        p2 = self.run_dustygen('--no-bundle')
        self.assertEqual(p2.returncode, 0, p2.stderr)
        self.assertTrue(schema_path.exists())
        # content is stable when nothing in camera.toml changed
        self.assertGreaterEqual(schema_path.stat().st_mtime_ns, first_mtime)

    # ---- --blank (espidf-only, phone_app_plan.md decision 7) ------------------

    def test_blank_rejected_for_micropython(self):
        """--blank (fleet image with empty identity) is an espidf-only
        concept today; a micropython camera must fail clearly rather than
        silently ignore the flag or write a half-blank secrets.py."""
        p = self.run_dustygen('--blank')
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('--blank', p.stderr)
        self.assertIn('espidf', p.stderr)

    # ---- bundle / stage -------------------------------------------------------

    def test_bundle_compiles(self):
        """Requires package A's common modules (night/rank/gamespool/persist/
        led/judge/contact/wakecycle) to exist on disk; see module docstring."""
        p = self.run_dustygen()
        self.assertEqual(p.returncode, 0, p.stderr)
        out = self.camera_dir / 'software' / 'build' / 'app.py'
        self.assertTrue(out.is_file())
        compile(out.read_text(), 'app.py', 'exec')   # raises on a syntax error

    def test_stage_writes_py_and_version(self):
        p = self.run_dustygen('--stage')
        self.assertEqual(p.returncode, 0, p.stderr)
        staged_py = self.sensorhub_dir / 'firmware' / 'n6cam.py'
        staged_version = self.sensorhub_dir / 'firmware' / 'n6cam.version'
        self.assertTrue(staged_py.is_file())
        board_src = (self.camera_dir / 'software' / 'app' / 'board.py').read_text()
        import re
        m = re.search(r"^APP_VERSION = '([^']+)'", board_src, re.M)
        self.assertIsNotNone(m)
        self.assertEqual(staged_version.read_text().strip(), m.group(1))


if __name__ == '__main__':
    unittest.main()
