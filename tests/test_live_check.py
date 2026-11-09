"""Tests for experiments/live_check.py. No model, no files, no cache."""
import importlib
import sys

from experiments.live_check import compare_results
from shotvision.shot_logic.state_machine import ShotOutcome, ShotResult


def _shot(outcome: str, frame: int) -> ShotResult:
    return ShotResult(outcome=ShotOutcome[outcome], frame_idx=frame)


def test_importing_live_check_does_not_import_ultralytics():
    sys.modules.pop("ultralytics", None)
    sys.modules.pop("experiments.live_check", None)
    importlib.import_module("experiments.live_check")
    assert "ultralytics" not in sys.modules


def test_identical_lists_have_no_unmatched_shots():
    shots = [_shot("MAKE", 100), _shot("MISS", 400)]
    pairs, live_only, replay_only = compare_results(shots, list(shots), tol_frames=12)
    assert len(pairs) == 2
    assert live_only == [] and replay_only == []


def test_shots_within_tolerance_pair_and_beyond_do_not():
    pairs, live_only, replay_only = compare_results([_shot("MAKE", 103)], [_shot("MAKE", 100)], tol_frames=12)
    assert len(pairs) == 1 and not live_only and not replay_only
    pairs, live_only, replay_only = compare_results([_shot("MAKE", 120)], [_shot("MAKE", 100)], tol_frames=12)
    assert pairs == []
    assert len(live_only) == 1 and len(replay_only) == 1


def test_different_outcomes_at_the_same_frame_do_not_pair():
    pairs, live_only, replay_only = compare_results([_shot("MAKE", 100)], [_shot("MISS", 100)], tol_frames=12)
    assert pairs == []
    assert len(live_only) == 1 and len(replay_only) == 1
