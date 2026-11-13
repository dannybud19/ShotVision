# Run log: PLAN_5 Part A (2026-11-13)

Plan: `docs/plans/PLAN_5_realtime_and_phase2_groundwork.md`, Part A only (A0 to A6). Branch `stage1/label-tooling`, main repo folder.

Owner decisions before the start:
- **A2.3 fixture fix (an error in the plan, owner's note):** the plan's synthetic arc never rises above the plan's rim `(500, 300, 60)`: the smallest `cy` on the arc is 365.6 (t = 12), so the apex rule `cy < hy` returns `no_apex`. Owner-approved fix: tests 1 and 2 use rim `(500, 450, 60)` and the arc runs t = 0 to 24 inclusive after the 10 hand frames (it comes back down through rim height near x = 528). Test 4 keeps rim `(500, 300, 60)`. Test 3 unchanged. Thresholds unchanged. If test 1 still fails, stop and report the fitted values.
- A3.2: no function builds the header text (it is an inline f-string in `run_frames`), so extract one, change nothing else.
- A3 sheets go to `sample_clips/_review/release/`, which is gitignored (`sample_clips/*`). The A3 commit carries code and tests only.
- A2 ball source: tracked ball from `FrameState.obs`, weak observations included. Ball width = `right - left`. Rim = median over the window of each frame's best hoop box with `conf >= 0.6`. If release coverage is low because the tracker has few points before the apex, report it plainly.
- Numpy and cv2 only (scipy is not installed).
- A6.4 numbers checked against `experiments/results/live_check_camera.json` (source fps 29.886, reported 15.0, p95 15.278 ms, `real_time` False under the old rule).

## A0: Pre-flight

- A0.1 `git checkout stage1/label-tooling`, `git pull --ff-only`, `git status --short`, `git log --oneline -3`.
  - Expected: latest commit `53fe77b` or later; only PLAN_5 untracked | Got: HEAD `53fe77b`, `?? docs/plans/PLAN_5_realtime_and_phase2_groundwork.md`, pull already up to date | Match: yes
  - Committed the plan: `ad612d8 Plans: PLAN_5 (real-time check fix, Phase 2 groundwork experiments)`.
- A0.2 Test command.
  - Expected: `172 passed, 2 deselected` | Got: `172 passed, 2 deselected in 0.87s` | Match: yes (BASE_TESTS = 172)
  - Note: my first attempt put the deselect flags in a zsh variable, which does not word-split, so it printed `no tests ran`. Rerun with the flags written out. Shell mistake only.
- A0.3 `evaluate.py --report > experiments/results/plan5_gate_a_before.txt`.
  - Expected: `Makes counted: 162/248 (65.3%)` | Got: `Makes counted: 162/248 (65.3%)` | Match: yes
  - Expected: `0/85 labeled misses, + 1 spurious makes` | Got: `False makes: 0/85 labeled misses, + 1 spurious makes` | Match: yes
  - Expected: `NOT ENOUGH MISSES TO JUDGE (8 < 50)` | Got: same | Match: yes
  - Expected: exit `1` | Got: `exit=1` | Match: yes
  - No Ultralytics/torch output (grep count 0).
- A0.4 Dependencies: `numpy 2.5.4 cv2 5.0.0`; `scipy`: `ModuleNotFoundError: No module named 'scipy'`. Numpy and cv2 only.

Files changed: PLAN_5 committed (`ad612d8`). Created (gitignored) `experiments/results/plan5_gate_a_before.txt`.

## A1: Real-time verdict for live cameras

- A1.1 `experiments/live_check.py`: added `is_real_time()` (verbatim from the plan) after `percentile`. In `run_live`, `source_type = source.type` is read inside the `with` block next to `reported_fps`; the verdict is computed after the run from `source_type`, `fps` (the value used), `processing_fps` and the p95 latency (now held in `latency_p95`). The summary's `real_time` uses it and a new `real_time_rule` key holds the reason string. `print_summary` prints `real time: YES|NO (<rule>)`. `py_compile` passes. The script was not run.
- A1.2 Four tests added to `tests/test_live_check.py` (file 123 vs 30, file 25 vs 30, device 29.89 / 15.3 ms with `33.5` in the reason, device 30 / 40 ms).
  - Expected: `BASE_TESTS + 4` = 176 passed | Got: `176 passed, 2 deselected` | Match: yes

Files changed: `experiments/live_check.py`, `tests/test_live_check.py`.

## A2: Release-moment experiment

- A2.1 Read first.
  - `FrameState` (scripts/evaluate.py) has `obs: BallObservation | None`, `rim: RimRegion | None`, `armed: bool`. `obs` is the tracker's followed ball: `x`, `y` (centre), `left`, `top`, `right`, `bottom`, `weak`, `track_id`. Ball width = `right - left`. So the tracked ball is exposed, and the raw-detection fallback is not used. `evaluate.py` is unchanged.
  - `experiments/shot_diagnostics.py` gets raw per-frame ball positions from `dets[f]` (best `ball` detection by confidence, `.center`) and the followed ball from `rep.frames[f].obs`.
- A2.2 New `experiments/release_moment.py`. `find_release` implements the plan's four steps with its numbers (6 points, 1.5 hoop widths, 2.0 s, 0.3 s, 0.25 ball widths, 0.25 s), none tuned. Runner: window = label start minus `to_frames(3.0, fps)` to label end, clamped; rim = median over the window of each frame's best hoop box (`conf >= 0.6`); points = `rep.frames[f].obs`, weak included. The runner exits if a clip has no detection cache, so it can never load the model.
- A2.3 `tests/test_release_moment.py`, with the owner-approved fixture fix.
  - Fixture: tests 1 and 2 use rim `(500, 450, 60)` and the arc t = 0 to 24 after 10 hand frames. Test 4 keeps rim `(500, 300, 60)`. Test 3 unchanged. Thresholds unchanged.
  - Fitted values (test 1): `release_frame 9`, `apex_frame 22`, `flight_frames 13`, `fit_points 23`, `rms 0.212`, `stop_reason residual`. Test 2 (frames 12 to 14 removed): `release_frame 9`, `apex_frame 22`, `fit_points 20`, `rms 0.214`, `stop_reason residual`. Both are within the plan's +-2 of frame 10.
  - The frame-9 result is the fit accepting the first hand frame (one outlier of about 21 px gives an RMS of 0.21 ball widths, under 0.25) and rejecting the second.
- A2.4 `.venv/bin/python experiments/release_moment.py --out experiments/results/release_moment.md --json experiments/results/release_moment.json`. Exit 0. No Ultralytics/torch/loading output (grep count 0). The detection cache was used for every clip.
  - Expected: shots processed = 248 + 85 = 333 | Got: 333 (248 makes, 85 misses) | Match: yes
  - Expected: tests pass | Got: `180 passed, 2 deselected` (176 + 4 new) | Match: yes
  - Results (see `experiments/results/release_moment.md`): releases found for 68/68 `fixed/single`, 147/162 `moving/single`, 97/103 `moving/multi` (312/333 in all). The only failure reason is `no_apex` (21 shots, all in moving-camera clips). Median tracked points in a window: 74 (`fixed/single`), 84, 127. So the tracker has plenty of points: coverage is not low.
  - Plain observation, not a verdict: median flight (apex minus release) is 0.63 s in `fixed/single`, 0.17 s in `moving/single` and 0.00 s in `moving/multi`. Releases with a flight of 0 frames (the walk back added nothing before the apex): 3 of 68 `fixed/single`, 39 of 147 `moving/single`, 49 of 97 `moving/multi`. The owner's marked frames (Part B) are what will say whether any of this is right.

Files changed: new `experiments/release_moment.py`, `tests/test_release_moment.py`, `experiments/results/release_moment.md` (the `.json` is gitignored).

## A3: Release review sheets

- A3.1 The 20 shots. Reading chosen (literal): go through the listed clips in the plan's order, at most 6 per clip, lowest label start first, only shots that got a release; stop at 20. `chonyy_two_score_three_miss.mp4` has only 5 labelled shots, so `aggie_NathanBBall.mov` supplies 3 and `video_test_5.mp4` none. Step 2 of the plan's order was not needed.

| # | Clip | Label start | Label end | Outcome | Estimated release frame |
| --- | --- | --- | --- | --- | --- |
| 1 | lf_shot_detection.mp4 | 55 | 82 | MAKE | 45 |
| 2 | lf_shot_detection.mp4 | 161 | 195 | MAKE | 151 |
| 3 | lf_shot_detection.mp4 | 272 | 303 | MAKE | 258 |
| 4 | lf_shot_detection.mp4 | 370 | 413 | MAKE | 356 |
| 5 | lf_shot_detection.mp4 | 503 | 532 | MAKE | 494 |
| 6 | lf_shot_detection.mp4 | 600 | 640 | MAKE | 591 |
| 7 | lf_back.mp4 | 44 | 75 | MAKE | 29 |
| 8 | lf_back.mp4 | 140 | 182 | MAKE | 135 |
| 9 | lf_back.mp4 | 261 | 297 | MAKE | 247 |
| 10 | lf_back.mp4 | 359 | 389 | MAKE | 345 |
| 11 | lf_back.mp4 | 491 | 525 | MAKE | 477 |
| 12 | lf_back.mp4 | 588 | 626 | MAKE | 574 |
| 13 | chonyy_two_score_three_miss.mp4 | 55 | 90 | MISS | 24 |
| 14 | chonyy_two_score_three_miss.mp4 | 150 | 195 | MISS | 128 |
| 15 | chonyy_two_score_three_miss.mp4 | 262 | 292 | MISS | 237 |
| 16 | chonyy_two_score_three_miss.mp4 | 362 | 390 | MAKE | 338 |
| 17 | chonyy_two_score_three_miss.mp4 | 460 | 486 | MAKE | 438 |
| 18 | aggie_NathanBBall.mov | 66 | 117 | MISS | 43 |
| 19 | aggie_NathanBBall.mov | 205 | 239 | MAKE | 181 |
| 20 | aggie_NathanBBall.mov | 308 | 351 | MAKE | 289 |

- A3.2 `experiments/review_sheets.py`: extracted `build_header_text(stem, target, note, first, last)` (it returns the same string the inline f-string did), added `--label` to `frames` (default `HEADER_NOTE`, so `pipeline: spurious MAKE`), and `run_frames` passes `args.label`. Nothing else changed. One test added to `tests/test_review_sheets.py` (default note without `--label`, custom note with it, via `parse_args` and `build_header_text`); the test file's import line grew to list the new names.
- A3.3 Ran the plan's command 20 times (one per shot, `--before 0.8 --after 0.8 --step 0.033 --label "release candidate" --out sample_clips/_review/release`), all cached detections, no model. Exit 0, no Ultralytics/torch/loading/cache errors in the output. The run took more than 2 minutes, so the harness moved it to the background; it completed.
  - Expected: 20 `.png` files | Got: 20 `.png` (plus 20 `_full.jpg` and one `_targets.json` per clip, 44 files in all) | Match: yes
  - Checked two sheets, only the two things the plan names. `lf_back_f29.png`: tiles f5 to f53, consecutive, 49 tiles; the green hoop box is on the hoop in every tile. `aggie_NathanBBall_f43.png`: tiles f19 to f67, consecutive; the hoop box is on the hoop in every tile. No verdicts.
  - Expected: tests pass | Got: `181 passed, 2 deselected` (180 + 1 new) | Match: yes
- What is visible, described and not judged: the tiles are crops centred on the hoop (`crop_box` uses the hoop boxes). In the two sheets I opened, the shooter is not inside the crop; the ball box enters the crop from the left edge later in the window. The `_full.jpg` of `lf_back_f29` (the whole frame at the estimated release frame) shows a player at the left of the frame with the ball box beside the player's raised hand. I changed nothing because of this; it is for the owner and the report.
- Oddity noticed (not fixed): `review_sheets.py frames` writes `<stem>_targets.json` once per call, so with one call per shot each call overwrites the previous call's file for the same clip.
- Slip: before the loop I ran `rm -rf sample_clips/_review/release` to start clean, without checking the target first. The folder did not exist (the folder's modified time is still 9 Nov 20:05 and the PLAN_3 sheets are all still there), so nothing was deleted. From now on I look before removing anything.

Files changed: `experiments/review_sheets.py`, `tests/test_review_sheets.py`. The sheets are in `sample_clips/_review/release/` (gitignored, local only).

## A4: Court-mapping module

- A4.1 New `experiments/court_map.py` (numpy and cv2 only). `COURTS` has `fiba` (arc 6.75, corner 6.60, free-throw line 5.80 from the baseline, rim 1.575 from the baseline) and `nba` (arc 7.24, corner 6.71, free-throw line 5.79, rim 1.575 with a comment saying approx). Origin under the rim centre, x along the baseline, y towards half court. `fit_homography` uses `cv2.findHomography` method 0 and raises `ValueError` for fewer than 4 points. `to_court` uses `cv2.perspectiveTransform`. `is_three`: true when outside the arc (`hypot > radius`) or when `|x| > corner_x` and `y <=` the height where the arc meets the corner line (`sqrt(r^2 - corner_x^2)`); on the line counts as two.
  - Small additions beyond the plan's text, for safety only: `fit_homography` also raises `ValueError` when the image and court point counts differ, and when OpenCV cannot fit (degenerate points, `findHomography` returns None).
  - `__main__` (`--image`): the click-and-type fitter. It needs the owner's screen. Not run. `py_compile` passes.
- A4.2 `tests/test_court_map.py` (5 tests): a made-up perspective view (`cv2.getPerspectiveTransform`) projects 6 known court points to image points, `fit_homography` recovers them within 1 cm (and one extra point not used in the fit); fewer than 4 points raises; `is_three` FIBA arc (6.0 m False, 7.0 m True, exactly 6.75 m False); FIBA corner (x 6.7 y 0.5 True, x 6.5 y 0.5 False, plus the mirror corner and the exact 6.60 line); NBA uses its own distances (7.0 m False, 7.5 m True, corner 6.8 True).
  - Expected: tests pass | Got: `186 passed, 2 deselected` (181 + 5 new) | Match: yes

Files changed: new `experiments/court_map.py`, new `tests/test_court_map.py`.

## A5: Decisions file

- Created `docs/plans/PLAN_5_decisions.md` from the plan's template: 20 rows filled from A3.1 (clip, label start-end, outcome, finder's estimate); the two Owner columns are empty. No `<...>` placeholders left, no em dashes. Followed the template literally, so it carries no note about the hoop-centred crops (that is in the report instead).
- No tests to run for this step (docs only); no code changed.

Files changed: new `docs/plans/PLAN_5_decisions.md`.

## A6: Docs, push, report

- `docs/PROJECT_LOG.md`: entry `### 2026-11-13: PLAN_5 Part A: real-time fix, release-moment experiment, court-mapping module` above `## Tools used`, one line per step with commit hashes (A6 shown as "this commit").
- `docs/tracking-research.md`: new `## 5. Phase 2 groundwork (experiments)` at the end, with the A2 per-class table (pasted from `experiments/results/release_moment.md`), the failure and stop-reason counts, and two sentences on the court-mapping module. No accuracy conclusions (that is Part B).
  - Ambiguity: the file already has a `## 5. Self-review` section, so there are now two sections numbered 5. I used the heading the plan gives, literally. Suggest renumbering later.
- `CLAUDE.md`: added the Phase 2 groundwork bullet (before the Next step bullet), kept the Next step bullet unchanged, added the "Owner, meanwhile" bullet after it. Test count: 174 to 188 total, 172 to 186 with the two model tests deselected.
- `HANDOVER.md` section 10: replaced items 1 and 2 with the plan's two lines (item 1: PLAN_4 done and the live webcam numbers; item 2: PLAN_5 Part A done). Items 3 to 5 unchanged. Nothing else touched. The webcam numbers were checked against `experiments/results/live_check_camera.json` (source fps 29.886, reported 15.0, p95 15.278 ms).
- Added-lines check: 0 em dashes.
  - Expected: tests pass | Got: `186 passed, 2 deselected` | Match: yes

Files changed: `docs/PROJECT_LOG.md`, `docs/tracking-research.md`, `CLAUDE.md`, `HANDOVER.md`, this run log.
