# ShotVision: project brief

**Goal:** single-camera basketball analytics. Phase 1 is a make/miss counter for one shooter. Later phases add 2PT/3PT, shot type, multiple players and shot-selection analysis. Full plan: `docs/ROADMAP.md`. Rule: no phase starts until the previous one is reliable on our own footage.

**Current phase: Phase 1, make/miss. In-scope results look good (55/60 makes, 0 false makes) but rest on only 8 misses; out-of-scope footage is a stress test.** Branch `stage1/label-tooling`.
- **Gate A (in scope: fixed camera, single ball):** 55/60 makes counted (91.7%), 0 false makes in 8 misses. The in-scope gate needs at least 50 misses, so it reports NOT ENOUGH MISSES TO JUDGE (8 < 50). `scripts/evaluate.py --report` splits by camera class, measured per clip by `experiments/camera_profile.py` and stored as `camera_class`/`ball_count` in `labels.json`. The owner reviewed the 5 "moving" GitHub clips on 2026-11-12 and re-tagged 3 as fixed (`camera_class_source` records it).
- **Out of scope (stress test, no pass/fail):** 107/188 makes, 1 false make in 77 misses. The 1 is a spurious make in a Bandits practice. The 4 Enosburg spurious makes were confirmed real makes by the owner and labelled (PLAN_3 B3). All clips, old definition: 162/248 (65.3%), 0/85 labelled misses scored MAKE.
- **Tracker fix (5 Nov) is done:** shot-centric ball selection took the dev set from 90 to 107/137 makes and 2 to 0 false makes; with Bandits 03: 132/193, 0/57 labeled misses scored MAKE, 1 spurious make.
- **Next step:** get 50+ fixed-camera misses (licensed fixed-camera shooting footage or the owner's own filming, spec in HANDOVER.md section 12). Phase 2 groundwork (release moment) may start as experiments only.
- **Follow-up (not done):** device sources (webcam) report 15 fps but delivered about 29 fps in the 2026-11-12 live check. Shot-logic timings use the reported fps, so live windows would be about half as long as intended. Measure the real frame rate on device sources instead of trusting `CAP_PROP_FPS`.
- Proposed, needs agreement: keep ShotVision's scoring; do not adopt the line-through-the-rim method (it adds false makes); next measure the in-scope split after PLAN_1's camera_class / ball_count labels land.
- **Labels:** the newer ones are Claude-made from contact sheets, not human-verified. Labeling pages: `python scripts/label_candidates.py <clip>`.
- **Legacy clips** (11 GitHub clips): 56/63 distinct makes, 0/8 false makes. Public footage: `sample_clips/public/`, provenance and licenses in `sample_clips/SOURCES.md`.
- **History:** `docs/PROJECT_LOG.md`, with an entry per session.

**Pipeline** (`shotvision/`): capture → YOLO ball/hoop detection (`detection/`) → `tracking/ball_tracker.py` → `shot_logic/` (`rim_tracker.py`, `state_machine.py`) → `stats/` → `overlay/`. Entry point: `python -m shotvision.main --source <file|0>`. Config: `shotvision/config/default.json`; all durations are in seconds (converted to frames with each source's fps; tuned at 30 fps).
- **Gated nearest-neighbour association, not ByteTrack.** ByteTrack dropped the fast ball and was removed on 2026-11-03.
- **MAKE requires a fitted crossing inside the inner rim gate, then the whole ball seen below.** Everything else resolves MISS.

**Hardware:** Apple Silicon M2 Pro, PyTorch on MPS. **No CUDA.** Flag any CUDA-only dependency.

**Tests:**
- `.venv/bin/python -m pytest -q` runs 167 tests. Two of them load `models/basketball_best.pt` (`test_detector_loads_real_basketball_checkpoint_and_predicts`, `test_update_runs_end_to_end_on_blank_frame`).
- To skip the model, add `--deselect tests/test_detector.py::test_detector_loads_real_basketball_checkpoint_and_predicts --deselect tests/test_ball_tracker.py::test_update_runs_end_to_end_on_blank_frame`. That leaves 165, all passing (0 skipped, ffmpeg installed) on 2026-11-12.

**Measuring:**
- `scripts/evaluate.py [-v] [--set key=value]` is the scoreboard. It replays cached detections from `experiments/.cache/detections`.
- `experiments/shot_diagnostics.py --cache-only` prints the per-shot exit path, the positions before resolution, the gaps, and which layer lost each failure.
- Re-run both after any change, and keep a change only if false makes stay at 0.

**Rules:**
- **Permission:** loading `models/basketball_best.pt` (a third-party pickle; it loads only on a cache miss) needs the user's approval in auto mode. Ask first.
- **Licenses:** the checkpoint has no clear license, and `ultralytics` is AGPL-3.0. Check every repo's license before using its code. No license means learn from it, don't copy it.
- **Experiments** go in `experiments/`. Don't refactor the tested pipeline without agreement.
- **Prefer missing a make to counting a false one.**
