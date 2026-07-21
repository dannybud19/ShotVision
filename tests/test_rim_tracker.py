import pytest

from shotvision.config.settings import ModelConfig, ShotLogicConfig
from shotvision.detection.detector import BALL, HOOP, Detection
from shotvision.shot_logic.rim_tracker import RimTracker


def _model_config(rim_conf=0.6):
    return ModelConfig(rim_conf=rim_conf)


def _shot_logic_config(**overrides):
    base = dict(
        inner_bound_shrink=0.15,
        rim_ema_alpha=0.5,  # fast-converging, easy to reason about in tests
        rim_lost_grace_frames=3,
        rim_size_jump_max_ratio=1.6,
    )
    base.update(overrides)
    return ShotLogicConfig(**base)


def _hoop(bbox, conf=0.9):
    return Detection(HOOP, conf, bbox, track_id=None)


def _tracker(**overrides):
    return RimTracker(_model_config(), _shot_logic_config(**overrides))


def test_no_rim_before_any_confirmed_hoop():
    tracker = _tracker()
    assert tracker.update([]) is None
    assert tracker.current_rim is None


def test_low_confidence_hoop_ignored():
    tracker = _tracker()
    result = tracker.update([_hoop((100, 50, 200, 70), conf=0.4)])  # below rim_conf=0.6
    assert result is None


def test_ball_detections_ignored():
    tracker = _tracker()
    result = tracker.update([Detection(BALL, 0.9, (10, 10, 20, 20))])
    assert result is None


def test_first_confident_hoop_produces_rim_immediately():
    tracker = _tracker()
    rim = tracker.update([_hoop((100, 50, 200, 70))])
    assert rim is not None
    assert rim.outer_left == 100
    assert rim.outer_right == 200
    assert rim.outer_top == 50
    assert rim.outer_bottom == 70


def test_ema_smooths_toward_new_readings_over_multiple_frames():
    tracker = _tracker(rim_ema_alpha=0.5)
    tracker.update([_hoop((100, 50, 200, 70))])
    # Second reading shifted right; alpha=0.5 -> halfway between old and new.
    rim = tracker.update([_hoop((120, 50, 220, 70))])
    assert rim.outer_left == pytest.approx(110)  # (100+120)/2
    assert rim.outer_right == pytest.approx(210)  # (200+220)/2


def test_occlusion_within_grace_keeps_last_rim():
    tracker = _tracker(rim_lost_grace_frames=3)
    tracker.update([_hoop((100, 50, 200, 70))])
    r1 = tracker.update([])  # miss 1
    r2 = tracker.update([])  # miss 2
    r3 = tracker.update([])  # miss 3 (== grace, still within tolerance)
    assert r1 is not None and r2 is not None and r3 is not None
    assert r1.outer_left == 100


def test_occlusion_beyond_grace_reverts_to_none():
    tracker = _tracker(rim_lost_grace_frames=2)
    tracker.update([_hoop((100, 50, 200, 70))])
    tracker.update([])  # miss 1
    tracker.update([])  # miss 2 (== grace)
    result = tracker.update([])  # miss 3 (> grace) -> lost
    assert result is None
    assert tracker.current_rim is None


def test_reacquires_fresh_after_being_lost():
    tracker = _tracker(rim_lost_grace_frames=1)
    tracker.update([_hoop((100, 50, 200, 70))])
    tracker.update([])  # miss 1 (== grace)
    tracker.update([])  # miss 2 (> grace) -> lost, resets EMA baseline
    # A very differently-positioned hoop should be accepted immediately,
    # not rejected as an implausible jump from stale history.
    rim = tracker.update([_hoop((500, 300, 560, 340))])
    assert rim is not None
    assert rim.outer_left == 500


def test_implausible_size_jump_rejected_as_if_missed():
    tracker = _tracker(rim_size_jump_max_ratio=1.6)
    tracker.update([_hoop((100, 50, 200, 70))])  # area = 100*20 = 2000
    # A box ~10x the area -- clearly not a gradual camera-motion size change.
    result = tracker.update([_hoop((0, 0, 1000, 200))])
    assert result is not None
    assert result.outer_left == 100  # unchanged: rejected reading, kept old rim


def test_plausible_size_change_is_accepted():
    tracker = _tracker(rim_size_jump_max_ratio=1.6, rim_ema_alpha=0.5)
    tracker.update([_hoop((100, 50, 200, 70))])  # area 2000
    # ~1.2x area -- gradual zoom/approach, within tolerance.
    rim = tracker.update([_hoop((100, 50, 210, 75))])  # area 110*25=2750, ratio 1.375
    assert rim.outer_right == pytest.approx(205)  # (200+210)/2, accepted+blended


def test_reset_clears_state():
    tracker = _tracker()
    tracker.update([_hoop((100, 50, 200, 70))])
    assert tracker.current_rim is not None

    tracker.reset()

    assert tracker.current_rim is None
    result = tracker.update([_hoop((500, 300, 560, 340))])
    assert result.outer_left == 500  # fresh acquisition, no stale-size rejection


def test_picks_highest_confidence_hoop_when_multiple_present():
    tracker = _tracker()
    dets = [
        _hoop((0, 0, 50, 20), conf=0.65),
        _hoop((100, 50, 200, 70), conf=0.95),
    ]
    rim = tracker.update(dets)
    assert rim.outer_left == 100
