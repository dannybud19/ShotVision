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

**Update, post-validation (same session):** recommendation #1 below was written before `experiments/arm_gate_sweep.py` existed. It has since been run against real detector output for all 3 clips, and the result changes what #1 can honestly claim — see its entry below for the corrected verdict. This is left visible rather than silently rewritten, per this doc's own adversarial-review standard: a "high confidence" claim that the validation step later falsified is exactly the kind of thing that should be shown, not erased.

1. **Loosen the arm-gate requirement itself — validated, and it is *not* sufficient on its own.**
   The idea: instead of requiring `descent_min_frames` *consecutive* qualifying frames (ball detected, above rim, x-aligned, descending) before a shot even starts being tracked, require N qualifying frames within a longer rolling window that tolerates gaps. This was proposed as the top recommendation on the reasoning that it directly targets sparse-but-nonzero detections during approach, without touching the crossing/scoring logic at all.
   **`experiments/arm_gate_sweep.py` ran this against the real detector/tracker/rim-tracker output for all 3 clips, sweeping N∈{2,3} × W∈{4,6,8,10,15}. Result: 0 of 5 missing makes rescued at every single (N, W) tested — and 0 spurious extra arms anywhere, at every setting.** This is not a bug in the sweep (its baseline replication correctly reproduced the known 0/5 result first, as a self-check). A direct count of raw frames satisfying "detected + above-rim + aligned" — the compound qualifying test, with descent/consecutiveness set aside entirely — inside each of the 5 missing-shot windows came back **0 in all 5 cases**. No amount of gap tolerance can recover a signal that was never captured under that test in the first place.
   **Revised confidence: low**, as a standalone fix for the measured problem (was: high). **Revised effort/risk: unchanged (low-medium effort, low risk)** — it never produced a spurious arm in this data, so it remains safe to layer in, just not sufficient alone.
   - *Superseded design note (still holds):* an even narrower earlier version (a small fixed `occlusion_grace_frames`-style tolerance for single dropped frames) was already known to be insufficient before this measurement — the sweep confirms the problem is more severe than "occasional single-frame gaps," it's the complete absence of qualifying frames.
   - **What actually needs to happen instead, per the sweep's own finding:** either (a) the qualifying test itself (`is_above` / `is_aligned`) needs loosening or auditing — the best-effort window-locator used a *looser* proxy (any detection within a generous band near the hoop, ignoring above-rim/aligned) to even locate these 5 windows at all, which implies the ball likely *was* detected somewhere in the vicinity but failed the strict geometric gate, not that detection was totally silent — or (b) the underlying detection-sparsity problem needs a real fix (#2 below). Which of (a) or (b) is true was **not** distinguished by this session's work and is now the single most valuable open question — see Section 4.
   - **Strongest case against, updated:** now stronger than originally written — this isn't just "thin evidence from one camera setup," it's a *validated negative result* on that one setup. Whether a windowed gate would help on different footage is still unknown, but on the only footage measured, it doesn't move the needle at all.

2. **TrackNet-style near-rim detection booster, invoked only as a fallback during a flagged shot window.**
   Addresses the root cause (raw detection sparsity) more directly than #1, but higher effort (must be built from the architecture idea since the reference repo is unlicensed; needs basketball-specific labeled data and training) and **medium confidence** — the mechanism is a good conceptual fit but was never validated against rim/net occlusion specifically, only tennis/badminton court occlusion. **Promoted in practical priority following #1's null result** — if the open question above resolves toward "raw detection is genuinely silent, not just failing the geometric gate," this becomes the most credible remaining fix.

3. **Audit the qualifying-test geometry itself** (`RimRegion.is_above` / `RimRegion.is_aligned`, and `align_tolerance_ratio=0.6`) **— newly surfaced by the sweep, not part of the original research pass.** Cheap to investigate (no model work, just re-running the existing diagnostics with the qualifying test's sub-conditions logged separately) and could turn out to be the real answer if the ball is being detected near the hoop but the alignment/above-rim thresholds are simply too strict for real shooting trajectories. See Section 4.

4. **Net-motion/pixel-disturbance signal as a secondary confirming feature**, layered on top of #1 once shots are actually being tracked — cheap, but doesn't rescue never-armed shots on its own, so it's a complement, not a fix, for the measured failure mode.

5. **Clip classification second opinion** — lowest priority; structurally can't fire for shots that never reach a timeout state (see Section 2), and its reference implementation is unlicensed besides.

6. **The bounce-up / `_passed_through` gating fix** (real bug, found by code read: `_update_armed`'s bounce-up check doesn't check whether the ball already validly crossed the inner gate before allowing a later noisy detection to overturn it to MISS) — keep on the list as a correct, trivial-risk fix, but it is **not** the cause of the reported symptom in this measured data (zero shots got far enough to be at risk of it). Fully designed and validated in `experiments/proposed_state_machine_patches.md`, including a traced consequence: once applied, `MISS_BOUNCE_UP` becomes structurally unreachable, not just rarer — worth knowing before applying it. Low priority, do eventually.

**"No new model needed" is not where this evidence points — and it's now a firmer conclusion than when this was first written.** The originally-proposed "boring" logic-gate fix was tested and, alone, does not solve the measured problem. That doesn't automatically mean a new model is required either — recommendation #3 (audit the qualifying-test thresholds) is just as "boring" and untested. The honest state is: the cheapest hypothesis was falsified, and the next-cheapest one hasn't been checked yet.

---

## Section 4: Do this next

**Single highest-value next step (revised after the sweep completed):** determine whether the 5 missing makes fail because the ball is genuinely never detected near the hoop, or because it *is* detected but fails the `is_above`/`is_aligned` qualifying test. This is now the pivotal open question — recommendation #1 turned out to be validated-but-insufficient specifically because this wasn't yet known. Concretely: instrument (or extend `experiments/arm_gate_sweep.py`, which already isolates the compound qualifying test) to log, per missing-shot window, three separate counts — (a) frames with any real ball detection at all, (b) of those, frames failing `is_above`, and (c) of those, frames failing `is_aligned`. If (a) is near-zero, this is a genuine raw-detection problem and recommendation #2 (TrackNet-style booster) is the right next investment. If (a) is meaningfully nonzero but (b) or (c) dominate, recommendation #3 (audit/loosen the qualifying-test thresholds — cheap, no model work) is very likely the actual fix, and should be tried before any model investment. The best-effort window-locator in `experiments/arm_gate_sweep.py` used a looser near-hoop proxy to find these windows at all, which is a hint (not proof) toward the latter.

**Footage to film to validate generalization** (directly addresses the strengthened strongest-case-against #1): at least one new clip corpus from a **different camera angle and/or distance** than the existing `chonyy_*` clips, ideally 10+ confirmed makes across 3+ distinct camera setups/gyms, to check whether this project's specific failure pattern — zero qualifying frames, not just sparse ones, during a make's approach — holds beyond this one recording, or was specific to this camera's geometry. This matters more now than when originally written: the sweep's null result was measured on the same two source recordings the original diagnosis came from, so it's not yet known whether either recommendation #1's insufficiency or the underlying sparsity itself generalizes.

---

## Adversarial self-review

- **Checked:** did the ranking favor the intellectually interesting fix (TrackNet) over the boring one (gate logic change)? No — the boring fix is ranked first specifically because it's what the measured data supports; TrackNet is ranked second specifically because its own research surfaced it as unvalidated for this exact occlusion pattern.
- **Flagged as unverified-not-fact:** TrackNet's fine-tuning cost (labeled-frame count, training hours) is inferred from its hyperparameters/architecture, not documented anywhere; the clip-classifier's "few hundred to ~1000 labeled clips" estimate is reasoned by analogy to its own training set, not verified against an actual second-opinion implementation.
- **Flagged as assumed-not-checked:** the clean 1:1 correlation between "missing shots" and "expected makes" rests on filename ground truth plus a partial manual spot-check of 2 of 6 resolved traces, not a full frame-by-frame human review of all 11 shots. The two-source-recording sample size is a real limitation, stated prominently rather than buried in a footnote.
