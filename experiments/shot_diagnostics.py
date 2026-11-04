"""Per-shot diagnostics: which exit path decided each shot, what the ball did
just before, and, for every labeled shot the pipeline got wrong, which layer
lost it (detector, tracker association, or shot logic).

Read-only with respect to the pipeline: replays the cached raw detections in
experiments/.cache/detections through the real BallTracker, RimTracker and
ShotStateMachine via scripts/evaluate.py, exactly as evaluate.py does. With
--cache-only it refuses to run detection (and so never loads the .pt).

Positions are reported in rim units so clips are comparable:
  ry = (y - hoop_box_top) / hoop_box_height   (0 = top of hoop box, 1 = bottom;
       the scoring line is at shot_logic.scoring_line_fraction, 0.4)
  rx = (x - hoop_center_x) / hoop_box_width   (|rx| <= 0.35 is inside the
       inner gate with inner_bound_shrink=0.15)

Usage:
  python experiments/shot_diagnostics.py                 # summary + failures
  python experiments/shot_diagnostics.py --all-shots     # every resolved shot
  python experiments/shot_diagnostics.py --json out.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import evaluate as ev  # noqa: E402
from shotvision.config.settings import load_config  # noqa: E402


def rim_units(x: float, y: float, rim) -> tuple[float, float]:
    h = rim.outer_bottom - rim.outer_top
    return (x - rim.center_x) / rim.outer_width, (y - rim.outer_top) / h


def zone(ry: float) -> str:
    return "above" if ry < 0 else ("below" if ry > 1 else "band")


def longest_none_run(entries: list[bool]) -> int:
    longest = run = 0
    for seen in entries:
        run = 0 if seen else run + 1
        longest = max(longest, run)
    return longest


def frame_rows(dets, rep, start: int, end: int, conf: float, align_tol: float) -> list[dict]:
    """One row per frame: best raw ball detection, followed observation, state."""
    rows = []
    for f in range(max(0, start), min(end + 1, len(rep.frames))):
        st = rep.frames[f]
        rim = st.rim
        balls = [d for d in dets[f] if d.class_name == "ball"]
        best = max(balls, key=lambda d: d.conf) if balls else None
        row = {"f": f, "armed": st.armed, "raw_n": len(balls),
               "raw_conf": round(best.conf, 2) if best else None}
        if best is not None and rim is not None:
            rx, ry = rim_units(*best.center, rim)
            row["raw_rx"], row["raw_ry"] = round(rx, 2), round(ry, 2)
            row["raw_confident"] = best.conf >= conf
        if st.obs is not None and rim is not None:
            rx, ry = rim_units(st.obs.x, st.obs.y, rim)
            row.update(obs_rx=round(rx, 2), obs_ry=round(ry, 2), weak=st.obs.weak,
                       tid=st.obs.track_id, zone=zone(ry),
                       aligned=rim.is_aligned(st.obs.x, align_tol))
        rows.append(row)
    return rows


def classify_unresolved(rows: list[dict]) -> str:
    """Why did a labeled shot never arm? Arming needs >= 2 (descent_min_frames)
    confirmed, aligned, above-rim, non-ascending observations."""
    raw_above = [r for r in rows if r.get("raw_confident") and r.get("raw_ry", 9) < 0
                 and abs(r.get("raw_rx", 9)) <= 1.0]
    obs_above = [r for r in rows if "obs_ry" in r and not r["weak"] and r["zone"] == "above"
                 and r["aligned"]]
    if len(raw_above) < 2:
        any_raw_above = [r for r in rows if r.get("raw_ry", 9) < 0 and abs(r.get("raw_rx", 9)) <= 1.0]
        return (f"DETECTOR: only {len(raw_above)} confident above-rim aligned raw detections "
                f"({len(any_raw_above)} at any conf)")
    if len(obs_above) < 2:
        return (f"TRACKER: {len(raw_above)} confident above-rim raw detections, but only "
                f"{len(obs_above)} became followed observations")
    return f"LOGIC: {len(obs_above)} above-rim aligned observations but no arm (descent/streak rule)"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cache-only", action="store_true", help="Exit instead of running detection")
    p.add_argument("--all-shots", action="store_true")
    p.add_argument("--json", help="Write per-shot records here")
    args = p.parse_args()

    config = load_config()
    conf = config.model.conf
    align_tol = config.shot_logic.align_tolerance_ratio
    labels = ev.load_labels()
    records, reason_counter, failures = [], Counter(), []

    for clip, shots in labels.items():
        path = ev.CLIPS_DIR / clip
        if args.cache_only and not ev._cache_path(path, config).exists():
            print(f"[cache-only] no detection cache for {clip}; stopping")
            return 2
        dets = ev.load_detections(path, config)
        rep = ev.replay(dets, config)
        score = ev.score_clip(clip, shots, rep, 0.6, 6)
        matched = {id(c.result): c for c in score.checks if c.result is not None}

        for r in rep.results:
            check = matched.get(id(r))
            label = check.label["outcome"] if check else "SPURIOUS"
            correct = check is not None and label == r.outcome.value
            armed_start = r.frame_idx - r.armed_frames
            rim = rep.frames[r.frame_idx].rim
            # Last confirmed (non-weak) positions before resolution, in rim units.
            last_pts = []
            for f in range(r.frame_idx, armed_start - 1, -1):
                o = rep.frames[f].obs
                if o is not None and not o.weak and rim is not None:
                    rx, ry = rim_units(o.x, o.y, rim)
                    last_pts.append((f, round(rx, 2), round(ry, 2)))
                if len(last_pts) == 4:
                    break
            seen = [rep.frames[f].obs is not None and not rep.frames[f].obs.weak
                    for f in range(armed_start, r.frame_idx + 1)]
            rec = {
                "clip": clip, "frame": r.frame_idx, "outcome": r.outcome.value, "label": label,
                "correct": correct, "reason": r.reason.value if r.reason else None,
                "armed_frames": r.armed_frames, "entered_inner": r.entered_inner,
                "no_ball_frames_before_resolve": r.occlusion_frames_before_resolve,
                "longest_confirmed_gap_while_armed": longest_none_run(seen),
                "weak_frames_while_armed": sum(
                    1 for f in range(armed_start, r.frame_idx + 1)
                    if rep.frames[f].obs is not None and rep.frames[f].obs.weak),
                "last_confirmed_points_rim_units": last_pts,
            }
            records.append(rec)
            reason_counter[(rec["reason"], label, rec["outcome"])] += 1

        for c in score.checks:
            if c.result is not None and c.result.outcome.value == c.label["outcome"]:
                continue
            lo, hi = c.label["start"] - 15, c.label["end"] + 5
            rows = frame_rows(dets, rep, lo, hi, conf, align_tol)
            cause = classify_unresolved(rows) if c.result is None else (
                f"RESOLVED WRONG via {c.result.reason.value}")
            failures.append({"clip": clip, "label": c.label, "cause": cause, "rows": rows,
                             "result": None if c.result is None else {
                                 "frame": c.result.frame_idx, "reason": c.result.reason.value,
                                 "trace": c.result.recent_trace}})

    print("=== Exit-path breakdown (reason, label, outcome): count ===")
    for (reason, label, outcome), n in sorted(reason_counter.items(), key=lambda kv: -kv[1]):
        print(f"  {reason:<26} label={label:<8} got={outcome:<4} : {n}")
    unresolved = sum(1 for f in failures if f["result"] is None)
    print(f"\nLabeled shots never resolved (never armed): {unresolved}")
    timeouts = sum(1 for r in records if r["reason"] and "timeout" in r["reason"])
    print(f"Shots resolved by a timeout path: {timeouts}")

    makes = [r for r in records if r["outcome"] == "MAKE"]
    if makes:
        gaps = sorted(r["longest_confirmed_gap_while_armed"] for r in makes)
        print(f"Resolved MAKEs: longest confirmed-ball gap while armed: median {gaps[len(gaps)//2]}, "
              f"max {gaps[-1]}; weak-only frames bridged in {sum(1 for r in makes if r['weak_frames_while_armed'])}"
              f"/{len(makes)}")
    misses = [r for r in records if r["outcome"] == "MISS"]
    for r in misses:
        print(f"  MISS {r['clip']} f{r['frame']} label={r['label']} via {r['reason']}: "
              f"no-ball before resolve {r['no_ball_frames_before_resolve']}, "
              f"armed {r['armed_frames']}f, last pts {r['last_confirmed_points_rim_units']}")

    if args.all_shots:
        print("\n=== Every resolved shot ===")
        for r in records:
            print(json.dumps(r))

    print("\n=== Failures ===")
    for f in failures:
        lab = f["label"]
        print(f"\n## {f['clip']} {lab['outcome']} [{lab['start']}-{lab['end']}]: {f['cause']}")
        if f["result"]:
            print(f"   resolved f{f['result']['frame']} ({f['result']['reason']}); trace {f['result']['trace']}")
        print("   f    st  raw(conf,rx,ry)        followed(rx,ry,zone,weak,tid)")
        for row in f["rows"]:
            raw = (f"{row['raw_conf']},{row.get('raw_rx')},{row.get('raw_ry')}"
                   if row["raw_conf"] is not None else "-")
            obs = (f"{row['obs_rx']},{row['obs_ry']},{row['zone']},{'W' if row['weak'] else 'C'},{row['tid']}"
                   + ("" if row["aligned"] else ",unaligned")) if "obs_rx" in row else "-"
            print(f"   {row['f']:<5}{'A' if row['armed'] else '.'}   {raw:<22} {obs}")

    if args.json:
        Path(args.json).write_text(json.dumps({"shots": records, "failures": failures}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
