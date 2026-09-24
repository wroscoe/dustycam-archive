"""led: the LED language. docs/camera_operation.md §10.

One `machine.LED(LED_NAME)` (LED_NAME is a board global, read lazily so the
board's value -- wherever it is bundled -- always wins); falls back to a
no-op LED when construction fails (no board, or the name doesn't exist), so
callers never need to guard.

`led_pattern(name)` is a short, blocking pattern (searching/contact/off are
not here: they are either instantaneous or need a caller-driven loop, so use
LedBlinker or led_pattern('solid')/('off')). `LedBlinker` is the
non-blocking one-LED-per-tick pattern for a wait loop (searching,
unprovisioned, recovery).
"""
import time

try:
    import machine
except ImportError:
    machine = None


class _NullLed:
    def on(self):
        pass

    def off(self):
        pass


def _get_led():
    name = globals().get('LED_NAME', 'LED_BLUE')
    if machine is not None:
        try:
            led = machine.LED(name)
            if led is not None and hasattr(led, 'on') and hasattr(led, 'off'):
                return led
        except Exception:
            pass
    return _NullLed()


def led_pattern(name, led=None):
    """Blocking. 'updated' 3x60/60ms, 'fail' 5x80/80ms, 'capture' one 50ms
    blink, 'off', 'solid' (steady on)."""
    led = led or _get_led()
    if name == 'updated':
        for _ in range(3):
            led.on()
            time.sleep_ms(60)
            led.off()
            time.sleep_ms(60)
    elif name == 'fail':
        for _ in range(5):
            led.on()
            time.sleep_ms(80)
            led.off()
            time.sleep_ms(80)
    elif name == 'capture':
        led.on()
        time.sleep_ms(50)
        led.off()
    elif name == 'off':
        led.off()
    elif name == 'solid':
        led.on()


class LedBlinker:
    """Non-blocking periodic pattern: call .tick() often from a wait loop.
    `period_ms`/`on_ms` alone gives one blink per period (e.g. 1000/120 =
    'searching', one blink a second; 2000/120 = 'recovery'). `double=True`
    gives two `on_ms` blinks separated by an `on_ms` gap near the start of
    each period ('unprovisioned')."""

    def __init__(self, period_ms, on_ms, double=False, led=None):
        self.period_ms = period_ms
        self.on_ms = on_ms
        self.double = double
        self.led = led or _get_led()
        self._t0 = time.ticks_ms()
        self._on = None

    def _want_on(self, elapsed):
        if self.double:
            return elapsed < self.on_ms or self.on_ms * 2 <= elapsed < self.on_ms * 3
        return elapsed < self.on_ms

    def tick(self):
        elapsed = time.ticks_diff(time.ticks_ms(), self._t0) % self.period_ms
        want = self._want_on(elapsed)
        if want != self._on:
            self._on = want
            if want:
                self.led.on()
            else:
                self.led.off()

    def stop(self):
        self._on = False
        self.led.off()
