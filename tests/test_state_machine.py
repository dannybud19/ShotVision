import pytest

from shotvision.config.settings import ShotLogicConfig
from shotvision.shot_logic.rim import RimRegion
from shotvision.shot_logic.state_machine import (
    ResolutionReason,
    ShotOutcome,
    ShotState,
    ShotStateMachine,
    _fit_cross_x,
)


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
    # Progressive rightward drift (realistic deflection shape, not a single
    # last-instant jump) landing outside inner_right=185 at the rim line.
    sm = ShotStateMachine(_rim(), _config())
    positions = [
        (150, 10), (150, 20),  # arm
        (165, 35),
        (180, 48),
        (200, 65),              # crosses rim_y=60 with estimated x ~194 -> rim-out
    ]
    results = _feed(sm, positions)
    assert len(results) == 1
    assert results[0].outcome is ShotOutcome.MISS


def test_bounces_upward_after_reaching_rim_height():
    # Post bounce-up-gating-fix: a bounce that happens AFTER a valid
    # through-crossing (_passed_through=True) no longer overturns the shot -
    # it now resolves MAKE once the whole ball clears the rim, instead of
    # the pre-fix MISS.
    sm = ShotStateMachine(_rim(), _config())
    positions = [
        (150, 10), (150, 20),  # arm
        (150, 60),              # reaches band, inside inner bounds -> passed_through=True
        (150, 30),              # bounces back above the rim - no longer resolves MISS here
        (150, 80),               # whole ball below rim -> MAKE (passed_through survived the bounce)
    ]
    results = _feed(sm, positions)
    assert len(results) == 1
    assert results[0].outcome is ShotOutcome.MAKE


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


def test_inband_first_detection_does_not_arm():
    # Arming requires the ball to be seen above the rim. (An earlier variant
    # armed from in-band detections too, to work around ByteTrack dropping
    # the fast ball above the rim; with that tracking bug fixed the stricter,
    # more false-positive-averse rule scores the ground-truth clips equally.)
    sm = ShotStateMachine(_rim(), _config(descent_min_frames=2))
    # rim: outer y 50..70 -> in-band is 50 <= y <= 70
    results = _feed(sm, [(150, 55), (150, 60)])
    assert sm.state is ShotState.IDLE
    assert results == []


def test_below_rim_detection_does_not_arm():
    sm = ShotStateMachine(_rim(), _config(descent_min_frames=2))
    results = _feed(sm, [(150, 90), (150, 95)])  # below outer_bottom=70
    assert sm.state is ShotState.IDLE
    assert results == []


# --- diagnostic reason tagging (does not change outcomes) ---


def test_reason_make_confirmed():
    sm = ShotStateMachine(_rim(), _config())
    results = _feed(sm, [(150, 10), (150, 20), (150, 60), (150, 80)])
    assert results[0].reason is ResolutionReason.MAKE_CONFIRMED
    assert results[0].entered_inner is True
    assert results[0].reached_band is True


def test_reason_rim_out_sideways():
    sm = ShotStateMachine(_rim(), _config())
    results = _feed(sm, [(150, 10), (150, 20), (165, 35), (180, 48), (200, 65)])
    assert results[0].reason is ResolutionReason.MISS_RIM_OUT_SIDEWAYS


def test_reason_below_without_inner():
    # Ball arms aligned, then its path crosses the rim line entirely outside
    # the outlined rim (interpolated crossing x > outer_right=200).
    sm = ShotStateMachine(_rim(), _config())
    results = _feed(sm, [(150, 10), (150, 20), (250, 80)])
    assert results[0].reason is ResolutionReason.MISS_BELOW_WITHOUT_INNER
    assert results[0].entered_inner is False


def test_reason_make_confirmed_after_bounce_post_passthrough():
    # A bounce back above the rim after a valid through-crossing does not
    # overturn the shot (the old MISS_BOUNCE_UP exit was unreachable and has
    # been removed; see experiments/proposed_state_machine_patches.md Patch 3).
    sm = ShotStateMachine(_rim(), _config())
    results = _feed(sm, [(150, 10), (150, 20), (150, 60), (150, 30), (150, 80)])
    assert results[0].reason is ResolutionReason.MAKE_CONFIRMED


def test_reason_occlusion_gap():
    sm = ShotStateMachine(_rim(), _config(occlusion_grace_frames=3, shot_timeout_frames=50))
    results = _feed(sm, [(150, 10), (150, 20), None, None, None, None])
    assert results[0].reason is ResolutionReason.MISS_OCCLUSION_GAP
    # 4 consecutive Nones, grace 3 -> resolves on the 4th.
    assert results[0].occlusion_frames_before_resolve == 4


def test_reason_timeout_above():
    sm = ShotStateMachine(_rim(), _config(shot_timeout_frames=5, occlusion_grace_frames=100))
    positions = [(150, 10), (150, 20)] + [(150, 30)] * 10
    results = _feed(sm, positions)
    assert results[0].reason is ResolutionReason.MISS_TIMEOUT_ABOVE


def test_result_carries_recent_trace():
    sm = ShotStateMachine(_rim(), _config())
    results = _feed(sm, [(150, 10), (150, 20), (150, 60), (150, 80)])
    trace = results[0].recent_trace
    # Trace holds (frame_idx, pos) tuples starting at the frame the shot
    # armed (frame 1 here — arming needs descent_min_frames=2 descending
    # frames, so frame 0 is still pre-arm), in order through resolution.
    assert trace[-1] == (3, (150, 80))
    assert trace[0] == (1, (150, 20))  # arming frame recorded
    assert results[0].armed_frames >= 1


# --- crossing-based scoring robustness (the point of the rewrite) ---


def test_make_scored_even_with_a_thin_rim_band():
    # A 3px-tall rim band (like the miscalibration that broke band-membership
    # scoring). The ball is never detected *inside* the band, jumping from
    # above it to below it — crossing interpolation must still score the make.
    thin_rim = RimRegion.from_points(
        [(100, 166), (200, 166), (100, 169), (200, 169)], inner_bound_shrink=0.15
    )
    sm = ShotStateMachine(thin_rim, _config())
    # arm above (y<166), then a single detection well below the 3px band,
    # aligned through the center — no detection ever lands in y:166..169.
    results = _feed(sm, [(150, 150), (150, 158), (150, 190)])
    assert len(results) == 1
    assert results[0].outcome is ShotOutcome.MAKE
    assert results[0].reason is ResolutionReason.MAKE_CONFIRMED


def test_make_scored_when_ball_is_occluded_through_the_rim():
    # Ball detected above the rim, then occluded (None) for several frames as
    # it passes through the net, reappearing below. The crossing spans the gap.
    sm = ShotStateMachine(_rim(), _config(occlusion_grace_frames=6))
    results = _feed(sm, [(150, 10), (150, 20), None, None, None, (150, 90)])
    assert len(results) == 1
    assert results[0].outcome is ShotOutcome.MAKE
    assert results[0].reason is ResolutionReason.MAKE_CONFIRMED


def test_whole_ball_must_be_below_rim_to_confirm_make():
    # After a valid through-crossing, a ball whose center is below the rim line
    # but whose body still straddles the rim (bbox top above outer_bottom) is
    # NOT yet confirmed; it only resolves once the whole ball clears the rim.
    from shotvision.shot_logic.state_machine import BallObservation

    sm = ShotStateMachine(_rim(), _config())  # rim y:50..70, rim_y=60
    sm.update((150, 40), 0)
    sm.update((150, 48), 1)  # armed
    # crossing frame: center just below rim_y but bbox top (65) still above
    # outer_bottom (70) -> through-crossing registered, not yet resolved.
    straddle = BallObservation(x=150, y=68, left=145, top=65, right=155, bottom=71)
    assert sm.update(straddle, 2) is None
    assert sm.state is ShotState.ARMED
    # now the whole ball is below the rim -> make confirms.
    below = BallObservation.from_bbox((145, 72, 155, 82))
    result = sm.update(below, 3)
    assert result is not None
    assert result.outcome is ShotOutcome.MAKE


# --- _fit_cross_x: multi-point crossing estimate ---


def test_fit_cross_x_two_points_matches_linear_interpolation():
    # With exactly 2 points the least-squares fit must reduce to the same
    # straight-line interpolation the old 2-point-only formula used.
    x = _fit_cross_x([(100, 40), (200, 60)], target_y=50)
    assert x == pytest.approx(150)


def test_fit_cross_x_single_point_returns_its_x():
    assert _fit_cross_x([(123, 45)], target_y=999) == 123


def test_fit_cross_x_degenerate_same_y_returns_mean_x():
    # All points share a y (den=0 in the least-squares formula) -> no slope
    # info; fall back to the mean x rather than dividing by zero.
    x = _fit_cross_x([(100, 30), (200, 30), (150, 30)], target_y=30)
    assert x == pytest.approx(150)


def test_fit_cross_x_uses_full_window_not_just_last_two_points():
    # Approach trajectory sits consistently near x=150-152, then the frame
    # exactly at the crossing reads x=188 (single-frame noise: a partially
    # net-occluded bbox, motion blur, etc). A pure 2-point line trusts that
    # one noisy endpoint completely; the multi-point fit pulls the estimate
    # back toward the established trend instead.
    two_point_only = _fit_cross_x([(152, 40), (188, 60)], target_y=60)
    with_history = _fit_cross_x([(150, 20), (152, 40), (188, 60)], target_y=60)
    assert with_history < two_point_only
    assert two_point_only == pytest.approx(188)  # unchanged: identical to old formula


def test_multi_point_fit_recovers_make_that_two_point_interpolation_would_miss():
    # Same shape as the diagnosed real-clip failures (state_machine.py trace
    # showed makes scored MISS off a single noisy post-gap detection) but with
    # one extra confirmed point along the approach. A naive 2-point line
    # between (152,40) and (188,60) gives x=188 (outside inner_right=185,
    # would resolve MISS_RIM_OUT_SIDEWAYS); the multi-point fit uses the
    # earlier (150,20) point too and correctly lands inside the inner gate.
    sm = ShotStateMachine(_rim(), _config())
    positions = [
        (150, 10), (150, 20),  # arm
        (152, 40),
        (188, 60),              # crossing frame: fit (with history) -> ~182, inside
        (188, 80),               # whole ball below -> MAKE
    ]
    results = _feed(sm, positions)
    assert len(results) == 1
    assert results[0].outcome is ShotOutcome.MAKE
    assert results[0].reason is ResolutionReason.MAKE_CONFIRMED


def test_weak_observation_never_arms():
    from shotvision.shot_logic.state_machine import BallObservation
    sm = ShotStateMachine(_rim(), _config())
    for i, y in enumerate((10, 20, 30)):
        sm.update(BallObservation.from_bbox((147, y - 3, 153, y + 3), weak=True), i)
    assert sm.state is ShotState.IDLE


def test_weak_observation_keeps_shot_alive_but_never_resolves_it():
    from shotvision.shot_logic.state_machine import BallObservation
    sm = ShotStateMachine(_rim(), _config(occlusion_grace_frames=2))
    _feed(sm, [(150, 10), (150, 20)])  # arm
    assert sm.state is ShotState.ARMED
    # Weak boxes well past the grace period, even below the rim: no resolution.
    for i in range(2, 8):
        r = sm.update(BallObservation.from_bbox((147, 77, 153, 83), weak=True), i)
        assert r is None
    assert sm.state is ShotState.ARMED


def test_armed_shot_ignores_a_different_tracked_object():
    from shotvision.shot_logic.state_machine import BallObservation
    sm = ShotStateMachine(_rim(), _config(occlusion_grace_frames=5))

    def obs(x, y, tid):
        o = BallObservation.from_center(x, y)
        o.track_id = tid
        return o

    sm.update(obs(150, 10, 1), 0)
    sm.update(obs(150, 20, 1), 1)
    assert sm.state is ShotState.ARMED
    # The tracker switches to another object below the rim, outside the gate.
    assert sm.update(obs(300, 90, 2), 2) is None
    assert sm.state is ShotState.ARMED
    # The armed ball continues through the rim: a make.
    sm.update(obs(150, 60, 1), 3)
    r = sm.update(obs(150, 80, 1), 4)
    assert r is not None and r.outcome is ShotOutcome.MAKE


def test_prearm_streak_survives_a_single_missed_frame():
    sm = ShotStateMachine(_rim(), _config(descent_min_frames=2, prearm_max_missed_frames=1))
    _feed(sm, [(150, 10), None, (150, 25)])
    assert sm.state is ShotState.ARMED
    sm2 = ShotStateMachine(_rim(), _config(descent_min_frames=2, prearm_max_missed_frames=1))
    _feed(sm2, [(150, 10), None, None, (150, 25)])
    assert sm2.state is ShotState.IDLE
