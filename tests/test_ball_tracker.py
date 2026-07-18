from collections import deque
from pathlib import Path

import numpy as np
import pytest

from shotvision.config.settings import ModelConfig, TrackerConfig
from shotvision.detection.detector import BALL, HOOP, Detection, Detector
from shotvision.tracking.ball_tracker import BallTracker, TrajectoryPoint

BASKETBALL_WEIGHTS = Path("models/basketball_best.pt")


def _make_tracker(buffer_len=5):
    tracker = BallTracker.__new__(BallTracker)
    tracker.trajectory = deque(maxlen=buffer_len)
    tracker.frame_idx = 0
    tracker.active_ball_track_id = None
    tracker.current_frame_ball_pos = None
    return tracker


def test_first_ball_seen_sets_active_track_and_appends_point():
    tracker = _make_tracker()
    ball = Detection(BALL, 0.8, (10, 10, 20, 20), track_id=1)

    tracker._update_trajectory([ball])

    assert tracker.active_ball_track_id == 1
    assert len(tracker.trajectory) == 1
    assert tracker.trajectory[0].x == 15
    assert tracker.trajectory[0].y == 15
    assert tracker.current_frame_ball_pos == (15, 15)


def test_sticks_to_active_track_id_over_higher_confidence_new_ball():
    tracker = _make_tracker()
    tracker.active_ball_track_id = 1
    existing = Detection(BALL, 0.4, (0, 0, 10, 10), track_id=1)
    distractor = Detection(BALL, 0.9, (100, 100, 110, 110), track_id=99)

    tracker._update_trajectory([distractor, existing])

    assert tracker.active_ball_track_id == 1
    assert tracker.trajectory[-1].x == 5  # center of `existing`, not distractor


def test_occlusion_frame_leaves_trajectory_and_active_id_untouched():
    tracker = _make_tracker()
    tracker.active_ball_track_id = 1
    tracker.trajectory.append(TrajectoryPoint(0, 5, 5, 0.5))

    hoop_only = [Detection(HOOP, 0.9, (0, 0, 50, 50), track_id=None)]
    tracker._update_trajectory(hoop_only)

    assert tracker.active_ball_track_id == 1
    assert len(tracker.trajectory) == 1  # unchanged
    # No ball this frame -> distinguishable from the stale trajectory point.
    assert tracker.current_frame_ball_pos is None


def test_current_frame_ball_pos_resets_between_calls():
    tracker = _make_tracker()
    tracker._update_trajectory([Detection(BALL, 0.8, (0, 0, 10, 10), track_id=1)])
    assert tracker.current_frame_ball_pos == (5, 5)

    tracker._update_trajectory([Detection(HOOP, 0.9, (0, 0, 50, 50), track_id=None)])
    assert tracker.current_frame_ball_pos is None


def test_reacquires_new_track_id_after_active_one_disappears():
    tracker = _make_tracker()
    tracker.active_ball_track_id = 1
    new_ball = Detection(BALL, 0.6, (20, 20, 30, 30), track_id=2)

    tracker._update_trajectory([new_ball])

    assert tracker.active_ball_track_id == 2
    assert tracker.trajectory[-1].x == 25


def test_trajectory_buffer_respects_maxlen():
    tracker = _make_tracker(buffer_len=3)
    for i in range(5):
        ball = Detection(BALL, 0.8, (i, i, i + 1, i + 1), track_id=1)
        tracker._update_trajectory([ball])
    assert len(tracker.trajectory) == 3
    # Oldest points evicted; last appended point should be from i=4
    assert tracker.trajectory[-1].x == pytest.approx(4.5)


@pytest.mark.skipif(
    not BASKETBALL_WEIGHTS.exists(), reason="basketball checkpoint not downloaded"
)
def test_update_runs_bytetrack_end_to_end_on_blank_frame():
    model_cfg = ModelConfig(weights=str(BASKETBALL_WEIGHTS), conf=0.35, imgsz=640)
    detector = Detector(model_cfg, device="cpu")
    ball_tracker = BallTracker(detector, TrackerConfig(), buffer_len=10)

    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    detections = ball_tracker.update(blank_frame)

    assert isinstance(detections, list)
    assert ball_tracker.frame_idx == 1
