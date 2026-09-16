/* ble_auth_internal.h: private helpers shared by dusty_ble.c and
 * ble_auth.c. Not part of the component's public API (not installed under
 * include/). docs/phone_app_plan.md §2 "Session".
 */
#ifndef BLE_AUTH_INTERNAL_H
#define BLE_AUTH_INTERNAL_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define BLE_AUTH_NONCE_LEN 16
#define BLE_AUTH_HMAC_LEN 32
#define BLE_AUTH_KEY_LEN 32

/* esp_fill_random() into out[16]. */
void ble_auth_gen_nonce(uint8_t out[BLE_AUTH_NONCE_LEN]);

/* Lowercase hex, NUL-terminated. hex_out must have room for 2*n + 1. */
void ble_auth_hex_encode(const uint8_t *bytes, size_t n, char *hex_out);

/* Decodes exactly out_n bytes (i.e. hex must be exactly 2*out_n chars, no
 * separators). Returns 0 on success, -1 on a malformed or mis-sized
 * string. */
int ble_auth_hex_decode(const char *hex, uint8_t *out, size_t out_n);

/* HMAC-SHA256(key, msg) via mbedtls. out must have room for 32 bytes. */
void ble_auth_hmac_sha256(const uint8_t *key, size_t key_len,
                           const uint8_t *msg, size_t msg_len,
                           uint8_t out[BLE_AUTH_HMAC_LEN]);

/* Constant-time compare (auth MACs, not a general helper). */
int ble_auth_consteq(const uint8_t *a, const uint8_t *b, size_t n);

/* ---------------- prov.set envelope (docs/phone_app_plan.md §2, §6) ----------------
 * `env` = base64(IV(12B) || AES-256-GCM ciphertext || TAG(16B)), key =
 * sk = HMAC-SHA256(ble_key, "sk"||cam_nonce||phone_nonce). This exact
 * layout is also documented on dusty_ble.h's DUSTY_BLE_PROV_ENV_* macros
 * so the phone app's encoder matches byte-for-byte. */
#define BLE_AUTH_GCM_IV_LEN 12
#define BLE_AUTH_GCM_TAG_LEN 16
#define BLE_AUTH_GCM_KEY_LEN 32 /* AES-256 */

/* Decrypts+authenticates `buf` (buf_len bytes: IV || ciphertext || TAG, in
 * that order) with key32 (32 raw bytes). `out` must have room for at
 * least buf_len - IV_LEN - TAG_LEN bytes (the plaintext is never longer
 * than the ciphertext). Returns the plaintext length on success (tag
 * verified), -1 on a bad length or an authentication failure -- out is
 * not written to on failure. */
int ble_auth_gcm_decrypt(const uint8_t key32[BLE_AUTH_GCM_KEY_LEN], const uint8_t *buf, size_t buf_len, uint8_t *out);

#ifdef __cplusplus
}
#endif
#endif
