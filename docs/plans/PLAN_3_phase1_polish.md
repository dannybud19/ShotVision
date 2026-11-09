# PLAN 3: Phase 1 polish (Part A, then a stop, then Part B)

Repo: ShotVision (`https://github.com/dannybud19/ShotVision`), main folder `~/Desktop/ShotVision`, branch `stage1/label-tooling`.
Written: 9 Nov 2026, for Sonnet 5.5 (or any model) running with `docs/plans/PROMPT_for_plan_runner.md`.

This plan has **two parts with a hard stop between them**.

| Part | What | Ends with |
| --- | --- | --- |
| **A** | Merge the line-crossing experiment, fix the in-scope gate, build review sheets, handle phone video rotation, add a live-check script, update docs | A decisions file the owner fills in. **STOP. Do not start Part B.** |
| **B** | Apply the owner's decisions (camera re-tags, Enosburg labels), re-score, update docs | Final report. **STOP.** |

Run **only the part you were told to run**. If you were told "Part A", stop after step A8. If you were told "Part B", start at B0 and only if the decisions file is complete.

---

## Runner prompt session notes (owner: paste this under "## The plan for this session" in the runner prompt)

```text
Run: docs/plans/PLAN_3_phase1_polish.md, PART A ONLY   (or: PART B ONLY)

Folder and branch: the main repo folder ~/Desktop/ShotVision on stage1/label-tooling.
Ignore the runner prompt's first paragraph about PLAN_1/PLAN_2 folders. There is no parallel plan this time.

Owner-approved exceptions to the runner prompt's hard rules, for this plan only. Nothing else is relaxed:
1. Step A2 edits scripts/evaluate.py (reporting only) and updates ONE existing test in tests/test_gate_report.py exactly as the plan says.
2. Step A5 edits shotvision/capture/source.py and tests/test_source.py exactly as the plan says. No other file under shotvision/.
3. Step A1 merges exp/line-crossing and removes the ../ShotVision-exp worktree with `git worktree remove` (never --force).
4. Step B3 ADDS new label entries to sample_clips/labels.json from the owner's decisions. Existing labels are never changed.
5. Never run experiments/live_check.py. It loads the model. The owner runs it.
```

---

## 0. Rules (read before every commit)

1. **Never load the model.** Never pass `--recollect`. Never run `shotvision/main.py`, `experiments/live_check.py`, `scripts/render_overlay.py` or `scripts/diagnose_shots.py`. All scoring replays cached detections in `experiments/.cache/detections/*.fd4cd3dc7f.pkl`. If any command prints Ultralytics/torch model-loading output, or takes more than about a minute per clip, stop it and report.
2. **Never change how a shot is scored.** No threshold, config value, matching rule or slack window changes. `shotvision/config/default.json` is never touched.
3. **Never change an existing label** (`start`, `end`, `outcome`, `miss_type`, `note`, `card`). Part B may only *add* new entries, and only the ones the owner wrote in the decisions file.
4. **Never make a make/miss judgement yourself.** You build the review sheets. The owner decides what they show. Do not write "this looks like a make" or similar anywhere, not even in the report. If you notice something, describe what is visible ("ball above the rim in frames X to Y, not detected after Y") without a verdict.
5. **Edit only the files each step names.** Exceptions are listed in the session notes above. No refactors, renames, formatting changes or "while I'm here" fixes. Put ideas under "Suggestions (not done)" in the final report.
6. **Tests pass before every commit.** Test command (two tests need the model, so they are deselected):
   ```bash
   .venv/bin/python -m pytest -q \
     --deselect tests/test_detector.py::test_detector_loads_real_basketball_checkpoint_and_predicts \
     --deselect tests/test_ball_tracker.py::test_update_runs_end_to_end_on_blank_frame
   ```
7. **Commit only where the plan says "Commit"**, with the message given.
8. **Python:** always `.venv/bin/python` from the repo root. Never `pip install` anything. If an import is missing, stop and report.
9. **No destructive git:** never `git reset --hard`, `git checkout -- <file>`, `git clean`, `git push --force`, `git worktree remove --force`, `git branch -D`.
10. **Numbers:** copy from command output. Never round differently or recall from memory.
11. **Docs style:** UK spelling, no em dashes (use commas, full stops or brackets), short sentences, tables for comparisons.
12. **Run log:** create `experiments/results/RUN_LOG_PLAN_3_<part>_<YYYY-MM-DD>.md` at the start. After each step append: step id, commands run, `Expected: ... | Got: ... | Match: yes/no` lines, files changed. Re-read this file and section 0 if you lose track.

---

# PART A

## A0. Pre-flight

### A0.1 Branch and tree
```bash
git checkout stage1/label-tooling
git status --short
git log --oneline -3
git worktree list
```
Expected:
- Branch `stage1/label-tooling`, latest commit `ff854c0 Docs: 5 Nov tracker fix log, camera split, held-out Enosburg result` (or a later commit by the owner).
- `git status --short` shows nothing, **or** only `?? docs/plans/PLAN_3_phase1_polish.md` (this file). Any other change: **stop and report**, discard nothing.
- `git worktree list` shows the main folder and `.../ShotVision-exp  f094fd0 [exp/line-crossing]`.

If this plan file is untracked, commit it now:
**Commit:** `Plans: PLAN_3 Phase 1 polish (Part A and Part B)`

### A0.2 Tests (baseline)
Run the test command from rule 6. Record the pass count as `BASE_TESTS`. Expected: all pass, 0 failed. If anything fails, stop and report.

### A0.3 Baseline Gate A report
```bash
mkdir -p experiments/results
.venv/bin/python scripts/evaluate.py --report > experiments/results/plan3_gate_a_before.txt 2>&1; echo "exit=$?"
sed -n '/=== Gate A ===/,$p' experiments/results/plan3_gate_a_before.txt
```
Expected in the `=== Gate A ===` block (these are the 6 Nov numbers):

| Line | Expected |
| --- | --- |
| Makes counted | `158/244 (64.8%)` |
| False makes | `0/85 labeled misses, + 5 spurious makes` |
| `fixed/single` row | `21/22    95.5%    0/6      39.3%` |
| `GATE A (all clips, old definition)` | `FAIL` |
| `GATE A (in scope: fixed camera, single ball)` | `PASS` |
| `STRESS TEST (out of scope)` | `makes 137/222, false makes 5/79` |
| exit code | `0` |

Any mismatch: **stop and report**. The rest of the plan assumes this baseline.

---

## A1. Merge the line-crossing experiment and remove the worktree

### A1.1 Check the branch only adds files
```bash
git diff --name-status stage1/label-tooling...exp/line-crossing
```
Expected: every line starts with `A` (added). Expected files include `experiments/line_crossing_experiment.py`, `tests/test_line_crossing.py` and `experiments/results/line_crossing_2026-11-06.md`. If any line starts with `M`, `D` or `R`: **stop and report**.

### A1.2 Merge
```bash
git merge --no-ff exp/line-crossing -m "Merge exp/line-crossing: line-through-the-rim experiment (PLAN_2)"
```
Expected: merge succeeds with no conflicts. On a conflict: `git merge --abort`, stop and report.

### A1.3 Tests
Run the test command. Expected: all pass, count > `BASE_TESTS` (the experiment adds tests). Record the new count as `TESTS_A1`.

### A1.4 Re-run the experiment with the camera split
```bash
.venv/bin/python experiments/line_crossing_experiment.py \
  --out experiments/results/line_crossing_with_split.md \
  --json experiments/results/line_crossing_with_split.json
```
It must run from cache in seconds. Expected in its summary table, row `SV`: makes `158/244`, false makes `0/85`, spurious makes `5`. These must equal A0.3 exactly. If not, **stop and report**.

Report the full summary table, including the in-scope columns (now filled because `labels.json` has `camera_class`).

### A1.5 Paste the "Docs to add after merge" text
Open `experiments/results/line_crossing_with_split.md` and find the section `## Docs to add after merge`. It holds three pieces of text. Paste each one where it says, **using the numbers from this rerun** (if the text in the section still shows the 6 Nov numbers without in-scope figures, replace only the numbers with the rerun's numbers, nothing else):
- the `docs/PROJECT_LOG.md` entry: add it at the end of the session list, above `## Tools used`;
- the `docs/tracking-research.md` section `0d. Line-through-the-rim side by side`: add it directly after section `0c`;
- the one-line "Proposed, needs agreement: ..." for `CLAUDE.md`: add it as a new bullet directly under the `**Next step:**` bullet. Do not change the existing Next step bullet yet (A8 does that).

Run the test command.
**Commit:** `Docs: line-crossing experiment results after merge, with camera split (PLAN_2 follow-up)`
(Stage: the three docs and `experiments/results/line_crossing_with_split.md`. The `.json` is gitignored, leave it.)

### A1.6 Remove the worktree (keep the branch)
```bash
ls -la ../ShotVision-exp/.venv ../ShotVision-exp/experiments/.cache
```
Expected: both are symlinks (`->`). If either is a real folder, **stop and report** (removing it could delete real data).

```bash
git -C ../ShotVision-exp status --short
```
If it lists `experiments/results/line_crossing_2026-11-06.json` (untracked), move it into the main folder first:
```bash
mv ../ShotVision-exp/experiments/results/line_crossing_2026-11-06.json experiments/results/
```
Run the status command again. Expected: empty. If anything else is listed, **stop and report**.

```bash
git worktree remove ../ShotVision-exp
git worktree list
```
Expected: the worktree is gone from the list; the `exp/line-crossing` branch still exists (`git branch --list exp/line-crossing` prints it). If `git worktree remove` refuses, **stop and report**. Never add `--force`.

No commit for this sub-step.

---

## A2. In-scope gate: require at least 50 misses before PASS

**Why:** the in-scope gate prints PASS on 6 misses. The project's Gate A rule needs 50+ misses. With 6, the honest verdict is "not enough misses to judge".

Edit **only** `scripts/evaluate.py` (function `print_gate_report`, plus `parse_args` and `main`) and `tests/test_gate_report.py`.

### A2.1 Change `print_gate_report`
Current signature: `def print_gate_report(scores, meta, min_make_rate: float = 0.90) -> bool`.

1. Add a keyword parameter: `min_misses: int = 50`. New signature:
   `def print_gate_report(scores: list["ClipScore"], meta: dict[str, dict], min_make_rate: float = 0.90, min_misses: int = 50) -> bool:`
2. Replace **only** the in-scope verdict. Currently:
   ```python
   is_passed = is_false == 0 and is_rate >= min_make_rate
   print(f"GATE A (in scope: fixed camera, single ball): {'PASS' if is_passed else 'FAIL'}")
   ```
   New logic, in this exact order (a false make or a low make rate fails even with few misses, because those are already known):
   ```python
   if is_false > 0 or is_rate < min_make_rate:
       is_verdict, is_passed = "FAIL", False
   elif is_misses < min_misses:
       is_verdict, is_passed = f"NOT ENOUGH MISSES TO JUDGE ({is_misses} < {min_misses})", False
   else:
       is_verdict, is_passed = "PASS", True
   print(f"GATE A (in scope: fixed camera, single ball): {is_verdict}")
   ```
3. Update the docstring's last sentence to: `Returns True only when the in-scope gate passes: 0 false makes, make rate >= min_make_rate and at least min_misses in-scope misses.`
4. Do **not** change the old-definition line, the stress-test line, or anything printed above them.

### A2.2 CLI flag
In `parse_args`, add:
```python
p.add_argument("--min-misses", type=int, default=50,
               help="in-scope Gate A needs at least this many labeled misses to PASS (default 50)")
```
In `main`, change the call `print_gate_report(scores, load_clip_meta())` to `print_gate_report(scores, load_clip_meta(), min_misses=args.min_misses)`. Keep `return 0 if ... else 1` as it is. (If the args variable in `main` has a different name, use that name.)

### A2.3 Tests in `tests/test_gate_report.py`
1. In the existing test `test_in_scope_gate_passes_despite_out_of_scope_false_make`, change the call to pass `min_misses=0` and add this comment on the line above it: `# min_misses=0: this test is about scope, not sample size.` Change nothing else in that test.
2. Check the second existing test (`test_in_scope_gate_fails_on_in_scope_false_make`). It must still pass unchanged (a false make is FAIL whatever the miss count). If it fails, stop and report.
3. Add four tests, reusing the file's `_check` helper. In each, the in-scope clip's meta is `{"camera_class": "fixed", "ball_count": "single"}`:

| Test name | In-scope clip checks | Call | Assert |
| --- | --- | --- | --- |
| `test_not_enough_misses_is_not_a_pass` | 10 × `_check("MAKE","MAKE")` | default `min_misses` | returns `False`; captured stdout contains `NOT ENOUGH MISSES TO JUDGE (0 < 50)` |
| `test_pass_with_enough_misses` | 10 × MAKE→MAKE + 50 × `_check("MISS","MISS")` | default | returns `True`; stdout contains `GATE A (in scope: fixed camera, single ball): PASS` |
| `test_false_make_fails_even_with_few_misses` | 10 × MAKE→MAKE + 1 × `_check("MISS","MAKE")` + 4 × MISS→MISS | default | returns `False`; stdout contains `GATE A (in scope: fixed camera, single ball): FAIL` and not `NOT ENOUGH` |
| `test_low_make_rate_fails_even_with_few_misses` | 8 × MAKE→MAKE + 2 × `_check("MAKE","MISS")` + 3 × MISS→MISS | default | returns `False`; stdout contains `: FAIL` on the in-scope line |

Use pytest's `capsys` fixture to read stdout.

### A2.4 Prove only the verdict line changed
```bash
.venv/bin/python scripts/evaluate.py --report > experiments/results/plan3_gate_a_after_A2.txt 2>&1; echo "exit=$?"
diff experiments/results/plan3_gate_a_before.txt experiments/results/plan3_gate_a_after_A2.txt
```
Expected: exactly one changed line:
```
< GATE A (in scope: fixed camera, single ball): PASS
---
> GATE A (in scope: fixed camera, single ball): NOT ENOUGH MISSES TO JUDGE (6 < 50)
```
and `exit=1` (it was 0). Any other difference: undo your edit (re-open the file and restore the original lines by hand) and report.

Run the test command. Expected: all pass, count = `TESTS_A1` + 4.
**Commit:** `evaluate --report: in-scope Gate A needs >= 50 misses to PASS; prints NOT ENOUGH MISSES TO JUDGE below that`

---

## A3. Review sheets, part 1: the 4 Enosburg makes that match no label

**Why:** in the held-out Enosburg game, the pipeline called 4 makes where there is no label: frames **35060, 125017, 201606, 207518** (from `experiments/results/gate_a_enosburg_heldout.txt`, lines starting `BAD spurious MAKE`). Each is either a real make the labelling missed, or a true false make. The owner will decide by eye. You only build the pictures.

### A3.1 Check tools
```bash
which ffmpeg; ffmpeg -version | head -1
.venv/bin/python -c "import cv2, numpy; print(cv2.__version__)"
```
Record whether ffmpeg exists. It is preferred for seeking in the long `.webm` (290,380 frames).

### A3.2 New script `experiments/review_sheets.py`
Read-only. Never loads the model. Import `load_detections`, `load_labels`, `clip_fps`, `CLIPS_DIR` from `scripts/evaluate.py` the same way `experiments/shot_diagnostics.py` does, and `load_config` from `shotvision.config.settings` (check `shot_diagnostics.py` for the exact import lines and copy that pattern). Detections: `list[list[Detection]]`, one inner list per frame; `Detection` has `class_name`, `conf`, `bbox=(x1,y1,x2,y2)`.

Two subcommands. This step builds `frames`; A4 builds `camera`.

**`frames` subcommand**
```
.venv/bin/python experiments/review_sheets.py frames --clip <clip> --frames F1 F2 ... \
    [--before 1.5] [--after 0.5] [--step 0.1] [--out sample_clips/_review]
```
For each target frame `t`:
1. `fps = clip_fps(path)`. Frame list: from `t - round(before*fps)` to `t + round(after*fps)` inclusive, every `max(1, round(step*fps))` frames. At 60 fps with defaults that is 21 frames.
2. Read each frame. With ffmpeg: `ffmpeg -v error -ss {i/fps:.4f} -i <path> -frames:v 1 -f image2pipe -vcodec png -` and decode the PNG bytes with `cv2.imdecode`. Without ffmpeg: `cv2.VideoCapture`, `set(cv2.CAP_PROP_POS_FRAMES, i)`, `read()`.
3. On each frame draw, from the cached detections for that frame index:
   - every `hoop` detection with `conf >= 0.6`: green rectangle;
   - every `ball` detection with `conf >= 0.3`: orange rectangle plus its conf as text (2 decimals);
   - the frame number, top-left, white text on a black box.
4. Crop each frame around the hoop: take the median centre and width of the highest-confidence hoop box over the window's frames that have one. Crop width = 6 × median hoop width, height = 5 × median hoop width, centred on the median hoop centre, clamped to the image. Resize each crop to 240 px wide. If no hoop is detected anywhere in the window, use the full frame resized to 240 px wide.
5. Tile the crops 7 per row into one image. Add a 40 px header strip with the text: `<clip stem>  target f<t>  pipeline: spurious MAKE  window f<first>-f<last>`.
6. Save `<out>/<clip stem>_f<t>.png`, plus a full-frame view of frame `t` alone resized to 1280 px wide as `<out>/<clip stem>_f<t>_full.jpg` (same boxes drawn).
7. Print, for each target, the labelled shots within ±10 s of `t` from `load_labels(split="all", include_duplicates=True)[clip]`: `start`, `end`, `outcome`, `card`. Also write all of this to `<out>/<clip stem>_targets.json` as `[{"frame": t, "nearby_labels": [...], "sheet": "...png", "full": "...jpg"}]`.

Keep the maths in plain functions (`window_frames(t, fps, before, after, step)`, `crop_box(hoop_boxes, frame_shape)`) and add `tests/test_review_sheets.py` that checks, with no files and no cache:
- `window_frames(600, 60, 1.5, 0.5, 0.1)` returns 21 frames, first 510, last 630, step 6;
- `crop_box` centres on the median hoop and clamps at the image edge (one case inside, one case touching the left edge);
- `crop_box` with an empty hoop list returns the full frame `(0, 0, w, h)`.

### A3.3 Run it
```bash
.venv/bin/python experiments/review_sheets.py frames \
  --clip public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm \
  --frames 35060 125017 201606 207518
git check-ignore -q sample_clips/_review && echo "ignored: ok"
```
Expected: 4 `.png` sheets, 4 `_full.jpg` files and 1 `_targets.json` in `sample_clips/_review/`, and `ignored: ok` (`sample_clips/*` is in `.gitignore`, so the images are never committed).

### A3.4 Seek check (important)
Open each of the 4 `.png` sheets with your file-reading tool and look at them. You are checking **one thing only**: in tiles where a green hoop box is drawn, does it sit on the basketball hoop in the picture?
- Yes in all sheets: write `Expected: green boxes on the hoop | Got: on the hoop | Match: yes`.
- If boxes are clearly offset from the hoop in any sheet, the frame seek is wrong. If you used `cv2` seeking, switch to ffmpeg (if available) and rerun. If boxes are still offset, **stop and report**.

Do not describe whether the ball went in. Rule 4.

Run the test command.
**Commit:** `experiments/review_sheets.py: review sheets for unlabelled pipeline makes (frames subcommand)`

---

## A4. Review sheets, part 2: are the 5 "moving" GitHub clips really moving?

**Why:** `experiments/camera_profile.py` tags a clip "moving" when the detected hoop box moves. Five GitHub clips came out "moving", but the measurement may be reacting to the detector jumping between boxes, not the camera moving. If the owner re-tags some as fixed, the in-scope test set grows.

Clips: `video_test_5.mp4`, `aggie_NathanBBall.mov`, `lf_alan.mp4`, `artur_vid29.mp4`, `kyle_test_video.mp4`. For comparison, also `lf_back.mp4` (measured fixed).

### A4.1 Add the `camera` subcommand to `experiments/review_sheets.py`
```
.venv/bin/python experiments/review_sheets.py camera --clips <clip> ... [--out sample_clips/_review]
```
For each clip:
1. From cached detections, for every frame with a `hoop` detection `conf >= 0.6`, take the highest-confidence one: centre `(cx, cy)`, width `w`. Medians `med_cx, med_cy, med_w`. Per frame: `dx = (cx - med_cx)/med_w`, `dy = (cy - med_cy)/med_w`, `s = w/med_w`.
2. **Track plot** (draw with cv2 only, no matplotlib): a 1200×360 white image with three lines over frame index: `dx` (blue), `dy` (red), `s - 1` (green). Draw horizontal reference lines at -0.5, 0 and +0.5 hoop widths, and label them. Frames with no hoop leave a gap.
3. **Spread frames:** 8 full frames at evenly spaced frame indices across the clip, each with **all** hoop detections `conf >= 0.6` drawn (green) and the highest one thicker, frame number top-left. Resize each to 400 px wide.
4. **Jump frames:** the 4 frames with the largest `hypot(dx, dy)`, drawn the same way, plus their `hypot(dx, dy)` value as text.
5. Stack into one image: header (clip name and the measured `hoop_move_p95`, `hoop_size_ratio` from `labels.json` → `camera_profile`), track plot, then the 8 spread frames (4 per row), then the 4 jump frames. Save `<out>/camera_<clip stem>.png`.
6. Print one row per clip: `clip`, `frames_with_hoop`, `share_with_2plus_hoops` (share of frames with 2 or more hoop detections `conf >= 0.6`), `max_jump` (largest `hypot(dx, dy)`), and the current `camera_class`. This is printed evidence for the owner only. **Do not use it to set any tag.**

Add to `tests/test_review_sheets.py`: a fake detection list where the hoop sits still except one frame with a second, far-away hoop box of higher confidence. Check that `share_with_2plus_hoops` is `1/N` and that the jump frame list includes that frame.

### A4.2 Run it
```bash
.venv/bin/python experiments/review_sheets.py camera --clips \
  video_test_5.mp4 aggie_NathanBBall.mov lf_alan.mp4 artur_vid29.mp4 kyle_test_video.mp4 lf_back.mp4
```
Expected: 6 `camera_*.png` files in `sample_clips/_review/`. Report the printed table.

Open each sheet and check only that it rendered (track plot visible, frames visible, boxes drawn). Do not decide fixed or moving. Rule 4.

Run the test command.
**Commit:** `experiments/review_sheets.py: camera subcommand (hoop track plot, spread and jump frames)`

---

## A5. Phone video rotation

**Why:** phones often store portrait video as landscape pixels plus a "rotate 90" flag. If OpenCV ignores the flag, the pipeline sees the court sideways. Future footage will likely be phone video.

Owner-approved exception: you may edit `shotvision/capture/source.py` and `tests/test_source.py`, only as described here.

### A5.1 Check OpenCV support
```bash
.venv/bin/python -c "import cv2; print(cv2.__version__, hasattr(cv2,'CAP_PROP_ORIENTATION_AUTO'), hasattr(cv2,'CAP_PROP_ORIENTATION_META'))"
```
Expected: both `True`. If either is `False`, **stop and report** (a different approach needs the owner's decision).

### A5.2 Audit the existing clips (nothing may change for them)
Write and run a short inline script (do not save it as a file) that, for every clip key in `sample_clips/labels.json` → `clips`, opens `sample_clips/<clip>` with `cv2.VideoCapture`, reads `CAP_PROP_ORIENTATION_META` and `CAP_PROP_ORIENTATION_AUTO`, reads one frame, and prints `clip, meta, auto, frame.shape`.
Expected: `meta` is `0` for every clip. If any clip has a non-zero `meta`, **stop and report**: changing rotation handling would change its frames compared with the cached detections.

### A5.3 Build a rotated test clip and observe current behaviour
Only if ffmpeg exists (A3.1). In a temp folder (`mktemp -d`), write a 64×48 test clip with cv2 the same way `tests/test_source.py::_write_test_clip` does, then try, in order, until `CAP_PROP_ORIENTATION_META` reads 90 or 270 on the output:
```bash
ffmpeg -v error -display_rotation 90 -i in.mp4 -c copy out.mp4
ffmpeg -v error -i in.mp4 -c copy -metadata:s:v:0 rotate=90 out.mp4
```
Record which command worked, and what frame shape `cv2.VideoCapture("out.mp4").read()` returns **before** your code change (shows whether OpenCV already auto-rotates by default).
If neither command sets the flag, note it and skip the rotated-clip test in A5.5 (implement the code change anyway, and flag "rotation unverified" in the report).

### A5.4 Code change in `shotvision/capture/source.py`
In `FrameSource.__init__`, directly after the `if not self._cap.isOpened(): raise ...` block, add:
```python
        # Phones store portrait video as landscape pixels plus a rotation flag.
        # Ask OpenCV to apply the flag so the pipeline always sees the picture upright.
        if self.type != DEVICE and hasattr(cv2, "CAP_PROP_ORIENTATION_AUTO"):
            self._cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1)
```
Add a property after `fps`:
```python
    @property
    def rotation(self) -> int:
        """Rotation flag stored in the file, in degrees (0 when absent or unsupported)."""
        if not hasattr(cv2, "CAP_PROP_ORIENTATION_META"):
            return 0
        meta = self._cap.get(cv2.CAP_PROP_ORIENTATION_META)
        return int(meta) if meta and meta > 0 else 0
```
Nothing else in the file changes.

### A5.5 Tests in `tests/test_source.py`
Add (do not change existing tests):
1. `test_normal_clip_reports_no_rotation(tmp_path)`: write a clip with `_write_test_clip`, open with `FrameSource`, assert `rotation == 0` and the first frame shape is `(48, 64, 3)`.
2. `test_rotated_clip_is_read_upright(tmp_path)`: create the rotated clip with whichever ffmpeg command worked in A5.3 (via `subprocess.run`). Decorate with `@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")`, and inside, if the produced file's `CAP_PROP_ORIENTATION_META` is not 90 or 270, call `pytest.skip("ffmpeg could not set a rotation flag")`. Assert `FrameSource(...).rotation in (90, 270)` and the first frame shape is `(64, 48, 3)` (portrait).

### A5.6 Prove nothing else changed
```bash
.venv/bin/python scripts/evaluate.py --report > experiments/results/plan3_gate_a_after_A5.txt 2>&1
diff experiments/results/plan3_gate_a_after_A2.txt experiments/results/plan3_gate_a_after_A5.txt && echo "identical"
```
Expected: `identical`.

Run the test command. Expected: all pass (the rotated test may show as skipped; say so).
**Commit:** `capture: apply phone rotation metadata for file and URL sources; FrameSource.rotation; tests`

---

## A6. Live-check script (the owner runs it, you never do)

**Why:** Gate C needs the pipeline to run live and give the same counts as the recorded version. Nothing measures that yet.

### A6.1 New script `experiments/live_check.py`
```
.venv/bin/python experiments/live_check.py --source <file|device index|url> \
    [--seconds N] [--results-out <path.json>] [--compare-to-replay]
```
Behaviour:
1. Build the pipeline exactly as `shotvision/main.py` `run()` does (read that function and use the same classes, arguments and order: `resolve_device`, `Detector`, `FrameSource`, `BallTracker`, `RimTracker`, `ShotStateMachine`, `StatsTracker`, `to_frames`). **Headless:** no `cv2.namedWindow`, `imshow`, `waitKey` or `Hud`. Do not import from `shotvision.main` and do not edit it; copy the loop logic into this script.
2. All model loading happens inside a function called from `main()`. Importing the module must not load anything heavy.
3. Stop when the source is exhausted, or after `--seconds` of wall time if given.
4. Measure: frames processed, wall time, **processing fps** (frames ÷ wall seconds), source fps, and per-frame latency (time from `source.read()` returning to the state-machine update finishing) p50 and p95 in milliseconds.
5. Collect every resolved shot as `{"frame_idx", "outcome", "reason"}`.
6. Print a summary block:
   ```
   === Live check ===
   source: ...   source fps: ...   processing fps: ...   real time: YES|NO (processing fps >= source fps)
   latency ms p50: ...  p95: ...
   shots: N  makes: M  misses: K
   ```
7. `--results-out` writes the summary and the shot list as JSON.
8. `--compare-to-replay` (file sources only; for other sources print `compare skipped: not a file` and continue): load the cached detections for the same clip with `load_detections`, run `replay(dets, config, fps=fps)` from `scripts/evaluate.py`, and compare the two shot lists with `compare_results(live, replayed, tol_frames=to_frames(0.2, fps))`. Print each pairing and a verdict line `COMPARE: SAME` or `COMPARE: DIFFERENT (<n> unmatched)`.

`compare_results(live, replayed, tol_frames)` is a plain function. It pairs each live shot with the closest unpaired replay shot with the same outcome within `tol_frames`, and returns `(pairs, live_only, replay_only)`.

### A6.2 Tests `tests/test_live_check.py`
No model, no files, no cache:
- importing `experiments/live_check.py` does not import `ultralytics` (check `"ultralytics" not in sys.modules` after import, removing it first if a previous test imported it);
- `compare_results` on identical lists returns no unmatched shots;
- a shot 3 frames apart with `tol_frames=12` pairs; 20 frames apart does not;
- a MAKE in one list and a MISS at the same frame in the other do not pair.

Use `ShotResult`, `ShotOutcome` from `shotvision.shot_logic.state_machine`.

### A6.3 Do not run it
Do not run `experiments/live_check.py`, not even `--help` if that would import the model (it should not, but don't test it). The owner's commands go in the decisions file (A7).

Run the test command.
**Commit:** `experiments/live_check.py: headless live run with processing fps, latency and compare-to-replay (owner runs it)`

---

## A7. Decisions file for the owner

Create `docs/plans/PLAN_3_decisions.md` with exactly this structure. Fill every `<...>` from your outputs. Leave the **Owner** columns empty.

````markdown
# PLAN_3 decisions (owner fills this in, then runs Part B)

Review images are in `sample_clips/_review/` (open in Finder). Fill every Owner cell. Part B refuses to start while any Owner cell is empty.

## 1. Enosburg: pipeline makes with no label

Sheets: `hazen_girls_v_enosburg_2025-12-12_f<frame>.png` (and `_full.jpg`). Choose one:
- `REAL_MAKE`: the ball went through the rim; the labelling missed it. Also give the label's start and end frames (start = ball's final approach, end = ball clear below the net; frame numbers are printed on each tile).
- `FALSE_MAKE`: the ball did not go through the rim. The pipeline made a false make.
- `CANT_TELL`: the frames don't show it clearly.

| Frame | Nearby labels (±10 s) | Owner: call | Owner: start | Owner: end | Owner: note |
| --- | --- | --- | --- | --- | --- |
| 35060 | <from _targets.json> | | | | |
| 125017 | <...> | | | | |
| 201606 | <...> | | | | |
| 207518 | <...> | | | | |

## 2. Camera tags

Sheets: `camera_<clip>.png`. `lf_back` is a known fixed camera, for comparison. Choose `fixed` (the camera doesn't move; any box movement is the detector jumping) or `moving` (the camera pans, zooms or shakes).

| Clip | Current tag | hoop_move_p95 | hoop_size_ratio | 2+ hoops share | Owner: tag | Owner: reason |
| --- | --- | --- | --- | --- | --- | --- |
| video_test_5.mp4 | moving | <...> | <...> | <...> | | |
| aggie_NathanBBall.mov | moving | <...> | <...> | <...> | | |
| lf_alan.mp4 | moving | <...> | <...> | <...> | | |
| artur_vid29.mp4 | moving | <...> | <...> | <...> | | |
| kyle_test_video.mp4 | moving | <...> | <...> | <...> | | |

## 3. Live check (owner runs these on the Mac, then pastes the output)

These load the model, which is why the agent didn't run them.

```bash
# a) recorded clip, compared with the cached replay. Expect COMPARE: SAME
.venv/bin/python experiments/live_check.py --source sample_clips/lf_shot_detection.mp4 --compare-to-replay --results-out experiments/results/live_check_file.json

# b) live camera for 60 s (phone as webcam, or laptop camera pointed at a screen playing a clip)
.venv/bin/python experiments/live_check.py --source 0 --seconds 60 --results-out experiments/results/live_check_camera.json
```

Owner: paste the `=== Live check ===` block of (a):

```
```

Owner: paste the `=== Live check ===` block of (b):

```
```

Owner: anything else Part B should know (or "none"):
````

**Commit:** `Plans: PLAN_3 decisions file for the owner`

---

## A8. Docs, push, report, STOP

1. **`CLAUDE.md`**, "Current phase" block:
   - Replace the Gate A bullet's ending `0 false makes in 6 misses. PASS.` with `0 false makes in 6 misses. The in-scope gate needs at least 50 misses, so it reports NOT ENOUGH MISSES TO JUDGE.`
   - Replace the first line `**Current phase: Phase 1, make/miss. In-scope Gate A passes; out-of-scope footage is a stress test.**` with `**Current phase: Phase 1, make/miss. In-scope results look good (21/22 makes, 0 false makes) but rest on only 6 misses; out-of-scope footage is a stress test.**`
   - Replace the `**Next step:**` bullet with `- **Next step:** owner fills docs/plans/PLAN_3_decisions.md (review sheets in sample_clips/_review/, live check commands), then PLAN_3 Part B. The real blocker remains: 50+ fixed-camera misses.` Keep the "Proposed, needs agreement" bullet from A1.5 under it.
   - In the **Tests** bullet, update the counts to the current numbers from your last test run.
2. **`docs/ROADMAP.md`**: in the status line near the top (it starts `Status (2026-11-06):`), replace `0 false makes in 6 misses, PASS.` with `0 false makes in 6 misses. The in-scope gate needs at least 50 misses before it can pass, so it currently reports NOT ENOUGH MISSES TO JUDGE.` Change nothing else.
3. **`docs/tracking-research.md`**: add a section directly after `0d`: `### 0e. Phase 1 polish (PLAN_3 Part A, <date>)` with: one sentence on the 50-miss rule and the new verdict line; the A4 printed table; one sentence saying review sheets and a live check exist and the owner's decisions are pending. No verdicts on the sheets.
4. **`docs/PROJECT_LOG.md`**: add a dated entry above `## Tools used`: `### <date> — PLAN_3 Part A: gate minimum, review sheets, rotation, live check` with what was done (one line per step A1 to A7) and the commit hashes.

Run the test command.
**Commit:** `Docs: PLAN_3 Part A (in-scope gate needs 50 misses, review sheets, rotation, live check)`

```bash
git status --short     # must be empty (ignored files don't show)
git push origin stage1/label-tooling
```

**Final report** in the runner prompt's 7-part format, plus a section **"Owner: what to do now"**:
1. Open `sample_clips/_review/` and look at the 4 Enosburg sheets and the 6 camera sheets.
2. Fill in `docs/plans/PLAN_3_decisions.md`, including the two live-check outputs.
3. Commit it (`git add docs/plans/PLAN_3_decisions.md && git commit -m "PLAN_3 decisions filled in"`), then start a new session with Part B.

## **STOP HERE. Do not start Part B.**

---

# PART B (only after the owner has filled in the decisions file)

## B0. Pre-flight

1. Create the run log `experiments/results/RUN_LOG_PLAN_3_B_<date>.md`.
2. `git checkout stage1/label-tooling`, `git pull`, `git status --short` (expected: empty), `git log --oneline -5`.
3. Open `docs/plans/PLAN_3_decisions.md`. Check every Owner cell:
   - Section 1: each row's call is `REAL_MAKE`, `FALSE_MAKE` or `CANT_TELL`. Every `REAL_MAKE` row has an integer start and end, with `start < end` and `start <= frame <= end + 60`.
   - Section 2: each row's tag is `fixed` or `moving`, with a reason.
   - Section 3: both pasted blocks are present, or the owner wrote why not.
   Any empty or invalid cell: **stop and list them**. Don't guess.
4. Run the test command. Record the count. All must pass.
5. Run the report and check it matches A8's state:
   ```bash
   .venv/bin/python scripts/evaluate.py --report > experiments/results/plan3_gate_a_before_B.txt 2>&1
   ```
   Expected: same Gate A block as `plan3_gate_a_after_A5.txt` (`diff` shows nothing). If it differs, stop and report.

## B1. Record the owner's decisions in the run log
Copy both decision tables into the run log verbatim. Count `K` = number of `REAL_MAKE` rows. Count `R` = number of clips the owner re-tagged (Owner tag differs from Current tag).

## B2. Apply camera tags
Python read-modify-write on `sample_clips/labels.json` (preserve key order; write with `json.dump(data, f, indent=2, ensure_ascii=False)` and a trailing newline). For each clip in section 2:
- set `"camera_class"` to the Owner tag (even if unchanged);
- add `"camera_class_source": "manual <YYYY-MM-DD>: <owner's reason>"` directly after `"camera_class"`;
- leave `"ball_count"` and `"camera_profile"` unchanged.

Check that no shot changed:
```bash
.venv/bin/python - <<'EOF'
import json, subprocess
old = json.loads(subprocess.check_output(["git", "show", "HEAD:sample_clips/labels.json"]))
new = json.load(open("sample_clips/labels.json"))
for clip, e in old["clips"].items():
    assert e.get("shots") == new["clips"][clip].get("shots"), clip
print("shots unchanged")
EOF
```
Expected: `shots unchanged`.

Re-score:
```bash
.venv/bin/python scripts/evaluate.py --report > experiments/results/plan3_gate_a_after_B2.txt 2>&1
sed -n '/=== Gate A ===/,$p' experiments/results/plan3_gate_a_after_B2.txt
```
Expected (re-tagging only regroups clips):
- `Makes counted` line: `158/244 (64.8%)`, unchanged.
- `False makes` line: `0/85 labeled misses, + 5 spurious makes`, unchanged.
- If `R = 0`, the whole block is identical to B0.5.
- If `R > 0`, only the camera-class rows, the in-scope verdict line and the stress-test line may differ.

Report the camera-class table and the three gate lines.

Run the test command.
**Commit:** `labels.json: owner-reviewed camera tags for 5 GitHub clips (PLAN_3)`

## B3. Apply Enosburg decisions
Only for `REAL_MAKE` rows. If `K = 0`, write "no labels added" in the run log and go to B4.

Clip key: `public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm`. For each `REAL_MAKE` row, **append** to that clip's `shots` list:
```json
{"start": <owner start>, "end": <owner end>, "outcome": "MAKE", "note": "added in PLAN_3 review by the owner: <owner note>"}
```
Then sort that clip's `shots` list by `start` (stable sort, so existing entries keep their order relative to each other). Do not add a `card` field. Do not add, change or remove anything for `FALSE_MAKE` or `CANT_TELL` rows.

Check that every old shot is still present and identical:
```bash
.venv/bin/python - <<'EOF'
import json, subprocess
old = json.loads(subprocess.check_output(["git", "show", "HEAD:sample_clips/labels.json"]))
new = json.load(open("sample_clips/labels.json"))
for clip, e in old["clips"].items():
    o, n = e.get("shots", []), new["clips"][clip].get("shots", [])
    for s in o:
        assert s in n, (clip, s)
    print(clip, "old", len(o), "new", len(n))
EOF
```
Expected: only the Enosburg clip's count grows, by exactly `K`.

Re-score:
```bash
.venv/bin/python scripts/evaluate.py --report > experiments/results/plan3_gate_a_after_B3.txt 2>&1
sed -n '/=== Gate A ===/,$p' experiments/results/plan3_gate_a_after_B3.txt
```
Expected, compared with B2:
- `Makes counted`: `(158 + K)/(244 + K)`;
- spurious makes: `5 - K`;
- labeled misses: still `0/85`.

If the new labels did not absorb the spurious makes (makes counted did not rise by `K`, or spurious did not fall by `K`), the owner's start/end frames don't line up with the pipeline's result frame. **Stop and report** each affected row with its frames. Don't adjust the frames yourself.

Run the test command.
**Commit:** `labels.json: <K> Enosburg makes added after owner review (PLAN_3)` (skip the commit if `K = 0`)

## B4. Final numbers
```bash
.venv/bin/python scripts/evaluate.py --report > experiments/results/plan3_gate_a_final.txt 2>&1; echo "exit=$?"
sed -n '/=== Gate A ===/,$p' experiments/results/plan3_gate_a_final.txt
```
Report the whole block. Then answer, from the output only:
1. In-scope (fixed/single): makes counted / makes, false makes / misses, 95% upper bound, and the verdict line.
2. How many more in-scope misses are needed to reach 50?
3. Enosburg: how many of the 4 were real makes, false makes, can't tell? (from the decisions file). How many false makes does the stress test now show?
4. Live check: from the owner's pasted blocks, was (a) `COMPARE: SAME`? Was processing fps at or above source fps in (a) and (b)? Copy the numbers.

## B5. Docs
1. **`docs/PROJECT_LOG.md`**: dated entry above `## Tools used`: `### <date> — PLAN_3 Part B: owner review applied`, with the decisions summary, the B4 numbers and the commit hashes.
2. **`docs/tracking-research.md`**: append to section `0e` a short "Owner review results" paragraph and the B4 camera-class table.
3. **`CLAUDE.md`**: update the "Current phase" numbers to B4's, and set the Next step bullet to: `- **Next step:** get 50+ fixed-camera misses (licensed fixed-camera shooting footage or the owner's own filming, spec in HANDOVER.md section 12). Phase 2 groundwork (release moment) may start as experiments only.` If live check (a) was not `SAME`, instead set it to: `- **Next step:** investigate why the live run differs from the cached replay (PLAN_3 B4).`
4. **`docs/ROADMAP.md`**: update only the numbers in the status line near the top.
5. If a `HANDOVER.md` exists in the repo root, update its "Headline numbers" table. If not, do nothing.

Run the test command.
**Commit:** `Docs: PLAN_3 Part B results (owner review applied)`

## B6. Push, report, STOP
```bash
git status --short     # must be empty
git push origin stage1/label-tooling
```
Final report in the runner prompt's 7-part format, including the B4 block and the four answers.

## **STOP HERE.** Do not start Phase 2 or any other work.
