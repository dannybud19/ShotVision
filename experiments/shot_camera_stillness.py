"""Count labelled shots taken while the camera was still (report only).

Phase 1 needs 50 in-scope (fixed camera, single ball) misses and has 8. A
broadcast game is tagged "moving" as a whole, but its camera often holds still
for a few seconds. This script measures the camera around every labelled MAKE
or MISS, using the same hoop measures and the same thresholds as
`experiments/camera_profile.py` but on one shot's window instead of a whole
clip, and counts how many shots were still. It also shows how ShotVision
scored them. It changes no tag, label, config value or gate, and reads only the
cached detections (it never loads the model).

Window for a shot: frames [start - 1.0 s, end + 0.5 s], clamped to the clip.
A shot is STILL when, on that window (hoop confidence = config.model.rim_conf):
  hoop_seen >= 0.8   and   move_p95 < 0.5   and   size_ratio < 1.3

Usage:
  python experiments/shot_camera_stillness.py
  python experiments/shot_camera_stillness.py --clips video_test_5.mp4
  python experiments/shot_camera_stillness.py --out experiments/results/shot_camera_stillness.md \\
      --json experiments/results/shot_camera_stillness.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from experiments.camera_profile import hoop_metrics  # noqa: E402
from shotvision.config.settings import to_frames  # noqa: E402

LEAD_S = 1.0  # window starts this long before the label's start
TAIL_S = 0.5  # window ends this long after the label's end
MIN_HOOP_SEEN = 0.8
MAX_MOVE_P95 = 0.5
MAX_SIZE_RATIO = 1.3
# The arguments scripts/evaluate.py main() passes to score_clip (its defaults).
MIN_COVERAGE = 0.6
MAX_GAP_S = 0.2
CLASS_ORDER = ("fixed/single", "fixed/multi", "moving/single", "moving/multi", "unclassified")


def shot_window(start: int, end: int, fps: float, n_frames: int) -> tuple[int, int]:
    """Frames [lo, hi) of the window around a shot, clamped to the clip.
    `end` is inclusive in the label, so the window includes frame end + tail."""
    lo = max(0, start - to_frames(LEAD_S, fps))
    hi = min(n_frames, end + to_frames(TAIL_S, fps) + 1)
    return lo, max(lo, hi)


def window_stillness(window_dets: list, rim_conf: float) -> dict:
    """Hoop measures on one window of per-frame detections, and the verdict."""
    hoop_seen, move_p95, size_ratio = hoop_metrics(window_dets, rim_conf)
    still = hoop_seen >= MIN_HOOP_SEEN and move_p95 < MAX_MOVE_P95 and size_ratio < MAX_SIZE_RATIO
    return {"hoop_seen": hoop_seen, "move_p95": move_p95, "size_ratio": size_ratio, "still": still}


def shot_stillness(dets: list, start: int, end: int, fps: float, rim_conf: float) -> dict:
    lo, hi = shot_window(start, end, fps, len(dets))
    return window_stillness(dets[lo:hi], rim_conf)


def class_key(entry: dict) -> str:
    cc, bc = entry.get("camera_class"), entry.get("ball_count")
    return f"{cc}/{bc}" if cc and bc else "unclassified"


def _resolved(result) -> str:
    if result is None:
        return "NOT RESOLVED"
    reason = result.reason.value if result.reason else "?"
    return f"{result.outcome.value} @f{result.frame_idx} ({reason})"


def collect(clips: list[str] | None) -> tuple[list[dict], dict]:
    """One record per labelled MAKE/MISS shot, plus scoreboard totals for a cross-check."""
    import evaluate as ev  # lazy: keeps the pure functions above importable without torch

    config = ev.load_config()
    labels = ev.load_labels(split="all", include_duplicates=False)
    meta = ev.load_clip_meta()
    records: list[dict] = []
    totals = {"makes": 0, "counted": 0, "misses": 0, "false_makes": 0, "spurious_makes": 0}
    for clip in labels:
        if clips and clip not in clips:
            continue
        path = ev.CLIPS_DIR / clip
        if not path.exists():
            print(f"[SKIP] {clip}: file not found in sample_clips/", file=sys.stderr)
            continue
        fps = ev.clip_fps(path)
        dets = ev.load_detections(path, config)
        rep = ev.replay(dets, config, fps=fps)
        score = ev.score_clip(clip, labels[clip], rep, MIN_COVERAGE, to_frames(MAX_GAP_S, fps), fps)
        ck = class_key(meta.get(clip, {}))
        totals["spurious_makes"] += sum(1 for r in score.spurious if r.outcome.value == "MAKE")
        for c in score.checks:
            label = c.label
            got = c.result.outcome.value if c.result is not None else None
            is_make = label["outcome"] == "MAKE"
            false_make = (not is_make) and got == "MAKE"
            counted = got == "MAKE" if is_make else not false_make
            totals["makes" if is_make else "misses"] += 1
            totals["counted"] += 1 if (is_make and counted) else 0
            totals["false_makes"] += 1 if false_make else 0
            st = shot_stillness(dets, label["start"], label["end"], fps, config.model.rim_conf)
            records.append({
                "clip": clip,
                "camera_class": ck,
                "start": label["start"],
                "end": label["end"],
                "outcome": label["outcome"],
                "miss_type": label.get("miss_type") or "untyped",
                "card": label.get("card"),
                "still": st["still"],
                "hoop_seen": round(st["hoop_seen"], 3),
                "move_p95": round(st["move_p95"], 3),
                "size_ratio": round(st["size_ratio"], 3),
                "resolved": _resolved(c.result),
                "counted_correctly": counted,
                "false_make": false_make,
            })
    return records, totals


def _md_table(header: list[str], rows: list[list]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines += ["| " + " | ".join(str(x) for x in row) + " |" for row in rows]
    return lines


def build_report(records: list[dict], totals: dict) -> tuple[str, dict]:
    makes = [r for r in records if r["outcome"] == "MAKE"]
    misses = [r for r in records if r["outcome"] == "MISS"]
    out: list[str] = []

    # Table A: per camera class of the clip.
    out += ["## Table A: shots taken while the camera was still, by the clip's camera class", ""]
    rows = []
    for ck in CLASS_ORDER:
        mk = [r for r in makes if r["camera_class"] == ck]
        ms = [r for r in misses if r["camera_class"] == ck]
        if not mk and not ms:
            continue
        rows.append([ck, f"{sum(r['still'] for r in mk)}/{len(mk)}", f"{sum(r['still'] for r in ms)}/{len(ms)}"])
    rows.append(["**all**", f"{sum(r['still'] for r in makes)}/{len(makes)}",
                 f"{sum(r['still'] for r in misses)}/{len(misses)}"])
    out += _md_table(["camera class", "makes still / total", "misses still / total"], rows)

    # Table B: still shots only, by clip.
    out += ["", "## Table B: still shots only, by clip", ""]
    by_clip: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if r["still"]:
            by_clip[r["clip"]].append(r)
    rows = []
    for clip in sorted(by_clip):
        rs = by_clip[clip]
        sm = [r for r in rs if r["outcome"] == "MAKE"]
        sx = [r for r in rs if r["outcome"] == "MISS"]
        rows.append([clip, rs[0]["camera_class"], f"{sum(r['counted_correctly'] for r in sm)}/{len(sm)}",
                     f"{sum(r['false_make'] for r in sx)}/{len(sx)}"])
    out += _md_table(["clip", "camera class", "still makes counted / still makes",
                      "false makes / still misses"], rows)

    # Table C: still misses by miss type.
    out += ["", "## Table C: still misses by miss type", ""]
    by_type: dict[str, list[dict]] = defaultdict(list)
    for r in misses:
        if r["still"]:
            by_type[r["miss_type"]].append(r)
    rows = [[t, len(rs), sum(r["false_make"] for r in rs)] for t, rs in sorted(by_type.items())]
    still_misses = [r for r in misses if r["still"]]
    rows.append(["**all**", len(still_misses), sum(r["false_make"] for r in still_misses)])
    out += _md_table(["miss type", "still misses", "false makes"], rows)

    # Headline.
    outside = [r for r in still_misses if r["camera_class"] != "fixed/single"]
    n, f = len(outside), sum(r["false_make"] for r in outside)
    in_scope_misses = sum(1 for r in misses if r["camera_class"] == "fixed/single")
    out += [
        "",
        "## Headline",
        "",
        f"Still-camera misses outside fixed/single clips: {n} (false makes: {f})",
        f"If counted in scope: in-scope misses would be {in_scope_misses} + {n} = {in_scope_misses + n}",
    ]

    # Sanity checks from the plan (step 5.3).
    out += ["", "## Sanity checks", ""]
    out.append(f"Totals: labelled makes {len(makes)} (scoreboard {totals['makes']}), "
               f"labelled misses {len(misses)} (scoreboard {totals['misses']}).")
    out.append(f"Scoreboard cross-check: makes counted {totals['counted']}/{totals['makes']}, "
               f"labelled misses scored MAKE {totals['false_makes']}/{totals['misses']}, "
               f"spurious makes {totals['spurious_makes']}.")
    fs = [r for r in records if r["camera_class"] == "fixed/single"]
    not_still: dict[str, list[dict]] = defaultdict(list)
    for r in fs:
        if not r["still"]:
            not_still[r["clip"]].append(r)
    out.append(f"fixed/single shots that are not still: {sum(len(v) for v in not_still.values())}/{len(fs)}.")
    if not_still:
        out += [""]
        out += _md_table(["fixed/single clip", "shots not still / shots"],
                         [[c, f"{len(v)}/{sum(1 for r in fs if r['clip'] == c)}"] for c, v in sorted(not_still.items())])

    # Every still miss, for spot-checking with review_sheets.py frames.
    out += ["", "## Still misses (all classes), for spot-checking", ""]
    rows = []
    for r in sorted(still_misses, key=lambda r: (r["clip"], r["start"])):
        rows.append([r["clip"], r["camera_class"], r["start"], r["end"], r["miss_type"], r["card"] or "",
                     r["resolved"] + (" FALSE MAKE" if r["false_make"] else "")])
    out += _md_table(["clip", "camera class", "start", "end", "miss_type", "card", "ShotVision resolved"], rows)

    summary = {
        "still_misses_outside_fixed_single": n,
        "false_makes_among_them": f,
        "in_scope_misses": in_scope_misses,
        "in_scope_misses_if_counted": in_scope_misses + n,
    }
    return "\n".join(out) + "\n", summary


def main() -> int:
    p = argparse.ArgumentParser(description="Count labelled shots taken while the camera was still")
    p.add_argument("--clips", nargs="*", help="Only these clip filenames")
    p.add_argument("--out", help="Also write the report as Markdown here")
    p.add_argument("--json", help="Also write the per-shot records as JSON here")
    args = p.parse_args()

    records, totals = collect(args.clips)
    report, summary = build_report(records, totals)
    print(report)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(report)
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(
            {"summary": summary, "totals": totals, "shots": records}, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
