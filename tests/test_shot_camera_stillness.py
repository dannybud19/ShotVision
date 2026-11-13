"""Unit tests for experiments/shot_camera_stillness.py's measurement functions.

Fake detections in memory (no cache, no model). At 30 fps a shot labelled
[40, 61] has the window frames 10..76 (67 frames): 30 frames of lead, 15 of tail.
"""
from dataclasses import dataclass

from experiments.shot_camera_stillness import shot_stillness, shot_window

FPS = 30.0
START, END = 40, 61
CLIP_FRAMES = 100


@dataclass
class _Det:
    class_name: str
    conf: float
    bbox: tuple


def _hoop(x: float = 100.0) -> _Det:
    return _Det("hoop", 0.9, (x, 100.0, x + 40.0, 140.0))  # width 40


def _stillness(dets):
    return shot_stillness(dets, START, END, FPS, rim_conf=0.6)


def test_shot_window_adds_lead_and_tail_and_clamps():
    assert shot_window(40, 61, FPS, 100) == (10, 77)  # 1.0 s before, 0.5 s after, end inclusive
    assert shot_window(5, 61, FPS, 100) == (0, 77)  # clamped at the clip start
    assert shot_window(40, 95, FPS, 100) == (10, 100)  # clamped at the clip end


def test_hoop_fixed_in_every_frame_is_still():
    dets = [[_hoop()] for _ in range(CLIP_FRAMES)]
    result = _stillness(dets)
    assert result["still"] is True
    assert result["hoop_seen"] == 1.0
    assert result["move_p95"] == 0.0


def test_hoop_moving_one_width_every_other_frame_is_not_still():
    # Odd frames jump by one hoop width; the window starts on an even frame
    # and has more even frames, so the median sits at the base position.
    dets = [[_hoop(140.0 if i % 2 else 100.0)] for i in range(CLIP_FRAMES)]
    result = _stillness(dets)
    assert result["move_p95"] >= 0.5
    assert result["still"] is False


def test_hoop_seen_in_half_the_window_is_not_still():
    # Hoop present in window frames 10..42 only (33 of 67, share 0.49).
    dets = [[_hoop()] if i <= 42 else [] for i in range(CLIP_FRAMES)]
    result = _stillness(dets)
    assert result["hoop_seen"] < 0.8
    assert result["move_p95"] == 0.0  # it is the hoop_seen rule that fails, not movement
    assert result["still"] is False
