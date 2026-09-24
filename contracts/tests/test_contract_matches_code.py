"""The contract must describe the code that exists today.

contracts/ was extracted from values that are currently typed by hand in four
places. Until each consumer actually includes the generated constants (phase 4
of docs/REPO_PLAN.md), nothing stops the two drifting apart — so this test
parses the real sources and asserts they still agree with contracts/.

When a consumer is switched over to the generated header, its checks here can
go: the compiler enforces it from then on.

    uv run --offline --no-project --with pytest python -m pytest contracts/tests -q
"""
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'contracts' / 'gen' / 'python'))

import dusty_contract as C  # noqa: E402

BLE_FRAME_H = ROOT / 'runtime/espidf/components/dusty_ble/include/ble_frame.h'
FRAMER_JAVA = ROOT / 'apps/dustyphone/src/com/dustycam/phone/ble/Framer.java'
DUSTYLINK_JAVA = ROOT / 'apps/dustyphone/src/com/dustycam/phone/ble/DustyLink.java'
APP_PY = ROOT / 'runtime/micropython/app.py'
META_TESTS = [
    ROOT / 'cameras/rt1062cam/tests/test_rt1062_app.py',
    ROOT / 'cameras/n6cam/tests/test_n6_app.py',
    ROOT / 'runtime/tests/test_game.py',
]


def defines(path):
    """#define NAME VALUE -> {NAME: int}, for the numeric ones."""
    out = {}
    for m in re.finditer(r'^#define\s+(\w+)\s+(.+)$', path.read_text(), re.M):
        name, raw = m.group(1), m.group(2).strip()
        raw = re.sub(r'/\*.*?\*/', '', raw).strip().rstrip('u')
        # (4u * 1024u) style
        expr = raw.strip('()').replace('u', '')
        if re.fullmatch(r'[\d\sxXa-fA-F*+]+', expr):
            try:
                out[name] = eval(expr)  # noqa: S307 - our own header, digits only
            except Exception:
                pass
    return out


def java_ints(path):
    out = {}
    for m in re.finditer(r'static final int (\w+)\s*=\s*([^;]+);', path.read_text()):
        expr = m.group(2).strip()
        if re.fullmatch(r'[\d\sxXa-fA-F*+]+', expr):
            out[m.group(1)] = eval(expr)  # noqa: S307
    return out


# ---------- C: runtime/espidf/components/dusty_ble ----------

def test_c_ble_frame_matches_contract():
    d = defines(BLE_FRAME_H)
    assert d['BLE_FRAME_HDR_LEN'] == C.BLE_HEADER_LEN
    assert d['BLE_FRAME_FLAG_LAST'] == C.BLE_FLAG_LAST
    assert d['BLE_FRAME_FLAG_BIN'] == C.BLE_FLAG_BIN
    assert d['BLE_FRAME_FLAG_ERR'] == C.BLE_FLAG_ERR
    assert d['BLE_FRAME_LIMIT_REQUEST'] == C.BLE_LIMIT_REQUEST
    assert d['BLE_FRAME_LIMIT_RESPONSE'] == C.BLE_LIMIT_RESPONSE
    assert d['BLE_FRAME_LIMIT_DATA'] == C.BLE_LIMIT_DATA
    assert d['BLE_FRAME_BIN_PREFIX_LEN'] == C.BLE_BIN_PREFIX_LEN


# ---------- Java: apps/dustyphone ----------

def test_java_framer_matches_contract():
    j = java_ints(FRAMER_JAVA)
    assert j['HEADER_LEN'] == C.BLE_HEADER_LEN
    assert j['ATT_OVERHEAD'] == C.BLE_ATT_OVERHEAD
    assert j['FLAG_LAST'] == C.BLE_FLAG_LAST
    assert j['FLAG_BIN'] == C.BLE_FLAG_BIN
    assert j['FLAG_ERR'] == C.BLE_FLAG_ERR
    assert j['REQ_MAX'] == C.BLE_LIMIT_REQUEST
    assert j['RSP_MAX'] == C.BLE_LIMIT_RESPONSE
    assert j['DATA_MAX'] == C.BLE_LIMIT_DATA


def test_java_and_c_agree_with_each_other():
    """The duplication this contract exists to remove: the same eight numbers
    are typed in ble_frame.h and Framer.java."""
    c, j = defines(BLE_FRAME_H), java_ints(FRAMER_JAVA)
    assert c['BLE_FRAME_HDR_LEN'] == j['HEADER_LEN']
    assert c['BLE_FRAME_LIMIT_REQUEST'] == j['REQ_MAX']
    assert c['BLE_FRAME_LIMIT_RESPONSE'] == j['RSP_MAX']
    assert c['BLE_FRAME_LIMIT_DATA'] == j['DATA_MAX']


def test_uuid_base_matches_contract():
    src = DUSTYLINK_JAVA.read_text()
    m = re.search(r'BASE_FMT\s*=\s*"([^"]+)"', src)
    assert m, 'BASE_FMT not found in DustyLink.java'
    assert m.group(1) == C.BLE_UUID_BASE_FMT

    chars = dict(re.findall(r'(\w+)_UUID\s*=\s*uuid\(0x([0-9a-fA-F]+)\)', src))
    for name, xx in chars.items():
        key = 'service' if name == 'SVC' else name.lower()
        if key in C.BLE_CHARS:
            assert C.BLE_CHARS[key] == int(xx, 16), name


# ---------- MicroPython: the meta keys ----------

def test_standard_meta_sets_match_contract():
    """STANDARD_META is copy-pasted into three test files."""
    for p in META_TESTS:
        m = re.search(r'STANDARD_META = \{([^}]+)\}', p.read_text())
        assert m, p
        keys = set(re.findall(r"'(\w+)'", m.group(1)))
        assert keys == set(C.META_KEYS), p


def test_build_meta_emits_the_contract_keys_in_order():
    """app.py hand-formats the meta JSON with a % string, so the key ORDER is
    part of the wire format."""
    src = APP_PY.read_text()
    # from `return (` so the docstring (which contains an escaped apostrophe)
    # cannot derail the string-literal scan, up to the `% (` that ends the
    # format and begins its arguments.
    body = src.split('def build_meta(', 1)[1].split('return (', 1)[1]
    fmt = ''.join(re.findall(r"'([^']*)'", body.split('% (', 1)[0]))
    assert re.findall(r'"(\w+)":', fmt) == list(C.META_ORDER)


# ---------- the mesh grammar parses its own examples ----------

def test_mesh_patterns_match_their_examples():
    mesh = tomllib.loads((ROOT / 'contracts/mesh/lines.toml').read_text())
    for name, u in mesh['uplink'].items():
        assert re.match(u['pattern'], u['example']), name
