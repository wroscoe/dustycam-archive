"""meshcore: encode (and, for tests, decode) MeshCore "group text" (channel)
packets, pure, dependency-free. On-air format extracted 2026-09-13 from
meshcore-dev/MeshCore `main` (src/Packet.h, src/Mesh.cpp createGroupDatagram,
src/Utils.cpp encrypt/encryptThenMAC, src/Dispatcher.cpp, src/helpers/
BaseChatMesh.cpp sendGroupMessage + channel hashing, examples/companion_radio/
MyMesh.cpp). No radio/board I/O here -- this only builds/parses the raw
packet bytes a LoRa driver would send/receive.

Packet layout (we always send route_type FLOOD, path_len 0, so we never
emit/parse the transport-code or path fields for real -- they're handled
below only so a differently-shaped inbound packet doesn't crash us):
    header (1) + [4 bytes transport codes, ONLY for route_type 0x00/0x03]
    + path_len (1) + path (path_len&63 hashes, each (path_len>>6)+1 bytes)
    + payload
header = (route_type & 0x03) | (payload_type & 0x0F) << 2 | (version & 0x03) << 6.
GRP_TXT payload = channel_hash (1) + MAC (2) + ciphertext.
Plaintext = timestamp uint32 LE (seconds) + flags (1, 0x00 = TXT_TYPE_PLAIN)
+ "<sender>: <text>" UTF-8, no null terminator. Ciphertext = AES-128-ECB over
the plaintext, zero-padded (in place, in the final block only) up to a
16-byte boundary -- an already-block-sized plaintext gets no extra block.
AES key = secret[:16]. MAC = HMAC-SHA256(key=secret (32 bytes), ciphertext)[:2].
Channel secret = 16-byte PSK + 16 zero bytes. channel_hash = sha256(psk)[0].

Crypto: hashlib.sha256 (stdlib on both MicroPython and CPython); HMAC-SHA256
hand-rolled (no `hmac` module on MicroPython); AES-128-ECB via
`cryptolib.aes(key, 1)` when `cryptolib` exists (MicroPython), else a small
pure-Python AES-128 block cipher (also what the CPython tests exercise).
"""
import binascii
import hashlib

try:
    import cryptolib
except ImportError:
    cryptolib = None

ROUTE_TYPE_FLOOD = 0x01
PAYLOAD_TYPE_GRP_TXT = 0x05
TXT_TYPE_PLAIN = 0x00
MAX_PACKET_PAYLOAD = 184

# Reserve 3 bytes for channel_hash+MAC and 15 for worst-case zero-padding of
# the final AES block, so the plaintext we build always yields a ciphertext
# (and packet) inside MAX_PACKET_PAYLOAD.
_MAX_PLAINTEXT = MAX_PACKET_PAYLOAD - 3 - 15

_HEADER_FLOOD_GRP_TXT = ((ROUTE_TYPE_FLOOD & 0x03) | ((PAYLOAD_TYPE_GRP_TXT & 0x0F) << 2)
                         | ((0 & 0x03) << 6))   # version 0 -> 0x15

PUBLIC_CHANNEL_PSK_B64 = 'izOH6cXN6mrJ5e26oRXNcg=='


# ---------- little-endian uint32, by hand (no struct dependency) ----------

def _u32le(v):
    return bytes((v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF))


def _u32le_unpack(b):
    return b[0] | (b[1] << 8) | (b[2] << 16) | (b[3] << 24)


# ---------- HMAC-SHA256, by hand (MicroPython has no hmac module) ----------

def _hmac_sha256(key, msg):
    block_size = 64
    if len(key) > block_size:
        key = hashlib.sha256(key).digest()
    if len(key) < block_size:
        key = key + b'\x00' * (block_size - len(key))
    o_pad = bytes(b ^ 0x5C for b in key)
    i_pad = bytes(b ^ 0x36 for b in key)
    inner = hashlib.sha256(i_pad + msg).digest()
    return hashlib.sha256(o_pad + inner).digest()


# ---------- pure-Python AES-128 (FIPS-197), used when cryptolib is absent ----------

_SBOX = bytes((
    0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
    0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0,
    0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,
    0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75,
    0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84,
    0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,
    0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8,
    0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2,
    0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,
    0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb,
    0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,
    0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,
    0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a,
    0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e,
    0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,
    0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16,
))

_INV_SBOX = bytes((
    0x52, 0x09, 0x6a, 0xd5, 0x30, 0x36, 0xa5, 0x38, 0xbf, 0x40, 0xa3, 0x9e, 0x81, 0xf3, 0xd7, 0xfb,
    0x7c, 0xe3, 0x39, 0x82, 0x9b, 0x2f, 0xff, 0x87, 0x34, 0x8e, 0x43, 0x44, 0xc4, 0xde, 0xe9, 0xcb,
    0x54, 0x7b, 0x94, 0x32, 0xa6, 0xc2, 0x23, 0x3d, 0xee, 0x4c, 0x95, 0x0b, 0x42, 0xfa, 0xc3, 0x4e,
    0x08, 0x2e, 0xa1, 0x66, 0x28, 0xd9, 0x24, 0xb2, 0x76, 0x5b, 0xa2, 0x49, 0x6d, 0x8b, 0xd1, 0x25,
    0x72, 0xf8, 0xf6, 0x64, 0x86, 0x68, 0x98, 0x16, 0xd4, 0xa4, 0x5c, 0xcc, 0x5d, 0x65, 0xb6, 0x92,
    0x6c, 0x70, 0x48, 0x50, 0xfd, 0xed, 0xb9, 0xda, 0x5e, 0x15, 0x46, 0x57, 0xa7, 0x8d, 0x9d, 0x84,
    0x90, 0xd8, 0xab, 0x00, 0x8c, 0xbc, 0xd3, 0x0a, 0xf7, 0xe4, 0x58, 0x05, 0xb8, 0xb3, 0x45, 0x06,
    0xd0, 0x2c, 0x1e, 0x8f, 0xca, 0x3f, 0x0f, 0x02, 0xc1, 0xaf, 0xbd, 0x03, 0x01, 0x13, 0x8a, 0x6b,
    0x3a, 0x91, 0x11, 0x41, 0x4f, 0x67, 0xdc, 0xea, 0x97, 0xf2, 0xcf, 0xce, 0xf0, 0xb4, 0xe6, 0x73,
    0x96, 0xac, 0x74, 0x22, 0xe7, 0xad, 0x35, 0x85, 0xe2, 0xf9, 0x37, 0xe8, 0x1c, 0x75, 0xdf, 0x6e,
    0x47, 0xf1, 0x1a, 0x71, 0x1d, 0x29, 0xc5, 0x89, 0x6f, 0xb7, 0x62, 0x0e, 0xaa, 0x18, 0xbe, 0x1b,
    0xfc, 0x56, 0x3e, 0x4b, 0xc6, 0xd2, 0x79, 0x20, 0x9a, 0xdb, 0xc0, 0xfe, 0x78, 0xcd, 0x5a, 0xf4,
    0x1f, 0xdd, 0xa8, 0x33, 0x88, 0x07, 0xc7, 0x31, 0xb1, 0x12, 0x10, 0x59, 0x27, 0x80, 0xec, 0x5f,
    0x60, 0x51, 0x7f, 0xa9, 0x19, 0xb5, 0x4a, 0x0d, 0x2d, 0xe5, 0x7a, 0x9f, 0x93, 0xc9, 0x9c, 0xef,
    0xa0, 0xe0, 0x3b, 0x4d, 0xae, 0x2a, 0xf5, 0xb0, 0xc8, 0xeb, 0xbb, 0x3c, 0x83, 0x53, 0x99, 0x61,
    0x17, 0x2b, 0x04, 0x7e, 0xba, 0x77, 0xd6, 0x26, 0xe1, 0x69, 0x14, 0x63, 0x55, 0x21, 0x0c, 0x7d,
))

_RCON = (0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36)


def _gmul(a, b):
    """Multiply two bytes in GF(2^8) (AES's field, reducing by 0x11b)."""
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        hi = a & 0x80
        a = (a << 1) & 0xFF
        if hi:
            a ^= 0x1B
        b >>= 1
    return p


def _key_expansion(key):
    """AES-128 key schedule: 44 4-byte words (Nk=4, Nr=10)."""
    nk = 4
    nr = 10
    w = [list(key[4 * i:4 * i + 4]) for i in range(nk)]
    for i in range(nk, 4 * (nr + 1)):
        temp = list(w[i - 1])
        if i % nk == 0:
            temp = temp[1:] + temp[:1]                # RotWord
            temp = [_SBOX[b] for b in temp]            # SubWord
            temp[0] ^= _RCON[i // nk - 1]
        w.append([w[i - nk][j] ^ temp[j] for j in range(4)])
    return w


def _add_round_key(state, w, rnd):
    for c in range(4):
        wc = w[rnd * 4 + c]
        for r in range(4):
            state[r + 4 * c] ^= wc[r]


def _shift_rows(state):
    out = state[:]
    for c in range(4):
        for r in range(4):
            out[r + 4 * c] = state[r + 4 * ((c + r) % 4)]
    state[:] = out


def _inv_shift_rows(state):
    out = state[:]
    for c in range(4):
        for r in range(4):
            out[r + 4 * c] = state[r + 4 * ((c - r) % 4)]
    state[:] = out


def _mix_columns(state):
    for c in range(4):
        i = 4 * c
        s0, s1, s2, s3 = state[i], state[i + 1], state[i + 2], state[i + 3]
        state[i] = _gmul(s0, 2) ^ _gmul(s1, 3) ^ s2 ^ s3
        state[i + 1] = s0 ^ _gmul(s1, 2) ^ _gmul(s2, 3) ^ s3
        state[i + 2] = s0 ^ s1 ^ _gmul(s2, 2) ^ _gmul(s3, 3)
        state[i + 3] = _gmul(s0, 3) ^ s1 ^ s2 ^ _gmul(s3, 2)


def _inv_mix_columns(state):
    for c in range(4):
        i = 4 * c
        s0, s1, s2, s3 = state[i], state[i + 1], state[i + 2], state[i + 3]
        state[i] = _gmul(s0, 14) ^ _gmul(s1, 11) ^ _gmul(s2, 13) ^ _gmul(s3, 9)
        state[i + 1] = _gmul(s0, 9) ^ _gmul(s1, 14) ^ _gmul(s2, 11) ^ _gmul(s3, 13)
        state[i + 2] = _gmul(s0, 13) ^ _gmul(s1, 9) ^ _gmul(s2, 14) ^ _gmul(s3, 11)
        state[i + 3] = _gmul(s0, 11) ^ _gmul(s1, 13) ^ _gmul(s2, 9) ^ _gmul(s3, 14)


def _aes_encrypt_block(inp, w):
    state = list(inp)
    _add_round_key(state, w, 0)
    for rnd in range(1, 10):
        state = [_SBOX[b] for b in state]
        _shift_rows(state)
        _mix_columns(state)
        _add_round_key(state, w, rnd)
    state = [_SBOX[b] for b in state]
    _shift_rows(state)
    _add_round_key(state, w, 10)
    return bytes(state)


def _aes_decrypt_block(inp, w):
    state = list(inp)
    _add_round_key(state, w, 10)
    for rnd in range(9, 0, -1):
        _inv_shift_rows(state)
        state = [_INV_SBOX[b] for b in state]
        _add_round_key(state, w, rnd)
        _inv_mix_columns(state)
    _inv_shift_rows(state)
    state = [_INV_SBOX[b] for b in state]
    _add_round_key(state, w, 0)
    return bytes(state)


def _aes128_ecb_encrypt_py(key, data):
    w = _key_expansion(key)
    out = bytearray()
    for i in range(0, len(data), 16):
        out += _aes_encrypt_block(data[i:i + 16], w)
    return bytes(out)


def _aes128_ecb_decrypt_py(key, data):
    w = _key_expansion(key)
    out = bytearray()
    for i in range(0, len(data), 16):
        out += _aes_decrypt_block(data[i:i + 16], w)
    return bytes(out)


def _aes_ecb_encrypt(key, data):
    if cryptolib is not None:
        return cryptolib.aes(key, 1).encrypt(data)
    return _aes128_ecb_encrypt_py(key, data)


def _aes_ecb_decrypt(key, data):
    if cryptolib is not None:
        return cryptolib.aes(key, 1).decrypt(data)
    return _aes128_ecb_decrypt_py(key, data)


# ---------- channel / packet API ----------

def mc_channel(psk_b64):
    """(hash_byte, secret) for a channel given its base64 16-byte PSK.
    secret is the 32-byte AES key material: PSK + 16 zero bytes."""
    psk = binascii.a2b_base64(psk_b64)
    secret = psk + b'\x00' * 16
    chash = hashlib.sha256(psk).digest()[0]
    return chash, secret


def mc_group_text(secret, chash, sender, text, timestamp):
    """Raw MeshCore packet bytes (header 0x15, path_len 0) for a group/channel
    text message. Truncates `text` (not `sender`) as needed to keep the
    packet within MAX_PACKET_PAYLOAD."""
    prefix = ('%s: ' % sender).encode('utf-8')
    text_bytes = text.encode('utf-8') if not isinstance(text, bytes) else text
    avail = _MAX_PLAINTEXT - 5 - len(prefix)
    if avail < 0:
        avail = 0
    if len(text_bytes) > avail:
        text_bytes = text_bytes[:avail]

    plaintext = _u32le(timestamp) + bytes((TXT_TYPE_PLAIN,)) + prefix + text_bytes
    pad_len = (-len(plaintext)) % 16
    padded = plaintext + b'\x00' * pad_len

    ciphertext = _aes_ecb_encrypt(secret[:16], padded)
    mac = _hmac_sha256(secret, ciphertext)[:2]
    payload = bytes((chash,)) + mac + ciphertext
    return bytes((_HEADER_FLOOD_GRP_TXT, 0)) + payload


def mc_parse(raw, secret, chash):
    """Parse+verify a raw packet against one channel's (chash, secret).
    None if too short, the channel hash doesn't match, or the MAC doesn't
    verify (wrong channel or a tampered packet). Otherwise a dict with
    route, ptype, timestamp, flags, text, sender, body."""
    if len(raw) < 2:
        return None
    header = raw[0]
    route = header & 0x03
    ptype = (header >> 2) & 0x0F
    offset = 1
    if route in (0x00, 0x03):          # transport codes: 2 fields x 2 bytes
        offset += 4
    if offset >= len(raw):
        return None
    path_len = raw[offset]
    offset += 1
    n_entries = path_len & 0x3F
    entry_size = (path_len >> 6) + 1
    offset += n_entries * entry_size

    payload = raw[offset:]
    if len(payload) < 3:
        return None
    if payload[0] != chash:
        return None
    mac = payload[1:3]
    ciphertext = payload[3:]
    if len(ciphertext) == 0 or len(ciphertext) % 16 != 0:
        return None
    if _hmac_sha256(secret, ciphertext)[:2] != mac:
        return None

    padded = _aes_ecb_decrypt(secret[:16], ciphertext)
    n = len(padded)
    while n > 0 and padded[n - 1] == 0:
        n -= 1
    plaintext = padded[:n]
    if len(plaintext) < 5:
        return None

    timestamp = _u32le_unpack(plaintext[0:4])
    flags = plaintext[4]
    body = plaintext[5:].decode('utf-8')
    idx = body.find(': ')
    if idx >= 0:
        sender = body[:idx]
        text = body[idx + 2:]
    else:
        sender = ''
        text = body

    return {'route': route, 'ptype': ptype, 'timestamp': timestamp,
            'flags': flags, 'text': text, 'sender': sender, 'body': body}
