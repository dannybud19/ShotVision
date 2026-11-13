"""Tests for experiments/release_moment.py's find_release.

Synthetic ball paths only (no cache, no model). 30 fps, ball width 20 px.
Frames 0-9: the ball moves with the hands. From frame 10: a parabola,
x = 200 + 15 t, y = 500 - 22 t + 0.9 t^2 for t = 0..24.

Fixture note (owner-approved, PLAN_5 A2.3): the arc's highest point is
y = 365.6, so the rim for the arc tests is (500, 450, 60), below the apex,
and the ball comes back down through rim height near x = 528. The "no apex"
test keeps its own rim at (500, 300, 60) and a path that never goes above it.
"""
from experiments.release_moment import find_release

FPS = 30.0
BALL_W = 20.0
ARC_RIM = (500.0, 450.0, 60.0)
HIGH_RIM = (500.0, 300.0, 60.0)


def _hand_points() -> list[tuple]:
    pts = []
    for f in range(10):
        wobble = 2.0 if f % 2 == 0 else -2.0
        y = 520.0 - 20.0 * f / 9.0 + wobble  # rises slowly from 520 to 500
        pts.append((f, 200.0, y, BALL_W))
    return pts


def _arc_points() -> list[tuple]:
    return [(10 + t, 200.0 + 15.0 * t, 500.0 - 22.0 * t + 0.9 * t * t, BALL_W) for t in range(25)]


def test_clean_arc_release_is_found_near_frame_10():
    result = find_release(_hand_points() + _arc_points(), ARC_RIM, FPS)
    assert result is not None and result["release_frame"] is not None, result
    assert abs(result["release_frame"] - 10) <= 2, result
    assert result["apex_frame"] == 22  # the arc's highest point is at t = 12
    assert result["flight_frames"] == result["apex_frame"] - result["release_frame"]


def test_gap_in_the_arc_still_finds_the_release():
    pts = [p for p in _hand_points() + _arc_points() if not 12 <= p[0] <= 14]
    result = find_release(pts, ARC_RIM, FPS)
    assert result is not None and result["release_frame"] is not None, result
    assert abs(result["release_frame"] - 10) <= 2, result


def test_too_few_points_returns_none():
    assert find_release(_arc_points()[:4], ARC_RIM, FPS) is None


def test_path_that_never_rises_above_the_rim_has_no_apex():
    pts = [(f, 480.0 + 4.0 * (f % 3), 400.0 + 2.0 * f, BALL_W) for f in range(12)]  # y >= 400 > 300
    result = find_release(pts, HIGH_RIM, FPS)
    assert result is not None
    assert result["release_frame"] is None
    assert result["reason"] == "no_apex"
