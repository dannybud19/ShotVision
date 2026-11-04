from collections import deque
from pathlib import Path

import numpy as np
import pytest

from shotvision.config.settings import ModelConfig, TrackerConfig
from shotvision.detection.detector import BALL, HOOP, Detection, Detector
from shotvision.tracking.ball_tracker import BallTracker, TrajectoryPoint

BASKETBALL_WEIGHTS = Path("models/basketball_best.pt")


class _FakeDetector:
    """Stands in for the confirmation-threshold check `_update_trajectory`
    performs — only `.conf` is read."""
    def __init__(self, conf=0.15):
        self.conf = conf


def _make_tracker(buffer_len=5, confirm_conf=0.15, max_jump_ball_widths=3.0, max_gap_frames=15):
    tracker = BallTracker.__new__(BallTracker)
    tracker.trajectory = deque(maxlen=buffer_len)
    tracker.frame_idx = 0
    tracker.current_frame_ball_pos = None
    tracker.current_frame_ball_obs = None
    tracker.detector = _FakeDetector(confirm_conf)
    tracker.fps = 30.0  # the config is in seconds; these tests count frames at 30 fps
    tracker.cfg = TrackerConfig(max_jump_widths_per_s=max_jump_ball_widths * 30, max_gap_s=max_gap_frames / 30)
    tracker._candidate_history = deque()
    tracker.track_id = 0
    return tracker


def _step(tracker, detections):
    """Feed one frame's detections and advance the frame counter, as update() does."""
    tracker._update_trajectory(detections)
    tracker.frame_idx += 1


def test_first_ball_seen_appends_point():
    tracker = _make_tracker()
    _step(tracker, [Detection(BALL, 0.8, (10, 10, 20, 20))])

    assert len(tracker.trajectory) == 1
    assert tracker.trajectory[0].x == 15
    assert tracker.trajectory[0].y == 15
    assert tracker.current_frame_ball_pos == (15, 15)


def test_first_acquisition_picks_most_confident_ball():
    tracker = _make_tracker()
    _step(tracker, [Detection(BALL, 0.3, (0, 0, 10, 10)), Detection(BALL, 0.9, (100, 100, 110, 110))])
    assert tracker.current_frame_ball_pos == (105, 105)


def test_follows_nearest_ball_over_higher_confidence_distractor():
    tracker = _make_tracker()
    _step(tracker, [Detection(BALL, 0.8, (0, 0, 10, 10))])
    near = Detection(BALL, 0.4, (8, 8, 18, 18))
    distractor = Detection(BALL, 0.95, (300, 300, 310, 310))

    _step(tracker, [distractor, near])

    assert tracker.trajectory[-1].x == 13  # center of `near`, not the distractor


def test_fast_ball_moving_half_its_width_per_frame_is_kept_every_frame():
    # Regression for the ByteTrack bug: a ~23px ball moving (12, 10) px/frame
    # barely overlaps itself frame to frame, which IoU-based association
    # (ByteTrack) never confirmed - the whole flight was dropped. Nearest-
    # neighbour association must keep every frame.
    tracker = _make_tracker(buffer_len=20)
    for i in range(10):
        x, y = 500 + 12 * i, 100 + 10 * i
        _step(tracker, [Detection(BALL, 0.85, (x, y, x + 23, y + 23))])
        assert tracker.current_frame_ball_obs is not None
    assert len(tracker.trajectory) == 10


def test_rejects_implausible_jump_then_reacquires_after_gap():
    tracker = _make_tracker(max_jump_ball_widths=3.0, max_gap_frames=3)
    _step(tracker, [Detection(BALL, 0.8, (0, 0, 10, 10))])
    far = Detection(BALL, 0.9, (500, 500, 510, 510))  # 70 ball-widths away in 1 frame

    _step(tracker, [far])
    assert tracker.current_frame_ball_obs is None  # rejected as a stray detection
    assert len(tracker.trajectory) == 1

    for _ in range(3):  # followed ball unseen for longer than max_gap_frames
        _step(tracker, [])
    _step(tracker, [far])
    assert tracker.current_frame_ball_pos == (505, 505)  # re-acquired


def test_jump_allowance_scales_with_frames_since_last_seen():
    tracker = _make_tracker(max_jump_ball_widths=3.0)
    _step(tracker, [Detection(BALL, 0.8, (0, 0, 10, 10))])
    # 50px away: too far for 1 frame (limit 30px) but fine after a 2-frame
    # detection gap (3 frames elapsed -> limit 90px).
    _step(tracker, [])
    _step(tracker, [])
    _step(tracker, [Detection(BALL, 0.8, (50, 0, 60, 10))])
    assert tracker.current_frame_ball_pos == (55, 5)


def test_occlusion_frame_leaves_trajectory_untouched():
    tracker = _make_tracker()
    _step(tracker, [Detection(BALL, 0.5, (0, 0, 10, 10))])

    _step(tracker, [Detection(HOOP, 0.9, (0, 0, 50, 50))])

    assert len(tracker.trajectory) == 1  # unchanged
    # No ball this frame -> distinguishable from the stale trajectory point.
    assert tracker.current_frame_ball_pos is None


def test_current_frame_ball_pos_resets_between_calls():
    tracker = _make_tracker()
    _step(tracker, [Detection(BALL, 0.8, (0, 0, 10, 10))])
    assert tracker.current_frame_ball_pos == (5, 5)

    _step(tracker, [Detection(HOOP, 0.9, (0, 0, 50, 50))])
    assert tracker.current_frame_ball_pos is None


def test_low_confidence_ball_below_confirmation_threshold_is_ignored():
    # A ball detection between track_conf (the raw candidate floor) and conf (the
    # confirmation threshold) exists in the raw detections list but must not
    # become a confirmed observation.
    tracker = _make_tracker(confirm_conf=0.15)
    low_conf_ball = Detection(BALL, 0.12, (0, 0, 10, 10), )

    tracker._update_trajectory([low_conf_ball])

    assert tracker.current_frame_ball_pos is None
    assert tracker.current_frame_ball_obs is None
    assert len(tracker.trajectory) == 0


def test_ball_at_or_above_confirmation_threshold_is_confirmed():
    tracker = _make_tracker(confirm_conf=0.15)
    ball = Detection(BALL, 0.15, (0, 0, 10, 10), )

    tracker._update_trajectory([ball])

    assert tracker.current_frame_ball_pos == (5, 5)
    assert tracker.current_frame_ball_obs is not None


def test_current_frame_ball_obs_carries_bbox():
    tracker = _make_tracker()
    ball = Detection(BALL, 0.8, (10, 20, 30, 40), )

    tracker._update_trajectory([ball])

    obs = tracker.current_frame_ball_obs
    assert (obs.left, obs.top, obs.right, obs.bottom) == (10, 20, 30, 40)
    assert obs.center == (20, 30)


def test_trajectory_buffer_respects_maxlen():
    tracker = _make_tracker(buffer_len=3)
    for i in range(5):
        ball = Detection(BALL, 0.8, (i, i, i + 1, i + 1), )
        tracker._update_trajectory([ball])
    assert len(tracker.trajectory) == 3
    # Oldest points evicted; last appended point should be from i=4
    assert tracker.trajectory[-1].x == pytest.approx(4.5)


@pytest.mark.skipif(
    not BASKETBALL_WEIGHTS.exists(), reason="basketball checkpoint not downloaded"
)
def test_update_runs_end_to_end_on_blank_frame():
    model_cfg = ModelConfig(weights=str(BASKETBALL_WEIGHTS), conf=0.35, imgsz=640)
    detector = Detector(model_cfg, device="cpu")
    ball_tracker = BallTracker(detector, TrackerConfig(), buffer_len=10)

    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    detections = ball_tracker.update(blank_frame)

    assert isinstance(detections, list)
    assert ball_tracker.frame_idx == 1


def test_ball_decelerating_in_net_stays_on_the_same_track():
    # The prediction overshoots when the net stops the ball; the gate also
    # accepts detections near the last position (measured failure: the ball in
    # the net at conf 0.72 was rejected for 7 frames).
    tracker = _make_tracker(buffer_len=20)
    for i in range(4):  # falling fast, 15 px/frame
        _step(tracker, [Detection(BALL, 0.8, (100, 100 + 15 * i, 120, 120 + 15 * i))])
    for _ in range(3):  # caught in the net: barely moving
        _step(tracker, [Detection(BALL, 0.7, (100, 147, 120, 167))])
        assert tracker.current_frame_ball_obs is not None
    assert tracker.track_id == 0  # no switch happened


def test_strong_false_positive_cannot_take_a_recently_strong_track():
    # The ball blurs to a low score at the rim; a confident head-like box
    # elsewhere must not take the track while the ball was strong recently.
    tracker = _make_tracker(buffer_len=20)
    for i in range(3):
        _step(tracker, [Detection(BALL, 0.8, (100, 100 + 10 * i, 120, 120 + 10 * i))])
    _step(tracker, [Detection(BALL, 0.2, (100, 130, 120, 150))])
    _step(tracker, [])
    _step(tracker, [Detection(BALL, 0.7, (300, 300, 328, 328))])
    assert tracker.current_frame_ball_obs is None
    assert tracker.track_id == 0


def test_switch_to_another_object_starts_a_new_track_identity():
    tracker = _make_tracker(buffer_len=20)
    _step(tracker, [Detection(BALL, 0.2, (0, 0, 20, 20))])  # weak track (e.g. a head)
    _step(tracker, [Detection(BALL, 0.9, (300, 300, 320, 320))])
    assert tracker.current_frame_ball_pos == (310, 310)
    assert tracker.current_frame_ball_obs.track_id == 1


def test_weak_detection_only_continues_a_followed_ball():
    tracker = _make_tracker(buffer_len=20, confirm_conf=0.15)
    _step(tracker, [Detection(BALL, 0.05, (0, 0, 20, 20))])
    assert tracker.current_frame_ball_obs is None  # never starts a track

    for i in range(3):
        _step(tracker, [Detection(BALL, 0.8, (100, 100 + 10 * i, 120, 120 + 10 * i))])
    _step(tracker, [Detection(BALL, 0.05, (100, 130, 120, 150))])  # on the predicted path
    obs = tracker.current_frame_ball_obs
    assert obs is not None and obs.weak


def test_stationary_detection_is_ignored():
    tracker = _make_tracker(buffer_len=200)
    tracker.cfg = TrackerConfig(stationary_min_hits_s=5 / 30, stationary_min_span_s=4 / 30, stationary_window_s=50 / 30)
    for _ in range(6):
        _step(tracker, [Detection(BALL, 0.3, (50, 50, 70, 70))])
    _step(tracker, [Detection(BALL, 0.3, (50, 50, 70, 70))])
    assert tracker.current_frame_ball_obs is None
