"""Unit tests for experiments/camera_profile.py's measurement functions.

These build fake detection lists in memory (no cache, no model) and check the
math only. The functions are duck-typed, so a minimal dataclass stands in for
the real Detection object.
"""
from dataclasses import dataclass

import pytest

from experiments.camera_profile import hoop_metrics, multi_ball_share


@dataclass
class _Det:
    class_name: str
    conf: float
    bbox: tuple


def test_static_hoop_has_zero_motion():
    hoop = _Det("hoop", 0.9, (100, 100, 140, 140))  # width 40, centre (120, 120)
    dets = [[hoop] for _ in range(10)]
    seen, move, ratio = hoop_metrics(dets, rim_conf=0.6)
    assert seen == 1.0
    assert move == 0.0
    assert ratio == pytest.approx(1.0)


def test_hoop_that_jumps_one_width():
    # Rest position (the median) in more than half the frames; the hoop jumps
    # by exactly one width in the rest. Because the median stays at the rest
    # position, the jumped frames sit one hoop width away and p95 is ~1.0.
    rest = _Det("hoop", 0.9, (100, 100, 140, 140))  # centre (120, 120), width 40
    jump = _Det("hoop", 0.9, (140, 100, 180, 140))  # centre (160, 120), one width right
    dets = [[rest] for _ in range(6)] + [[jump] for _ in range(4)]
    seen, move, ratio = hoop_metrics(dets, rim_conf=0.6)
    assert seen == 1.0
    assert move == pytest.approx(1.0, abs=0.01)


def test_two_separated_balls_every_frame():
    b1 = _Det("ball", 0.9, (0, 0, 10, 10))    # centre (5, 5), width 10
    b2 = _Det("ball", 0.9, (100, 0, 110, 10))  # centre (105, 5), width 10
    dets = [[b1, b2] for _ in range(5)]
    assert multi_ball_share(dets) == 1.0
