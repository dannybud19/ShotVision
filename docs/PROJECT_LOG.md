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

*(Note: full `git log --oneline -20` output was not retrievable this session due to a sandbox permission restriction on shell access to the repo directory; the above reflects the most recent commits visible in this session's git status snapshot. Update this list with the fuller history next time shell access is available.)*

### 2026-07-24 — Missed-makes investigation: measurement + external research

- Measured (via `scripts/diagnose_shots.py`) that real makes are being **dropped**, not misclassified: of 11 real shot attempts across 3 ground-truth-labeled clips, only 6 ever produced a `ShotResult`; the other 5 never armed the state machine at all, and that count of 5 matches the count of expected makes exactly in every clip.
- Extended `scripts/diagnose_shots.py` with "never-armed candidate episode" detection to make this failure mode directly measurable instead of inferred.
- Researched 6 external repos/architectures (TrackNet, two basketball-specific classifiers, two basketball shot-trajectory detectors, one MIT-licensed highlight-extraction tool) plus the "net-motion/pixel-disturbance" idea from patent literature, evaluating license status and relevance to the measured failure mode.
- Wrote `docs/tracking-research.md` with the full measured diagnosis, per-repo findings, and ranked recommendations — top recommendation is a state-machine arm-gate redesign (not a new model), with a TrackNet-style detection booster and a net-motion secondary signal ranked below it.
- Built an `experiments/` arm-gate sweep validator to quantify, from already-captured trace data, how many of the 5 missing makes different window/threshold parameters would rescue — validation results in progress, see `experiments/`.

**Addition, same day — arm-gate sweep completed:** `experiments/arm_gate_sweep.py` ran the real detection/tracking/rim-tracking pipeline over the 3 ground-truth clips, replicated today's `_update_idle` pre-arm logic locally (validated: reproduces the known 0/5 rescued), and swept a windowed (gap-tolerant) variant across N∈{2,3} × W∈{4,6,8,10,15}. Result: **0 of 5 missing makes rescued at every (N, W) tested**, with **0 spurious extra arm events** anywhere in the 3 clips at every setting. This was cross-checked (not a sweep bug) two ways: the baseline replication correctly reproduces 0/5, and a direct count of raw qualifying frames (detected + above-rim + aligned, before descent/consecutiveness) inside each of the 5 best-effort missing-shot windows came back exactly 0 in all 5 cases — a fresh, independent re-run of `scripts/diagnose_shots.py`'s never-armed-episode detector against all 3 clips this session also found 0 episodes beyond the 6 already-resolved shots in every clip, confirming these 5 misses have literally zero above-rim+aligned detections anywhere, not merely a broken streak. **Conclusion: the windowed arm-gate change (research doc's top recommendation) is still low-risk and worth keeping on the roadmap, but it would NOT by itself have rescued any of the 5 measured missing makes — it needs to be paired with either a looser above-rim/aligned test or a real detection-sparsity fix (recommendation #2, TrackNet-style) to address what was actually measured.** Wrote up both this windowed-gate patch and the previously-designed (and, this session, code-flow-verified) bounce-up gating fix as unapplied, ready-to-review proposals in `experiments/proposed_state_machine_patches.md`, including a discovery that the bounce-up fix makes `ResolutionReason.MISS_BOUNCE_UP` structurally unreachable going forward (traced through `_update_armed`'s control flow, not just asserted). Added `tests/test_arm_gate_sweep.py` (3 tests, passing) covering the sweep's own windowed-gate simulation in isolation. Full suite: 98/98 passing (95 pre-existing + 3 new). No files under `shotvision/` were modified — `experiments/arm_gate_sweep.py`, `experiments/proposed_state_machine_patches.md`, and `tests/test_arm_gate_sweep.py` are new files only.

---

## Tools used

- Python 3.12
- `ultralytics` (YOLO) for ball + hoop detection
- ByteTrack (`bytetrack.yaml`) for multi-object tracking
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
