# PLAN 4: Tidy-up, live frame rate, and a still-camera shot count

Repo: ShotVision (`https://github.com/dannybud19/ShotVision`), main folder `~/Desktop/ShotVision`, branch `stage1/label-tooling`.
Written: 13 Nov 2026, for Sonnet 5.5 running with `docs/plans/PROMPT_for_plan_runner.md`.
One part, no owner stop in the middle. Ends with a final report. **STOP after step 7.**

| Step | What | Edits |
| --- | --- | --- |
| 1 | Pre-flight | none |
| 2 | Report crash when a lost make has no reason | `scripts/evaluate.py`, `tests/test_gate_report.py` |
| 3 | Replace the test-only guard in `FrameSource` | `shotvision/capture/source.py`, one existing test helper in `tests/test_source.py` |
| 4 | Measure a live camera's real frame rate | `shotvision/capture/source.py`, `shotvision/main.py`, `experiments/live_check.py`, tests |
| 5 | Count labelled shots taken while the camera was still (report only) | new `experiments/shot_camera_stillness.py`, new test |
| 6 | Add `HANDOVER.md`, fix stale docs | docs only |
| 7 | Push, report, STOP | none |

---

## Runner prompt session notes (owner: paste under "## The plan for this session")

```text
Run: docs/plans/PLAN_4_tidy_and_still_shots.md (steps 1 to 7). Stop after step 7.

Folder and branch: the main repo folder ~/Desktop/ShotVision on stage1/label-tooling. Ignore the runner prompt's first paragraph about PLAN_1/PLAN_2 folders. No parallel plan, no worktree.

Owner-approved exceptions to the runner prompt's hard rules, for this session only. Nothing else is relaxed:
1. Step 3 edits shotvision/capture/source.py and the FakeCap helper in tests/test_source.py exactly as described.
2. Step 4 edits shotvision/capture/source.py, shotvision/main.py and experiments/live_check.py exactly as described.
3. Step 2 edits scripts/evaluate.py (reporting only).

Never run shotvision/main.py, experiments/live_check.py, or anything that loads models/basketball_best.pt. Cached detections only. The owner runs the live check afterwards.

Effort: high for steps 4 and 5, medium for the rest.

Begin with "Before you do anything" from the runner prompt: read the files and write the summary, then wait for my go-ahead.
```

---

## 0. Rules (read before every commit)

1. **Never load the model.** Never pass `--recollect`. Never run `shotvision/main.py`, `experiments/live_check.py`, `scripts/render_overlay.py` or `scripts/diagnose_shots.py`. If anything prints Ultralytics/torch loading output, stop it and report.
2. **Never change how a shot is scored.** No threshold, config value, matching rule or slack window changes. `shotvision/config/default.json` is never touched. No label in `sample_clips/labels.json` changes in this plan (it is not edited at all).
3. **Edit only the files each step names**, only as described. No refactors, renames or formatting changes. Ideas go under "Suggestions (not done)".
4. **Tests pass before every commit.** Test command:
   ```bash
   .venv/bin/python -m pytest -q \
     --deselect tests/test_detector.py::test_detector_loads_real_basketball_checkpoint_and_predicts \
     --deselect tests/test_ball_tracker.py::test_update_runs_end_to_end_on_blank_frame
   ```
5. **Commit only where the plan says**, with the message given.
6. **Python:** `.venv/bin/python` from the repo root. Never `pip install`. ffmpeg is installed.
7. **No destructive git** (`reset --hard`, `checkout -- <file>`, `clean`, `push --force`, `branch -D`).
8. **Numbers:** copy from command output. Never round differently.
9. **Docs style:** UK spelling, no em dashes, short sentences, tables for comparisons.
10. **Run log:** `experiments/results/RUN_LOG_PLAN_4_<YYYY-MM-DD>.md`. After each step append the step id, commands, `Expected: ... | Got: ... | Match: yes/no` lines and files changed. Commit the run log with the step 6 docs commit.

---

## 1. Pre-flight

### 1.1 Branch and tree
```bash
git checkout stage1/label-tooling
git pull --ff-only
git status --short
git log --oneline -3
```
Expected: latest commit `c2e1916 Docs: PLAN_3 Part B results (owner review applied)` or later. `git status --short` empty, **or** only these untracked files the owner added before this session: `?? docs/plans/PLAN_4_tidy_and_still_shots.md` and `?? HANDOVER.md`. Anything else: stop and report. If `git pull --ff-only` fails, stop and report.

If the two files are untracked, commit them now:
**Commit:** `Plans: PLAN_4 (tidy-up, live frame rate, still-camera shot count) and HANDOVER.md`

### 1.2 Tests
Run the test command. Expected: `165 passed, 2 deselected`. Record as `BASE_TESTS`. If any fail, stop.

### 1.3 Baseline report
```bash
mkdir -p experiments/results
.venv/bin/python scripts/evaluate.py --report > experiments/results/plan4_gate_a_before.txt 2>&1; echo "exit=$?"
sed -n '/=== Gate A ===/,$p' experiments/results/plan4_gate_a_before.txt
```
Expected:

| Line | Expected |
| --- | --- |
| Makes counted | `162/248 (65.3%)` |
| False makes | `0/85 labeled misses, + 1 spurious makes` |
| `fixed/single` row | `55/60    91.7%    0/8` (95% UB `31.2%`) |
| in-scope verdict | `NOT ENOUGH MISSES TO JUDGE (8 < 50)` |
| `STRESS TEST (out of scope)` | `makes 107/188, false makes 1/77` |
| exit code | `1` |

Any mismatch: stop and report.

---

## 2. Report crash when a lost make has no reason

**Bug (found in PLAN_3):** in `print_gate_report` (`scripts/evaluate.py`), this line crashes with `'NoneType' object has no attribute 'value'` if a lost make's result exists but its `reason` is `None`:
```python
reasons["make lost: " + (c.result.reason.value if c.result else "never armed")] += 1
```
Real pipeline results always carry a reason, so the scoreboard never hits it, but test fakes and future code can.

### 2.1 Fix
Replace that one line with:
```python
if c.result is None:
    why = "never armed"
elif c.result.reason is None:
    why = "no reason recorded"
else:
    why = c.result.reason.value
reasons["make lost: " + why] += 1
```
Keep the indentation of the surrounding `else:` block. Nothing else changes.

### 2.2 Test
In `tests/test_gate_report.py`, add `test_lost_make_without_reason_does_not_crash`: one in-scope clip (`{"camera_class": "fixed", "ball_count": "single"}`) with one `ShotCheck(label={"outcome": "MAKE", "start": 0, "end": 10}, result=ShotResult(outcome=ShotOutcome.MISS, frame_idx=0))` (no `reason` passed). Call `print_gate_report(..., min_misses=0)` with `capsys` and assert stdout contains `make lost: no reason recorded`.

If PLAN_3's `_lost_make()` helper in that file now duplicates what this test needs, leave the helper exactly as it is. Don't refactor.

### 2.3 Check
```bash
.venv/bin/python scripts/evaluate.py --report > experiments/results/plan4_gate_a_after_2.txt 2>&1
diff experiments/results/plan4_gate_a_before.txt experiments/results/plan4_gate_a_after_2.txt && echo identical
```
Expected: `identical`.

Run the tests. Expected: `BASE_TESTS + 1` passed.
**Commit:** `evaluate --report: don't crash when a lost make has no reason`

---

## 3. Replace the test-only guard in `FrameSource`

**Why:** in PLAN_3, Sonnet added `hasattr(self._cap, "set")` to the rotation guard in `shotvision/capture/source.py`, only because a test's fake camera (`FakeCap` in `tests/test_source.py`) had no `set()` method. Production code shouldn't carry a check that exists only for a test.

### 3.1 Read first
Open `shotvision/capture/source.py`. Find the rotation block added in PLAN_3. It should look like:
```python
if self.type != DEVICE and hasattr(cv2, "CAP_PROP_ORIENTATION_AUTO") and hasattr(self._cap, "set"):
    self._cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1)
```
(the exact layout may differ). Open `tests/test_source.py` and find the `FakeCap` class used by `test_source_key_distinguishes_device_and_url`. Write both in the run log. If either doesn't match this description, stop and report.

### 3.2 Change
- In `source.py`, remove only `and hasattr(self._cap, "set")` from that condition. Nothing else.
- In `FakeCap`, add:
  ```python
  def set(self, prop, value):
      return True
  ```
  This is the only change to an existing test file in this step.

Run the tests. Expected: `BASE_TESTS + 1` passed (same as after step 2).
**Commit:** `capture: drop the test-only hasattr guard; FakeCap gets set()`

---

## 4. Measure a live camera's real frame rate

**Why (measured by the owner in PLAN_3):** the laptop webcam reported 15 fps through `CAP_PROP_FPS` but delivered about 29 frames per second. Shot-logic timings are in seconds and are converted to frames with the reported rate, so on that camera every time window (occlusion grace, timeouts) was about half as long as intended. Recorded files report their rate correctly, so this only affects device sources.

### 4.1 `FrameSource.measure_fps` in `shotvision/capture/source.py`
Add `import time` at the top if it isn't there. Add this method to `FrameSource`, after the `fps` property:
```python
    def measure_fps(self, seconds: float = 2.0, clock=time.monotonic) -> float:
        """Read and discard frames for about `seconds` and return the real
        delivery rate. For live devices, whose reported CAP_PROP_FPS can be
        wrong. The first frame is not counted (cameras often stall on start)."""
        first = self.read()
        if first is None:
            return self.fps
        start = clock()
        frames = 0
        while clock() - start < seconds:
            if self.read() is None:
                break
            frames += 1
        elapsed = clock() - start
        return frames / elapsed if frames > 0 and elapsed > 0 else self.fps
```
Nothing else in the file changes.

### 4.2 Use it in `shotvision/main.py`
In `run()`, the current line is:
```python
fps = config.camera.fps or source.fps
print(f"[ShotVision] Timing at {fps:.2f} fps.")
```
Replace it with:
```python
if config.camera.fps:
    fps = config.camera.fps
elif source.type == "device":
    fps = source.measure_fps()
    print(f"[ShotVision] Camera reports {source.fps:.2f} fps, measured {fps:.2f} fps; using measured.")
else:
    fps = source.fps
print(f"[ShotVision] Timing at {fps:.2f} fps.")
```
Nothing else in `main.py` changes.

### 4.3 Same in `experiments/live_check.py`
Find the equivalent `fps = config.camera.fps or source.fps` line in `run_live` and replace it with the same block (use the script's own print style if it prints differently; keep the message text). Also:
- add `"reported_fps": source.fps` next to `"source_fps"` in the summary dict;
- make `"source_fps"` hold the `fps` value actually used;
- in the printed summary, after `source fps: ...`, print `(reported ...)` only when the two differ by more than 0.5.

Read the function first and adapt the variable names to what is there. If the structure differs so much that this can't be done without restructuring the function, stop and report.

### 4.4 Tests
In `tests/test_source.py`, add (no real camera, no files):
- `test_measure_fps_uses_delivered_rate`: build a `FrameSource`-like object without opening a real capture. The simplest way: create a `FrameSource` on a tiny test clip (as other tests do), then replace `source.read` with a function that always returns a small numpy frame, and pass a fake clock that advances by 1/30 s on every call. Assert `measure_fps(seconds=1.0, clock=fake)` is within 1.0 of 30.
- `test_measure_fps_falls_back_when_no_frames`: replace `source.read` with a function returning `None`. Assert the result equals `source.fps`.

In `tests/test_main.py`, check how existing tests exercise `run()`. If there's no practical way to test the new branch without a camera or the model, don't add a main.py test; write that in the run log.

### 4.5 Check
Run the evaluation and diff against step 2's output. Expected: identical (the replay never goes through `main.py`).
Run the tests. Expected: all pass. Record the count.
**Commit:** `Live sources: measure the camera's real frame rate instead of trusting CAP_PROP_FPS (main and live_check)`

Do not run the live check. The owner reruns it afterwards (see step 7).

---

## 5. Count labelled shots taken while the camera was still (report only)

**Why:** Phase 1 is blocked on fixed-camera misses (8 of the 50 needed). The two Hardwick broadcast games are tagged "moving" as a whole, but broadcast cameras often hold still for a few seconds, for example during free throws. A miss filmed while the camera was still is closer to the target setup. This step only **counts** them and shows how ShotVision scored them. It changes no tag, label or gate. The owner decides afterwards whether this is a fair way to grow the in-scope set.

### 5.1 New script `experiments/shot_camera_stillness.py`
Read-only. Imports `load_labels`, `load_detections`, `clip_fps`, `CLIPS_DIR`, `replay`, `score_clip`, `load_clip_meta` from `scripts/evaluate.py` the way `experiments/shot_diagnostics.py` does, plus `load_config` and `to_frames`. Reuse `hoop_metrics`-style maths from `experiments/camera_profile.py` by importing its functions if they take a detection list (read that file first). If they don't fit a sub-window, write a small function that does the same maths on a slice. Don't edit `camera_profile.py`.

For every clip in `load_labels(split="all", include_duplicates=False)`, and every labelled shot with outcome `MAKE` or `MISS`:
1. Window = frames `start - to_frames(1.0, fps)` to `end + to_frames(0.5, fps)`, clamped to the clip.
2. On the cached detections in that window, compute, with the same definitions and confidence (`0.6`) as `camera_profile.py`:
   - `hoop_seen`: share of window frames with a hoop;
   - `move_p95`: 95th percentile hoop-centre displacement from the window's median, in median hoop widths;
   - `size_ratio`: 95th / 5th percentile of hoop width over the window's median.
3. Shot is **still** when `hoop_seen >= 0.8` **and** `move_p95 < 0.5` **and** `size_ratio < 1.3` (the clip-level thresholds, applied per shot). Otherwise **not still**.
4. Score the clip once with the same call the `--report` path uses (`replay` then `score_clip` with the same arguments `scripts/evaluate.py` `main` passes; read `main` and copy them), and record for each shot whether ShotVision counted it correctly (MAKE counted, or MISS not called MAKE).

Print and write (`--out experiments/results/shot_camera_stillness.md`, `--json experiments/results/shot_camera_stillness.json`):
- **Table A, per camera class of the clip** (from `labels.json`): makes still / total, misses still / total.
- **Table B, still shots only, by clip:** makes counted / still makes, false makes / still misses.
- **Table C, still misses by miss type:** count, false makes.
- **Headline line:** `Still-camera misses outside fixed/single clips: N (false makes: F)` and `If counted in scope: in-scope misses would be 8 + N = M`.
- A list of every still miss (clip, label start, end, `miss_type`, `card` if present, how ShotVision resolved it), sorted by clip and frame, so the owner can spot-check them with `experiments/review_sheets.py frames`.

`--clips` optional, as in `evaluate.py`.

### 5.2 Test `tests/test_shot_camera_stillness.py`
Fake detections in memory (no cache, no model):
- a hoop fixed in every frame → the shot is still;
- a hoop that moves by 1 hoop width every other frame → not still;
- a hoop seen in only half the window → not still (`hoop_seen` rule).

### 5.3 Run it
```bash
.venv/bin/python experiments/shot_camera_stillness.py --out experiments/results/shot_camera_stillness.md --json experiments/results/shot_camera_stillness.json
```
Expected sanity checks (stop if any fail):
- Every shot in clips tagged `fixed/single` should be still, or close to it. Report how many are not, by clip. Don't change any threshold to make this pass; just report it.
- Total labelled makes in Table A = `248`, total labelled misses = `85` (the same totals as the scoreboard).

Report Tables A to C, the headline lines and the still-miss list.

Run the tests.
**Commit:** `experiments/shot_camera_stillness.py: count labelled shots taken while the camera was still (report only)`
(The `.md` results file is committed; the `.json` is gitignored.)

---

## 6. `HANDOVER.md` and stale docs

1. `HANDOVER.md` in the repo root was supplied by the owner (committed in 1.1). Update only its section 3 "Where things stand" numbers if steps 2 to 5 changed any (they shouldn't change the scoreboard). Add one line to its section 10 with the step 5 headline. Nothing else.
2. **`CLAUDE.md`**:
   - The **Next step** bullet points to "HANDOVER.md section 12". That now exists, so leave the pointer.
   - Replace the stale "Proposed, needs agreement" bullet (it mentions "after PLAN_1's labels land") with: `- **Proposed, needs agreement:** count still-camera shots from out-of-scope clips towards the in-scope misses (step 5 of PLAN_4 measured N of them). Owner decides.` Put the real N in.
   - Add one bullet under the pipeline section: `- **Live sources:** the frame rate is measured over 2 s at start-up (CAP_PROP_FPS can be wrong on webcams); files use their reported rate.`
   - Update the test count.
3. **`docs/PROJECT_LOG.md`**: dated entry above `## Tools used`: `### <date>: PLAN_4: tidy-up, live frame rate, still-camera shot count`, one line per step, with commit hashes and the step 5 headline.
4. **`docs/tracking-research.md`**: add `### 0f. Still-camera shots inside moving-camera clips (<date>)` after `0e`, with Tables A to C and the headline lines. No recommendation beyond "owner decides".

Run the tests.
**Commit:** `Docs: PLAN_4 (live frame rate, still-camera shot count), HANDOVER.md updated`
(Include the run log.)

---

## 7. Push, report, STOP

```bash
git status --short     # must be empty
git push origin stage1/label-tooling
```

Final report in the runner prompt's 7-part format, plus **"Owner: what to do now"**:
1. Rerun the live camera check:
   ```bash
   .venv/bin/python experiments/live_check.py --source 0 --seconds 60 --results-out experiments/results/live_check_camera.json
   ```
   Expected: a line `Camera reports ... fps, measured ... fps; using measured.` and a `source fps` close to 30.
2. Read the step 5 still-miss list and decide whether still-camera shots from broadcast clips should count towards the in-scope set.

## **STOP HERE.**