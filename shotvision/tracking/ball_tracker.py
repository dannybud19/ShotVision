"""Frame-to-frame ball tracking: raw per-frame detection + gated
nearest-neighbour association, and a rolling trajectory buffer for the shot
state machine and HUD.

Why not ByteTrack (`model.track()`): ByteTrack associates boxes across frames
by IoU and only outputs *confirmed* tracks. A basketball in flight moves
~12-15 px/frame while its box is only ~20-25 px wide, so consecutive boxes
barely overlap — ByteTrack never confirms the track and silently drops the
ball for the entire flight, outputting it only once it slows down in the net.
Measured on the chonyy ground-truth clips: the detector found the ball above
the rim at conf 0.79-0.88 for ~12 straight frames per make, and `track()`
returned none of them. That was the root cause of every "missing make".

Association rules, per frame (all thresholds in TrackerConfig):
  1. Candidates are ball detections with conf >= the confirmation threshold,
     minus *stationary* ones — a spot that has kept producing detections for
     seconds (a round sign on the hoop pole was detected 219 times in one
     clip). A ball in play doesn't sit still that long.
  2. If a ball is being followed, predict where it should be now from its
     recent velocity and accept the nearest candidate inside a gate around
     that prediction (gate grows with frames since last seen).
  3. A candidate outside the gate is accepted only if it is confident and
     the followed ball was itself weak, or has been unseen for
     switch_stale_frames (longer than a normal motion-blur gap at the rim) — otherwise a shooter's
     head (conf ~0.2) a few ball-widths away can hijack the track mid-shot
     and fake a "ball below the rim", which is exactly what produced wrong
     MISS calls on measured footage.
  4. After max_gap_frames without an accepted detection, re-acquire the most
     confident candidate.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

from shotvision.config.settings import TrackerConfig
from shotvision.detection.detector import BALL, Detection, Detector
from shotvision.shot_logic.state_machine import BallObservation

# Velocity is only estimated from two confirmed points this close in time.
_VELOCITY_MAX_SPAN_FRAMES = 3


@dataclass
class TrajectoryPoint:
    frame_idx: int
    x: float
    y: float
    conf: float
    width: float = 0.0  # bbox width; sizes the association gate


def _width(d: Detection) -> float:
    return d.bbox[2] - d.bbox[0]


class BallTracker:
    def __init__(self, detector: Detector, tracker_config: TrackerConfig, buffer_len: int = 60):
        self.detector = detector
        self.cfg = tracker_config
        self.trajectory: deque[TrajectoryPoint] = deque(maxlen=buffer_len)
        self.frame_idx = 0
        # Every confirmed-confidence ball candidate seen recently, chosen or
        # not: (frame_idx, x, y). Feeds the stationary-object filter.
        self._candidate_history: deque[tuple[int, float, float]] = deque()
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

    # --- association helpers -------------------------------------------

    def _last_point(self) -> TrajectoryPoint | None:
        """The last accepted position, if recent enough to associate with."""
        if not self.trajectory:
            return None
        last = self.trajectory[-1]
        if self.frame_idx - last.frame_idx > self.cfg.max_gap_frames:
            return None
        return last

    def _velocity(self) -> tuple[float, float] | None:
        if len(self.trajectory) < 2:
            return None
        p0, p1 = self.trajectory[-2], self.trajectory[-1]
        span = p1.frame_idx - p0.frame_idx
        if span <= 0 or span > _VELOCITY_MAX_SPAN_FRAMES:
            return None
        return ((p1.x - p0.x) / span, (p1.y - p0.y) / span)

    def _is_stationary(self, d: Detection) -> bool:
        x, y = d.center
        r = self.cfg.stationary_radius_widths * _width(d)
        frames = [f for f, hx, hy in self._candidate_history if math.hypot(hx - x, hy - y) <= r]
        return (
            len(frames) >= self.cfg.stationary_min_hits
            and frames[-1] - frames[0] >= self.cfg.stationary_min_span_frames
        )

    def _record_candidates(self, candidates: list[Detection]) -> None:
        horizon = self.frame_idx - self.cfg.stationary_window_frames
        while self._candidate_history and self._candidate_history[0][0] < horizon:
            self._candidate_history.popleft()
        for d in candidates:
            self._candidate_history.append((self.frame_idx, *d.center))

    def _choose(self, candidates: list[Detection]) -> Detection | None:
        last = self._last_point()
        if last is None:
            return max(candidates, key=lambda d: d.conf)

        elapsed = max(1, self.frame_idx - last.frame_idx)
        velocity = self._velocity()
        if velocity is not None:
            anchor = (last.x + velocity[0] * elapsed, last.y + velocity[1] * elapsed)
            gate_widths = self.cfg.gate_base_widths + self.cfg.gate_per_frame_widths * elapsed
        else:
            anchor = (last.x, last.y)
            gate_widths = self.cfg.max_jump_ball_widths * elapsed

        # Size the gate by the followed ball, not the candidate: a false
        # positive (a head) is often bigger than the ball and would widen its
        # own gate.
        ball_width = last.width or min(_width(d) for d in candidates)
        nearest = min(candidates, key=lambda d: math.dist(d.center, anchor))
        if math.dist(nearest.center, anchor) <= gate_widths * ball_width:
            return nearest

        # Nothing plausible near the followed ball. Switch only to a confident
        # detection, and only if the followed ball is stale or was weak.
        strong = max(candidates, key=lambda d: d.conf)
        followed_is_stale_or_weak = (
            elapsed >= self.cfg.switch_stale_frames or last.conf < self.cfg.switch_weak_conf
        )
        if strong.conf >= self.cfg.switch_strong_conf and followed_is_stale_or_weak:
            return strong
        return None

    def _update_trajectory(self, detections: list[Detection]) -> None:
        self.current_frame_ball_pos = None
        self.current_frame_ball_obs = None
        # Only confidence >= the confirmation threshold counts as a real
        # observation; lower-confidence boxes (down to track_conf) are still
        # returned to callers (e.g. for hoop tracking) but never become ball
        # observations by themselves.
        confident = [
            d for d in detections if d.class_name == BALL and d.conf >= self.detector.conf
        ]
        candidates = [d for d in confident if not self._is_stationary(d)]
        self._record_candidates(confident)
        if not candidates:
            return  # occlusion frame: trajectory untouched

        chosen = self._choose(candidates)
        if chosen is None:
            return  # implausible jump: treat as unobserved

        x, y = chosen.center
        self.trajectory.append(TrajectoryPoint(self.frame_idx, x, y, chosen.conf, _width(chosen)))
        self.current_frame_ball_pos = (x, y)
        self.current_frame_ball_obs = BallObservation.from_bbox(chosen.bbox)

    def reset(self) -> None:
        self.trajectory.clear()
        self._candidate_history.clear()
        self.frame_idx = 0
        self.current_frame_ball_pos = None
        self.current_frame_ball_obs = None
