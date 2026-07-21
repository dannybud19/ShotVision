"""Automatic rim tracking from the model's own hoop detections.

Replaces manual click calibration: turns a per-frame HOOP detection — still
jittery frame to frame, occasionally briefly missed — into a stable
RimRegion via EMA smoothing, occlusion tolerance, and a sanity gate against
implausible sudden size jumps. A real hoop's on-screen size changes
gradually with camera motion, not in one frame, so a sudden jump is more
likely a stray misclassification than the real hoop — false rim readings
are higher-stakes than a missed ball frame, since they corrupt the scoring
geometry itself.

Consumes the same per-frame detections list BallTracker.update() already
returns (ball + hoop + person from one inference pass) — no extra inference
cost to track the rim alongside the ball.
"""
from __future__ import annotations

from shotvision.config.settings import ModelConfig, ShotLogicConfig
from shotvision.detection.detector import HOOP, Detection
from shotvision.shot_logic.rim import RimRegion

Bbox = tuple[float, float, float, float]


def _bbox_area(bbox: Bbox) -> float:
    x1, y1, x2, y2 = bbox
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


class RimTracker:
    def __init__(self, model_config: ModelConfig, shot_logic_config: ShotLogicConfig):
        self.rim_conf = model_config.rim_conf
        self.ema_alpha = shot_logic_config.rim_ema_alpha
        self.lost_grace_frames = shot_logic_config.rim_lost_grace_frames
        self.size_jump_max_ratio = shot_logic_config.rim_size_jump_max_ratio
        self.inner_bound_shrink = shot_logic_config.inner_bound_shrink

        self.current_rim: RimRegion | None = None
        self._ema_box: Bbox | None = None
        self._frames_since_hoop = 0

    def update(self, detections: list[Detection]) -> RimRegion | None:
        """Feed one frame's full detections list. Returns the current best
        rim estimate, or None if never yet acquired (or lost for longer
        than `rim_lost_grace_frames`)."""
        hoop_dets = [
            d for d in detections if d.class_name == HOOP and d.conf >= self.rim_conf
        ]
        chosen = max(hoop_dets, key=lambda d: d.conf) if hoop_dets else None

        if chosen is None or (self._ema_box is not None and not self._is_plausible_size(chosen.bbox)):
            self._frames_since_hoop += 1
            if self._frames_since_hoop > self.lost_grace_frames:
                self.current_rim = None
                self._ema_box = None
            return self.current_rim

        self._frames_since_hoop = 0
        self._update_ema(chosen.bbox)
        self.current_rim = RimRegion.from_bbox(self._ema_box, self.inner_bound_shrink)
        return self.current_rim

    def _is_plausible_size(self, bbox: Bbox) -> bool:
        current_area = _bbox_area(self._ema_box)
        if current_area <= 0:
            return True
        ratio = _bbox_area(bbox) / current_area
        return (1 / self.size_jump_max_ratio) <= ratio <= self.size_jump_max_ratio

    def _update_ema(self, bbox: Bbox) -> None:
        if self._ema_box is None:
            self._ema_box = bbox
            return
        a = self.ema_alpha
        self._ema_box = tuple(a * new + (1 - a) * old for new, old in zip(bbox, self._ema_box))

    def reset(self) -> None:
        """Force reacquisition from scratch (e.g. 'r' key in main.py)."""
        self.current_rim = None
        self._ema_box = None
        self._frames_since_hoop = 0
