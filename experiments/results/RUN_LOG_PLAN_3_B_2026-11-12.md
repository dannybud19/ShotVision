# Run log: PLAN_3 Part B, 2026-11-12

## B0
- Branch stage1/label-tooling, `git pull --ff-only`: already up to date. Tree clean. HEAD 968a97c.
- Owner cells validated: section 1 four REAL_MAKE rows (integer start/end, start < end, start <= frame <= end+60); section 2 five tags with reasons; section 3 both blocks present.
- Tests. Expected: all pass | Got: 165 passed, 2 deselected | Match: yes
- Report to plan3_gate_a_before_B.txt. Expected: identical to plan3_gate_a_after_A5.txt | Got: identical (exit=1, in-scope verdict NOT ENOUGH MISSES TO JUDGE (6 < 50)) | Match: yes

## B1
Owner decisions (copied from docs/plans/PLAN_3_decisions.md).

| Frame | Nearby labels (±10 s) | Owner: call | Owner: start | Owner: end | Owner: note |
| --- | --- | --- | --- | --- | --- |
| 35060 | none | REAL_MAKE | 35012 | 35066 | owner confirmed the ball went through; start/end set to frame -48/+6 to match this game's label lengths |
| 125017 | 124450-124492 IGNORE (card 71) | REAL_MAKE | 124969 | 125023 | owner confirmed the ball went through; start/end set to frame -48/+6 to match this game's label lengths |
| 201606 | none | REAL_MAKE | 201558 | 201612 | owner confirmed the ball went through; start/end set to frame -48/+6 to match this game's label lengths |
| 207518 | none | REAL_MAKE | 207470 | 207524 | owner confirmed the ball went through; start/end set to frame -48/+6 to match this game's label lengths |

| Clip | Current tag | hoop_move_p95 | hoop_size_ratio | 2+ hoops share | Owner: tag | Owner: reason |
| --- | --- | --- | --- | --- | --- | --- |
| video_test_5.mp4 | moving | 0.764 | 1.168 | 0.0000 | fixed | owner reviewed: background stays still across the clip |
| aggie_NathanBBall.mov | moving | 0.713 | 1.062 | 0.0000 | fixed | owner reviewed: background stays still across the clip |
| lf_alan.mp4 | moving | 1.75 | 1.387 | 0.0000 | moving | owner reviewed: perspective shifts during the clip, so not a single fixed camera (background stays in view) |
| artur_vid29.mp4 | moving | 2.151 | 1.12 | 0.0000 | fixed | owner reviewed: background stays still across the clip |
| kyle_test_video.mp4 | moving | 1.17 | 1.728 | 0.0000 | moving | owner reviewed: camera moves |

K = 4 (REAL_MAKE rows). R = 3 (video_test_5, aggie_NathanBBall, artur_vid29).
Live-check finding (follow-up only, not fixed): webcam reports 15 fps but delivers about 29; shot-logic timings use reported fps, so live windows would be about half as long as intended.

## B2
- Edited sample_clips/labels.json: camera_class set and camera_class_source added for 5 clips (diff: 8 insertions, 3 deletions, nothing else).
- Shots check. Expected: shots unchanged | Got: shots unchanged | Match: yes
- Makes counted. Expected: 158/244 (64.8%) | Got: 158/244 (64.8%) | Match: yes
- False makes. Expected: 0/85 + 5 spurious | Got: 0/85 labeled misses, + 5 spurious makes | Match: yes
- Diff vs before_B: only fixed/single, moving/single, in-scope verdict and stress-test lines changed | Match: yes
- fixed/single 55/60 91.7% 0/8 31.2%; in-scope verdict NOT ENOUGH MISSES TO JUDGE (8 < 50); stress test makes 103/184, false makes 5/77.
- Tests: 165 passed, 2 deselected.

## B3
- Appended 4 MAKE entries to the Enosburg clip, stable-sorted by start. No card field.
- Integrity. Expected: only Enosburg grows, by K=4 | Got: Enosburg old 98 new 102, all 16 clips' old shots present | Match: yes
- Makes counted. Expected: 162/248 | Got: 162/248 (65.3%) | Match: yes
- Labelled misses. Expected: 0/85 | Got: 0/85 | Match: yes
- Spurious makes. Expected: 5-4 = 1 | Got: 1 | Match: yes
- In-scope verdict: NOT ENOUGH MISSES TO JUDGE (8 < 50). Stress test: makes 107/188, false makes 1/77.
- Tests: 165 passed, 2 deselected.

## B4
- Final report identical to after_B3. In-scope fixed/single 55/60 (91.7%), 0/8, 95% UB 31.2%, NOT ENOUGH MISSES TO JUDGE (8 < 50). 42 more in-scope misses needed. Stress test 107/188, false makes 1/77.
- Enosburg: 4 real makes, 0 false makes, 0 can't tell (owner).
- Live (a): COMPARE: SAME, 122.92 fps vs 30.00 source. Live (b): 29.23 fps vs 15.00 reported source, real time YES.

## B5
- Edited CLAUDE.md, docs/PROJECT_LOG.md, docs/tracking-research.md (0e), docs/ROADMAP.md (status numbers). No HANDOVER.md exists, nothing done.
- Note: CLAUDE.md Next step text refers to HANDOVER.md section 12, which does not exist (text given by the plan).
- Run log committed with the docs so `git status` is empty (Part A committed its log the same way). Tests: 165 passed, 2 deselected.
