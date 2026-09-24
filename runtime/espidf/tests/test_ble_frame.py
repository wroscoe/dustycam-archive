"""Host tests for ble_frame (the portable half of dusty_ble): builds
libble_frame.so via the host Makefile and drives it through ctypes.
stdlib unittest only, same pattern as test_core.py.

Run from the repo root:
    python3 -m unittest cameras.common.espidf.tests.test_ble_frame -v
or:
    python3 -m unittest discover -s runtime/espidf/tests -v
"""
import ctypes
import os
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
COMPONENT_DIR = os.path.normpath(os.path.join(HERE, "..", "components", "dusty_ble"))
HOST_DIR = os.path.join(COMPONENT_DIR, "host")
SO_PATH = os.path.join(HOST_DIR, "libble_frame.so")

BLE_FRAME_HDR_LEN = 4
FLAG_LAST = 0x01
FLAG_BIN = 0x02
FLAG_ERR = 0x04

LIMIT_REQUEST = 4 * 1024
LIMIT_RESPONSE = 8 * 1024
LIMIT_DATA = 512 * 1024

OK, DONE = 0, 1
ERR_SHORT, ERR_ORDER, ERR_TOOBIG, ERR_ID = -1, -2, -3, -4


class BleFrameHdr(ctypes.Structure):
    _fields_ = [("id", ctypes.c_uint8), ("flags", ctypes.c_uint8), ("idx", ctypes.c_uint16)]


class BleFrameReassembler(ctypes.Structure):
    _fields_ = [
        ("buf", ctypes.POINTER(ctypes.c_uint8)),
        ("cap", ctypes.c_size_t),
        ("len", ctypes.c_size_t),
        ("next_idx", ctypes.c_uint16),
        ("id", ctypes.c_uint8),
        ("flags", ctypes.c_uint8),
        ("active", ctypes.c_uint8),
    ]


SINK_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t, ctypes.c_void_p)


def _load_lib():
    lib = ctypes.CDLL(SO_PATH)

    lib.ble_frame_parse_hdr.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t, ctypes.POINTER(BleFrameHdr)]
    lib.ble_frame_parse_hdr.restype = ctypes.c_int

    lib.ble_frame_write_hdr.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(BleFrameHdr)]
    lib.ble_frame_write_hdr.restype = ctypes.c_size_t

    lib.ble_frame_chunk_size.argtypes = [ctypes.c_size_t]
    lib.ble_frame_chunk_size.restype = ctypes.c_size_t

    lib.ble_frame_fragment_count.argtypes = [ctypes.c_size_t, ctypes.c_size_t]
    lib.ble_frame_fragment_count.restype = ctypes.c_size_t

    lib.ble_frame_send.argtypes = [
        ctypes.c_uint8, ctypes.c_uint8, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t,
        ctypes.c_size_t, SINK_FN, ctypes.c_void_p,
    ]
    lib.ble_frame_send.restype = ctypes.c_int

    lib.ble_frame_reassembler_init.argtypes = [ctypes.POINTER(BleFrameReassembler), ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
    lib.ble_frame_reassembler_init.restype = None

    lib.ble_frame_reassembler_reset.argtypes = [ctypes.POINTER(BleFrameReassembler)]
    lib.ble_frame_reassembler_reset.restype = None

    lib.ble_frame_reassembler_feed.argtypes = [
        ctypes.POINTER(BleFrameReassembler), ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t, ctypes.POINTER(BleFrameHdr),
    ]
    lib.ble_frame_reassembler_feed.restype = ctypes.c_int

    lib.ble_frame_bin_prefix_write.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_uint32, ctypes.c_uint32]
    lib.ble_frame_bin_prefix_write.restype = ctypes.c_size_t

    lib.ble_frame_bin_prefix_read.argtypes = [
        ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
    ]
    lib.ble_frame_bin_prefix_read.restype = ctypes.c_int

    lib.ble_crc32.argtypes = [ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
    lib.ble_crc32.restype = ctypes.c_uint32

    return lib


def to_buf(b):
    return (ctypes.c_uint8 * len(b))(*b)


def cast_u8p(buf):
    return ctypes.cast(buf, ctypes.POINTER(ctypes.c_uint8))


class BleFrameTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        r = subprocess.run(["make", "-C", HOST_DIR, "clean", "all"], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("host build failed:\n%s\n%s" % (r.stdout, r.stderr))
        cls.lib = _load_lib()

    def send(self, id_, flags, payload, mtu):
        """Fragment payload via ble_frame_send, return list of frame bytes."""
        frames = []

        def sink(frame_ptr, frame_len, ctx):
            frames.append(bytes(ctypes.string_at(frame_ptr, frame_len)))
            return 0

        csink = SINK_FN(sink)
        buf = to_buf(payload) if payload else None
        rc = self.lib.ble_frame_send(id_, flags, cast_u8p(buf) if buf is not None else None,
                                      len(payload), mtu, csink, None)
        return rc, frames

    def reassembler(self, cap):
        buf = (ctypes.c_uint8 * cap)()
        r = BleFrameReassembler()
        self.lib.ble_frame_reassembler_init(ctypes.byref(r), cast_u8p(buf), cap)
        return r, buf

    def feed(self, r, frame_bytes):
        fb = to_buf(frame_bytes)
        hdr = BleFrameHdr()
        rc = self.lib.ble_frame_reassembler_feed(ctypes.byref(r), cast_u8p(fb), len(frame_bytes), ctypes.byref(hdr))
        return rc, hdr


class Crc32Tests(BleFrameTestCase):
    def test_standard_vector(self):
        data = to_buf(b"123456789")
        crc = self.lib.ble_crc32(0, cast_u8p(data), 9)
        self.assertEqual(crc, 0xCBF43926)

    def test_empty(self):
        crc = self.lib.ble_crc32(0, None, 0)
        self.assertEqual(crc, 0)

    def test_incremental_matches_oneshot(self):
        payload = bytes(range(256)) * 3
        whole = to_buf(payload)
        one_shot = self.lib.ble_crc32(0, cast_u8p(whole), len(payload))

        mid = len(payload) // 3
        part1 = to_buf(payload[:mid])
        part2 = to_buf(payload[mid:])
        crc = self.lib.ble_crc32(0, cast_u8p(part1), mid)
        crc = self.lib.ble_crc32(crc, cast_u8p(part2), len(payload) - mid)
        self.assertEqual(crc, one_shot)


class LimitsAndSizingTests(BleFrameTestCase):
    def test_limit_constants(self):
        self.assertEqual(LIMIT_REQUEST, 4096)
        self.assertEqual(LIMIT_RESPONSE, 8192)
        self.assertEqual(LIMIT_DATA, 512 * 1024)

    def test_chunk_size(self):
        # payload <= mtu - 3 (ATT) - 4 (our header)
        self.assertEqual(self.lib.ble_frame_chunk_size(517), 517 - 7)
        self.assertEqual(self.lib.ble_frame_chunk_size(23), 23 - 7)
        self.assertEqual(self.lib.ble_frame_chunk_size(7), 0)
        self.assertEqual(self.lib.ble_frame_chunk_size(3), 0)

    def test_fragment_count(self):
        chunk = self.lib.ble_frame_chunk_size(23)  # 16
        self.assertEqual(chunk, 16)
        self.assertEqual(self.lib.ble_frame_fragment_count(0, 23), 1)
        self.assertEqual(self.lib.ble_frame_fragment_count(16, 23), 1)
        self.assertEqual(self.lib.ble_frame_fragment_count(17, 23), 2)
        self.assertEqual(self.lib.ble_frame_fragment_count(32, 23), 2)
        self.assertEqual(self.lib.ble_frame_fragment_count(33, 23), 3)
        self.assertEqual(self.lib.ble_frame_fragment_count(100, 3), 0)  # mtu too small


class HeaderTests(BleFrameTestCase):
    def test_write_then_parse_roundtrip(self):
        hdr = BleFrameHdr(id=42, flags=FLAG_LAST | FLAG_BIN, idx=0x1234)
        buf = (ctypes.c_uint8 * 4)()
        n = self.lib.ble_frame_write_hdr(cast_u8p(buf), ctypes.byref(hdr))
        self.assertEqual(n, 4)
        parsed = BleFrameHdr()
        rc = self.lib.ble_frame_parse_hdr(cast_u8p(buf), 4, ctypes.byref(parsed))
        self.assertEqual(rc, 0)
        self.assertEqual(parsed.id, 42)
        self.assertEqual(parsed.flags, FLAG_LAST | FLAG_BIN)
        self.assertEqual(parsed.idx, 0x1234)

    def test_parse_too_short(self):
        buf = (ctypes.c_uint8 * 2)(0, 0)
        parsed = BleFrameHdr()
        rc = self.lib.ble_frame_parse_hdr(cast_u8p(buf), 2, ctypes.byref(parsed))
        self.assertEqual(rc, -1)


class SendReassembleRoundTripTests(BleFrameTestCase):
    def _roundtrip(self, payload, mtu, base_flags=0, id_=7):
        rc, frames = self.send(id_, base_flags, payload, mtu)
        expected_frags = self.lib.ble_frame_fragment_count(len(payload), mtu)
        self.assertEqual(rc, expected_frags)
        self.assertGreaterEqual(len(frames), 1)

        r, _buf = self.reassembler(LIMIT_DATA)
        result = None
        for i, frame in enumerate(frames):
            result, hdr = self.feed(r, frame)
            self.assertEqual(hdr.id, id_)
            self.assertEqual(hdr.idx, i)
            if i < len(frames) - 1:
                self.assertEqual(result, OK)
            else:
                self.assertEqual(result, DONE)
        self.assertEqual(r.len, len(payload))
        got = bytes(ctypes.cast(r.buf, ctypes.POINTER(ctypes.c_uint8 * r.len)).contents) if r.len else b""
        self.assertEqual(got, payload)
        return frames

    def test_single_fragment_small_json(self):
        self._roundtrip(b'{"op":"hello","pn":"aabbccdd"}', mtu=517)

    def test_multi_fragment_at_small_mtu(self):
        payload = bytes(range(256)) * 2  # 512 bytes
        frames = self._roundtrip(payload, mtu=23)
        self.assertGreater(len(frames), 1)

    def test_empty_payload(self):
        self._roundtrip(b"", mtu=517)

    def test_last_fragment_exact_multiple_of_chunk(self):
        chunk = self.lib.ble_frame_chunk_size(23)
        payload = bytes(range(chunk * 3))  # exact multiple: must not emit a trailing empty fragment
        frames = self._roundtrip(payload, mtu=23)
        self.assertEqual(len(frames), 3)

    def test_binary_transfer_with_crc_prefix(self):
        raw = bytes((i * 7) % 256 for i in range(50000))  # spans many fragments at 517 MTU
        crc = self.lib.ble_crc32(0, cast_u8p(to_buf(raw)), len(raw))
        prefix = (ctypes.c_uint8 * 8)()
        self.lib.ble_frame_bin_prefix_write(cast_u8p(prefix), len(raw), crc)
        payload = bytes(prefix) + raw

        frames = self._roundtrip(payload, mtu=517, base_flags=FLAG_BIN)
        # every fragment carries BIN
        for f in frames:
            hdr = BleFrameHdr()
            self.lib.ble_frame_parse_hdr(cast_u8p(to_buf(f)), len(f), ctypes.byref(hdr))
            self.assertTrue(hdr.flags & FLAG_BIN)

        total_out = ctypes.c_uint32()
        crc_out = ctypes.c_uint32()
        body = to_buf(payload)
        rc = self.lib.ble_frame_bin_prefix_read(cast_u8p(body), len(payload), ctypes.byref(total_out), ctypes.byref(crc_out))
        self.assertEqual(rc, 0)
        self.assertEqual(total_out.value, len(raw))
        self.assertEqual(crc_out.value, crc)
        # and the raw bytes after the prefix crc-check out
        raw_recovered = payload[8:]
        recrc = self.lib.ble_crc32(0, cast_u8p(to_buf(raw_recovered)), len(raw_recovered))
        self.assertEqual(recrc, crc)

    def test_request_limit_fits(self):
        payload = b"x" * LIMIT_REQUEST
        self._roundtrip(payload, mtu=517)

    def test_response_limit_fits(self):
        payload = b"y" * LIMIT_RESPONSE
        self._roundtrip(payload, mtu=517)


class ReassemblerRejectionTests(BleFrameTestCase):
    def frame_bytes(self, id_, flags, idx, chunk):
        hdr = BleFrameHdr(id=id_, flags=flags, idx=idx)
        buf = (ctypes.c_uint8 * 4)()
        self.lib.ble_frame_write_hdr(cast_u8p(buf), ctypes.byref(hdr))
        return bytes(buf) + chunk

    def test_out_of_order_skip_rejected_then_recovers(self):
        r, _buf = self.reassembler(LIMIT_REQUEST)
        f0 = self.frame_bytes(1, 0, 0, b"AAAA")
        f2 = self.frame_bytes(1, FLAG_LAST, 2, b"CCCC")  # skips idx 1
        rc, _ = self.feed(r, f0)
        self.assertEqual(rc, OK)
        rc, _ = self.feed(r, f2)
        self.assertEqual(rc, ERR_ORDER)
        self.assertEqual(r.active, 0)

        # a fresh idx-0 fragment must be accepted after the reset
        f0b = self.frame_bytes(1, FLAG_LAST, 0, b"ZZZZ")
        rc, _ = self.feed(r, f0b)
        self.assertEqual(rc, DONE)
        self.assertEqual(bytes(ctypes.cast(r.buf, ctypes.POINTER(ctypes.c_uint8 * r.len)).contents), b"ZZZZ")

    def test_duplicate_fragment_rejected(self):
        r, _buf = self.reassembler(LIMIT_REQUEST)
        f0 = self.frame_bytes(1, 0, 0, b"AAAA")
        f1 = self.frame_bytes(1, 0, 1, b"BBBB")
        rc, _ = self.feed(r, f0)
        self.assertEqual(rc, OK)
        rc, _ = self.feed(r, f1)
        self.assertEqual(rc, OK)
        # repeat idx 1 (duplicate notify / retried write)
        rc, _ = self.feed(r, f1)
        self.assertEqual(rc, ERR_ORDER)
        self.assertEqual(r.active, 0)

    def test_duplicate_first_fragment_after_completion_starts_fresh(self):
        r, _buf = self.reassembler(LIMIT_REQUEST)
        f0 = self.frame_bytes(1, FLAG_LAST, 0, b"AAAA")
        rc, _ = self.feed(r, f0)
        self.assertEqual(rc, DONE)
        # id 1 idx 0 again: this is a NEW message (previous one completed),
        # so it must be accepted, not rejected as a duplicate.
        rc, _ = self.feed(r, f0)
        self.assertEqual(rc, DONE)

    def test_id_change_mid_message_rejected(self):
        r, _buf = self.reassembler(LIMIT_REQUEST)
        f0 = self.frame_bytes(5, 0, 0, b"AAAA")
        f1_other_id = self.frame_bytes(6, FLAG_LAST, 1, b"BBBB")
        rc, _ = self.feed(r, f0)
        self.assertEqual(rc, OK)
        rc, _ = self.feed(r, f1_other_id)
        self.assertEqual(rc, ERR_ID)
        self.assertEqual(r.active, 0)

    def test_too_big_rejected_and_resets(self):
        cap = 8
        r, _buf = self.reassembler(cap)
        f0 = self.frame_bytes(1, 0, 0, b"AAAAAAAA")  # exactly cap: still OK
        rc, _ = self.feed(r, f0)
        self.assertEqual(rc, OK)
        f1 = self.frame_bytes(1, FLAG_LAST, 1, b"X")  # one more byte overflows cap
        rc, _ = self.feed(r, f1)
        self.assertEqual(rc, ERR_TOOBIG)
        self.assertEqual(r.active, 0)

    def test_short_frame_rejected(self):
        r, _buf = self.reassembler(LIMIT_REQUEST)
        rc, _ = self.feed(r, b"\x00\x00")
        self.assertEqual(rc, ERR_SHORT)


if __name__ == "__main__":
    unittest.main()
