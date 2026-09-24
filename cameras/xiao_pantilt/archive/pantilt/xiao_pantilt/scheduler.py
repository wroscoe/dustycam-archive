"""Phase-locked, coalescing scheduler for periodic scan cycles."""
from __future__ import annotations


class PhaseLockedScheduler:
    def __init__(self, period_seconds: float = 180.0, epoch: float = 0.0) -> None:
        if period_seconds <= 0:
            raise ValueError("period_seconds must be positive")
        self.period_seconds = period_seconds
        self.next_due = epoch
        self.running = False
        self.coalesced = 0

    def due(self, now: float) -> bool:
        if now < self.next_due:
            return False
        skipped = int((now - self.next_due) // self.period_seconds)
        self.next_due += (skipped + 1) * self.period_seconds
        if self.running:
            self.coalesced += 1
            return False
        self.running = True
        return True

    def complete(self, now: float | None = None) -> None:
        self.running = False
        # A synchronous scan may itself run across one or more periods. Do not
        # immediately launch a stale queued slot; preserve the original phase.
        if now is not None and now >= self.next_due:
            skipped = int((now - self.next_due) // self.period_seconds)
            self.next_due += (skipped + 1) * self.period_seconds
