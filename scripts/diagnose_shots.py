"""Headless shot-resolution diagnostic.

Runs the real detection + tracking + make/miss state machine over a clip,
with the rim located automatically from the model's own hoop detections
(shot_logic/rim_tracker.py — same as main.py, no manual calibration needed),
and reports — per resolved shot — which exit path resolved it, the ball's
recent observed positions classified against the rim, and the occlusion gap
immediately before resolution. Ends with an aggregate breakdown of counts by
resolution reason, plus overall detection health.

This answers: are makes being scored as misses because the ball isn't detected
during the confirming frames, because the scoring geometry never catches the
ball, or because the logic is wrong even on a cleanly tracked ball?

Usage:
  python scripts/diagnose_shots.py --source sample_clips/video_test_5.mp4
  python scripts/diagnose_shots.py --source sample_clips/video_test_5.mp4 --max-frames 900
"""
from __future__ import annotations

import argparse
from collections import Counter

from shotvision.capture.source import FrameSource
from shotvision.config.settings import load_config
from shotvision.detection.detector import Detector
from shotvision.detection.device import log_device_choice, resolve_device
from shotvision.shot_logic.rim import RimRegion
from shotvision.shot_logic.rim_tracker import RimTracker
from shotvision.shot_logic.state_machine import ShotOutcome, ShotState, ShotStateMachine
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

    ball_tracker = BallTracker(detector, config.tracker, config.shot_logic.trajectory_buffer_len)
    rim_tracker = RimTracker(config.model, config.shot_logic)
    state_machine: ShotStateMachine | None = None

    total = 0
    ball_frames = 0
    in_band_ball_frames = 0
    rim_acquired_frame: int | None = None
    results = []

    # --- Diagnostic-only extension: surface shot attempts that never armed ---
    # `results` only holds *resolved* ShotResults. But shot_logic/state_machine.py
    # `_update_idle` resets the pre-arm descent streak to zero on ANY single
    # missed ball detection (no occlusion-grace tolerance there, unlike the
    # armed phase, which tolerates `occlusion_grace_frames` gaps). At this
    # project's real ball-detection rates, a genuine shot attempt can easily
    # never accumulate `descent_min_frames` consecutive detected+aligned+above
    # -rim frames, so it never reaches ShotState.ARMED and produces ZERO
    # ShotResults — silently invisible rather than an explicit MISS.
    #
    # This block does not touch shot_logic/ at all — it only *observes* the
    # already-public `state_machine.state` to log exact IDLE->ARMED
    # transitions, and independently reconstructs the arming *precondition*
    # (ball detected, above the rim, horizontally aligned) frame-by-frame
    # using the same public RimRegion/config helpers the real state machine
    # already uses. Runs of such "candidate" frames are grouped into episodes
    # (allowing gaps, since detections are sparse); an episode with enough
    # candidate frames to plausibly be a real attempt, but with no ARM
    # transition inside it, is flagged as a likely never-armed shot.
    CANDIDATE_EPISODE_GAP = 20  # frames; groups sparse candidate detections into one episode
    MIN_EPISODE_CANDIDATES = 2  # matches default descent_min_frames — the minimum a real arm needs
    arm_frames: list[int] = []
    candidate_frames: list[tuple[int, float, float]] = []  # (frame_idx, x, y)

    with FrameSource(config.camera.source) as source:
        while args.max_frames is None or total < args.max_frames:
            frame = source.read()
            if frame is None:
                break
            total += 1

            detections = ball_tracker.update(frame)
            rim = rim_tracker.update(detections)

            obs = ball_tracker.current_frame_ball_obs
            if obs is not None:
                ball_frames += 1
                if rim is not None and rim.is_in_band(obs.y):
                    in_band_ball_frames += 1

            if rim is not None:
                if state_machine is None:
                    state_machine = ShotStateMachine(rim, config.shot_logic)
                    rim_acquired_frame = total - 1
                else:
                    state_machine.rim = rim

            if state_machine is not None:
                frame_idx = total - 1
                if (
                    obs is not None
                    and rim is not None
                    and rim.is_above(obs.y)
                    and rim.is_aligned(obs.x, config.shot_logic.align_tolerance_ratio)
                ):
                    candidate_frames.append((frame_idx, obs.x, obs.y))

                prev_state = state_machine.state
                result = state_machine.update(obs, frame_idx)
                if prev_state is ShotState.IDLE and state_machine.state is ShotState.ARMED:
                    arm_frames.append(frame_idx)
                if result is not None:
                    results.append(result)

    final_rim = rim_tracker.current_rim
    print(f"\nProcessed {total} frames")
    if final_rim is None:
        print("Rim never acquired — no hoop detected above rim_conf in this clip.")
        pct = (100 * ball_frames / total) if total else 0
        print(f"Ball detected in {ball_frames}/{total} frames ({pct:.1f}%)")
        return

    print(f"Rim first acquired at frame {rim_acquired_frame}")
    rim_h = final_rim.outer_bottom - final_rim.outer_top
    rim_w = final_rim.outer_right - final_rim.outer_left
    print(
        f"Final rim box: x[{final_rim.outer_left:.0f}..{final_rim.outer_right:.0f}] "
        f"y[{final_rim.outer_top:.0f}..{final_rim.outer_bottom:.0f}]  "
        f"(width={rim_w:.0f}px, height={rim_h:.0f}px)  "
        f"inner x[{final_rim.inner_left:.0f}..{final_rim.inner_right:.0f}]"
    )
    if rim_h < 10:
        print(
            f"  ** WARNING: rim band is only {rim_h:.0f}px tall — a descending "
            f"ball can skip it entirely between frames. **"
        )

    pct = (100 * ball_frames / total) if total else 0
    print(f"Ball detected in {ball_frames}/{total} frames ({pct:.1f}%)")
    print(
        f"Ball detected *inside the rim band* in {in_band_ball_frames} frames "
        f"(crossing-based scoring no longer needs these, but low values here "
        f"confirm why band-membership scoring failed)"
    )

    # Trace positions are classified against the final rim estimate as an
    # approximation — the rim tracker can drift slightly frame to frame
    # (EMA smoothing), but this is close enough for diagnostic purposes.
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
            print(f"    f{frame_idx:>5}: {classify_position(final_rim, pos)}")

    print(f"\n{'='*70}\nAggregate\n{'='*70}")
    makes = sum(1 for r in results if r.outcome is ShotOutcome.MAKE)
    misses = sum(1 for r in results if r.outcome is ShotOutcome.MISS)
    print(f"MAKES: {makes}   MISSES: {misses}   ATTEMPTS: {len(results)}")
    print("\nBy resolution reason:")
    by_reason = Counter(r.reason for r in results)
    for reason, count in by_reason.most_common():
        print(f"  {reason.value if reason else '?':<26} {count}")

    # --- Diagnostic-only extension (continued): never-armed episode report ---
    # Group "candidate" frames (ball detected, above rim, aligned — the raw
    # ingredient for arming) into episodes, allowing gaps up to
    # CANDIDATE_EPISODE_GAP frames so sparse detections spanning one real
    # attempt aren't fractured into noise. Flag any episode with at least
    # MIN_EPISODE_CANDIDATES candidate frames that contains no IDLE->ARMED
    # transition — a real shot attempt the state machine never even armed.
    episodes: list[dict] = []
    for frame_idx, x, y in candidate_frames:
        if episodes and frame_idx - episodes[-1]["end"] <= CANDIDATE_EPISODE_GAP:
            ep = episodes[-1]
            ep["end"] = frame_idx
            ep["frames"].append(frame_idx)
        else:
            episodes.append({"start": frame_idx, "end": frame_idx, "frames": [frame_idx]})

    def _max_consecutive_run(frames: list[int]) -> int:
        """Longest run of frame indices with no gap at all (diff==1) — this is
        exactly what the real pre-arm streak needs consecutively; if this
        never reaches descent_min_frames within an episode, that alone
        explains why it never armed."""
        best = run = 1
        for a, b in zip(frames, frames[1:]):
            run = run + 1 if b - a == 1 else 1
            best = max(best, run)
        return best

    never_armed = []
    for ep in episodes:
        if len(ep["frames"]) < MIN_EPISODE_CANDIDATES:
            continue
        armed_inside = any(ep["start"] <= af <= ep["end"] for af in arm_frames)
        if not armed_inside:
            never_armed.append(ep)

    print(f"\n{'='*70}\nNever-armed candidate shot attempts\n{'='*70}")
    print(
        f"(episodes of >= {MIN_EPISODE_CANDIDATES} 'ball above rim & aligned' frames, "
        f"grouped with <= {CANDIDATE_EPISODE_GAP}f gaps, that never reached ShotState.ARMED)"
    )
    if not never_armed:
        print("  none — every sufficiently-large candidate approach window armed.")
    else:
        for ep in never_armed:
            run = _max_consecutive_run(ep["frames"])
            print(
                f"  frames {ep['start']:>5}-{ep['end']:<5} "
                f"candidate_frames={len(ep['frames']):<3} "
                f"longest_consecutive_run={run} "
                f"(needs {config.shot_logic.descent_min_frames} consecutive to arm)"
            )
    print(
        f"\nTotal candidate episodes: {len(episodes)}   "
        f"Armed+resolved: {len(results)}   "
        f"Flagged never-armed: {len(never_armed)}"
    )


if __name__ == "__main__":
    main()
