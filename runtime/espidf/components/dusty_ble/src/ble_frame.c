/* ble_frame.c: see include/ble_frame.h. Portable C99, no IDF headers. */
#include "ble_frame.h"
#include <string.h>

int ble_frame_parse_hdr(const uint8_t *buf, size_t frame_len, ble_frame_hdr_t *out)
{
    if (!buf || !out || frame_len < BLE_FRAME_HDR_LEN) return -1;
    out->id = buf[0];
    out->flags = buf[1];
    out->idx = (uint16_t)(buf[2] | ((uint16_t)buf[3] << 8)); /* LE */
    return 0;
}

size_t ble_frame_write_hdr(uint8_t *buf, const ble_frame_hdr_t *hdr)
{
    buf[0] = hdr->id;
    buf[1] = hdr->flags;
    buf[2] = (uint8_t)(hdr->idx & 0xFF);
    buf[3] = (uint8_t)((hdr->idx >> 8) & 0xFF);
    return BLE_FRAME_HDR_LEN;
}

size_t ble_frame_chunk_size(size_t mtu)
{
    /* payload <= MTU - 3 (ATT opcode+handle) - 4 (our header) */
    size_t overhead = 3 + BLE_FRAME_HDR_LEN;
    if (mtu <= overhead) return 0;
    return mtu - overhead;
}

size_t ble_frame_fragment_count(size_t payload_len, size_t mtu)
{
    size_t chunk = ble_frame_chunk_size(mtu);
    if (chunk == 0) return 0;
    if (payload_len == 0) return 1;
    return (payload_len + chunk - 1) / chunk;
}

int ble_frame_send(uint8_t id, uint8_t base_flags, const uint8_t *payload, size_t payload_len,
                    size_t mtu, ble_frame_sink_fn sink, void *ctx)
{
    size_t chunk = ble_frame_chunk_size(mtu);
    if (chunk == 0 || !sink) return -1;

    uint8_t frame[BLE_FRAME_HDR_LEN + 512]; /* generous local scratch; chunk is always < mtu <= 517 in practice */
    size_t frame_cap = sizeof(frame) - BLE_FRAME_HDR_LEN;
    if (chunk > frame_cap) chunk = frame_cap;

    size_t sent_bytes = 0;
    uint16_t idx = 0;
    int fragments = 0;

    do {
        size_t remaining = payload_len - sent_bytes;
        size_t n = remaining < chunk ? remaining : chunk;
        int is_last = (sent_bytes + n >= payload_len);

        ble_frame_hdr_t hdr;
        hdr.id = id;
        hdr.flags = (uint8_t)(base_flags | (is_last ? BLE_FRAME_FLAG_LAST : 0));
        hdr.idx = idx;
        ble_frame_write_hdr(frame, &hdr);
        if (n) memcpy(frame + BLE_FRAME_HDR_LEN, payload + sent_bytes, n);

        if (sink(frame, BLE_FRAME_HDR_LEN + n, ctx) != 0) return -1;

        sent_bytes += n;
        idx++;
        fragments++;
    } while (sent_bytes < payload_len);

    return fragments;
}

void ble_frame_reassembler_init(ble_frame_reassembler_t *r, uint8_t *buf, size_t cap)
{
    memset(r, 0, sizeof(*r));
    r->buf = buf;
    r->cap = cap;
}

void ble_frame_reassembler_reset(ble_frame_reassembler_t *r)
{
    r->len = 0;
    r->next_idx = 0;
    r->id = 0;
    r->flags = 0;
    r->active = 0;
}

int ble_frame_reassembler_feed(ble_frame_reassembler_t *r, const uint8_t *frame, size_t frame_len,
                                ble_frame_hdr_t *hdr_out)
{
    ble_frame_hdr_t hdr;
    if (ble_frame_parse_hdr(frame, frame_len, &hdr) != 0) {
        return BLE_FRAME_ERR_SHORT;
    }
    if (hdr_out) *hdr_out = hdr;

    size_t payload_len = frame_len - BLE_FRAME_HDR_LEN;

    if (!r->active) {
        if (hdr.idx != 0) {
            /* Can't start a message mid-sequence. */
            ble_frame_reassembler_reset(r);
            return BLE_FRAME_ERR_ORDER;
        }
        r->active = 1;
        r->id = hdr.id;
        r->flags = hdr.flags;
        r->len = 0;
        r->next_idx = 0;
    } else if (hdr.id != r->id) {
        ble_frame_reassembler_reset(r);
        return BLE_FRAME_ERR_ID;
    } else if (hdr.idx != r->next_idx) {
        /* Out of order or a duplicate (repeat of an already-consumed idx,
         * or a gap). Either way: reject and reset. */
        ble_frame_reassembler_reset(r);
        return BLE_FRAME_ERR_ORDER;
    }

    if (r->len + payload_len > r->cap) {
        ble_frame_reassembler_reset(r);
        return BLE_FRAME_ERR_TOOBIG;
    }
    if (payload_len) memcpy(r->buf + r->len, frame + BLE_FRAME_HDR_LEN, payload_len);
    r->len += payload_len;
    r->next_idx++;

    if (hdr.flags & BLE_FRAME_FLAG_LAST) {
        r->flags = hdr.flags; /* final fragment's flags win (BIN/ERR set on frag 0 anyway) */
        int done_flags = r->flags;
        (void)done_flags;
        /* Message complete; leave len/buf in place for the caller to read,
         * but mark inactive so the next idx-0 fragment starts a fresh one. */
        r->active = 0;
        return BLE_FRAME_DONE;
    }
    return BLE_FRAME_OK;
}

size_t ble_frame_bin_prefix_write(uint8_t *out, uint32_t total, uint32_t crc)
{
    out[0] = (uint8_t)(total & 0xFF);
    out[1] = (uint8_t)((total >> 8) & 0xFF);
    out[2] = (uint8_t)((total >> 16) & 0xFF);
    out[3] = (uint8_t)((total >> 24) & 0xFF);
    out[4] = (uint8_t)(crc & 0xFF);
    out[5] = (uint8_t)((crc >> 8) & 0xFF);
    out[6] = (uint8_t)((crc >> 16) & 0xFF);
    out[7] = (uint8_t)((crc >> 24) & 0xFF);
    return BLE_FRAME_BIN_PREFIX_LEN;
}

int ble_frame_bin_prefix_read(const uint8_t *in, size_t in_len, uint32_t *total_out, uint32_t *crc_out)
{
    if (!in || in_len < BLE_FRAME_BIN_PREFIX_LEN) return -1;
    uint32_t total = (uint32_t)in[0] | ((uint32_t)in[1] << 8) | ((uint32_t)in[2] << 16) | ((uint32_t)in[3] << 24);
    uint32_t crc = (uint32_t)in[4] | ((uint32_t)in[5] << 8) | ((uint32_t)in[6] << 16) | ((uint32_t)in[7] << 24);
    if (total_out) *total_out = total;
    if (crc_out) *crc_out = crc;
    return 0;
}

/* ---------------- crc32 (IEEE 802.3, the zlib polynomial 0xEDB88320) ---------------- */

/* Table is deterministic (every writer computes the identical 256 words),
 * so a race between two first-callers before FreeRTOS concurrency starts
 * is harmless; in practice this is only ever called from dusty_ble's
 * single request task. */
static uint32_t s_crc_table[256];
static int s_crc_table_ready;

static void crc_table_init(void)
{
    for (uint32_t i = 0; i < 256; i++) {
        uint32_t c = i;
        for (int k = 0; k < 8; k++) {
            c = (c & 1) ? (0xEDB88320u ^ (c >> 1)) : (c >> 1);
        }
        s_crc_table[i] = c;
    }
    s_crc_table_ready = 1;
}

uint32_t ble_crc32(uint32_t crc, const uint8_t *buf, size_t len)
{
    if (!s_crc_table_ready) crc_table_init();
    uint32_t c = ~crc;
    for (size_t i = 0; i < len; i++) {
        c = s_crc_table[(c ^ buf[i]) & 0xFF] ^ (c >> 8);
    }
    return ~c;
}
