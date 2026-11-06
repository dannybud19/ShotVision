# RUN LOG — PLAN_1_score_split — 2026-11-06

Agent run log. Plan: `docs/plans/PLAN_1_score_split.md`. Branch `stage1/label-tooling`.

## Step 1.1 Branch and tree
- `git checkout stage1/label-tooling` -> already on it.
- `git status` -> clean.
- `git log --oneline -3`:
  - aab75f6 Plans: camera split (PLAN_1), line-crossing side by side (PLAN_2), runner prompt
  - daaa8a6 labels: Hazen v Enosburg (held out from the tracker fix), Claude-labeled, not human-verified
  - 0376cfb Bandits 03 labeled (Sonnet), evaluator matches by closest label end, research doc 0b
- Expected: branch stage1/label-tooling, clean tree, latest aab75f6 with daaa8a6 before it.
  - Got: match. | Match: yes

## Step 1.2 Cache check
- `ls experiments/.cache/detections/ | grep fd4cd3dc7f`
- Got: (see below)

## Step 1.2 Cache check (result)
- All 16 clips in labels.json have a matching `.fd4cd3dc7f.pkl`. Missing: none.
- Expected: every labeled clip has a cache file, including Enosburg. Got: match. | Match: yes

## Step 1.3 Tests (baseline)
- Command: pytest -q with 2 deselects.
- Got: `134 passed, 2 deselected in 0.90s`
- Expected: all pass. | Match: yes

## Step 1.4 Reproduce last known Gate A numbers
- Command: evaluate.py --report --clips <14 pre-Enosburg clips> > gate_a_before_split.txt
- Expected: Makes counted 132/193, 0 false makes on labeled misses, 1 spurious make, GATE A: FAIL.
- Got: `Makes counted: 132/193 (68.4%)`, `False makes: 0/57 labeled misses, + 1 spurious makes`, `GATE A: FAIL`.
- | Match: yes

## Step 2 Commit the held-out Enosburg labels
- Session note: Enosburg labels already committed (daaa8a6). So only item 1 (check) and item 3 (SOURCES.md).
- Item 1 check:
  - Got: `dev commons:hardwick_game_HELDOUT_for_tracker_fix Counter({'MAKE': 51, 'MISS': 28, 'IGNORE': 19})`
  - Expected: same. | Match: yes
- Item 3: SOURCES.md had no Enosburg row. Added one after the Lyndon row (CC BY 4.0, HCTV, 1920x1080 60 fps 81 min).
- Commit: 36d469f SOURCES: Hazen v Enosburg provenance

## Step 3 Score the held-out game on its own
- Command: evaluate.py --report -v --clips <enosburg>
- Gate A block:
  - Makes counted: 26/51 (51.0%)
  - False makes: 0/28 labeled misses, + 4 spurious makes -> 95% upper bound 29.8%
  - GATE A: FAIL
- SUMMARY: 0/1 clips pass | 44/79 labeled shots correct | false makes 4 | spurious shots 14
- False makes (all spurious, unlabeled, so no label card number): f35060, f125017, f201606, f207518 (all make_confirmed)
- Diagnostics: shot_diagnostics.py --cache-only (no --clips option, so runs all clips; plan says fine). 7019 lines, 397 KB.
- .gitignore: added `experiments/results/*.txt` (diagnostics file 397 KB > 200 KB). No dedicated commit point in the plan for this; will bundle with the final docs commit (step 7). Flagging in final report.

## Step 4.1 New script experiments/camera_profile.py + tests/test_camera_profile.py
- Wrote camera_profile.py (pure functions hoop_metrics, multi_ball_share, _percentile, _well_separated_pair; lazy `import evaluate` inside profile_rows/main so the pure functions import without torch/ultralytics).
- Wrote tests/test_camera_profile.py (3 checks, uses a local _Det dataclass, no cache/model).
- Test file alone: 3 passed.

## Step 4.2 Run it
- Command: `python experiments/camera_profile.py --json experiments/results/camera_profile.json`
- Full table (stdout):
```
clip                                                        frames   fps     hoop_seen   hoop_move_p95   hoop_size_ratio  multi_ball
chonyy_one_score_one_miss.mp4                               214      30.0    0.995       0.059           1.078            0.0
chonyy_two_score_two_miss.mp4                               403      30.0    0.985       0.057           1.097            0.0
chonyy_two_score_three_miss.mp4                             503      30.0    0.99        0.055           1.093            0.0
video_test_5.mp4                                            3378     29.97   0.937       0.764           1.168            0.013
chonyy_sample_video.mp4                                     101      30.0    0.98        0.086           1.126            0.0
lf_shot_detection.mp4                                       1116     30.0    0.973       0.055           1.084            0.0
lf_back.mp4                                                 1221     29.995  0.949       0.041           1.082            0.012
lf_alan.mp4                                                 658      24.0    0.778       1.75            1.387            0.0
artur_vid29.mp4                                             884      29.99   0.997       2.151           1.12             0.0
kyle_test_video.mp4                                         353      29.97   1.0         1.17            1.728            0.006
aggie_NathanBBall.mov                                       806      29.963  0.963       0.713           1.062            0.002
public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm  277327   60.0    0.307       14.058          2.432            0.035
public/commons_bandits/bandits_practice_02.webm             13150    60.0    0.964       1.734           1.159            0.082
public/commons_bandits/bandits_practice_01.webm             3934     60.0    0.295       10.778          2.563            0.031
public/commons_bandits/bandits_practice_03.webm             23828    60.0    0.747       6.488           3.043            0.085
public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm  290380   60.0    0.352       9.64            2.036            0.037
```

## Step 4.3 Propose a class for each clip
Rules applied literally: fixed = move<0.5 AND ratio<1.3; single = multi<0.05.

Classes written (16):
- fixed/single: chonyy_one, chonyy_two_score_two_miss, chonyy_two_score_three_miss, chonyy_sample, lf_shot, lf_back (6)
- moving/single: video_test_5, lf_alan, artur, kyle, aggie, lyndon, bandits_01, enosburg (8)
- moving/multi: bandits_02, bandits_03 (2)

Borderline (within 20% of a threshold = [0.8t, 1.2t]):
- hoop_move_p95 [0.4, 0.6]: none.
- multi_ball [0.04, 0.06]: none.
- hoop_size_ratio [1.04, 1.56]: 11 clips (chonyy_one 1.078, chonyy_two_score_two_miss 1.097, chonyy_two_score_three_miss 1.093, video_test_5 1.168, chonyy_sample 1.126, lf_shot 1.084, lf_back 1.082, lf_alan 1.387, artur 1.12, aggie 1.062, bandits_02 1.159). Note: this band is wide and catches most fixed clips (fixed ratios cluster ~1.06-1.17, zooming clips 1.39-3.04); no clip is genuinely near the 1.3 zoom threshold, and camera_class is decided by hoop_move_p95 alone for every clip here.

Disagreements with the sanity check (not overridden):
- Sanity: GitHub clips "mostly fixed/single". Measured moving among GitHub clips: aggie (0.713), video_test_5 (0.764), lf_alan (1.75), artur (2.151), kyle (1.17) -> 5 of 11 GitHub clips measure "moving".
- Sanity: Bandits "should come out multi, and probably moving". bandits_01 measures multi_ball 0.031 -> "single" (disagrees); bandits_02 (0.082) and bandits_03 (0.085) are "multi", all three "moving".

## Step 4.4 Write classes into labels.json
- Read-modify-write: inserted camera_class, ball_count, camera_profile after "split" for all 16 clips; preserved key order; json.dump(indent=2, ensure_ascii=False) + trailing newline.
- `git diff --stat sample_clips/labels.json`: 1 file changed, 160 insertions(+), 0 deletions.
- Shots-unchanged assertion: "shots unchanged".
- .gitignore: also added experiments/results/*.json (camera_profile.json is a derived artifact; plan only named *.txt). Flagging.
- Commit: d603b6b Camera profile: measured hoop motion, zoom and multi-ball per clip; camera_class/ball_count in labels.json

## Step 5 Add the split to the Gate A report
- Step 5.1: edited only print_gate_report in scripts/evaluate.py. Added a by_class accumulator (makes/counted/misses/false makes per camera class, spurious makes attributed to the clip's class), a "By camera class" table (5 canonical rows), renamed the old line to "GATE A (all clips, old definition)", added "GATE A (in scope: fixed camera, single ball)" and "STRESS TEST (out of scope)", and made the return value the in-scope pass/fail. main() unchanged (still returns 0/1 from print_gate_report).
- Step 5.2: re-ran the step 1.4 command -> gate_a_after_split.txt, then diff vs gate_a_before_split.txt.
  - Diff shows ONLY: (a) the new "By camera class" table, (b) "GATE A: FAIL" -> "GATE A (all clips, old definition): FAIL", (c) the two new gate lines.
  - New section values:
```
By camera class (makes counted/makes, make rate, false makes/misses, 95% UB):
  fixed/single       21/22    95.5%    0/6      39.3%
  fixed/multi         0/0      0.0%    0/0     100.0%
  moving/single      58/85    68.2%    0/34      8.4%
  moving/multi       53/86    61.6%    1/17     25.0%
  unclassified        0/0      0.0%    0/0     100.0%
```
  - New gate lines: `GATE A (all clips, old definition): FAIL`, `GATE A (in scope: fixed camera, single ball): PASS`, `STRESS TEST (out of scope): makes 111/171, false makes 1/51`.
  - Exit code now 0 (in-scope PASS). Expected per plan (return value is in-scope). | Match: yes
- Step 5.3: added tests/test_gate_report.py (2 tests). Full suite: 139 passed, 2 deselected.
- Commit: e7a3b73 evaluate --report: Gate A split by camera class; in-scope gate (fixed, single ball) plus out-of-scope stress test

## Step 6 Run the full report with everything included
- Command: `python scripts/evaluate.py --report > experiments/results/gate_a_split_full.txt 2>&1` (exit 0, in-scope PASS).
- Full Gate A block:
```
=== Gate A ===
Makes counted: 158/244 (64.8%)  [need >= 90%]
False makes: 0/85 labeled misses, + 5 spurious makes -> 95% upper bound on false-make rate 12.0%  [need 0 false makes]
By miss type (misses, false makes, resolved as MISS, 95% UB):
  airball           1    0    1   95.0%
  back_rim         23    0   19   12.2%
  front_rim        36    0   26    8.0%
  other            13    0    7   20.6%
  side_rim_out     12    0   10   22.1%
By source (makes counted/makes, false makes/misses):
  commons:bandits_practice   53/87     1/18
  commons:hardwick_game    23/43     0/31
  commons:hardwick_game_HELDOUT_for_tracker_fix   26/51     4/28
  github:aggie              5/5      0/1
  github:artur              3/3      0/1
  github:chonyy             4/4      0/4
  github:kyle               0/1      0/0
  github:lf                18/20     0/2
  github:video_test_5      26/30     0/0
By camera class (makes counted/makes, make rate, false makes/misses, 95% UB):
  fixed/single       21/22    95.5%    0/6      39.3%
  fixed/multi         0/0      0.0%    0/0     100.0%
  moving/single      84/136   61.8%    4/62     14.2%
  moving/multi       53/86    61.6%    1/17     25.0%
  unclassified        0/0      0.0%    0/0     100.0%
Lost makes by exit reason:
  make lost: never armed                   57
  make lost: miss_occlusion_gap            12
  make lost: miss_below_without_inner      10
  make lost: miss_rim_out_sideways         6
  make lost: miss_in_and_out               1
GATE A (all clips, old definition): FAIL
GATE A (in scope: fixed camera, single ball): PASS
STRESS TEST (out of scope): makes 137/222, false makes 5/79
```
- SUMMARY: 4/15 clips pass | 221/329 labeled shots correct | false makes 5 | spurious shots 33

Answers to the four questions (from output only):
1. In-scope make rate 95.5% (21/22), 0 false makes. It is 5.5 points above 90% and meets 0 false makes.
2. In-scope misses = 6. 95% upper bound 39.3%. Under 30, so the false-make rate cannot be shown to be low yet.
3. One in-scope clip loses a make: lf_shot_detection.mp4, label MAKE [600-640] -> MISS @f626 via miss_rim_out_sideways.
4. Enosburg vs Lyndon (same panning broadcast camera): Lyndon 23/43 (53.5%), 0 false makes in 31 misses. Enosburg 26/51 (51.0%), 0 labeled false makes but 4 spurious makes. Enosburg is worse: slightly lower make rate and 4 false makes where Lyndon had 0.

## Step 7 Update the docs
- docs/PROJECT_LOG.md: added two entries (2026-11-05 later: tracker fix and Bandits 03; 2026-11-06: camera split and held-out game).
- CLAUDE.md: rewrote the "Current phase" block (in-scope gate passes, out-of-scope stress test, tracker fix done, next step PLAN_2).
- docs/ROADMAP.md: updated status line and the Phase 1 "Where it stands" bullet to state the gate is judged on in-scope clips and out-of-scope is a stress test. No other phase changed.
- docs/tracking-research.md: added "### 0c. Split by camera class (2026-11-06)" with the step 6 table.
- HANDOVER.md: does not exist, skipped.

## Step 8 Finish (pending at time of this entry)
- Will run tests, check git status clean, push.
