"""Make/miss state machine — the part that matters most.

False positives (rim-outs or near-misses counted as makes) are worse than
missed detections, so every ambiguous case resolves to MISS, never MAKE.

Flow (per ball position fed in frame by frame):
  IDLE   -> ARMED  : ball seen above the rim, roughly aligned horizontally,
                      and descending for `descent_min_frames` in a row.
  ARMED  -> MAKE    : ball crosses the rim's vertical band while inside the
                      *inner* horizontal bounds, then continues below the
                      rim without bouncing back up above rim height.
  ARMED  -> MISS    : ball is in the rim's vertical band but outside the
                      inner bounds (rim-out), bounces back up above the rim
                      after having reached rim height or below, reaches
                      below the rim without ever having registered inside
                      the inner bounds, or the shot never resolves within
                      `shot_timeout_frames` / a `occlusion_grace_frames`
                      gap in detections.

A brief net/hand occlusion (missing detections for up to
`occlusion_grace_frames`) does not itself fail a shot — only a longer gap
does. This works the same for netted and net-less rims: the state machine
doesn't look at the net at all, only ball position relative to the rim box.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from shotvision.config.settings import ShotLogicConfig
from shotvision.shot_logic.rim import RimRegion

# Small pixel tolerance so per-frame detection jitter doesn't reset the
# pre-arm descent streak on an essentially-flat step.
_DESCENT_JITTER_PX = 3.0


class ShotState(Enum):
    IDLE = auto()
    ARMED = auto()  # shot in progress / undetermined


class ShotOutcome(Enum):
    MAKE = "MAKE"
    MISS = "MISS"


@dataclass
class ShotResult:
    outcome: ShotOutcome
    frame_idx: int


class ShotStateMachine:
    def __init__(self, rim: RimRegion, config: ShotLogicConfig):
        self.rim = rim
        self.config = config
        self.state = ShotState.IDLE
        self._reset_prearm()
        self._reset_armed()

    def _reset_prearm(self) -> None:
        self._prearm_streak = 0
        self._prearm_last_y: float | None = None

    def _reset_armed(self) -> None:
        self._entered_inner = False
        self._reached_band_or_below = False
        self._frames_since_detection = 0
        self._frames_in_state = 0

    def update(self, ball_pos: tuple[float, float] | None, frame_idx: int) -> ShotResult | None:
        """Feed the current frame's ball position (or None if not detected
        this frame). Returns a ShotResult on the frame a shot resolves."""
        if self.state is ShotState.IDLE:
            return self._update_idle(ball_pos)
        return self._update_armed(ball_pos, frame_idx)

    def _update_idle(self, ball_pos: tuple[float, float] | None) -> None:
        if ball_pos is None:
            self._reset_prearm()
            return None

        x, y = ball_pos
        if self.rim.is_above(y) and self.rim.is_aligned(x, self.config.align_tolerance_ratio):
            if self._prearm_last_y is not None and y >= self._prearm_last_y - _DESCENT_JITTER_PX:
                self._prearm_streak += 1
            else:
                self._prearm_streak = 1
            self._prearm_last_y = y

            if self._prearm_streak >= self.config.descent_min_frames:
                self._reset_prearm()
                self._reset_armed()
                self.state = ShotState.ARMED
        else:
            self._reset_prearm()
        return None

    def _update_armed(
        self, ball_pos: tuple[float, float] | None, frame_idx: int
    ) -> ShotResult | None:
        self._frames_in_state += 1

        if ball_pos is None:
            self._frames_since_detection += 1
            if self._frames_since_detection > self.config.occlusion_grace_frames:
                return self._resolve(ShotOutcome.MISS, frame_idx)
            if self._frames_in_state > self.config.shot_timeout_frames:
                return self._resolve(ShotOutcome.MISS, frame_idx)
            return None

        self._frames_since_detection = 0
        x, y = ball_pos

        # Bounced back up above the rim after having reached rim height or
        # below it — rim-out / airball off the back iron.
        if self._reached_band_or_below and self.rim.is_above(y):
            return self._resolve(ShotOutcome.MISS, frame_idx)

        if self.rim.is_below(y):
            self._reached_band_or_below = True
            if self._entered_inner:
                return self._resolve(ShotOutcome.MAKE, frame_idx)
            return self._resolve(ShotOutcome.MISS, frame_idx)

        if self.rim.is_in_band(y):
            self._reached_band_or_below = True
            if self.rim.is_inside_inner_bounds(x):
                self._entered_inner = True
            else:
                # At rim height but outside the inner gate — rim-out.
                return self._resolve(ShotOutcome.MISS, frame_idx)

        # Still above the rim, or in-band-and-inside-bounds: keep waiting.
        if self._frames_in_state > self.config.shot_timeout_frames:
            return self._resolve(ShotOutcome.MISS, frame_idx)
        return None

    def _resolve(self, outcome: ShotOutcome, frame_idx: int) -> ShotResult:
        self.state = ShotState.IDLE
        self._reset_prearm()
        self._reset_armed()
        return ShotResult(outcome, frame_idx)
