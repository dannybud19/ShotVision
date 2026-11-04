"""Frame-rate independence: thresholds are seconds, converted per source fps."""
from collections import deque

import pytest

from shotvision.config.settings import (
    REFERENCE_FPS,
    ModelConfig,
    ShotLogicConfig,
    TrackerConfig,
    ema_alpha_at,
    load_config,
    per_frame,
    to_frames,
)
from shotvision.detection.detector import BALL, HOOP, Detection
from shotvision.shot_logic.rim import RimRegion
from shotvision.shot_logic.rim_tracker import RimTracker
from shotvision.shot_logic.state_machine import ResolutionReason, ShotStateMachine
from shotvision.tracking.ball_tracker import BallTracker


def test_defaults_convert_back_to_the_tuned_frame_counts_at_30_fps():
    cfg = load_config()
    sl, tr = cfg.shot_logic, cfg.tracker
    assert to_frames(sl.descent_min_s, 30) == 2
    assert to_frames(sl.prearm_max_missed_s, 30) == 1
    assert to_frames(sl.occlusion_grace_s, 30) == 12
    assert to_frames(sl.rim_occlusion_grace_s, 30) == 24
    assert to_frames(sl.shot_timeout_s, 30) == 90
    assert to_frames(sl.trajectory_buffer_s, 30) == 60
    assert to_frames(sl.crossing_fit_window_s, 30) == 4
    assert to_frames(sl.rim_lost_grace_s, 30) == 30
    assert to_frames(tr.max_gap_s, 30) == 15
    assert to_frames(tr.switch_stale_s, 30) == 8
    assert to_frames(tr.velocity_max_span_s, 30) == 8
    assert to_frames(tr.strength_window_s, 30) == 10
    assert to_frames(tr.stationary_window_s, 30) == 180
    assert to_frames(tr.stationary_min_span_s, 30) == 90
    assert to_frames(tr.stationary_min_hits_s, 30) == 25
    assert per_frame(tr.gate_growth_widths_per_s, 30) == 0.5
    assert per_frame(tr.max_jump_widths_per_s, 30) == 3.0


def test_ntsc_rate_keeps_the_same_frame_counts():
    cfg = load_config()
    assert to_frames(cfg.shot_logic.occlusion_grace_s, 29.97) == 12
    assert to_frames(cfg.shot_logic.shot_timeout_s, 29.97) == 90
    assert to_frames(cfg.shot_logic.descent_min_s, 29.97) == 2


def test_60_fps_doubles_frame_counts():
    cfg = load_config()
    assert to_frames(cfg.shot_logic.occlusion_grace_s, 60) == 24
    assert to_frames(cfg.shot_logic.descent_min_s, 60) == 4
    assert to_frames(cfg.tracker.max_gap_s, 60) == 30


def test_ema_alpha_is_exact_at_reference_and_keeps_time_constant_elsewhere():
    assert ema_alpha_at(0.25, REFERENCE_FPS) == 0.25
    a60 = ema_alpha_at(0.25, 60)
    # Two 60 fps steps decay old values as much as one 30 fps step.
    assert (1 - a60) ** 2 == pytest.approx(0.75)


def _rim():
    return RimRegion.from_points([(100, 50), (200, 50), (100, 70), (200, 70)], inner_bound_shrink=0.15)


def test_state_machine_occlusion_grace_is_the_same_duration_at_60_fps():
    cfg = ShotLogicConfig(align_tolerance_ratio=0.6, occlusion_grace_s=0.1, shot_timeout_s=5.0)
    for fps, grace_frames in ((30, 3), (60, 6)):
        sm = ShotStateMachine(_rim(), cfg, fps=fps)
        assert sm.occlusion_grace_frames == grace_frames
        arm = to_frames(cfg.descent_min_s, fps)
        frames = [(150, 5 + i) for i in range(arm)] + [None] * (grace_frames + 1)
        results = [r for i, p in enumerate(frames) if (r := sm.update(p, i)) is not None]
        assert len(results) == 1
        assert results[0].reason is ResolutionReason.MISS_OCCLUSION_GAP
        assert results[0].occlusion_frames_before_resolve == grace_frames + 1


def test_state_machine_arming_needs_the_same_descent_time_at_60_fps():
    cfg = ShotLogicConfig(align_tolerance_ratio=0.6)
    sm = ShotStateMachine(_rim(), cfg, fps=60)
    assert sm.descent_min_frames == 4
    for i in range(3):
        sm.update((150, 5 + i), i)
    assert sm.state.name == "IDLE"
    sm.update((150, 8), 3)
    assert sm.state.name == "ARMED"


class _FakeDetector:
    conf = 0.15


def _tracker(fps):
    t = BallTracker(_FakeDetector(), TrackerConfig(), buffer_len=20, fps=fps)
    return t


def test_ball_tracker_jump_gate_is_per_second_not_per_frame():
    # One prior point, no velocity: allowance = max_jump_widths_per_s / fps per
    # elapsed frame. 50 px away after 1 frame with a 10 px ball: 5 widths.
    # At 30 fps the limit is 3 widths (30 px): rejected. At 10 fps it is
    # 9 widths (90 px): accepted.
    for fps, accepted in ((30, False), (10, True)):
        t = _tracker(fps)
        t.ingest([Detection(BALL, 0.8, (0, 0, 10, 10))])
        t.ingest([Detection(BALL, 0.8, (50, 0, 60, 10))])
        assert (t.current_frame_ball_pos == (55, 5)) is accepted
        if not accepted:
            assert t.current_frame_ball_pos is None


def test_rim_tracker_lost_grace_is_the_same_duration_at_60_fps():
    sl = ShotLogicConfig(rim_lost_grace_s=0.1)
    hoop = [Detection(HOOP, 0.9, (100, 50, 200, 70))]
    for fps, grace in ((30, 3), (60, 6)):
        rt = RimTracker(ModelConfig(rim_conf=0.6), sl, fps=fps)
        rt.update(hoop)
        for _ in range(grace):
            assert rt.update([]) is not None
        assert rt.update([]) is None
