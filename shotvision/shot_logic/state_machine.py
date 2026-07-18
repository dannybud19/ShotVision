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

from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto

from shotvision.config.settings import ShotLogicConfig
from shotvision.shot_logic.rim import RimRegion

# Small pixel tolerance so per-frame detection jitter doesn't reset the
# pre-arm descent streak on an essentially-flat step.
_DESCENT_JITTER_PX = 3.0

# How many of the most recent armed frames to snapshot onto a ShotResult for
# diagnostics (both detected positions and None occlusion frames).
_TRACE_LEN = 8


class ShotState(Enum):
    IDLE = auto()
    ARMED = auto()  # shot in progress / undetermined


class ShotOutcome(Enum):
    MAKE = "MAKE"
    MISS = "MISS"


class ResolutionReason(Enum):
    """Which exit path in the state machine produced a resolution — one per
    `_resolve(...)` call site. Purely diagnostic; does not affect outcomes."""
    MAKE_CONFIRMED = "make_confirmed"
    MISS_RIM_OUT_SIDEWAYS = "miss_rim_out_sideways"  # in band, outside inner gate
    MISS_BELOW_WITHOUT_INNER = "miss_below_without_inner"  # below rim, never inside inner
    MISS_BOUNCE_UP = "miss_bounce_up"  # bounced back above rim after reaching band/below
    MISS_OCCLUSION_GAP = "miss_occlusion_gap"  # no detection longer than grace
    MISS_TIMEOUT_OCCLUDED = "miss_timeout_occluded"  # timed out during an occlusion gap
    MISS_TIMEOUT_ABOVE = "miss_timeout_above"  # timed out still hovering above the rim


TraceEntry = tuple[int, "tuple[float, float] | None"]  # (frame_idx, ball_pos or None)


@dataclass
class ShotResult:
    outcome: ShotOutcome
    frame_idx: int
    # --- diagnostics (defaulted so ShotResult(outcome, frame_idx) still works) ---
    reason: ResolutionReason | None = None
    recent_trace: list[TraceEntry] = field(default_factory=list)
    occlusion_frames_before_resolve: int = 0
    entered_inner: bool = False
    reached_band: bool = False
    armed_frames: int = 0


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
        # Rolling record of the armed shot's frames for diagnostics.
        self._trace: deque[TraceEntry] = deque(maxlen=_TRACE_LEN)

    def update(self, ball_pos: tuple[float, float] | None, frame_idx: int) -> ShotResult | None:
        """Feed the current frame's ball position (or None if not detected
        this frame). Returns a ShotResult on the frame a shot resolves."""
        if self.state is ShotState.IDLE:
            return self._update_idle(ball_pos, frame_idx)
        return self._update_armed(ball_pos, frame_idx)

    def _update_idle(
        self, ball_pos: tuple[float, float] | None, frame_idx: int
    ) -> None:
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
                # Record the arming frame as the first trace entry.
                self._trace.append((frame_idx, ball_pos))
        else:
            self._reset_prearm()
        return None

    def _update_armed(
        self, ball_pos: tuple[float, float] | None, frame_idx: int
    ) -> ShotResult | None:
        self._frames_in_state += 1
        self._trace.append((frame_idx, ball_pos))

        if ball_pos is None:
            self._frames_since_detection += 1
            if self._frames_since_detection > self.config.occlusion_grace_frames:
                return self._resolve(ShotOutcome.MISS, frame_idx, ResolutionReason.MISS_OCCLUSION_GAP)
            if self._frames_in_state > self.config.shot_timeout_frames:
                return self._resolve(ShotOutcome.MISS, frame_idx, ResolutionReason.MISS_TIMEOUT_OCCLUDED)
            return None

        self._frames_since_detection = 0
        x, y = ball_pos

        # Bounced back up above the rim after having reached rim height or
        # below it — rim-out / airball off the back iron.
        if self._reached_band_or_below and self.rim.is_above(y):
            return self._resolve(ShotOutcome.MISS, frame_idx, ResolutionReason.MISS_BOUNCE_UP)

        if self.rim.is_below(y):
            self._reached_band_or_below = True
            if self._entered_inner:
                return self._resolve(ShotOutcome.MAKE, frame_idx, ResolutionReason.MAKE_CONFIRMED)
            return self._resolve(ShotOutcome.MISS, frame_idx, ResolutionReason.MISS_BELOW_WITHOUT_INNER)

        if self.rim.is_in_band(y):
            self._reached_band_or_below = True
            if self.rim.is_inside_inner_bounds(x):
                self._entered_inner = True
            else:
                # At rim height but outside the inner gate — rim-out.
                return self._resolve(ShotOutcome.MISS, frame_idx, ResolutionReason.MISS_RIM_OUT_SIDEWAYS)

        # Still above the rim, or in-band-and-inside-bounds: keep waiting.
        if self._frames_in_state > self.config.shot_timeout_frames:
            return self._resolve(ShotOutcome.MISS, frame_idx, ResolutionReason.MISS_TIMEOUT_ABOVE)
        return None

    def _resolve(
        self, outcome: ShotOutcome, frame_idx: int, reason: ResolutionReason
    ) -> ShotResult:
        result = ShotResult(
            outcome=outcome,
            frame_idx=frame_idx,
            reason=reason,
            recent_trace=list(self._trace),
            occlusion_frames_before_resolve=self._frames_since_detection,
            entered_inner=self._entered_inner,
            reached_band=self._reached_band_or_below,
            armed_frames=self._frames_in_state,
        )
        self.state = ShotState.IDLE
        self._reset_prearm()
        self._reset_armed()
        return result
