"""Frame-to-frame ball tracking via Ultralytics' built-in ByteTrack.

Calls Detector.model.track(...) (instead of .predict()) so detections carry
persistent track IDs across frames, and maintains a rolling trajectory
buffer of the ball's positions for the shot state machine and HUD.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from shotvision.config.settings import TrackerConfig
from shotvision.detection.detector import BALL, Detection, Detector
from shotvision.shot_logic.state_machine import BallObservation


@dataclass
class TrajectoryPoint:
    frame_idx: int
    x: float
    y: float
    conf: float


class BallTracker:
    def __init__(self, detector: Detector, tracker_config: TrackerConfig, buffer_len: int = 60):
        self.detector = detector
        self.tracker_yaml = tracker_config.tracker_yaml
        self.trajectory: deque[TrajectoryPoint] = deque(maxlen=buffer_len)
        self.frame_idx = 0
        self.active_ball_track_id: int | None = None
        # The ball for the frame just processed by update(), or None if no
        # ball was detected that frame — distinct from trajectory[-1], which
        # stays stale during an occlusion gap. `current_frame_ball_obs` (center
        # + bbox) is what the shot state machine consumes; the plain
        # `current_frame_ball_pos` center is kept for convenience.
        self.current_frame_ball_pos: tuple[float, float] | None = None
        self.current_frame_ball_obs: BallObservation | None = None

    def update(self, frame) -> list[Detection]:
        """Runs tracking on one frame, returns all canonical detections
        (ball, hoop, person) at the tracker's low recovery floor, and
        updates the ball trajectory buffer from the subset that clears the
        confirmation threshold."""
        results = self.detector.model.track(
            frame,
            persist=True,
            tracker=self.tracker_yaml,
            # Feed ByteTrack the full low/high recovery range it's designed
            # for (see ModelConfig.track_conf) — filtering to the stricter
            # confirmation threshold here would starve its low-confidence
            # recovery of exactly the partially-occluded-ball boxes it
            # exists to use. We still only treat detections >= self.conf as
            # confirmed observations, below.
            conf=self.detector.track_conf,
            imgsz=self.detector.imgsz,
            device=self.detector.device,
            verbose=False,
        )
        detections = self.detector.parse_result(results[0])
        self._update_trajectory(detections)
        self.frame_idx += 1
        return detections

    def _update_trajectory(self, detections: list[Detection]) -> None:
        self.current_frame_ball_pos = None
        self.current_frame_ball_obs = None
        # Only confidence >= the confirmation threshold counts as a real
        # observation — the lower track_conf floor above exists purely to
        # help ByteTrack's internal association, not to feed the state
        # machine noisier low-confidence boxes directly.
        ball_detections = [
            d for d in detections if d.class_name == BALL and d.conf >= self.detector.conf
        ]
        if not ball_detections:
            return  # occlusion frame: leave trajectory/active id untouched

        chosen: Detection | None = None
        if self.active_ball_track_id is not None:
            chosen = next(
                (d for d in ball_detections if d.track_id == self.active_ball_track_id),
                None,
            )
        if chosen is None:
            # Lost the active track (or none yet) — adopt the most
            # confident ball detection this frame.
            chosen = max(ball_detections, key=lambda d: d.conf)
            self.active_ball_track_id = chosen.track_id

        x, y = chosen.center
        self.trajectory.append(TrajectoryPoint(self.frame_idx, x, y, chosen.conf))
        self.current_frame_ball_pos = (x, y)
        self.current_frame_ball_obs = BallObservation.from_bbox(chosen.bbox)

    def reset(self) -> None:
        self.trajectory.clear()
        self.active_ball_track_id = None
        self.frame_idx = 0
        self.current_frame_ball_pos = None
        self.current_frame_ball_obs = None
