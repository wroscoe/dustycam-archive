#include "ble_auth_internal.h"

#include "esp_random.h"
#include "mbedtls/md.h"
#include "mbedtls/gcm.h"

void ble_auth_gen_nonce(uint8_t out[BLE_AUTH_NONCE_LEN])
{
    esp_fill_random(out, BLE_AUTH_NONCE_LEN);
}

void ble_auth_hex_encode(const uint8_t *bytes, size_t n, char *hex_out)
{
    static const char digits[] = "0123456789abcdef";
    for (size_t i = 0; i < n; i++) {
        hex_out[2 * i] = digits[(bytes[i] >> 4) & 0xF];
        hex_out[2 * i + 1] = digits[bytes[i] & 0xF];
    }
    hex_out[2 * n] = '\0';
}

static int hex_nibble(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

int ble_auth_hex_decode(const char *hex, uint8_t *out, size_t out_n)
{
    if (!hex || !out) return -1;
    for (size_t i = 0; i < out_n; i++) {
        int hi = hex_nibble(hex[2 * i]);
        int lo = hex_nibble(hex[2 * i + 1]);
        if (hi < 0 || lo < 0) return -1;
        out[i] = (uint8_t)((hi << 4) | lo);
    }
    if (hex[2 * out_n] != '\0') return -1; /* trailing junk: wrong length */
    return 0;
}

void ble_auth_hmac_sha256(const uint8_t *key, size_t key_len,
                           const uint8_t *msg, size_t msg_len,
                           uint8_t out[BLE_AUTH_HMAC_LEN])
{
    const mbedtls_md_info_t *info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
    mbedtls_md_hmac(info, key, key_len, msg, msg_len, out);
}

int ble_auth_consteq(const uint8_t *a, const uint8_t *b, size_t n)
{
    uint8_t diff = 0;
    for (size_t i = 0; i < n; i++) diff |= (uint8_t)(a[i] ^ b[i]);
    return diff == 0;
}

int ble_auth_gcm_decrypt(const uint8_t key32[BLE_AUTH_GCM_KEY_LEN], const uint8_t *buf, size_t buf_len, uint8_t *out)
{
    if (!key32 || !buf || !out) return -1;
    if (buf_len < (size_t)(BLE_AUTH_GCM_IV_LEN + BLE_AUTH_GCM_TAG_LEN)) return -1;

    const uint8_t *iv = buf;
    size_t ct_len = buf_len - BLE_AUTH_GCM_IV_LEN - BLE_AUTH_GCM_TAG_LEN;
    const uint8_t *ct = buf + BLE_AUTH_GCM_IV_LEN;
    const uint8_t *tag = buf + BLE_AUTH_GCM_IV_LEN + ct_len;

    mbedtls_gcm_context ctx;
    mbedtls_gcm_init(&ctx);
    int rc = mbedtls_gcm_setkey(&ctx, MBEDTLS_CIPHER_ID_AES, key32, BLE_AUTH_GCM_KEY_LEN * 8);
    if (rc == 0) {
        rc = mbedtls_gcm_auth_decrypt(&ctx, ct_len, iv, BLE_AUTH_GCM_IV_LEN, NULL, 0,
                                       tag, BLE_AUTH_GCM_TAG_LEN, ct, out);
    }
    mbedtls_gcm_free(&ctx);
    return rc == 0 ? (int)ct_len : -1;
}
