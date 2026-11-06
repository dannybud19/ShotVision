# PLAN 1: Split the Gate A score by camera type, and score the held-out game

Repo: ShotVision (`https://github.com/dannybud19/ShotVision`), branch `stage1/label-tooling`.
Written: 6 Nov 2026. This plan runs **in parallel** with `PLAN_2_line_crossing_experiment.md`. PLAN_2 runs in a separate worktree (`../ShotVision-exp`, branch `exp/line-crossing`) and only creates new files. Work only in this repo folder, on `stage1/label-tooling`. Don't touch the other worktree or branch, and don't create or edit `experiments/line_crossing_experiment.py` or `tests/test_line_crossing.py`.

---

## 0. Read this first (rules for the agent)

You are working in an existing, tested Python project. Follow these rules exactly. If a rule and a step conflict, the rule wins. Stop and report instead of guessing.

1. **Do not change anything under `shotvision/`.** That is the tested pipeline. This plan only touches `scripts/evaluate.py`, `sample_clips/labels.json`, a new file in `experiments/`, tests and docs.
2. **Do not change how any shot is scored.** Matching, slack windows, thresholds and config in `shotvision/config/default.json` stay exactly as they are. You are only adding new ways to *group* the existing results.
3. **Do not load the model.** Never pass `--recollect`. Every clip in this plan already has cached detections in `experiments/.cache/detections/*.fd4cd3dc7f.pkl`. If a command tries to load `models/basketball_best.pt` (you will see Ultralytics/torch loading output, or it takes more than about a minute per clip), stop it and report. Loading that file needs the owner's approval.
4. **Do not tune anything to make a gate pass.** If a number looks bad, report it. Do not change thresholds, labels or code to improve it.
5. **Keep every test passing.** Run the test command in step 1.3 before you start and before every commit.
6. **One commit per step** where the step says "Commit". Use the message given. End every commit message with a blank line and then `Co-Authored-By:` whatever your tool normally adds, if any.
7. **Writing style for docs:** UK spelling, no em dashes (use commas, full stops or brackets), short sentences, tables for comparisons.
8. **Python:** always use `.venv/bin/python` from the repo root.
9. When the plan says **"Report"**, paste the exact command output (or the relevant lines) into your final summary. Never paraphrase numbers.

---

## 1. Pre-flight checks

### 1.1 Branch and tree
```bash
git checkout stage1/label-tooling
git status
git log --oneline -3
```
Expected:
- Branch `stage1/label-tooling`. The latest commit is normally `labels: Hazen v Enosburg (held out from the tracker fix), ...`, which the owner commits before starting both plans. The one before it is `0376cfb Bandits 03 labeled ...`.
- A clean working tree.

If the Enosburg labels are still uncommitted (`sample_clips/labels.json` shows as modified), that's acceptable. Step 2 commits them. If there are any other uncommitted changes, **stop and report**. Don't discard anything.

### 1.2 Cache check
```bash
ls experiments/.cache/detections/ | grep fd4cd3dc7f
```
Every clip in `sample_clips/labels.json` must have a matching `<clip stem>.fd4cd3dc7f.pkl`, including `hazen_girls_v_enosburg_2025-12-12.fd4cd3dc7f.pkl`. If one is missing, stop and report which.

### 1.3 Tests (baseline)
```bash
.venv/bin/python -m pytest -q \
  --deselect tests/test_detector.py::test_detector_loads_real_basketball_checkpoint_and_predicts \
  --deselect tests/test_ball_tracker.py::test_update_runs_end_to_end_on_blank_frame
```
Record the pass count. Every test must pass. If any fail before you change anything, stop and report.

### 1.4 Reproduce the last known Gate A numbers
The Enosburg labels are already in `labels.json` (uncommitted), so a plain `--report` now includes that game. To reproduce the last committed result, exclude it:

```bash
.venv/bin/python scripts/evaluate.py --report --clips \
  chonyy_one_score_one_miss.mp4 chonyy_two_score_three_miss.mp4 video_test_5.mp4 \
  chonyy_sample_video.mp4 lf_shot_detection.mp4 lf_back.mp4 lf_alan.mp4 artur_vid29.mp4 \
  kyle_test_video.mp4 aggie_NathanBBall.mov \
  public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm \
  public/commons_bandits/bandits_practice_01.webm \
  public/commons_bandits/bandits_practice_02.webm \
  public/commons_bandits/bandits_practice_03.webm \
  > experiments/results/gate_a_before_split.txt 2>&1
```
(Create `experiments/results/` first with `mkdir -p experiments/results`.)

Expected in the `=== Gate A ===` block: **Makes counted 132/193**, **0 false makes on labeled misses**, **1 spurious make**, `GATE A: FAIL`.

If the numbers differ, **stop and report the difference**. Something has changed since 5 Nov and the rest of this plan would be measuring the wrong thing.

---

## 2. Commit the held-out Enosburg labels (unchanged)

**If `git log -1` already shows the Enosburg labels commit, skip items 2 to 4 below.** Just do item 1 (the check) and item 3 (SOURCES.md). If SOURCES.md needs a row, commit it as `SOURCES: Hazen v Enosburg provenance`.

The labels for `public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm` were made by Claude subagents from contact sheets. They have **not** been checked by a human. The clip was deliberately kept out of development of the 5 Nov tracker fix, so it is the only honest check of that fix.

1. Check the entry is well formed:
   ```bash
   .venv/bin/python -c "import json; d=json.load(open('sample_clips/labels.json')); e=d['clips']['public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm']; from collections import Counter; print(e['split'], e['source']['group'], Counter(s['outcome'] for s in e['shots']))"
   ```
   Expected: `dev commons:hardwick_game_HELDOUT_for_tracker_fix Counter({'MAKE': 51, 'MISS': 28, 'IGNORE': 19})` (counts may differ slightly; report what you see).
2. Do **not** edit any label.
3. Check `sample_clips/SOURCES.md` lists this file with its licence (CC BY 4.0, Hardwick Community Television). If it is missing, add a row in the same format as the Lyndon game row.
4. **Commit:** `labels: Hazen v Enosburg (held out from the tracker fix), Claude-labeled, not human-verified`

---

## 3. Score the held-out game on its own

```bash
.venv/bin/python scripts/evaluate.py --report -v \
  --clips public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm \
  > experiments/results/gate_a_enosburg_heldout.txt 2>&1
```

**Report:** the `=== Gate A ===` block and the `SUMMARY` line.

Then run the per-shot diagnostics on the same clip and save them:
```bash
.venv/bin/python experiments/shot_diagnostics.py --cache-only \
  > experiments/results/diagnostics_enosburg_heldout.txt 2>&1
```
(If `shot_diagnostics.py` has no option to restrict clips, it runs on all; that is fine. Check its `--help` first.)

**Important:** if this clip shows any false make, list each one with clip, label card number and frame number. Do not try to fix it. That goes in the report for the owner.

Do not commit the `experiments/results/*.txt` files unless they are small (under about 200 KB each). If they are larger, add `experiments/results/*.txt` to `.gitignore` and mention it.

---

## 4. Measure each clip's camera, objectively

Gate A is meant to test Phase 1's target setup: **one fixed camera, one shooter, one ball**. The public footage mixes that with a panning broadcast camera and crowded multi-ball practices. We want to tag every clip so the report can show the in-scope number separately. Tag clips from measurements, not from guesses.

### 4.1 New script: `experiments/camera_profile.py`

Write a read-only script that loads the cached detections for each labeled clip (reuse `load_labels`, `load_detections`, `clip_fps` and `CLIPS_DIR` from `scripts/evaluate.py` the same way `experiments/shot_diagnostics.py` imports them) and prints one row per clip with these measurements.

Each cached file is a `list[list[Detection]]`, one inner list per frame. `Detection` has `class_name` (`'ball'`, `'hoop'`, `'person'` or a raw name), `conf` and `bbox = (x1, y1, x2, y2)`.

| Column | How to compute |
| --- | --- |
| `frames` | number of frames |
| `fps` | `clip_fps(path)` |
| `hoop_seen` | share of frames with at least one `hoop` detection with `conf >= 0.6` (the config `model.rim_conf`) |
| `hoop_move_p95` | For frames where a hoop is seen, take the single highest-confidence hoop box. Compute its centre and width. Let `med_cx, med_cy, med_w` be the medians over the clip. For each such frame, displacement = `hypot(cx - med_cx, cy - med_cy) / med_w`. Report the 95th percentile. Units are hoop widths. |
| `hoop_size_ratio` | 95th percentile of `w / med_w` divided by 5th percentile of `w / med_w` (zoom indicator) |
| `multi_ball` | share of frames with **2 or more** `ball` detections with `conf >= 0.5` whose centres are more than 2 ball-widths apart |

Arguments: `--clips` (optional list, same as evaluate.py) and `--json <path>` to also write the rows as JSON. Print a fixed-width table to stdout.

Add a small test file `tests/test_camera_profile.py` that builds a fake detection list in memory (no cache, no model) and checks:
- a hoop that never moves gives `hoop_move_p95 == 0`;
- a hoop that jumps by one hoop width in half the frames gives a value close to 1;
- two well-separated confident balls in every frame give `multi_ball == 1.0`.

Put the maths in plain functions that take the detection list so they can be tested without files.

### 4.2 Run it
```bash
.venv/bin/python experiments/camera_profile.py --json experiments/results/camera_profile.json
```
**Report** the full table.

### 4.3 Propose a class for each clip

Use these rules. They are starting points, so apply them literally and flag borderline clips rather than adjusting the thresholds.

| Field | Value | Rule |
| --- | --- | --- |
| `camera_class` | `fixed` | `hoop_move_p95 < 0.5` **and** `hoop_size_ratio < 1.3` |
| | `moving` | otherwise |
| `ball_count` | `single` | `multi_ball < 0.05` |
| | `multi` | otherwise |

A clip is **in scope** for Phase 1 when `camera_class == "fixed"` and `ball_count == "single"`.

Flag as **borderline** any clip within 20% of a threshold (for example `hoop_move_p95` between 0.4 and 0.6). List borderline clips separately in your report so the owner can look at them.

Sanity check against what we already know (from `labels.json` source notes and the research doc):
- `hazen_girls_v_lyndon` and `hazen_girls_v_enosburg` are a panning, zooming broadcast camera. They should come out `moving`.
- The Bandits practices are "floor level, handheld-ish" with several balls. They should come out `multi`, and probably `moving`.
- The 11 GitHub clips are mostly phone cameras on a tripod or on the ground with one shooter. Most should be `fixed`/`single`.

If the measurements disagree with any of these, **do not override the measurement**. Report it as a disagreement.

### 4.4 Write the classes into `labels.json`

For every clip entry under `"clips"`, add two clip-level keys next to `"split"`: `"camera_class"` and `"ball_count"`, plus `"camera_profile"` holding the measured numbers (rounded to 3 decimals). Do this with a short Python read-modify-write that preserves the existing key order and uses `json.dump(..., indent=2, ensure_ascii=False)` followed by a trailing newline. Then run:
```bash
git diff --stat sample_clips/labels.json
```
Only additions should appear. No label (`start`, `end`, `outcome`, `miss_type`, `note`) may change. Check with:
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

**Commit:** `Camera profile: measured hoop motion, zoom and multi-ball per clip; camera_class/ball_count in labels.json`

---

## 5. Add the split to the Gate A report

Edit **only** `scripts/evaluate.py`, and only the reporting part.

### 5.1 What to add

In `print_gate_report`, after the existing "By source" section, add:

1. **"By camera class"** table: rows `fixed/single`, `fixed/multi`, `moving/single`, `moving/multi`, `unclassified`. Columns: makes counted / makes, make rate %, false makes (labeled + spurious) / misses, 95% upper bound (use the existing `binomial_upper_bound`).
2. **Two gate lines** at the end, replacing nothing:
   - `GATE A (in scope: fixed camera, single ball): PASS|FAIL` using the same rule as now (0 false makes and make rate >= 90%) on in-scope clips only.
   - `STRESS TEST (out of scope): makes x/y, false makes a/b` with no pass/fail.
3. Keep the existing `GATE A: PASS|FAIL` line exactly as it is, renamed in the printout to `GATE A (all clips, old definition): ...` so old and new can be compared. The **return value** of `print_gate_report` should become the in-scope result. Make sure the exit code stays 0 for pass and 1 for fail.

Spurious makes must be attributed to the clip they came from (the current code already does `by_group[g][3] += 1` for these; do the same for camera class).

Read `camera_class` and `ball_count` from the clip meta returned by `load_clip_meta()`. If a clip has no class, put it under `unclassified` and **do not** count it as in scope.

### 5.2 Prove nothing else changed
Run the step 1.4 command again into `experiments/results/gate_a_after_split.txt`, then:
```bash
diff experiments/results/gate_a_before_split.txt experiments/results/gate_a_after_split.txt
```
The only differences allowed are the new sections and the renamed gate line. Every per-clip line, the SUMMARY line and every existing number must be identical. If anything else differs, undo and report.

### 5.3 Test
Add a test in a new file `tests/test_gate_report.py` that builds two fake `ClipScore` objects (one in scope, one out of scope) with hand-made `ShotCheck`s and `ShotResult`s (import `ShotResult`, `ShotOutcome` from `shotvision.shot_logic.state_machine`) and checks that:
- the in-scope gate passes when the in-scope clip has 10/10 makes counted and 0 false makes, even if the out-of-scope clip has a false make;
- the in-scope gate fails when the in-scope clip has a false make.

Capture stdout with `capsys` if you need to check printed lines.

Run the full test command from 1.3. All must pass.

**Commit:** `evaluate --report: Gate A split by camera class; in-scope gate (fixed, single ball) plus out-of-scope stress test`

---

## 6. Run the full report with everything included

```bash
.venv/bin/python scripts/evaluate.py --report > experiments/results/gate_a_split_full.txt 2>&1
```
This now includes the Enosburg game. **Report** the whole `=== Gate A ===` block.

Then answer these questions in the final report, using numbers from the output only:

1. What is the in-scope make rate and false-make count? How far is it from 90% and 0?
2. How many in-scope **misses** are there? Give the 95% upper bound. (If it's under 30 misses, say plainly that the false-make rate cannot be shown to be low yet.)
3. Which in-scope clips lose makes, and by which exit reason?
4. Did the held-out Enosburg game behave like the Lyndon game (same camera), better or worse?

---

## 7. Update the docs

All in UK English, no em dashes.

1. **`docs/PROJECT_LOG.md`**: add two dated entries at the end of the session list (above "Tools used"):
   - **2026-11-05 (later): tracker fix and Bandits 03.** Summarise from the commit messages of `5670a1e` and `0376cfb` (`git show --stat 5670a1e 0376cfb`). Key numbers: makes 90 to 107 of 137, false makes 2 to 0, legacy 56/63 unchanged, then with Bandits 03: 132/193, 0/57 labeled misses scored MAKE, 1 spurious make (ball in front of the hoop, depth case).
   - **Today's date: camera split and held-out game.** What was done in this plan and the numbers from steps 3 and 6.
2. **`CLAUDE.md`**: the "Current phase" block still says the tracker fix is the next step. It is done. Update it to the latest numbers, describe the new in-scope gate in one line, and set "Next step" to: `Line-crossing side-by-side experiment (PLAN_2).`
3. **`docs/ROADMAP.md`**: in the Phase 1 gate description, write that Gate A is judged on in-scope clips (fixed camera, single ball), and out-of-scope clips are tracked as a stress test without pass/fail. Do not change any other phase.
4. **`docs/tracking-research.md`**: add a short section `0c. Split by camera class (date)` with the table from step 6.
5. If a file named `HANDOVER.md` exists in the repo root, update its "Current status" table with the new numbers. If it does not exist, do nothing.

**Commit:** `Docs: 5 Nov tracker fix log, camera split, held-out Enosburg result`

---

## 8. Finish

1. Run the tests from 1.3 one last time.
2. `git status` must be clean (apart from ignored files).
3. `git push origin stage1/label-tooling`.
4. Final report to the owner, in this order:
   - Commits made (hash and message).
   - The step 1.4 reproduction result (matched or not).
   - The Enosburg held-out Gate A block.
   - The camera profile table, the class given to each clip, and any borderline or disagreeing clips.
   - The full Gate A block from step 6 and the answers to the four questions.
   - Anything you were unsure about or skipped, and why.

Stop there. Do **not** merge `exp/line-crossing` or touch PLAN_2's work. The owner merges both.
