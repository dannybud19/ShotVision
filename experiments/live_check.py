"""Headless live check: does the pipeline run in real time, and does a live run
give the same shots as the recorded (cached) replay?

THE OWNER RUNS THIS. It loads the model (models/basketball_best.pt).

It builds the pipeline the way shotvision/main.py run() does (same classes,
arguments and order) but with no window, HUD or keyboard. It measures
processing fps, per-frame latency (from source.read() returning to the shot
logic update finishing, so it includes detection) and collects every resolved
shot. With --compare-to-replay (file sources only) it replays the cached
detections for the same clip through scripts/evaluate.py's replay() and pairs
the two shot lists.

Usage:
  python experiments/live_check.py --source sample_clips/lf_shot_detection.mp4 \\
      --compare-to-replay --results-out experiments/results/live_check_file.json
  python experiments/live_check.py --source 0 --seconds 60 \\
      --results-out experiments/results/live_check_camera.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import evaluate as ev  # noqa: E402  (light: no model is loaded at import)
from shotvision.config.settings import load_config, to_frames  # noqa: E402


# ---------------------------------------------------------------------------
# Plain function: tested in tests/test_live_check.py
# ---------------------------------------------------------------------------


def compare_results(live: list, replayed: list, tol_frames: int) -> tuple[list, list, list]:
    """Pair each live shot with the closest unpaired replayed shot that has the
    same outcome and a frame within tol_frames. Returns (pairs, live_only,
    replay_only); pairs are (live_shot, replay_shot). Shots are ShotResult-like
    (.outcome, .frame_idx)."""
    unpaired = list(replayed)
    pairs, live_only = [], []
    for shot in live:
        candidates = [
            r for r in unpaired
            if r.outcome == shot.outcome and abs(r.frame_idx - shot.frame_idx) <= tol_frames
        ]
        if not candidates:
            live_only.append(shot)
            continue
        best = min(candidates, key=lambda r: abs(r.frame_idx - shot.frame_idx))
        unpaired.remove(best)
        pairs.append((shot, best))
    return pairs, live_only, unpaired


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(pct / 100 * (len(ordered) - 1)))]


# ---------------------------------------------------------------------------
# Live run (loads the model; only called from main())
# ---------------------------------------------------------------------------


def run_live(config, seconds: float | None, loop: bool = False) -> dict:
    from shotvision.capture.source import FrameSource
    from shotvision.detection.detector import Detector
    from shotvision.detection.device import log_device_choice, resolve_device
    from shotvision.shot_logic.rim_tracker import RimTracker
    from shotvision.shot_logic.state_machine import ShotStateMachine
    from shotvision.stats.tracker import StatsTracker
    from shotvision.tracking.ball_tracker import BallTracker

    device, reason = resolve_device(config.model.device)
    log_device_choice(device, reason)
    detector = Detector(config.model, device)
    stats = StatsTracker()
    state_machine: ShotStateMachine | None = None
    shots, results, latencies = [], [], []

    with FrameSource(config.camera.source, loop=loop) as source:
        fps = config.camera.fps or source.fps
        ball_tracker = BallTracker(
            detector, config.tracker, to_frames(config.shot_logic.trajectory_buffer_s, fps), fps=fps
        )
        rim_tracker = RimTracker(config.model, config.shot_logic, fps=fps)
        frame_idx = 0
        started = time.perf_counter()
        while True:
            if seconds is not None and time.perf_counter() - started >= seconds:
                break
            frame = source.read()
            if frame is None:
                break
            t0 = time.perf_counter()

            detections = ball_tracker.detect(frame)
            rim = rim_tracker.update(detections)
            ball_tracker.ingest(
                detections,
                rim=rim,
                locked_track_id=state_machine.armed_track_id if state_machine else None,
            )
            if rim is not None:
                if state_machine is None:
                    state_machine = ShotStateMachine(rim, config.shot_logic, fps=fps)
                else:
                    state_machine.rim = rim
            elif state_machine is not None:
                state_machine.rim = None  # hoop lost: no arming; an armed shot is cancelled
            if state_machine is not None:
                result = state_machine.update(ball_tracker.current_frame_ball_obs, frame_idx)
                if result is not None:
                    stats.record(result)
                    results.append(result)
                    shots.append({
                        "frame_idx": result.frame_idx,
                        "outcome": result.outcome.value,
                        "reason": result.reason.value if result.reason else None,
                    })
            latencies.append((time.perf_counter() - t0) * 1000)
            frame_idx += 1
        wall = time.perf_counter() - started
        source_fps = source.fps

    processing_fps = frame_idx / wall if wall > 0 else 0.0
    return {
        "source": str(config.camera.source),
        "frames": frame_idx,
        "wall_seconds": wall,
        "fps_used_for_timing": fps,
        "source_fps": source_fps,
        "processing_fps": processing_fps,
        "real_time": processing_fps >= source_fps,
        "latency_ms_p50": statistics.median(latencies) if latencies else 0.0,
        "latency_ms_p95": percentile(latencies, 95),
        "shots": shots,
        "makes": sum(1 for s in shots if s["outcome"] == "MAKE"),
        "misses": sum(1 for s in shots if s["outcome"] == "MISS"),
        "_results": results,  # ShotResult objects, for the comparison (not written to JSON)
    }


def print_summary(summary: dict) -> None:
    print("\n=== Live check ===")
    print(f"source: {summary['source']}   source fps: {summary['source_fps']:.2f}   "
          f"processing fps: {summary['processing_fps']:.2f}   "
          f"real time: {'YES' if summary['real_time'] else 'NO'} (processing fps >= source fps)")
    print(f"latency ms p50: {summary['latency_ms_p50']:.1f}  p95: {summary['latency_ms_p95']:.1f}")
    print(f"shots: {len(summary['shots'])}  makes: {summary['makes']}  misses: {summary['misses']}")


def compare_to_replay(config, summary: dict, seconds: float | None) -> dict | None:
    """Replay the cached detections for the same clip and pair the shot lists.
    Never runs detection: with no cache it skips."""
    source = summary["source"]
    if source.isdigit() or "://" in source:
        print("compare skipped: not a file")
        return None
    path = Path(source)
    if not ev._cache_path(path, config).exists():
        print("compare skipped: no cached detections for this clip (this script never recollects them)")
        return None
    fps = summary["fps_used_for_timing"]
    dets = ev.load_detections(path, config)
    if seconds is not None:
        dets = dets[: summary["frames"]]  # a time-limited live run only saw this many frames
    replayed = ev.replay(dets, config, fps=fps).results
    pairs, live_only, replay_only = compare_results(
        summary["_results"], replayed, tol_frames=to_frames(0.2, fps)
    )
    print("\nCompare with cached replay:")
    for live_shot, replay_shot in pairs:
        print(f"  paired    {live_shot.outcome.value} live f{live_shot.frame_idx}  "
              f"replay f{replay_shot.frame_idx}  (diff {live_shot.frame_idx - replay_shot.frame_idx:+d})")
    for s in live_only:
        print(f"  live only   {s.outcome.value} f{s.frame_idx}")
    for s in replay_only:
        print(f"  replay only {s.outcome.value} f{s.frame_idx}")
    unmatched = len(live_only) + len(replay_only)
    verdict = "COMPARE: SAME" if unmatched == 0 else f"COMPARE: DIFFERENT ({unmatched} unmatched)"
    print(verdict)
    return {
        "verdict": verdict,
        "pairs": [{"live": l.frame_idx, "replay": r.frame_idx, "outcome": l.outcome.value} for l, r in pairs],
        "live_only": [{"frame_idx": s.frame_idx, "outcome": s.outcome.value} for s in live_only],
        "replay_only": [{"frame_idx": s.frame_idx, "outcome": s.outcome.value} for s in replay_only],
    }


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Headless live check (loads the model; the owner runs it)")
    p.add_argument("--source", required=True, help="video file, device index or stream URL")
    p.add_argument("--seconds", type=float, help="stop after this many seconds of wall time")
    p.add_argument("--results-out", help="write the summary and shot list as JSON")
    p.add_argument("--compare-to-replay", action="store_true",
                   help="file sources only: compare with the cached-detection replay")
    p.add_argument("--config", help="JSON file of config overrides")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    config = load_config(override_path=args.config, cli_overrides={"camera.source": args.source})
    summary = run_live(config, args.seconds)
    print_summary(summary)
    comparison = compare_to_replay(config, summary, args.seconds) if args.compare_to_replay else None
    if args.results_out:
        out = {k: v for k, v in summary.items() if k != "_results"}
        if comparison is not None:
            out["compare"] = comparison
        Path(args.results_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.results_out).write_text(json.dumps(out, indent=2) + "\n")
        print(f"results written to {args.results_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
