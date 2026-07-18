import pytest

from shotvision.config.settings import ShotLogicConfig
from shotvision.shot_logic.rim import RimRegion
from shotvision.shot_logic.state_machine import ShotOutcome, ShotState, ShotStateMachine


def _rim():
    # outer box x:100..200 (width 100), y:50..70; inner shrunk by 15% -> 115..185
    return RimRegion.from_points([(100, 50), (200, 50), (100, 70), (200, 70)], inner_bound_shrink=0.15)


def _config(**overrides):
    base = dict(
        inner_bound_shrink=0.15,
        align_tolerance_ratio=0.6,
        descent_min_frames=2,
        occlusion_grace_frames=5,
        shot_timeout_frames=20,
        trajectory_buffer_len=60,
    )
    base.update(overrides)
    return ShotLogicConfig(**base)


def _feed(sm, positions, start_frame=0):
    """positions: list of (x, y) or None. Returns list of non-None results."""
    results = []
    for i, pos in enumerate(positions):
        r = sm.update(pos, start_frame + i)
        if r is not None:
            results.append(r)
    return results


def test_idle_stays_idle_without_qualifying_motion():
    sm = ShotStateMachine(_rim(), _config())
    results = _feed(sm, [None, (150, 100), (150, 20)])  # (150,20) alone doesn't hit descent_min_frames
    assert results == []
    assert sm.state is ShotState.IDLE


def test_arms_after_sustained_aligned_descent_above_rim():
    sm = ShotStateMachine(_rim(), _config(descent_min_frames=2))
    sm.update((150, 10), 0)
    assert sm.state is ShotState.IDLE  # only 1 qualifying frame so far
    sm.update((150, 20), 1)  # 2nd consecutive descending, aligned, above-rim frame
    assert sm.state is ShotState.ARMED


def test_clean_make_through_center_of_inner_bounds():
    sm = ShotStateMachine(_rim(), _config())
    positions = [
        (150, 10), (150, 20),  # arm
        (150, 40),             # still above rim, approaching
        (150, 60),             # in rim band, inside inner bounds (115..185)
        (150, 80),             # below rim -> MAKE
    ]
    results = _feed(sm, positions)
    assert len(results) == 1
    assert results[0].outcome is ShotOutcome.MAKE
    assert sm.state is ShotState.IDLE


def test_rim_out_exits_inner_bounds_at_rim_height():
    sm = ShotStateMachine(_rim(), _config())
    positions = [
        (150, 10), (150, 20),  # arm
        (150, 45),
        (195, 60),              # in band but x=195 > inner_right=185 -> rim-out
    ]
    results = _feed(sm, positions)
    assert len(results) == 1
    assert results[0].outcome is ShotOutcome.MISS


def test_bounces_upward_after_reaching_rim_height():
    sm = ShotStateMachine(_rim(), _config())
    positions = [
        (150, 10), (150, 20),  # arm
        (150, 60),              # reaches band, inside inner bounds
        (150, 30),              # bounces back up above the rim (outer_top=50)
    ]
    results = _feed(sm, positions)
    assert len(results) == 1
    assert results[0].outcome is ShotOutcome.MISS


def test_reaches_below_rim_without_ever_being_inside_inner_bounds():
    sm = ShotStateMachine(_rim(), _config())
    # Ball skips straight from above-rim to below-rim (e.g. detection gap
    # across the band) while horizontally outside the inner gate throughout.
    positions = [
        (195, 10), (195, 20),  # arm (still within outer alignment tolerance)
        (195, 80),              # jumps to below rim, x still outside inner bounds
    ]
    results = _feed(sm, positions)
    assert len(results) == 1
    assert results[0].outcome is ShotOutcome.MISS


def test_occlusion_within_grace_does_not_fail_shot():
    sm = ShotStateMachine(_rim(), _config(occlusion_grace_frames=5))
    positions = [
        (150, 10), (150, 20),  # arm
        None, None, None,       # brief occlusion (e.g. hand at release) — within grace
        (150, 60),               # reacquire in band, inside inner bounds
        (150, 80),               # below rim -> MAKE
    ]
    results = _feed(sm, positions)
    assert len(results) == 1
    assert results[0].outcome is ShotOutcome.MAKE


def test_occlusion_beyond_grace_resolves_as_miss():
    sm = ShotStateMachine(_rim(), _config(occlusion_grace_frames=3, shot_timeout_frames=50))
    positions = [
        (150, 10), (150, 20),  # arm
        None, None, None, None,  # 4 consecutive misses > grace of 3
    ]
    results = _feed(sm, positions)
    assert len(results) == 1
    assert results[0].outcome is ShotOutcome.MISS


def test_net_occlusion_inside_grace_still_resolves_make():
    """A netted rim briefly hides the ball at/after the band; should behave
    identically to the no-net case as long as occlusion stays within grace."""
    sm = ShotStateMachine(_rim(), _config(occlusion_grace_frames=5))
    positions = [
        (150, 10), (150, 20),
        (150, 60),   # enters band, inside inner bounds
        None, None,  # net occludes the ball briefly
        (150, 80),   # reappears below rim -> MAKE
    ]
    results = _feed(sm, positions)
    assert len(results) == 1
    assert results[0].outcome is ShotOutcome.MAKE


def test_shot_never_resolving_times_out_as_miss():
    sm = ShotStateMachine(_rim(), _config(shot_timeout_frames=5, occlusion_grace_frames=100))
    positions = [(150, 10), (150, 20)]  # arm
    positions += [(150, 30)] * 10  # hovering above rim, never reaching band
    results = _feed(sm, positions)
    assert len(results) == 1
    assert results[0].outcome is ShotOutcome.MISS


def test_misaligned_motion_never_arms():
    sm = ShotStateMachine(_rim(), _config())
    # x=400 is far outside alignment tolerance of rim centered at 150
    results = _feed(sm, [(400, 10), (400, 20), (400, 30), (400, 80)])
    assert results == []
    assert sm.state is ShotState.IDLE


def test_resets_to_idle_ready_for_next_shot_after_resolving():
    sm = ShotStateMachine(_rim(), _config())
    make_positions = [(150, 10), (150, 20), (150, 60), (150, 80)]
    _feed(sm, make_positions)
    assert sm.state is ShotState.IDLE

    # A second shot should arm and resolve independently.
    results = _feed(sm, make_positions, start_frame=100)
    assert len(results) == 1
    assert results[0].outcome is ShotOutcome.MAKE
