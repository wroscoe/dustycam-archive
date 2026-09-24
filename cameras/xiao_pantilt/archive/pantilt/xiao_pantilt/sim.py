"""Deterministic, dependency-free world/motor/camera simulation and CLI."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import math

from .core import ScanConfig, ScanController
from .interfaces import CapturedPhoto, Frame


class SimClock:
    def __init__(self) -> None: self.now = 0.0
    def monotonic(self) -> float: return self.now


class TexturedWorld:
    """Repeatable equirectangular luminance texture; no image libraries needed."""
    def __init__(self, width: int = 1440, height: int = 96, seed: int = 7) -> None:
        rng = random.Random(seed)
        self.width, self.height = width, height
        # Low-frequency random texture plus sparse landmarks yields a scene
        # that registers even with affine lighting changes.
        walk = rng.randrange(55, 185)
        profile = []
        for x in range(width):
            walk = max(15, min(225, walk + rng.randrange(-22, 23)))
            # Wide deterministic landmarks avoid a periodic or textureless
            # panorama and make horizontal registration well-conditioned.
            landmark = 55 if ((x * 37 + 13) % 211) < 9 else 0
            profile.append(max(0, min(255, walk + landmark)))
        rows = []
        for y in range(height):
            rows.append([max(0, min(255, v + ((x * 11 + y * 17) % 15 - 7)))
                         for x, v in enumerate(profile)])
        self.pixels = rows

    def render(self, yaw_deg: float, fov_deg: float, width: int, height: int,
               brightness: float = 1.0, moving_patch: bool = False) -> Frame:
        data = bytearray(width * height)
        focal = width / (2 * math.tan(math.radians(fov_deg) / 2))
        for y in range(height):
            sy = int(y * self.height / height)
            for x in range(width):
                # Rectilinear/pinhole projection: x is tangent of bearing,
                # not a linear equirectangular crop.
                angle = yaw_deg + math.degrees(math.atan((x - (width - 1) / 2) / focal))
                sx = int((angle % 360.0) * self.width / 360.0) % self.width
                value = self.pixels[sy][sx] * brightness
                # A small moving leaf/animal occluder: present but insufficient
                # to dominate the panorama signature.
                if moving_patch and width * .44 < x < width * .56 and height * .40 < y < height * .60:
                    value = 35 + ((x * 7 + y * 13) % 120)
                data[y * width + x] = max(0, min(255, round(value)))
        return Frame(width, height, bytes(data))


class SimPanDrive:
    """Unobserved motor: bias, reversal backlash, random-ish fixed slip, stops."""
    def __init__(self, clock: SimClock, speed_deg_s: float = 20.0, speed_bias: float = .88,
                 slip: float = .04, backlash_deg: float = 3.0, min_deg: float = 0,
                 max_deg: float = 180) -> None:
        self.clock, self.speed, self.bias, self.slip = clock, speed_deg_s, speed_bias, slip
        self.backlash, self.min_deg, self.max_deg = backlash_deg, min_deg, max_deg
        self.yaw_deg, self._last_direction = min(max_deg, max(min_deg, 47.0)), 0
        self.pulses: list[tuple[int, float]] = []

    def pulse(self, direction: int, seconds: float) -> None:
        direction = 1 if direction > 0 else -1
        travel = seconds * self.speed * self.bias * (1.0 - self.slip)
        if self._last_direction and direction != self._last_direction:
            travel = max(0.0, travel - self.backlash)
        self.yaw_deg = max(self.min_deg, min(self.max_deg, self.yaw_deg + direction * travel))
        self._last_direction = direction
        self.clock.now += seconds
        self.pulses.append((direction, seconds))

    def home_to_stop(self, direction: int, max_seconds: float) -> bool:
        if direction >= 0 or max_seconds <= 0:
            return False
        # This reports execution of the modeled datum command, not an angle.
        # It only succeeds if the bounded command actually reaches the stop.
        speed = self.speed * self.bias * (1 - self.slip)
        needed = max(0.0, self.yaw_deg - self.min_deg) / max(.001, speed)
        duration = min(max_seconds, needed)
        self.yaw_deg = max(self.min_deg, self.yaw_deg - duration * speed)
        self.clock.now += duration
        self._last_direction = -1
        self.pulses.append((-1, duration))
        return self.yaw_deg <= self.min_deg + 1e-9


class SimCamera:
    def __init__(self, world: TexturedWorld, drive: SimPanDrive, clock: SimClock,
                 fov_deg: float = 110, width: int = 160, height: int = 72,
                 lighting: tuple[float, ...] = (1.0, 0.78, 1.15, 0.9)) -> None:
        self.world, self.drive, self.clock = world, drive, clock
        self.fov, self.width, self.height, self.lighting = fov_deg, width, height, lighting
        self.capture_count = 0
        self._last_tracking: Frame | None = None
        self.fail_after: int | None = None
        self.fail_indices: set[int] = set()

    def capture_tracking(self) -> Frame:
        self.capture_count += 1
        if ((self.fail_after is not None and self.capture_count >= self.fail_after)
                or self.capture_count in self.fail_indices):
            self._last_tracking = Frame(self.width, self.height, bytes(self.width * self.height), self.clock.monotonic())
            return self._last_tracking
        light = self.lighting[(self.capture_count - 1) % len(self.lighting)]
        f = self.world.render(self.drive.yaw_deg, self.fov, self.width, self.height, light,
                              moving_patch=(self.capture_count % 5 == 0))
        self._last_tracking = Frame(f.width, f.height, f.pixels, self.clock.monotonic())
        return self._last_tracking

    # Compatibility convenience for direct simulator experiments.
    def capture(self) -> Frame:
        return self.capture_tracking()

    def capture_photo(self) -> CapturedPhoto:
        frame = self._last_tracking or self.capture_tracking()
        return CapturedPhoto(frame.width, frame.height, frame.pixels, captured_at=frame.captured_at)


class DirectoryPhotoSink:
    def __init__(self, directory: str | Path, actual_yaw_provider=None) -> None:
        self.directory = Path(directory); self.directory.mkdir(parents=True, exist_ok=True); self.count = 0
        self.actual_yaw_provider, self.saved = actual_yaw_provider, []
    def save(self, frame: CapturedPhoto, metadata: dict) -> str:
        stem = f"{self.count:03d}_{metadata['phase']}_{metadata['logical_yaw_deg']:06.1f}"
        image = self.directory / (stem + ".pgm")
        image.write_bytes(f"P5\n{frame.width} {frame.height}\n255\n".encode() + frame.pixels)
        meta = self.directory / (stem + ".json")
        disk_meta = dict(metadata)
        if self.actual_yaw_provider is not None:
            disk_meta["simulator_actual_yaw_deg"] = self.actual_yaw_provider()
        meta.write_text(json.dumps(disk_meta, indent=2, sort_keys=True) + "\n")
        self.saved.append(disk_meta)
        self.count += 1
        return str(image)


def run_simulation(output: str | Path, seed: int = 7, fail_after: int | None = None) -> tuple[dict, SimPanDrive]:
    clock = SimClock(); world = TexturedWorld(seed=seed); drive = SimPanDrive(clock)
    camera = SimCamera(world, drive, clock); camera.fail_after = fail_after
    sink = DirectoryPhotoSink(output, actual_yaw_provider=lambda: drive.yaw_deg)
    controller = ScanController(camera, drive, sink, clock, ScanConfig())
    report = controller.run_cycle()
    summary = {"state": report.state.value, "photos": report.photos, "events": report.events,
               "home_verified": report.home_verified, "failure": report.failure,
               "actual_final_yaw_deg": drive.yaw_deg, "scene_coverage_deg": report.plan.scene_coverage_deg if report.plan else None}
    Path(output).mkdir(parents=True, exist_ok=True)
    (Path(output) / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary, drive


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic XIAO pan-camera reference simulation")
    parser.add_argument("--output", default="xiao_pantilt_sim_output")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--fail-after", type=int)
    args = parser.parse_args(argv)
    summary, _ = run_simulation(args.output, args.seed, args.fail_after)
    print(json.dumps({k: summary[k] for k in ("state", "home_verified", "failure", "actual_final_yaw_deg", "scene_coverage_deg")}, indent=2))
    return 0 if summary["state"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
