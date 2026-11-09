# Run log: PLAN_3 Part A, 2026-11-09

## A0.1 Branch and tree
Commands: git checkout, git status --short, git log, git worktree list.
- Expected: branch stage1/label-tooling, ff854c0 latest, only plan file untracked, worktree ShotVision-exp f094fd0 | Got: as expected | Match: yes
- Committed plan file: 9dc6c18 `Plans: PLAN_3 Phase 1 polish (Part A and Part B)`.
- Note: `experiments/results/RUN_LOG_*.md` is tracked (PLAN_1's log is), so this log is committed in the final A8 docs commit so `git status --short` is empty.

## A0.2 Baseline tests
- Expected: all pass | Got: 139 passed, 2 deselected | Match: yes. BASE_TESTS=139 (CLAUDE.md says 124; stale, A8 updates it).

## A0.3 Baseline Gate A (experiments/results/plan3_gate_a_before.txt, 15 s, no model output)
- Makes counted 158/244 (64.8%) | Match: yes
- False makes 0/85 labeled misses, + 5 spurious makes | Match: yes
- fixed/single 21/22 95.5% 0/6 39.3% | Match: yes
- GATE A (all clips, old definition): FAIL | Match: yes
- GATE A (in scope): PASS | Match: yes
- STRESS TEST makes 137/222, false makes 5/79 | Match: yes
- exit=0 | Match: yes

## A1.1
Commands: `git diff --name-status stage1/label-tooling...exp/line-crossing`
- Expected: all lines `A` | Got: 5 files, all `A` (line_crossing_experiment.py, RUN_LOG_PLAN_2, line_crossing_2026-11-06.md, line_crossing_sv_baseline.txt, tests/test_line_crossing.py) | Match: yes

## A1.2 Merge
- `git merge --no-ff exp/line-crossing`. Expected: no conflicts | Got: clean merge, commit 4c13da3 | Match: yes
- (I briefly staged this run log by mistake before the merge, unstaged it with `git restore --staged`, then merged. No effect.)

## A1.3 Tests
- Expected: all pass, count > 139 | Got: 146 passed, 2 deselected. TESTS_A1=146 | Match: yes

## A1.4 Experiment rerun with camera split (18 s, from cache)
- Expected: SV makes 158/244, false makes 0/85, spurious 5, equal to A0.3 | Got: SV 158/244, 0/85, 5 | Match: yes
- Full summary table is in the final report.

## A1.5 Docs
- Ambiguity: the rerun file `line_crossing_with_split.md` has NO `## Docs to add after merge` section (the script does not generate it). The section is in the committed 6 Nov file `line_crossing_2026-11-06.md`. I used that section. Every number in it equals the rerun's (SV through H3 identical), so no numbers were replaced. The text says "141 tests pass", which was true on the exp branch at the time; I left it verbatim (146 now, post-merge).
- Pasted: PROJECT_LOG entry above `## Tools used`; tracking-research `0d` directly after `0c`; CLAUDE.md "Proposed, needs agreement" bullet under Next step.
- Tests: 146 passed. Commit 8a1ac9e `Docs: line-crossing experiment results after merge, with camera split (PLAN_2 follow-up)`.
- Files: CLAUDE.md, docs/PROJECT_LOG.md, docs/tracking-research.md, experiments/results/line_crossing_with_split.md.

## A1.6 Worktree
- Expected: .venv and experiments/.cache are symlinks | Got: both `->` symlinks | Match: yes
- Untracked `experiments/results/line_crossing_2026-11-06.json` was in the worktree; moved to the main folder. Status afterwards: empty | Match: yes
- `git worktree remove ../ShotVision-exp` (no --force) succeeded. `git worktree list` shows only the main folder; `exp/line-crossing` branch still exists | Match: yes. Main `.venv` and `experiments/.cache` intact.

## A2
Files: scripts/evaluate.py (print_gate_report, parse_args, main), tests/test_gate_report.py.
- Expected: second existing test passes unchanged | Got: passes | Match: yes
- Expected diff vs before: exactly one changed line (PASS -> NOT ENOUGH MISSES TO JUDGE (6 < 50)), exit=1 | Got: exactly that one line, exit=1 | Match: yes
- Expected tests: TESTS_A1 + 4 = 150 | Got: 150 passed, 2 deselected | Match: yes
- Deviation (test file only): the plan's 4th test (`_check("MAKE","MISS")`) crashed inside the existing `print_gate_report` with `AttributeError: 'NoneType' object has no attribute 'value'`, because `_check` builds a ShotResult with `reason=None` and the report reads `c.result.reason.value` for lost makes. I did not touch evaluate.py for this. I added a `_lost_make()` helper in tests/test_gate_report.py that sets `reason=ResolutionReason.MISS_BELOW_WITHOUT_INNER`, and imported `ResolutionReason`. Real results always carry a reason, so this is a test-fake artefact only (noted in the report).
- Commit: see git log (`evaluate --report: in-scope Gate A needs >= 50 misses ...`).

## A3
Done. Commit 90ef637.

## A3 Review sheets, frames subcommand
- A3.1: ffmpeg NOT installed (`ffmpeg not found`); cv2 5.0.0 and numpy import fine. So frames are read with cv2 (one seek to a window frame, then sequential reads). The ffmpeg branch exists in the code but is untested here.
- A3.2: new `experiments/review_sheets.py` (frames subcommand), new `tests/test_review_sheets.py` (5 tests: window_frames 21 frames/510/630/step 6; crop_box centred, clamped at left edge, median, empty = full frame).
- A3.3: ran on the 4 frames in <2 s, from cache. Expected: 4 png + 4 _full.jpg + 1 _targets.json, `ignored: ok` | Got: exactly that, ignored: ok | Match: yes
- A3.4 seek check: Expected: green boxes on the hoop | Got: on the hoop in all 4 sheets (boxes follow the panning hoop; a few fast-pan tiles, e.g. f201624, show a loosely placed box with consistent neighbours) | Match: yes
- Nearby labels (±10 s): f35060 none; f125017 start 124450 end 124492 IGNORE card 71; f201606 none; f207518 none.
- Choice made: crop_box moves the crop box (keeps its size) when it would leave the image, so all tiles in a sheet are the same size. Frame number is drawn on each tile after cropping, so it stays visible.
- Tests: all pass. See git log for commit.

## A4
Done. Commit 41181e4.

## A4 Camera sheets
- Added `camera` subcommand to experiments/review_sheets.py; 4 more tests in tests/test_review_sheets.py (second far hoop frame: share 1/10 and jump list includes it; plus still hoop, no hoop, spread indices). Tests: 155 -> 159.
- Ran on the 6 clips (2 s, from cache). Expected: 6 camera_*.png | Got: 6 | Match: yes
- Printed table:
  | clip | frames_with_hoop | share_with_2plus_hoops | max_jump | camera_class |
  | --- | --- | --- | --- | --- |
  | video_test_5.mp4 | 3165 | 0.0000 | 0.90 | moving |
  | aggie_NathanBBall.mov | 776 | 0.0000 | 0.82 | moving |
  | lf_alan.mp4 | 512 | 0.0000 | 1.81 | moving |
  | artur_vid29.mp4 | 881 | 0.0000 | 2.31 | moving |
  | kyle_test_video.mp4 | 353 | 0.0000 | 1.49 | moving |
  | lf_back.mp4 | 1159 | 0.0000 | 0.18 | fixed |
- Render check (only): track plot, spread frames, jump frames and boxes visible on all 6 sheets. No tag decided.
- Choice: `share_with_2plus_hoops` = frames with 2+ hoop detections (conf >= 0.6) divided by ALL frames in the clip (literal reading). `max_jump` and jump frames use the highest-confidence hoop per frame. Spread frames use evenly spaced indices from first to last frame.
- Oddity: the video_test_5 spread tile for f3377 (the last frame) is black. It decoded without error (read ok); not investigated. Plot values beyond +-1.5 hoop widths are clipped to the plot edge (artur's dx).
- Tests all pass.

## A5
Done. Commit 60c518d.

## A5 Phone rotation
- A5.1: Expected both True | Got `5.0.0 True True` | Match: yes
- A5.2 audit of all 16 clips in labels.json: Expected meta 0 for every clip | Got meta 0.0 for all 16 (auto already reads 1.0, i.e. OpenCV auto-rotates by default; frame shapes e.g. artur_vid29 is portrait 1280x720 natively) | Match: yes
- A5.3: SKIPPED. ffmpeg is not installed, so no rotated test clip could be built and "before" behaviour with a real rotation flag was not observed. ROTATION UNVERIFIED.
- A5.4: edited shotvision/capture/source.py as specified, with ONE deviation: the guard also checks `hasattr(self._cap, "set")`. Reason: the existing test `test_source_key_distinguishes_device_and_url` uses a `FakeCap` with no `set()`; the plan's exact code made it fail (AttributeError at source.py:51 for the URL source). The plan forbids changing existing tests, so I added the guard. No effect on a real cv2.VideoCapture. Alternative if the owner prefers: remove the guard and add `def set(self, *a): pass` to FakeCap.
- A5.5: added `test_normal_clip_reports_no_rotation` (passes) and `test_rotated_clip_is_read_upright` (skipped here: needs ffmpeg; tries `-display_rotation 90` then `-metadata:s:v:0 rotate=90`, neither command verified on this machine).
- A5.6: Expected `identical` | Got identical | Match: yes
- Tests: 160 passed, 1 skipped (rotated test), 2 deselected.

## A6
Done. Commit 4eadeef.

## A6 live_check.py
- New `experiments/live_check.py` (pipeline copied from main.py run(): resolve_device, Detector, FrameSource, BallTracker(detector, ...), RimTracker, ShotStateMachine, StatsTracker; headless) and `tests/test_live_check.py` (4 tests). NOT RUN (it loads the model); only `py_compile` was run on it.
- Tests: Expected all pass | Got 164 passed, 1 skipped, 2 deselected (160 + 4) | Match: yes
- Choices: latency covers detect + tracking + state machine (from after source.read() to the update finishing). Processing fps = frames / wall seconds of the read loop (excludes model load). `--compare-to-replay` skips with a message if the clip has no cached detections (never recollects), and with `--seconds` it compares only the frames the live run saw. Live shots are paired with `compare_results` on ShotResult objects; JSON output has the summary, shots and comparison.
- Added an optional `--config` flag (mirrors main.py) beyond the plan's list.

## A7
Done. Commit 335b7cc.

## A7 Decisions file
- Created docs/plans/PLAN_3_decisions.md with the plan's structure. Filled: nearby labels from _targets.json, hoop_move_p95 / hoop_size_ratio from labels.json camera_profile, 2+ hoops share from the A4 table. Owner columns empty.
- Share column shows 0.0000 for all five clips (A4 printed value).
Done. Commit f5d1694.

## A8 Docs, push
- CLAUDE.md (Gate A bullet, Current phase line, Next step replaced with the "Proposed, needs agreement" bullet kept under it, Tests bullet 126 -> 167 and 124 -> 165), docs/ROADMAP.md status line, docs/tracking-research.md section 0e (with the A4 table), docs/PROJECT_LOG.md entry above `## Tools used`.
- Tests: 164 passed, 1 skipped (needs ffmpeg), 2 deselected.
- This run log is committed with the A8 docs commit so `git status --short` is empty.
