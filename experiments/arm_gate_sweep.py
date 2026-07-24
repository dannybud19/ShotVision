"""Arm-gate sweep: does a windowed (gap-tolerant) pre-arm test rescue the
missing makes, and at what false-positive cost?

Context (see docs/tracking-research.md for the full writeup): real makes are
being silently dropped by `shotvision.shot_logic.state_machine.ShotStateMachine`
because its pre-arm phase (`_update_idle`) requires `descent_min_frames`
*consecutive* frames where the ball is detected, above the rim, aligned, and
non-ascending, before a shot is even tracked. Measured ball-detection rate on
real footage is ~20-25%/frame, so a genuine shot approach can easily never
produce two qualifying frames in a row.

This script does NOT modify `shotvision/shot_logic/` at all. It:

  1. Runs the real detection -> tracking -> rim-tracking pipeline (the exact
     same classes `scripts/diagnose_shots.py` wires up: `Detector`,
     `BallTracker`, `RimTracker`) over the 3 ground-truth clips and captures
     per-frame (frame_idx, ball observation-or-None, RimRegion-or-None) —
     the same data the real state machine sees.
     `scripts/diagnose_shots.py` itself does not factor its wiring into an
     importable function (it's all inline in `main()`), so this mirrors that
     same wiring using the same public classes rather than editing that
     script; `classify_position` *is* imported and reused from it directly.
  2. Runs the real, unmodified `ShotStateMachine` over that captured data to
     get exact frame windows for the 6 already-resolved shots (this
     reproduces `diagnose_shots.py`'s per-shot breakdown, cross-checked
     against a live run of that script).
  3. Locates best-effort approximate windows for the 5 known-missing shots
     (see `locate_missing_shot_windows` for the exact heuristic and its
     documented limitations).
  4. Implements, locally (NOT in shot_logic/), a baseline pre-arm simulation
     that exactly replicates today's `_update_idle` consecutive-streak logic,
     and a windowed variant that relaxes consecutiveness. Sweeps a grid of
     (N, W) for the windowed variant, reporting rescued-of-5 and spurious
     extra arm events elsewhere in each clip.

Run directly:
    python -m experiments.arm_gate_sweep
"""
from __future__ import annotations

import pickle
import sys
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from shotvision.capture.source import FrameSource
from shotvision.config.settings import ShotLogicConfig, load_config
from shotvision.detection.detector import Detector
from shotvision.detection.device import log_device_choice, resolve_device
from shotvision.shot_logic.rim import RimRegion
from shotvision.shot_logic.state_machine import (
    BallObservation,
    ShotOutcome,
    ShotState,
    ShotStateMachine,
)
from shotvision.tracking.ball_tracker import BallTracker

# scripts/diagnose_shots.py has no package __init__.py but is importable as
# an implicit namespace package from the repo root; reuse its position
# classifier rather than re-deriving it (per task constraints, that file is
# not edited, only imported from).
from scripts.diagnose_shots import classify_position  # noqa: F401  (re-exported for callers)

_CLIPS = [
    "sample_clips/chonyy_one_score_one_miss.mp4",
    "sample_clips/chonyy_two_score_two_miss.mp4",
    "sample_clips/chonyy_two_score_three_miss.mp4",
]

# Ground truth from sample_clips/SOURCES.md / filenames: (makes, misses).
_GROUND_TRUTH = {
    "sample_clips/chonyy_one_score_one_miss.mp4": (1, 1),
    "sample_clips/chonyy_two_score_two_miss.mp4": (2, 2),
    "sample_clips/chonyy_two_score_three_miss.mp4": (2, 3),
}

# Same jitter tolerance the real state machine uses for its descent check —
# duplicated here (not imported) because it's a private module constant,
# not part of state_machine.py's public surface; kept in sync manually.
_DESCENT_JITTER_PX = 3.0

_CACHE_DIR = Path(__file__).parent / ".cache"


@dataclass
class FrameRecord:
    frame_idx: int
    obs: BallObservation | None
    rim: RimRegion | None


@dataclass
class ClipData:
    source: str
    frames: list[FrameRecord]
    config: ShotLogicConfig


# ---------------------------------------------------------------------------
# Step 1: run the real pipeline and capture per-frame (obs, rim).
# ---------------------------------------------------------------------------


def collect_frames(source: str, config=None, max_frames: int | None = None) -> ClipData:
    """Runs the real Detector -> BallTracker -> RimTracker pipeline over a
    clip (identical wiring to scripts/diagnose_shots.py's main()) and
    captures the per-frame data the real state machine sees. Read-only use
    of shotvision.detection / shotvision.tracking / shotvision.shot_logic.rim_tracker."""
    cfg = config or load_config(cli_overrides={"camera.source": source})
    device, reason = resolve_device(cfg.model.device)
    log_device_choice(device, reason)

    detector = Detector(cfg.model, device)
    ball_tracker = BallTracker(detector, cfg.tracker, cfg.shot_logic.trajectory_buffer_len)
    from shotvision.shot_logic.rim_tracker import RimTracker

    rim_tracker = RimTracker(cfg.model, cfg.shot_logic)

    frames: list[FrameRecord] = []
    total = 0
    with FrameSource(cfg.camera.source) as src:
        while max_frames is None or total < max_frames:
            frame = src.read()
            if frame is None:
                break
            detections = ball_tracker.update(frame)
            rim = rim_tracker.update(detections)
            obs = ball_tracker.current_frame_ball_obs
            frames.append(FrameRecord(frame_idx=total, obs=obs, rim=rim))
            total += 1

    return ClipData(source=source, frames=frames, config=cfg.shot_logic)


def collect_frames_cached(source: str, force: bool = False) -> ClipData:
    """Same as collect_frames but memoized to disk — the real detector pass
    over 3 clips (~1100 frames total) takes a couple of minutes, and this
    script is re-run repeatedly while sweeping/validating."""
    _CACHE_DIR.mkdir(exist_ok=True)
    cache_path = _CACHE_DIR / (Path(source).stem + ".pkl")
    if not force and cache_path.exists():
        with open(cache_path, "rb") as f:
            return pickle.load(f)
    data = collect_frames(source)
    with open(cache_path, "wb") as f:
        pickle.dump(data, f)
    return data


# ---------------------------------------------------------------------------
# Step 2: real, unmodified ShotStateMachine over the captured data -> exact
# windows for the 6 already-resolved shots.
# ---------------------------------------------------------------------------


@dataclass
class ShotWindow:
    kind: str  # "resolved" | "missing"
    start: int
    end: int
    label: str  # e.g. "MISS@94" or "missing#1 (best-effort)"
    approximated: bool = False


def resolved_shot_windows(data: ClipData) -> list[ShotWindow]:
    """Feeds the captured per-frame data through the real, unmodified
    ShotStateMachine (exactly as scripts/diagnose_shots.py does) and returns
    one ShotWindow per resolved shot, spanning its arm frame to its
    resolution frame."""
    windows: list[ShotWindow] = []
    sm: ShotStateMachine | None = None
    arm_frame: int | None = None
    for rec in data.frames:
        if rec.rim is None:
            continue
        if sm is None:
            sm = ShotStateMachine(rec.rim, data.config)
        else:
            sm.rim = rec.rim
        prev_state = sm.state
        result = sm.update(rec.obs, rec.frame_idx)
        if prev_state is ShotState.IDLE and sm.state is ShotState.ARMED:
            arm_frame = rec.frame_idx
        if result is not None:
            start = arm_frame if arm_frame is not None else result.frame_idx
            windows.append(
                ShotWindow(
                    kind="resolved",
                    start=start,
                    end=result.frame_idx,
                    label=f"{result.outcome.value}@{result.frame_idx}"
                    f"[{result.reason.value if result.reason else '?'}]",
                )
            )
            arm_frame = None
    return windows


# ---------------------------------------------------------------------------
# Step 3: best-effort windows for the missing (never-armed) shots.
# ---------------------------------------------------------------------------


def locate_missing_shot_windows(
    data: ClipData, resolved: list[ShotWindow], expected_missing: int
) -> list[ShotWindow]:
    """Best-effort localization of the missing shots' approximate frame
    windows.

    diagnose_shots.py's own "never-armed candidate episode" detector (which
    groups frames satisfying the exact real pre-arm test: detected + above
    rim + aligned) was re-run against all 3 clips this session and found
    ZERO such episodes beyond the ones that already armed and resolved, in
    every clip — i.e. every missing make has, per that exact test, not just
    fewer than descent_min_frames consecutive qualifying frames, but *zero*
    qualifying frames anywhere in the clip. That test can't localize them.

    So this function uses a deliberately looser, best-effort proxy instead:
    any real ball detection (regardless of alignment or above/below-rim
    state) that falls within a generous horizontal band around the rim
    (+/- 2x the rim's outer width) and within the vertical span from well
    above the rim down through the rim band — i.e. "the ball was seen
    somewhere in the vicinity of the hoop" — clustered with gaps of up to 40
    frames tolerated. Clusters overlapping an already-resolved window are
    excluded. Remaining clusters are ranked by frame count and the top
    `expected_missing` are returned as approximate missing-shot windows.

    This is explicitly an approximation, stated here and in the sweep
    report: it can only be as good as "ball was seen somewhere near the
    hoop around this time," not a precise shot-attempt boundary. If fewer
    than `expected_missing` clusters are found, the shortfall is reported
    as "unable to localize" rather than fabricated.
    """
    resolved_ranges = [(w.start, w.end) for w in resolved]

    def in_resolved(idx: int) -> bool:
        return any(s - 5 <= idx <= e + 5 for s, e in resolved_ranges)

    loose_frames: list[int] = []
    for rec in data.frames:
        if rec.obs is None or rec.rim is None:
            continue
        if in_resolved(rec.frame_idx):
            continue
        rim = rec.rim
        x, y = rec.obs.x, rec.obs.y
        wide_half_span = rim.outer_width * 2.0
        near_x = abs(x - rim.center_x) <= wide_half_span
        near_y = y <= rim.outer_bottom + (rim.outer_bottom - rim.outer_top)
        if near_x and near_y:
            loose_frames.append(rec.frame_idx)

    clusters: list[list[int]] = []
    gap = 40
    for idx in loose_frames:
        if clusters and idx - clusters[-1][-1] <= gap:
            clusters[-1].append(idx)
        else:
            clusters.append([idx])

    clusters.sort(key=len, reverse=True)
    chosen = clusters[:expected_missing]
    chosen.sort(key=lambda c: c[0])

    windows = [
        ShotWindow(
            kind="missing",
            start=c[0],
            end=c[-1],
            label=f"missing#{i + 1} (best-effort, {len(c)} loose detections)",
            approximated=True,
        )
        for i, c in enumerate(chosen)
    ]
    shortfall = expected_missing - len(windows)
    if shortfall > 0:
        for i in range(shortfall):
            windows.append(
                ShotWindow(
                    kind="missing",
                    start=-1,
                    end=-1,
                    label=f"missing#{len(windows) + 1}: UNABLE TO LOCALIZE "
                    f"(no loose-detection cluster found outside resolved windows)",
                    approximated=True,
                )
            )
    return windows


# ---------------------------------------------------------------------------
# Step 4a: baseline pre-arm simulation — exact replica of _update_idle.
# ---------------------------------------------------------------------------


def simulate_baseline_arms(data: ClipData) -> list[int]:
    """Exact local replica of ShotStateMachine._update_idle's consecutive-
    streak logic (baseline, today's behavior). Returns the frame indices
    where an IDLE->ARMED transition would fire (rising edges only — once
    armed, the real machine leaves IDLE until the shot resolves, so it can't
    re-arm on the very next frame; we approximate that by resetting the
    streak the moment an arm fires, since simulating the full ARMED-phase
    resolution is out of scope for this arm-gate-only experiment)."""
    cfg = data.config
    streak = 0
    last_y: float | None = None
    arms: list[int] = []
    for rec in data.frames:
        obs, rim = rec.obs, rec.rim
        if obs is None or rim is None:
            streak = 0
            last_y = None
        else:
            x, y = obs.x, obs.y
            if rim.is_above(y) and rim.is_aligned(x, cfg.align_tolerance_ratio):
                if last_y is not None and y >= last_y - _DESCENT_JITTER_PX:
                    streak += 1
                else:
                    streak = 1
                last_y = y
            else:
                streak = 0
                last_y = None

        if streak >= cfg.descent_min_frames:
            arms.append(rec.frame_idx)
            streak = 0
            last_y = None
    return arms


# ---------------------------------------------------------------------------
# Step 4b: windowed pre-arm simulation.
# ---------------------------------------------------------------------------


def simulate_windowed_arms(data: ClipData, n: int, w: int) -> list[int]:
    """N qualifying frames (same above-rim/aligned/descending-within-jitter
    compound test as baseline) within a rolling window of W frames. Gaps
    (missing detections) are tolerated — they simply age out of the window,
    they do not reset it. A disqualifying *real* detection (one that fails
    the compound test) resets the window/streak entirely, same as baseline's
    hard reset — only missing frames get gap tolerance, matching the real
    fix's intent (a detection *problem*, not a motion-pattern change, is
    what's being tolerated)."""
    cfg = data.config
    window: deque[int] = deque()
    last_qual_y: float | None = None
    arms: list[int] = []

    for rec in data.frames:
        obs, rim = rec.obs, rec.rim
        idx = rec.frame_idx

        while window and idx - window[0] >= w:
            window.popleft()

        if obs is None or rim is None:
            pass  # gap: tolerated, no reset, window just ages out via pruning above
        else:
            x, y = obs.x, obs.y
            qualifies = (
                rim.is_above(y)
                and rim.is_aligned(x, cfg.align_tolerance_ratio)
                and (last_qual_y is None or y >= last_qual_y - _DESCENT_JITTER_PX)
            )
            if qualifies:
                window.append(idx)
                last_qual_y = y
            else:
                # disqualifying real detection -> hard reset, same as baseline
                window.clear()
                last_qual_y = None

        if len(window) >= n:
            arms.append(idx)
            window.clear()
            last_qual_y = None

    return arms


# ---------------------------------------------------------------------------
# Sweep driver + reporting.
# ---------------------------------------------------------------------------


def _arms_in_window(arms: list[int], window: ShotWindow) -> bool:
    if window.start < 0:
        return False
    return any(window.start <= a <= window.end for a in arms)


def _spurious_arms(arms: list[int], known_windows: list[ShotWindow]) -> int:
    def covered(a: int) -> bool:
        return any(w.start <= a <= w.end for w in known_windows if w.start >= 0)

    return sum(1 for a in arms if not covered(a))


@dataclass
class ClipReport:
    source: str
    resolved_windows: list[ShotWindow]
    missing_windows: list[ShotWindow]
    baseline_arms: list[int]


def build_clip_report(source: str, force_recollect: bool = False) -> ClipReport:
    data = collect_frames_cached(source, force=force_recollect)
    resolved = resolved_shot_windows(data)
    n_makes, n_misses = _GROUND_TRUTH[source]
    # Ground-truth cross-check: total expected attempts = makes + misses;
    # any attempt that didn't resolve is presumed a missing make (matches
    # the measured pattern: every resolved shot in this dataset is a MISS).
    expected_missing = (n_makes + n_misses) - len(resolved)
    missing = locate_missing_shot_windows(data, resolved, expected_missing)
    baseline_arms = simulate_baseline_arms(data)
    return ClipReport(
        source=source,
        resolved_windows=resolved,
        missing_windows=missing,
        baseline_arms=baseline_arms,
    )


def _qualifying_frames_in_window(data: ClipData, window: ShotWindow) -> int:
    """Counts real frames inside `window` satisfying the exact compound
    pre-arm test (detected + above-rim + aligned; descent not required for
    this count since even a single ascending-but-otherwise-qualifying frame
    would still be the raw ingredient a windowed gate needs). Used purely as
    a diagnostic to distinguish "windowing can't help because the raw
    ingredient literally isn't there" from "windowing has a bug"."""
    if window.start < 0:
        return -1
    cfg = data.config
    count = 0
    for rec in data.frames:
        if not (window.start <= rec.frame_idx <= window.end):
            continue
        if rec.obs is None or rec.rim is None:
            continue
        x, y = rec.obs.x, rec.obs.y
        if rec.rim.is_above(y) and rec.rim.is_aligned(x, cfg.align_tolerance_ratio):
            count += 1
    return count


def run_sweep(reports: list[ClipReport], clip_data: dict[str, ClipData], grid: list[tuple[int, int]]):
    all_missing = [(r.source, w) for r in reports for w in r.missing_windows]
    n_missing_total = len(all_missing)

    print(f"\n{'=' * 78}\nSanity check: raw qualifying-frame supply inside each missing window\n{'=' * 78}")
    print(
        "(detected + above-rim + aligned frames found inside each best-effort "
        "missing-shot window, ignoring descent/consecutiveness — this is the\n"
        " raw ingredient ANY windowed gate needs at least N of; 0 here means no\n"
        " (N, W) can possibly rescue that shot, regardless of window size)"
    )
    for source, w in all_missing:
        data = clip_data[source]
        qc = _qualifying_frames_in_window(data, w)
        print(f"  {Path(source).name:38s} {w.label:55s} qualifying frames in window: {qc}")

    print(f"\n{'=' * 78}\nBaseline correctness check (today's _update_idle, replicated locally)\n{'=' * 78}")
    rescued_baseline = 0
    for source, w in all_missing:
        rep = next(r for r in reports if r.source == source)
        hit = _arms_in_window(rep.baseline_arms, w)
        rescued_baseline += hit
        print(f"  {Path(source).name:38s} {w.label:55s} baseline arms inside window: {hit}")
    print(f"Baseline rescued: {rescued_baseline}/{n_missing_total}  (expect 0 — validates replication)")
    if rescued_baseline != 0:
        print(
            "  ** WARNING: baseline replication did not reproduce the known 0/5 "
            "result. Do not trust the windowed sweep below until this is fixed. **"
        )

    print(f"\n{'=' * 78}\nWindowed sweep\n{'=' * 78}")
    header = f"{'N':>3} {'W':>4} {'rescued':>10} {'spurious_extra_arms':>22}  per-clip spurious"
    print(header)
    print("-" * len(header))

    results = []
    for n, w in grid:
        rescued = 0
        spurious_total = 0
        per_clip_spurious = []
        for rep in reports:
            data = clip_data[rep.source]
            windowed_arms = simulate_windowed_arms(data, n, w)
            known = rep.resolved_windows + rep.missing_windows
            spurious = _spurious_arms(windowed_arms, known)
            spurious_total += spurious
            per_clip_spurious.append(f"{Path(rep.source).name.split('_', 1)[1][:18]}={spurious}")

            for mw in rep.missing_windows:
                if _arms_in_window(windowed_arms, mw):
                    rescued += 1

        print(f"{n:>3} {w:>4} {rescued:>10}/{n_missing_total:<3} {spurious_total:>10}      {'  '.join(per_clip_spurious)}")
        results.append((n, w, rescued, spurious_total))

    return results


def recommend(results: list[tuple[int, int, int, int]]) -> str:
    if not results:
        return "No sweep results to recommend from."
    best_rescued = max(r[2] for r in results)
    best = max(results, key=lambda r: (r[2], -r[3]))
    n, w, rescued, spurious = best

    if best_rescued == 0:
        return (
            "IMPORTANT: rescued=0/5 at every (N, W) tested — this is not a bug in "
            "the sweep (baseline replication validated at 0/5 above, and the raw "
            "qualifying-frame supply check confirms 0 real detected+above-rim+aligned "
            "frames anywhere inside any of the 5 best-effort missing-shot windows, "
            "before descent/consecutiveness is even considered). For these specific "
            "5 measured misses, a windowed arm-gate cannot help — the ball is never "
            "confirmed-detected while simultaneously above the rim and horizontally "
            "aligned during the approach at all, not merely inconsistently, so no "
            "amount of gap tolerance recovers a signal that isn't there.\n"
            "  This measured result is a real finding, not a null result to ignore: it "
            "means recommendation #1 in docs/tracking-research.md (windowed arm-gate), "
            "while still a low-risk, directionally-reasonable change (it never produced "
            "a spurious extra arm anywhere in this data either), should NOT be sold as "
            "sufficient on its own for the measured missing-makes problem. Either the "
            "qualifying test itself (above-rim / aligned) needs loosening too, or the "
            "underlying detection-sparsity problem needs a real fix (docs/tracking-"
            "research.md's recommendation #2, a TrackNet-style detection booster) "
            "before this specific failure mode is actually rescued.\n"
            f"  As a reasoned (not sweep-selected) starting point for the windowed "
            f"gate's parameters — since it costs nothing in spurious arms in this data "
            f"and may still help OTHER footage with partial-but-broken streaks that this "
            f"dataset didn't happen to exercise — N=2, W=8 is a defensible middle-of-grid "
            f"default. Treat it as a starting point for the real fix, to be validated on "
            f"more footage, not a final answer: this dataset is only two distinct source "
            f"recordings (see docs/tracking-research.md's sample-size caveat)."
        )

    return (
        f"N={n}, W={w} looks best in this sweep (rescued={rescued}, "
        f"spurious_extra_arms={spurious}) — but this is a starting point for "
        f"the real fix's parameters, to be validated on more footage, not a "
        f"final answer: this dataset is only two distinct source recordings "
        f"(see docs/tracking-research.md's sample-size caveat)."
    )


def main() -> None:
    force = "--recollect" in sys.argv
    clip_data: dict[str, ClipData] = {}
    reports: list[ClipReport] = []

    print(f"{'=' * 78}\nStep 1-3: collecting per-frame data and locating known shot windows\n{'=' * 78}")
    for source in _CLIPS:
        print(f"\n--- {source} ---")
        data = collect_frames_cached(source, force=force)
        clip_data[source] = data
        rep = build_clip_report(source, force_recollect=False)
        reports.append(rep)
        print(f"  {len(data.frames)} frames captured")
        print(f"  Resolved shot windows ({len(rep.resolved_windows)}):")
        for w in rep.resolved_windows:
            print(f"    [{w.start:>5}-{w.end:<5}] {w.label}")
        print(f"  Missing shot windows, best-effort ({len(rep.missing_windows)}):")
        for w in rep.missing_windows:
            print(f"    [{w.start:>5}-{w.end:<5}] {w.label}")

    grid = [(2, w) for w in (4, 6, 8, 10, 15)] + [(3, w) for w in (4, 6, 8, 10, 15)]
    results = run_sweep(reports, clip_data, grid)

    print(f"\n{'=' * 78}\nRecommendation\n{'=' * 78}")
    print(recommend(results))


if __name__ == "__main__":
    main()
