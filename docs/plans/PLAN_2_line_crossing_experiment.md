# PLAN 2: Side-by-side experiment, ShotVision vs the "line through the rim" method

Repo: ShotVision (`https://github.com/dannybud19/ShotVision`).
Written: 6 Nov 2026.

**This plan runs in parallel with `PLAN_1_score_split.md`**, in its own git worktree on its own branch, `exp/line-crossing`. That folder is a sibling of the main repo, normally `../ShotVision-exp`. The owner sets the worktree up before you start (section 9 has the setup and merge steps). Inside it:
- `.venv`, `experiments/.cache` and the video files are symlinks to the main repo. Don't delete or replace them.
- `labels.json` already contains the committed Enosburg labels. It will **not** have the `camera_class` / `ball_count` fields that PLAN_1 adds. That's expected. Your script must read those fields if they exist and otherwise report clips as "unclassified". After both plans are merged, the owner reruns your script once to get the in-scope split.

To avoid merge conflicts, this plan **only creates new files**. It edits no existing file.

---

## 0. Read this first (rules for the agent)

1. **This is an experiment, and it only creates new files.** Don't edit any existing file: nothing under `shotvision/` or `scripts/`, no `labels.json`, no `.gitignore`, and none of `CLAUDE.md`, `docs/*` or `README.md`. PLAN_1 is editing several of those at the same time, and any edit here would cause a merge conflict. Your new files go in `experiments/` and `tests/`.
1b. Work only in the `exp/line-crossing` worktree. Never switch branches, never touch `stage1/label-tooling`, and never `cd` into the main repo folder.
2. **Do not load the model.** Use only the cached detections in `experiments/.cache/detections/*.fd4cd3dc7f.pkl`. Never pass `--recollect`. If anything starts loading `models/basketball_best.pt`, stop and report.
3. **Do not copy code from the avishah3 repository.** It has no licence, so its code can't be reused. Implement the method from the description in section 2 of this plan only. Do not fetch or open that repo's source.
4. **Do not tune.** Run exactly the variants in section 3 with exactly the numbers given. Do not add variants, sweep parameters or change labels to improve a result. If you think another variant is worth trying, write it in the report as a suggestion.
5. **False makes matter more than makes.** A variant that counts more makes but adds even one false make is not "better". Report it honestly either way.
6. **Keep every test passing:**
   ```bash
   .venv/bin/python -m pytest -q \
     --deselect tests/test_detector.py::test_detector_loads_real_basketball_checkpoint_and_predicts \
     --deselect tests/test_ball_tracker.py::test_update_runs_end_to_end_on_blank_frame
   ```
7. Docs: UK spelling, no em dashes, tables for comparisons.
8. Always use `.venv/bin/python` from the repo root. Paste exact numbers from output into the report. Never paraphrase.

---

## 1. Background (why we are doing this)

ShotVision scores a make when the ball's path, fitted over a short window, crosses the scoring line inside the inner rim gate and the whole ball is then seen below. Most lost makes are cases where **the ball is invisible for 7 to 25 frames at the rim** (motion blur over the backboard, or hidden in the net). ShotVision gives up after an occlusion grace (`occlusion_grace_s` 0.4 s, `rim_occlusion_grace_s` 0.8 s) and resolves a miss (`MISS_OCCLUSION_GAP`), or it never arms the shot at all.

The public repo `avishah3/AI-Basketball-Shot-Detection-Tracker` (the source of our `basketball_best.pt` and of the `video_test_5.mp4` clip) uses a simpler rule. It takes **the last ball point above the rim and the first point below it**, draws a straight line between them, and calls a make if the line crosses rim height inside the rim. It doesn't care how many frames are missing between the two points. That could rescue our invisible-at-the-rim makes, but it could also create false makes.

**Question this experiment answers:** using our labels and our cached detections, how many makes does that method count, how many misses does it call makes, and does a limited "rescue" version on top of ShotVision help without adding false makes?

---

## 2. The method to implement (specification)

Implement in a new file `experiments/line_crossing_experiment.py`. Credit the idea in the module docstring: "Method idea from avishah3/AI-Basketball-Shot-Detection-Tracker (no licence; reimplemented from a description, no code copied)."

All coordinates are image pixels, **y increases downward**. Convert every frame count to the clip's fps with `to_frames(seconds, fps)` from `shotvision.config.settings` (the original was written for 30 fps; the seconds below are the 30 fps values converted).

### 2.1 Inputs per frame
From the cached `list[list[Detection]]` (`Detection.class_name`, `.conf`, `.bbox = (x1, y1, x2, y2)`):
- centre `(cx, cy) = ((x1+x2)/2, (y1+y2)/2)`, width `w = x2-x1`, height `h = y2-y1`.

### 2.2 Hoop history
- Each frame, take the **highest-confidence** detection with `class_name == "hoop"` and `conf > 0.5`, if any. Append `(cx, cy, w, h, frame_idx)` to `hoop_pos`.
- Clean after each append (only if `len(hoop_pos) > 1`), comparing the newest entry (2) with the one before (1):
  - if the centre moved more than `0.5 * hypot(w1, h1)` **and** the frame difference is under `to_frames(0.1667, fps)`, remove the newest entry;
  - separately (not else), if `w2 * 1.3 < h2` or `h2 * 1.3 < w2`, remove the newest entry if it is still there;
  - keep at most the last 25 entries.
- "Current hoop" = `hoop_pos[-1]`. Until there is one, do nothing else for that frame.

### 2.3 Ball history
- Ball candidates this frame: `class_name == "ball"` and (`conf > 0.3`, or `conf > 0.15` **and** the centre is in the hoop region).
- Hoop region (relative to current hoop `hx, hy, hw, hh`): `hx - hw < cx < hx + hw` and `hy - hh < cy < hy + 0.5*hh`.
- Which candidates are appended depends on the variant (section 3): **all of them** in detection order, or **only the highest-confidence one**.
- Append `(cx, cy, w, h, frame_idx)` to `ball_pos`.
- Clean after each append (only if `len(ball_pos) > 1`), comparing newest (2) with previous (1):
  - if the centre moved more than `4 * hypot(w1, h1)` **and** the frame difference is under `to_frames(0.1667, fps)`, remove the newest;
  - else if `w2 * 1.4 < h2` or `h2 * 1.4 < w2`, remove the newest.
- Age limit: if `frame_idx - ball_pos[0].frame > to_frames(1.0, fps)`, remove the oldest entry (one entry per frame at most, like the original).

### 2.4 Shot start and end
Using the current hoop:
- **Up:** newest ball point satisfies `hx - 4*hw < cx < hx + 4*hw` and `hy - 2*hh < cy < hy - 0.5*hh`. When true and not already up, set `up = True`, `up_frame = that point's frame`.
- **Down:** only checked while `up` is true. Newest ball point has `cy > hy + 0.5*hh`. Set `down = True`, `down_frame = that point's frame`.
- **Check:** every `to_frames(0.3333, fps)` frames (use `frame_idx % step == 0`), if `up and down and up_frame < down_frame`: score the shot (2.5), record a result, then reset `up = down = False`.

### 2.5 Scoring
- `rim_line = hy - 0.5*hh` (top of the hoop box).
- Walk `ball_pos` backwards and find the **latest** index `i` with `cy < rim_line`. If there is no such point, or no point after it, the result is MISS.
- Points: `A = ball_pos[i]` (last above) and `B = ball_pos[i+1]` (first after it, should be below).
- **Line method:** fit `y = m*x + b` through A and B. If `abs(Bx - Ax) < 1e-6`, `predicted_x = Ax`. Otherwise `predicted_x = (rim_line - b) / m`. If `m == 0`, MISS.
- **Rim bounds:** `left = hx - 0.4*hw`, `right = hx + 0.4*hw`.
- **Make zone** depends on the variant: `left - 10 < predicted_x < right + 10` (the original's fixed 10 pixel allowance) or `left < predicted_x < right` (strict).
- Record a `ShotResult(outcome=ShotOutcome.MAKE or MISS, frame_idx=down_frame)`. Use `down_frame` (when the ball was first seen below), not the check frame, so it lines up with the labels. Import `ShotResult`, `ShotOutcome` from `shotvision.shot_logic.state_machine`.
- For diagnostics, also keep per shot: `up_frame`, `down_frame`, `A`, `B`, `gap_frames = B.frame - A.frame`, `predicted_x` expressed in hoop widths from centre `(predicted_x - hx) / hw`, and which method decided it.

### 2.6 Gap limit (used by some variants)
If `gap_frames > to_frames(0.5, fps)`, the shot is MISS regardless of the line. Record the reason `gap_too_long`.

### 2.7 Arc method (used by some variants)
Replaces the straight line in 2.5:
- Take every point in `ball_pos` with `cy < rim_line` whose frame is within `to_frames(0.5, fps)` before `A.frame` (A included), plus B.
- If fewer than 3 points, fall back to the line method and record `arc_fallback`.
- Fit `x(t)` as a straight line in frame index `t` (`np.polyfit(t, x, 1)`), and `y(t)` as a quadratic (`np.polyfit(t, y, 2)`, giving `a, b, c`).
- If `a <= 0` (the curve isn't falling the way gravity makes it in image coordinates), fall back to the line method and record `arc_fallback`.
- Solve `a*t^2 + b*t + c = rim_line`. Take the smallest real root with `t > A.frame`. If there is none, MISS.
- If that root is more than `to_frames(0.5, fps)` after `A.frame`, MISS (`gap_too_long`).
- `predicted_x = x(root)`, then apply the make zone as in 2.5.

---

## 3. Variants to run (exactly these)

Each variant changes one thing from the one before, so the effect of each change is visible.

| ID | Ball points kept | Gap limit (2.6) | Crossing method | Make zone |
| --- | --- | --- | --- | --- |
| **SV** | ShotVision as is (from `scripts/evaluate.py` `replay`) | | | |
| **L0** | all candidates (faithful) | no | line | ±10 px |
| **L1** | highest-confidence only | no | line | ±10 px |
| **L2** | highest-confidence only | yes | line | ±10 px |
| **L3** | highest-confidence only | yes | line | strict |
| **L4** | highest-confidence only | yes | arc (2.7) | strict |

Then two **hybrids** that keep ShotVision and only use the line method as a rescue:

| ID | Rule |
| --- | --- |
| **H1** | Start from SV's results. For every SV result with reason `MISS_OCCLUSION_GAP` or `MISS_TIMEOUT_OCCLUDED`, look for an **L3** shot whose `down_frame` is within `to_frames(1.0, fps)` of the SV result's `frame_idx`. If that L3 shot is MAKE, change the SV result to MAKE (keep SV's `frame_idx`). Otherwise leave it. |
| **H2** | H1, plus: every **L3** MAKE that has **no** SV result within `to_frames(1.0, fps)` of its `down_frame` is added as a new MAKE result (this targets makes SV never armed). |
| **H3** | Same as H2 but using **L4** instead of L3. |

Record for each hybrid how many results were changed (H1 to H3) and added (H2, H3).

---

## 4. Scoring the variants

Reuse the existing scorer so the numbers are directly comparable with Gate A:

- Load labels with `load_labels(split="all", include_duplicates=False)` (duplicates excluded, exactly as `--report` does).
- For each clip: `fps = clip_fps(path)`, `dets = load_detections(path, config)` with `config = load_config()`.
- Run `sv = replay(dets, config, fps=fps)` once. Its `frames` list is reused for every variant so `score_clip` can compute smoothness (smoothness doesn't matter here; ignore it).
- For each variant, build `Replay(frames=sv.frames, results=<that variant's ShotResult list sorted by frame_idx>)` and call `score_clip(clip, labels[clip], rep, 0.6, to_frames(0.2, fps), fps)`.
- Then call `print_gate_report(scores, load_clip_meta())` per variant, capturing stdout, so you get the same Gate A block for every variant. (If PLAN_1 has been done, that block includes the camera-class split and the in-scope gate.)

Also produce your own summary table with these columns per variant:

| Column | Meaning |
| --- | --- |
| makes counted / makes | all clips |
| false makes / misses | labeled misses scored MAKE |
| spurious makes | MAKE results matched to no label (outside IGNORE windows) |
| 95% upper bound | `binomial_upper_bound(false + spurious, misses)` |
| in-scope makes counted | clips with `camera_class == "fixed"` and `ball_count == "single"` |
| in-scope false + spurious makes | same clips |
| legacy GitHub clips | makes counted / 63-ish and false makes, for comparison with the known 56/63 and 0 |

### 4.1 Sanity checks (do these before trusting any numbers)
1. **Before writing any code**, run `.venv/bin/python scripts/evaluate.py --report > experiments/results/line_crossing_sv_baseline.txt 2>&1` in this worktree. It should load from the cache in seconds and never load the model. Write down its `=== Gate A ===` numbers. Then **SV in your script must reproduce those numbers exactly** (makes counted, false makes, spurious makes). If it doesn't, stop and report. The harness is wrong. (For reference, without the Enosburg game the last known result was 132/193 makes, 0/57 labeled misses scored MAKE and 1 spurious make. With Enosburg included the totals will be higher, so don't expect those exact numbers.)
2. **Hand-check on `video_test_5.mp4`.** This is the avishah3 repo's own demo clip. L0 should count most of its 30 makes. If L0 counts fewer than 20, something in your implementation is likely wrong. Print the per-shot diagnostics for that clip and check the geometry before going further. Don't change the specification to raise the number. Look for a bug.
3. Print, for L0 on `video_test_5.mp4`, the first 5 shots' `up_frame`, `down_frame`, `gap_frames` and `predicted_x` in hoop widths. Include them in the report.

---

## 5. Tests

New file `tests/test_line_crossing.py`. Build synthetic detections in memory (a list of frames, each a list of `Detection` objects). No cache, no model, no video files. Use a fixed hoop box, e.g. centre (500, 300), width 60, height 50, conf 0.9, in every frame, and fps 30.

Required tests:
1. **Clean make:** ball (20×20 box, conf 0.9) falls straight down through x = 500 from y = 150 to y = 420, one point per frame. L1 returns exactly one MAKE.
2. **Clear miss to the side:** same fall at x = 600. L1 returns one MISS.
3. **Gap rescue:** same as test 1, but delete the frames where y is between 250 and 380. L1 still returns MAKE (the line crosses the gap).
4. **Gap limit:** same as test 3, but the gap lasts 0.8 s (24 frames at 30 fps, holding the ball invisible). L2 returns MISS with reason `gap_too_long`.
5. **Arc:** a parabola `y = 150 + 0*t + 2.0*t^2` style path whose descending branch crosses `rim_line` at x ≈ 500, with 6 frames missing just above and below the rim (under 0.5 s). L4 returns MAKE. The same path shifted so it crosses at x = 540 (inside ±10 px but outside strict) returns MISS for L4 and MAKE for L2.
6. **Faithful vs one ball:** add a second confident ball sitting still at (200, 450) in every frame. Check that L1 still scores test 1 as MAKE, and record (don't assert) what L0 does. Write in a comment what you observed.
7. **Hybrid H1:** construct a fake SV result list with one `ShotResult(MISS, frame_idx=k, reason=ResolutionReason.MISS_OCCLUSION_GAP)` and an L3 MAKE near it. Check H1 turns it into MAKE. A `MISS_RIM_OUT_SIDEWAYS` SV result must **not** change.

Put the core logic in plain functions (`run_line_method(dets, fps, variant) -> (results, diagnostics)`, `apply_hybrid(sv_results, line_results, line_diag, fps, add_new) -> results`) so they can be tested directly.

Run the full test command from section 0. All tests must pass.

---

## 6. Run it

```bash
mkdir -p experiments/results
.venv/bin/python experiments/line_crossing_experiment.py \
  --out experiments/results/line_crossing_$(date +%Y-%m-%d).md \
  --json experiments/results/line_crossing_$(date +%Y-%m-%d).json
```

The script should:
- print the summary table (section 4) to stdout;
- write a Markdown report to `--out` containing the summary table, each variant's Gate A block, and the lists in section 7;
- write every per-shot diagnostic to `--json`.

Add `--clips` (optional, same meaning as `evaluate.py`) for quick runs on one clip.

---

## 7. What the report must contain

1. The summary table for SV, L0 to L4 and H1 to H3.
2. **Every false make and spurious make**, for every variant, as a table: variant, clip, label card number (`card` field in the label, if present), label frames, result frame, `gap_frames`, `predicted_x` in hoop widths, and miss type. Sort by clip and frame so the owner can open the clip at that frame and look.
3. **Every make a variant gained over SV** (counted by the variant, lost by SV), with SV's exit reason for that make (from `sv.results` or "never armed").
4. **Every make a variant lost compared with SV.**
5. For L2 to L4, how many shots were decided by `gap_too_long` and `arc_fallback`.
6. A short plain-English conclusion. Answer these, using only the numbers:
   - Does the line method count makes that ShotVision loses because the ball is invisible at the rim?
   - What does it cost in false makes, and on which kinds of footage (in scope vs out of scope)?
   - Does the gap limit or the arc remove those false makes, and how many rescued makes does that cost?
   - Is H1, H2 or H3 at **0 false makes in scope** while counting more in-scope makes than SV? If yes, say which and by how much. If no, say so.
7. A "Suggested next step" paragraph. This is a suggestion for the owner only. **Do not implement it.** Changing the pipeline needs the owner's agreement.

---

## 8. Finish (no doc edits)

1. **Don't edit any doc.** Instead, at the end of the Markdown results file, add a section `## Docs to add after merge` holding the exact text for:
   - a `docs/PROJECT_LOG.md` entry (what was run, the summary table, the conclusion);
   - a `docs/tracking-research.md` section `0d. Line-through-the-rim side by side (date)`;
   - a one-line "Proposed, needs agreement: ..." for the `CLAUDE.md` next step.
   UK English, no em dashes. The owner pastes these in after merging, so they don't collide with PLAN_1's doc edits.
2. Commit in two commits, both on `exp/line-crossing`:
   - `Experiment: line-through-the-rim method (avishah3 idea, reimplemented) side by side with ShotVision; hybrids H1-H3` (the script and tests)
   - `Experiment results: line-crossing side by side` (the Markdown results file and `line_crossing_sv_baseline.txt`). Don't commit the JSON file. Leave it untracked and mention it in the report. Don't edit `.gitignore`.
3. Run the tests, then check that `git status` shows only the untracked JSON. If it also shows `.venv` or `experiments/.cache`, do **not** add or commit them (they are symlinks into the main repo). Stop and tell the owner the setup exclude step was missed. Then `git push -u origin exp/line-crossing`.
4. Final message to the owner: commit hashes, the summary table, the false-make list, the conclusion, and anything you skipped or were unsure about.

Stop there.

---

## 9. For the owner: setup and merge (the agent doesn't run this section)

### Before starting either plan (once, in the main repo folder)
```bash
cd ~/Desktop/ShotVision
git checkout stage1/label-tooling
git add sample_clips/labels.json
git commit -m "labels: Hazen v Enosburg (held out from the tracker fix), Claude-labeled, not human-verified"
git push

git worktree add ../ShotVision-exp -b exp/line-crossing
cd ../ShotVision-exp
ln -s ../ShotVision/.venv .venv
mkdir -p experiments
ln -s ../../ShotVision/experiments/.cache experiments/.cache
for f in ../ShotVision/sample_clips/*; do
  n=$(basename "$f")
  [ -e "sample_clips/$n" ] || ln -s "../../ShotVision/sample_clips/$n" "sample_clips/$n"
done
# git ignores folders by "name/", but these are symlinks (files to git), so hide them explicitly.
# info/exclude is shared by all worktrees and never committed.
printf '.venv\nexperiments/.cache\n' >> "$(git rev-parse --git-common-dir)/info/exclude"
git status --short                                       # should print nothing
.venv/bin/python scripts/evaluate.py --report | tail -5   # should run from cache in seconds
```
Then start PLAN_1 in `~/Desktop/ShotVision` and PLAN_2 in `~/Desktop/ShotVision-exp`, each in its own agent session.

### After both finish
```bash
cd ~/Desktop/ShotVision          # on stage1/label-tooling, with PLAN_1 done and pushed
git merge exp/line-crossing      # only new files on that branch, so no conflicts expected
.venv/bin/python experiments/line_crossing_experiment.py \
  --out experiments/results/line_crossing_with_split.md
```
The rerun takes seconds and now shows the in-scope split. Then paste the "Docs to add after merge" text into the docs (using the rerun's numbers), commit, push, and remove the worktree with `git worktree remove ../ShotVision-exp`.
