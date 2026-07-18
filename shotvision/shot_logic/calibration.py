"""Interactive 4-click rim calibration, plus JSON persistence keyed by
camera source so recalibration isn't needed every run.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2

from shotvision.shot_logic.rim import RimRegion


class ClickCollector:
    """Pure point-collection state for the 4-click calibration flow,
    decoupled from any actual window/display so it's unit-testable."""

    def __init__(self, required_points: int = 4):
        self.required_points = required_points
        self.points: list[tuple[int, int]] = []

    def on_click(self, event, x, y, flags, param) -> None:
        if event == cv2.EVENT_LBUTTONDOWN and len(self.points) < self.required_points:
            self.points.append((x, y))

    def reset(self) -> None:
        self.points.clear()

    @property
    def is_complete(self) -> bool:
        return len(self.points) >= self.required_points


def load_calibration(path: str | Path, source_key: str) -> RimRegion | None:
    path = Path(path)
    if not path.exists():
        return None
    with open(path) as f:
        data = json.load(f)
    entry = data.get(source_key)
    if entry is None:
        return None
    return RimRegion.from_dict(entry)


def save_calibration(path: str | Path, source_key: str, rim: RimRegion) -> None:
    path = Path(path)
    data = {}
    if path.exists():
        with open(path) as f:
            data = json.load(f)
    data[source_key] = rim.to_dict()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def run_calibration_ui(
    frame,
    inner_bound_shrink: float,
    window_name: str = "ShotVision - Calibrate Rim (click 4 points, ESC to cancel)",
) -> RimRegion | None:
    """Blocking interactive loop: click 4 points around the rim on `frame`.
    Returns the resulting RimRegion, or None if cancelled with ESC. Not
    unit-tested — needs a real display; ClickCollector above holds all the
    testable logic."""
    collector = ClickCollector()
    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, collector.on_click)

    try:
        while True:
            display = frame.copy()
            for pt in collector.points:
                cv2.circle(display, pt, 5, (0, 255, 255), -1)
            if len(collector.points) >= 2:
                xs = [p[0] for p in collector.points]
                ys = [p[1] for p in collector.points]
                cv2.rectangle(
                    display, (min(xs), min(ys)), (max(xs), max(ys)), (0, 255, 255), 1
                )
            cv2.imshow(window_name, display)

            key = cv2.waitKey(20) & 0xFF
            if key == 27:  # ESC cancels
                return None
            if collector.is_complete:
                break
    finally:
        cv2.destroyWindow(window_name)

    return RimRegion.from_points(collector.points, inner_bound_shrink)
