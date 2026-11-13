"""Release moment from the ball's arc alone (experiment, no model, report only).

Phase 2 (two or three points) needs to know WHEN the ball left the shooter's
hands, so it knows WHERE the shooter stood. A shot's flight is a smooth arc
(a parabola in image space, y increasing downward). Before release the ball
moves with the hands. The release is where the arc begins.

`find_release` walks back from the arc's apex, adding earlier ball positions
while one quadratic still fits them. It reads only the tracked ball positions
that the scoreboard replay already produces (`FrameState.obs`) and the cached
hoop detections. It never loads the model and nothing in shotvision/ uses it.

Usage:
  python experiments/release_moment.py
  python experiments/release_moment.py --clips lf_back.mp4
  python experiments/release_moment.py --out experiments/results/release_moment.md \\
      --json experiments/results/release_moment.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from shotvision.config.settings import to_frames  # noqa: E402

# Spec numbers (PLAN_5 A2.2). Do not tune.
MIN_POINTS = 6
NEAR_RIM_WIDTHS = 1.5  # "within 1.5 hoop widths horizontally of the hoop"
APEX_LOOKBACK_S = 2.0
APEX_FORWARD_S = 0.3  # the fit starts with the points from the apex to this long after it
MAX_RMS_BALL_WIDTHS = 0.25
MAX_GAP_S = 0.25
HOOP_CONF = 0.6
WINDOW_LEAD_S = 3.0
CLASS_ORDER = ("fixed/single", "fixed/multi", "moving/single", "moving/multi", "unclassified")


def _fail(reason: str) -> dict:
    return {"release_frame": None, "reason": reason}


def _fit(points: list[tuple], apex_f: int) -> tuple[float, float, float, float, float]:
    """Quadratic y(t) and line x(t), t = frame - apex frame. Returns
    (a, rms of y in ball widths, x slope, x rms in ball widths, median ball width)."""
    t = np.array([p[0] - apex_f for p in points], dtype=float)
    x = np.array([p[1] for p in points], dtype=float)
    y = np.array([p[2] for p in points], dtype=float)
    w = float(np.median([p[3] for p in points]))
    w = max(w, 1e-9)
    a, b, c = np.polyfit(t, y, 2)
    rms_y = float(np.sqrt(np.mean((y - np.polyval([a, b, c], t)) ** 2))) / w
    slope, icpt = np.polyfit(t, x, 1)
    rms_x = float(np.sqrt(np.mean((x - (slope * t + icpt)) ** 2))) / w
    return float(a), rms_y, float(slope), rms_x, w


def find_release(points: list[tuple], rim: tuple, fps: float) -> dict | None:
    """Release frame of one shot from its ball path.

    points: (frame_idx, cx, cy, w) for one shot window, gaps allowed.
    rim: (hx, hy, hw), the hoop centre and width.
    Returns None for fewer than 6 points. Otherwise a dict: on success it has
    `release_frame` (an int) and the fit details; on failure `release_frame`
    is None and `reason` says why ("no_apex").
    """
    if len(points) < MIN_POINTS:
        return None
    pts = sorted(points, key=lambda p: p[0])
    hx, hy, hw = rim

    # 1. Apex: highest point above the rim, within 2.0 s before the last point
    #    that is near the hoop horizontally.
    near = [p for p in pts if abs(p[1] - hx) <= NEAR_RIM_WIDTHS * hw]
    if not near:
        return _fail("no_apex")
    last_f = near[-1][0]
    first_f = last_f - to_frames(APEX_LOOKBACK_S, fps)
    cands = [i for i, p in enumerate(pts) if first_f <= p[0] <= last_f and p[2] < hy]
    if not cands:
        return _fail("no_apex")
    apex_i = min(cands, key=lambda i: pts[i][2])
    apex_f = pts[apex_i][0]

    # 2. Start with the apex and the points up to 0.3 s after it, then walk back.
    end_f = apex_f + to_frames(APEX_FORWARD_S, fps)
    hi = apex_i
    while hi + 1 < len(pts) and pts[hi + 1][0] <= end_f:
        hi += 1
    earliest = apex_i
    stop_reason = "ran_out"
    max_gap = to_frames(MAX_GAP_S, fps)
    for i in range(apex_i - 1, -1, -1):
        # 3. Stop on a gap, a residual above 0.25 ball widths, or a curve that
        #    does not fall the way gravity does in image space (a <= 0).
        if pts[earliest][0] - pts[i][0] > max_gap:
            stop_reason = "gap"
            break
        trial = pts[i:hi + 1]
        if len(trial) >= 3:  # a quadratic needs three points
            a, rms_y, _, _, _ = _fit(trial, apex_f)
            if rms_y > MAX_RMS_BALL_WIDTHS:
                stop_reason = "residual"
                break
            if a <= 0:
                stop_reason = "curvature"
                break
        earliest = i

    # 4. Release = the earliest point still in the accepted fit.
    accepted = pts[earliest:hi + 1]
    rel_f, rel_x, rel_y, _ = pts[earliest]
    out = {
        "release_frame": int(rel_f),
        "release_xy": [float(rel_x), float(rel_y)],
        "release_rim_units": [float((rel_x - hx) / hw), float((rel_y - hy) / hw)],
        "apex_frame": int(apex_f),
        "flight_frames": int(apex_f - rel_f),
        "fit_points": len(accepted),
        "rms": None,
        "x_slope_px_per_frame": None,
        "stop_reason": stop_reason,
    }
    if len(accepted) >= 3:
        _, rms_y, slope, _, _ = _fit(accepted, apex_f)
        out["rms"] = rms_y
        out["x_slope_px_per_frame"] = slope
    return out


# ---------------------------------------------------------------------------
# Runner (reads the detection cache; never loads the model)
# ---------------------------------------------------------------------------


def shot_window(start: int, end: int, fps: float, n_frames: int) -> tuple[int, int]:
    """Frames [lo, hi] (inclusive) from 3.0 s before the label's start to its end, clamped."""
    return max(0, start - to_frames(WINDOW_LEAD_S, fps)), min(n_frames - 1, end)


def window_rim(dets: list, lo: int, hi: int) -> tuple | None:
    """Hoop centre and width: median over the window of each frame's best hoop box (conf >= 0.6)."""
    xs, ys, ws = [], [], []
    for f in range(lo, hi + 1):
        hoops = [d for d in dets[f] if d.class_name == "hoop" and d.conf >= HOOP_CONF]
        if not hoops:
            continue
        x1, y1, x2, y2 = max(hoops, key=lambda d: d.conf).bbox
        xs.append((x1 + x2) / 2)
        ys.append((y1 + y2) / 2)
        ws.append(x2 - x1)
    if not xs:
        return None
    return float(np.median(xs)), float(np.median(ys)), float(np.median(ws))


def window_points(rep, lo: int, hi: int) -> list[tuple]:
    """The tracked ball (weak observations included) as (frame, cx, cy, width)."""
    pts = []
    for f in range(lo, min(hi, len(rep.frames) - 1) + 1):
        obs = rep.frames[f].obs
        if obs is not None:
            pts.append((f, obs.x, obs.y, obs.right - obs.left))
    return pts


def class_key(entry: dict) -> str:
    cc, bc = entry.get("camera_class"), entry.get("ball_count")
    return f"{cc}/{bc}" if cc and bc else "unclassified"


def collect(clips: list[str] | None) -> list[dict]:
    import evaluate as ev  # lazy: keeps find_release importable without the pipeline

    config = ev.load_config()
    labels = ev.load_labels(split="all", include_duplicates=False)
    meta = ev.load_clip_meta()
    records: list[dict] = []
    for clip in labels:
        if clips and clip not in clips:
            continue
        path = ev.CLIPS_DIR / clip
        if not path.exists():
            print(f"[SKIP] {clip}: file not found in sample_clips/", file=sys.stderr)
            continue
        if not ev._cache_path(path, config).exists():
            sys.exit(f"no detection cache for {clip}; this script never runs detection")
        fps = ev.clip_fps(path)
        dets = ev.load_detections(path, config)
        rep = ev.replay(dets, config, fps=fps)
        ck = class_key(meta.get(clip, {}))
        for shot in labels[clip]:
            if shot["outcome"] not in ("MAKE", "MISS"):
                continue
            lo, hi = shot_window(shot["start"], shot["end"], fps, len(dets))
            points = window_points(rep, lo, hi)
            rim = window_rim(dets, lo, hi)
            if rim is None:
                result = _fail("no_hoop")
            else:
                result = find_release(points, rim, fps)
                if result is None:
                    result = _fail("too_few_points")
            records.append({
                "clip": clip,
                "label_start": shot["start"],
                "label_end": shot["end"],
                "outcome": shot["outcome"],
                "card": shot.get("card"),
                "camera_class": ck,
                "fps": fps,
                "window": [lo, hi],
                "n_points": len(points),
                "rim": list(rim) if rim else None,
                **result,
            })
    return records


def _pct(values: list[float], q: float) -> float:
    return float(np.percentile(values, q))


def build_report(records: list[dict]) -> str:
    out = ["# Release moment from the ball's arc (PLAN_5 A2)", ""]
    out.append("Ball: the tracker's followed ball from the scoreboard replay (weak observations included). Window: 3.0 s before the "
               "label's start to its end. No model. Report only: no release frame has been checked against "
               "the footage yet.")
    out.append("")
    header = ("| camera class | shots | got a release | no release | median flight (s) | p90 flight (s) "
              "| median tracked points in window |")
    out += [header, "| --- | --- | --- | --- | --- | --- | --- |"]

    def row(label: str, rs: list[dict]) -> str:
        got = [r for r in rs if r["release_frame"] is not None]
        flights = [r["flight_frames"] / r["fps"] for r in got]
        med = f"{_pct(flights, 50):.2f}" if flights else "-"
        p90 = f"{_pct(flights, 90):.2f}" if flights else "-"
        pts = f"{_pct([r['n_points'] for r in rs], 50):.0f}" if rs else "-"
        return f"| {label} | {len(rs)} | {len(got)} | {len(rs) - len(got)} | {med} | {p90} | {pts} |"

    for ck in CLASS_ORDER:
        rs = [r for r in records if r["camera_class"] == ck]
        if rs:
            out.append(row(ck, rs))
    out.append(row("**all**", records))

    out += ["", "## Failure reasons (no release), by camera class", ""]
    reasons = sorted({r["reason"] for r in records if r["release_frame"] is None})
    if reasons:
        out += ["| camera class | " + " | ".join(reasons) + " |", "| --- | " + " | ".join("---" for _ in reasons) + " |"]
        for ck in CLASS_ORDER + ("**all**",):
            rs = records if ck == "**all**" else [r for r in records if r["camera_class"] == ck]
            if not rs:
                continue
            c = Counter(r["reason"] for r in rs if r["release_frame"] is None)
            out.append(f"| {ck} | " + " | ".join(str(c.get(x, 0)) for x in reasons) + " |")
    else:
        out.append("(none)")

    out += ["", "## Why the fit stopped (shots with a release)", ""]
    stops = Counter(r["stop_reason"] for r in records if r["release_frame"] is not None)
    out += ["| stop reason | shots |", "| --- | --- |"]
    out += [f"| {k} | {v} |" for k, v in sorted(stops.items())] or ["| (none) | 0 |"]
    out.append("")
    out.append(f"Shots processed: {len(records)} "
               f"({sum(r['outcome'] == 'MAKE' for r in records)} makes, "
               f"{sum(r['outcome'] == 'MISS' for r in records)} misses).")
    return "\n".join(out) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description="Release frame from the ball's arc, for every labelled shot")
    p.add_argument("--clips", nargs="*", help="Only these clip filenames")
    p.add_argument("--out", help="Also write the report as Markdown here")
    p.add_argument("--json", help="Also write one record per shot as JSON here")
    args = p.parse_args()

    records = collect(args.clips)
    report = build_report(records)
    print(report)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(report)
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(records, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
