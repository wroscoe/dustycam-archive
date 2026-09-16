package com.dustycam.phone.ble;

import java.io.ByteArrayOutputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.CRC32;

/**
 * dustycam GATT protocol v1 framing (docs/phone_app_plan.md §2).
 *
 * <p>Header, 4 bytes, present on {@code cmd} writes and every notify frame
 * ({@code rsp}/{@code data}/{@code evt}):
 * <pre>  [id u8][flags u8][idx u16 LE]</pre>
 * flags: {@code 0x01 LAST}, {@code 0x02 BIN}, {@code 0x04 ERR}. Per-fragment
 * payload is at most {@code mtu - 3 (ATT header) - 4 (this header)} bytes.
 *
 * <p>Binary ({@code BIN}) transfers: the first fragment's payload begins with
 * {@code [total u32 LE][crc32 u32 LE]}, followed by raw bytes. {@code total}
 * and the CRC-32 (java.util.zip.CRC32 — the same ISO-3309/zlib polynomial the
 * firmware side uses) are verified against the reassembled bytes once
 * {@code LAST} arrives.
 *
 * <p>Pure Java, no Android imports — host-testable with a plain {@code java}
 * run (see {@code tests/FramerTest.java}) and mirrors the firmware's
 * {@code ble_frame.c} exactly, since both sides were built to this same spec.
 */
public final class Framer {

    public static final int HEADER_LEN = 4;
    public static final int ATT_OVERHEAD = 3;

    public static final int FLAG_LAST = 0x01;
    public static final int FLAG_BIN  = 0x02;
    public static final int FLAG_ERR  = 0x04;

    /** Request limit (app -> camera on {@code cmd}). */
    public static final int REQ_MAX = 4 * 1024;
    /** Response (JSON, non-binary) limit. */
    public static final int RSP_MAX = 8 * 1024;
    /** Binary data limit. */
    public static final int DATA_MAX = 512 * 1024;

    private Framer() {}

    /**
     * Split {@code payload} into wire fragments carrying {@code id}. {@code
     * baseFlags} supplies BIN/ERR (any LAST bit in it is ignored — LAST is set
     * automatically, on the last fragment only). Always emits at least one
     * fragment, even for an empty payload.
     */
    public static List<byte[]> fragment(int id, int baseFlags, byte[] payload, int mtu) {
        if (payload == null) payload = new byte[0];
        int chunk = mtu - ATT_OVERHEAD - HEADER_LEN;
        if (chunk <= 0) throw new IllegalArgumentException("mtu too small: " + mtu);
        int flagsNoLast = baseFlags & ~FLAG_LAST;

        List<byte[]> out = new ArrayList<>();
        int off = 0;
        int idx = 0;
        do {
            int n = Math.min(chunk, payload.length - off);
            boolean last = (off + n) >= payload.length;
            byte[] frame = new byte[HEADER_LEN + n];
            frame[0] = (byte) id;
            frame[1] = (byte) (flagsNoLast | (last ? FLAG_LAST : 0));
            frame[2] = (byte) (idx & 0xFF);
            frame[3] = (byte) ((idx >> 8) & 0xFF);
            System.arraycopy(payload, off, frame, HEADER_LEN, n);
            out.add(frame);
            off += n;
            idx++;
        } while (off < payload.length);
        return out;
    }

    /** Build the [total u32 LE][crc32 u32 LE] + raw bytes blob that becomes a BIN transfer's payload. */
    public static byte[] binPayload(byte[] data) {
        CRC32 crc = new CRC32();
        crc.update(data);
        long crcVal = crc.getValue();
        long total = data.length;
        byte[] out = new byte[8 + data.length];
        putU32le(out, 0, total);
        putU32le(out, 4, crcVal);
        System.arraycopy(data, 0, out, 8, data.length);
        return out;
    }

    private static void putU32le(byte[] b, int off, long v) {
        b[off] = (byte) (v & 0xFF);
        b[off + 1] = (byte) ((v >> 8) & 0xFF);
        b[off + 2] = (byte) ((v >> 16) & 0xFF);
        b[off + 3] = (byte) ((v >> 24) & 0xFF);
    }

    private static long u32le(byte[] b, int off) {
        return (b[off] & 0xFFL) | ((b[off + 1] & 0xFFL) << 8)
                | ((b[off + 2] & 0xFFL) << 16) | ((b[off + 3] & 0xFFL) << 24);
    }

    /** One parsed wire fragment: header fields + payload slice (header stripped). */
    public static final class Frame {
        public final int id;
        public final int flags;
        public final int idx;
        public final byte[] payload;

        Frame(int id, int flags, int idx, byte[] payload) {
            this.id = id;
            this.flags = flags;
            this.idx = idx;
            this.payload = payload;
        }

        public boolean isLast() { return (flags & FLAG_LAST) != 0; }
        public boolean isBin()  { return (flags & FLAG_BIN) != 0; }
        public boolean isErr()  { return (flags & FLAG_ERR) != 0; }
    }

    public static Frame parse(byte[] wire) {
        if (wire == null || wire.length < HEADER_LEN) {
            throw new IllegalArgumentException("frame shorter than the 4-byte header");
        }
        int id = wire[0] & 0xFF;
        int flags = wire[1] & 0xFF;
        int idx = (wire[2] & 0xFF) | ((wire[3] & 0xFF) << 8);
        byte[] payload = new byte[wire.length - HEADER_LEN];
        System.arraycopy(wire, HEADER_LEN, payload, 0, payload.length);
        return new Frame(id, flags, idx, payload);
    }

    /** Any framing violation: out-of-order idx, a size limit exceeded, or a binary total/crc mismatch. */
    public static class FramingException extends Exception {
        public FramingException(String msg) { super(msg); }
    }

    /** A fully reassembled message. */
    public static final class Message {
        public final int id;
        public final boolean bin;
        public final boolean err;
        public final byte[] data;

        Message(int id, boolean bin, boolean err, byte[] data) {
            this.id = id;
            this.bin = bin;
            this.err = err;
            this.data = data;
        }
    }

    /**
     * Reassembles fragmented frames, keyed by id, for one notify characteristic
     * ({@code rsp}, {@code data}, or {@code evt}). Only one transfer per id is
     * ever outstanding in this protocol (DustyLink recycles ids 1..255; 0 is
     * events, which never overlap each other either), so a single
     * fragment-index counter per id is enough to detect out-of-order delivery.
     */
    public static final class Reassembler {

        private static final class InFlight {
            int nextIdx = 0;
            int flags;
            final ByteArrayOutputStream buf = new ByteArrayOutputStream();
            boolean binHeaderParsed = false;
            long expectedTotal = -1;
            long expectedCrc = -1;
        }

        private final Map<Integer, InFlight> inFlight = new HashMap<>();

        /**
         * Feed one raw notify payload (header + fragment bytes). Returns the
         * completed {@link Message} once {@code LAST} arrives, or {@code null}
         * while more fragments are still expected.
         */
        public Message accept(byte[] wire) throws FramingException {
            Frame f = parse(wire);
            InFlight st;

            if (f.idx == 0) {
                // idx 0 always (re)starts a transfer for this id.
                st = new InFlight();
                st.flags = f.flags;
                inFlight.put(f.id, st);
            } else {
                st = inFlight.get(f.id);
                if (st == null || f.idx != st.nextIdx) {
                    inFlight.remove(f.id);
                    throw new FramingException("out-of-order fragment: id=" + f.id
                            + " idx=" + f.idx + " expected=" + (st == null ? 0 : st.nextIdx));
                }
            }
            st.nextIdx = f.idx + 1;

            boolean bin = (st.flags & FLAG_BIN) != 0;
            byte[] payload = f.payload;

            if (bin) {
                int p = 0;
                if (!st.binHeaderParsed) {
                    if (f.idx != 0) {
                        inFlight.remove(f.id);
                        throw new FramingException("binary header missing on first fragment");
                    }
                    if (payload.length < 8) {
                        inFlight.remove(f.id);
                        throw new FramingException("binary header truncated");
                    }
                    st.expectedTotal = u32le(payload, 0);
                    st.expectedCrc = u32le(payload, 4);
                    st.binHeaderParsed = true;
                    p = 8;
                    if (st.expectedTotal > DATA_MAX) {
                        inFlight.remove(f.id);
                        throw new FramingException("data too large: " + st.expectedTotal);
                    }
                }
                st.buf.write(payload, p, payload.length - p);
                if (st.buf.size() > DATA_MAX) {
                    inFlight.remove(f.id);
                    throw new FramingException("data exceeds " + DATA_MAX + "-byte limit: " + st.buf.size());
                }
            } else {
                st.buf.write(payload, 0, payload.length);
                if (st.buf.size() > RSP_MAX) {
                    inFlight.remove(f.id);
                    throw new FramingException("response exceeds " + RSP_MAX + "-byte limit: " + st.buf.size());
                }
            }

            if (!f.isLast()) return null;

            inFlight.remove(f.id);
            byte[] data = st.buf.toByteArray();

            if (bin) {
                if (st.expectedTotal != data.length) {
                    inFlight.remove(f.id);
                    throw new FramingException("size mismatch: total=" + st.expectedTotal + " got=" + data.length);
                }
                CRC32 crc = new CRC32();
                crc.update(data);
                long got = crc.getValue();
                if (got != st.expectedCrc) {
                    throw new FramingException("crc mismatch: expected=0x"
                            + Long.toHexString(st.expectedCrc) + " got=0x" + Long.toHexString(got));
                }
            }

            return new Message(f.id, bin, (st.flags & FLAG_ERR) != 0, data);
        }

        /** True while a transfer for this id has been started but not completed. */
        public boolean isPending(int id) { return inFlight.containsKey(id); }
    }
}
