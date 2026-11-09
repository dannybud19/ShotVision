# ShotVision: project brief

**Goal:** single-camera basketball analytics. Phase 1 is a make/miss counter for one shooter. Later phases add 2PT/3PT, shot type, multiple players and shot-selection analysis. Full plan: `docs/ROADMAP.md`. Rule: no phase starts until the previous one is reliable on our own footage.

**Current phase: Phase 1, make/miss. In-scope Gate A passes; out-of-scope footage is a stress test.** Branch `stage1/label-tooling`.
- **Gate A (in scope: fixed camera, single ball):** 21/22 makes counted (95.5%), 0 false makes in 6 misses. PASS. `scripts/evaluate.py --report` now splits by camera class, measured per clip by `experiments/camera_profile.py` and stored as `camera_class`/`ball_count` in `labels.json`.
- **Out of scope (stress test, no pass/fail):** 137/222 makes, 5 false makes in 79 misses. All 5 are spurious makes: 4 in the held-out Enosburg game, 1 in a Bandits practice. All clips, old definition: 158/244 (64.8%).
- **Tracker fix (5 Nov) is done:** shot-centric ball selection took the dev set from 90 to 107/137 makes and 2 to 0 false makes; with Bandits 03: 132/193, 0/57 labeled misses scored MAKE, 1 spurious make.
- **Next step:** Line-crossing side-by-side experiment (PLAN_2).
- Proposed, needs agreement: keep ShotVision's scoring; do not adopt the line-through-the-rim method (it adds false makes); next measure the in-scope split after PLAN_1's camera_class / ball_count labels land.
- **Labels:** the newer ones are Claude-made from contact sheets, not human-verified. Labeling pages: `python scripts/label_candidates.py <clip>`.
- **Legacy clips** (11 GitHub clips): 56/63 distinct makes, 0/8 false makes. Public footage: `sample_clips/public/`, provenance and licenses in `sample_clips/SOURCES.md`.
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
