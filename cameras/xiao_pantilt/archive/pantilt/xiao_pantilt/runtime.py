"""Minimal polling service that binds the phase-locked schedule to scans."""
from __future__ import annotations

from .core import ScanController, ScanReport
from .scheduler import PhaseLockedScheduler


class ScanService:
    """Call :meth:`poll` from a host event loop or a device task.

    Missed periods are coalesced, never queued: after a long scan the next
    capture remains aligned to the original three-minute wall-clock phase.
    """
    def __init__(self, controller: ScanController, scheduler: PhaseLockedScheduler | None = None) -> None:
        self.controller = controller
        self.scheduler = scheduler or PhaseLockedScheduler(controller.config.period_seconds)
        self.last_report: ScanReport | None = None

    def poll(self) -> ScanReport | None:
        if not self.scheduler.due(self.controller.clock.monotonic()):
            return None
        try:
            self.last_report = self.controller.run_cycle()
            return self.last_report
        finally:
            self.scheduler.complete(self.controller.clock.monotonic())
