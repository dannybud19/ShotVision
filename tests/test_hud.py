from collections import deque

import numpy as np

from shotvision.overlay.hud import BLUE, GREEN, PURPLE, RED, Hud, RESULT_FLASH_FRAMES
from shotvision.shot_logic.rim import RimRegion
from shotvision.shot_logic.state_machine import ShotOutcome, ShotState
from shotvision.stats.tracker import StatsTracker
from shotvision.tracking.ball_tracker import TrajectoryPoint


def test_armed_state_is_purple_regardless_of_history():
    hud = Hud()
    assert hud.trajectory_color(ShotState.ARMED, frame_idx=5) == PURPLE


def test_idle_with_no_history_is_blue():
    hud = Hud()
    assert hud.trajectory_color(ShotState.IDLE, frame_idx=5) == BLUE


def test_make_flashes_green_within_window_then_reverts_to_blue():
    hud = Hud()
    hud.note_result(ShotOutcome.MAKE, frame_idx=10)

    assert hud.trajectory_color(ShotState.IDLE, frame_idx=10) == GREEN
    assert hud.trajectory_color(ShotState.IDLE, frame_idx=10 + RESULT_FLASH_FRAMES) == GREEN
    assert hud.trajectory_color(ShotState.IDLE, frame_idx=10 + RESULT_FLASH_FRAMES + 1) == BLUE


def test_miss_flashes_red_within_window():
    hud = Hud()
    hud.note_result(ShotOutcome.MISS, frame_idx=10)
    assert hud.trajectory_color(ShotState.IDLE, frame_idx=15) == RED


def test_new_armed_shot_overrides_flash_color():
    hud = Hud()
    hud.note_result(ShotOutcome.MAKE, frame_idx=10)
    # A new shot arming immediately after should show purple, not green.
    assert hud.trajectory_color(ShotState.ARMED, frame_idx=11) == PURPLE


def test_draw_runs_without_error_on_blank_frame():
    hud = Hud()
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    rim = RimRegion.from_points([(100, 50), (200, 50), (100, 70), (200, 70)], inner_bound_shrink=0.15)
    trajectory = deque(
        [TrajectoryPoint(0, 150, 10, 0.9), TrajectoryPoint(1, 150, 20, 0.85)], maxlen=60
    )
    stats = StatsTracker()

    out = hud.draw(frame, rim, trajectory, ShotState.ARMED, stats, frame_idx=1, conf=0.35)

    assert out is frame
    assert frame.any()  # something was drawn (non-zero pixels)


def test_draw_handles_missing_rim_and_empty_trajectory():
    hud = Hud()
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    stats = StatsTracker()

    out = hud.draw(frame, None, deque(), ShotState.IDLE, stats, frame_idx=0, conf=0.35)
    assert out is frame
