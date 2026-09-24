"""gamespool: the ranked SD spool for game_lowpower. camera_operation.md §7.

Layout: /sdcard/spool/<boot>/<seq:06d>.jpg + .json (sidecar first, image to
.tmp, rename); /sdcard/debug/<boot>/<wake_n:06d>.jpg + .json for debug
frames. The four path globals below are read fresh on every call (never
cached into a default arg or a closure) so tests can monkeypatch them to a
tmp_path root.
"""
import json
import os
import time

from uplink import *
from rank import *

SPOOL_DIR = '/sdcard/spool'
DEBUG_DIR = '/sdcard/debug'
THUMB_FILE = '/sdcard/spool/thumb.bin'
WAKELOG = '/sdcard/wakelog.txt'
WAKELOG_ROTATED = '/sdcard/wakelog.1.txt'
WAKELOG_MAX = 1024 * 1024


def _is_dir(path):
    try:
        os.listdir(path)
        return True
    except OSError:
        return False


def gs_ready():
    """mkdir both dirs (idempotent); True if both are listable afterward."""
    ok = True
    for d in (SPOOL_DIR, DEBUG_DIR):
        try:
            os.mkdir(d)
        except OSError:
            pass
        if not _is_dir(d):
            ok = False
    return ok


def _boot_name(root, boot):
    d = '%s/%s' % (root, boot)
    try:
        os.mkdir(d)
    except OSError:
        pass
    return d


def gs_name(boot, seq):
    return '%s/%06d' % (_boot_name(SPOOL_DIR, boot), seq)


def _debug_name(boot, wake_n):
    return '%s/%06d' % (_boot_name(DEBUG_DIR, boot), wake_n)


def _gs_write_files(base, data, meta):
    try:
        with open(base + '.json', 'w') as f:
            f.write(meta)
        with open(base + '.tmp', 'wb') as f:
            f.write(data)
        os.rename(base + '.tmp', base + '.jpg')
        return True
    except OSError:
        for ext in ('.json', '.tmp', '.jpg'):
            try:
                os.remove(base + ext)
            except OSError:
                pass
        return False


def gs_write(boot, seq, data, meta):
    return _gs_write_files(gs_name(boot, seq), data, meta)


def gs_write_debug(boot, wake_n, data, meta):
    return _gs_write_files(_debug_name(boot, wake_n), data, meta)


def gs_scan(root):
    """[{'base','score','seq'}] for every sidecar under `root`. A bad or
    missing score reads as -1 (sorts last, never crashes the drain)."""
    out = []
    try:
        boots = os.listdir(root)
    except OSError:
        return out
    for b in boots:
        bp = root + '/' + b
        try:
            files = os.listdir(bp)
        except OSError:
            continue                       # not a directory (e.g. thumb.bin)
        for f in files:
            if not f.endswith('.json'):
                continue
            stem = f[:-5]
            try:
                seq = int(stem)
            except ValueError:
                seq = 0
            score = -1
            try:
                with open(bp + '/' + f) as fp:
                    score = json.loads(fp.read()).get('score', -1)
            except (OSError, ValueError):
                score = -1
            out.append({'base': bp + '/' + stem, 'score': score, 'seq': seq})
    return out


def gs_count(root):
    n = 0
    try:
        boots = os.listdir(root)
    except OSError:
        return 0
    for b in boots:
        try:
            files = os.listdir(root + '/' + b)
        except OSError:
            continue
        n += sum(1 for f in files if f.endswith('.json'))
    return n


def gs_drain(root, cap, idle, version, on_sent=None, ip=None):
    """Rank-ordered upload of `root`, up to `cap` files. Deletes both files
    of an accepted frame; stops after 5 consecutive failures. Returns
    (sent, failed)."""
    entries = rank_order(gs_scan(root))
    sent = 0
    failed = 0
    consec_fail = 0
    n = 0
    for e in entries:
        if sent >= cap:
            break
        base = e['base']
        ok = False
        t_f = time.ticks_ms()
        try:
            try:
                with open(base + '.json') as fp:
                    meta = fp.read()
            except OSError:
                meta = '{"buffered": true, "v": "%s"}' % version
            if ip:
                # off-grid frames are captured with the radio off (ip 0.0.0.0);
                # the address that is valid is the one we are uploading from
                try:
                    m = json.loads(meta)
                    m['ip'] = ip
                    meta = json.dumps(m)
                except ValueError:
                    pass
            with open(base + '.jpg', 'rb') as fp:
                ok = post_blob('frame', fp, meta, os.stat(base + '.jpg')[6])
        except OSError:
            ok = False
        if ok:
            sent += 1
            consec_fail = 0
            for ext in ('.jpg', '.json'):
                try:
                    os.remove(base + ext)
                except OSError:
                    pass
            if on_sent:
                try:
                    on_sent(e)
                except Exception:
                    pass
        else:
            failed += 1
            consec_fail += 1
        t_i = time.ticks_ms()
        idle()
        n += 1
        if n <= 5 or n % 20 == 0:
            print('drain %d %s post=%dms idle=%dms' % (n, 'ok' if ok else 'FAIL', time.ticks_diff(t_i, t_f), time.ticks_diff(time.ticks_ms(), t_i)))
        if consec_fail >= 5:
            break
    return sent, failed


def gs_reclaim(max_frames):
    """Delete the oldest spool frames (lowest boot dir, then lowest seq)
    until the spool count is <= max_frames; removes emptied boot dirs.
    Returns the number removed."""
    n = gs_count(SPOOL_DIR)
    if n <= max_frames:
        return 0
    try:
        boots = [b for b in os.listdir(SPOOL_DIR) if _is_dir(SPOOL_DIR + '/' + b)]
    except OSError:
        return 0
    boots.sort(key=lambda b: int(b) if b.isdigit() else b)
    removed = 0
    for b in boots:
        if n <= max_frames:
            break
        bp = SPOOL_DIR + '/' + b
        try:
            files = os.listdir(bp)
        except OSError:
            continue
        seqs = sorted(f[:-5] for f in files if f.endswith('.json'))
        for s in seqs:
            if n <= max_frames:
                break
            base = bp + '/' + s
            for ext in ('.jpg', '.json'):
                try:
                    os.remove(base + ext)
                except OSError:
                    pass
            n -= 1
            removed += 1
        try:
            if not os.listdir(bp):
                os.rmdir(bp)
        except OSError:
            pass
    return removed


def gs_thumb_load():
    try:
        with open(THUMB_FILE, 'rb') as f:
            return f.read()
    except OSError:
        return None


def gs_thumb_save(data):
    try:
        with open(THUMB_FILE, 'wb') as f:
            f.write(data)
        return True
    except OSError:
        return False


def gs_log(line):
    try:
        try:
            if os.stat(WAKELOG)[6] > WAKELOG_MAX:
                try:
                    os.remove(WAKELOG_ROTATED)
                except OSError:
                    pass
                os.rename(WAKELOG, WAKELOG_ROTATED)
        except OSError:
            pass
        with open(WAKELOG, 'a') as f:
            f.write(line + '\n')
        return True
    except OSError:
        return False
