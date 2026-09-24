"""Pinhole-aware, pure-Python visual registration for overlapping views."""
from __future__ import annotations

from dataclasses import dataclass
import math

from .interfaces import Frame


@dataclass(frozen=True)
class Registration:
    yaw_delta_deg: float
    confidence: float
    pixel_shift: int
    score: float = 0.0


class ZNCCRegistrar:
    """Register rectilinear frames by evaluating candidate camera bearings.

    A candidate yaw is mapped through the pinhole projection, so wide-angle
    shifts are not incorrectly treated as constant pixel translations. The
    caller supplies a physically plausible signed window for control.
    """
    def __init__(self, horizontal_fov_deg: float, step_deg: float | None = None,
                 min_samples: int = 28, texture_floor: float = 5.0) -> None:
        self.horizontal_fov_deg = horizontal_fov_deg
        self.step_deg, self.min_samples, self.texture_floor = step_deg, min_samples, texture_floor

    @staticmethod
    def _profiles(frame: Frame) -> tuple[list[float], list[float]]:
        w, h, p = frame.width, frame.height, frame.pixels
        raw = [sum(p[y * w + x] for y in range(h)) / h for x in range(w)]
        grad = [abs(raw[min(w - 1, x + 1)] - raw[max(0, x - 1)]) for x in range(w)]
        return raw, grad

    @staticmethod
    def _zncc(a: list[float], b: list[float]) -> float:
        n = len(a)
        if n < 2:
            return -1.0
        ma, mb = sum(a) / n, sum(b) / n
        va = sum((v - ma) ** 2 for v in a); vb = sum((v - mb) ** 2 for v in b)
        if va <= 1e-9 or vb <= 1e-9:
            return -1.0
        return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)

    @staticmethod
    def _sample(values: list[float], x: float) -> float:
        lo = int(x); hi = min(len(values) - 1, lo + 1)
        return values[lo] * (hi - x) + values[hi] * (x - lo)

    def _x_to_bearing(self, x: float, width: int) -> float:
        focal = width / (2 * math.tan(math.radians(self.horizontal_fov_deg) / 2))
        return math.degrees(math.atan((x - (width - 1) / 2) / focal))

    def _bearing_to_x(self, bearing: float, width: int) -> float:
        focal = width / (2 * math.tan(math.radians(self.horizontal_fov_deg) / 2))
        return (width - 1) / 2 + focal * math.tan(math.radians(bearing))

    def register(self, reference: Frame, current: Frame, *, min_delta_deg: float | None = None,
                 max_delta_deg: float | None = None) -> Registration:
        if (reference.width, reference.height) != (current.width, current.height):
            raise ValueError("registration requires equal frame dimensions")
        w = reference.width; raw_a, grad_a = self._profiles(reference); raw_b, grad_b = self._profiles(current)
        mean = sum(raw_a) / w
        if math.sqrt(sum((v - mean) ** 2 for v in raw_a) / w) < self.texture_floor:
            return Registration(0.0, 0.0, 0, -1.0)
        # Reject a repeated visual signature by autocorrelation rather than a
        # brittle intensity-class count. This catches fences/periodic bark
        # while permitting low-contrast but non-repeating natural texture.
        periodic = max((self._zncc(raw_a[:-lag], raw_a[lag:])
                        for lag in range(8, min(w // 2, 64))), default=-1.0)
        if periodic > .985:
            return Registration(0.0, 0.0, 0, -1.0)
        extent = self.horizontal_fov_deg * .96
        lo = -extent if min_delta_deg is None else max(-extent, min_delta_deg)
        hi = extent if max_delta_deg is None else min(extent, max_delta_deg)
        if lo > hi:
            return Registration(0.0, 0.0, 0, -1.0)
        # Sub-pixel bearing candidates avoid accumulating the 0.69° sampling
        # quantisation error over many visual-servo increments.
        step = self.step_deg or min(.25, self.horizontal_fov_deg / w)
        candidates: list[tuple[float, float]] = []
        for i in range(int(math.floor((hi - lo) / step)) + 2):
            delta = min(hi, lo + i * step)
            a1: list[float] = []; b1: list[float] = []; a2: list[float] = []; b2: list[float] = []
            for x in range(1, w - 1):
                other_x = self._bearing_to_x(self._x_to_bearing(x, w) - delta, w)
                if 1 <= other_x < w - 1:
                    a1.append(raw_a[x]); b1.append(self._sample(raw_b, other_x))
                    a2.append(grad_a[x]); b2.append(self._sample(grad_b, other_x))
            if len(a1) >= self.min_samples:
                candidates.append((.72 * self._zncc(a1, b1) + .28 * self._zncc(a2, b2), delta))
        if not candidates:
            return Registration(0.0, 0.0, 0, -1.0)
        candidates.sort(reverse=True)
        score, delta = candidates[0]
        rival = next((s for s, d in candidates[1:] if abs(d - delta) >= 4.0), -1.0)
        margin = max(0.0, score - rival)
        confidence = max(0.0, min(1.0, ((score + 1) / 2) * min(1.0, .45 + margin * 5)))
        pixel_shift = round(self._bearing_to_x(-delta, w) - (w - 1) / 2)
        return Registration(delta, confidence, pixel_shift, score)
