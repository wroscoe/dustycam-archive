package com.dustycam.phone.ble;

import java.nio.charset.StandardCharsets;
import java.util.Arrays;

/**
 * Plain-{@code main} assertions for {@link Crypto} — no JUnit, no Android.
 * Compiled and run with the bare JDK: `make test` (see ../Makefile).
 */
public class CryptoTest {

    private static int passed = 0;
    private static int failed = 0;

    public static void main(String[] args) throws Exception {
        testHmacKnownVector();
        testAesGcmRoundTrip();
        testAesGcmTamperDetected();
        testAesGcmFreshIvPerCall();
        testSessionKeyDeterministicAnd32Bytes();
        testHexRoundTrip();

        System.out.println();
        System.out.println(passed + " passed, " + failed + " failed");
        if (failed > 0) System.exit(1);
    }

    /** RFC 4231 test case 1: HMAC-SHA-256(key=0x0b*20, "Hi There"). */
    private static void testHmacKnownVector() {
        byte[] key = new byte[20];
        Arrays.fill(key, (byte) 0x0b);
        byte[] data = "Hi There".getBytes(StandardCharsets.US_ASCII);
        String want = "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7";
        String got = Crypto.toHex(Crypto.hmacSha256(key, data));
        check("hmac RFC4231 test case 1", got.equals(want));
    }

    private static void testAesGcmRoundTrip() {
        byte[] key = new byte[32];
        Arrays.fill(key, (byte) 0x42);
        byte[] plaintext = "{\"device\":\"xiaocam1\",\"ssid\":\"home\",\"pass\":\"s3cr3t\"}"
                .getBytes(StandardCharsets.UTF_8);

        byte[] envelope = Crypto.aesGcmEncrypt(key, plaintext);
        // Wire layout: IV(12B) || ciphertext(len(plaintext)) || TAG(16B).
        check("envelope length = iv(12) + ciphertext + tag(16)",
                envelope.length == plaintext.length + 12 + 16);

        byte[] decrypted = Crypto.aesGcmDecrypt(key, envelope);
        check("aes-gcm round trip bytes match", Arrays.equals(decrypted, plaintext));

        // base64 wrapping (what actually goes in the `env` JSON field) round trips too.
        String b64 = Crypto.toBase64(envelope);
        byte[] back = Crypto.fromBase64(b64);
        check("base64 round trip", Arrays.equals(back, envelope));
    }

    private static void testAesGcmTamperDetected() {
        byte[] key = new byte[32];
        Arrays.fill(key, (byte) 7);
        byte[] plaintext = "secret identity payload".getBytes(StandardCharsets.UTF_8);
        byte[] envelope = Crypto.aesGcmEncrypt(key, plaintext);
        envelope[envelope.length - 1] ^= 0x01; // flip a bit in the GCM tag (last 16 bytes)

        boolean threw = false;
        try {
            Crypto.aesGcmDecrypt(key, envelope);
        } catch (RuntimeException e) {
            threw = true;
        }
        check("aes-gcm tampered tag rejected", threw);
    }

    private static void testAesGcmFreshIvPerCall() {
        byte[] key = new byte[32];
        Arrays.fill(key, (byte) 9);
        byte[] plaintext = "same plaintext twice".getBytes(StandardCharsets.UTF_8);
        byte[] e1 = Crypto.aesGcmEncrypt(key, plaintext);
        byte[] e2 = Crypto.aesGcmEncrypt(key, plaintext);
        byte[] iv1 = Arrays.copyOfRange(e1, 0, 12);
        byte[] iv2 = Arrays.copyOfRange(e2, 0, 12);
        check("fresh random IV per encrypt call", !Arrays.equals(iv1, iv2));
    }

    private static void testSessionKeyDeterministicAnd32Bytes() {
        byte[] bleKey = new byte[32];
        Arrays.fill(bleKey, (byte) 1);
        byte[] camNonce = new byte[16];
        Arrays.fill(camNonce, (byte) 2);
        byte[] phoneNonce = new byte[16];
        Arrays.fill(phoneNonce, (byte) 3);

        byte[] sk1 = Crypto.sessionKey(bleKey, camNonce, phoneNonce);
        byte[] sk2 = Crypto.sessionKey(bleKey, camNonce, phoneNonce);
        check("sessionKey is deterministic", Arrays.equals(sk1, sk2));
        check("sessionKey is 32 bytes (usable directly as an AES-256 key)", sk1.length == 32);

        byte[] otherPhoneNonce = new byte[16];
        Arrays.fill(otherPhoneNonce, (byte) 4);
        byte[] sk3 = Crypto.sessionKey(bleKey, camNonce, otherPhoneNonce);
        check("sessionKey changes with phone nonce", !Arrays.equals(sk1, sk3));
    }

    private static void testHexRoundTrip() {
        byte[] b = new byte[]{0x00, 0x01, (byte) 0xFF, 0x10, (byte) 0xAB};
        String hex = Crypto.toHex(b);
        check("toHex length = 2*n", hex.length() == b.length * 2);
        check("hex round trip", Arrays.equals(Crypto.fromHex(hex), b));
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
