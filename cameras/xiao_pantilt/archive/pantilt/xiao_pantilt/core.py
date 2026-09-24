"""Safe image-only scan state machine with an explicit mechanical datum."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .interfaces import Camera, Clock, Frame, PanDrive, PhotoSink
from .planner import ScanPlan, plan_scan
from .registration import ZNCCRegistrar


class ScanState(str, Enum):
    UNHOMED = "unhomed"
    HOMING = "homing"
    OUTBOUND = "outbound"
    RETURNING = "returning"
    COMPLETE = "complete"
    ABORTED = "aborted"


@dataclass(frozen=True)
class ScanConfig:
    period_seconds: float = 180.0
    pan_min_deg: float = 0.0
    pan_max_deg: float = 180.0
    horizontal_fov_deg: float = 110.0
    overlap_deg: float = 30.0
    nominal_speed_deg_s: float = 20.0
    max_pulse_seconds: float = .6
    max_move_seconds: float = 12.0
    max_step_deg: float = 10.0
    max_measurements: int = 28
    max_zero_motion: int = 2
    minimum_confidence: float = .40
    tolerance_deg: float = 2.0
    home_max_seconds: float = 12.0
    recovery_max_pulses: int = 3
    cycle_max_seconds: float = 120.0


@dataclass
class Anchor:
    yaw_deg: float
    frame: Frame
    path: str


@dataclass
class ScanReport:
    state: ScanState
    photos: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    home_verified: bool = False
    failure: str | None = None
    plan: ScanPlan | None = None


class ScanController:
    def __init__(self, camera: Camera, drive: PanDrive, sink: PhotoSink, clock: Clock,
                 config: ScanConfig = ScanConfig(), registrar: ZNCCRegistrar | None = None) -> None:
        self.camera, self.drive, self.sink, self.clock, self.config = camera, drive, sink, clock, config
        self.registrar = registrar or ZNCCRegistrar(config.horizontal_fov_deg)
        self.state = ScanState.UNHOMED
        self._verified_home: Anchor | None = None

    def _photo(self, yaw: float, phase: str, report: ScanReport, frame: Frame | None = None) -> Anchor:
        frame = frame or self.camera.capture_tracking()
        meta = {"captured_at": self.clock.monotonic(), "logical_yaw_deg": yaw, "phase": phase,
                "position_source": "image_registration_only"}
        # Adapter contract: photo is captured at the same braked/settled pose
        # as ``frame``. Tracking images are never passed to the photo sink.
        path = self.sink.save(self.camera.capture_photo(), meta); report.photos.append(dict(meta, path=path))
        return Anchor(yaw, frame, path)

    def _pulse(self, direction: int, seconds: float, report: ScanReport, reason: str) -> bool:
        seconds = min(self.config.max_pulse_seconds, max(0.0, seconds))
        if seconds <= 0:
            return False
        self.drive.pulse(1 if direction > 0 else -1, seconds)
        report.events.append({"event": "pulse", "direction": 1 if direction > 0 else -1,
                              "seconds": seconds, "reason": reason})
        return True

    def _within_cycle_budget(self, started: float) -> bool:
        return self.clock.monotonic() - started <= self.config.cycle_max_seconds

    def _move_from_anchor(self, source: Anchor, target_yaw: float, report: ScanReport,
                          phase: str, started: float, target_anchor: Anchor | None = None) -> tuple[bool, Frame | None, str | None]:
        """Advance in short pulses; every pulse is followed by a visual measure."""
        desired = target_yaw - source.yaw_deg
        direction = 1 if desired >= 0 else -1
        max_time = abs(desired) / self.config.nominal_speed_deg_s
        if max_time > self.config.max_move_seconds:
            return False, None, "motion time bound exceeded"
        measured = 0.0; zero_motion = 0; commanded = 0.0
        last_frame: Frame | None = source.frame; previous = source.frame
        for attempt in range(self.config.max_measurements):
            if not self._within_cycle_budget(started):
                return False, None, "cycle time bound exceeded"
            error = desired - measured
            if abs(error) <= self.config.tolerance_deg:
                return True, last_frame, None
            # Never emit an unmeasured final command: the loop reserves a next
            # iteration/capture for every pulse.
            if attempt == self.config.max_measurements - 1:
                return False, None, "visual servo measurement bound exceeded"
            step_deg = min(self.config.max_step_deg, abs(error))
            duration = min(self.config.max_pulse_seconds, step_deg / self.config.nominal_speed_deg_s)
            if commanded + duration > self.config.max_move_seconds:
                return False, None, "cumulative motion time bound exceeded"
            self._pulse(1 if error > 0 else -1, duration,
                        report, phase + "-step")
            commanded += duration
            current = self.camera.capture_tracking()
            # Register only this one short step to the preceding tracking
            # frame. It has ~100° overlap, unlike a far-edge keyframe.
            local_lo, local_hi = ((-3.0, self.config.max_step_deg + 5.0) if error > 0
                                  else (-self.config.max_step_deg - 5.0, 3.0))
            r = self.registrar.register(previous, current, min_delta_deg=local_lo, max_delta_deg=local_hi)
            if r.confidence < self.config.minimum_confidence:
                # A fresh settled exposure handles transient leaf/lighting
                # changes without issuing another unmeasured motion command.
                retry = self.camera.capture_tracking()
                r = self.registrar.register(previous, retry, min_delta_deg=local_lo, max_delta_deg=local_hi)
                current = retry
            report.events.append({"event": "registration", "phase": phase, "attempt": attempt,
                                  "yaw_delta_deg": r.yaw_delta_deg, "confidence": r.confidence,
                                  "score": r.score})
            if r.confidence < self.config.minimum_confidence:
                return False, None, "low registration confidence"
            if abs(r.yaw_delta_deg) < .75 and abs(error) > self.config.tolerance_deg:
                zero_motion += 1
                if zero_motion >= self.config.max_zero_motion:
                    return False, None, "no visual motion (backlash/stall)"
            else:
                zero_motion = 0
            measured += r.yaw_delta_deg
            previous, last_frame = current, current
            # Once close, use the stored target keyframe as a drift check. It
            # is a correction/validation only, never the primary far-edge
            # tracker.
            if target_anchor is not None and abs(desired - measured) <= 14.0:
                key = self.registrar.register(target_anchor.frame, current,
                                              min_delta_deg=-14.0, max_delta_deg=14.0)
                report.events.append({"event": "keyframe_check", "phase": phase,
                                      "yaw_delta_deg": key.yaw_delta_deg,
                                      "confidence": key.confidence, "score": key.score})
                if key.confidence >= self.config.minimum_confidence:
                    measured = desired + key.yaw_delta_deg
        return False, None, "visual servo measurement bound exceeded"

    def _recover(self, anchors: list[Anchor], report: ScanReport) -> None:
        self.state = ScanState.RETURNING
        # On loss of visual lock, movement is reverse-only and bounded. A
        # successful match stops recovery; failures never justify outward drive.
        for count, anchor in enumerate(reversed(anchors)):
            if count >= self.config.recovery_max_pulses:
                break
            try:
                self._pulse(-1, self.config.max_pulse_seconds, report, "failure-recovery")
                frame = self.camera.capture_tracking()
                r = self.registrar.register(anchor.frame, frame, min_delta_deg=-25, max_delta_deg=25)
                report.events.append({"event": "recovery_registration", "yaw_deg": anchor.yaw_deg,
                                      "confidence": r.confidence, "score": r.score})
                if r.confidence >= self.config.minimum_confidence:
                    break
            except Exception as exc:
                report.events.append({"event": "recovery_adapter_exception", "error": type(exc).__name__})
                break
        try:
            executed = self.drive.home_to_stop(-1, self.config.home_max_seconds)
        except Exception as exc:
            executed = False
            report.events.append({"event": "recovery_adapter_exception", "error": type(exc).__name__})
        report.events.append({"event": "failure_home_command", "executed": executed,
                              "max_seconds": self.config.home_max_seconds})
        if executed:
            try:
                frame = self.camera.capture_tracking()
                dock = self.registrar.register(anchors[0].frame, frame, min_delta_deg=-10, max_delta_deg=10)
                report.events.append({"event": "failure_home_dock", "yaw_delta_deg": dock.yaw_delta_deg,
                                      "confidence": dock.confidence, "score": dock.score})
                if dock.confidence >= self.config.minimum_confidence and abs(dock.yaw_delta_deg) <= self.config.tolerance_deg:
                    report.home_verified = True
            except Exception as exc:
                report.events.append({"event": "recovery_adapter_exception", "error": type(exc).__name__})
        self.state = ScanState.ABORTED

    def run_cycle(self) -> ScanReport:
        self._active_report: ScanReport | None = None
        self._active_anchors: list[Anchor] = []
        try:
            return self._run_cycle()
        except Exception as exc:
            report = self._active_report or ScanReport(self.state)
            report.failure = "adapter exception: " + type(exc).__name__
            try:
                if self._active_anchors:
                    self._recover(self._active_anchors, report)
                else:
                    # Even if saving/capturing the first home frame failed, a
                    # bounded datum command prevents an unknown post-motion pose.
                    executed = self.drive.home_to_stop(-1, self.config.home_max_seconds)
                    report.events.append({"event": "failure_home_command", "executed": executed,
                                          "max_seconds": self.config.home_max_seconds})
            except Exception as recovery_exc:
                report.events.append({"event": "recovery_adapter_exception", "error": type(recovery_exc).__name__})
            self.state = ScanState.ABORTED
            report.state = self.state
            return report

    def _run_cycle(self) -> ScanReport:
        started = self.clock.monotonic()
        plan = plan_scan(self.config.pan_min_deg, self.config.pan_max_deg,
                         self.config.horizontal_fov_deg, self.config.overlap_deg)
        report = ScanReport(self.state, plan=plan)
        self._active_report = report
        warm_frame: Frame | None = None
        if self._verified_home is not None:
            warm_frame = self.camera.capture_tracking()
            warm = self.registrar.register(self._verified_home.frame, warm_frame,
                                           min_delta_deg=-8, max_delta_deg=8)
            report.events.append({"event": "warm_home_check", "yaw_delta_deg": warm.yaw_delta_deg,
                                  "confidence": warm.confidence, "score": warm.score})
            if warm.confidence < self.config.minimum_confidence or abs(warm.yaw_delta_deg) > self.config.tolerance_deg:
                warm_frame = None
        if warm_frame is None:
            self.state = ScanState.HOMING
            if not self.drive.home_to_stop(-1, self.config.home_max_seconds):
                self.state = ScanState.UNHOMED; report.state = self.state; report.failure = "mechanical datum command failed"
                return report
            report.events.append({"event": "homed", "max_seconds": self.config.home_max_seconds})
        if not self._within_cycle_budget(started):
            self.state = ScanState.ABORTED; report.state = self.state; report.failure = "cycle time bound exceeded"; return report
        self.state = ScanState.OUTBOUND
        anchors: list[Anchor] = [self._photo(plan.anchors_deg[0], "outbound", report, warm_frame)]
        self._active_anchors = anchors
        for target in plan.anchors_deg[1:]:
            ok, frame, why = self._move_from_anchor(anchors[-1], target, report, "outbound", started)
            if not ok or frame is None:
                report.failure = why; self._recover(anchors, report); report.state = self.state; return report
            anchors.append(self._photo(target, "outbound", report, frame))
        self.state = ScanState.RETURNING
        for target in reversed(anchors[:-1]):
            ok, frame, why = self._move_from_anchor(anchors[-1], target.yaw_deg, report, "return", started,
                                                     target_anchor=target)
            if not ok or frame is None:
                report.failure = "return: " + (why or "unknown"); self._recover(anchors, report); report.state = self.state; return report
            dock = self.registrar.register(target.frame, frame, min_delta_deg=-8, max_delta_deg=8)
            report.events.append({"event": "return_dock", "yaw_deg": target.yaw_deg,
                                  "yaw_delta_deg": dock.yaw_delta_deg, "confidence": dock.confidence,
                                  "score": dock.score})
            if dock.confidence < self.config.minimum_confidence or abs(dock.yaw_delta_deg) > self.config.tolerance_deg:
                report.failure = "return dock mismatch"; self._recover(anchors, report); report.state = self.state; return report
            anchors.pop()
        # A fresh direct docking comparison to the saved same-cycle home image
        # is mandatory before calling home verified.
        dock = self.camera.capture_tracking()
        r = self.registrar.register(anchors[0].frame, dock, min_delta_deg=-8, max_delta_deg=8)
        report.events.append({"event": "home_dock", "yaw_delta_deg": r.yaw_delta_deg,
                              "confidence": r.confidence, "score": r.score})
        if r.confidence < self.config.minimum_confidence or abs(r.yaw_delta_deg) > self.config.tolerance_deg:
            report.failure = "final home dock mismatch"; self._recover(anchors, report); report.state = self.state; return report
        report.home_verified = True; self._verified_home = anchors[0]
        self.state = ScanState.COMPLETE; report.state = self.state
        return report
