"""Camera profile: measure each labeled clip's camera objectively from cached
detections.

For every labeled clip this prints one row of camera measurements, so the
report can separate Phase 1's in-scope setup (one fixed camera, one shooter,
one ball) from the out-of-scope public footage (panning broadcast, multi-ball
practices). It is read-only with respect to the pipeline: it loads only the
cached raw detections in experiments/.cache/detections and never runs
detection, so it never loads the .pt.

Columns (see docs/plans/PLAN_1_score_split.md step 4.1 for the definitions):
  frames          number of frames
  fps             the clip's own frame rate (header only)
  hoop_seen       share of frames with a hoop detection at conf >= rim_conf
  hoop_move_p95   95th percentile of the hoop centre's displacement from its
                  median, in hoop widths (0 = static, larger = panning)
  hoop_size_ratio 95th / 5th percentile of hoop width over its median width
                  (a zoom indicator; 1 = constant zoom)
  multi_ball      share of frames with 2+ well-separated confident balls

Usage:
  python experiments/camera_profile.py
  python experiments/camera_profile.py --clips video_test_5.mp4
  python experiments/camera_profile.py --json experiments/results/camera_profile.json
"""
from __future__ import annotations

import argparse
import json
import sys
from math import hypot
from pathlib import Path
from statistics import median

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

BALL_CONF = 0.5  # "confident ball" floor for the multi-ball measure


def _percentile(sorted_values: list[float], q: float) -> float:
    """Linear-interpolated percentile of an already-sorted, non-empty list."""
    k = (len(sorted_values) - 1) * q
    lo = int(k)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = k - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


def hoop_metrics(dets: list, rim_conf: float) -> tuple[float, float, float]:
    """Return (hoop_seen, hoop_move_p95, hoop_size_ratio) from per-frame dets.

    `dets` is one list of Detection per frame. Each Detection is duck-typed:
    it needs `class_name`, `conf` and `bbox = (x1, y1, x2, y2)`.
    """
    centres: list[tuple[float, float, float]] = []
    seen = 0
    for frame in dets:
        hoops = [d for d in frame if d.class_name == "hoop" and d.conf >= rim_conf]
        if not hoops:
            continue
        seen += 1
        best = max(hoops, key=lambda d: d.conf)
        x1, y1, x2, y2 = best.bbox
        centres.append(((x1 + x2) / 2, (y1 + y2) / 2, x2 - x1))

    hoop_seen = seen / len(dets) if dets else 0.0
    if not centres:
        return hoop_seen, 0.0, 1.0
    med_cx = median(c[0] for c in centres)
    med_cy = median(c[1] for c in centres)
    med_w = median(c[2] for c in centres)
    if med_w <= 0:
        return hoop_seen, 0.0, 1.0

    disps = sorted(hypot(cx - med_cx, cy - med_cy) / med_w for cx, cy, _ in centres)
    move = _percentile(disps, 0.95)
    ratios = sorted(w / med_w for _, _, w in centres)
    size_ratio = _percentile(ratios, 0.95) / _percentile(ratios, 0.05)
    return hoop_seen, move, size_ratio


def _well_separated_pair(balls: list) -> bool:
    """True if any two balls' centres are more than two of the larger ball's
    width apart (so two overlapping boxes of one ball never count)."""
    for i in range(len(balls)):
        xa1, ya1, xa2, ya2 = balls[i].bbox
        wa = xa2 - xa1
        cax, cay = (xa1 + xa2) / 2, (ya1 + ya2) / 2
        for j in range(i + 1, len(balls)):
            xb1, yb1, xb2, yb2 = balls[j].bbox
            wb = xb2 - xb1
            cbx, cby = (xb1 + xb2) / 2, (yb1 + yb2) / 2
            if hypot(cax - cbx, cay - cby) > 2 * max(wa, wb):
                return True
    return False


def multi_ball_share(dets: list, ball_conf: float = BALL_CONF) -> float:
    """Share of frames with 2+ confident balls more than 2 ball-widths apart."""
    if not dets:
        return 0.0
    multi = 0
    for frame in dets:
        balls = [d for d in frame if d.class_name == "ball" and d.conf >= ball_conf]
        if _well_separated_pair(balls):
            multi += 1
    return multi / len(dets)


def profile_rows(clips: list[str]) -> list[dict]:
    """Measure every clip from cached detections (never loads the model)."""
    import evaluate as ev  # lazy: keeps the pure functions importable without torch

    config = ev.load_config()
    labels = ev.load_labels()
    rows = []
    for clip in clips:
        path = ev.CLIPS_DIR / clip
        if clip not in labels:
            continue
        dets = ev.load_detections(path, config)
        hoop_seen, hoop_move, hoop_ratio = hoop_metrics(dets, config.model.rim_conf)
        rows.append({
            "clip": clip,
            "frames": len(dets),
            "fps": round(ev.clip_fps(path), 3),
            "hoop_seen": round(hoop_seen, 3),
            "hoop_move_p95": round(hoop_move, 3),
            "hoop_size_ratio": round(hoop_ratio, 3),
            "multi_ball": round(multi_ball_share(dets), 3),
        })
    return rows


def _print_table(rows: list[dict]) -> None:
    widths = {
        "clip": 58, "frames": 7, "fps": 6, "hoop_seen": 10,
        "hoop_move_p95": 14, "hoop_size_ratio": 15, "multi_ball": 10,
    }
    order = ["clip", "frames", "fps", "hoop_seen", "hoop_move_p95", "hoop_size_ratio", "multi_ball"]
    header = "  ".join(f"{k:<{widths[k]}}" for k in order)
    print(header)
    print("  ".join("-" * widths[k] for k in order))
    for row in rows:
        print("  ".join(f"{str(row[k]):<{widths[k]}}" for k in order))


def main() -> int:
    import evaluate as ev  # lazy: only the CLI path needs the pipeline imports

    p = argparse.ArgumentParser(description="Measure each labeled clip's camera from cached detections")
    p.add_argument("--clips", nargs="*", help="Only these clip filenames")
    p.add_argument("--json", help="Also write the rows as JSON here")
    args = p.parse_args()

    labels = ev.load_labels()
    clips = [c for c in labels if not args.clips or c in args.clips]
    rows = profile_rows(clips)
    _print_table(rows)
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
