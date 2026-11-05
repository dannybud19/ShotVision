# ShotVision Project Log

> This file is updated at the end of every work session — see the most recent dated entry under "What's been done" for current status.

## What's been done

**Phase 1 pipeline (foundational build):** Core capture/detection/tracking/shot_logic/stats/overlay modules built out, establishing the end-to-end pipeline: video capture → YOLO ball+hoop detection → ByteTrack-based tracking → shot-logic state machine → stats aggregation → overlay rendering.

- YOLO ball+hoop detection wired into the pipeline.
- ByteTrack-based tracking added for consistent ball identity across frames (`bytetrack.yaml`).
- Detection threshold tuning performed via `scripts/tune_detection.py`, settling on `imgsz=960`, `conf=0.15` for ball detection, and `rim_conf=0.60` for hoop detection.
- `scripts/tune_detection.py` extended to also measure hoop detection alongside ball detection, not just ball-only.
- `RimTracker` added: automatic rim tracking derived from hoop detections, removing the need for manual calibration.
- `RimTracker` wired into `main.py`, and manual calibration removed entirely from the pipeline.
- `scripts/diagnose_shots.py` wired to `RimTracker` — no calibration file needed, added as a headless per-shot diagnostic tool.
- README updated to reflect the automatic rim tracking pipeline.

Recent commit history (`git log --oneline`), most recent first:

```
9c682a1 Update README for automatic rim tracking
84d34a3 Wire diagnose_shots.py to RimTracker, no calibration file needed
e68ecfd Extend tune_detection.py to measure hoop alongside ball detection
cd4c8e1 Wire RimTracker into main.py, remove manual calibration entirely
b28fce2 Add RimTracker: automatic rim tracking from hoop detections
```


### 2026-07-24 — Missed-makes investigation: measurement + external research

- Measured (via `scripts/diagnose_shots.py`) that real makes are being **dropped**, not misclassified: of 11 real shot attempts across 3 ground-truth-labeled clips, only 6 ever produced a `ShotResult`; the other 5 never armed the state machine at all, and that count of 5 matches the count of expected makes exactly in every clip.
- Extended `scripts/diagnose_shots.py` with "never-armed candidate episode" detection to make this failure mode directly measurable instead of inferred.
- Researched 6 external repos/architectures (TrackNet, two basketball-specific classifiers, two basketball shot-trajectory detectors, one MIT-licensed highlight-extraction tool) plus the "net-motion/pixel-disturbance" idea from patent literature, evaluating license status and relevance to the measured failure mode.
- Wrote `docs/tracking-research.md` with the full measured diagnosis, per-repo findings, and ranked recommendations — top recommendation is a state-machine arm-gate redesign (not a new model), with a TrackNet-style detection booster and a net-motion secondary signal ranked below it.
- Built an `experiments/` arm-gate sweep validator to quantify, from already-captured trace data, how many of the 5 missing makes different window/threshold parameters would rescue — validation results in progress, see `experiments/`.

### 2026-08-12 — Applied in-band arming fix + bounce-up fix, real-pipeline validation surfaces a second bug

- Applied Patch 2 (in-band arming: `self.rim.is_above(y)` → `not self.rim.is_below(y)` in `_update_idle`) and Patch 3 (bounce-up gating: `_update_armed`'s bounce-up check now also requires `not self._passed_through`) to `shotvision/shot_logic/state_machine.py`, per `experiments/proposed_state_machine_patches.md`. Added 3 new tests for Patch 2 and updated 2 existing bounce-up tests for Patch 3's changed behavior (their trajectories now resolve MAKE, not MISS, matching the traced consequence that `MISS_BOUNCE_UP` becomes structurally unreachable). Full suite: 101/101 passing (98 pre-existing + 3 new).
- Re-ran `scripts/diagnose_shots.py` against all 3 ground-truth clips with the real pipeline (not the offline simulation). **Arming is fully fixed**: 11 of 11 real attempts now produce a `ShotResult`, up from 6 of 11, with the original 6 shots' outcomes/reasons unchanged (no regression). **But all 11 now resolve as MISS** — the 5 newly-armed shots all resolve via `MISS_BELOW_WITHOUT_INNER` (`entered_inner=False`), when ground truth expects 5 of the 11 to be makes.
- Diagnosed why (verified against `rim.py`, not inferred): `rim.rim_y` is the midline of the outer band; Patch 2 allows arming from anywhere in-band, not just the top. With ~20% per-frame detection and a 2-consecutive-frame arm requirement, the points seeded into `_recent` at arming are often already at/past `rim_y`, so `_update_armed`'s crossing check (`prev.y < rim.rim_y <= y`) never has a valid "before the line" point to start from — `_passed_through` can never become `True` for these shots. This is a genuinely new bug the offline `simulate_inband_arms` validation could not have caught, since it only checked arming, not downstream scoring.
- Documented in `docs/tracking-research.md` (Update 3, Section 3, and revised Section 4 "do this next"). Not yet fixed — needs a fresh measure-before-fix pass on the crossing-detection logic, same discipline as the rest of this investigation. Changes committed (tests pass, no regression) but the missing-makes problem is not resolved end-to-end.

**Addition, same day — arm-gate sweep completed:** `experiments/arm_gate_sweep.py` ran the real detection/tracking/rim-tracking pipeline over the 3 ground-truth clips, replicated today's `_update_idle` pre-arm logic locally (validated: reproduces the known 0/5 rescued), and swept a windowed (gap-tolerant) variant across N∈{2,3} × W∈{4,6,8,10,15}. Result: **0 of 5 missing makes rescued at every (N, W) tested**, with **0 spurious extra arm events** anywhere in the 3 clips at every setting. This was cross-checked (not a sweep bug) two ways: the baseline replication correctly reproduces 0/5, and a direct count of raw qualifying frames (detected + above-rim + aligned, before descent/consecutiveness) inside each of the 5 best-effort missing-shot windows came back exactly 0 in all 5 cases — a fresh, independent re-run of `scripts/diagnose_shots.py`'s never-armed-episode detector against all 3 clips this session also found 0 episodes beyond the 6 already-resolved shots in every clip, confirming these 5 misses have literally zero above-rim+aligned detections anywhere, not merely a broken streak. **Conclusion: the windowed arm-gate change (research doc's top recommendation) is still low-risk and worth keeping on the roadmap, but it would NOT by itself have rescued any of the 5 measured missing makes — it needs to be paired with either a looser above-rim/aligned test or a real detection-sparsity fix (recommendation #2, TrackNet-style) to address what was actually measured.** Wrote up both this windowed-gate patch and the previously-designed (and, this session, code-flow-verified) bounce-up gating fix as unapplied, ready-to-review proposals in `experiments/proposed_state_machine_patches.md`, including a discovery that the bounce-up fix makes `ResolutionReason.MISS_BOUNCE_UP` structurally unreachable going forward (traced through `_update_armed`'s control flow, not just asserted). Added `tests/test_arm_gate_sweep.py` (3 tests, passing) covering the sweep's own windowed-gate simulation in isolation. Full suite: 98/98 passing (95 pre-existing + 3 new). No files under `shotvision/` were modified — `experiments/arm_gate_sweep.py`, `experiments/proposed_state_machine_patches.md`, and `tests/test_arm_gate_sweep.py` are new files only.

### 2026-11-03 — Root cause found: ByteTrack was dropping the ball; tracker replaced, evaluation harness added

- **Root cause of every "missing make":** `BallTracker` used `model.track()` (ByteTrack). Raw `predict()` detects the ball above the rim at conf 0.79-0.88 for ~12 straight frames per make, but ByteTrack's IoU association never confirms a track for a ball moving ~12-15 px/frame on a ~23 px box, so `track()` output nothing until the ball slowed down in the net. The "~20% detection rate", "makes are never seen above the rim", the arming failure and the 2026-08-12 scoring bug were all downstream of this.
- **Fix (branch `fix/ball-tracking`):** `BallTracker` now runs `predict()` and links the ball by nearest neighbour, with a jump gate scaled by ball width × frames elapsed (`tracker.max_jump_ball_widths`, `tracker.max_gap_frames`). Ball coverage on the chonyy clips went from ~20% to ~75% of frames.
- **Reverted in-band arming (Patch 2):** with the ball visible above the rim, the original stricter above-rim arming scores identically. Removed the unreachable `MISS_BOUNCE_UP` exit.
- **Measured:** the hoop box from this checkpoint spans rim + net (y 174-212 on the chonyy camera, rim ring at ~175-182), so `rim.rim_y` sits mid-net. Not currently causing errors; candidate cleanup.
- **New `scripts/evaluate.py`:** scores the pipeline against `sample_clips/labels.json` (per-shot outcomes, false makes, spurious shots, and ball-coverage smoothness on makes), with cached detections so logic changes replay in seconds. **New `scripts/render_overlay.py`:** headless HUD video for visual review.
- **Result:** chonyy clips (labeled from viewed frames) score 11/11 shots correct, 0 false makes, make-window ball coverage 90-96% with gaps of at most 2 frames.
- **External research** (11 open-source shot trackers, read in code): avishah3, whose checkpoint we use, runs plain per-frame detection with no tracker; abdullahtarek deliberately avoids ByteTrack for the ball. JadenS180 (MIT) reports 28/29 shots with 0 false makes using a ~0.25 s make-confirmation hold, size and steepness vetoes that can only turn makes into misses, and a stationary-false-positive filter. These are queued as loop candidates.
- **Labels:** the user labeled 68 candidate shot windows across 8 more clips on a labeling page (59 makes, 4 misses, 5 not-a-shot; kyle_validation_video dropped at the user's request). Two video_test_5 cards were one shot and were merged. The new tracker found 2 lf_back makes that had no card; both were confirmed by frame review and added, marked as such. Total: 11 clips, 75 shots (65 makes, 10 misses).
- **Evaluate → fix loop** (agreed stop rule: every clip exact, 0 false makes, smoothness passing; cap ~8 iterations). Every iteration kept 0 false makes:

  | Iter | Change | Correct |
  |---|---|---|
  | 0 | baseline (ByteTrack fix) | 52/75 |
  | 1 | velocity-gated association, stationary-object filter (a round "1" sign was detected as a ball 219 times), guarded track switching | 56/75 |
  | 2 | no track switching during the 2-4 frame blur gap at the rim (a shooter's head, conf up to 0.69, was taking over) | 58/75 |
  | 3-4 | gate sized by the followed ball; 24-frame occlusion grace when last seen at the hoop (ball hidden in the net 11-19 frames); arming survives one missed frame; align tolerance 0.6 → 1.0 | 66/75 |
  | 5 | weak (0.03-0.15) boxes continue a followed ball through the net; never arm/cross/resolve | 66/75 (make coverage 70% → 75%) |
  | 6 | track identity (a shot only scores the ball it armed on); strength = best recent conf; velocity over gaps up to 8 frames; gate around last position too | 67/75 |
  | 7 | scoring line at 0.4 of the hoop box (box spans rim + net; midline is mid-net) | **68/75** |

  A subagent measured detection variants on the 12 hardest windows: imgsz 1280 and a hoop-ROI crop each *added* false makes; low conf helped only as continuation.
- **Stopped at iteration 7, stop rule not met.** 5/11 clips pass outright. Of the 7 remaining failures, 6 are makes the detector cannot see (dark ball motion-blurred over the backboard or below the net, ball out of frame, a huge blurred ball on kyle_test_video) at any setting tried. The 7th (lf_shot_detection f600) would need a more make-favourable rule across a 14-frame gap, which 10 labeled misses can't show is safe. Smoothness: average make-window coverage 76%, average longest gap 5.7 frames, but 23 of 65 make windows still fail the strict check (gap ≤ 6 frames, coverage ≥ 60%), almost all because of the net/blur gap.
- **Next:** (1) film and label misses from the target camera (rim-outs, in-and-outs, airballs) so false-make safety is actually measured; (2) fine-tune the detector on motion-blurred ball frames from that camera (scripts/finetune_roboflow.py); (3) re-run scripts/evaluate.py after each.

### 2026-11-04 — Session recovery: measured diagnosis, roadmap rewrite, CLAUDE.md

- Rebuilt context after a lost session. The user's recovery summary was out of date. ByteTrack had already been replaced and PR #1 merged; the score was 68/75 with 0 false makes; detection coverage was ~76% in make windows, not 11%; there were 111 passing tests, not 76.
- New `experiments/shot_diagnostics.py`. It replays cached detections (`--cache-only` never loads the .pt) and reports each shot's exit path, its last confirmed positions in rim units, the gaps, and which layer lost each failure.
- **Measured:** 0 shots resolve by timeout. Of the 7 failed makes, 4 never arm, 2 end through the occlusion grace and 1 resolves sideways. 6 of the 7 involve the ball being invisible for 7-25 frames at the rim. All 10 labeled misses resolve with the ball in view. The vt5 "spurious" MISS at f3156 is the f3104 make resolving 27 frames after its label window.
- **Threshold sweeps:** align tolerance, descent frames, prearm gap and occlusion grace each trade one make for another (best 69/75). Inner shrink 0.15 → 0.05 gives 2 false makes.
- **`experiments/track_adopt_experiment.py`:** adopting a new track id at the hoop gives 69/75 with 0 false makes. It fired once, on vt5 f2597. Queued, not applied.
- **Research** (3 subagents, licenses checked) on WASB/TrackNet, clip classifiers, trajectory fits, net motion, products and patents.
- Rewrote `docs/tracking-research.md` and `docs/ROADMAP.md`, and added `CLAUDE.md`. The user wants make/miss to work from any angle where hoop, ball and person are visible; the roadmap records the single-camera depth limits that come with that.
- **Next:** film our own camera at 60 fps with a fast shutter (shot list in the research doc, "Do this next"), and measure with the logic unchanged.

### 2026-11-04 (later) — Phase 1 stage on public footage: items 1-3 done, 4-5 pending

- **In-and-out:** a ball back above the rim after crossing inside it now resolves as `MISS_IN_AND_OUT`. Before and after: 58/65 makes counted, 0 false makes. The exit never fired on the existing clips.
- **`scripts/label_candidates.py`:** one command turns a clip into a labeling page, and `merge` writes the results into labels.json. Recall: every labeled shot got a card on the 6 clips checked.
- **Frame-rate independence:** all thresholds are now in seconds or per second. The evaluate output is byte-identical on every 30 and 29.97 fps clip. lf_alan (24 fps) changed only in coverage, by 1%.
- **`evaluate.py --report`** prints Gate A. labels.json now has split, source, duplicate and miss_type fields. On the distinct legacy set: 56/63 makes counted (88.9%), 0/8 false makes, 95% upper bound 31%. **Gate A FAIL** on make rate.
- **ROADMAP:** release-moment detection and shooter position moved from Phase 3 into Phase 2.
- **Not done (usage limit):** item 4 (licensed public misses: a search agent was started and then stopped) and item 5 (Gate A on the bigger set).

### 2026-11-05 — Items 4-5: public miss set and Gate A (FAIL)

- **Public footage:** searched Wikimedia Commons and the Internet Archive.
  - Kept a full high-school game (Hardwick Community TV, CC BY 4.0, 1080p60, panning sideline camera) and two Vancouver Bandits practice clips (CC BY 3.0, 720p60).
  - Rejected 4 clips as unusable, and skipped archive.org "CC BY" NBA re-uploads as license-dubious.
  - Provenance is in `sample_clips/SOURCES.md`.
- **Labeling tool:** 3 s cards sampled every 0.1 s, plus an IGNORE ("can't tell") outcome. evaluate.py now allows 1 s after a labeled window, since the pipeline resolves up to ~1 s after the ball leaves the net. Legacy results are unchanged.
- **Labels:** made by Claude subagents from contact sheets (Opus for Bandits, Sonnet for the game, to save tokens). Claude checked every make disagreement and relabeled one card as MISS (the scoreboard didn't change). Not human-verified.
- **Gate A: FAIL.**
  - 90/137 makes counted.
  - 2 false makes in 46 distinct misses, both the tracker following a non-ball object under a moving camera.
  - 41 lost makes never armed; 24 of those are tracker losses (it stays locked on a resting or second ball).
- **No pipeline changes were made** for this (stage rule). The recommended next step is shot-centric ball selection.
- **Not done:** Bandits 03 (98 cards) is unlabeled; 46 misses is short of the 50 target.

---

## Tools used

- Python 3.12
- `ultralytics` (YOLO) for ball + hoop detection
- Per-frame YOLO detection + gated nearest-neighbour ball association (ByteTrack removed 2026-11-03)
- `scripts/evaluate.py` + `sample_clips/labels.json` as the regression scoreboard
- OpenCV for video I/O and frame processing
- PyTorch on MPS (Apple Silicon) for inference
- `certifi` (SSL workaround, needed for model/weight downloads on macOS)
- `pytest` for testing

Roboflow is referenced as the intended path for a future licensed/custom dataset (see `scripts/finetune_roboflow.py`) but is **not yet in use**.

---

## Model / training status

**No in-house training has happened yet.** State this accurately — do not overclaim.

- `models/basketball_best.pt` is a community YOLOv8 ball+hoop fine-tune pulled directly from `avishah3/AI-Basketball-Shot-Detection-Tracker`. License unspecified upstream — local prototyping only, not for redistribution.
- `scripts/finetune_roboflow.py` is a ready-but-never-run follow-up script for fine-tuning on a properly licensed (e.g. CC BY 4.0) Roboflow dataset.

**Instruction to future self:** update this section the day real training is actually run, with dataset size/source and resulting metrics. Until then, this section should continue to say "no in-house training yet."
