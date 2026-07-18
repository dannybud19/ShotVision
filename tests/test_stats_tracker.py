import pytest

from shotvision.shot_logic.state_machine import ShotOutcome, ShotResult
from shotvision.stats.tracker import StatsTracker


def test_starts_at_zero():
    tracker = StatsTracker()
    assert tracker.makes == 0
    assert tracker.misses == 0
    assert tracker.attempts == 0
    assert tracker.percentage == 0.0
    assert tracker.log == []


def test_records_make_and_miss_counts():
    tracker = StatsTracker()
    tracker.record(ShotResult(ShotOutcome.MAKE, frame_idx=10))
    tracker.record(ShotResult(ShotOutcome.MISS, frame_idx=20))
    tracker.record(ShotResult(ShotOutcome.MAKE, frame_idx=30))

    assert tracker.makes == 2
    assert tracker.misses == 1
    assert tracker.attempts == 3
    assert tracker.percentage == pytest.approx(200 / 3)


def test_log_preserves_order_and_frame_indices():
    tracker = StatsTracker()
    tracker.record(ShotResult(ShotOutcome.MAKE, frame_idx=10))
    tracker.record(ShotResult(ShotOutcome.MISS, frame_idx=20))

    assert [e.outcome for e in tracker.log] == [ShotOutcome.MAKE, ShotOutcome.MISS]
    assert [e.frame_idx for e in tracker.log] == [10, 20]


def test_reset_clears_everything():
    tracker = StatsTracker()
    tracker.record(ShotResult(ShotOutcome.MAKE, frame_idx=1))
    tracker.reset()

    assert tracker.makes == 0
    assert tracker.misses == 0
    assert tracker.log == []
