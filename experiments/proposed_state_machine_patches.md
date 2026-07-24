# Proposed `shot_logic/state_machine.py` patches — NOT applied

**Both patches below are proposals only.** Neither has been applied to
`shotvision/shot_logic/state_machine.py`, `shotvision/config/settings.py`,
`shotvision/config/default.json`, or `tests/test_state_machine.py`. Each
requires explicit human confirmation before being applied to the real
pipeline.

---

## Patch 1: Windowed arm-gate (gap-tolerant pre-arm)

### Why, and what the sweep actually showed

`docs/tracking-research.md` ranked "loosen the arm-gate from N-consecutive to
N-within-a-window" as the top recommendation for the missing-makes problem.
`experiments/arm_gate_sweep.py` was built this session to validate that
before proposing it for real. The honest result:

- The sweep's baseline replication reproduces the known **0 of 5** missing
  makes rescued by today's code — this validates the replication is
  faithful, it is not the interesting number.
- The windowed variant, swept across N∈{2,3} × W∈{4,6,8,10,15}, **also
  rescues 0 of 5** at every single (N, W) combination tested, with **0**
  spurious extra arm events anywhere in the 3 clips at every setting.
- This is not a bug in the sweep: a direct count of raw qualifying frames
  (detected + above-rim + aligned, before descent/consecutiveness is even
  considered) inside each of the 5 best-effort missing-shot windows came
  back **0 in all 5 cases**. No amount of gap tolerance can recover a signal
  that was never detected in the first place — for these 5 specific
  measured misses, the ball is never confirmed-detected while
  simultaneously above the rim and horizontally aligned during the
  approach at all, not merely inconsistently.

**What this means for this patch:** it is still a low-risk, directionally
reasonable change — it never introduced a spurious arm anywhere in the
measured data, and it should still help *other* footage where a real
partial-but-gap-broken streak occurs (this dataset's 5 misses simply didn't
happen to be that failure mode; the earlier "0 cases of a 2+ frame streak
broken by a single gap" finding in `docs/tracking-research.md` holds up and
is now confirmed even more strongly: it's 0 qualifying frames, not 1). It
should **not** be presented as a fix for the measured missing-makes problem
on its own. Pair it with either loosening the above-rim/aligned test itself,
or a real detection-sparsity fix (`docs/tracking-research.md` recommendation
#2), if the goal is actually rescuing these 5 shots.

Parameters below (`descent_min_frames=2` unchanged, new
`prearm_window_frames=8`) are the sweep's reasoned starting default — picked
because it costs nothing in spurious arms in this data — **not** a
data-selected optimum, since the sweep was flat (0 rescued) across the whole
grid. Full numbers: see `experiments/arm_gate_sweep.py`'s output.

### Config change

`shotvision/config/settings.py`, `ShotLogicConfig`:

```python
@dataclass
class ShotLogicConfig:
    inner_bound_shrink: float = 0.15
    align_tolerance_ratio: float = 0.6
    descent_min_frames: int = 2
    # NEW: rolling window (in frames) the pre-arm phase looks back across
    # when counting qualifying frames, replacing the old strictly-
    # consecutive requirement. A qualifying frame no longer needs to be
    # immediately adjacent to the previous one — only within this many
    # frames of it — so a missed detection mid-approach no longer zeroes
    # pre-arm progress. Only *missing* detections get this tolerance; a
    # real detection that fails the above-rim/aligned/descending test still
    # hard-resets pre-arm progress, same as today. Default chosen as a
    # reasoned starting point (see experiments/arm_gate_sweep.py) — swept
    # against 3 ground-truth clips but the sweep was flat (0/5 rescued at
    # every setting tested on that data; see that script's docstring/output
    # for why), so this is not a data-optimized value, just a safe default
    # to start real-footage validation from.
    prearm_window_frames: int = 8
    occlusion_grace_frames: int = 12
    shot_timeout_frames: int = 90
    trajectory_buffer_len: int = 60
    rim_ema_alpha: float = 0.25
    rim_lost_grace_frames: int = 30
    rim_size_jump_max_ratio: float = 1.6
```

`shotvision/config/default.json`, `shot_logic` section:

```json
"shot_logic": {
  "inner_bound_shrink": 0.15,
  "align_tolerance_ratio": 0.6,
  "descent_min_frames": 2,
  "prearm_window_frames": 8,
  "occlusion_grace_frames": 12,
  "shot_timeout_frames": 90,
  "trajectory_buffer_len": 60,
  "rim_ema_alpha": 0.25,
  "rim_lost_grace_frames": 30,
  "rim_size_jump_max_ratio": 1.6
}
```

### `state_machine.py` change

`deque` is already imported at the top of the file (used for `_recent` and
`_trace`), so no new imports are needed.

```python
def _reset_prearm(self) -> None:
    # Rolling record of frame indices where a qualifying pre-arm frame was
    # observed (oldest first). Frames age out via pruning in _update_idle
    # once they fall outside config.prearm_window_frames of the current
    # frame — a missing detection does NOT clear this, only pruning and a
    # disqualifying real detection do. This replaces the old strictly-
    # consecutive _prearm_streak counter.
    self._prearm_window: deque[int] = deque()
    self._prearm_last_y: float | None = None

def _update_idle(self, obs: BallObservation | None, frame_idx: int) -> None:
    # Age out qualifying frames that have fallen outside the rolling
    # window, regardless of whether this frame itself has a detection —
    # the window is anchored on frame index, not on detection events.
    while (
        self._prearm_window
        and frame_idx - self._prearm_window[0] >= self.config.prearm_window_frames
    ):
        self._prearm_window.popleft()

    if obs is None:
        # Missing detection: tolerated. This is the entire behavior change
        # versus today — a gap no longer zeroes pre-arm progress, it just
        # doesn't add to it. The pruning above still ages old entries out.
        return None

    x, y = obs.center
    qualifies = (
        self.rim.is_above(y)
        and self.rim.is_aligned(x, self.config.align_tolerance_ratio)
        and (self._prearm_last_y is None or y >= self._prearm_last_y - _DESCENT_JITTER_PX)
    )
    if qualifies:
        self._prearm_window.append(frame_idx)
        self._prearm_last_y = y

        if len(self._prearm_window) >= self.config.descent_min_frames:
            self._reset_prearm()
            self._reset_armed()
            self.state = ShotState.ARMED
            self._recent.append(obs)  # seed the trajectory for crossing tests
            self._trace.append((frame_idx, obs.center))
    else:
        # Disqualifying real detection (misaligned, not above the rim, or
        # broke the descent-within-jitter check) - hard reset, same as
        # today's behavior for a genuinely disqualifying frame. Only a
        # *missing* detection gets the new gap tolerance.
        self._reset_prearm()
    return None
```

Note this bundles the descent-within-jitter check into the single
`qualifies` test, so an ascending real detection (fails only the descent
part) now hard-resets the window rather than softly restarting a streak at
1 the way today's code does. This is a deliberate simplification — it's
exactly what `experiments/arm_gate_sweep.py`'s windowed simulation
implements and what the sweep above validated, so the proposed real patch
and the validated experiment stay behaviorally identical. (Today's code's
finer distinction — ascend restarts the streak at 1 rather than zeroing it —
was not preserved; if that nuance turns out to matter, it would need a
second, separately-swept experiment before folding it in.)

### New tests for `tests/test_state_machine.py`

All three add `prearm_window_frames` to the `_config()` overrides (the
existing `_config()` helper would need this default added too, or each test
passes it explicitly as shown):

```python
def test_windowed_gate_arms_across_a_gap_that_todays_code_would_miss():
    # Two qualifying frames (0 and 4) with a 3-frame detection gap between
    # them. Today's strictly-consecutive _update_idle would reset the
    # streak to 0 on each missing frame and never reach descent_min_frames
    # consecutive - this exact shape is why 5 of 11 real shots in the
    # ground-truth clips never armed at all (see docs/tracking-research.md).
    # The windowed gate, with a window wide enough to span the gap, arms.
    sm = ShotStateMachine(_rim(), _config(descent_min_frames=2, prearm_window_frames=5))
    positions = [(150, 10), None, None, None, (150, 10)]
    _feed(sm, positions)
    assert sm.state is ShotState.ARMED


def test_windowed_gate_does_not_arm_on_sparse_non_shot_motion():
    # Two above-rim/aligned-looking detections that are genuinely far apart
    # in time (7-frame gap, wider than the 5-frame window) - not a real
    # approach, just sparse noise. Must not arm: the window must still
    # enforce *some* temporal locality, not accept any two qualifying
    # frames anywhere in the clip. Matches the current design's miss-biased
    # philosophy (ambiguous cases resolve to "don't arm", not "arm").
    sm = ShotStateMachine(_rim(), _config(descent_min_frames=2, prearm_window_frames=5))
    positions = [(150, 10), None, None, None, None, None, None, (150, 10)]
    results = _feed(sm, positions)
    assert sm.state is ShotState.IDLE
    assert results == []


def test_windowed_gate_disqualifying_frame_still_hard_resets():
    # A genuinely disqualifying REAL detection (misaligned x=400, far
    # outside tolerance) between two qualifying frames must still reset
    # progress entirely, even though the window would otherwise easily
    # span the gap - only *missing* detections get the new tolerance, a
    # real detection that fails the qualifying test does not, matching the
    # patch's stated intent exactly.
    sm = ShotStateMachine(_rim(), _config(descent_min_frames=2, prearm_window_frames=10))
    positions = [(150, 10), (400, 10), (150, 10)]
    results = _feed(sm, positions)
    assert sm.state is ShotState.IDLE
    assert results == []
```

---

## Patch 2: Bounce-up gating fix

**Status: verified-by-code-read, not measured-as-occurring-in-this-dataset.**
Zero instances of `MISS_BOUNCE_UP` occurred anywhere in the 3 ground-truth
clips measured this session (see `docs/tracking-research.md` Section 1) —
no shot ever got far enough through the state machine to be at risk of this
bug. This is a real, low-risk fix found by reading the code, reproduced
faithfully here per this session's earlier design, not redesigned.

### The bug

In `_update_armed`:

```python
if self._reached_rim and rim.is_above(y):
    return self._resolve(ShotOutcome.MISS, frame_idx, ResolutionReason.MISS_BOUNCE_UP)
```

This does not check whether the ball already validly crossed the inner
scoring gate (`self._passed_through`) before allowing a later, possibly
noisy, detection that reads as "above the rim" to overturn an
already-confirmed make to a miss.

### The fix

```python
if self._reached_rim and not self._passed_through and rim.is_above(y):
    return self._resolve(ShotOutcome.MISS, frame_idx, ResolutionReason.MISS_BOUNCE_UP)
```

### Observed consequence worth flagging (not a redesign, just tracing the control flow)

Given the rest of `_update_armed`'s control flow, `_reached_rim` can only
remain `True` *across* frames (i.e., without the same call immediately
resolving and returning) via the inner-bounds branch of the crossing check —
and that branch sets `_passed_through = True` in the same statement block,
on the same frame. Both other paths that set `_reached_rim = True` (the
outer-bounds crossing branch, and the whole-ball-below-rim branch) always
resolve and return immediately in that same call, so they can never leave
`_reached_rim = True` dangling for a later frame to see.

Net effect: with this fix applied, `self._reached_rim and not
self._passed_through` can never be `True` on any frame *after* the one
where `_reached_rim` was first set — meaning `ResolutionReason.MISS_BOUNCE_UP`
becomes structurally unreachable, not just rarer. This is consistent with
zero measured occurrences in this session's data, and is exactly the
"overturns an already-good make" bug being fixed — it isn't presented here
as a reason to change the proposed fix, just as a consequence a human
reviewer should know before applying it (e.g., whether to also remove the
now-dead `ResolutionReason.MISS_BOUNCE_UP` enum member and its trace
plumbing is a separate decision, deliberately left open here rather than
folded into this patch).

### Required test updates

`tests/test_bounces_upward_after_reaching_rim_height` and
`tests/test_reason_bounce_up` both use the exact same trajectory —
`[(150, 10), (150, 20), (150, 60), (150, 30)]` — and both currently assert
`MISS`. Tracing it against rim `y:50..70` (`rim_y=60`): the crossing check
at `(150, 60)` satisfies `prev.y(20) < rim_y(60) <= y(60)`, and the fitted
crossing x lands inside the inner bounds (115..185), so `_passed_through`
becomes `True` on the *same* frame `_reached_rim` becomes `True`. Under the
fix, the next frame's bounce back up to `(150, 30)` therefore no longer
triggers `MISS_BOUNCE_UP` (per the "observed consequence" above, it never
can again for any trajectory) — the shot keeps waiting, unresolved, for
the whole ball to clear the rim. Both tests need an added final point,
e.g. `(150, 80)`, to reach `obs.top >= rim.outer_bottom` and resolve —
now correctly as `MAKE`, since `_passed_through` survived the bounce.

```python
def test_bounces_upward_after_reaching_rim_height():
    # Renamed intent post-fix: this trajectory demonstrates that a bounce
    # AFTER a valid through-crossing no longer overturns the shot - it now
    # resolves MAKE once the whole ball clears the rim, instead of the
    # pre-fix MISS.
    sm = ShotStateMachine(_rim(), _config())
    positions = [
        (150, 10), (150, 20),   # arm
        (150, 60),               # reaches band, inside inner bounds -> passed_through=True
        (150, 30),               # bounces back above the rim - no longer resolves MISS here
        (150, 80),               # whole ball below rim -> MAKE (passed_through survived the bounce)
    ]
    results = _feed(sm, positions)
    assert len(results) == 1
    assert results[0].outcome is ShotOutcome.MAKE


def test_reason_bounce_up():
    # NOTE: post-fix, this can no longer test MISS_BOUNCE_UP - per the
    # "observed consequence" note above, that reason becomes structurally
    # unreachable once the fix is applied, so no trajectory can exercise it
    # anymore. Recommend renaming this test (e.g. to
    # test_reason_make_confirmed_after_bounce_post_passthrough) rather than
    # keeping a name that no longer matches what it verifies. Body, with the
    # same added final point as above:
    sm = ShotStateMachine(_rim(), _config())
    results = _feed(sm, [(150, 10), (150, 20), (150, 60), (150, 30), (150, 80)])
    assert results[0].reason is ResolutionReason.MAKE_CONFIRMED
```

If preserving direct test coverage of `ResolutionReason.MISS_BOUNCE_UP`
itself is wanted despite it becoming unreachable, that's not possible with
a real trajectory post-fix — the only way to exercise that branch at all
would be to construct the machine already mid-armed with `_reached_rim`
manually forced `True` and `_passed_through` manually forced `False`
(bypassing `_update_armed`'s own state transitions entirely), which tests
the branch's literal code rather than any reachable real behavior. Left as
a judgment call for whoever applies this patch rather than decided here.
