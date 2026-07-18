"""Live overlay: calibrated rim box, ball trajectory trail (color-coded by
shot state), and a running makes/misses/percentage counter.

Color convention adapted from chonyy/AI-basketball-analysis's shot
visualization (convention only — no code from that project is used here;
it depends on CUDA/OpenPose and a Faster R-CNN detector we deliberately
avoided in favor of our own YOLO+ByteTrack pipeline):
  blue   = ball tracked normally, no shot in progress
  purple = shot in progress / undetermined
  green  = most recent shot was a MAKE
  red    = most recent shot was a MISS
"""
from __future__ import annotations

from collections import deque

import cv2

from shotvision.shot_logic.rim import RimRegion
from shotvision.shot_logic.state_machine import ShotOutcome, ShotState
from shotvision.stats.tracker import StatsTracker
from shotvision.tracking.ball_tracker import TrajectoryPoint

# BGR tuples (OpenCV convention).
BLUE = (255, 0, 0)
PURPLE = (200, 0, 160)
GREEN = (0, 200, 0)
RED = (0, 0, 220)
YELLOW = (0, 220, 220)
WHITE = (255, 255, 255)

# How long to keep flashing the make/miss color after a shot resolves
# before the trajectory reverts to the normal "tracked" color.
RESULT_FLASH_FRAMES = 30


class Hud:
    def __init__(self):
        self._last_outcome: ShotOutcome | None = None
        self._last_outcome_frame: int | None = None

    def note_result(self, outcome: ShotOutcome, frame_idx: int) -> None:
        self._last_outcome = outcome
        self._last_outcome_frame = frame_idx

    def trajectory_color(self, state: ShotState, frame_idx: int) -> tuple[int, int, int]:
        if state is ShotState.ARMED:
            return PURPLE
        if (
            self._last_outcome is not None
            and self._last_outcome_frame is not None
            and frame_idx - self._last_outcome_frame <= RESULT_FLASH_FRAMES
        ):
            return GREEN if self._last_outcome is ShotOutcome.MAKE else RED
        return BLUE

    def draw(
        self,
        frame,
        rim: RimRegion | None,
        trajectory: deque[TrajectoryPoint],
        state: ShotState,
        stats: StatsTracker,
        frame_idx: int,
        conf: float,
    ):
        if rim is not None:
            self._draw_rim(frame, rim)

        color = self.trajectory_color(state, frame_idx)
        self._draw_trajectory(frame, trajectory, color)
        self._draw_counter(frame, stats, state, conf)
        return frame

    def _draw_rim(self, frame, rim: RimRegion) -> None:
        cv2.rectangle(
            frame,
            (int(rim.outer_left), int(rim.outer_top)),
            (int(rim.outer_right), int(rim.outer_bottom)),
            YELLOW,
            2,
        )
        cv2.line(
            frame,
            (int(rim.inner_left), int(rim.outer_top)),
            (int(rim.inner_left), int(rim.outer_bottom)),
            YELLOW,
            1,
        )
        cv2.line(
            frame,
            (int(rim.inner_right), int(rim.outer_top)),
            (int(rim.inner_right), int(rim.outer_bottom)),
            YELLOW,
            1,
        )

    def _draw_trajectory(self, frame, trajectory: deque[TrajectoryPoint], color) -> None:
        points = [(int(p.x), int(p.y)) for p in trajectory]
        for i in range(1, len(points)):
            cv2.line(frame, points[i - 1], points[i], color, 2)
        if points:
            cv2.circle(frame, points[-1], 5, color, -1)

    def _draw_counter(self, frame, stats: StatsTracker, state: ShotState, conf: float) -> None:
        lines = [
            f"Makes: {stats.makes}  Misses: {stats.misses}  Pct: {stats.percentage:.0f}%",
            f"State: {state.name}  Conf: {conf:.2f}",
        ]
        y = 25
        for line in lines:
            cv2.putText(frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 2, cv2.LINE_AA)
            y += 25
