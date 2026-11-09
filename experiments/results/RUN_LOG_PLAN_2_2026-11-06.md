# Run log: PLAN_2 line-crossing experiment

Date: 2026-11-06
Branch: exp/line-crossing
Plan: docs/plans/PLAN_2_line_crossing_experiment.md

## Goal

Side-by-side experiment comparing ShotVision scoring with the "line through the
rim" method (idea from avishah3, reimplemented from a description, no code
copied). Variants SV, L0 to L4, H1 to H3.

## Owner decisions and corrections (approved before starting)

1. L0-L4 use placeholder ShotResult reasons: MAKE_CONFIRMED for MAKE,
   MISS_BELOW_WITHOUT_INNER for MISS. The "Lost makes by exit reason" lines in
   the L0-L4 Gate A blocks are placeholders and not meaningful. The real
   breakdown (line / gap_too_long / arc_fallback / no point after the last
   above-rim point) comes from my own diagnostics. H1-H3: unchanged SV results
   keep their real SV reasons; changed/added results use MAKE_CONFIRMED and are
   marked "rescued" or "added" in diagnostics.
2. 2.5 checks ordered: vertical (abs(Bx - Ax) < 1e-6 -> predicted_x = Ax),
   then fit line, then m == 0 -> MISS, then divide.
3. One named record type for every point, fields cx, cy, w, h, frame.
4. Hybrid "within": abs(diff) <= to_frames(1.0, fps).
5. labels.json has no camera_class / ball_count, so every clip reports as
   "unclassified" and the in-scope columns are empty/zero.

Correction to plan section 5 test 5 (owner): the plan's x = 540 is outside both
rim bounds (500 ± 24 strict, 500 ± 34 with 10 px). Use x = 530 instead (inside
±34, outside ±24): L4 gives MISS (strict), L2 gives MAKE (±10 px).

## Steps

### Step 4.1.1 (baseline)
Command: `.venv/bin/python scripts/evaluate.py --report > experiments/results/line_crossing_sv_baseline.txt 2>&1`
Exit code 1 (expected: Gate A FAIL returns 1). Loaded from cache, did not load the model.

Gate A numbers to reproduce (SV):
- Makes counted: 158/244 (64.8%)
- False makes: 0/85 labeled misses, + 5 spurious makes -> 95% upper bound 12.0%
- GATE A: FAIL

Expected: baseline runs from cache in seconds, no model load | Got: yes, exit 1 with Gate A FAIL block | Match: yes

### Step 4.1.2 (L0 sanity on video_test_5.mp4)
Command: `.venv/bin/python experiments/line_crossing_experiment.py --clips video_test_5.mp4 --json /tmp/line_check.json --out /tmp/line_check.md`
L0 counts 24/30 makes.
Expected: L0 counts >= 20 of 30 | Got: 24/30 | Match: yes

### Step 4.1.3 (L0 first 5 shots on video_test_5.mp4)
up_frame / down_frame / gap_frames / predicted_x (hoop widths):
1. 31 / 69 / 7 / 0.043
2. 219 / 230 / 9 / 0.320
3. 379 / 420 / 7 / 0.096
4. 542 / 560 / 6 / 0.287
5. 638 / 680 / 7 / 0.028

### Step 5 (tests)
Command: `.venv/bin/python -m pytest -q --deselect tests/test_detector.py::test_detector_loads_real_basketball_checkpoint_and_predicts --deselect tests/test_ball_tracker.py::test_update_runs_end_to_end_on_blank_frame`
Got: 141 passed, 2 deselected. All pass.
Note: test 1-4 use a 6 px/frame fall (see test module docstring) because a literal
1 px/frame fall ages the above-rim point out of ball_pos before the down check.
Test 5 uses x = 530 (owner correction) and a parabola a = 0.5 with frames 15-20 missing.

### Step 6 (full run)
Command: `.venv/bin/python experiments/line_crossing_experiment.py --out experiments/results/line_crossing_2026-11-06.md --json experiments/results/line_crossing_2026-11-06.json`
Exit 0. Summary table:

| variant | makes counted / makes | false makes / misses | spurious makes | 95% upper bound | in-scope makes counted | in-scope false+spurious | legacy GitHub clips |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SV | 158/244 | 0/85 | 5 | 12.0% | 0/0 | 0 | 56/63 makes, 0 false+spur |
| L0 | 160/244 | 18/85 | 28 | 63.4% | 0/0 | 0 | 56/63 makes, 5 false+spur |
| L1 | 155/244 | 17/85 | 23 | 56.5% | 0/0 | 0 | 56/63 makes, 4 false+spur |
| L2 | 148/244 | 17/85 | 21 | 54.2% | 0/0 | 0 | 51/63 makes, 4 false+spur |
| L3 | 138/244 | 11/85 | 18 | 43.5% | 0/0 | 0 | 51/63 makes, 3 false+spur |
| L4 | 118/244 | 12/85 | 16 | 42.3% | 0/0 | 0 | 50/63 makes, 2 false+spur |
| H1 | 163/244 | 2/85 | 6 | 16.3% | 0/0 | 0 | 56/63 makes, 0 false+spur |
| H2 | 177/244 | 3/85 | 16 | 31.1% | 0/0 | 0 | 58/63 makes, 1 false+spur |
| H3 | 175/244 | 4/85 | 15 | 31.1% | 0/0 | 0 | 58/63 makes, 1 false+spur |

SV reproduction check (plan 4.1.1):
Expected: makes counted 158/244, false makes 0/85, spurious makes 5, 95% UB 12.0% | Got: 158/244, 0/85, 5, 12.0% | Match: yes

Hybrid change/add counts: H1 10 changed / 0 added, H2 10 / 30, H3 9 / 29.
gap_too_long / arc_fallback: L2 20 / 0, L3 20 / 0, L4 21 / 38.

### Step 7 (report)
Wrote experiments/results/line_crossing_2026-11-06.md with summary table, Gate A blocks,
false/spurious makes table, gained/lost lists, gap/arc counts, hybrid counts, then
hand-added Conclusion (7.6), Suggested next step (7.7) and Docs to add after merge (8.1).
JSON (every per-shot diagnostic) written to experiments/results/line_crossing_2026-11-06.json.
