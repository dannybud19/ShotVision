"""Aggregates shot results into running makes/misses/attempts/percentage,
plus a per-shot log for later debugging.
"""
from __future__ import annotations

from dataclasses import dataclass

from shotvision.shot_logic.state_machine import ShotOutcome, ShotResult


@dataclass
class ShotLogEntry:
    frame_idx: int
    outcome: ShotOutcome


class StatsTracker:
    def __init__(self):
        self.makes = 0
        self.misses = 0
        self.log: list[ShotLogEntry] = []

    def record(self, result: ShotResult) -> None:
        if result.outcome is ShotOutcome.MAKE:
            self.makes += 1
        else:
            self.misses += 1
        self.log.append(ShotLogEntry(result.frame_idx, result.outcome))

    @property
    def attempts(self) -> int:
        return self.makes + self.misses

    @property
    def percentage(self) -> float:
        if self.attempts == 0:
            return 0.0
        return 100.0 * self.makes / self.attempts

    def reset(self) -> None:
        self.makes = 0
        self.misses = 0
        self.log.clear()
