> **Superseded 2026-11-03.** The root cause of the missing makes was ByteTrack (`model.track()`) dropping the fast-moving ball above the rim, not the arming or crossing logic analysed here. See the 2026-11-03 entry in `docs/PROJECT_LOG.md`. Kept for the record.

# Tracking Research: Why Real Makes Are Being Missed

## Section 1: Measured diagnosis

**Real makes are being silently dropped — not misclassified.** This is the headline finding, and it changes what kind of fix is worth pursuing.

This was measured by running `scripts/diagnose_shots.py` (extended this session to also flag "never-armed candidate episodes") against three ground-truth-labeled clips whose filenames encode the expected outcome — a convention confirmed in `sample_clips/SOURCES.md`.

| Clip | Expected make/miss | Resolved shots | Resolution reasons | Missing (never armed) |
|---|---|---|---|---|
| chonyy_one_score_one_miss.mp4 | 1/1 | 1 | miss_occlusion_gap×1 | 1 |
| chonyy_two_score_two_miss.mp4 | 2/2 | 2 | miss_below_without_inner×2 | 2 |
| chonyy_two_score_three_miss.mp4 | 2/3 | 3 | miss_below_without_inner×2, miss_occlusion_gap×1 | 2 |
| **Total** | **5 makes / 6 misses / 11** | **6** | 4× below_without_inner, 2× occlusion_gap | **5** |

### Key facts

- Of 11 real shot attempts across the three clips, only 6 ever produced a `ShotResult` at all. The count of missing (never-`ShotResult`'d) attempts equals the count of expected makes **exactly**, in all three clips individually.
- Every one of the 6 resolved shots came back MISS. Zero ever reached a valid inner-gate crossing (`entered_inner=True`). Zero instances of `MISS_BOUNCE_UP` anywhere in the data.
- The state machine's own state (`ShotState.IDLE` vs `ARMED`) was independently observed per frame. The extension grouped candidate frames (ball detected, above rim, aligned) into episodes and found **zero** cases of "a 2+ frame streak broken by a single dropped frame." In every missing attempt there were essentially 0-1 qualifying frames in the entire approach window — not a near-miss streak interrupted by a gap.
- Ball detection rate on this footage: 19.6%, 24.6%, 23.1% per clip — consistent with (and somewhat worse than in variance) the project's documented ~11% baseline on other footage.
- Two of the three clips share underlying footage: `two_score_three_miss` appears to be the `two_score_two_miss` recording with one extra miss appended — traces at frames 86 and 191 are byte-identical between them. **Sample-size caveat:** this dataset is effectively **two distinct source recordings**, not three independent samples.
- Manual trace review of 2 of the 6 resolved-MISS shots showed clear rim-out drift (ball x-position drifting from 597→584, outside the rim's outer box, while descending through the rim band) — genuine misses, not misclassifications. The other 4 resolved shots were **not** manually eyeballed frame-by-frame; the make/miss mapping rests on the exact count correlation plus this partial spot-check, not a full manual video review of all 11 shots.

### Conclusion

The data confirms the "ball detection is too sparse during the shot's approach to the rim to ever arm the state machine" failure mode as **dominant and severe** (not a mild single-frame-gap issue), and finds **zero evidence** for a separate hypothesis that had been raised from code-reading alone — a "bounce-up" check that can overturn an already-confirmed make. That second bug is real by code inspection but did not occur in this measured data, because no shot ever got far enough to be at risk of it.

---

## Section 2: Per-repo findings

For each repository: license status first (stated plainly), then relevance to this project's actual measured failure mode.

### yastrebksv/TrackNet

Unofficial PyTorch implementation of TrackNet V1/V4 (arXiv 1907.03698 and 2409.14543). **No LICENSE file; GitHub API confirms `license: null` — unusable to reuse code as-is.** Architecture ideas are still fair to learn from.

Multi-frame (3-consecutive-frame input) Gaussian heatmap regression for small/fast/occluded ball detection — architecturally plausible fit for this project's sparse-detection problem (that's exactly what it was built for), but only ever validated on tennis/badminton against uniform court backgrounds, never against rim/net occlusion specifically. A boost here is plausible, not proven.

No custom CUDA kernels; standard conv ops throughout (MPS-compatible), but the reference code hardcodes `device='cuda'` with no fallback — a trivial one-line patch, not a structural blocker.

Original training used ~19,835 labeled frames across 10 tennis broadcasts. Fine-tuning cost for basketball is inferred from architecture/hyperparameters (VGG16-style encoder-decoder, `num_epochs=500` default in the reference script), since no hardware/time figures are documented — expect a non-trivial multi-hour-plus training investment on an M2. This is a reasoned estimate, not a verified one.

Its 3-frame fixed sliding-window inference (no RNN/stateful memory) means running it only as a fallback during a state-machine-flagged shot window is architecturally sound, not a hack — it would just need a small buffer of prior frames before the window opens.

### NohanJoemon/Basketball-video-classification

**No LICENSE file; GitHub API confirms `license: null` — unusable to reuse code as-is.**

Whole-frame VGG16 feature extraction at ~1fps + a dense sigmoid head, averaged across sampled frames (no ROI cropping, no temporal modeling) — trained on 2,194 clips (885 scoring / 1,309 non-scoring).

Structurally mismatched to this project's actual failure mode: it's designed to be invoked as a "second opinion when the primary logic times out," but this project's missing shots never reach a timeout state — they never leave `IDLE` in the first place, so a second-opinion-at-timeout hook would never fire for them.

A rim-cropped, temporally-aware lighter-weight variant (MobileNetV3/EfficientNet-Lite scale, few hundred to ~1000 labeled clips) is a more appropriate design than this repo's approach if pursued later, but doesn't address the measured failure mode as currently scoped.

### avishah3/AI-Basketball-Shot-Detection-Tracker

**No LICENSE file, `license: null` — unusable to reuse code as-is** (note: this project's own default checkpoint `models/basketball_best.pt` was already sourced from this same repo per this project's README, with the license caveat already documented there).

Its make/miss scoring uses only the *first* ball point above the rim and *first* point below it (2-point interpolation) to fit a crossing line — this is weaker than this project's existing 4-point least-squares crossing fit already in `shot_logic/state_machine.py`. Not an upgrade.

### nvan21/Basketball-Shot-Detection

**No LICENSE file, `license: null` — unusable to reuse code as-is.**

Uses a 2nd-degree parabola fit over accumulated points, but requires ≥15 in-ROI trajectory samples to trigger its confidence check — degrades badly (not gracefully) under this project's actual sparse-detection failure mode, since 15 samples is far more than what's typically available. Its own documentation acknowledges a pure-2D depth-ambiguity limitation (can't distinguish a ball grazing the back rim from a clean make).

### iamyb/shotcut

**MIT licensed — confirmed directly from the repo's LICENSE file. Usable.**

Stationary-camera ball/hoop interaction analysis for highlight extraction; no published algorithm detail beyond "trajectory + hoop interaction" was retrievable, so limited actionable detail despite being license-clear.

### srz08/basketball-shot-analysis

**No LICENSE file, `license: null` — unusable to reuse code as-is.**

This repo is actually about shooting-form/biomechanics analysis (YOLO + MediaPipe pose), not make/miss scoring — the weakest reference for this project's actual problem.

### Net-motion / pixel-disturbance signal

No standalone open-source implementation found (none of the repos above implement it); appears in commercial patent literature only. Cited generically: patent literature describes hoop/net-movement detection combined with ball-in-ROI state to adjudicate makes — a known idea, not proprietary to any one source.

Cheap and real-time-feasible (frame-differencing/optical-flow over a small fixed ROI, sub-millisecond, no model inference needed) but needs per-camera/per-setup calibration of the net region, and doesn't work on net-less rims (which this project explicitly supports per its own docstrings) — would need to be optional/gated, not required.

Critically: it only helps *after* a shot is already being tracked near the rim — it does not address this project's measured failure mode (shots that never arm in the first place).

---

## Section 3: Ranked recommendations

**Update 3, real-pipeline post-apply validation — arming fixed, a second bug surfaced:** Patch 2 and Patch 3 (`experiments/proposed_state_machine_patches.md`) were applied to `shot_logic/state_machine.py` and re-run through the real pipeline (`scripts/diagnose_shots.py`, not the offline simulation) against all 3 ground-truth clips. **Arming is fully fixed: 11 of 11 real attempts now produce a `ShotResult`, up from 6 of 11 — the never-armed problem is gone, and the original 6 shots' outcomes/reasons are unchanged (no regression).** However, **all 11 resolved shots come back MISS**, all 5 newly-rescued shots via `MISS_BELOW_WITHOUT_INNER` with `entered_inner=False` — when ground truth expects 5 of these 11 to be makes. Root cause (verified by reading `rim.py`, not just inferred): `rim.rim_y` (line 31) is the *midline* of the outer band, but Patch 2 arms from any in-band position, not just the top of the band. Given ~20% per-frame detection and a 2-consecutive-frame arm requirement, the trajectory points seeded into `_recent` at arming time are frequently already at or past `rim_y` by the time `ARMED` triggers. `_update_armed`'s crossing check (`prev.y < rim.rim_y <= y`) requires a confirmed point *before* the midline to exist at all — for these shots there no longer is one, so `_passed_through` can never become `True` for the rest of that shot's life, and it falls through to the "whole ball below, no valid crossing" branch regardless of whether it was a real make. **This is a newly-discovered second bug, not something Patch 2's original validation (`simulate_inband_arms`) could have caught — that simulation only checked whether shots armed, never whether they scored correctly afterward.** Kept applied (tests pass, no regression to the original 6 shots), but the missing-makes problem is not resolved end-to-end yet. Not yet investigated further pending direction — see Section 4.

**Update 2, root cause identified (same session):** the open question left by Update 1 has been answered — see the new top entry below. Both this and Update 1 are left visible rather than silently rewritten, per this doc's own adversarial-review standard.

1. **Arm from in-band detections too, not only above-rim ones — root cause identified AND fix validated.**
   `experiments/arm_gate_sweep.py` was extended to break each missing shot's detected frames down by which sub-condition of the qualifying test they fail. Result, identical across all 5 missing makes: detection rate 85-100% (the ball is reliably seen), `is_aligned` never fails, and `is_above` fails 100% of the time. A per-frame classification trace explains why: every one of the 5 windows' first detected frame is already `IN-BAND` — the ball is **never once observed while genuinely above the rim**, only from the moment it's already at rim height, descending smoothly to `below` from there.
   This means `_update_idle`'s hard requirement to confirm the ball above the rim before arming is checking for a precondition that essentially never occurs for a real make on this camera setup. The fix: let the pre-arm phase also arm from an aligned, descending `IN-BAND` detection, not only an above-rim one.
   **Validated**: `simulate_inband_arms` in `experiments/arm_gate_sweep.py` implements exactly this (same consecutive-streak/jitter/alignment semantics as today, only the vertical zone relaxed from "above" to "above OR in-band") and was run against real detector/tracker/rim-tracker output for all 3 clips. **Result: 5 of 5 missing makes rescued, with 0 spurious extra arms anywhere across all 3 clips.**
   **Confidence: high**, both on the mechanism (direct trace of real data) and the fix (validated with a clean, unambiguous result — not just "didn't hurt," but rescued every missing shot with zero cost). The one-line diff (`self.rim.is_above(y)` → `not self.rim.is_below(y)`) is drafted in `experiments/proposed_state_machine_patches.md` (Patch 2), including new test coverage — not yet applied to `shot_logic/state_machine.py`, pending explicit confirmation per this project's standing rule.
   - **Strongest case against:** arming on an in-band detection is a materially looser precondition than requiring above-rim first — closer to the rim's scoring zone, where false arms from non-shot motion (a hand near the rim, a pass through the area) are more plausible in principle. The measured spurious-arm count on this data is 0, which is reassuring but not proof it stays 0 on footage with more incidental near-rim motion (passes, rebounds, players' hands) than these 3 clips happen to contain.
   - **Sample-size caveat, now stronger:** the 5 missing-shot trajectories' raw pixel coordinates are strikingly similar across all 3 clips, suggesting the whole `chonyy_*` corpus shares one camera position, not just "two source recordings." This finding — like everything else in this document — is validated against effectively one camera setup only.

2. **Loosen the arm-gate requirement to tolerate gaps — validated, and shown to be the wrong lever for this specific problem.**
   The idea: instead of requiring `descent_min_frames` *consecutive* qualifying frames before arming, require N qualifying frames within a longer rolling window that tolerates gaps. Proposed as the original top recommendation, on the reasoning that it targets sparse-but-nonzero detections during approach.
   **`experiments/arm_gate_sweep.py` ran this against real detector/tracker/rim-tracker output for all 3 clips, sweeping N∈{2,3} × W∈{4,6,8,10,15}. Result: 0 of 5 missing makes rescued at every setting, with 0 spurious extra arms.** Now explained by #1 above: there's no gap to bridge — the ball is never above-rim at all in these windows, so no amount of temporal gap-tolerance on the *same* above-rim requirement can help. This recommendation is superseded by #1, not merely deprioritized.
   Still a safe, low-risk change in isolation (never produced a spurious arm), but should not be pursued as a standalone fix — if #1 is implemented, this becomes redundant for the above-rim case it targeted, though it could still be layered on top of #1's in-band requirement for the same gap-tolerance reasoning.

3. **TrackNet-style near-rim detection booster, invoked only as a fallback during a flagged shot window.**
   **Demoted following #1's finding.** This was framed as the likely fix if detection turned out to be genuinely silent — it isn't; detection is 85-100% once the ball is in-band. A detection-rate booster doesn't address an architectural precondition problem. Still potentially useful later (e.g. if #1's fix reveals the ball is *also* poorly detected during whatever brief above-rim window does exist on other camera setups), but it's no longer the natural second choice.

4. **Net-motion/pixel-disturbance signal as a secondary confirming feature** — cheap, but doesn't address an arming precondition problem; a complement to #1, not an alternative to it.

5. **Clip classification second opinion** — lowest priority; structurally can't fire for shots that never reach a timeout state (see Section 2), and its reference implementation is unlicensed besides.

6. **The bounce-up / `_passed_through` gating fix** (real bug, found by code read: `_update_armed`'s bounce-up check doesn't check whether the ball already validly crossed the inner gate before allowing a later noisy detection to overturn it to MISS) — keep on the list as a correct, trivial-risk fix, but it is **not** the cause of the reported symptom in this measured data (zero shots got far enough to be at risk of it, since none of them ever armed). Fully designed and validated in `experiments/proposed_state_machine_patches.md`, including a traced consequence: once applied, `MISS_BOUNCE_UP` becomes structurally unreachable, not just rarer. Independent of #1 — can be applied on its own at any time. Low priority, do eventually.

**"No new model needed" holds, more clearly than at either earlier point in this document.** The root cause is a single hard-coded precondition in the state machine's arming logic, not a detection-quality problem and not a config-threshold problem. The fix is a one-line logic change to `shot_logic/state_machine.py` — drafted and validated (5/5 rescued, 0 spurious arms), not yet applied.

---

## Section 4: Do this next

**Superseded by Update 3 above.** Patch 2 and Patch 3 have been applied. The resolved-shot count did move from 6/11 to 11/11 as predicted, but all 11 resolve as MISS — the missing-makes problem is now a scoring bug (crossing never detected) rather than an arming bug. **New highest-value next step:** fix the crossing check in `_update_armed` so a shot that arms already in-band (with no confirmed point above `rim.rim_y`) can still register a valid through-crossing — candidate approaches (not yet designed or validated): (a) treat the arming observation itself as a potential crossing point when it's already at-or-past `rim_y`, testing its x against the inner bounds directly rather than requiring a prior above-the-line point; (b) seed `_recent` at arm time with a synthetic/extrapolated pre-line point; (c) some other approach worth designing fresh rather than assuming (a) or (b) is right without checking against the real traces first. Needs the same measure-before-fix discipline this document has followed throughout: trace what `rim_y` actually is relative to arming position in the 5 rescued shots' real data before designing a fix, don't guess.

**Footage to film, still the top priority after that:** the 5 missing-shot trajectories' raw pixel coordinates are strikingly similar across all 3 clips (e.g. `(633,191)→...→(610,247)` and `(632,192)→...→(610,247)`), strongly suggesting the entire `chonyy_*` corpus shares one camera position/hoop setup, not just two source recordings as previously stated. Every finding in this document is effectively validated against **a single camera setup**. Footage from a genuinely different angle/distance/gym is the only way to know whether "makes are never seen above the rim" is a property of basketball shot geometry generally, or an artifact of this one camera's placement — and whether the in-band arming fix's 0-spurious-arms result holds up where there's more incidental near-rim motion (passes, rebounds, hands) than these 3 clips contain.

---

## Adversarial self-review

- **Checked:** did the ranking favor the intellectually interesting fix (TrackNet) over the boring one (gate logic change)? No — the boring fix is ranked first specifically because it's what the measured data supports; TrackNet is ranked second specifically because its own research surfaced it as unvalidated for this exact occlusion pattern.
- **Flagged as unverified-not-fact:** TrackNet's fine-tuning cost (labeled-frame count, training hours) is inferred from its hyperparameters/architecture, not documented anywhere; the clip-classifier's "few hundred to ~1000 labeled clips" estimate is reasoned by analogy to its own training set, not verified against an actual second-opinion implementation.
- **Flagged as assumed-not-checked:** the clean 1:1 correlation between "missing shots" and "expected makes" rests on filename ground truth plus a partial manual spot-check of 2 of 6 resolved traces, not a full frame-by-frame human review of all 11 shots. The two-source-recording sample size is a real limitation, stated prominently rather than buried in a footnote.
