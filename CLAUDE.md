# ShotVision: project brief

**Goal:** single-camera basketball analytics. Phase 1 is a make/miss counter for one shooter. Later phases add 2PT/3PT, shot type, multiple players and shot-selection analysis. Full plan: `docs/ROADMAP.md`. Rule: no phase starts until the previous one is reliable on our own footage.

**Current phase: Phase 1, make/miss (blocked).** Stage plan in progress on branch `stage1/label-tooling` (2026-11-04):
items 1-3 are done (in-and-out MISS, `scripts/label_candidates.py`, seconds-based thresholds); item 6 is partly done (ROADMAP updated).
Items 4-5 are NOT done: grow the miss set to at least 50 licensed public misses, label them, then run Gate A (`scripts/evaluate.py --report`).
The Gate A baseline on the distinct legacy set is 56/63 makes (88.9%, FAIL: needs 90%) with 0/8 false makes.
Public footage may be partly downloaded in `sample_clips/public/` (see SOURCES_public.md there, if it exists); check each file's license before using it.
- **Score:** 68/75 labeled shots correct, 0 false makes, on 11 third-party clips (`sample_clips/labels.json`). Only 8 of those shots are distinct misses.
- **Blocker, measured 2026-11-04:** all 7 failures are makes that weren't counted.
  - 6 involve the ball being invisible for 7-25 frames at the rim: blur over the backboard, or hidden in/below the net.
  - 4 never arm, 2 end through the occlusion grace, 1 is a net-deflected ball that looks sideways in 2D. 0 are timeouts.
  - Threshold tuning trades one make for another, and widening the inner gate creates false makes.
  - The next step is our own footage: 60 fps, fast shutter, ≥80 misses. Spec, diagnosis and ranked options: `docs/tracking-research.md`.
- **History:** `docs/PROJECT_LOG.md`, with an entry per session.

**Pipeline** (`shotvision/`): capture → YOLO ball/hoop detection (`detection/`) → `tracking/ball_tracker.py` → `shot_logic/` (`rim_tracker.py`, `state_machine.py`) → `stats/` → `overlay/`. Entry point: `python -m shotvision.main --source <file|0>`. Config: `shotvision/config/default.json`; all durations are in seconds (converted to frames with each source's fps; tuned at 30 fps).
- **Gated nearest-neighbour association, not ByteTrack.** ByteTrack dropped the fast ball and was removed on 2026-11-03.
- **MAKE requires a fitted crossing inside the inner rim gate, then the whole ball seen below.** Everything else resolves MISS.

**Hardware:** Apple Silicon M2 Pro, PyTorch on MPS. **No CUDA.** Flag any CUDA-only dependency.

**Tests:**
- `.venv/bin/python -m pytest -q` runs 126 tests. Two of them load `models/basketball_best.pt` (`test_detector_loads_real_basketball_checkpoint_and_predicts`, `test_update_runs_end_to_end_on_blank_frame`).
- To skip the model, add `--deselect tests/test_detector.py::test_detector_loads_real_basketball_checkpoint_and_predicts --deselect tests/test_ball_tracker.py::test_update_runs_end_to_end_on_blank_frame`. That leaves 124, all passing on 2026-11-04.

**Measuring:**
- `scripts/evaluate.py [-v] [--set key=value]` is the scoreboard. It replays cached detections from `experiments/.cache/detections`.
- `experiments/shot_diagnostics.py --cache-only` prints the per-shot exit path, the positions before resolution, the gaps, and which layer lost each failure.
- Re-run both after any change, and keep a change only if false makes stay at 0.

**Rules:**
- **Permission:** loading `models/basketball_best.pt` (a third-party pickle; it loads only on a cache miss) needs the user's approval in auto mode. Ask first.
- **Licenses:** the checkpoint has no clear license, and `ultralytics` is AGPL-3.0. Check every repo's license before using its code. No license means learn from it, don't copy it.
- **Experiments** go in `experiments/`. Don't refactor the tested pipeline without agreement.
- **Prefer missing a make to counting a false one.**
