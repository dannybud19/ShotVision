"""Scoreboard: score the full pipeline against labeled clips.

Runs detection once per clip (cached), then replays the cached raw detections
through the real BallTracker association, RimTracker and ShotStateMachine, and
compares the resolved shots to `sample_clips/labels.json`.

Per clip it reports correct makes/misses, FALSE MAKES (the error this project
cares most about), missed makes, wrong-outcome and unlabeled ("spurious")
shots, plus a tracking-smoothness check on every labeled make: the share of
frames inside the make's window with a confirmed ball, and the longest run of
frames without one.

Exit code 0 only when every labeled clip passes:
  - every labeled shot matched with the correct outcome, no spurious shots,
  - zero false makes,
  - every labeled make's window has >= --min-coverage ball coverage and no
    gap longer than --max-gap-s seconds.

Labels format (frame indices are 0-based, inclusive):
  {"clips": {"<file in sample_clips/>": {"shots": [
      {"start": 258, "end": 292, "outcome": "MAKE"}, ...]}}}
For a make, [start, end] should span the ball's final approach to the rim
through its exit from the bottom of the net. Outcome "IGNORE" marks a window
the labeler couldn't call (e.g. the ball is hidden): a resolved shot inside it
is neither scored nor counted as spurious. A clip whose shots include any
other outcome (e.g. "?") is skipped as not yet labeled.

Usage:
  python scripts/evaluate.py                         # all labeled clips
  python scripts/evaluate.py --clips chonyy_two_score_two_miss.mp4 -v
  python scripts/evaluate.py --set shot_logic.inner_bound_shrink=0.2
  python scripts/evaluate.py --set model.imgsz=1280  # new detection cache key
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from shotvision.config.settings import REFERENCE_FPS, Config, load_config, to_frames  # noqa: E402
from shotvision.detection.detector import Detection  # noqa: E402
from shotvision.shot_logic.rim import RimRegion  # noqa: E402
from shotvision.shot_logic.rim_tracker import RimTracker  # noqa: E402
from shotvision.shot_logic.state_machine import (  # noqa: E402
    BallObservation,
    ShotResult,
    ShotState,
    ShotStateMachine,
)
from shotvision.tracking.ball_tracker import BallTracker  # noqa: E402

CLIPS_DIR = REPO_ROOT / "sample_clips"
LABELS_PATH = CLIPS_DIR / "labels.json"
CACHE_DIR = REPO_ROOT / "experiments" / ".cache" / "detections"

# A resolved shot matches a labeled shot if its resolution frame falls in the
# labeled window, widened by MATCH_SLACK_S before it (15 frames at 30 fps) and
# MATCH_SLACK_AFTER_S after it: a shot can only resolve after the ball reaches
# the rim, and with the ball hidden in the net the state machine resolves
# up to ~1 s after the labeled exit (measured: 31-36 frames late at 60 fps on
# the Hazen game, 27 frames at 30 fps on video_test_5 f3104).
MATCH_SLACK_S = 0.5
MATCH_SLACK_AFTER_S = 1.0


def clip_fps(clip: Path) -> float:
    """The clip's own frame rate (header only; no decoding, no model)."""
    import cv2

    cap = cv2.VideoCapture(str(clip))
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    cap.release()
    return fps if fps > 1 else REFERENCE_FPS


# ---------------------------------------------------------------------------
# Detection cache
# ---------------------------------------------------------------------------


def _cache_path(clip: Path, config: Config) -> Path:
    weights = Path(config.model.weights)
    key = f"{weights.name}|{config.model.imgsz}|{config.model.track_conf}"
    digest = hashlib.sha1(key.encode()).hexdigest()[:10]
    return CACHE_DIR / f"{clip.stem}.{digest}.pkl"


def load_detections(clip: Path, config: Config, recollect: bool = False) -> list[list[Detection]]:
    """Raw per-frame detections (all classes, conf >= model.track_conf) for a
    clip — exactly what BallTracker.update() would compute — cached on disk
    keyed by weights/imgsz/track_conf so logic-only changes replay in seconds."""
    path = _cache_path(clip, config)
    if path.exists() and not recollect:
        with open(path, "rb") as f:
            return pickle.load(f)

    from shotvision.capture.source import FrameSource
    from shotvision.detection.detector import Detector
    from shotvision.detection.device import resolve_device

    device, _ = resolve_device(config.model.device)
    detector = Detector(config.model, device)
    frames: list[list[Detection]] = []
    with FrameSource(str(clip)) as source:
        while (frame := source.read()) is not None:
            result = detector.model.predict(
                frame,
                conf=config.model.track_conf,
                imgsz=config.model.imgsz,
                device=device,
                verbose=False,
            )[0]
            frames.append(detector.parse_result(result))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(frames, f)
    return frames


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------


@dataclass
class FrameState:
    obs: BallObservation | None
    rim: RimRegion | None
    armed: bool


@dataclass
class Replay:
    frames: list[FrameState]
    results: list[ShotResult]
    trajectories: list[list] = field(default_factory=list)  # per-frame trajectory snapshot (optional)


def replay(
    detections: list[list[Detection]],
    config: Config,
    keep_trajectories: bool = False,
    fps: float = REFERENCE_FPS,
) -> Replay:
    """Feed recorded detections through the real tracking + shot logic, wired
    exactly as shotvision/main.py wires it, timed at the clip's fps."""
    ball_tracker = BallTracker(
        SimpleNamespace(conf=config.model.conf),
        config.tracker,
        to_frames(config.shot_logic.trajectory_buffer_s, fps),
        fps=fps,
    )
    rim_tracker = RimTracker(config.model, config.shot_logic, fps=fps)
    state_machine: ShotStateMachine | None = None
    out = Replay(frames=[], results=[])
    for frame_idx, dets in enumerate(detections):
        rim = rim_tracker.update(dets)
        ball_tracker.ingest(dets, rim=rim, locked_track_id=state_machine.armed_track_id if state_machine else None)
        if rim is not None and state_machine is None:
            state_machine = ShotStateMachine(rim, config.shot_logic, fps=fps)
        elif state_machine is not None and (rim is not None or config.shot_logic.cancel_when_rim_lost):
            state_machine.rim = rim  # None while the hoop is lost: no arming, armed shot cancelled
        obs = ball_tracker.current_frame_ball_obs
        if state_machine is not None:
            result = state_machine.update(obs, frame_idx)
            if result is not None:
                out.results.append(result)
        armed = state_machine is not None and state_machine.state is ShotState.ARMED
        out.frames.append(FrameState(obs=obs, rim=rim, armed=armed))
        if keep_trajectories:
            out.trajectories.append(list(ball_tracker.trajectory))
    return out


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


@dataclass
class ShotCheck:
    label: dict
    result: ShotResult | None
    coverage: float | None = None  # makes only
    longest_gap: int | None = None  # makes only


@dataclass
class ClipScore:
    clip: str
    checks: list[ShotCheck]
    spurious: list[ShotResult]
    smoothness_ok: bool = True

    @property
    def false_makes(self) -> int:
        wrong = sum(
            1 for c in self.checks
            if c.result is not None and c.result.outcome.value == "MAKE" and c.label["outcome"] == "MISS"
        )
        return wrong + sum(1 for r in self.spurious if r.outcome.value == "MAKE")

    @property
    def counts_exact(self) -> bool:
        return not self.spurious and all(
            c.result is not None and c.result.outcome.value == c.label["outcome"] for c in self.checks
        )

    @property
    def passed(self) -> bool:
        return self.counts_exact and self.false_makes == 0 and self.smoothness_ok


def _smoothness(frames: list[FrameState], start: int, end: int) -> tuple[float, int]:
    window = frames[max(0, start): end + 1]
    if not window:
        return 0.0, 0
    seen = [f.obs is not None for f in window]
    longest = run = 0
    for s in seen:
        run = 0 if s else run + 1
        longest = max(longest, run)
    return sum(seen) / len(seen), longest


def score_clip(
    clip: str, shots: list[dict], rep: Replay, min_coverage: float, max_gap: int, fps: float = REFERENCE_FPS
) -> ClipScore:
    unmatched = list(rep.results)
    checks: list[ShotCheck] = []
    slack = to_frames(MATCH_SLACK_S, fps)
    slack_after = to_frames(MATCH_SLACK_AFTER_S, fps)
    # Resolutions inside IGNORE windows (same slack as scored windows) are
    # dropped first: neither scored nor spurious.
    for shot in shots:
        if shot["outcome"] == "IGNORE":
            lo, hi = shot["start"] - slack, shot["end"] + slack_after
            unmatched = [r for r in unmatched if not lo <= r.frame_idx <= hi]
    shots = [s for s in shots if s["outcome"] != "IGNORE"]
    for shot in sorted(shots, key=lambda s: s["start"]):
        lo, hi = shot["start"] - slack, shot["end"] + slack_after
        match = next((r for r in unmatched if lo <= r.frame_idx <= hi), None)
        if match is not None:
            unmatched.remove(match)
        check = ShotCheck(label=shot, result=match)
        if shot["outcome"] == "MAKE":
            check.coverage, check.longest_gap = _smoothness(rep.frames, shot["start"], shot["end"])
        checks.append(check)
    score = ClipScore(clip=clip, checks=checks, spurious=unmatched)
    score.smoothness_ok = all(
        c.coverage >= min_coverage and c.longest_gap <= max_gap
        for c in checks if c.coverage is not None
    )
    return score


def print_score(score: ClipScore, rep: Replay, verbose: bool) -> None:
    status = "PASS" if score.passed else "FAIL"
    labeled_makes = sum(1 for c in score.checks if c.label["outcome"] == "MAKE")
    labeled_misses = len(score.checks) - labeled_makes
    got_makes = sum(1 for r in rep.results if r.outcome.value == "MAKE")
    got_misses = len(rep.results) - got_makes
    ball_pct = 100 * sum(f.obs is not None for f in rep.frames) / max(1, len(rep.frames))
    print(
        f"[{status}] {score.clip}: got {got_makes}M/{got_misses}m, expected "
        f"{labeled_makes}M/{labeled_misses}m | false makes {score.false_makes} | "
        f"ball in {ball_pct:.0f}% of frames"
    )
    for c in score.checks:
        lab = f"{c.label['outcome']:<4} [{c.label['start']}-{c.label['end']}]"
        if c.result is None:
            got, ok = "NOT RESOLVED", False
        else:
            reason = c.result.reason.value if c.result.reason else "?"
            got = f"{c.result.outcome.value} @f{c.result.frame_idx} ({reason})"
            ok = c.result.outcome.value == c.label["outcome"]
        smooth = ""
        if c.coverage is not None:
            smooth = f" | coverage {100 * c.coverage:.0f}%, longest gap {c.longest_gap}f"
        if verbose or not ok or (c.coverage is not None and not score.smoothness_ok):
            print(f"    {'ok ' if ok else 'BAD'} label {lab} -> {got}{smooth}")
    for r in score.spurious:
        reason = r.reason.value if r.reason else "?"
        print(f"    BAD spurious {r.outcome.value} @f{r.frame_idx} ({reason}) — no labeled shot here")


def load_labels(split: str = "all", include_duplicates: bool = True) -> dict[str, list[dict]]:
    """Labeled clips. `split` filters on the clip's "split" field ("dev" when
    absent). Clips marked "duplicate_of" another clip are dropped unless
    include_duplicates, so distinct-shot counts aren't inflated."""
    data = json.loads(LABELS_PATH.read_text())
    labeled = {}
    for clip, entry in data["clips"].items():
        if split != "all" and entry.get("split", "dev") != split:
            continue
        if not include_duplicates and entry.get("duplicate_of"):
            continue
        shots = entry.get("shots", [])
        if shots and all(s.get("outcome") in ("MAKE", "MISS", "IGNORE") for s in shots):
            labeled[clip] = shots
    return labeled


def load_clip_meta() -> dict[str, dict]:
    data = json.loads(LABELS_PATH.read_text())
    return {clip: {k: v for k, v in entry.items() if k != "shots"} for clip, entry in data["clips"].items()}


def binomial_upper_bound(k: int, n: int, confidence: float = 0.95) -> float:
    """One-sided exact (Clopper-Pearson) upper bound on a rate after k events
    in n trials. With k=0 this is 1 - (1-confidence)^(1/n), about 3/n."""
    from math import comb

    if n == 0:
        return 1.0
    if k >= n:
        return 1.0
    alpha = 1 - confidence
    lo, hi = k / n, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2
        cdf = sum(comb(n, i) * mid ** i * (1 - mid) ** (n - i) for i in range(k + 1))
        if cdf > alpha:
            lo = mid
        else:
            hi = mid
    return hi


def _group(meta: dict, clip: str) -> str:
    src = meta.get("source") or {}
    return src.get("group") or clip.split("/")[0].split("_")[0]


def print_gate_report(scores: list["ClipScore"], meta: dict[str, dict], min_make_rate: float = 0.90) -> bool:
    """Gate A: makes counted / makes, false makes / misses (with the 95% upper
    bound), by miss type and by source group. Returns pass/fail."""
    from collections import defaultdict

    makes = counted = misses = false_makes = 0
    by_type = defaultdict(lambda: [0, 0, 0])  # misses, false makes, resolved MISS
    by_group = defaultdict(lambda: [0, 0, 0, 0])  # makes, counted, misses, false makes
    spurious_makes = 0
    reasons = defaultdict(int)
    for sc in scores:
        g = _group(meta.get(sc.clip, {}), sc.clip)
        for c in sc.checks:
            got = c.result.outcome.value if c.result is not None else None
            if c.label["outcome"] == "MAKE":
                makes += 1
                by_group[g][0] += 1
                if got == "MAKE":
                    counted += 1
                    by_group[g][1] += 1
                else:
                    reasons["make lost: " + (c.result.reason.value if c.result else "never armed")] += 1
            else:
                misses += 1
                t = c.label.get("miss_type") or "untyped"
                by_type[t][0] += 1
                by_group[g][2] += 1
                if got == "MAKE":
                    false_makes += 1
                    by_type[t][1] += 1
                    by_group[g][3] += 1
                elif got == "MISS":
                    by_type[t][2] += 1
        for r in sc.spurious:
            if r.outcome.value == "MAKE":
                spurious_makes += 1
                by_group[g][3] += 1

    total_false = false_makes + spurious_makes
    ub = binomial_upper_bound(total_false, misses)
    make_rate = counted / makes if makes else 0.0
    passed = total_false == 0 and make_rate >= min_make_rate
    print("\n=== Gate A ===")
    print(f"Makes counted: {counted}/{makes} ({100 * make_rate:.1f}%)  [need >= {100 * min_make_rate:.0f}%]")
    print(f"False makes: {false_makes}/{misses} labeled misses, + {spurious_makes} spurious makes "
          f"-> 95% upper bound on false-make rate {100 * ub:.1f}%  [need 0 false makes]")
    print("By miss type (misses, false makes, resolved as MISS, 95% UB):")
    for t, (n, fm, res) in sorted(by_type.items()):
        print(f"  {t:<14} {n:>4} {fm:>4} {res:>4}  {100 * binomial_upper_bound(fm, n):5.1f}%")
    print("By source (makes counted/makes, false makes/misses):")
    for g, (mk, ct, ms, fm) in sorted(by_group.items()):
        print(f"  {g:<22} {ct:>4}/{mk:<4} {fm:>3}/{ms:<4}")
    if reasons:
        print("Lost makes by exit reason:")
        for r, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
            print(f"  {r:<40} {n}")
    print(f"GATE A: {'PASS' if passed else 'FAIL'}")
    return passed


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Score the pipeline against labeled clips")
    p.add_argument("--clips", nargs="*", help="Only these clip filenames")
    p.add_argument("--set", action="append", metavar="dotted.key=value", help="Config override (repeatable)")
    p.add_argument("--config", help="JSON file of config overrides")
    p.add_argument("--recollect", action="store_true", help="Ignore cached detections")
    p.add_argument("--min-coverage", type=float, default=0.6)
    p.add_argument("--max-gap-s", type=float, default=0.2, help="longest allowed ball gap in a make window (6 frames at 30 fps)")
    p.add_argument("-v", "--verbose", action="store_true", help="Show every shot, not just failures")
    p.add_argument("--split", default="all", help="Only clips with this split (dev | test | all)")
    p.add_argument("--report", action="store_true",
                   help="Gate A report (by miss type and source); duplicate clips are excluded")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    overrides = dict(item.partition("=")[::2] for item in (args.set or []))
    config = load_config(override_path=args.config, cli_overrides=overrides)
    labels = load_labels(args.split, include_duplicates=not args.report)
    clips = [c for c in labels if not args.clips or c in args.clips]
    if not clips:
        print("No labeled clips to evaluate (labels with outcome '?' are skipped).")
        return 1

    scores = []
    for clip in clips:
        path = CLIPS_DIR / clip
        if not path.exists():
            print(f"[SKIP] {clip}: file not found in sample_clips/")
            continue
        fps = clip_fps(path)
        rep = replay(load_detections(path, config, args.recollect), config, fps=fps)
        score = score_clip(clip, labels[clip], rep, args.min_coverage, to_frames(args.max_gap_s, fps), fps)
        print_score(score, rep, args.verbose)
        scores.append(score)

    passed = sum(s.passed for s in scores)
    false_makes = sum(s.false_makes for s in scores)
    shots = sum(len(s.checks) for s in scores)
    correct = sum(
        1 for s in scores for c in s.checks
        if c.result is not None and c.result.outcome.value == c.label["outcome"]
    )
    spurious = sum(len(s.spurious) for s in scores)
    print(
        f"\nSUMMARY: {passed}/{len(scores)} clips pass | {correct}/{shots} labeled shots correct | "
        f"false makes {false_makes} | spurious shots {spurious}"
    )
    if args.report:
        return 0 if print_gate_report(scores, load_clip_meta()) else 1
    return 0 if scores and passed == len(scores) else 1


if __name__ == "__main__":
    sys.exit(main())
