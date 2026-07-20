"""Make/miss state machine — the part that matters most.

False positives (rim-outs or near-misses counted as makes) are worse than
missed detections, so every ambiguous case resolves to MISS, never MAKE.

Scoring is **trajectory-crossing based**, not band-membership based. Rather
than requiring a ball detection to land inside the rim's (possibly very thin)
vertical band, we test whether the *segment* between two consecutive observed
ball positions crosses the rim's horizontal midline (`rim.rim_y`), and where.
This is robust to sparse detections and thin calibrations — the ball can be
occluded or simply not detected while passing through the rim, and we still
recover the crossing by interpolating between the last position above the rim
and the first below it.

Flow (per ball observation fed in frame by frame):
  IDLE  -> ARMED : ball above the rim, roughly aligned horizontally, and
                    descending for `descent_min_frames` in a row.
  ARMED -> MAKE  : the ball's path crosses the rim line within the inner
                    horizontal gate, and the *whole ball* then reaches below
                    the outlined rim (bbox top edge below `outer_bottom`)
                    without bouncing back up.
  ARMED -> MISS  : the path crosses the rim line outside the inner gate
                    (rim-out), the whole ball reaches below the rim without a
                    valid through-crossing, the ball bounces back above the
                    rim after reaching it, or the shot never resolves within
                    `shot_timeout_frames` / an `occlusion_grace_frames` gap.

A brief net/hand occlusion (missing detections up to `occlusion_grace_frames`)
does not fail a shot and does not break crossing detection — the segment simply
spans the gap. Works identically for netted and net-less rims.
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


@dataclass
class BallObservation:
    """One frame's ball detection: center plus bounding box, so the make/miss
    logic can reason about the *whole ball* (e.g. whole ball below the rim),
    not just its center point."""
    x: float
    y: float
    left: float
    top: float
    right: float
    bottom: float

    @property
    def center(self) -> tuple[float, float]:
        return (self.x, self.y)

    @classmethod
    def from_bbox(cls, bbox: tuple[float, float, float, float]) -> "BallObservation":
        x1, y1, x2, y2 = bbox
        return cls(x=(x1 + x2) / 2, y=(y1 + y2) / 2, left=x1, top=y1, right=x2, bottom=y2)

    @classmethod
    def from_center(cls, x: float, y: float, radius: float = 3.0) -> "BallObservation":
        """Build an observation from a center point with an assumed radius —
        convenience for callers/tests that only have a center."""
        return cls(x=x, y=y, left=x - radius, top=y - radius, right=x + radius, bottom=y + radius)


def _interp_x_at_y(p0: tuple[float, float], p1: tuple[float, float], y: float) -> float:
    """X coordinate where the segment p0->p1 crosses the horizontal line at y."""
    (x0, y0), (x1, y1) = p0, p1
    if y1 == y0:
        return x1
    t = (y - y0) / (y1 - y0)
    return x0 + (x1 - x0) * t


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
    MISS_RIM_OUT_SIDEWAYS = "miss_rim_out_sideways"  # crossed rim line outside inner gate
    MISS_BELOW_WITHOUT_INNER = "miss_below_without_inner"  # whole ball below, no valid crossing
    MISS_BOUNCE_UP = "miss_bounce_up"  # bounced back above rim after reaching it
    MISS_OCCLUSION_GAP = "miss_occlusion_gap"  # no detection longer than grace
    MISS_TIMEOUT_OCCLUDED = "miss_timeout_occluded"  # timed out during an occlusion gap
    MISS_TIMEOUT_ABOVE = "miss_timeout_above"  # timed out still hovering above the rim


TraceEntry = tuple[int, "tuple[float, float] | None"]  # (frame_idx, ball center or None)


@dataclass
class ShotResult:
    outcome: ShotOutcome
    frame_idx: int
    # --- diagnostics (defaulted so ShotResult(outcome, frame_idx) still works) ---
    reason: ResolutionReason | None = None
    recent_trace: list[TraceEntry] = field(default_factory=list)
    occlusion_frames_before_resolve: int = 0
    entered_inner: bool = False  # a through-crossing (inner gate) was registered
    reached_band: bool = False  # the ball reached the rim line / below it
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
        self._passed_through = False
        self._reached_rim = False
        self._prev_obs: BallObservation | None = None
        self._frames_since_detection = 0
        self._frames_in_state = 0
        # Rolling record of the armed shot's frames for diagnostics.
        self._trace: deque[TraceEntry] = deque(maxlen=_TRACE_LEN)

    def update(
        self, obs: BallObservation | tuple[float, float] | None, frame_idx: int
    ) -> ShotResult | None:
        """Feed the current frame's ball observation (or None if not detected
        this frame). Returns a ShotResult on the frame a shot resolves. A plain
        (x, y) center tuple is accepted as a convenience and coerced to a
        BallObservation with an assumed small radius."""
        if isinstance(obs, tuple):
            obs = BallObservation.from_center(*obs)
        if self.state is ShotState.IDLE:
            return self._update_idle(obs, frame_idx)
        return self._update_armed(obs, frame_idx)

    def _update_idle(self, obs: BallObservation | None, frame_idx: int) -> None:
        if obs is None:
            self._reset_prearm()
            return None

        x, y = obs.center
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
                self._prev_obs = obs  # seed the trajectory for crossing tests
                self._trace.append((frame_idx, obs.center))
        else:
            self._reset_prearm()
        return None

    def _update_armed(self, obs: BallObservation | None, frame_idx: int) -> ShotResult | None:
        self._frames_in_state += 1
        self._trace.append((frame_idx, obs.center if obs is not None else None))

        if obs is None:
            self._frames_since_detection += 1
            if self._frames_since_detection > self.config.occlusion_grace_frames:
                return self._resolve(ShotOutcome.MISS, frame_idx, ResolutionReason.MISS_OCCLUSION_GAP)
            if self._frames_in_state > self.config.shot_timeout_frames:
                return self._resolve(ShotOutcome.MISS, frame_idx, ResolutionReason.MISS_TIMEOUT_OCCLUDED)
            return None

        self._frames_since_detection = 0
        x, y = obs.center
        rim = self.rim

        # Did the segment from the previous detected position to this one cross
        # the rim line going downward? (Spans occlusion gaps — prev is the last
        # *detected* position, not necessarily the immediately previous frame.)
        if self._prev_obs is not None and self._prev_obs.y < rim.rim_y <= y:
            self._reached_rim = True
            cross_x = _interp_x_at_y(self._prev_obs.center, obs.center, rim.rim_y)
            if rim.is_inside_inner_bounds(cross_x):
                self._passed_through = True
            else:
                # Crossed the rim line outside the scoring gate — it did not go
                # through the opening and cannot become a make now.
                if rim.is_within_outer_x(cross_x):
                    return self._resolve(ShotOutcome.MISS, frame_idx, ResolutionReason.MISS_RIM_OUT_SIDEWAYS)
                return self._resolve(ShotOutcome.MISS, frame_idx, ResolutionReason.MISS_BELOW_WITHOUT_INNER)

        # Bounced back up above the rim after having reached it — rim-out /
        # airball off the back iron.
        if self._reached_rim and rim.is_above(y):
            return self._resolve(ShotOutcome.MISS, frame_idx, ResolutionReason.MISS_BOUNCE_UP)

        # Whole ball below the outlined rim (bbox top edge past the bottom) —
        # the shot has resolved one way or the other.
        if obs.top >= rim.outer_bottom:
            self._reached_rim = True
            if self._passed_through:
                return self._resolve(ShotOutcome.MAKE, frame_idx, ResolutionReason.MAKE_CONFIRMED)
            return self._resolve(ShotOutcome.MISS, frame_idx, ResolutionReason.MISS_BELOW_WITHOUT_INNER)

        if self._frames_in_state > self.config.shot_timeout_frames:
            return self._resolve(ShotOutcome.MISS, frame_idx, ResolutionReason.MISS_TIMEOUT_ABOVE)

        self._prev_obs = obs
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
            entered_inner=self._passed_through,
            reached_band=self._reached_rim,
            armed_frames=self._frames_in_state,
        )
        self.state = ShotState.IDLE
        self._reset_prearm()
        self._reset_armed()
        return result
