/* ble_frame: the wire framing for dustyphone's GATT protocol (docs/
 * phone_app_plan.md §2). PORTABLE: no IDF headers, C99 only, no heap, no
 * I/O -- driven from runtime/espidf/tests/test_ble_frame.py through
 * ctypes, same pattern as dusty_core (see that component's host/Makefile).
 *
 * Header (4 B, every cmd/rsp/data/evt frame): [id u8][flags u8][idx u16 LE].
 * flags: LAST=0x01 (final fragment of this message), BIN=0x02 (payload is
 * a binary transfer: reassembled payload starts with an 8 B prefix, see
 * below), ERR=0x04 (this message is an error). `id` correlates a request
 * with its response/data frames (0 is reserved for unsolicited `evt`
 * frames). `idx` starts at 0 and increments by one per fragment of the
 * same id; a receiver that sees anything else (skip, repeat, or a new id
 * arriving mid-message) must reject and reset -- see
 * ble_frame_reassembler_feed().
 *
 * Binary transfers (BIN flag): the first fragment's payload begins with
 * `[total u32 LE][crc32 u32 LE]` (the IEEE/zlib polynomial, ble_crc32()
 * below), followed by `total` raw bytes spread across as many fragments
 * as needed. There is no per-fragment ACK: the link layer is ordered and
 * reliable, so the receiver only needs to check total+crc once the last
 * fragment (LAST) has arrived.
 *
 * Limits (docs/phone_app_plan.md §2): request <= 4 KB, response <= 8 KB,
 * data <= 512 KB. These are not baked into this file -- the caller sizes
 * the reassembler's buffer to the limit that applies to what it is
 * receiving (a cmd write vs. a data transfer) via BLE_FRAME_LIMIT_*.
 */
#ifndef BLE_FRAME_H
#define BLE_FRAME_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define BLE_FRAME_HDR_LEN 4u

#define BLE_FRAME_FLAG_LAST 0x01u
#define BLE_FRAME_FLAG_BIN  0x02u
#define BLE_FRAME_FLAG_ERR  0x04u

#define BLE_FRAME_LIMIT_REQUEST  (4u * 1024u)
#define BLE_FRAME_LIMIT_RESPONSE (8u * 1024u)
#define BLE_FRAME_LIMIT_DATA     (512u * 1024u)

/* [total u32 LE][crc32 u32 LE] prefix on the first fragment of a BIN
 * transfer's payload. */
#define BLE_FRAME_BIN_PREFIX_LEN 8u

typedef struct {
    uint8_t id;
    uint8_t flags;
    uint16_t idx;
} ble_frame_hdr_t;

/* Parses the 4 B header from the front of `buf` (frame_len >= 4). Returns
 * 0 on success, -1 if frame_len < BLE_FRAME_HDR_LEN. */
int ble_frame_parse_hdr(const uint8_t *buf, size_t frame_len, ble_frame_hdr_t *out);

/* Writes the 4 B header into buf[0..4). buf must have room for at least
 * BLE_FRAME_HDR_LEN bytes. Returns BLE_FRAME_HDR_LEN. */
size_t ble_frame_write_hdr(uint8_t *buf, const ble_frame_hdr_t *hdr);

/* Largest application payload that fits in one fragment at this ATT MTU
 * (mtu - 3 B ATT header - BLE_FRAME_HDR_LEN), or 0 if mtu is too small to
 * carry a header at all. */
size_t ble_frame_chunk_size(size_t mtu);

/* Number of fragments ble_frame_send() will emit for a payload of this
 * size at this mtu (>= 1, even for payload_len == 0: an empty message is
 * still one header-only fragment). 0 if mtu is too small. */
size_t ble_frame_fragment_count(size_t payload_len, size_t mtu);

/* Called once per outgoing fragment by ble_frame_send(). `frame` (header +
 * chunk, <= mtu - 3 bytes) is only valid for the duration of the call --
 * the sink must copy anything it needs to keep (e.g. into the actual BLE
 * notify buffer) before returning. Return 0 to continue sending, nonzero
 * to abort (ble_frame_send() then returns -1). */
typedef int (*ble_frame_sink_fn)(const uint8_t *frame, size_t frame_len, void *ctx);

/* Fragments `payload` (payload_len bytes, may be NULL/0) into frames of at
 * most ble_frame_chunk_size(mtu) application bytes, id in every header,
 * base_flags ORed onto every fragment (e.g. BLE_FRAME_FLAG_BIN for a data
 * transfer -- build the 8 B total+crc32 prefix into `payload` yourself
 * first, see ble_frame_bin_prefix_write()), BLE_FRAME_FLAG_LAST added
 * automatically to the final fragment, idx starting at 0. Calls `sink`
 * once per fragment. Returns the number of fragments sent, or -1 if mtu
 * is too small to carry even one byte of payload, or a sink call aborted
 * the send. */
int ble_frame_send(uint8_t id, uint8_t base_flags, const uint8_t *payload, size_t payload_len,
                    size_t mtu, ble_frame_sink_fn sink, void *ctx);

/* ---------------- reassembler ---------------- */

typedef enum {
    BLE_FRAME_OK   = 0,  /* fragment accepted, message still in progress */
    BLE_FRAME_DONE = 1,  /* fragment accepted, LAST seen: message complete (r->len bytes in r->buf) */
    BLE_FRAME_ERR_SHORT  = -1, /* frame shorter than BLE_FRAME_HDR_LEN */
    BLE_FRAME_ERR_ORDER  = -2, /* idx out of sequence (skip, repeat, or LAST already seen): reset */
    BLE_FRAME_ERR_TOOBIG = -3, /* would exceed the reassembler's capacity: reset */
    BLE_FRAME_ERR_ID     = -4, /* a different id arrived while a message was in progress: reset */
} ble_frame_result_t;

typedef struct {
    uint8_t *buf;     /* caller-owned, cap bytes; holds the reassembled payload */
    size_t cap;
    size_t len;       /* bytes assembled so far */
    uint16_t next_idx;
    uint8_t id;
    uint8_t flags;    /* flags observed on the first fragment (BIN/ERR carry through) */
    uint8_t active;   /* 1 once the first fragment of a message has been accepted */
} ble_frame_reassembler_t;

/* buf/cap are kept by reference; buf must outlive the reassembler and be
 * at least cap bytes (cap is normally one of BLE_FRAME_LIMIT_*). */
void ble_frame_reassembler_init(ble_frame_reassembler_t *r, uint8_t *buf, size_t cap);

/* Resets to the "no message in progress" state without touching buf. */
void ble_frame_reassembler_reset(ble_frame_reassembler_t *r);

/* Feeds one received frame (header + chunk, frame_len bytes) into the
 * reassembler. On BLE_FRAME_DONE, r->len is the total reassembled length
 * and r->flags carries BIN/ERR from the first fragment. On any negative
 * result the reassembler has already reset itself (a fresh idx-0 fragment
 * for a new message will be accepted next). hdr_out may be NULL. */
int ble_frame_reassembler_feed(ble_frame_reassembler_t *r, const uint8_t *frame, size_t frame_len,
                                ble_frame_hdr_t *hdr_out);

/* ---------------- binary transfer prefix ---------------- */

/* Writes [total u32 LE][crc32 u32 LE] into out[0..8). Returns
 * BLE_FRAME_BIN_PREFIX_LEN. out must have room for 8 bytes. */
size_t ble_frame_bin_prefix_write(uint8_t *out, uint32_t total, uint32_t crc);

/* Reads the 8 B prefix from the front of a reassembled BIN payload.
 * Returns 0 on success (in_len >= 8), -1 otherwise. */
int ble_frame_bin_prefix_read(const uint8_t *in, size_t in_len, uint32_t *total_out, uint32_t *crc_out);

/* ---------------- crc32 (IEEE 802.3 / zlib polynomial) ---------------- */

/* Same algorithm and calling convention as zlib's crc32(): start with
 * crc=0 for a new buffer, or with the previous return value to continue
 * over more data (crc32(data) == ble_crc32(0, data, len)). Verified
 * against the standard test vector: ble_crc32(0, "123456789", 9) ==
 * 0xCBF43926. */
uint32_t ble_crc32(uint32_t crc, const uint8_t *buf, size_t len);

#ifdef __cplusplus
}
#endif
#endif
