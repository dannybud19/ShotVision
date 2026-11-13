"""How far is the ball-arc release finder from the owner's marked release frames?

Joins `sample_clips/release_labels.json` (owner-marked frames, PLAN_5) with
`experiments/results/release_moment.json` (the finder's output, one record per
shot) on clip + label start + label end. Error = finder frame minus owner
frame, so a negative error means the finder is early. Report only: it reads two
JSON files, loads no model and changes nothing.

Usage:
  python experiments/release_error.py
  python experiments/release_error.py --out experiments/results/release_error.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
LABELS_PATH = REPO_ROOT / "sample_clips" / "release_labels.json"
MOMENT_PATH = REPO_ROOT / "experiments" / "results" / "release_moment.json"
DECISIONS_PATH = REPO_ROOT / "docs" / "plans" / "PLAN_5_decisions.md"

WITHIN_NARROW = 2  # frames
WITHIN_WIDE = 5  # frames
WORST_N = 3


def join_rows(labels: dict, moment: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Join on (clip, label_start, label_end). Returns (scored, no_finder, unmatched):
    scored rows have both frames, no_finder rows are owner-marked shots where the
    finder gave no release, unmatched rows have no finder record at all."""
    index = {(r["clip"], r["label_start"], r["label_end"]): r for r in moment}
    scored, no_finder, unmatched = [], [], []
    for shot in labels["shots"]:
        key = (shot["clip"], shot["label_start"], shot["label_end"])
        rec = index.get(key)
        if rec is None:
            unmatched.append(shot)
            continue
        if rec.get("release_frame") is None:
            no_finder.append({**shot, "reason": rec.get("reason")})
            continue
        fps = float(rec.get("fps") or 30.0)
        err = int(rec["release_frame"]) - int(shot["release_frame"])
        scored.append({
            "clip": shot["clip"],
            "label_start": shot["label_start"],
            "label_end": shot["label_end"],
            "owner": int(shot["release_frame"]),
            "finder": int(rec["release_frame"]),
            "error": err,
            "error_ms": 1000.0 * err / fps,
            "stop_reason": rec.get("stop_reason"),
        })
    return scored, no_finder, unmatched


def summarise(scored: list[dict]) -> dict:
    """Error statistics over the scored rows (empty input gives n = 0 only)."""
    if not scored:
        return {"n": 0}
    err = np.array([r["error"] for r in scored], dtype=float)
    ms = np.array([r["error_ms"] for r in scored], dtype=float)
    abs_f, abs_ms = np.abs(err), np.abs(ms)
    worst = sorted(scored, key=lambda r: (-abs(r["error"]), r["clip"], r["label_start"]))[:WORST_N]
    return {
        "n": len(scored),
        "median_abs_frames": float(np.median(abs_f)),
        "median_abs_ms": float(np.median(abs_ms)),
        "p90_abs_frames": float(np.percentile(abs_f, 90)),
        "p90_abs_ms": float(np.percentile(abs_ms, 90)),
        "within_2": int((abs_f <= WITHIN_NARROW).sum()),
        "within_5": int((abs_f <= WITHIN_WIDE).sum()),
        "signed_mean_frames": float(err.mean()),
        "signed_mean_ms": float(ms.mean()),
        "worst": worst,
    }


def count_cant_tell(decisions_path: Path) -> int | None:
    """CANT_TELL rows in the owner's decisions table (release_labels.json holds
    integer rows only, so they can only be counted there). None if no file."""
    if not decisions_path.exists():
        return None
    n = 0
    for line in decisions_path.read_text().splitlines():
        if not re.match(r"\| \d+ \|", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) > 5 and cells[5] == "CANT_TELL":
            n += 1
    return n


def build_report(scored: list[dict], no_finder: list[dict], unmatched: list[dict], cant_tell: int | None) -> str:
    s = summarise(scored)
    lines = [
        "# Release finder error (PLAN_5 Part B)",
        "",
        "Error = finder frame minus owner frame. Negative means the finder is early.",
        "",
        f"- Owner rows scored: {s['n']}",
        f"- Owner rows where the finder gave no release: {len(no_finder)}",
        f"- Owner rows with no finder record: {len(unmatched)}",
        f"- CANT_TELL rows: {'n/a (decisions file not found)' if cant_tell is None else cant_tell}",
        "",
    ]
    if s["n"] == 0:
        lines.append("No rows to score.")
        return "\n".join(lines) + "\n"
    n = s["n"]
    lines += [
        "| Measure | Frames | Milliseconds |",
        "| --- | --- | --- |",
        f"| Median absolute error | {s['median_abs_frames']:.1f} | {s['median_abs_ms']:.0f} |",
        f"| p90 absolute error | {s['p90_abs_frames']:.1f} | {s['p90_abs_ms']:.0f} |",
        f"| Signed mean (early < 0 < late) | {s['signed_mean_frames']:+.2f} | {s['signed_mean_ms']:+.0f} |",
        "",
        "| Within | Shots | Share |",
        "| --- | --- | --- |",
        f"| ±{WITHIN_NARROW} frames | {s['within_2']}/{n} | {100 * s['within_2'] / n:.0f}% |",
        f"| ±{WITHIN_WIDE} frames | {s['within_5']}/{n} | {100 * s['within_5'] / n:.0f}% |",
        "",
        f"Worst {len(s['worst'])}:",
        "",
        "| Clip | Label start-end | Owner | Finder | Error | Stop reason |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in s["worst"]:
        lines.append(
            f"| {r['clip']} | {r['label_start']}-{r['label_end']} | {r['owner']} | {r['finder']} "
            f"| {r['error']:+d} | {r['stop_reason']} |"
        )
    lines += ["", "All rows:", "", "| Clip | Label start-end | Owner | Finder | Error | Stop reason |", "| --- | --- | --- | --- | --- | --- |"]
    for r in scored:
        lines.append(
            f"| {r['clip']} | {r['label_start']}-{r['label_end']} | {r['owner']} | {r['finder']} "
            f"| {r['error']:+d} | {r['stop_reason']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description="Release finder error against the owner's marked frames")
    p.add_argument("--labels", default=str(LABELS_PATH))
    p.add_argument("--moment", default=str(MOMENT_PATH))
    p.add_argument("--decisions", default=str(DECISIONS_PATH), help="decisions table, only to count CANT_TELL rows")
    p.add_argument("--out", help="Also write the report as Markdown here")
    args = p.parse_args()

    labels = json.loads(Path(args.labels).read_text())
    moment = json.loads(Path(args.moment).read_text())
    scored, no_finder, unmatched = join_rows(labels, moment)
    report = build_report(scored, no_finder, unmatched, count_cant_tell(Path(args.decisions)))
    print(report)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
