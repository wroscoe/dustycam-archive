package com.dustycam.phone.ble;

import java.util.List;
import java.util.Random;

/**
 * Plain-{@code main} assertions for {@link Framer} — no JUnit, no Android.
 * Compiled and run with the bare JDK: `make test` (see ../Makefile).
 */
public class FramerTest {

    private static int passed = 0;
    private static int failed = 0;

    public static void main(String[] args) throws Exception {
        testJsonRoundTrip(23);
        testJsonRoundTrip(517);
        testBinaryRoundTripMultiFragment();
        testCrcFailureDetected();
        testOutOfOrderRejected();
        testEmptyPayload();
        testSizeLimitEnforced();

        System.out.println();
        System.out.println(passed + " passed, " + failed + " failed");
        if (failed > 0) System.exit(1);
    }

    // ---- JSON (non-binary) round trip at a given MTU ----

    private static void testJsonRoundTrip(int mtu) throws Exception {
        String name = "jsonRoundTrip(mtu=" + mtu + ")";
        String json = "{\"id\":5,\"ok\":true,\"status\":{\"device\":\"xiaocam1\",\"cfg\":7,"
                + "\"note\":\"" + repeat("x", 300) + "\"}}";
        byte[] payload = json.getBytes("UTF-8");
        int id = 5;

        List<byte[]> frames = Framer.fragment(id, 0, payload, mtu);
        int maxFrag = mtu - Framer.ATT_OVERHEAD - Framer.HEADER_LEN;
        for (byte[] fr : frames) {
            check(name + ": fragment <= mtu-7", fr.length - Framer.HEADER_LEN <= maxFrag);
        }

        Framer.Reassembler r = new Framer.Reassembler();
        Framer.Message msg = null;
        for (int i = 0; i < frames.size(); i++) {
            Framer.Message m = r.accept(frames.get(i));
            if (i < frames.size() - 1) {
                check(name + ": not done before LAST", m == null);
            } else {
                msg = m;
            }
        }
        check(name + ": message produced", msg != null);
        check(name + ": id matches", msg.id == id);
        check(name + ": not binary", !msg.bin);
        check(name + ": bytes match", new String(msg.data, "UTF-8").equals(json));
    }

    // ---- Binary transfer spanning several fragments, with a correct CRC ----

    private static void testBinaryRoundTripMultiFragment() throws Exception {
        String name = "binaryRoundTripMultiFragment";
        byte[] jpeg = randomBytes(6000, 42);
        byte[] withHeader = Framer.binPayload(jpeg);
        int id = 9;
        int mtu = 185; // forces several fragments for a 6008-byte payload

        List<byte[]> frames = Framer.fragment(id, Framer.FLAG_BIN, withHeader, mtu);
        check(name + ": multiple fragments", frames.size() > 1);

        Framer.Reassembler r = new Framer.Reassembler();
        Framer.Message msg = null;
        for (byte[] fr : frames) msg = r.accept(fr);

        check(name + ": message produced", msg != null);
        check(name + ": binary flag set", msg.bin);
        check(name + ": length matches", msg.data.length == jpeg.length);
        check(name + ": bytes match", java.util.Arrays.equals(msg.data, jpeg));
    }

    // ---- A corrupted binary transfer must fail the CRC check on LAST ----

    private static void testCrcFailureDetected() throws Exception {
        String name = "crcFailureDetected";
        byte[] jpeg = randomBytes(3000, 7);
        byte[] withHeader = Framer.binPayload(jpeg);
        withHeader[20] ^= 0xFF; // flip a data byte after the 8-byte total/crc header
        int mtu = 100;

        List<byte[]> frames = Framer.fragment(3, Framer.FLAG_BIN, withHeader, mtu);
        Framer.Reassembler r = new Framer.Reassembler();
        boolean threw = false;
        try {
            for (byte[] fr : frames) r.accept(fr);
        } catch (Framer.FramingException e) {
            threw = e.getMessage().contains("crc mismatch");
        }
        check(name + ": crc mismatch raised", threw);
    }

    // ---- A skipped fragment index must be rejected ----

    private static void testOutOfOrderRejected() throws Exception {
        String name = "outOfOrderRejected";
        byte[] payload = randomBytes(500, 1);
        List<byte[]> frames = Framer.fragment(11, 0, payload, 60);
        check(name + ": setup has >= 3 fragments", frames.size() >= 3);

        Framer.Reassembler r = new Framer.Reassembler();
        r.accept(frames.get(0)); // idx 0, fine
        boolean threw = false;
        try {
            r.accept(frames.get(2)); // skip idx 1
        } catch (Framer.FramingException e) {
            threw = e.getMessage().contains("out-of-order");
        }
        check(name + ": rejected", threw);
    }

    // ---- fragment() on an empty payload still yields exactly one (LAST) frame ----

    private static void testEmptyPayload() throws Exception {
        String name = "emptyPayload";
        List<byte[]> frames = Framer.fragment(1, 0, new byte[0], 23);
        check(name + ": exactly one frame", frames.size() == 1);
        Framer.Frame f = Framer.parse(frames.get(0));
        check(name + ": LAST set", f.isLast());
        check(name + ": zero-length payload", f.payload.length == 0);

        Framer.Reassembler r = new Framer.Reassembler();
        Framer.Message msg = r.accept(frames.get(0));
        check(name + ": message produced", msg != null);
        check(name + ": empty data", msg.data.length == 0);
    }

    // ---- A response over the 8 KB rsp limit must be rejected ----

    private static void testSizeLimitEnforced() throws Exception {
        String name = "sizeLimitEnforced";
        byte[] tooBig = randomBytes(Framer.RSP_MAX + 500, 3);
        List<byte[]> frames = Framer.fragment(2, 0, tooBig, 200);
        Framer.Reassembler r = new Framer.Reassembler();
        boolean threw = false;
        try {
            for (byte[] fr : frames) r.accept(fr);
        } catch (Framer.FramingException e) {
            threw = e.getMessage().contains("exceeds");
        }
        check(name + ": limit enforced", threw);
    }

    // ---- helpers ----

    private static byte[] randomBytes(int n, long seed) {
        byte[] b = new byte[n];
        new Random(seed).nextBytes(b);
        return b;
    }

    private static String repeat(String s, int n) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < n; i++) sb.append(s);
        return sb.toString();
    }

    private static void check(String name, boolean cond) {
        if (cond) {
            passed++;
            System.out.println("PASS  " + name);
        } else {
            failed++;
            System.out.println("FAIL  " + name);
        }
    }
}
