"""Make/miss state machine — the part that matters most.

False positives (rim-outs or near-misses counted as makes) are worse than
missed detections, so every ambiguous case resolves to MISS, never MAKE.

Scoring is **trajectory-crossing based**, not band-membership based. Rather
than requiring a ball detection to land inside the rim's (possibly very thin)
vertical band, we test whether the ball's path crosses the rim's horizontal
midline (`rim.rim_y`), and where. This is robust to sparse detections and
thin calibrations — the ball can be occluded or simply not detected while
passing through the rim, and we still recover the crossing.

The crossing x is estimated with `_fit_cross_x`: a least-squares line over the
last few *confirmed* observations (`_CROSSING_FIT_WINDOW`), not just the two
points immediately bracketing the crossing. With exactly 2 points this is
identical to straight-line interpolation; with more, it uses the shape of the
approach instead of trusting a single potentially-noisy endpoint (a bbox
distorted by partial net occlusion, motion blur, etc. right at the rim — the
highest-risk region for a bad reading). Trade-off, deliberate and tested
(`test_fit_cross_x_uses_full_window_not_just_last_two_points`): a single
suspicious last-instant position can no longer unilaterally flip the outcome
when preceded by a consistent approach; only a sustained drift across the
window does.

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

# How many recent *confirmed* observations to use when estimating where the
# ball's path crosses the rim line. More than 2 points lets the estimate use
# the shape of the approach instead of a single fragile 2-point straight
# line across a detection gap; naturally degrades to a 2-point line when
# fewer points are available (e.g. right after arming).
_CROSSING_FIT_WINDOW = 4


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


def _fit_cross_x(points: list[tuple[float, float]], target_y: float) -> float:
    """Estimate the x coordinate at `target_y` from a small window of recent
    (x, y) observations via a least-squares line x = m*y + c. With exactly 2
    points this is identical to straight-line interpolation between them;
    with more points it uses the shape of the approach instead of trusting a
    single pair of (possibly noisy, possibly gap-spanning) endpoints."""
    n = len(points)
    if n == 1:
        return points[0][0]

    mean_y = sum(y for _, y in points) / n
    mean_x = sum(x for x, _ in points) / n
    num = sum((y - mean_y) * (x - mean_x) for x, y in points)
    den = sum((y - mean_y) ** 2 for _, y in points)
    if den == 0:
        return mean_x
    m = num / den
    c = mean_x - m * mean_y
    return m * target_y + c


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
        # Rolling window of confirmed observations made so far this armed
        # shot (most recent last), used both as "the previous point" for the
        # crossing trigger and as the fit window for _fit_cross_x.
        self._recent: deque[BallObservation] = deque(maxlen=_CROSSING_FIT_WINDOW)
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
                self._recent.append(obs)  # seed the trajectory for crossing tests
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
        prev = self._recent[-1] if self._recent else None

        # Did the segment from the previous confirmed position to this one
        # cross the rim line going downward? (Spans occlusion/low-confidence
        # gaps — prev is the last *confirmed* position, not necessarily the
        # immediately previous frame.)
        if prev is not None and prev.y < rim.rim_y <= y:
            self._reached_rim = True
            fit_points = [p.center for p in self._recent] + [obs.center]
            cross_x = _fit_cross_x(fit_points, rim.rim_y)
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

        self._recent.append(obs)
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
