# PLAN 5: Real-time check fix, and Phase 2 groundwork (experiments only)

Repo: ShotVision (`https://github.com/dannybud19/ShotVision`), main folder `~/Desktop/ShotVision`, branch `stage1/label-tooling`.
Written: 13 Nov 2026, for Sonnet 5.5 running with `docs/plans/PROMPT_for_plan_runner.md`.

**Phase 1 is not finished.** It is waiting for the owner's own filming (50+ fixed-camera misses). This plan does two things that don't depend on that footage:

1. Fixes the live check's "real time" verdict, which is wrong for live cameras.
2. Builds **Phase 2 groundwork as experiments only**: finding the release moment from the ball's path, and a court-mapping tool. Nothing in `shotvision/` changes for Phase 2. Nothing ships.

Two parts with a hard stop between them, like PLAN_3:

| Part | Steps | Ends with |
| --- | --- | --- |
| **A** | A0 pre-flight · A1 real-time fix · A2 release-moment experiment · A3 release review sheets · A4 court-mapping module · A5 decisions file · A6 docs, push | The owner marks the true release frame on 20 shots. **STOP.** |
| **B** | B0 checks the decisions · B1 measures the release finder's error · B2 docs, push | Final report. **STOP.** |

---

## Runner prompt session notes (owner: paste under "## The plan for this session")

```text
Run: docs/plans/PLAN_5_realtime_and_phase2_groundwork.md, PART A ONLY   (or: PART B ONLY)

Folder and branch: the main repo folder ~/Desktop/ShotVision on stage1/label-tooling. Ignore the runner prompt's first paragraph about PLAN_1/PLAN_2 folders. No parallel plan, no worktree.

Owner-approved exceptions to the runner prompt's hard rules, for this session only. Nothing else is relaxed:
1. Step A1 edits experiments/live_check.py and its test file exactly as described.
2. Step A3 may add an optional argument to experiments/review_sheets.py exactly as described.
3. Part B creates sample_clips/release_labels.json from the owner's decisions. sample_clips/labels.json is never edited in this plan.

Never edit anything under shotvision/. Never run shotvision/main.py, experiments/live_check.py, or anything that loads models/basketball_best.pt. Cached detections only. Never pip install anything.

Effort: high.

Begin with "Before you do anything" from the runner prompt: read the files and write the summary, then wait for my go-ahead.
```

---

## 0. Rules (read before every commit)

1. **Never load the model.** Never pass `--recollect`. Never run `shotvision/main.py`, `experiments/live_check.py`, `scripts/render_overlay.py` or `scripts/diagnose_shots.py`. If anything prints Ultralytics/torch model-loading output, stop it and report.
2. **Nothing under `shotvision/` changes.** No scoring, threshold, config or label change. `sample_clips/labels.json` is not edited.
3. **No new dependencies.** Never `pip install`. Use only what is already importable in `.venv` (check with `.venv/bin/python -c "import <name>"`). If something needed is missing, stop and report.
4. **Never decide where a release happened yourself.** You build the finder and the review sheets. The owner marks the true release frames. Describe what is visible, never a verdict.
5. **Edit only the files each step names.** Ideas go under "Suggestions (not done)".
6. **Tests pass before every commit.** Test command:
   ```bash
   .venv/bin/python -m pytest -q \
     --deselect tests/test_detector.py::test_detector_loads_real_basketball_checkpoint_and_predicts \
     --deselect tests/test_ball_tracker.py::test_update_runs_end_to_end_on_blank_frame
   ```
7. **Commit only where the plan says**, with the message given.
8. **No destructive git** (`reset --hard`, `checkout -- <file>`, `clean`, `push --force`, `branch -D`).
9. **Numbers:** copy from command output.
10. **Docs:** UK spelling, no em dashes, short sentences, tables for comparisons.
11. **Run log:** `experiments/results/RUN_LOG_PLAN_5_<part>_<YYYY-MM-DD>.md`, created after A0.1's commit. After each step append the step id, commands, `Expected: ... | Got: ... | Match: yes/no` lines and files changed. Commit it with the docs commit.

---

# PART A

## A0. Pre-flight

### A0.1 Branch and tree
```bash
git checkout stage1/label-tooling
git pull --ff-only
git status --short
git log --oneline -3
```
Expected: latest commit `53fe77b Docs: PLAN_4 ...` or later. `git status --short` empty, or only `?? docs/plans/PLAN_5_realtime_and_phase2_groundwork.md`. Anything else: stop and report.

If the plan is untracked, commit it:
**Commit:** `Plans: PLAN_5 (real-time check fix, Phase 2 groundwork experiments)`

### A0.2 Tests
Expected: `172 passed, 2 deselected`. Record as `BASE_TESTS`. If not, stop.

### A0.3 Baseline report
```bash
mkdir -p experiments/results
.venv/bin/python scripts/evaluate.py --report > experiments/results/plan5_gate_a_before.txt 2>&1; echo "exit=$?"
sed -n '/=== Gate A ===/,$p' experiments/results/plan5_gate_a_before.txt
```
Expected: `Makes counted: 162/248 (65.3%)`, `0/85 labeled misses, + 1 spurious makes`, in-scope verdict `NOT ENOUGH MISSES TO JUDGE (8 < 50)`, exit `1`. Mismatch: stop.

### A0.4 What's available
```bash
.venv/bin/python -c "import numpy, cv2; print('numpy', numpy.__version__, 'cv2', cv2.__version__)"
.venv/bin/python -c "import scipy; print('scipy', scipy.__version__)" || echo "no scipy"
```
Record both. Use numpy and cv2 only, even if scipy exists.

---

## A1. Real-time verdict for live cameras

**Why:** a live camera delivers frames at its own rate, so processing fps can never exceed it. The owner's webcam run showed `source fps 29.89`, `processing fps 29.29`, `latency p95 15.3 ms`, and printed `real time: NO`. With a 33.5 ms frame interval and 15.3 ms latency, it clearly keeps up. The verdict is wrong for device sources.

### A1.1 Change in `experiments/live_check.py`
Read the script first. Find where `real_time` is computed and printed.
- Put the verdict in a plain function:
  ```python
  def is_real_time(source_type: str, fps_used: float, processing_fps: float, latency_p95_ms: float) -> tuple[bool, str]:
      """Files: real time when processing fps >= the file's fps.
      Live devices and URLs: frames can't be processed faster than they arrive,
      so real time means each frame is analysed within one frame interval (p95)."""
      if source_type == "file":
          return processing_fps >= fps_used, "processing fps >= source fps"
      budget_ms = 1000.0 / fps_used if fps_used > 0 else float("inf")
      return latency_p95_ms < budget_ms, f"latency p95 {latency_p95_ms:.1f} ms < frame interval {budget_ms:.1f} ms"
  ```
- Use it for the summary's `real_time` value and for the printed line, so it reads e.g. `real time: YES (latency p95 15.3 ms < frame interval 33.5 ms)`.
- Add `"real_time_rule"` (the reason string) to the summary dict.
- Use the source type the script already has (`source.type` or equivalent). If it has none, derive it with `_classify_source` from `shotvision.capture.source` (import only, no edit).

Nothing else in the script changes.

### A1.2 Tests
In the existing live-check test file (`tests/test_live_check.py`), add:
- file, 123 processing fps vs 30 → `True`;
- file, 25 vs 30 → `False`;
- device, fps 29.89, p95 15.3 ms → `True`, and the reason string contains `33.5`;
- device, fps 30, p95 40 ms → `False`.

Run the tests. Expected: `BASE_TESTS + 4` passed.
**Commit:** `live_check: real-time verdict for live sources uses p95 latency against the frame interval`

Do not run the script.

---

## A2. Release-moment experiment

**Why:** Phase 2 (two or three) needs to know **when** the ball left the shooter's hands, so it knows **where** the shooter was standing. The first step is finding the release moment from the ball's path alone, with no new model. A shot's flight after release is a smooth arc (a parabola in image space, y increasing downward). Before release the ball moves with the shooter's hands. The release is where the arc begins.

### A2.1 Read first
Read `scripts/evaluate.py` (`replay`, `Replay`, `FrameState`) and `experiments/shot_diagnostics.py`. Write in the run log:
- which `FrameState` field (if any) holds the tracked ball's position per frame, and its format;
- how `shot_diagnostics.py` gets per-frame ball positions.

Use the **tracked** ball if `FrameState` exposes it. Otherwise fall back to the highest-confidence `ball` detection with `conf >= 0.3` per frame from the cached detections, and say so in the run log. Don't change `evaluate.py` to expose anything.

### A2.2 New script `experiments/release_moment.py`
Read-only. Imports from `scripts/evaluate.py` the same way `shot_diagnostics.py` does.

**Core function (plain, testable):**
```
find_release(points, rim, fps) -> dict | None
```
- `points`: list of `(frame_idx, cx, cy, w)` for one shot window, sorted by frame, gaps allowed.
- `rim`: `(hx, hy, hw)`, the hoop centre and width (median of the window's highest-confidence hoop boxes, `conf >= 0.6`).
- Returns `None` if there are fewer than 6 points.

Algorithm (implement exactly; don't tune the numbers):
1. **Apex:** among points that are above the rim top (`cy < hy`) and within `to_frames(2.0, fps)` before the last point that is within 1.5 hoop widths horizontally of `hx`, the point with the smallest `cy`. If none, return `None` with reason `no_apex`.
2. **Walk back from the apex.** Start with the points from the apex to `to_frames(0.3, fps)` after it. Then add earlier points one at a time. After each addition, fit `y(t)` as a quadratic and `x(t)` as a line (`numpy.polyfit`, t = frame index), and compute the RMS residual of y in units of median ball width (`w`).
3. Stop adding when **either** the RMS residual exceeds `0.25` ball widths, **or** the quadratic's `a <= 0` (not falling the way gravity does in image space), **or** the gap to the next earlier point exceeds `to_frames(0.25, fps)`.
4. The **release frame** = the earliest point still in the accepted fit. Also return:
   - `release_xy` (pixels) and `release_rim_units`: `((x - hx)/hw, (y - hy)/hw)`;
   - `flight_frames` = apex frame minus release frame;
   - `fit_points`, `rms`, and `stop_reason` (`residual`, `curvature`, `gap`, `ran_out`).

**Runner:** for every labelled `MAKE` or `MISS` shot in `load_labels(split="all", include_duplicates=False)`, window = label `start - to_frames(3.0, fps)` to label `end`, clamped. Run `find_release`. Write:
- `--json experiments/results/release_moment.json`: one record per shot (clip, label start/end/outcome/card, camera class from `load_clip_meta()`, and the `find_release` output or the failure reason);
- `--out experiments/results/release_moment.md`: per camera class, how many shots got a release, the failure reasons by count, and the median and p90 of `flight_frames` converted to seconds.

`--clips` optional, as in `evaluate.py`.

### A2.3 Tests `tests/test_release_moment.py`
Synthetic points only (no cache, no model), fps 30, rim `(500, 300, 60)`, ball width 20:
1. **Clean arc:** 10 frames of the ball moving with the hands (x = 200, y rising slowly 520 → 500, small wobble ±2 px), then a parabola from frame 10: `x = 200 + 15·t`, `y = 500 - 22·t + 0.9·t²` (t from 0). Expect release frame within ±2 of 10.
2. **Gap:** the same arc with frames 12 to 14 removed. Expect release within ±2 of 10.
3. **Too few points:** 4 points → `None`.
4. **No apex above the rim:** a path that never goes above `y = 300` → reason `no_apex`.

If test 1 fails, check the implementation against the spec before anything else. Do not change the thresholds (0.25, 0.3 s, 0.25 s, 2.0 s, 1.5 hoop widths) to make it pass. If it can't pass with the spec as written, stop and report the fitted values.

### A2.4 Run it
```bash
.venv/bin/python experiments/release_moment.py --out experiments/results/release_moment.md --json experiments/results/release_moment.json
```
Report the `.md` content. Sanity check: the number of shots processed equals `248 + 85 = 333`. If not, report the difference.

Run the tests.
**Commit:** `experiments/release_moment.py: release frame from the ball's arc (no model), report by camera class`
(Commit the `.md`; the `.json` is gitignored.)

---

## A3. Release review sheets (for the owner to mark the true release)

### A3.1 Pick 20 shots
From `release_moment.json`, pick shots that got a release, in this order until you have 20:
1. every `fixed/single` shot whose clip is one of `lf_shot_detection.mp4`, `lf_back.mp4`, `chonyy_two_score_three_miss.mp4`, `aggie_NathanBBall.mov`, `video_test_5.mp4`, taking at most 6 per clip, lowest label start first;
2. if still short, other `fixed/single` shots, lowest start first.

Mix makes and misses as they come; don't filter by outcome. Write the list (clip, label start, end, outcome, estimated release frame) to the run log.

### A3.2 Optional argument in `experiments/review_sheets.py`
Add to the `frames` subcommand, without changing its default behaviour:
- `--label <text>`: replaces the header's `pipeline: spurious MAKE` text with `<text>`. Default stays `pipeline: spurious MAKE`.

Add one test in `tests/test_review_sheets.py` that the header text uses the default when `--label` isn't given, and the custom text when it is (test the function that builds the header string; if no such function exists, extract one, and change nothing else).

### A3.3 Build the sheets
For each of the 20 shots, run:
```bash
.venv/bin/python experiments/review_sheets.py frames --clip <clip> --frames <estimated release> \
  --before 0.8 --after 0.8 --step 0.033 --label "release candidate" --out sample_clips/_review/release
```
At 30 fps that tiles every frame in a 1.6 s window, so the owner can read exact frame numbers. Check the 20 `.png` files exist. Open two of them and check only that the frame numbers on the tiles are consecutive and the hoop box is on the hoop. Rule 4: no verdicts.

Run the tests.
**Commit:** `review_sheets: optional --label header text; release-candidate sheets built for 20 fixed-camera shots`

---

## A4. Court-mapping module (no footage needed)

**Why:** two or three is decided by where the shooter's feet are on the floor. With a fixed camera, clicking 4 or more court points with known positions gives a homography: a mapping from image pixels to court coordinates. This step builds and tests the maths. The owner tries it on a real frame later.

### A4.1 New file `experiments/court_map.py`
Plain functions, numpy and cv2 only:
- `COURTS`: a dict with two entries, values in metres, origin at the centre of the rim projected on the floor, x along the baseline, y towards half court:
  - `"fiba"`: three-point arc radius `6.75`; corner three distance `6.60` from the rim centre, measured along x; the corner straight sections end where the arc meets them; free-throw line `5.80` from the baseline; rim centre `1.575` from the baseline.
  - `"nba"`: arc radius `7.24`; corner distance `6.71`; free-throw line `5.79` from the baseline; rim centre `1.575` from the baseline (approximately; note "approx" in a comment).
- `fit_homography(image_pts, court_pts) -> H` with `cv2.findHomography` (method 0, at least 4 points). Raise `ValueError` for fewer than 4 points.
- `to_court(H, x, y) -> (cx, cy)` using `cv2.perspectiveTransform`.
- `is_three(court_xy, court="fiba") -> bool`: outside the arc radius, or in a corner (|x| beyond the corner distance and y within the corner straight section, i.e. the baseline side of where the arc meets the corner line). On the line counts as two.
- `__main__`: `--image <png/jpg>` opens the image in a cv2 window, the owner clicks points and types each point's court coordinates in the terminal, then the script prints `H` and saves it as JSON next to the image. **This part needs the owner's screen. Don't run it.**

### A4.2 Tests `tests/test_court_map.py`
- Make up a homography (e.g. a perspective warp from `cv2.getPerspectiveTransform` on four corners), project known court points into "image" points, fit back with `fit_homography`, and check `to_court` returns the original points within 1 cm.
- `is_three`: a point at radius 6.0 m in front of the rim → False; 7.0 m → True (fiba); a point exactly on the 6.75 m arc → False; a corner point at x = 6.7, y = 0.5 → True (fiba); x = 6.5, y = 0.5 → False.
- Fewer than 4 points → `ValueError`.

Run the tests.
**Commit:** `experiments/court_map.py: homography from clicked court points, is_three (FIBA and NBA), tests`

---

## A5. Decisions file

Create `docs/plans/PLAN_5_decisions.md`:

````markdown
# PLAN_5 decisions (owner fills this in, then runs Part B)

Release sheets: `sample_clips/_review/release/`. Each tile has its frame number. For each shot, find the **first frame where the ball has fully left the shooter's hand(s)** and write that frame number. If you can't see it (ball hidden, hands out of frame), write `CANT_TELL`.

| # | Clip | Label start-end | Outcome | Finder's estimate | Owner: true release frame | Owner: note |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | <...> | <...> | <...> | <...> | | |
...(20 rows)

Owner: anything else Part B should know (or "none"):
````

Fill every `<...>` from A3.1. Leave the Owner columns empty.

**Commit:** `Plans: PLAN_5 decisions file (release frames for the owner)`

---

## A6. Docs, push, report, STOP

1. **`docs/PROJECT_LOG.md`**: entry above `## Tools used`: `### <date>: PLAN_5 Part A: real-time fix, release-moment experiment, court-mapping module`, one line per step, commit hashes.
2. **`docs/tracking-research.md`**: new section `## 5. Phase 2 groundwork (experiments)` at the end, with the A2 report table and two sentences on the court-mapping module. No conclusions about accuracy yet (that's Part B).
3. **`CLAUDE.md`**: add a bullet under the current phase: `- **Phase 2 groundwork (experiments only):** experiments/release_moment.py (release frame from the ball's arc) and experiments/court_map.py (homography, is_three). Nothing in shotvision/ uses them.` Update the test count. Keep the Next step bullet as it is, and add after it: `- **Owner, meanwhile:** mark release frames in docs/plans/PLAN_5_decisions.md, then PLAN_5 Part B.`
4. **`HANDOVER.md`**: in section 10, replace items 1 and 2 (run PLAN_4, rerun the webcam check) with one line: `PLAN_4 done. Live webcam: measured 29.89 fps vs 15 reported, latency p95 15.3 ms; real-time verdict fixed in PLAN_5.` Add a line: `PLAN_5 Part A done; owner marks release frames, then Part B.` Nothing else.

Run the tests.
**Commit:** `Docs: PLAN_5 Part A`

```bash
git status --short     # must be empty
git push origin stage1/label-tooling
```

Final report in the 7-part format plus **"Owner: what to do now"**:
1. Open `sample_clips/_review/release/`, mark the 20 release frames in `docs/plans/PLAN_5_decisions.md`, commit it.
2. Optional: try the court mapper on a still frame from a fixed clip: `.venv/bin/python experiments/court_map.py --image <frame.png>`.
3. Start a new session with `PART B ONLY`.

## **STOP HERE. Do not start Part B.**

---

# PART B (only after the owner has filled in the decisions file)

## B0. Pre-flight
1. Run log `RUN_LOG_PLAN_5_B_<date>.md`. `git pull --ff-only`, `git status --short` (empty).
2. Check every Owner cell in `docs/plans/PLAN_5_decisions.md`: an integer frame, or `CANT_TELL`. Any empty or other value: stop and list them.
3. Tests pass. Report matches `plan5_gate_a_before.txt` (diff empty).

## B1. Measure the finder's error
1. Write `sample_clips/release_labels.json`: `{"_doc": "Owner-marked release frames (PLAN_5). Frame = first frame the ball has fully left the hand(s).", "shots": [{"clip", "label_start", "label_end", "release_frame", "note"}]}`, integer rows only. Check it's tracked by git (`git check-ignore` must print nothing; if it's ignored, stop and report, since `sample_clips/*` is ignored except listed files, and adding an exception means editing `.gitignore`, which needs the owner).
2. New script `experiments/release_error.py`: joins `release_labels.json` with `release_moment.json` and reports, for the `N` integer rows: error = finder frame minus owner frame; median absolute error in frames and in ms; p90 absolute error; share within ±2 frames and within ±5 frames; the signed mean (early vs late bias); the worst 3 with their `stop_reason`. Also how many rows were `CANT_TELL`.
3. Test `tests/test_release_error.py` with a hand-made pair of files in `tmp_path`.
4. Run it, write `experiments/results/release_error.md`, report it.

Do **not** change the finder to improve the numbers. If you see a pattern (for example, always late when `stop_reason` is `gap`), put it under Suggestions.

Run the tests.
**Commit:** `Release frames marked by the owner; experiments/release_error.py measures the finder`

## B2. Docs, push, report, STOP
1. `docs/tracking-research.md` section 5: add the error table and one plain sentence: whether the ball-arc release finder is within ±2 frames on most shots (state the share), or not.
2. `docs/PROJECT_LOG.md`: dated entry, `### <date>: PLAN_5 Part B: release finder measured`.
3. `CLAUDE.md`: remove the "Owner, meanwhile" bullet; add the headline error to the Phase 2 groundwork bullet.
4. `HANDOVER.md` section 10: replace the PLAN_5 line with the headline result.

Run the tests.
**Commit:** `Docs: PLAN_5 Part B (release finder error)`
Push. Final report in the 7-part format.

## **STOP HERE.** Do not start Phase 2 for real, and don't touch `shotvision/`.
