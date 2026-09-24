"""Scene coverage planning, deliberately separate from motor travel."""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ScanPlan:
    anchors_deg: tuple[float, ...]
    pan_min_deg: float
    pan_max_deg: float
    horizontal_fov_deg: float
    overlap_deg: float

    @property
    def scene_coverage_deg(self) -> float:
        return (self.pan_max_deg - self.pan_min_deg) + self.horizontal_fov_deg


def plan_scan(pan_min_deg: float = 0, pan_max_deg: float = 180,
              horizontal_fov_deg: float = 110, overlap_deg: float = 30) -> ScanPlan:
    """Return inclusive camera headings with at least ``overlap_deg`` overlap."""
    if pan_max_deg <= pan_min_deg or horizontal_fov_deg <= 0:
        raise ValueError("travel and field of view must be positive")
    if not 0 <= overlap_deg < horizontal_fov_deg:
        raise ValueError("overlap must be non-negative and smaller than the FOV")
    step = horizontal_fov_deg - overlap_deg
    span = pan_max_deg - pan_min_deg
    count = max(1, math.ceil(span / step))
    anchors = [pan_min_deg + step * i for i in range(count)]
    if anchors[-1] != pan_max_deg:
        anchors.append(pan_max_deg)
    # A float-safe unique/inclusive sequence for odd user configurations.
    result = tuple(dict.fromkeys(min(pan_max_deg, round(a, 8)) for a in anchors))
    return ScanPlan(result, pan_min_deg, pan_max_deg, horizontal_fov_deg, overlap_deg)
