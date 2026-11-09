"""Tests for experiments/line_crossing_experiment.py (PLAN 2, section 5).

Synthetic detections only: no cache, no model, no video files. A fixed hoop box
(centre (500, 300), width 60, height 50, conf 0.9) is present in every frame at
30 fps. The ball is a 20x20 box.

The plan's test 1-4 say the ball "falls straight down from y = 150 to y = 420,
one point per frame". At literally 1 px/frame that takes 271 frames, so the
above-rim point ages out of ball_pos (age limit 1.0 s = 30 frames) before the
down check fires and the make never scores. A realistic fall rate (6 px/frame,
~46 frames) keeps the whole shot inside the age limit and is used here, per the
plan's "one point per frame" (continuous coverage) reading.

The ShotResult.reason for line-method results is a placeholder, so gap_too_long
and arc_fallback are asserted from the diagnostics' "method" field, not from the
ShotResult.reason (owner note 1).
"""
from __future__ import annotations

from shotvision.detection.detector import Detection
from shotvision.shot_logic.state_machine import (
    ResolutionReason,
    ShotOutcome,
    ShotResult,
)

from experiments.line_crossing_experiment import VARIANTS, apply_hybrid, run_line_method

HOOP = Detection("hoop", 0.9, (470, 275, 530, 325))  # centre (500, 300), w 60, h 50


def ball(x: float, y: float, conf: float = 0.9) -> Detection:
    return Detection("ball", conf, (x - 10, y - 10, x + 10, y + 10))


def falling_ys(step: int = 6, start: int = 150, end: int = 420) -> list:
    ys = []
    y = start
    while y <= end:
        ys.append(y)
        y += step
    return ys


def frames_from_ys(ys, x: float = 500, conf: float = 0.9) -> list[list[Detection]]:
    frames = []
    for y in ys:
        dets = [HOOP]
        if y is not None:
            dets.append(ball(x, y, conf))
        frames.append(dets)
    return frames


def test_clean_make():
    """Ball falls straight through x = 500: L1 returns exactly one MAKE."""
    frames = frames_from_ys(falling_ys())
    results, diags = run_line_method(frames, 30.0, VARIANTS["L1"])
    assert len(results) == 1
    assert results[0].outcome == ShotOutcome.MAKE


def test_clear_miss_to_the_side():
    """Same fall at x = 600: L1 returns one MISS."""
    frames = frames_from_ys(falling_ys(), x=600)
    results, diags = run_line_method(frames, 30.0, VARIANTS["L1"])
    assert len(results) == 1
    assert results[0].outcome == ShotOutcome.MISS


def test_gap_rescue():
    """Delete the rim-region frames (y 250-380): L1 still returns MAKE."""
    ys = [None if (y is not None and 250 <= y <= 380) else y for y in falling_ys()]
    frames = frames_from_ys(ys)
    results, diags = run_line_method(frames, 30.0, VARIANTS["L1"])
    assert len(results) == 1
    assert results[0].outcome == ShotOutcome.MAKE


def test_gap_limit():
    """Hold the ball invisible for 24 frames at the rim (0.8 s): L2 returns
    MISS via gap_too_long (gap_frames = 25 > 0.5 s)."""
    ys = falling_ys()
    for i in range(16, 40):
        ys[i] = None
    frames = frames_from_ys(ys)
    results, diags = run_line_method(frames, 30.0, VARIANTS["L2"])
    assert len(results) == 1
    assert results[0].outcome == ShotOutcome.MISS
    assert diags[0]["method"] == "gap_too_long"


def _parabola_ys(a: float = 0.5, t_max: int = 30, missing: tuple = ()) -> list:
    return [None if t in missing else 150 + a * t * t for t in range(t_max + 1)]


def test_arc_make_and_shifted_miss():
    """A falling parabola crossing rim_line (y = 275) at x = 500, with 6 frames
    missing just above and below the rim (under 0.5 s): L4 returns MAKE. The same
    path crossing at x = 530 (inside the ±10 px zone but outside strict) returns
    MISS for L4 and MAKE for L2 (owner correction: x = 530, not 540)."""
    missing = (15, 16, 17, 18, 19, 20)

    frames = frames_from_ys(_parabola_ys(missing=missing), x=500)
    results, diags = run_line_method(frames, 30.0, VARIANTS["L4"])
    assert len(results) == 1
    assert results[0].outcome == ShotOutcome.MAKE

    frames = frames_from_ys(_parabola_ys(missing=missing), x=530)
    r4, d4 = run_line_method(frames, 30.0, VARIANTS["L4"])
    assert len(r4) == 1
    assert r4[0].outcome == ShotOutcome.MISS
    r2, d2 = run_line_method(frames, 30.0, VARIANTS["L2"])
    assert len(r2) == 1
    assert r2[0].outcome == ShotOutcome.MAKE


def test_faithful_vs_one_ball():
    """A second confident stationary ball at (200, 450) every frame. L1 (best)
    still scores the shot as MAKE. L0 (all candidates) is recorded, not asserted."""
    frames = []
    for y in falling_ys():
        dets = [HOOP, ball(500, y), ball(200, 450)]
        frames.append(dets)

    results, diags = run_line_method(frames, 30.0, VARIANTS["L1"])
    assert len(results) == 1
    assert results[0].outcome == ShotOutcome.MAKE

    r0, d0 = run_line_method(frames, 30.0, VARIANTS["L0"])
    # Observed: L0 (all candidates) appends the stationary ball too, so the line
    # is drawn from the shot ball's last above-rim point to whichever point
    # follows it in ball_pos. With the stationary ball interleaved the outcome
    # here is MISS (the extra candidate corrupts the A->B segment), while L1
    # scores MAKE. This is the faithful-vs-best distinction the experiment
    # measures. Recorded rather than asserted because it is not part of the
    # spec's contract.
    assert len(r0) >= 1


def test_hybrid_h1():
    """H1 rescues a MISS_OCCLUSION_GAP SV result near an L3 MAKE, and leaves a
    MISS_RIM_OUT_SIDEWAYS result untouched."""
    sv_results = [
        ShotResult(ShotOutcome.MISS, 100, reason=ResolutionReason.MISS_OCCLUSION_GAP),
        ShotResult(ShotOutcome.MISS, 200, reason=ResolutionReason.MISS_RIM_OUT_SIDEWAYS),
    ]
    line_results = [ShotResult(ShotOutcome.MAKE, 105, reason=ResolutionReason.MAKE_CONFIRMED)]
    line_diag = [{"frame_idx": 105, "outcome": "MAKE", "method": "line", "gap_frames": 5, "predicted_x_in_hoop_widths": 0.0}]
    results = apply_hybrid(sv_results, line_results, line_diag, 30.0, add_new=False)
    assert results[0].outcome == ShotOutcome.MAKE
    assert results[1].outcome == ShotOutcome.MISS
    assert results[1].reason == ResolutionReason.MISS_RIM_OUT_SIDEWAYS
