> **Superseded 2026-11-03.** The root cause of the missing makes was ByteTrack (`model.track()`) dropping the fast-moving ball above the rim, not the arming or crossing logic analysed here. See the 2026-11-03 entry in `docs/PROJECT_LOG.md`. Kept for the record.

# Proposed `shot_logic/state_machine.py` patches — NOT applied

**All three patches below are proposals only.** None have been applied to
`shotvision/shot_logic/state_machine.py`, `shotvision/config/settings.py`,
`shotvision/config/default.json`, or `tests/test_state_machine.py`. Each
requires explicit human confirmation before being applied to the real
pipeline.

Read in this order: **Patch 2 is the current recommendation** — it's the
one validated against the actual root cause (see
`docs/tracking-research.md`). Patch 1 (windowed arm-gate) was the
original top idea, built and tested first, and found to rescue 0/5 real
missing makes — kept here for the record, not as something to apply.
Patch 3 (bounce-up gating) is an independent, low-risk bug fix that can
be applied on its own regardless of what happens with 1/2.

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

## Patch 2: Arm from in-band detections too, not only above-rim ones

### Why, and what the validation showed

`docs/tracking-research.md`'s root-cause finding: for all 5 missing makes,
ball detection is 85-100% (reliable) and `is_aligned` never fails, but
`is_above` fails 100% of the time — every missing shot's first detected
frame is already `IN-BAND`, descending smoothly to `below`. The ball is
never once observed genuinely above the rim on this camera setup, so
`_update_idle`'s hard requirement to see it above the rim before arming
is checking for a precondition that essentially never occurs for a real
make here.

**Validated in `experiments/arm_gate_sweep.py`'s `simulate_inband_arms`**,
run against real detector/tracker/rim-tracker output for all 3 clips: the
qualifying test relaxed from "above-rim" to "above-rim OR in-band" (same
consecutive-streak/jitter/alignment semantics as today, only the vertical
zone changes) — **rescues 5 of 5 missing makes, with 0 spurious extra arms
anywhere across all 3 clips.** Unlike Patch 1 (the windowed arm-gate,
which rescued 0/5 regardless of parameters because there was no above-rim
detection to ever bridge a gap to), this directly targets the confirmed
mechanism and the validation numbers back it up cleanly.

**Confidence: high**, on the same camera setup this was measured on. The
sample-size caveat still applies in full — see `docs/tracking-research.md`
Section 4 — this has only been validated on what is effectively one
camera position.

### `state_machine.py` change

Single-line change to the qualifying condition in `_update_idle`:

```python
def _update_idle(self, obs: BallObservation | None, frame_idx: int) -> None:
    if obs is None:
        self._reset_prearm()
        return None

    x, y = obs.center
    if not self.rim.is_below(y) and self.rim.is_aligned(x, self.config.align_tolerance_ratio):
        if self._prearm_last_y is not None and y >= self._prearm_last_y - _DESCENT_JITTER_PX:
            self._prearm_streak += 1
        else:
            self._prearm_streak = 1
        self._prearm_last_y = y

        if self._prearm_streak >= self.config.descent_min_frames:
            self._reset_prearm()
            self._reset_armed()
            self.state = ShotState.ARMED
            self._recent.append(obs)  # seed the trajectory for crossing tests
            self._trace.append((frame_idx, obs.center))
    else:
        self._reset_prearm()
    return None
```

Only `self.rim.is_above(y)` → `not self.rim.is_below(y)` changes (line
197 in the current file). No new config field needed — `RimRegion.is_below`
already exists (`rim.py`) and is reused as-is.

### Why not combine with Patch 1 (windowed arm-gate)

Patch 1 is now understood to target a different, non-occurring failure
mode on this dataset (a partial streak broken by a gap — never observed;
every missing shot had either 0 or 100% qualifying frames within its
window depending on which zone counts). It remains a safe, low-risk,
independent addition if a future camera setup exhibits genuine
above-rim-detection gaps that this one didn't, but isn't needed to fix
the problem actually measured here. Recommend applying Patch 3 alone
first, re-measuring, and only adding Patch 1 later if a *new* failure
mode (a genuine gap-broken streak) is observed on different footage.

### New/updated tests for `tests/test_state_machine.py`

The existing pre-arm tests should be reviewed for whether any implicitly
depended on "in-band but not yet above-rim" correctly failing to arm
(none currently appear to, based on the test names, but this should be
confirmed at apply-time, not assumed). New coverage:

```python
def test_inband_detection_arms_without_ever_being_seen_above_rim():
    # Regression test for the actual measured failure mode: a ball whose
    # first-ever detection is already in-band (never observed above the
    # rim at all) must still be able to arm, given enough consecutive
    # in-band+aligned+descending frames. This is the exact shape of all 5
    # real missing makes in the ground-truth clips (see
    # docs/tracking-research.md).
    sm = ShotStateMachine(_rim(), _config(descent_min_frames=2))
    # rim: outer y 50..70 (see _rim() helper) -> in-band is 50 <= y <= 70
    positions = [(150, 55), (150, 60)]
    _feed(sm, positions)
    assert sm.state is ShotState.ARMED


def test_inband_arming_still_requires_alignment():
    # Loosening the vertical test must not loosen the horizontal one -
    # an in-band but misaligned detection (x far from rim center) must
    # still fail to arm, same as today's above-rim behavior.
    sm = ShotStateMachine(_rim(), _config(descent_min_frames=2))
    positions = [(400, 55), (400, 60)]
    results = _feed(sm, positions)
    assert sm.state is ShotState.IDLE
    assert results == []


def test_below_rim_detection_still_does_not_arm():
    # The fix relaxes above-rim to above-OR-in-band, not to "anywhere" -
    # a detection already below the rim must still fail to arm, since
    # by that point a real shot attempt would already be resolving
    # through _update_armed, not still in pre-arm.
    sm = ShotStateMachine(_rim(), _config(descent_min_frames=2))
    positions = [(150, 90), (150, 95)]  # below outer_bottom=70
    results = _feed(sm, positions)
    assert sm.state is ShotState.IDLE
    assert results == []
```

(Exact rim bounds/coordinates above assume this file's existing `_rim()`
test helper — verify against its actual values at apply-time rather than
trusting these numbers blindly.)

---

## Patch 3: Bounce-up gating fix

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
