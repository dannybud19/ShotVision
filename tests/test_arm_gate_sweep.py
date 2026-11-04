"""Unit tests for experiments/arm_gate_sweep.py's own simulation functions —
NOT the real pipeline (shotvision/detection, tracking, shot_logic are
untouched by this task). Verifies the local pre-arm-gate replicas behave
correctly in isolation against synthetic frame sequences, independent of any
real video or detector."""
from shotvision.config.settings import ShotLogicConfig
from shotvision.shot_logic.rim import RimRegion
from shotvision.shot_logic.state_machine import BallObservation

from experiments.arm_gate_sweep import (
    ClipData,
    FrameRecord,
    simulate_baseline_arms,
    simulate_windowed_arms,
)


def _rim():
    # Same fixture shape as tests/test_state_machine.py: outer x:100..200,
    # y:50..70 -> above-rim is y<50, aligned x roughly within [70, 230] at
    # align_tolerance_ratio=0.6.
    return RimRegion.from_points([(100, 50), (200, 50), (100, 70), (200, 70)], inner_bound_shrink=0.15)


def _config(**overrides):
    base = dict(
        inner_bound_shrink=0.15,
        align_tolerance_ratio=0.6,
        descent_min_frames=2,
        occlusion_grace_frames=5,
        shot_timeout_frames=20,
    )
    base.update(overrides)
    # The config is in seconds; these tests count frames at 30 fps.
    keys = {"descent_min_frames": "descent_min_s", "occlusion_grace_frames": "occlusion_grace_s",
            "shot_timeout_frames": "shot_timeout_s"}
    return ShotLogicConfig(**{keys.get(k, k): (v / 30 if k in keys else v) for k, v in base.items()})


def _obs(x=150.0, y=10.0):
    return BallObservation.from_center(x, y)


def _clip(positions: list[tuple[float, float] | None], config=None) -> ClipData:
    """positions: one entry per frame, either an (x, y) qualifying-candidate
    center, "disqualify" for a real-but-misaligned detection, or None for a
    missing/undetected frame."""
    rim = _rim()
    frames = []
    for i, p in enumerate(positions):
        if p is None:
            frames.append(FrameRecord(frame_idx=i, obs=None, rim=rim))
        elif p == "disqualify":
            # Real detection, but far outside alignment tolerance (rim
            # centered at x=150, half-span ~80 -> x=1000 is nowhere close).
            frames.append(FrameRecord(frame_idx=i, obs=_obs(1000.0, 10.0), rim=rim))
        else:
            frames.append(FrameRecord(frame_idx=i, obs=_obs(*p), rim=rim))
    return ClipData(source="synthetic", frames=frames, config=config or _config())


def test_exactly_n_qualifying_frames_spread_across_exactly_w_arms():
    # Two qualifying frames (0 and 4) spanning a 5-frame window, with three
    # missing frames in between — baseline (consecutive-only) would never
    # arm this; the windowed variant with N=2, W=5 should.
    positions = [(150, 10), None, None, None, (150, 10)]
    data = _clip(positions)

    baseline_arms = simulate_baseline_arms(data)
    assert baseline_arms == [], "sanity check: baseline must NOT arm on this gap-broken sequence"

    windowed_arms = simulate_windowed_arms(data, n=2, w=5)
    assert windowed_arms == [4]


def test_n_minus_one_qualifying_frames_within_w_does_not_arm():
    # Only one qualifying frame in the whole sequence — N=2 can never be
    # reached regardless of window size.
    positions = [(150, 10), None, None, None, None]
    data = _clip(positions)

    windowed_arms = simulate_windowed_arms(data, n=2, w=5)
    assert windowed_arms == []


def test_disqualifying_frame_resets_the_window():
    # Frame 0 qualifies, frame 1 is a real but disqualifying detection
    # (misaligned) which must hard-reset the window, frame 2 qualifies again.
    # Without the reset, frames 0 and 2 would both still be inside a W=5
    # window and would incorrectly arm at frame 2 (only 1 qualifying frame
    # actually available since frame 0's contribution was cleared).
    positions = [(150, 10), "disqualify", (150, 10), None, None]
    data = _clip(positions)

    windowed_arms = simulate_windowed_arms(data, n=2, w=5)
    assert windowed_arms == [], "a disqualifying real detection must clear the window, not just skip it"

    # Confirm the window does still work normally when nothing disqualifies:
    # two clean qualifying frames close together should arm.
    clean_positions = [(150, 10), (150, 10), None, None, None]
    clean_data = _clip(clean_positions)
    assert simulate_windowed_arms(clean_data, n=2, w=5) == [1]
