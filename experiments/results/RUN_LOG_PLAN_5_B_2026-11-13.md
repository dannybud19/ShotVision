# Run log: PLAN_5 Part B (2026-11-13)

Plan: `docs/plans/PLAN_5_realtime_and_phase2_groundwork.md`, Part B only (B0 to B2). Branch `stage1/label-tooling`, main repo folder.

Owner decisions before the start:
- Stale count in the plan: A0 expected 172 tests. The owner's expected state for Part B is `191 passed, 2 deselected`.
- `sample_clips/release_labels.json` is gitignored (`.gitignore:6: sample_clips/*`). Owner-approved fix: add the line `!sample_clips/release_labels.json` directly next to `!sample_clips/labels.json` in `.gitignore`, change nothing else in `.gitignore`, confirm `git check-ignore` prints nothing, and include `.gitignore` in the B1 commit.
- The sheets were rebuilt shooter-centred (`--center-on-release`) after A3. Part B joins on clip and label start/end, so this does not matter.

## B0: Pre-flight

- B0.1 `git checkout stage1/label-tooling`, `git pull --ff-only`, `git status --short`.
  - Expected: up to date, status empty, HEAD `4acfc2a` | Got: up to date, status empty, HEAD `4acfc2a PLAN_5 decisions filled in (20 release frames)` | Match: yes
- B0.2 Owner cells in `docs/plans/PLAN_5_decisions.md` (parsed column 6 of the 20 rows).
  - Expected: 20 rows, each an integer or `CANT_TELL` | Got: 20 rows, 0 bad, all integers, no `CANT_TELL` | Match: yes
- B0.3 Tests (test command from section 0).
  - Expected: `191 passed, 2 deselected` | Got: `191 passed, 2 deselected in 0.65s` | Match: yes
- B0.3 `scripts/evaluate.py --report` (cached detections), output diffed against `experiments/results/plan5_gate_a_before.txt`.
  - Expected: diff empty (exit 1 as in the baseline) | Got: exit=1, `diff` empty | Match: yes

## B1: Measure the finder's error

- B1.1 `.gitignore`: added `!sample_clips/release_labels.json` directly after `!sample_clips/labels.json` (owner's instruction). Nothing else in `.gitignore` changed.
  - Wrote `sample_clips/release_labels.json` from the 20 integer rows of `PLAN_5_decisions.md` (clip, label_start, label_end, release_frame, note; notes are empty).
  - Expected: `git check-ignore sample_clips/release_labels.json` prints nothing | Got: no output (with `-v` git also lists the negation rule `.gitignore:16:!sample_clips/release_labels.json`, which is not an ignore) | Match: yes
  - `sample_clips/labels.json`: `git diff --stat` empty, not edited.
- B1.2 `experiments/release_error.py`: joins on clip + label_start + label_end. Error = finder minus owner. p90 is numpy's linear percentile. Milliseconds use each shot's own fps from `release_moment.json`.
  - Choice made: `release_labels.json` holds integer rows only, so the CANT_TELL count is read from the decisions table (`--decisions`, default `docs/plans/PLAN_5_decisions.md`). Finder-failure rows (no release) and rows with no finder record are counted separately and left out of the error statistics. Both are 0 here.
- B1.3 `tests/test_release_error.py`: 6 tests, hand-made files in `tmp_path`.
  - Expected: all pass | Got: `6 passed` | Match: yes
- B1.4 `.venv/bin/python experiments/release_error.py --out experiments/results/release_error.md`
  - Expected: 20 rows scored (20 integer rows, 0 CANT_TELL) | Got: 20 scored, 0 no finder release, 0 no finder record, 0 CANT_TELL | Match: yes
  - Result: median abs error 4.0 frames (133 ms), p90 5.0 (167 ms), signed mean -2.75 frames (-92 ms), within ±2: 2/20 (10%), within ±5: 20/20 (100%).
  - Files: `.gitignore`, `sample_clips/release_labels.json`, `experiments/release_error.py`, `tests/test_release_error.py`, `experiments/results/release_error.md`, this log.
- Commit B1: `29de7f8 Release frames marked by the owner; experiments/release_error.py measures the finder`. Tests before commit: `197 passed, 2 deselected`.

## B2: Docs, push, report

- Re-read section 0 before the commit.
- `docs/tracking-research.md` (second "## 5." heading, Phase 2 groundwork): added the error tables and one sentence: not within ±2 frames on most shots (2/20, 10%), within ±5 on 20/20, early on 15, late on 4, exact on 1. I first wrote "early on 17 of 20" without checking, then counted from the data (15 early, 4 late, 1 exact) and corrected it before any commit.
- `docs/PROJECT_LOG.md`: entry `### 2026-11-13: PLAN_5 Part B: release finder measured`.
- `CLAUDE.md`: removed the "Owner, meanwhile" bullet, added the headline error to the Phase 2 groundwork bullet. Choice made: also updated the stale test counts in the Tests section (188 to 199 total, 186 to 197 with the two model tests deselected), because Part B adds 6 tests and the old figure was already out of date.
- `HANDOVER.md` section 10: replaced the PLAN_5 line with the headline result. Nothing else.
- Em dash check on added lines: none.
- Expected: tests pass before commit | Got: `197 passed, 2 deselected` | Match: yes
