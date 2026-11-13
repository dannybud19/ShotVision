# ShotVision: Handover

Owner: Danny (GitHub: dannybud19, repo `dannybud19/ShotVision`)
Last updated: 13 Nov 2026
Replaces: the 9 Nov handover. Lives in the repo root from PLAN_4 onwards.

Purpose: give a new Claude chat or coding session the full context of this project. Paste or upload this file and say: "Read HANDOVER.md, this is my project. Pick up from section 10."

---

## 1. How to resume in under 5 minutes

1. **Planning chat (claude.ai or similar):** upload this file. Ask for help with section 10.
2. **Coding session (Claude Code or another agent) in the repo root:**
   > Read HANDOVER.md, CLAUDE.md, docs/ROADMAP.md, docs/tracking-research.md and docs/PROJECT_LOG.md. Check git status, the branch, `git worktree list`, and run the tests. Tell me where we are before doing anything.
3. **Cheaper models (DeepSeek, Kimi, GLM):** give them a written plan plus the runner prompt (`PROMPT_for_plan_runner.md`). Never give a cheap model an open-ended task. See section 9.
4. The repo docs are the source of truth for code details. This handover is the source of truth for the reasoning, the decisions and the next steps.

Test command (2 tests need the model file, so they are skipped):
```bash
.venv/bin/python -m pytest -q \
  --deselect tests/test_detector.py::test_detector_loads_real_basketball_checkpoint_and_predicts \
  --deselect tests/test_ball_tracker.py::test_update_runs_end_to_end_on_blank_frame
```

---

## 2. What the project is

A single fixed camera watches you shoot and counts makes and misses automatically.

- **Type:** passion and learning project, not a product.
- **Phase 1 (now):** make or miss for one shooter from one fixed camera.
- **Long-term:** one app for solo training and pickup games. 2 vs 3, shot types, per-player stats, hot zones, highlights.
- **Differentiator:** shot selection feedback (for example, flagging fade-aways you didn't need to take). HomeCourt does solo drills, Hooper does pickup stats, neither judges decision quality.
- **Core rule:** a make only counts if the ball goes through the rim. **A false make is worse than a missed make.**

---

## 3. Where things stand (13 Nov 2026)

### Git state

| Item | State |
| --- | --- |
| Main folder | `~/Desktop/ShotVision`, branch `stage1/label-tooling`, PLAN_3 done at `c2e1916`, PLAN_4 steps 1 to 5 on top (`f85ff61` to `d9b7a1c`) plus its docs commit, pushed |
| `exp/line-crossing` | Merged into `stage1/label-tooling` (PLAN_3 A1). Worktree removed, branch kept |
| `main` | Has PR #1 only (the ByteTrack replacement) |
| Tests | 172 passed, 2 deselected (they load the model), 0 skipped (ffmpeg installed) |
| Model | `models/basketball_best.pt` (from avishah3, no licence). Loading it needs the owner's approval. All evaluation replays cached detections in `experiments/.cache/detections/*.fd4cd3dc7f.pkl` |

Commits since the 9 Nov handover, oldest first:

| Commit | What |
| --- | --- |
| `9dc6c18` to `a12a320` | PLAN_3 Part A: merge line-crossing, in-scope gate needs 50 misses, review sheets, rotation handling, live check script, decisions file, docs |
| (owner, two commits ending `968a97c`) | Fix: device index from config arrived as an int, so `--source 0` crashed (FrameSource and live_check cast it to str). Then the PLAN_3 decisions file filled in |
| `64d1fe8` `998757a` `c2e1916` | PLAN_3 Part B: 3 GitHub clips re-tagged fixed, 4 Enosburg makes added, docs |

### Headline numbers (cached replay, duplicates excluded)

| Footage | Makes counted | False makes | Misses tested |
| --- | --- | --- | --- |
| **Fixed camera, one ball (in scope)** | **55/60 (91.7%)** | **0** | **8** |
| Moving camera, one ball | 54/102 (52.9%) | 0 | 60 |
| Moving camera, several balls | 53/86 (61.6%) | 1 | 17 |
| **All** | 162/248 (65.3%) | 0 on 85 labelled misses, + 1 spurious make | 85 |

- In-scope verdict: `NOT ENOUGH MISSES TO JUDGE (8 < 50)`. 95% upper bound on the in-scope false-make rate: 31.2%.
- The only false make left anywhere is Bandits 03 f10473: a ball close to the camera passing in front of the hoop (depth case).
- **The real blocker: 42 more fixed-camera misses.**

### Live check (PLAN_3, owner ran it)

| Run | Result |
| --- | --- |
| Recorded clip `lf_shot_detection.mp4`, live code vs cached replay | `COMPARE: SAME` (10/10 shots identical), 122.92 fps processing vs 30 fps source, latency p50 6.6 ms |
| Laptop webcam, 60 s, no ball | Runs, 29.23 fps processing. **Webcam reported 15 fps but delivered about 29**, so live timings were half as long as intended. Fix in PLAN_4 step 4 |

---

## 4. Gate A explained

A gate is a pass mark a phase must hit before the next phase starts. **No phase starts until the one before passes its gate on real footage.**

| Gate | Footage | Pass mark |
| --- | --- | --- |
| **A** | Public clips (other people's cameras) | 50+ misses, 0 false makes, 90%+ makes counted |
| B | Danny's own filming | 0 false makes in 80 misses, 90%+ makes, scored per camera position |
| C | Danny's camera, live | Same as B |

Gate A is a rehearsal so problems show up before court time is spent. It isn't proof. Gate B is.

Since PLAN_1, `scripts/evaluate.py --report` prints three lines:
- `GATE A (all clips, old definition)`: FAIL
- `GATE A (in scope: fixed camera, single ball)`: `NOT ENOUGH MISSES TO JUDGE (8 < 50)`. Since PLAN_3 it can only PASS with at least 50 in-scope misses. A false make or a make rate under 90% is FAIL at any sample size.
- `STRESS TEST (out of scope)`: makes 107/188, false makes 1/77, no pass/fail.

---

## 5. How the code works

Pipeline (`shotvision/`): capture, then YOLO ball and hoop detection, then the ball tracker, then the rim tracker and shot state machine, then stats, then the overlay. Entry point: `python -m shotvision.main --source <file|0>`.

```
ShotVision/
├── CLAUDE.md, README.md, requirements*.txt
├── shotvision/
│   ├── main.py
│   ├── capture/source.py          # camera, URL or file
│   ├── detection/                 # detector.py (YOLO), device.py (MPS/CPU), model_registry.py
│   ├── tracking/ball_tracker.py   # nearest-neighbour tracker, shot-centric selection
│   ├── shot_logic/                # rim.py, rim_tracker.py (auto hoop), state_machine.py
│   ├── stats/tracker.py
│   ├── overlay/hud.py
│   └── config/                    # default.json (all timings in seconds), settings.py
├── scripts/                       # evaluate.py (scoreboard, Gate A), label_candidates.py, diagnose_shots.py,
│                                  # render_overlay.py, tune_detection.py, finetune_roboflow.py (never run)
├── experiments/                   # shot_diagnostics.py, camera_profile.py, track_adopt_experiment.py,
│                                  # arm_gate_sweep.py, line_crossing_experiment.py (on exp branch),
│                                  # .cache/ (saved detections), results/
├── tests/
├── sample_clips/                  # videos (gitignored), labels.json, SOURCES.md, public/, _label/
└── docs/                          # ROADMAP.md, tracking-research.md, PROJECT_LOG.md, plans/
```

- **Make rule:** ball seen above the rim, a fitted crossing inside the inner rim area while falling, then the whole ball seen below. Everything else is a miss. A ball that comes back above the rim after crossing is an in-and-out miss.
- **No hoop, no shot:** if the hoop is lost mid-shot, the shot is cancelled.
- **Tracker:** per-frame YOLO plus gated nearest-neighbour association (ByteTrack was removed). It picks the ball approaching the hoop, not one global ball.
- **Scoreboard:** `scripts/evaluate.py --report` replays the saved detections in seconds. Diagnostics: `experiments/shot_diagnostics.py --cache-only`.
- **Labels:** `sample_clips/labels.json`. The public-footage labels were made by Claude from contact sheets and **have not been checked by a human.**

---

## 6. Data

| Source | Clips | Licence | Camera tag (measured) |
| --- | --- | --- | --- |
| GitHub repos (chonyy, lf, avishah3, artur, kyle, aggie) | 11 | Varies, local dev use only | 9 fixed (video_test_5, aggie, artur re-tagged by the owner from review sheets), lf_alan and kyle moving |
| Hardwick high-school games (Lyndon, Enosburg) | 2 full games | CC BY 4.0 | moving (panning broadcast) |
| Vancouver Bandits practices 01 to 03 | 3 | CC BY 3.0 | moving, 02 and 03 multi-ball |

All public footage is **development data**. The final accuracy check must use Danny's own held-out footage. Provenance is in `sample_clips/SOURCES.md`.

Camera tags come from `experiments/camera_profile.py`. A clip is "fixed" when the hoop's 95th-percentile movement is under 0.5 hoop widths and the zoom ratio is under 1.3. It's "multi" when 5% or more of frames have two confident, separated balls.

---

## 7. Experiments and what they proved

### 7.1 PLAN_2: the "line through the rim" method (avishah3)

The idea: take the last ball point above the rim and the first below, draw a straight line, and call a make if the line crosses inside the rim (±0.4 hoop width + 10 px). It ignores how long the ball was invisible between the two points. It was reimplemented from a description (the repo has no licence) and run side by side with ShotVision.

| Variant | Makes | Labelled misses called makes | Unlabelled makes |
| --- | --- | --- | --- |
| ShotVision | 158/244 | 0/85 | 5 |
| L0 line, faithful | 160/244 | 18/85 | 28 |
| L3 line + gap limit + strict zone | 138/244 | 11/85 | 18 |
| L4 arc fit | 118/244 | 12/85 | 16 |
| H1 ShotVision, line rescues occlusion misses only | 163/244 | 2/85 | 6 |
| H2 H1 + adds line makes ShotVision never armed | 177/244 | 3/85 | 16 |

**Conclusion: not safe, rejected.** The line method's false makes are mostly front-rim and back-rim misses (the 2D depth problem). ShotVision's strict checks (whole ball below, in-and-out) are exactly what keep it at 0 false makes on labelled misses. Even the safest hybrid traded 5 makes for 3 false makes. Full results: `experiments/results/line_crossing_2026-11-06.md` on `exp/line-crossing`. In-scope columns are blank until that branch is merged and the script is re-run.

### 7.2 PLAN_1: camera split and the held-out game

- In scope: 21/22 makes, 0 false makes, 6 misses. The one lost in-scope make is `lf_shot_detection.mp4` [600-640], which resolves MISS at f626 via `miss_rim_out_sideways`.
- **Held-out Enosburg game:** 0 false makes on 28 labelled misses. The 4 unlabelled pipeline makes (frames 35060, 125017, 201606, 207518) were all checked by the owner from review sheets and are **real makes the labelling missed**. They were added as labels (frame -48 to +6). So the tracker fix held up on unseen footage.
- First real-footage firing of the in-and-out rule: 1 labelled make lost via `miss_in_and_out`. Worth checking which shot.

### 7.3 Earlier diagnosis (still true)

- In the original measurements, every lost make involved the ball invisible for 7 to 25 frames at the rim (motion blur over the backboard, or hidden in the net). Every labelled miss was decided with the ball in view.
- Threshold tuning trades one make for another. Widening the scoring gate creates false makes.
- No new model is justified yet. The gap is data (misses from a fixed camera), not the model.

---

## 8. Open issues

1. **Only 8 in-scope misses.** Need 50. This is the one thing between Phase 1 and Phase 2.
2. **Webcam frame rate:** reported 15 fps, delivered about 29. PLAN_4 step 4 measures the real rate on live devices.
3. **The in-front-of-the-hoop false make** (Bandits 03 f10473). Needs a depth cue (net drawn over the ball, or ball size vs balls that went through). Not fixable with a threshold from one example.
4. Labels for public footage are Claude-made and only partly human-checked (the 4 Enosburg makes and 5 camera tags were checked by the owner).
5. Small leftovers fixed in PLAN_4: report crash on a lost make with no reason; test-only `hasattr` guard in `FrameSource`; stale CLAUDE.md bullets.

---

## 9. How we work (process and tools)

- **Planning** happens in a strong model (Claude). **Execution** of well-scoped work goes to cheaper models using a written plan plus `PROMPT_for_plan_runner.md`.
- The runner prompt makes the agent: summarise the plan first and wait, go step by step, write `Expected | Got | Match` for every expected number, stop on any mismatch, keep a run log, never tune, never edit the pipeline unless told, and report in a fixed 7-part format.
- **Plans can run in parallel** when they never edit the same file. PLAN_2 ran in a git worktree on its own branch and only created new files. Its doc text went into its results file to paste in after merging. Symlinks in the worktree point `.venv`, `experiments/.cache` and the videos at the main folder, and are hidden from git via `.git/info/exclude`.
- **Model choice** (benchmarks are mostly vendor-reported, Nov 2026):

| Model | Use for |
| --- | --- |
| DeepSeek V4 Pro | Mechanical plans (cheapest, about $0.66/$1.98 per M off-peak). Weak on long sessions |
| GLM-5.3 | Long, careful plans (best long-horizon scores, most expensive, $1.40/$4.40) |
| Kimi K3 | Close second to GLM, best on hard science questions |
| Hy4 (Tencent) | Newest, best at maths, least independently verified. Wait |

- **Effort:** medium (or thinking off) for mechanical plans, high (thinking on) for anything that writes new algorithms.
- Always bring the agent's final report back to a planning chat to review before merging or changing the pipeline.

---

## 10. Next actions (in order)

1. PLAN_4 done. Live webcam: measured 29.89 fps vs 15 reported, latency p95 15.3 ms; real-time verdict fixed in PLAN_5.
2. PLAN_5 Part A done; owner marks release frames, then Part B.
3. **Decide on still-camera shots.** If PLAN_4 step 5 finds many still-camera misses in the broadcast games, decide whether they fairly count towards the in-scope set (they are a fixed view, but a different angle and zoom from your own setup).
   - PLAN_4 step 5 result: `Still-camera misses outside fixed/single clips: 22 (false makes: 0)`; `If counted in scope: in-scope misses would be 8 + 22 = 30`. Of the 22, 9 are in the single-ball Hardwick games and 13 are in the multi-ball Bandits practices (`experiments/results/shot_camera_stillness.md`).
4. **Get fixed-camera misses.** Public options are thin (13 Nov search): stock sites have short clips, mostly makes, with licences that don't clearly allow this use; Roboflow sets are single images, not video; research datasets (BASKET, PL-NBA) are broadcast highlights with unclear licences. **Own filming is the realistic route** and settles Gate B at the same time (spec in section 12). Borrowing a friend's phone and one 2-hour session is enough.
5. Only then: ideas for catching more makes when the ball is invisible at the rim, all keeping ShotVision's strict checks (net movement, a short look-ahead, hoop lock for a fixed camera, fine-tuning on blurred balls).

Phase 2 groundwork (release moment, shooter position) can start as experiments only while waiting for footage, as long as nothing ships and `shot_logic/` is untouched.

---

## 11. Roadmap

| Phase | What | Gate |
| --- | --- | --- |
| 1. Make or miss (now) | One shooter, one fixed camera | A, B, C (section 4) |
| 2. Two or three | Release moment, shooter position, court mapped once per setup | Correct 2/3 on a labelled set incl. shots on the line |
| 3. Shot type | Layups, pull-ups, fade-aways. Rules first, learned model later | Each type reliable on unseen clips |
| 4. Multiple players | Credit each shot to its shooter, per-player stats | Matches a hand-counted game |

Backlog after Phase 4: shot selection feedback, tendencies, hot zones, possession tracking, auto highlights, pickup analytics, ask your stats in plain English, one combined app.

---

## 12. Filming plan (when a court is available)

60 fps, shutter 1/500 s or faster, camera about 2.5 to 3.5 m high near half court, facing the hoop. iPhone: the free Blackmagic Camera app locks fps and shutter.

| Set | Makes | Misses | Notes |
| --- | --- | --- | --- |
| Main | 60 (half touching rim or backboard) | 80: 20 front-rim, 20 back-rim, 15 in-and-out, 10 side rim-out, 15 airball | Plus 20 non-shots near the rim |
| Blur control | 20 | 20 | 30 fps auto exposure |
| Angle control | 20 | 20 | 45° wing |
| Held out | One full session | | Never used for tuning |

Say the result out loud on every shot. Film a 2-minute test clip first, because gyms can be dim. Check the capture layer respects rotation metadata on vertical video.

---

## 13. Decisions and rules

| Decision | Why |
| --- | --- |
| Trained detector, not colour | Orange ball on an orange floor, motion blur |
| Miss-biased logic | False makes are worse than missed makes |
| Learn from open repos, don't copy unlicensed code | avishah3 and others have no licence. Ideas yes, code no |
| Never extract models from closed apps | Hooper, Veo, BallerCam are proprietary |
| Public footage only from clear licences | Creative Commons, Roboflow or Kaggle datasets, Pexels or Pixabay. Not YouTube downloads |
| Public footage is development data only | Final check is Danny's own held-out footage |
| Thresholds in seconds | Works at 30, 60, 120 fps |
| Gate A judged on in-scope footage | Phase 1 promises a fixed camera and one shooter. Out of scope is a stress test |
| Line-through-the-rim rejected | Measured: false makes on front and back-rim misses |

Working preferences:
- Diagnose with measurements before changing code. "No new model, just better data" is a valid answer.
- Don't tune to pass a gate. Don't break passing tests. Experiments go in `experiments/`.
- Check every repo's licence before using its code.
- Push at the end of every session.
- Tables for options and comparisons. Describe features by what they do.
- Once decided, execute rather than re-deliberate.
- UK spelling, no em dashes in written copy.

---

## 14. Files that come with this handover

| File | What it is |
| --- | --- |
| `HANDOVER.md` | This file |
| `PLAN_1_score_split.md` | Completed plan: camera split, held-out game. A template for future plans |
| `PLAN_3_phase1_polish.md`, `PLAN_3_decisions.md` | Completed: two-part plan with an owner decision stop in the middle |
| `PLAN_4_tidy_and_still_shots.md` | Next plan |
| `PLAN_2_line_crossing_experiment.md` | Completed plan: line-crossing experiment, run in a worktree in parallel |
| `PROMPT_for_plan_runner.md` | Generic runner prompt for cheaper models. Fill in the "Run:" line and add session notes for anything the plan gets out of date |

All plans are in the repo at `docs/plans/`. This handover is in the repo root.

## 15. References

- Research and licences: `docs/tracking-research.md` (TrackNet/WASB, clip classifiers, trajectory fitting repos, net motion, products).
- avishah3/AI-Basketball-Shot-Detection-Tracker (source of the model and video_test_5; no licence; claims 95% with no method).
- Related project: Basketball Statistics Similarity (repo GreenFN), NBA player comparisons. Possible future link: feed this tracker's stats into it.