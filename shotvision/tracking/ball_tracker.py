"""Frame-to-frame ball tracking: raw per-frame detection + nearest-neighbour
association, and a rolling trajectory buffer for the shot state machine and
HUD.

Why not ByteTrack (`model.track()`): ByteTrack associates boxes across frames
by IoU and only outputs *confirmed* tracks. A basketball in flight moves
~12-15 px/frame while its box is only ~20-25 px wide, so consecutive boxes
barely overlap — ByteTrack never confirms the track and silently drops the
ball for the entire flight, outputting it only once it slows down in the net.
Measured on the chonyy ground-truth clips: the detector found the ball above
the rim at conf 0.79-0.88 for ~12 straight frames per make, and `track()`
returned none of them (ball coverage ~20% of frames vs ~77% with raw
detections). That was the root cause of every "missing make".

So instead: run plain `predict()`, keep ball detections at or above the
confirmation threshold, and pick the one nearest the last confirmed position,
gated by a jump limit that scales with ball size and with the number of
frames since that position was seen (a fast ball that went undetected for a
few frames legitimately moves further).
"""
from __future__ import annotations

import math
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
        self.max_jump_ball_widths = tracker_config.max_jump_ball_widths
        self.max_gap_frames = tracker_config.max_gap_frames
        self.trajectory: deque[TrajectoryPoint] = deque(maxlen=buffer_len)
        self.frame_idx = 0
        # The ball for the frame just processed by update(), or None if no
        # ball was confirmed that frame — distinct from trajectory[-1], which
        # stays stale during an occlusion gap. `current_frame_ball_obs` (center
        # + bbox) is what the shot state machine consumes; the plain
        # `current_frame_ball_pos` center is kept for convenience.
        self.current_frame_ball_pos: tuple[float, float] | None = None
        self.current_frame_ball_obs: BallObservation | None = None

    def update(self, frame) -> list[Detection]:
        """Runs detection on one frame, returns all canonical detections
        (ball, hoop, person) at the raw candidate floor (`track_conf`), and
        updates the ball trajectory from the subset that clears the
        confirmation threshold."""
        results = self.detector.model.predict(
            frame,
            conf=self.detector.track_conf,
            imgsz=self.detector.imgsz,
            device=self.detector.device,
            verbose=False,
        )
        return self.ingest(self.detector.parse_result(results[0]))

    def ingest(self, detections: list[Detection]) -> list[Detection]:
        """Advance one frame using an already-computed detections list —
        update() without the inference, so recorded detections can be
        replayed (scripts/evaluate.py) through the exact same association."""
        self._update_trajectory(detections)
        self.frame_idx += 1
        return detections

    def _last_point(self) -> TrajectoryPoint | None:
        """The last confirmed position, if recent enough to associate with."""
        if not self.trajectory:
            return None
        last = self.trajectory[-1]
        if self.frame_idx - last.frame_idx > self.max_gap_frames:
            return None
        return last

    def _update_trajectory(self, detections: list[Detection]) -> None:
        self.current_frame_ball_pos = None
        self.current_frame_ball_obs = None
        # Only confidence >= the confirmation threshold counts as a real
        # observation; lower-confidence boxes (down to track_conf) are still
        # returned to callers (e.g. for hoop tracking) but never become ball
        # observations by themselves.
        candidates = [
            d for d in detections if d.class_name == BALL and d.conf >= self.detector.conf
        ]
        if not candidates:
            return  # occlusion frame: trajectory untouched

        last = self._last_point()
        if last is None:
            # Nothing recent to associate with — (re)acquire the most
            # confident ball.
            chosen = max(candidates, key=lambda d: d.conf)
        else:
            chosen = min(candidates, key=lambda d: math.dist(d.center, (last.x, last.y)))
            elapsed = self.frame_idx - last.frame_idx
            width = chosen.bbox[2] - chosen.bbox[0]
            max_jump = self.max_jump_ball_widths * width * max(1, elapsed)
            if math.dist(chosen.center, (last.x, last.y)) > max_jump:
                # Implausible jump from the ball we're following — more likely
                # a stray detection than the same ball. Treat this frame as
                # unobserved; once the followed ball has been gone longer than
                # max_gap_frames, _last_point() expires and we re-acquire.
                return

        x, y = chosen.center
        self.trajectory.append(TrajectoryPoint(self.frame_idx, x, y, chosen.conf))
        self.current_frame_ball_pos = (x, y)
        self.current_frame_ball_obs = BallObservation.from_bbox(chosen.bbox)

    def reset(self) -> None:
        self.trajectory.clear()
        self.frame_idx = 0
        self.current_frame_ball_pos = None
        self.current_frame_ball_obs = None
