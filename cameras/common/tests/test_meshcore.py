"""Host tests for meshcore.py (MeshCore group-text packet encode/decode).
Uses the shared boardstubs (no board, no radio) plus the `cryptography`
package as an independent reference for the AES-128-ECB implementation:

    cd /home/wroscoe/code/dustycam && uv run --offline --no-project \
        --with pytest --with cryptography python -m pytest \
        cameras/common/tests/test_meshcore.py -q
"""
import hmac
import os
import random

import pytest
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

import meshcore

FIPS_KEY = bytes.fromhex('000102030405060708090a0b0c0d0e0f')
FIPS_PLAIN = bytes.fromhex('00112233445566778899aabbccddeeff')
FIPS_CIPHER = bytes.fromhex('69c4e0d86a7b0430d8cdb78070b4c55a')


def _ref_aes_ecb_encrypt(key, data):
    enc = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
    return enc.update(data) + enc.finalize()


def _ref_aes_ecb_decrypt(key, data):
    dec = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
    return dec.update(data) + dec.finalize()


# ---------- (1) pure-Python AES-128 vs `cryptography` + FIPS-197 vector ----------

def test_aes_matches_fips197_vector():
    assert meshcore._aes128_ecb_encrypt_py(FIPS_KEY, FIPS_PLAIN) == FIPS_CIPHER
    assert meshcore._aes128_ecb_decrypt_py(FIPS_KEY, FIPS_CIPHER) == FIPS_PLAIN


def test_aes_matches_cryptography_on_random_blocks():
    rng = random.Random(1234)
    for _ in range(8):
        key = bytes(rng.randrange(256) for _ in range(16))
        data = bytes(rng.randrange(256) for _ in range(16 * rng.randint(1, 4)))
        assert meshcore._aes128_ecb_encrypt_py(key, data) == _ref_aes_ecb_encrypt(key, data)
        ct = _ref_aes_ecb_encrypt(key, data)
        assert meshcore._aes128_ecb_decrypt_py(key, ct) == _ref_aes_ecb_decrypt(key, ct)


# ---------- (2) hand-rolled HMAC-SHA256 vs Python's hmac ----------

def test_hmac_sha256_matches_stdlib_hmac():
    rng = random.Random(99)
    for _ in range(5):
        key = os.urandom(rng.choice((10, 32, 64, 100)))
        msg = os.urandom(rng.randrange(0, 200))
        assert meshcore._hmac_sha256(key, msg) == hmac.new(key, msg, 'sha256').digest()


# ---------- (3) Public channel hash + secret ----------

def test_public_channel_hash_and_secret():
    import base64
    import hashlib
    psk = base64.b64decode(meshcore.PUBLIC_CHANNEL_PSK_B64)
    chash, secret = meshcore.mc_channel(meshcore.PUBLIC_CHANNEL_PSK_B64)
    assert len(secret) == 32
    assert secret[:16] == psk
    assert secret[16:] == b'\x00' * 16
    assert chash == hashlib.sha256(psk).digest()[0]


# ---------- (4) round trip ----------

def test_round_trip_public_channel():
    chash, secret = meshcore.mc_channel(meshcore.PUBLIC_CHANNEL_PSK_B64)
    ts = 1_700_000_000
    raw = meshcore.mc_group_text(secret, chash, 'cam1', 'motion detected', ts)

    assert raw[0] == 0x15
    assert raw[1] == 0
    ciphertext = raw[2 + 3:]
    assert len(ciphertext) % 16 == 0
    assert len(raw) <= 2 + 184

    parsed = meshcore.mc_parse(raw, secret, chash)
    assert parsed is not None
    assert parsed['timestamp'] == ts
    assert parsed['flags'] == 0
    assert parsed['sender'] == 'cam1'
    assert parsed['text'] == 'motion detected'
    assert parsed['body'] == 'cam1: motion detected'
    assert parsed['route'] == meshcore.ROUTE_TYPE_FLOOD
    assert parsed['ptype'] == meshcore.PAYLOAD_TYPE_GRP_TXT


# ---------- (5) tampered MAC / wrong channel ----------

def test_tampered_mac_returns_none():
    chash, secret = meshcore.mc_channel(meshcore.PUBLIC_CHANNEL_PSK_B64)
    raw = bytearray(meshcore.mc_group_text(secret, chash, 'cam1', 'hello', 1700000000))
    raw[3] ^= 0xFF   # flip a bit inside the MAC
    assert meshcore.mc_parse(bytes(raw), secret, chash) is None


def test_wrong_channel_returns_none():
    chash, secret = meshcore.mc_channel(meshcore.PUBLIC_CHANNEL_PSK_B64)
    raw = meshcore.mc_group_text(secret, chash, 'cam1', 'hello', 1700000000)
    other_chash, other_secret = meshcore.mc_channel('AAAAAAAAAAAAAAAAAAAAAA==')
    assert meshcore.mc_parse(raw, other_secret, other_chash) is None
    # right secret, but caller checking against a different channel hash
    assert meshcore.mc_parse(raw, secret, (chash + 1) % 256) is None


# ---------- (6) over-long text is truncated, packet stays in budget ----------

def test_overlong_text_is_truncated_and_packet_stays_in_budget():
    chash, secret = meshcore.mc_channel(meshcore.PUBLIC_CHANNEL_PSK_B64)
    raw = meshcore.mc_group_text(secret, chash, 'cam1', 'x' * 5000, 1700000000)
    payload = raw[2:]
    assert len(payload) <= meshcore.MAX_PACKET_PAYLOAD
    parsed = meshcore.mc_parse(raw, secret, chash)
    assert parsed is not None
    assert parsed['text'] == 'x' * (meshcore._MAX_PLAINTEXT - 5 - len('cam1: '))


# ---------- (7) exact-multiple-of-16 plaintext adds no extra block ----------

def test_exact_multiple_plaintext_adds_no_padding_block():
    chash, secret = meshcore.mc_channel(meshcore.PUBLIC_CHANNEL_PSK_B64)
    sender = 'cam1'
    # plaintext = 4 (ts) + 1 (flags) + len(sender)+2 (": ") + len(text)
    prefix_len = len(sender) + 2
    text_len = 32 - 5 - prefix_len
    assert text_len > 0
    text = 'y' * text_len
    raw = meshcore.mc_group_text(secret, chash, sender, text, 1700000000)
    ciphertext = raw[2 + 3:]
    assert len(ciphertext) == 32          # no extra 16-byte block appended
    parsed = meshcore.mc_parse(raw, secret, chash)
    assert parsed['text'] == text
