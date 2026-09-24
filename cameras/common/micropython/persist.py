"""persist: the backup-register state that survives STM32 standby.
docs/camera_operation.md §2 (openmv_n6/PLAN.md).

word 0 of the backup domain = magic (0xD057 << 16 | layout version); words
1..len(PERSIST_FIELDS) = the fields, in order, one 32-bit word each. A bad
magic (power loss: VBAT lost) means defaults. `mem32` returns signed ints on
MicroPython, so reads are masked back to unsigned.

On hosts without `stm` (every non-STM32 MicroPython port, and CPython for
the tests) falls back to a JSON file at PERSIST_FILE.
"""
import json

MAGIC = (0xD057 << 16) | 1        # high half: magic; low half: layout version
PERSIST_FIELDS = (
    'wake_n', 'seq', 'awake_ms', 'dark_n', 'night', 'night_start',
    'night_s_last', 'clock_state', 'last_ts', 'pending_n', 'contact_n',
    'debug_n', 'crash_n', 'flags',
)
PERSIST_FILE = '/flash/persist.json'
_REG_BASE = 0x100                 # byte offset into the TAMP backup domain


def _defaults():
    return dict((k, 0) for k in PERSIST_FIELDS)


def _stm():
    try:
        import stm
        return stm
    except ImportError:
        return None


def persist_load():
    stm = _stm()
    if stm is not None:
        try:
            base = stm.TAMP_NS + _REG_BASE
            magic = stm.mem32[base] & 0xFFFFFFFF
            if magic != MAGIC:
                return _defaults()
            d = {}
            for i, k in enumerate(PERSIST_FIELDS):
                d[k] = stm.mem32[base + 4 * (i + 1)] & 0xFFFFFFFF
            return d
        except Exception:
            return _defaults()
    try:
        with open(PERSIST_FILE) as f:
            d = json.loads(f.read())
        if d.get('_magic') != MAGIC:
            return _defaults()
        out = _defaults()
        for k in PERSIST_FIELDS:
            if k in d:
                out[k] = int(d[k])
        return out
    except (OSError, ValueError):
        return _defaults()


def persist_save(d):
    stm = _stm()
    if stm is not None:
        try:
            base = stm.TAMP_NS + _REG_BASE
            stm.mem32[base] = MAGIC
            for i, k in enumerate(PERSIST_FIELDS):
                stm.mem32[base + 4 * (i + 1)] = int(d.get(k, 0)) & 0xFFFFFFFF
            return True
        except Exception:
            pass
    out = {'_magic': MAGIC}
    for k in PERSIST_FIELDS:
        out[k] = int(d.get(k, 0))
    try:
        with open(PERSIST_FILE, 'w') as f:
            f.write(json.dumps(out))
        return True
    except OSError:
        return False
