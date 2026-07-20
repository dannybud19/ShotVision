"""Rim geometry derived from 4 manually-clicked points around the rim.

Two bound sets: the outer box (used for above/at/below-rim tests) and an
inner horizontal scoring gate, shrunk in from the outer box so a make must
pass cleanly through the middle of the rim rather than clip an edge —
false-positive-averse, per the make/miss requirement.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RimRegion:
    outer_left: float
    outer_right: float
    outer_top: float
    outer_bottom: float
    inner_left: float
    inner_right: float

    @property
    def outer_width(self) -> float:
        return self.outer_right - self.outer_left

    @property
    def center_x(self) -> float:
        return (self.outer_left + self.outer_right) / 2

    @property
    def rim_y(self) -> float:
        """The horizontal scoring plane — the rim's vertical midline. A made
        shot's path crosses this line while within the inner horizontal gate.
        Using a single line (not the full band) makes scoring robust to sparse
        detections and thin calibrations: we test whether the segment between
        two consecutive ball positions crosses it, not whether a detection
        happened to land inside the band."""
        return (self.outer_top + self.outer_bottom) / 2

    def is_within_outer_x(self, x: float) -> bool:
        return self.outer_left <= x <= self.outer_right

    def is_aligned(self, x: float, tolerance_ratio: float) -> bool:
        """True if x is within tolerance_ratio * outer_width of rim center
        (on top of the rim's own half-width) — the 'roughly aligned
        horizontally' check for arming a shot."""
        half_span = (self.outer_width / 2) * (1 + tolerance_ratio)
        return abs(x - self.center_x) <= half_span

    def is_inside_inner_bounds(self, x: float) -> bool:
        return self.inner_left <= x <= self.inner_right

    def is_above(self, y: float) -> bool:
        return y < self.outer_top

    def is_in_band(self, y: float) -> bool:
        return self.outer_top <= y <= self.outer_bottom

    def is_below(self, y: float) -> bool:
        return y > self.outer_bottom

    @classmethod
    def from_points(
        cls, points: list[tuple[float, float]], inner_bound_shrink: float
    ) -> "RimRegion":
        """points: 4 (x, y) points clicked around the rim, any order —
        treated as defining a bounding box, not an ordered polygon."""
        if len(points) != 4:
            raise ValueError(f"Rim calibration requires exactly 4 points, got {len(points)}")
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        outer_left, outer_right = min(xs), max(xs)
        outer_top, outer_bottom = min(ys), max(ys)
        shrink = (outer_right - outer_left) * inner_bound_shrink
        return cls(
            outer_left=outer_left,
            outer_right=outer_right,
            outer_top=outer_top,
            outer_bottom=outer_bottom,
            inner_left=outer_left + shrink,
            inner_right=outer_right - shrink,
        )

    def to_dict(self) -> dict:
        return {
            "outer_left": self.outer_left,
            "outer_right": self.outer_right,
            "outer_top": self.outer_top,
            "outer_bottom": self.outer_bottom,
            "inner_left": self.inner_left,
            "inner_right": self.inner_right,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RimRegion":
        return cls(**data)
