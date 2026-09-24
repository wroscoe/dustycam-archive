"""night: the night policy, pure. docs/camera_operation.md §6, mirrors
dc_night_step / dc_night_predict in runtime/espidf/components/
dusty_core/src/night.c exactly (semantics), generalised so the long "sleep
toward dawn" figure can be recomputed on every probe, not only at the
moment night is entered -- this lets a wake resume mid-night from a saved
state and still land near the learned dawn.

State dict: {'night': 0/1, 'dark_n': int, 'start': epoch_s, 'hist': [..<=7]}
(newest length last). `night_step` never sleeps or does I/O; the caller
saves the state and deep-sleeps for `sleep_s`.
"""
import json

NIGHT_HIST = 7


def night_new():
    return {'night': 0, 'dark_n': 0, 'start': 0, 'hist': []}


def night_predict(state):
    """Median of the newest up-to-3 of up to 7 lengths. 0 with no history."""
    hist = state.get('hist') or []
    if not hist:
        return 0
    last = hist[-3:]
    s = sorted(last)
    k = len(s)
    if k % 2 == 1:
        return s[k // 2]
    return (s[k // 2 - 1] + s[k // 2]) // 2


def _night_sleep(state, cfg, now):
    if not state.get('hist'):
        return cfg['night_probe_s']
    predicted = night_predict(state)
    remaining = predicted - cfg['night_margin_s'] - (now - state.get('start', now))
    if remaining > cfg['night_probe_s']:
        return remaining
    return cfg['night_probe_s']


def night_step(state, lum, now, cfg):
    """(sleep_s, event). event in 'none','enter','probe','exit'. sleep_s is
    None only when not applicable (never, in practice: not-night returns
    cfg['period_s'])."""
    if not state.get('night'):
        if lum < cfg['lum_night']:
            state['dark_n'] = state.get('dark_n', 0) + 1
        else:
            state['dark_n'] = 0
        if state['dark_n'] >= cfg['night_confirm_n']:
            state['night'] = 1
            state['start'] = now
            state['dark_n'] = 0
            sleep_s = _night_sleep(state, cfg, now)
            return sleep_s, 'enter'
        return cfg['period_s'], 'none'

    # already in night: this wake is a probe
    if lum >= cfg['lum_day']:
        length = now - state.get('start', now)
        hist = state.get('hist') or []
        hist.append(length)
        state['hist'] = hist[-NIGHT_HIST:]
        state['last_len'] = length
        state['night'] = 0
        state['dark_n'] = 0
        return cfg['period_s'], 'exit'

    sleep_s = _night_sleep(state, cfg, now)
    return sleep_s, 'probe'


def night_load(path):
    st = night_new()
    try:
        with open(path) as f:
            d = json.loads(f.read())
        st['hist'] = list(d.get('hist', []))[-NIGHT_HIST:]
        st['night'] = int(d.get('night', 0))
        st['start'] = int(d.get('start', 0))
    except (OSError, ValueError):
        pass
    return st


def night_save(path, state):
    d = {'hist': list(state.get('hist', []))[-NIGHT_HIST:],
         'night': state.get('night', 0), 'start': state.get('start', 0)}
    try:
        with open(path, 'w') as f:
            f.write(json.dumps(d))
        return True
    except OSError:
        return False
