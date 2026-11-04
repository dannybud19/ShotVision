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
     that prediction (gate grows with time since last seen).
  3. A candidate outside the gate is accepted only if it is confident and
     the followed ball was itself weak, or has been unseen for
     switch_stale_s (longer than a normal motion-blur gap at the rim) — otherwise a shooter's
     head (conf ~0.2) a few ball-widths away can hijack the track mid-shot
     and fake a "ball below the rim", which is exactly what produced wrong
     MISS calls on measured footage.
  4. After max_gap_s without an accepted detection, re-acquire the most
     confident candidate.
  5. If no confident detection was accepted, a *weak* one (track_conf <= conf
     < the confirmation threshold) may continue the followed ball — only
     inside a tighter gate around the prediction and at a consistent size.
     It is marked `weak=True`; the state machine uses it to keep an armed
     shot alive (the ball faintly visible through the net) and nothing else.

All durations are configured in seconds and converted to frames with the
source's fps (`fps` argument; 30 by default, the rate everything was tuned at).
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

from shotvision.config.settings import REFERENCE_FPS, TrackerConfig, per_frame, to_frames
from shotvision.detection.detector import BALL, Detection, Detector
from shotvision.shot_logic.state_machine import BallObservation

# TrackerConfig.velocity_max_span_s: velocity is only estimated from two
# accepted points this close in time. (3 frames was too short: after a short
# blur gap there was no velocity, and the no-velocity fallback gate grew to
# ~400px — wide enough to admit a head.)
#
# TrackerConfig.strength_window_s: a followed ball's strength is its best
# confident sighting within this window: a ball seen at 0.8 that blurs to 0.2
# at the rim is still a strong track, not one a passing false positive may
# take over.


@dataclass
class TrajectoryPoint:
    frame_idx: int
    x: float
    y: float
    conf: float
    width: float = 0.0  # bbox width; sizes the association gate
    track_id: int = 0  # which followed-ball identity this point belongs to


def _width(d: Detection) -> float:
    return d.bbox[2] - d.bbox[0]


class BallTracker:
    def __init__(
        self,
        detector: Detector,
        tracker_config: TrackerConfig,
        buffer_len: int = 60,
        fps: float = REFERENCE_FPS,
    ):
        self.detector = detector
        self.cfg = tracker_config
        self.fps = fps
        self.trajectory: deque[TrajectoryPoint] = deque(maxlen=buffer_len)
        self.frame_idx = 0
        # Identity of the followed ball: bumped whenever the tracker abandons
        # a live followed ball for a different object, and carried on each BallObservation so the state machine
        # only scores the ball a shot armed on.
        self.track_id = 0
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

    def _frames(self, seconds: float) -> int:
        return to_frames(seconds, getattr(self, "fps", REFERENCE_FPS))

    def _per_frame(self, rate_per_s: float) -> float:
        return per_frame(rate_per_s, getattr(self, "fps", REFERENCE_FPS))

    def _last_point(self) -> TrajectoryPoint | None:
        """The last accepted position, if recent enough to associate with."""
        if not self.trajectory:
            return None
        last = self.trajectory[-1]
        if self.frame_idx - last.frame_idx > self._frames(self.cfg.max_gap_s):
            return None
        return last

    def _velocity(self) -> tuple[float, float] | None:
        if len(self.trajectory) < 2:
            return None
        p0, p1 = self.trajectory[-2], self.trajectory[-1]
        span = p1.frame_idx - p0.frame_idx
        if span <= 0 or span > self._frames(self.cfg.velocity_max_span_s):
            return None
        return ((p1.x - p0.x) / span, (p1.y - p0.y) / span)

    def _is_stationary(self, d: Detection) -> bool:
        x, y = d.center
        r = self.cfg.stationary_radius_widths * _width(d)
        frames = [f for f, hx, hy in self._candidate_history if math.hypot(hx - x, hy - y) <= r]
        return (
            len(frames) >= self._frames(self.cfg.stationary_min_hits_s)
            and frames[-1] - frames[0] >= self._frames(self.cfg.stationary_min_span_s)
        )

    def _record_candidates(self, candidates: list[Detection]) -> None:
        horizon = self.frame_idx - self._frames(self.cfg.stationary_window_s)
        while self._candidate_history and self._candidate_history[0][0] < horizon:
            self._candidate_history.popleft()
        for d in candidates:
            self._candidate_history.append((self.frame_idx, *d.center))

    def _choose(self, candidates: list[Detection]) -> tuple[Detection | None, bool]:
        """Returns (chosen detection or None, whether it starts a new
        followed-ball identity)."""
        last = self._last_point()
        if last is None:
            # (Re)acquisition after the followed ball expired keeps the
            # identity: e.g. the ball reappearing below the net after a long
            # occlusion is the same ball the shot armed on. Only abandoning a
            # live track for another object (below) starts a new identity.
            return max(candidates, key=lambda d: d.conf), False

        elapsed = max(1, self.frame_idx - last.frame_idx)
        velocity = self._velocity()
        if velocity is not None:
            # Gate around the predicted position AND the last position: a ball
            # caught by the net or rolling on the rim decelerates abruptly, so
            # the prediction overshoots while the ball stays put (measured:
            # the ball in the net at conf 0.72 was rejected for 7 frames).
            predicted = (last.x + velocity[0] * elapsed, last.y + velocity[1] * elapsed)
            anchors = [predicted, (last.x, last.y)]
            gate_widths = self.cfg.gate_base_widths + self._per_frame(self.cfg.gate_growth_widths_per_s) * elapsed
        else:
            anchors = [(last.x, last.y)]
            gate_widths = self._per_frame(self.cfg.max_jump_widths_per_s) * elapsed

        # Size the gate by the followed ball, not the candidate: a false
        # positive (a head) is often bigger than the ball and would widen its
        # own gate.
        ball_width = last.width or min(_width(d) for d in candidates)
        def dist(d: Detection) -> float:
            return min(math.dist(d.center, a) for a in anchors)

        nearest = min(candidates, key=dist)
        if dist(nearest) <= gate_widths * ball_width:
            return nearest, False

        # Nothing plausible near the followed ball. Switch only to a confident
        # detection, and only if the followed ball is stale or was weak.
        strong = max(candidates, key=lambda d: d.conf)
        # Judge the followed ball by its last *confident* sighting: a weak
        # continuation through the net must not make the track look weak
        # and hand it to a strong false positive (measured: a shooter's head).
        followed_conf = max(
            (
                p.conf for p in self.trajectory
                if p.track_id == last.track_id
                and p.conf >= self.detector.conf
                and last.frame_idx - p.frame_idx <= self._frames(self.cfg.strength_window_s)
            ),
            default=0.0,
        )
        followed_is_stale_or_weak = (
            elapsed >= self._frames(self.cfg.switch_stale_s) or followed_conf < self.cfg.switch_weak_conf
        )
        if strong.conf >= self.cfg.switch_strong_conf and followed_is_stale_or_weak:
            return strong, True
        return None, False

    def _choose_weak(self, weak: list[Detection]) -> Detection | None:
        """A low-confidence detection may only continue a followed ball with
        a velocity estimate: nearest to the prediction, inside
        weak_gate_scale x the normal gate, and within weak_size_ratio of the
        followed ball's width."""
        last = self._last_point()
        velocity = self._velocity()
        if not weak or last is None or velocity is None or not last.width:
            return None
        elapsed = max(1, self.frame_idx - last.frame_idx)
        anchor = (last.x + velocity[0] * elapsed, last.y + velocity[1] * elapsed)
        gate = (
            self.cfg.weak_gate_scale
            * (self.cfg.gate_base_widths + self._per_frame(self.cfg.gate_growth_widths_per_s) * elapsed)
            * last.width
        )
        ratio = self.cfg.weak_size_ratio
        plausible = [
            d for d in weak
            if math.dist(d.center, anchor) <= gate and 1 / ratio <= _width(d) / last.width <= ratio
        ]
        return min(plausible, key=lambda d: math.dist(d.center, anchor)) if plausible else None

    def _update_trajectory(self, detections: list[Detection]) -> None:
        self.current_frame_ball_pos = None
        self.current_frame_ball_obs = None
        # Only confidence >= the confirmation threshold counts as a real
        # observation; lower-confidence boxes (down to track_conf) are still
        # returned to callers (e.g. for hoop tracking) but never become ball
        # observations by themselves.
        balls = [d for d in detections if d.class_name == BALL]
        confident = [d for d in balls if d.conf >= self.detector.conf]
        candidates = [d for d in confident if not self._is_stationary(d)]
        self._record_candidates(confident)

        chosen, new_track = self._choose(candidates) if candidates else (None, False)
        weak = False
        if chosen is None:
            chosen = self._choose_weak([d for d in balls if d.conf < self.detector.conf])
            weak = chosen is not None
        if chosen is None:
            return  # occlusion frame or implausible jump: trajectory untouched

        if new_track:
            self.track_id += 1
        x, y = chosen.center
        self.trajectory.append(
            TrajectoryPoint(self.frame_idx, x, y, chosen.conf, _width(chosen), self.track_id)
        )
        self.current_frame_ball_pos = (x, y)
        obs = BallObservation.from_bbox(chosen.bbox, weak=weak)
        obs.track_id = self.track_id
        self.current_frame_ball_obs = obs

    def reset(self) -> None:
        self.trajectory.clear()
        self._candidate_history.clear()
        self.frame_idx = 0
        self.current_frame_ball_pos = None
        self.current_frame_ball_obs = None
