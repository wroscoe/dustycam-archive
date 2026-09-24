"""rank: score, drain order, motion-centred crop box and the judge decision.
docs/camera_operation.md §7; crop_box mirrors dc_crop_box in
runtime/espidf/components/dusty_core/src/motion.c exactly. All pure.
"""

_SCORE_CAP = 1.499999   # 'boot'/'heartbeat' (2.0) and 'manual' (1.5) always outrank a judged/motion frame


def score_for(why, diff, conf, sharp):
    """Rank for the drain (camera_operation.md §7): proof-of-life frames
    first, then manual shots, then judged/motion frames by confidence (or
    diff when unjudged), sharpness as a small tiebreaker."""
    tie = (sharp or 0.0) / 1e6
    if why in ('boot', 'heartbeat'):
        return 2.0 + tie
    if why == 'manual':
        return 1.5
    val = (conf if conf is not None else diff) + tie
    if val >= 1.5:
        val = _SCORE_CAP
    return val


def rank_order(entries):
    """Sort entries (dicts with 'score', 'seq') score desc, seq asc."""
    return sorted(entries, key=lambda e: (-e['score'], e['seq']))


def crop_box(bx, by, bw, bh, tw, th, W, H, pad=0.5, diffuse=0.6, min_side=96):
    """Motion-centred square crop: bbox (bx,by,bw,bh) in a tw x th thumbnail
    maps to a W x H capture, padded by `pad` (0.5 = 50%%), made square,
    clamped to the frame, at least min_side. Falls back to the largest
    centred square when there is no bbox (bw == 0) or it covers more than
    `diffuse` of the thumbnail area."""
    if bw == 0 or float(bw) * bh > diffuse * tw * th:
        side = min(W, H)
        return (W - side) // 2, (H - side) // 2, side

    x0, x1 = bx, bx + bw - 1
    y0, y1 = by, by + bh - 1
    fx0 = (x0 + 0.5) * W / tw
    fx1 = (x1 + 0.5) * W / tw
    fy0 = (y0 + 0.5) * H / th
    fy1 = (y1 + 0.5) * H / th

    bw_f, bh_f = fx1 - fx0, fy1 - fy0
    padpx = pad * max(bw_f, bh_f)
    fx0 -= padpx
    fx1 += padpx
    fy0 -= padpx
    fy1 += padpx
    bw_f, bh_f = fx1 - fx0, fy1 - fy0

    cx = (fx0 + fx1) * 0.5
    cy = (fy0 + fy1) * 0.5
    side = max(bw_f, bh_f)
    if side < min_side:
        side = min_side
    max_side = min(W, H)
    if side > max_side:
        side = max_side

    x = cx - side * 0.5
    y = cy - side * 0.5
    if x + side > W:
        x = W - side
    if x < 0:
        x = 0
    if y + side > H:
        y = H - side
    if y < 0:
        y = 0
    return int(x + 0.5), int(y + 0.5), int(side + 0.5)


def judge_decide(conf, cfg, seq):
    """(keep, reason). conf is the gate confidence 0..1, or None when the
    gate did not run (fail-open)."""
    if conf is None:
        return True, 'open'
    if conf * 100 >= cfg['gate_pct']:
        return True, 'pass'
    if cfg.get('keep_all'):
        return True, 'keep_all'
    audit_n = cfg.get('audit_n')
    if audit_n and seq % audit_n == 0:
        return True, 'audit'
    return False, 'reject'
