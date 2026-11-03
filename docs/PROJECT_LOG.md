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
- **Next:** 9 more sample clips (68 candidate shot windows) are awaiting user labels on a labeling page; then an evaluate → fix loop until every labeled clip is exact with 0 false makes.

---

## Tools used

- Python 3.12
- `ultralytics` (YOLO) for ball + hoop detection
- Per-frame YOLO detection + nearest-neighbour ball association (ByteTrack removed 2026-11-03)
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
