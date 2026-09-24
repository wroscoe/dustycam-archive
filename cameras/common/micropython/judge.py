"""judge: the on-device gate. docs/camera_operation.md §7, animal_model.md.

`ml.Model(GATE_MODEL)` (GATE_MODEL is a board global, default
'/flash/gate.tflite') with the hard-fault guard: a `model_pending.txt`
marker is written before the load and removed after, so a load that hangs
the MCU shows up as a leftover marker on the *next* boot -- that becomes
`model_bad.txt` (storing the file's size) and the gate stays open (fails
open) until a differently-sized file appears at GATE_MODEL.

Everything else fails open too: no `ml` module, no file, a predict
exception -- `gate_score` never raises, it returns None and the caller
(rank.judge_decide) treats None as "keep everything" (§7's `keep_all`
except the caller doesn't even need that: reason 'open').

Output interpretation mirrors cameras/xiao_pantilt/software/app/main/gate.cc
(gate_score there): the model is a MobileNetV2-0.35 gate whose animal class
is a fixed output index (1 of a 2-class softmax on the XIAO), dequantised as
(raw - zero_point) * scale. Here we additionally consult `model.labels` when
present (the N6's larger/relabelled model) to find the 'animal' index, and
fall back to index 0 for a single-output model or index 1 for a 2/3-class
one with no labels.
"""
import os
import time

try:
    import ml
except ImportError:
    ml = None

MODEL_PENDING = '/flash/model_pending.txt'
MODEL_BAD = '/flash/model_bad.txt'

LAST_JUDGE = ['']          # human-readable last outcome, for /status
GATE_MS = [0]               # last predict() wall time, ms

_model = None


def _gate_read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return ''


def _gate_write(path, text):
    try:
        with open(path, 'w') as f:
            f.write(text)
    except OSError:
        pass


def _gate_rm(path):
    try:
        os.remove(path)
    except OSError:
        pass


def gate_init():
    """Load the gate model, applying the hard-fault guard. Returns the
    model, or None (fails open) with LAST_JUDGE explaining why. Never
    raises."""
    global _model
    _model = None
    model_path = globals().get('GATE_MODEL', '/flash/gate.tflite')
    if ml is None:
        LAST_JUDGE[0] = 'no ml module'
        return None
    try:
        size = os.stat(model_path)[6]
    except OSError:
        LAST_JUDGE[0] = 'no model file'
        return None

    if _gate_read(MODEL_PENDING):
        # a load was in progress when the board last stopped responding
        _gate_write(MODEL_BAD, str(size))
        _gate_rm(MODEL_PENDING)
        LAST_JUDGE[0] = 'model hard-faulted last boot, blacklisted'
        return None

    bad = _gate_read(MODEL_BAD)
    if bad == str(size):
        LAST_JUDGE[0] = 'model blacklisted (bad)'
        return None
    if bad:
        _gate_rm(MODEL_BAD)                       # a new file (different size) re-arms

    _gate_write(MODEL_PENDING, str(size))
    m = None
    err = None
    for attempt in range(2):
        # OpenMV N6 fw 5.0.0: the first ml.Model() of a boot raises
        # 'Failed to load network' and the second succeeds (bench 2026-09-13),
        # so one retry is normal, not a bad model.
        try:
            m = ml.Model(model_path)
            break
        except Exception as e:
            err = e
    if m is None:
        _gate_write(MODEL_BAD, str(size))
        _gate_rm(MODEL_PENDING)
        LAST_JUDGE[0] = 'load failed %r' % err
        return None
    _gate_rm(MODEL_PENDING)
    _model = m
    LAST_JUDGE[0] = 'ready'
    return m


def _shape_hw(model):
    s = model.input_shape
    if s and isinstance(s[0], (tuple, list)):
        s = s[0]
    # (1, h, w, c) or (1, h, w)
    return s[1], s[2]


def _at(attr, idx, n):
    if attr is None:
        return None
    if isinstance(attr, (list, tuple)):
        if idx < len(attr):
            return attr[idx]
        return attr[0] if attr else None
    return attr           # a single scalar shared by every output


def _animal_index(model, n):
    labels = getattr(model, 'labels', None)
    if labels:
        for i, lb in enumerate(labels):
            if str(lb).lower() == 'animal':
                return i
        return 0
    if n >= 2:
        return 1           # cameras/xiao_pantilt gate.cc: class 1 = animal
    return 0


def gate_score(img, x, y, side):
    """Crop (x,y,side,side) out of `img`, scale to the model's input, run
    predict, return the animal confidence 0..1, or None on any failure
    (fail open). Never raises."""
    if _model is None:
        LAST_JUDGE[0] = 'no model'
        return None
    t0 = time.ticks_ms()
    try:
        # fw 5.0: Image.crop() has no copy= keyword and scale() differs by
        # version; copy(roi=...) is the one form proven on the board, and
        # predict() scales any image to the model input itself.
        crop = img.copy(roi=(x, y, side, side), copy_to_fb=False)
        outputs = _model.predict([crop])
        # fw 5.0 (bench 2026-09-13): predict() returns dequantised float
        # arrays, one per output, shaped (1, n): [[p_not_animal, p_animal]].
        out = outputs[0]
        # ulab ndarrays on fw 5.0: hasattr(row, '__len__') is False for a
        # 1-D array even though len() works, so flatten via tolist() instead
        # of probing attributes (bench 2026-09-13: float(row) raised
        # 'invalid syntax for number').
        vals = out.tolist() if hasattr(out, 'tolist') else out
        while isinstance(vals, (list, tuple)) and len(vals) == 1 and isinstance(vals[0], (list, tuple)):
            vals = vals[0]
        if isinstance(vals, (list, tuple)) and vals and isinstance(vals[0], (list, tuple)):
            vals = vals[0]
        if not isinstance(vals, (list, tuple)):
            vals = [vals]
        n = len(vals)
        idx = _animal_index(_model, n) if n > 1 else 0
        raw = float(vals[idx])
        conf = raw
        if raw > 1.0 or raw < -0.001:
            # a raw int8 output (older firmware): dequantise like gate.cc
            scale = _at(getattr(_model, 'output_scale', None), idx, n)
            zp = _at(getattr(_model, 'output_zero_point', None), idx, n)
            if scale:
                conf = (raw - (zp or 0)) * scale
        if conf < 0.0:
            conf = 0.0
        elif conf > 1.0:
            conf = 1.0
        GATE_MS[0] = time.ticks_diff(time.ticks_ms(), t0)
        LAST_JUDGE[0] = 'conf %.3f (%dms)' % (conf, GATE_MS[0])
        return conf
    except Exception as e:
        GATE_MS[0] = time.ticks_diff(time.ticks_ms(), t0)
        LAST_JUDGE[0] = 'error %r' % e
        return None
