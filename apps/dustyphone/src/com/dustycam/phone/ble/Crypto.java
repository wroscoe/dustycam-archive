package com.dustycam.phone.ble;

import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.Arrays;
import java.util.Base64;
import javax.crypto.Cipher;
import javax.crypto.Mac;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

/**
 * Crypto primitives for the GATT protocol (docs/phone_app_plan.md §1.5, §2):
 * HMAC-SHA256 for the {@code hello}/{@code auth} handshake and the session
 * key, AES-256-GCM for the {@code prov.set} envelope, plus hex/base64/nonce
 * helpers.
 *
 * <p>Pure Java (java.security/javax.crypto/java.util.Base64 only, no Android
 * imports — {@code java.util.Base64} has been available since API 26, this
 * app's minSdk) so it stays host-testable with a plain {@code java} run
 * (tests/CryptoTest.java).
 */
public final class Crypto {

    private static final String HMAC_ALGO = "HmacSHA256";
    private static final String AES_GCM_ALGO = "AES/GCM/NoPadding";
    private static final int GCM_IV_LEN = 12;
    private static final int GCM_TAG_BITS = 128;

    private Crypto() {}

    public static byte[] hmacSha256(byte[] key, byte[] message) {
        try {
            Mac mac = Mac.getInstance(HMAC_ALGO);
            mac.init(new SecretKeySpec(key, HMAC_ALGO));
            return mac.doFinal(message);
        } catch (Exception e) {
            throw new RuntimeException("HMAC-SHA256 failed", e);
        }
    }

    /**
     * The {@code auth} op's {@code mac} field: hex(HMAC-SHA256(ble_key,
     * cam_nonce_bytes || phone_nonce_bytes)) (§2 "Session").
     */
    public static String authMac(byte[] bleKey, byte[] camNonce, byte[] phoneNonce) {
        byte[] msg = new byte[camNonce.length + phoneNonce.length];
        System.arraycopy(camNonce, 0, msg, 0, camNonce.length);
        System.arraycopy(phoneNonce, 0, msg, camNonce.length, phoneNonce.length);
        return toHex(hmacSha256(bleKey, msg));
    }

    /** 16-byte nonce for the {@code hello} op's {@code pn} field. */
    public static byte[] randomNonce16() {
        byte[] n = new byte[16];
        new SecureRandom().nextBytes(n);
        return n;
    }

    /**
     * The {@code prov.set} envelope's session key (§2 "Session"): {@code sk =
     * HMAC(ble_key, "sk" || cam_nonce || phone_nonce)} — 32 bytes, used
     * directly as the AES-256 key below.
     */
    public static byte[] sessionKey(byte[] bleKey, byte[] camNonce, byte[] phoneNonce) {
        byte[] prefix = "sk".getBytes(StandardCharsets.US_ASCII);
        byte[] msg = new byte[prefix.length + camNonce.length + phoneNonce.length];
        System.arraycopy(prefix, 0, msg, 0, prefix.length);
        System.arraycopy(camNonce, 0, msg, prefix.length, camNonce.length);
        System.arraycopy(phoneNonce, 0, msg, prefix.length + camNonce.length, phoneNonce.length);
        return hmacSha256(bleKey, msg);
    }

    /**
     * Encrypts {@code plaintext} under {@code key} (32 B) for {@code
     * prov.set}'s {@code env} field. Wire layout of the returned bytes —
     * base64 that separately for the JSON field — is exactly what the plan
     * specifies: {@code IV(12 B) || AES-256-GCM ciphertext || TAG(16 B)}. A
     * fresh random IV is generated per call (GCM must never reuse an IV under
     * the same key); {@code javax.crypto}'s GCM {@code Cipher.doFinal}
     * already appends the 16-byte tag to the ciphertext, so the IV is simply
     * prepended to that combined output — no separate tag handling needed.
     */
    public static byte[] aesGcmEncrypt(byte[] key, byte[] plaintext) {
        try {
            byte[] iv = new byte[GCM_IV_LEN];
            new SecureRandom().nextBytes(iv);
            Cipher cipher = Cipher.getInstance(AES_GCM_ALGO);
            cipher.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(key, "AES"), new GCMParameterSpec(GCM_TAG_BITS, iv));
            byte[] ciphertextAndTag = cipher.doFinal(plaintext);
            byte[] envelope = new byte[iv.length + ciphertextAndTag.length];
            System.arraycopy(iv, 0, envelope, 0, iv.length);
            System.arraycopy(ciphertextAndTag, 0, envelope, iv.length, ciphertextAndTag.length);
            return envelope;
        } catch (Exception e) {
            throw new RuntimeException("AES-GCM encrypt failed", e);
        }
    }

    /** Inverse of {@link #aesGcmEncrypt}; throws (wrapped) if the tag doesn't verify. */
    public static byte[] aesGcmDecrypt(byte[] key, byte[] envelope) {
        try {
            if (envelope.length < GCM_IV_LEN + 16) {
                throw new IllegalArgumentException("envelope shorter than iv+tag: " + envelope.length);
            }
            byte[] iv = Arrays.copyOfRange(envelope, 0, GCM_IV_LEN);
            byte[] ciphertextAndTag = Arrays.copyOfRange(envelope, GCM_IV_LEN, envelope.length);
            Cipher cipher = Cipher.getInstance(AES_GCM_ALGO);
            cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(key, "AES"), new GCMParameterSpec(GCM_TAG_BITS, iv));
            return cipher.doFinal(ciphertextAndTag);
        } catch (Exception e) {
            throw new RuntimeException("AES-GCM decrypt failed", e);
        }
    }

    public static String toBase64(byte[] b) {
        return Base64.getEncoder().encodeToString(b);
    }

    public static byte[] fromBase64(String s) {
        return Base64.getDecoder().decode(s);
    }

    public static String toHex(byte[] b) {
        StringBuilder sb = new StringBuilder(b.length * 2);
        for (byte x : b) sb.append(String.format("%02x", x));
        return sb.toString();
    }

    public static byte[] fromHex(String hex) {
        int n = hex.length();
        if ((n & 1) != 0) throw new IllegalArgumentException("odd-length hex string");
        byte[] out = new byte[n / 2];
        for (int i = 0; i < n; i += 2) {
            out[i / 2] = (byte) ((Character.digit(hex.charAt(i), 16) << 4)
                    + Character.digit(hex.charAt(i + 1), 16));
        }
        return out;
    }
}
