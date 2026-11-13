# Run log: PLAN_4 (2026-11-13)

Plan: `docs/plans/PLAN_4_tidy_and_still_shots.md`. Branch `stage1/label-tooling`, main repo folder.

Owner answers before the start:
- `HANDOVER.md` replaced with the ShotVision handover (first line `# ShotVision: Handover`, checked).
- Step 6: replace the stale "Follow-up (not done)" device fps bullet in `CLAUDE.md` with the new "Live sources" bullet.
- The two untracked files are committed before this log is created.
- `config.model.rim_conf` is 0.6 (`shotvision/config/default.json` line 13). Checked, no stop needed.

## Step 1: Pre-flight

Commands: `git checkout stage1/label-tooling`, `git pull --ff-only`, `git status --short`, `git log --oneline -3`, test command, `scripts/evaluate.py --report`.

- Expected: latest commit c2e1916 or later; only `HANDOVER.md` and PLAN_4 untracked | Got: HEAD c2e1916, `?? HANDOVER.md`, `?? docs/plans/PLAN_4_tidy_and_still_shots.md`; pull already up to date | Match: yes
- 1.1 commit: `f85ff61 Plans: PLAN_4 (tidy-up, live frame rate, still-camera shot count) and HANDOVER.md`
- Expected: `165 passed, 2 deselected` | Got: `165 passed, 2 deselected in 1.57s` | Match: yes (BASE_TESTS = 165)
- Expected: makes counted `162/248 (65.3%)` | Got: `162/248 (65.3%)` | Match: yes
- Expected: `0/85 labeled misses, + 1 spurious makes` | Got: `0/85 labeled misses, + 1 spurious makes` | Match: yes
- Expected: `fixed/single` `55/60    91.7%    0/8`, 95% UB `31.2%` | Got: `55/60    91.7%    0/8      31.2%` | Match: yes
- Expected: `NOT ENOUGH MISSES TO JUDGE (8 < 50)` | Got: same | Match: yes
- Expected: `makes 107/188, false makes 1/77` | Got: `makes 107/188, false makes 1/77` | Match: yes
- Expected: exit code 1 | Got: `exit=1` | Match: yes
- No Ultralytics/torch output in the baseline report (grep count 0).

Files changed: `HANDOVER.md` and `docs/plans/PLAN_4_tidy_and_still_shots.md` (committed, f85ff61). Created (gitignored) `experiments/results/plan4_gate_a_before.txt`.

## Step 2: Report crash when a lost make has no reason

Commands: edit `scripts/evaluate.py` (the one `reasons["make lost: " ...]` line became the three-way `if`, indentation kept); append `test_lost_make_without_reason_does_not_crash` to `tests/test_gate_report.py` (existing `_lost_make()` helper left untouched); `evaluate.py --report > plan4_gate_a_after_2.txt`; diff; test command.

- Expected: `identical` | Got: `identical` | Match: yes
- Expected: `BASE_TESTS + 1` = 166 passed | Got: `166 passed, 2 deselected` | Match: yes

Files changed: `scripts/evaluate.py`, `tests/test_gate_report.py`.

## Step 3: Replace the test-only guard in `FrameSource`

3.1 Read first. Both match the plan's description.
- `shotvision/capture/source.py` line 52, before: `if self.type != DEVICE and hasattr(cv2, "CAP_PROP_ORIENTATION_AUTO") and hasattr(self._cap, "set"):` followed by `self._cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1)`.
- `tests/test_source.py` `FakeCap` (inside `test_source_key_distinguishes_device_and_url`): methods `isOpened`, `get`, `release`; no `set`.

3.2 Change: removed only `and hasattr(self._cap, "set")` from the condition; added `set(self, prop, value): return True` to `FakeCap`.

- Expected: `BASE_TESTS + 1` = 166 passed | Got: `166 passed, 2 deselected` | Match: yes

Files changed: `shotvision/capture/source.py`, `tests/test_source.py`.

## Step 4: Measure a live camera's real frame rate

- 4.1 `shotvision/capture/source.py`: added `import time` and `FrameSource.measure_fps` (verbatim from the plan), after the `fps` property.
- 4.2 `shotvision/main.py`: replaced the `fps = config.camera.fps or source.fps` line and its print with the plan's block. Nothing else changed.
- 4.3 `experiments/live_check.py` `run_live`: same block (the function had no "Timing at" print, so I added it with the same text as `main.py`). The structure fitted, so no restructuring was needed. `source_fps = source.fps` became `reported_fps = source.fps`. Summary dict: `"source_fps": fps` (the value used), new `"reported_fps": reported_fps`. `real_time` now compares processing fps with `fps` (the value used). `print_summary` prints `(reported X)` after `source fps: ...` only when the two differ by more than 0.5. `compare_to_replay` already read `fps_used_for_timing`, so it is unaffected. `py_compile` passes on all three files. Nothing was run.
- 4.4 Tests added to `tests/test_source.py`: `test_measure_fps_uses_delivered_rate`, `test_measure_fps_falls_back_when_no_frames`.
- `tests/test_main.py` only tests `build_cli_overrides`. `run()` opens a window and loads the detector, so there is no practical way to test the new branch without a camera or the model. No `main.py` test added (as the plan allows).

Ambiguity and choice: the plan says the fake clock "advances by 1/30 s on every call". Read literally, `measure_fps(seconds=1.0)` returns 28.125 (the loop's own `clock()` calls inflate the elapsed time: 29 frames over 31 ticks), which fails the plan's own "within 1.0 of 30". I checked this with a scratch script. I made the fake clock advance by 1/30 s on every frame read instead (a camera delivering 30 fps), which returns 30.0. Test-only choice. It changes no result.

- Expected: evaluation identical to step 2's output | Got: `identical` | Match: yes
- Expected: all tests pass, record the count | Got: `168 passed, 2 deselected` | Match: yes (166 + 2 new)

Files changed: `shotvision/capture/source.py`, `shotvision/main.py`, `experiments/live_check.py`, `tests/test_source.py`. The live check was not run.

## Step 5: Count labelled shots taken while the camera was still (report only)

- 5.1 New `experiments/shot_camera_stillness.py`. It imports `hoop_metrics` from `experiments/camera_profile.py` unchanged (it takes any detection list, so it works on a window slice). `evaluate` is imported lazily, as `camera_profile.py` does. Window `[start - to_frames(1.0), end + to_frames(0.5)]`, end inclusive, clamped. Thresholds `hoop_seen >= 0.8`, `move_p95 < 0.5`, `size_ratio < 1.3`. Hoop confidence is `config.model.rim_conf`, which is 0.6 (checked before the run, as agreed). Scoring uses `replay` then `score_clip` with `min_coverage=0.6` and `to_frames(0.2, fps)`, the defaults `evaluate.py` `main` passes. Clip set is `load_labels(split="all", include_duplicates=False)`, the same as `--report`. The "8" in the headline is computed (the `fixed/single` miss total), not hard-coded.
- 5.2 New `tests/test_shot_camera_stillness.py`: fixed hoop is still, hoop moving one width every other frame is not still, hoop seen in half the window is not still, plus one test of the window clamping.
- 5.3 Command: `.venv/bin/python experiments/shot_camera_stillness.py --out experiments/results/shot_camera_stillness.md --json experiments/results/shot_camera_stillness.json`. Exit 0. No Ultralytics/torch/loading output (grep count 0). Every clip was already in the detection cache, so no model load was possible.

- Expected: Table A total makes 248 | Got: 248 (119 still) | Match: yes
- Expected: Table A total misses 85 | Got: 85 (30 still) | Match: yes
- Expected (extra, from the scoreboard): makes counted 162/248, labelled misses scored MAKE 0/85, spurious makes 1 | Got: `162/248`, `0/85`, `1` | Match: yes
- Report only (plan: do not change thresholds): fixed/single shots that are not still: 6/68. By clip: aggie_NathanBBall.mov 1/6, artur_vid29.mp4 1/4, video_test_5.mp4 4/30.
- Headline: `Still-camera misses outside fixed/single clips: 22 (false makes: 0)`; `If counted in scope: in-scope misses would be 8 + 22 = 30`.
- Observation (not a result of the plan): of the 22 outside misses, 13 are in moving/multi clips (Bandits practices, multi-ball) and 9 are in moving/single clips (the two Hardwick games). Phase 1 scope is a single ball.
- Tests: expected all pass | Got: `172 passed, 2 deselected` (168 + 4 new) | Match: yes

Files changed: new `experiments/shot_camera_stillness.py`, new `tests/test_shot_camera_stillness.py`, new `experiments/results/shot_camera_stillness.md` (the `.json` is gitignored).

## Step 6: HANDOVER.md and stale docs

- `HANDOVER.md` section 3: updated the branch row (PLAN_3 done at `c2e1916`, PLAN_4 steps 1 to 5 `f85ff61` to `d9b7a1c` plus the docs commit) and the tests row (165 to 172). The scoreboard numbers did not change. Section 10: added one sub-line under item 3 with the step 5 headline and the 9 (Hardwick) / 13 (Bandits) split. Nothing else touched. Section 10 items 1 and 2 ("Run PLAN_4", "Rerun the webcam live check after PLAN_4") are now partly stale; the plan says nothing else changes, so I left them.
- `CLAUDE.md`: replaced the "Proposed, needs agreement" bullet with the plan's text (N = 22). Per the owner's instruction in this session, removed the stale "Follow-up (not done)" device-fps bullet and added the plan's "Live sources" bullet under the pipeline section. Test count: 167 to 174 total, 165 to 172 with the two model tests deselected, dated 2026-11-13. The "Next step" pointer to HANDOVER.md section 12 is unchanged (section 12 exists: "Filming plan").
- `docs/PROJECT_LOG.md`: new entry `### 2026-11-13: PLAN_4: ...` above `## Tools used` (the plan's heading format, with a colon; older entries use an em dash, which the docs style forbids).
- `docs/tracking-research.md`: new `### 0f` after `0e`, Tables A to C and the headline lines pasted from `experiments/results/shot_camera_stillness.md`. No recommendation beyond "owner decides".
- Added-lines check: 0 em dashes.

- Expected: tests pass | Got: `172 passed, 2 deselected` | Match: yes

Files changed: `HANDOVER.md`, `CLAUDE.md`, `docs/PROJECT_LOG.md`, `docs/tracking-research.md`, this run log.
