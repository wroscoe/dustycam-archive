"""Small hardware boundary; adapters may be synchronous or wrap these calls."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Frame:
    width: int
    height: int
    # Row-major 8-bit luminance.  Keeping this primitive makes the core
    # runnable on CPython and portable to constrained targets.
    pixels: bytes
    captured_at: float = 0.0

    def __post_init__(self) -> None:
        if len(self.pixels) != self.width * self.height:
            raise ValueError("frame pixels do not match dimensions")


@dataclass(frozen=True)
class CapturedPhoto:
    """Full-resolution still at the same stationary pose as a tracking frame."""
    width: int
    height: int
    pixels: bytes
    mime_type: str = "image/x-portable-graymap"
    captured_at: float = 0.0


class Camera(Protocol):
    def capture_tracking(self) -> Frame: ...
    def capture_photo(self) -> CapturedPhoto: ...


class PanDrive(Protocol):
    def pulse(self, direction: int, seconds: float) -> None:
        """Drive +1 or -1 for a bounded duration. No position is returned."""

    def home_to_stop(self, direction: int, max_seconds: float) -> bool:
        """Seek a mechanical datum/hard stop within a strict time bound.

        A hardware implementation must use a safe stall/current/limit-switch
        policy. It returns only whether the datum was reached, never an angle.
        """


class PhotoSink(Protocol):
    def save(self, photo: CapturedPhoto, metadata: dict) -> str: ...


class Clock(Protocol):
    def monotonic(self) -> float: ...
