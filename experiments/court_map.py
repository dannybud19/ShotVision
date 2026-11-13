"""Court mapping for a fixed camera (experiment, no model, nothing ships).

Two or three points is decided by where the shooter's feet are on the floor.
With a fixed camera, clicking four or more floor points whose court positions
are known gives a homography: a mapping from image pixels to court metres.
This module holds the maths. The owner tries it on a real frame later.

Court coordinates are in metres. The origin is the centre of the rim projected
onto the floor, x runs along the baseline, y runs towards half court. So the
baseline is at y = -rim_from_baseline.

  to_court(H, x, y)   image pixel -> (court x, court y)
  fit_homography      image points + court points (>= 4) -> H
  is_three            is a shot taken from this court position worth three?

Interactive use (needs the owner's screen; click points, then type each
point's court coordinates in the terminal):
  python experiments/court_map.py --image sample_clips/_review/some_frame.png
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

# Metres, origin under the rim centre. `corner_x` is the distance of the corner
# three-point line from the rim centre, measured along x. The straight corner
# sections run from the baseline to where they meet the arc.
COURTS = {
    "fiba": {
        "arc_radius": 6.75,
        "corner_x": 6.60,
        "free_throw_line_from_baseline": 5.80,
        "rim_from_baseline": 1.575,
    },
    "nba": {
        "arc_radius": 7.24,
        "corner_x": 6.71,
        "free_throw_line_from_baseline": 5.79,
        "rim_from_baseline": 1.575,  # approx
    },
}


def fit_homography(image_pts, court_pts) -> np.ndarray:
    """3x3 homography from image pixels to court metres (least squares, method 0).
    Needs at least 4 matching points."""
    src = np.asarray(image_pts, dtype=np.float64).reshape(-1, 2)
    dst = np.asarray(court_pts, dtype=np.float64).reshape(-1, 2)
    if len(src) < 4 or len(dst) < 4:
        raise ValueError(f"need at least 4 points, got {min(len(src), len(dst))}")
    if len(src) != len(dst):
        raise ValueError(f"image and court point counts differ: {len(src)} vs {len(dst)}")
    H, _ = cv2.findHomography(src, dst, 0)
    if H is None:
        raise ValueError("could not fit a homography (are the points degenerate, e.g. on one line?)")
    return H


def to_court(H, x: float, y: float) -> tuple[float, float]:
    """Image pixel (x, y) -> court position (cx, cy) in metres."""
    pt = np.array([[[x, y]]], dtype=np.float64)
    cx, cy = cv2.perspectiveTransform(pt, np.asarray(H, dtype=np.float64))[0, 0]
    return float(cx), float(cy)


def is_three(court_xy, court: str = "fiba") -> bool:
    """True when the position is behind the three-point line: outside the arc, or
    in a corner (beyond the corner line, on the baseline side of where the arc
    meets it). Standing exactly on the line counts as two."""
    spec = COURTS[court]
    x, y = float(court_xy[0]), float(court_xy[1])
    r, corner_x = spec["arc_radius"], spec["corner_x"]
    if float(np.hypot(x, y)) > r:
        return True
    arc_meets_corner_y = float(np.sqrt(r * r - corner_x * corner_x))
    return abs(x) > corner_x and y <= arc_meets_corner_y


# ---------------------------------------------------------------------------
# Interactive fitter (owner's screen only)
# ---------------------------------------------------------------------------


def _interactive(image_path: Path) -> int:
    img = cv2.imread(str(image_path))
    if img is None:
        sys.exit(f"could not read image: {image_path}")
    shown = img.copy()
    clicks: list[tuple[int, int]] = []
    image_pts: list[list[float]] = []
    court_pts: list[list[float]] = []
    window = "court_map: click a floor point, type its court x y in the terminal; f = fit, q = quit"

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            clicks.append((x, y))

    cv2.namedWindow(window)
    cv2.setMouseCallback(window, on_mouse)
    print("Click a floor point of known court position in the window, then type its court x and y in metres")
    print("(origin under the rim centre, x along the baseline, y towards half court), e.g.:  0 4.225")
    print("In the window: f = fit and save (needs 4+ points), q = quit without saving.")
    while True:
        cv2.imshow(window, shown)
        key = cv2.waitKey(30) & 0xFF
        if clicks:
            x, y = clicks.pop(0)
            text = input(f"point {len(image_pts) + 1} at pixel ({x}, {y}): court x y = ").strip()
            try:
                cx, cy = (float(v) for v in text.replace(",", " ").split())
            except ValueError:
                print("  not two numbers, point ignored")
                continue
            image_pts.append([float(x), float(y)])
            court_pts.append([cx, cy])
            cv2.circle(shown, (x, y), 5, (0, 0, 255), -1)
            cv2.putText(shown, str(len(image_pts)), (x + 6, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        elif key == ord("q"):
            cv2.destroyAllWindows()
            return 1
        elif key == ord("f"):
            try:
                H = fit_homography(image_pts, court_pts)
            except ValueError as err:
                print(f"  cannot fit yet: {err}")
                continue
            print("H (image pixels -> court metres):")
            print(H)
            out = image_path.with_name(image_path.stem + "_homography.json")
            out.write_text(json.dumps(
                {"image": image_path.name, "image_pts": image_pts, "court_pts": court_pts, "H": H.tolist()},
                indent=2) + "\n")
            print(f"saved {out}")
            cv2.destroyAllWindows()
            return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Fit a pixel-to-court homography from clicked points")
    p.add_argument("--image", required=True, help="a still frame (png/jpg) from a fixed-camera clip")
    args = p.parse_args()
    return _interactive(Path(args.image))


if __name__ == "__main__":
    sys.exit(main())
