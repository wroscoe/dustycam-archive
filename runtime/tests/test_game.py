"""Host tests for the game_lowpower profile modules (no board, no card).
Runs the shared stubs from runtime/tests/conftest.py (boardstubs)."""
import json

import config
import contact
import control
import gamespool
import judge
import led
import network
import night
import persist
import rank
import secrets
import wakecycle

STANDARD_META = {'ts', 'seq', 'w', 'h', 'v', 'cfg', 'ip', 'mode', 'why', 'diff', 'gate', 'heartbeat', 'buffered'}

NIGHT_CFG = {'lum_night': 12, 'lum_day': 25, 'night_confirm_n': 3,
             'night_margin_s': 2700, 'night_probe_s': 1200, 'period_s': 30}


# ---------- night.py ----------

def test_night_enters_after_confirm_n_dark_wakes():
    st = night.night_new()
    sleep_s, evt = night.night_step(st, 5, 0, NIGHT_CFG)
    assert evt == 'none' and sleep_s == NIGHT_CFG['period_s'] and st['dark_n'] == 1
    sleep_s, evt = night.night_step(st, 5, 30, NIGHT_CFG)
    assert evt == 'none' and st['dark_n'] == 2
    sleep_s, evt = night.night_step(st, 5, 60, NIGHT_CFG)
    assert evt == 'enter' and st['night'] == 1 and st['dark_n'] == 0
    assert sleep_s == NIGHT_CFG['night_probe_s']       # no history -> probe cadence


def test_night_dark_n_resets_on_a_light_wake():
    st = night.night_new()
    night.night_step(st, 5, 0, NIGHT_CFG)
    night.night_step(st, 5, 30, NIGHT_CFG)
    assert st['dark_n'] == 2
    night.night_step(st, 30, 60, NIGHT_CFG)            # a light wake in between
    assert st['dark_n'] == 0


def test_night_probes_at_fixed_cadence_with_no_history():
    st = night.night_new()
    for now in (0, 30, 60):
        night.night_step(st, 5, now, NIGHT_CFG)
    assert st['night'] == 1
    sleep_s, evt = night.night_step(st, 5, 1260, NIGHT_CFG)   # still dark: another probe
    assert evt == 'probe' and sleep_s == NIGHT_CFG['night_probe_s']


def test_night_learned_sleep_is_median_minus_margin_minus_elapsed():
    st = night.night_new()
    st['hist'] = [9800, 10000, 10800]                  # median of last 3 = 10000
    st['night'] = 1
    st['start'] = 5000
    # freshly entered (elapsed 0): predicted - margin - 0 = 10000 - 2700 = 7300
    sleep_s, evt = night.night_step(st, 5, 5000, NIGHT_CFG)
    assert evt == 'probe' and sleep_s == 7300
    # resumed later in the same night (elapsed 5000): 10000 - 2700 - 5000 = 2300
    sleep_s, evt = night.night_step(st, 5, 10000, NIGHT_CFG)
    assert evt == 'probe' and sleep_s == 2300
    # close to the learned dawn: remaining would be negative -> probe cadence floor
    sleep_s, evt = night.night_step(st, 5, 14000, NIGHT_CFG)
    assert evt == 'probe' and sleep_s == NIGHT_CFG['night_probe_s']


def test_night_exit_appends_length_and_keeps_newest_seven():
    st = night.night_new()
    st['night'] = 1
    st['start'] = 1000
    st['hist'] = [100, 200, 300, 400, 500, 600, 700]
    sleep_s, evt = night.night_step(st, 30, 1500, NIGHT_CFG)
    assert evt == 'exit' and st['night'] == 0
    assert st['last_len'] == 500                        # 1500 - 1000
    assert st['hist'] == [200, 300, 400, 500, 600, 700, 500]   # oldest dropped, newest kept
    assert sleep_s == NIGHT_CFG['period_s']


def test_night_predict_median_of_last_three():
    st = night.night_new()
    st['hist'] = [1, 2, 3, 100, 50]
    assert night.night_predict(st) == 50                # median of [3, 100, 50] -> sorted [3,50,100] -> 50


def test_night_save_load_resumes_mid_night(tmp_path):
    path = str(tmp_path / 'night.json')
    st = night.night_new()
    st['night'] = 1
    st['start'] = 4242
    st['hist'] = [111, 222]
    st['dark_n'] = 7                                     # not persisted (transient)
    assert night.night_save(path, st)
    loaded = night.night_load(path)
    assert loaded['night'] == 1 and loaded['start'] == 4242 and loaded['hist'] == [111, 222]
    assert loaded['dark_n'] == 0


def test_night_load_missing_file_gives_fresh_state(tmp_path):
    loaded = night.night_load(str(tmp_path / 'nope.json'))
    assert loaded == night.night_new()


# ---------- rank.py ----------

def test_score_boot_and_heartbeat_always_outrank_everything():
    assert rank.score_for('boot', 0.0, None, 0.0) == 2.0
    assert rank.score_for('heartbeat', 1.0, 0.99, 0.0) == 2.0
    assert rank.score_for('boot', 0, None, 0) > rank.score_for('manual', 0, None, 0)
    assert rank.score_for('manual', 0, None, 0) == 1.5
    assert rank.score_for('manual', 0, None, 0) > rank.score_for('motion', 0.99, 0.99, 0)


def test_score_prefers_confidence_over_diff():
    low_conf = rank.score_for('motion', 0.9, 0.2, 0.0)
    high_diff_no_conf = rank.score_for('motion', 0.9, None, 0.0)
    assert high_diff_no_conf == 0.9
    assert low_conf == 0.2
    assert high_diff_no_conf > low_conf


def test_score_sharpness_is_a_small_tiebreak():
    base = rank.score_for('motion', 0.5, None, 0.0)
    sharper = rank.score_for('motion', 0.5, None, 500000.0)
    assert sharper > base
    assert abs(sharper - (base + 0.5)) < 1e-9


def test_score_never_reaches_manual_from_a_judged_frame():
    val = rank.score_for('motion', 0.99, 0.999999, 5_000_000.0)
    assert val < 1.5


def test_rank_order_score_desc_seq_asc():
    entries = [{'score': 0.2, 'seq': 5}, {'score': 2.0, 'seq': 1}, {'score': 0.2, 'seq': 1}]
    ordered = rank.rank_order(entries)
    assert [(e['score'], e['seq']) for e in ordered] == [(2.0, 1), (0.2, 1), (0.2, 5)]


def test_crop_box_pads_and_centres():
    x, y, side = rank.crop_box(10, 10, 4, 4, 40, 30, 640, 480, pad=0.5, diffuse=0.6, min_side=96)
    assert side >= 96
    assert 0 <= x <= 640 - side and 0 <= y <= 480 - side


def test_crop_box_diffuse_fallback_is_full_frame_centred():
    x, y, side = rank.crop_box(0, 0, 35, 25, 40, 30, 640, 480, pad=0.5, diffuse=0.6, min_side=96)
    assert side == 480 and x == 80 and y == 0


def test_crop_box_no_bbox_is_full_frame_centred():
    x, y, side = rank.crop_box(5, 5, 0, 0, 40, 30, 640, 480)
    assert side == 480 and x == 80 and y == 0


def test_crop_box_clamps_to_the_frame():
    x, y, side = rank.crop_box(0, 0, 2, 2, 40, 30, 200, 150, pad=0.5, diffuse=0.9, min_side=96)
    assert x >= 0 and y >= 0 and x + side <= 200 and y + side <= 150


def test_judge_decide_table():
    cfg = {'gate_pct': 60, 'keep_all': False, 'audit_n': 5}
    assert rank.judge_decide(None, cfg, 1) == (True, 'open')
    assert rank.judge_decide(0.7, cfg, 1) == (True, 'pass')
    assert rank.judge_decide(0.3, dict(cfg, keep_all=True), 1) == (True, 'keep_all')
    assert rank.judge_decide(0.3, cfg, 10) == (True, 'audit')     # 10 % 5 == 0
    assert rank.judge_decide(0.3, cfg, 11) == (False, 'reject')


# ---------- gamespool.py ----------

def _mk_spool(monkeypatch, tmp_path):
    monkeypatch.setattr(gamespool, 'SPOOL_DIR', str(tmp_path / 'spool'))
    monkeypatch.setattr(gamespool, 'DEBUG_DIR', str(tmp_path / 'debug'))
    monkeypatch.setattr(gamespool, 'THUMB_FILE', str(tmp_path / 'spool' / 'thumb.bin'))
    monkeypatch.setattr(gamespool, 'WAKELOG', str(tmp_path / 'wakelog.txt'))
    monkeypatch.setattr(gamespool, 'WAKELOG_ROTATED', str(tmp_path / 'wakelog.1.txt'))
    assert gamespool.gs_ready()


def test_gs_write_scan_and_count(tmp_path, monkeypatch):
    _mk_spool(monkeypatch, tmp_path)
    gamespool.gs_write(1, 1, b'a', json.dumps({'score': 0.2}))
    gamespool.gs_write(1, 2, b'b', json.dumps({'score': 0.9}))
    gamespool.gs_write(2, 1, b'c', json.dumps({'score': 0.5}))
    assert gamespool.gs_count(gamespool.SPOOL_DIR) == 3
    entries = gamespool.gs_scan(gamespool.SPOOL_DIR)
    assert {e['seq'] for e in entries} == {1, 2}
    scores = sorted(e['score'] for e in entries)
    assert scores == [0.2, 0.5, 0.9]


def test_gs_scan_bad_sidecar_scores_minus_one(tmp_path, monkeypatch):
    _mk_spool(monkeypatch, tmp_path)
    gamespool.gs_write(1, 1, b'a', 'not json')
    entries = gamespool.gs_scan(gamespool.SPOOL_DIR)
    assert entries[0]['score'] == -1


def test_gs_drain_uploads_in_rank_order_and_deletes_on_accept(tmp_path, monkeypatch):
    _mk_spool(monkeypatch, tmp_path)
    gamespool.gs_write(1, 1, b'a', json.dumps({'score': 0.2}))
    gamespool.gs_write(1, 2, b'b', json.dumps({'score': 0.9}))
    gamespool.gs_write(2, 1, b'c', json.dumps({'score': 0.5}))
    order = []

    def fake_post_blob(kind, data, meta, length=None):
        order.append(json.loads(meta)['score'])
        return True

    monkeypatch.setattr(gamespool, 'post_blob', fake_post_blob)
    sent, failed = gamespool.gs_drain(gamespool.SPOOL_DIR, 10, lambda: None, 'v1')
    assert (sent, failed) == (3, 0)
    assert order == [0.9, 0.5, 0.2]
    assert gamespool.gs_count(gamespool.SPOOL_DIR) == 0


def test_gs_drain_respects_cap(tmp_path, monkeypatch):
    _mk_spool(monkeypatch, tmp_path)
    for i in range(3):
        gamespool.gs_write(1, i, b'x', json.dumps({'score': float(i)}))
    monkeypatch.setattr(gamespool, 'post_blob', lambda *a, **k: True)
    sent, failed = gamespool.gs_drain(gamespool.SPOOL_DIR, 2, lambda: None, 'v1')
    assert sent == 2 and gamespool.gs_count(gamespool.SPOOL_DIR) == 1


def test_gs_drain_stops_after_five_consecutive_failures(tmp_path, monkeypatch):
    _mk_spool(monkeypatch, tmp_path)
    for i in range(6):
        gamespool.gs_write(1, i, b'x', json.dumps({'score': float(i)}))
    monkeypatch.setattr(gamespool, 'post_blob', lambda *a, **k: False)
    calls = []
    sent, failed = gamespool.gs_drain(gamespool.SPOOL_DIR, 10, lambda: calls.append(1), 'v1')
    assert (sent, failed) == (0, 5)
    assert gamespool.gs_count(gamespool.SPOOL_DIR) == 6      # nothing deleted on failure
    assert len(calls) == 5                                   # idle() called once per attempt


def test_gs_reclaim_deletes_oldest_boot_then_seq(tmp_path, monkeypatch):
    _mk_spool(monkeypatch, tmp_path)
    for i in (1, 2, 3):
        gamespool.gs_write(1, i, b'x', json.dumps({'score': 0.1}))
    for i in (1, 2):
        gamespool.gs_write(2, i, b'x', json.dumps({'score': 0.1}))
    removed = gamespool.gs_reclaim(3)
    assert removed == 2
    assert gamespool.gs_count(gamespool.SPOOL_DIR) == 3
    remaining = sorted(e['base'] for e in gamespool.gs_scan(gamespool.SPOOL_DIR))
    assert remaining == [gamespool.SPOOL_DIR + '/1/000003',
                          gamespool.SPOOL_DIR + '/2/000001',
                          gamespool.SPOOL_DIR + '/2/000002']


def test_gs_reclaim_removes_emptied_boot_dir(tmp_path, monkeypatch):
    import os
    _mk_spool(monkeypatch, tmp_path)
    gamespool.gs_write(1, 1, b'x', json.dumps({'score': 0.1}))
    gamespool.gs_write(2, 1, b'x', json.dumps({'score': 0.1}))
    gamespool.gs_reclaim(1)
    assert not os.path.isdir(gamespool.SPOOL_DIR + '/1')
    assert os.path.isdir(gamespool.SPOOL_DIR + '/2')


def test_gs_thumb_round_trip(tmp_path, monkeypatch):
    _mk_spool(monkeypatch, tmp_path)
    assert gamespool.gs_thumb_load() is None
    gamespool.gs_thumb_save(b'\x01\x02\x03')
    assert gamespool.gs_thumb_load() == b'\x01\x02\x03'


def test_gs_log_rotates_past_max_size(tmp_path, monkeypatch):
    _mk_spool(monkeypatch, tmp_path)
    monkeypatch.setattr(gamespool, 'WAKELOG_MAX', 10)
    gamespool.gs_log('a' * 20)
    gamespool.gs_log('second line')
    with open(gamespool.WAKELOG_ROTATED) as f:
        assert f.read().strip() == 'a' * 20
    with open(gamespool.WAKELOG) as f:
        assert f.read().strip() == 'second line'


# ---------- persist.py ----------

def test_persist_round_trip_via_file_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(persist, 'PERSIST_FILE', str(tmp_path / 'persist.json'))
    d = persist.persist_load()
    assert d == dict((k, 0) for k in persist.PERSIST_FIELDS)
    d['wake_n'] = 42
    d['flags'] = 3
    assert persist.persist_save(d)
    loaded = persist.persist_load()
    assert loaded['wake_n'] == 42 and loaded['flags'] == 3
    for k in persist.PERSIST_FIELDS:
        assert k in loaded


def test_persist_bad_magic_gives_defaults(tmp_path, monkeypatch):
    path = tmp_path / 'persist.json'
    path.write_text(json.dumps({'_magic': 1, 'wake_n': 99}))
    monkeypatch.setattr(persist, 'PERSIST_FILE', str(path))
    d = persist.persist_load()
    assert d['wake_n'] == 0


# ---------- contact.py: parse_http_date ----------

def test_parse_http_date_rfc1123():
    assert contact.parse_http_date('Sun, 06 Nov 1994 08:49:37 GMT') == 784111777


def test_parse_http_date_bad_input():
    assert contact.parse_http_date('not a date') is None
    assert contact.parse_http_date('') is None


# ---------- contact.py: two networks, chosen by a pre-join scan ----------

def test_contact_scan_decodes_ssids_and_fails_open_to_empty():
    class _Wlan:
        def scan(self):
            return [(b'homenet', b'', 1, -50, 3, 0), (b'other', b'', 6, -70, 3, 0)]
    assert contact.contact_scan(_Wlan()) == {'homenet', 'other'}

    class _Bad:
        def scan(self):
            raise OSError('radio busy')
    assert contact.contact_scan(_Bad()) == set()


def test_contact_scan_lan_true_only_when_lan_ssid_configured_and_seen(monkeypatch):
    class _Wlan:
        def scan(self):
            return [(b'homenet', b'', 1, -50, 3, 0)]
    monkeypatch.setattr(secrets, 'LAN_SSID', 'homenet', raising=False)
    assert contact.contact_scan_lan(_Wlan()) is True
    monkeypatch.setattr(secrets, 'LAN_SSID', 'someoneelse', raising=False)
    assert contact.contact_scan_lan(_Wlan()) is False
    monkeypatch.delattr(secrets, 'LAN_SSID', raising=False)
    assert contact.contact_scan_lan(_Wlan()) is False


def test_contact_picks_lan_when_visible(monkeypatch):
    monkeypatch.setattr(secrets, 'LAN_SSID', 'homenet', raising=False)
    monkeypatch.setattr(secrets, 'LAN_PASS', 'lanpass', raising=False)
    monkeypatch.setattr(secrets, 'LAN_HOST', '192.168.1.50', raising=False)
    monkeypatch.setattr(secrets, 'LAN_PORT', 8089, raising=False)
    monkeypatch.setattr(secrets, 'LAN_TLS', False, raising=False)
    monkeypatch.setattr(network.WLAN, 'scan_results', [(b'homenet', b'', 1, -50, 3, 0)])
    calls = []
    monkeypatch.setattr(contact, 'set_server', lambda *a: calls.append(a))
    logs = []
    ok = contact.contact_run({}, {}, lambda *a, **k: None, logs.append)
    assert ok is False        # the stub WLAN has no connect() -- join fails, as in every other contact test
    assert calls[0] == ('192.168.1.50', 8089, False)
    assert any('network homenet (lan), scan saw 1' in l for l in logs)


def test_contact_picks_hotspot_when_lan_not_visible(monkeypatch):
    monkeypatch.setattr(secrets, 'LAN_SSID', 'homenet', raising=False)
    monkeypatch.setattr(network.WLAN, 'scan_results', [])   # LAN configured but not in range
    calls = []
    monkeypatch.setattr(contact, 'set_server', lambda *a: calls.append(a))
    logs = []
    ok = contact.contact_run({}, {}, lambda *a, **k: None, logs.append)
    assert ok is False
    assert calls[0] == (None,)
    assert any('network %s (hotspot), scan saw 0' % secrets.WIFI_SSID in l for l in logs)


# ---------- wakecycle.py: game_meta / game_telemetry ----------

def test_game_meta_has_every_standard_key_plus_the_game_lowpower_extras(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'CFG_FILE', str(tmp_path / 'c.json'))
    config.cfg_init({'period_s': 30})
    m = json.loads(wakecycle.game_meta(1700000000, 3, 1280, 800, 'motion', 0.03, 0.02,
                                        False, False, 0.75, 'set', 40, [{'label': 'animal', 'conf': 0.75}]))
    assert STANDARD_META.issubset(set(m))
    assert m['score'] == 0.75 and m['clock'] == 'set' and m['lum'] == 40
    assert m['det'] == [{'label': 'animal', 'conf': 0.75}]
    assert 'night_s' not in m


def test_game_meta_carries_night_s_on_the_morning_frame(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'CFG_FILE', str(tmp_path / 'c.json'))
    config.cfg_init({'period_s': 30})
    m = json.loads(wakecycle.game_meta(1700000000, 1, 640, 400, 'boot', 1.0, 0.02,
                                        False, False, 2.0, 'set', 20, [], night_s=25200))
    assert m['night_s'] == 25200


def test_game_telemetry_has_standard_plus_offgrid_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'CFG_FILE', str(tmp_path / 'c.json'))
    config.cfg_init({'period_s': 30})
    st = {'sent': 3, 'skipped': 1, 'failed': 0, 'pending_n': 2, 'wake_n': 7, 'night': 1, 'contact_n': 4}
    vals = wakecycle.game_telemetry(st, 0, lum=33, clock_skew_s=5)
    expected = {'uptime_s', 'mem_free', 'frames_sent', 'frames_skipped', 'upload_failures',
                'pending_files', 'mode', 'cfg', 'boot_count', 'night', 'pending_cold',
                'contact_n', 'clock_skew_s', 'lum'}
    assert expected.issubset(set(vals))
    assert vals['night'] == 1 and vals['contact_n'] == 4 and vals['clock_skew_s'] == 5 and vals['lum'] == 33


# ---------- config.py: list coercion ----------

def test_coerce_list_default_to_list_of_str():
    assert config._coerce(['animal', 'person'], ['bird', 'deer']) == ['bird', 'deer']


def test_cfg_apply_coerces_list_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'CFG_FILE', str(tmp_path / 'none.json'))
    defaults = {'keep_labels': ['animal', 'person'], 'gate_pct': 60}
    config.cfg_init(defaults)
    changed = config.cfg_apply({'keep_labels': ['animal']}, defaults)
    assert changed == ['keep_labels']
    assert config.CFG['keep_labels'] == ['animal']


# ---------- control.py: contact mode + /live hook ----------

def test_mode_num_has_contact():
    assert control.MODE_NUM['contact'] == 3


def test_dispatch_live_increments_live_req():
    control.STATE['live_req'] = 0

    class _Conn:
        def write(self, b):
            pass

        def close(self):
            pass

    req = (_Conn(), 'GET', '/live', {}, {})
    control._dispatch(req, False)
    assert control.STATE['live_req'] == 1


# ---------- judge.py: fails open with no ml module ----------

def test_gate_init_fails_open_without_ml_module():
    assert judge.gate_init() is None
    assert judge.gate_score(None, 0, 0, 96) is None


# ---------- led.py ----------

def test_led_pattern_never_raises_without_a_real_led():
    for name in ('updated', 'fail', 'capture', 'off', 'solid'):
        led.led_pattern(name)


def test_led_blinker_tick_and_stop_never_raise():
    b = led.LedBlinker(1000, 100, double=True)
    for _ in range(5):
        b.tick()
    b.stop()


def test_gate_init_retries_the_first_load_failure(tmp_path, monkeypatch):
    import sys, types
    import judge
    calls = []

    class Model:
        input_shape = ((1, 96, 96, 3),)

        def __init__(self, path, **k):
            calls.append(path)
            if len(calls) == 1:
                raise RuntimeError('Failed to load network')

    monkeypatch.setattr(judge, 'ml', types.SimpleNamespace(Model=Model))
    monkeypatch.setattr(judge, 'MODEL_PENDING', str(tmp_path / 'p.txt'))
    monkeypatch.setattr(judge, 'MODEL_BAD', str(tmp_path / 'b.txt'))
    model = tmp_path / 'gate.tflite'
    model.write_bytes(b'x' * 10)
    monkeypatch.setitem(judge.__dict__, 'GATE_MODEL', str(model))
    assert judge.gate_init() is not None
    assert len(calls) == 2 and not (tmp_path / 'b.txt').exists() and not (tmp_path / 'p.txt').exists()
    calls.clear()

    class Bad:
        def __init__(self, path, **k):
            calls.append(path)
            raise RuntimeError('nope')

    monkeypatch.setattr(judge, 'ml', types.SimpleNamespace(Model=Bad))
    assert judge.gate_init() is None
    assert (tmp_path / 'b.txt').read_text() == '10'


def test_gate_score_parses_a_nested_float_array(tmp_path, monkeypatch):
    import types
    import judge

    class Arr:                      # ulab-like: tolist() only, no __len__
        def __init__(self, v):
            self.v = v

        def tolist(self):
            return self.v

    class Model:
        input_shape = ((1, 96, 96, 3),)
        labels = None

        def predict(self, imgs):
            return [Arr([[0.35, 0.65]])]

    class Img:
        def copy(self, **k):
            return self

    monkeypatch.setattr(judge, '_model', Model())
    assert abs(judge.gate_score(Img(), 0, 0, 96) - 0.65) < 1e-6


def test_gs_drain_stamps_the_contact_ip_into_the_meta(tmp_path, monkeypatch):
    import json as _json
    import gamespool
    root = tmp_path / 'spool'
    monkeypatch.setattr(gamespool, 'SPOOL_DIR', str(root))
    (root / '1').mkdir(parents=True)
    (root / '1' / '000001.json').write_text(_json.dumps({'ip': '0.0.0.0', 'why': 'motion', 'score': 0.5, 'seq': 1}))
    (root / '1' / '000001.jpg').write_bytes(b'x' * 100)
    seen = []
    monkeypatch.setattr(gamespool, 'post_blob', lambda kind, fp, meta, n: seen.append(_json.loads(meta)) or True)
    sent, failed = gamespool.gs_drain(str(root), 10, lambda: None, 'v', ip='10.1.2.3')
    assert sent == 1 and seen[0]['ip'] == '10.1.2.3' and seen[0]['why'] == 'motion'
