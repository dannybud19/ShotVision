"""Headless shot-resolution diagnostic.

Runs the real detection + tracking + make/miss state machine over a clip using
its *saved manual calibration* (reproducing exactly what you saw when running
main.py), and reports — per resolved shot — which exit path resolved it, the
ball's recent observed positions classified against the rim, and the occlusion
gap immediately before resolution. Ends with an aggregate breakdown of counts
by resolution reason, plus overall detection health.

This answers: are makes being scored as misses because the ball isn't detected
during the confirming frames, because the scoring geometry (e.g. a too-thin
rim band) never catches the ball, or because the logic is wrong even on a
cleanly tracked ball?

Usage:
  python scripts/diagnose_shots.py --source sample_clips/video_test_5.mp4
  python scripts/diagnose_shots.py --source sample_clips/video_test_5.mp4 --max-frames 900

Requires a saved calibration for the source (run main.py once to calibrate,
which writes shotvision/config/calibrations.json). This script can't calibrate
itself — that needs an interactive display.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter

from shotvision.capture.source import FrameSource
from shotvision.config.settings import load_config
from shotvision.detection.detector import BALL, HOOP, Detector
from shotvision.detection.device import log_device_choice, resolve_device
from shotvision.shot_logic.calibration import load_calibration
from shotvision.shot_logic.rim import RimRegion
from shotvision.shot_logic.state_machine import ShotOutcome, ShotStateMachine
from shotvision.tracking.ball_tracker import BallTracker


def classify_position(rim: RimRegion, pos: tuple[float, float] | None) -> str:
    if pos is None:
        return "no-detection"
    x, y = pos
    if rim.is_above(y):
        vert = "above"
    elif rim.is_below(y):
        vert = "below"
    else:
        vert = "IN-BAND"
    inner = "inner=Y" if rim.is_inside_inner_bounds(x) else "inner=n"
    return f"{vert:>7} {inner} @({x:.0f},{y:.0f})"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose shot make/miss resolutions")
    parser.add_argument("--source", default="sample_clips/video_test_5.mp4")
    parser.add_argument("--max-frames", type=int, default=None)
    parser.add_argument("--config", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(override_path=args.config, cli_overrides={"camera.source": args.source})

    device, reason = resolve_device(config.model.device)
    log_device_choice(device, reason)

    detector = Detector(config.model, device)
    print(f"Weights: {detector.weights_path} (has_hoop_class={detector.has_hoop_class})")

    with FrameSource(config.camera.source) as source:
        rim = load_calibration(config.calibration.path, source.source_key)
        if rim is None:
            print(
                f"\nNo saved calibration for {source.source_key!r}.\n"
                f"Run `python -m shotvision.main --source {args.source}` once to "
                f"click the rim (writes {config.calibration.path}), then rerun this.",
                file=sys.stderr,
            )
            sys.exit(1)

        rim_h = rim.outer_bottom - rim.outer_top
        rim_w = rim.outer_right - rim.outer_left
        print(
            f"\nRim box in use: x[{rim.outer_left:.0f}..{rim.outer_right:.0f}] "
            f"y[{rim.outer_top:.0f}..{rim.outer_bottom:.0f}]  "
            f"(width={rim_w:.0f}px, height={rim_h:.0f}px)  "
            f"inner x[{rim.inner_left:.0f}..{rim.inner_right:.0f}]"
        )
        if rim_h < 10:
            print(
                f"  ** WARNING: rim band is only {rim_h:.0f}px tall — a descending "
                f"ball can skip it entirely between frames. **"
            )

        ball_tracker = BallTracker(detector, config.tracker, config.shot_logic.trajectory_buffer_len)
        state_machine = ShotStateMachine(rim, config.shot_logic)

        total = 0
        ball_frames = 0
        in_band_ball_frames = 0
        results = []

        while args.max_frames is None or total < args.max_frames:
            frame = source.read()
            if frame is None:
                break
            total += 1
            detections = ball_tracker.update(frame)
            pos = ball_tracker.current_frame_ball_pos
            if pos is not None:
                ball_frames += 1
                if rim.is_in_band(pos[1]):
                    in_band_ball_frames += 1
            result = state_machine.update(pos, total - 1)
            if result is not None:
                results.append(result)

    print(f"\nProcessed {total} frames")
    pct = (100 * ball_frames / total) if total else 0
    print(f"Ball detected in {ball_frames}/{total} frames ({pct:.1f}%)")
    print(
        f"Ball detected *inside the rim band* in {in_band_ball_frames} frames "
        f"(these are the only frames that can register a make)"
    )

    print(f"\n{'='*70}\nPer-shot breakdown ({len(results)} resolved shots)\n{'='*70}")
    for i, r in enumerate(results, 1):
        print(
            f"\nShot #{i} @frame {r.frame_idx}: {r.outcome.value} "
            f"[{r.reason.value if r.reason else '?'}]"
        )
        print(
            f"  armed_frames={r.armed_frames}  entered_inner={r.entered_inner}  "
            f"reached_band={r.reached_band}  "
            f"occlusion_frames_before_resolve={r.occlusion_frames_before_resolve}"
        )
        print("  recent trace (oldest -> resolution):")
        for frame_idx, pos in r.recent_trace:
            print(f"    f{frame_idx:>5}: {classify_position(rim, pos)}")

    print(f"\n{'='*70}\nAggregate\n{'='*70}")
    makes = sum(1 for r in results if r.outcome is ShotOutcome.MAKE)
    misses = sum(1 for r in results if r.outcome is ShotOutcome.MISS)
    print(f"MAKES: {makes}   MISSES: {misses}   ATTEMPTS: {len(results)}")
    print("\nBy resolution reason:")
    by_reason = Counter(r.reason for r in results)
    for reason, count in by_reason.most_common():
        print(f"  {reason.value if reason else '?':<26} {count}")


if __name__ == "__main__":
    main()
