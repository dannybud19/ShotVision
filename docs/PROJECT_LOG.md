# ShotVision Project Log

> This file is updated at the end of every work session — see the most recent dated entry under "What's been done" for current status.

## What's been done

**Phase 1 pipeline (foundational build):** Core capture/detection/tracking/shot_logic/stats/overlay modules built out, establishing the end-to-end pipeline: video capture → YOLO ball+hoop detection → ByteTrack-based tracking → shot-logic state machine → stats aggregation → overlay rendering.

- YOLO ball+hoop detection wired into the pipeline.
- ByteTrack-based tracking added for consistent ball identity across frames (`bytetrack.yaml`).
- Detection threshold tuning performed via `scripts/tune_detection.py`, settling on `imgsz=960`, `conf=0.15` for ball detection, and `rim_conf=0.60` for hoop detection.
- `scripts/tune_detection.py` extended to also measure hoop detection alongside ball detection, not just ball-only.
- `RimTracker` added: automatic rim tracking derived from hoop detections, removing the need for manual calibration.
- `RimTracker` wired into `main.py`, and manual calibration removed entirely from the pipeline.
- `scripts/diagnose_shots.py` wired to `RimTracker` — no calibration file needed, added as a headless per-shot diagnostic tool.
- README updated to reflect the automatic rim tracking pipeline.

Recent commit history (`git log --oneline`), most recent first:

```
9c682a1 Update README for automatic rim tracking
84d34a3 Wire diagnose_shots.py to RimTracker, no calibration file needed
e68ecfd Extend tune_detection.py to measure hoop alongside ball detection
cd4c8e1 Wire RimTracker into main.py, remove manual calibration entirely
b28fce2 Add RimTracker: automatic rim tracking from hoop detections
```


### 2026-07-24 — Missed-makes investigation: measurement + external research

- Measured (via `scripts/diagnose_shots.py`) that real makes are being **dropped**, not misclassified: of 11 real shot attempts across 3 ground-truth-labeled clips, only 6 ever produced a `ShotResult`; the other 5 never armed the state machine at all, and that count of 5 matches the count of expected makes exactly in every clip.
- Extended `scripts/diagnose_shots.py` with "never-armed candidate episode" detection to make this failure mode directly measurable instead of inferred.
- Researched 6 external repos/architectures (TrackNet, two basketball-specific classifiers, two basketball shot-trajectory detectors, one MIT-licensed highlight-extraction tool) plus the "net-motion/pixel-disturbance" idea from patent literature, evaluating license status and relevance to the measured failure mode.
- Wrote `docs/tracking-research.md` with the full measured diagnosis, per-repo findings, and ranked recommendations — top recommendation is a state-machine arm-gate redesign (not a new model), with a TrackNet-style detection booster and a net-motion secondary signal ranked below it.
- Built an `experiments/` arm-gate sweep validator to quantify, from already-captured trace data, how many of the 5 missing makes different window/threshold parameters would rescue — validation results in progress, see `experiments/`.

### 2026-08-12 — Applied in-band arming fix + bounce-up fix, real-pipeline validation surfaces a second bug

- Applied Patch 2 (in-band arming: `self.rim.is_above(y)` → `not self.rim.is_below(y)` in `_update_idle`) and Patch 3 (bounce-up gating: `_update_armed`'s bounce-up check now also requires `not self._passed_through`) to `shotvision/shot_logic/state_machine.py`, per `experiments/proposed_state_machine_patches.md`. Added 3 new tests for Patch 2 and updated 2 existing bounce-up tests for Patch 3's changed behavior (their trajectories now resolve MAKE, not MISS, matching the traced consequence that `MISS_BOUNCE_UP` becomes structurally unreachable). Full suite: 101/101 passing (98 pre-existing + 3 new).
- Re-ran `scripts/diagnose_shots.py` against all 3 ground-truth clips with the real pipeline (not the offline simulation). **Arming is fully fixed**: 11 of 11 real attempts now produce a `ShotResult`, up from 6 of 11, with the original 6 shots' outcomes/reasons unchanged (no regression). **But all 11 now resolve as MISS** — the 5 newly-armed shots all resolve via `MISS_BELOW_WITHOUT_INNER` (`entered_inner=False`), when ground truth expects 5 of the 11 to be makes.
- Diagnosed why (verified against `rim.py`, not inferred): `rim.rim_y` is the midline of the outer band; Patch 2 allows arming from anywhere in-band, not just the top. With ~20% per-frame detection and a 2-consecutive-frame arm requirement, the points seeded into `_recent` at arming are often already at/past `rim_y`, so `_update_armed`'s crossing check (`prev.y < rim.rim_y <= y`) never has a valid "before the line" point to start from — `_passed_through` can never become `True` for these shots. This is a genuinely new bug the offline `simulate_inband_arms` validation could not have caught, since it only checked arming, not downstream scoring.
- Documented in `docs/tracking-research.md` (Update 3, Section 3, and revised Section 4 "do this next"). Not yet fixed — needs a fresh measure-before-fix pass on the crossing-detection logic, same discipline as the rest of this investigation. Changes committed (tests pass, no regression) but the missing-makes problem is not resolved end-to-end.

**Addition, same day — arm-gate sweep completed:** `experiments/arm_gate_sweep.py` ran the real detection/tracking/rim-tracking pipeline over the 3 ground-truth clips, replicated today's `_update_idle` pre-arm logic locally (validated: reproduces the known 0/5 rescued), and swept a windowed (gap-tolerant) variant across N∈{2,3} × W∈{4,6,8,10,15}. Result: **0 of 5 missing makes rescued at every (N, W) tested**, with **0 spurious extra arm events** anywhere in the 3 clips at every setting. This was cross-checked (not a sweep bug) two ways: the baseline replication correctly reproduces 0/5, and a direct count of raw qualifying frames (detected + above-rim + aligned, before descent/consecutiveness) inside each of the 5 best-effort missing-shot windows came back exactly 0 in all 5 cases — a fresh, independent re-run of `scripts/diagnose_shots.py`'s never-armed-episode detector against all 3 clips this session also found 0 episodes beyond the 6 already-resolved shots in every clip, confirming these 5 misses have literally zero above-rim+aligned detections anywhere, not merely a broken streak. **Conclusion: the windowed arm-gate change (research doc's top recommendation) is still low-risk and worth keeping on the roadmap, but it would NOT by itself have rescued any of the 5 measured missing makes — it needs to be paired with either a looser above-rim/aligned test or a real detection-sparsity fix (recommendation #2, TrackNet-style) to address what was actually measured.** Wrote up both this windowed-gate patch and the previously-designed (and, this session, code-flow-verified) bounce-up gating fix as unapplied, ready-to-review proposals in `experiments/proposed_state_machine_patches.md`, including a discovery that the bounce-up fix makes `ResolutionReason.MISS_BOUNCE_UP` structurally unreachable going forward (traced through `_update_armed`'s control flow, not just asserted). Added `tests/test_arm_gate_sweep.py` (3 tests, passing) covering the sweep's own windowed-gate simulation in isolation. Full suite: 98/98 passing (95 pre-existing + 3 new). No files under `shotvision/` were modified — `experiments/arm_gate_sweep.py`, `experiments/proposed_state_machine_patches.md`, and `tests/test_arm_gate_sweep.py` are new files only.

### 2026-11-03 — Root cause found: ByteTrack was dropping the ball; tracker replaced, evaluation harness added

- **Root cause of every "missing make":** `BallTracker` used `model.track()` (ByteTrack). Raw `predict()` detects the ball above the rim at conf 0.79-0.88 for ~12 straight frames per make, but ByteTrack's IoU association never confirms a track for a ball moving ~12-15 px/frame on a ~23 px box, so `track()` output nothing until the ball slowed down in the net. The "~20% detection rate", "makes are never seen above the rim", the arming failure and the 2026-08-12 scoring bug were all downstream of this.
- **Fix (branch `fix/ball-tracking`):** `BallTracker` now runs `predict()` and links the ball by nearest neighbour, with a jump gate scaled by ball width × frames elapsed (`tracker.max_jump_ball_widths`, `tracker.max_gap_frames`). Ball coverage on the chonyy clips went from ~20% to ~75% of frames.
- **Reverted in-band arming (Patch 2):** with the ball visible above the rim, the original stricter above-rim arming scores identically. Removed the unreachable `MISS_BOUNCE_UP` exit.
- **Measured:** the hoop box from this checkpoint spans rim + net (y 174-212 on the chonyy camera, rim ring at ~175-182), so `rim.rim_y` sits mid-net. Not currently causing errors; candidate cleanup.
- **New `scripts/evaluate.py`:** scores the pipeline against `sample_clips/labels.json` (per-shot outcomes, false makes, spurious shots, and ball-coverage smoothness on makes), with cached detections so logic changes replay in seconds. **New `scripts/render_overlay.py`:** headless HUD video for visual review.
- **Result:** chonyy clips (labeled from viewed frames) score 11/11 shots correct, 0 false makes, make-window ball coverage 90-96% with gaps of at most 2 frames.
- **External research** (11 open-source shot trackers, read in code): avishah3, whose checkpoint we use, runs plain per-frame detection with no tracker; abdullahtarek deliberately avoids ByteTrack for the ball. JadenS180 (MIT) reports 28/29 shots with 0 false makes using a ~0.25 s make-confirmation hold, size and steepness vetoes that can only turn makes into misses, and a stationary-false-positive filter. These are queued as loop candidates.
- **Labels:** the user labeled 68 candidate shot windows across 8 more clips on a labeling page (59 makes, 4 misses, 5 not-a-shot; kyle_validation_video dropped at the user's request). Two video_test_5 cards were one shot and were merged. The new tracker found 2 lf_back makes that had no card; both were confirmed by frame review and added, marked as such. Total: 11 clips, 75 shots (65 makes, 10 misses).
- **Evaluate → fix loop** (agreed stop rule: every clip exact, 0 false makes, smoothness passing; cap ~8 iterations). Every iteration kept 0 false makes:

  | Iter | Change | Correct |
  |---|---|---|
  | 0 | baseline (ByteTrack fix) | 52/75 |
  | 1 | velocity-gated association, stationary-object filter (a round "1" sign was detected as a ball 219 times), guarded track switching | 56/75 |
  | 2 | no track switching during the 2-4 frame blur gap at the rim (a shooter's head, conf up to 0.69, was taking over) | 58/75 |
  | 3-4 | gate sized by the followed ball; 24-frame occlusion grace when last seen at the hoop (ball hidden in the net 11-19 frames); arming survives one missed frame; align tolerance 0.6 → 1.0 | 66/75 |
  | 5 | weak (0.03-0.15) boxes continue a followed ball through the net; never arm/cross/resolve | 66/75 (make coverage 70% → 75%) |
  | 6 | track identity (a shot only scores the ball it armed on); strength = best recent conf; velocity over gaps up to 8 frames; gate around last position too | 67/75 |
  | 7 | scoring line at 0.4 of the hoop box (box spans rim + net; midline is mid-net) | **68/75** |

  A subagent measured detection variants on the 12 hardest windows: imgsz 1280 and a hoop-ROI crop each *added* false makes; low conf helped only as continuation.
- **Stopped at iteration 7, stop rule not met.** 5/11 clips pass outright. Of the 7 remaining failures, 6 are makes the detector cannot see (dark ball motion-blurred over the backboard or below the net, ball out of frame, a huge blurred ball on kyle_test_video) at any setting tried. The 7th (lf_shot_detection f600) would need a more make-favourable rule across a 14-frame gap, which 10 labeled misses can't show is safe. Smoothness: average make-window coverage 76%, average longest gap 5.7 frames, but 23 of 65 make windows still fail the strict check (gap ≤ 6 frames, coverage ≥ 60%), almost all because of the net/blur gap.
- **Next:** (1) film and label misses from the target camera (rim-outs, in-and-outs, airballs) so false-make safety is actually measured; (2) fine-tune the detector on motion-blurred ball frames from that camera (scripts/finetune_roboflow.py); (3) re-run scripts/evaluate.py after each.

### 2026-11-04 — Session recovery: measured diagnosis, roadmap rewrite, CLAUDE.md

- Rebuilt context after a lost session. The user's recovery summary was out of date. ByteTrack had already been replaced and PR #1 merged; the score was 68/75 with 0 false makes; detection coverage was ~76% in make windows, not 11%; there were 111 passing tests, not 76.
- New `experiments/shot_diagnostics.py`. It replays cached detections (`--cache-only` never loads the .pt) and reports each shot's exit path, its last confirmed positions in rim units, the gaps, and which layer lost each failure.
- **Measured:** 0 shots resolve by timeout. Of the 7 failed makes, 4 never arm, 2 end through the occlusion grace and 1 resolves sideways. 6 of the 7 involve the ball being invisible for 7-25 frames at the rim. All 10 labeled misses resolve with the ball in view. The vt5 "spurious" MISS at f3156 is the f3104 make resolving 27 frames after its label window.
- **Threshold sweeps:** align tolerance, descent frames, prearm gap and occlusion grace each trade one make for another (best 69/75). Inner shrink 0.15 → 0.05 gives 2 false makes.
- **`experiments/track_adopt_experiment.py`:** adopting a new track id at the hoop gives 69/75 with 0 false makes. It fired once, on vt5 f2597. Queued, not applied.
- **Research** (3 subagents, licenses checked) on WASB/TrackNet, clip classifiers, trajectory fits, net motion, products and patents.
- Rewrote `docs/tracking-research.md` and `docs/ROADMAP.md`, and added `CLAUDE.md`. The user wants make/miss to work from any angle where hoop, ball and person are visible; the roadmap records the single-camera depth limits that come with that.
- **Next:** film our own camera at 60 fps with a fast shutter (shot list in the research doc, "Do this next"), and measure with the logic unchanged.

### 2026-11-04 (later) — Phase 1 stage on public footage: items 1-3 done, 4-5 pending

- **In-and-out:** a ball back above the rim after crossing inside it now resolves as `MISS_IN_AND_OUT`. Before and after: 58/65 makes counted, 0 false makes. The exit never fired on the existing clips.
- **`scripts/label_candidates.py`:** one command turns a clip into a labeling page, and `merge` writes the results into labels.json. Recall: every labeled shot got a card on the 6 clips checked.
- **Frame-rate independence:** all thresholds are now in seconds or per second. The evaluate output is byte-identical on every 30 and 29.97 fps clip. lf_alan (24 fps) changed only in coverage, by 1%.
- **`evaluate.py --report`** prints Gate A. labels.json now has split, source, duplicate and miss_type fields. On the distinct legacy set: 56/63 makes counted (88.9%), 0/8 false makes, 95% upper bound 31%. **Gate A FAIL** on make rate.
- **ROADMAP:** release-moment detection and shooter position moved from Phase 3 into Phase 2.
- **Not done (usage limit):** item 4 (licensed public misses: a search agent was started and then stopped) and item 5 (Gate A on the bigger set).

### 2026-11-05 — Items 4-5: public miss set and Gate A (FAIL)

- **Public footage:** searched Wikimedia Commons and the Internet Archive.
  - Kept a full high-school game (Hardwick Community TV, CC BY 4.0, 1080p60, panning sideline camera) and two Vancouver Bandits practice clips (CC BY 3.0, 720p60).
  - Rejected 4 clips as unusable, and skipped archive.org "CC BY" NBA re-uploads as license-dubious.
  - Provenance is in `sample_clips/SOURCES.md`.
- **Labeling tool:** 3 s cards sampled every 0.1 s, plus an IGNORE ("can't tell") outcome. evaluate.py now allows 1 s after a labeled window, since the pipeline resolves up to ~1 s after the ball leaves the net. Legacy results are unchanged.
- **Labels:** made by Claude subagents from contact sheets (Opus for Bandits, Sonnet for the game, to save tokens). Claude checked every make disagreement and relabeled one card as MISS (the scoreboard didn't change). Not human-verified.
- **Gate A: FAIL.**
  - 90/137 makes counted.
  - 2 false makes in 46 distinct misses, both the tracker following a non-ball object under a moving camera.
  - 41 lost makes never armed; 24 of those are tracker losses (it stays locked on a resting or second ball).
- **No pipeline changes were made** for this (stage rule). The recommended next step is shot-centric ball selection.
- **Not done:** Bandits 03 (98 cards) is unlabeled; 46 misses is short of the 50 target.

### 2026-11-05 (later) — tracker fix and Bandits 03

- **Tracker fix (shot-centric ball selection):** the agreed fix for the Gate A failure. A confident, ball-sized candidate above the rim near its centre takes over from an object that is not approaching the hoop. Size consistency continues or re-acquires a ball only within 2.0 of its median recent width. No arming while the hoop is untracked, and an armed shot is cancelled without a result.
- **Result:** on the dev set, makes 90 to 107 of 137, false makes 2 to 0. Legacy GitHub clips unchanged at 56/63, every shot's outcome the same.
- **Bandits 03 labeled (Sonnet):** 55 makes, 11 misses, 20 ignored windows. The evaluator now pairs each label with the resolution whose end is closest, which fixed multi-ball practice where the first result in the window was another ball's.
- **Gate A with Bandits 03:** 132/193 makes, 0/57 labeled misses scored MAKE, 1 spurious make (a ball thrown close to the camera passing in front of the hoop, the depth case). Still FAIL.

### 2026-11-06 — camera split and held-out game

- **Held-out Enosburg game scored for the first time.** Kept out of the 5 Nov tracker fix. 26/51 makes (51.0%), 0/28 labeled misses scored MAKE, 4 spurious makes. The 4 false makes are all unlabeled shots: f35060, f125017, f201606 and f207518, each make_confirmed. Compared with the Lyndon game (same panning broadcast camera, 23/43 makes, 0 false makes), Enosburg is worse: a slightly lower make rate and 4 false makes where Lyndon had none.
- **Camera profile** (`experiments/camera_profile.py`): measured hoop motion, zoom and multi-ball per clip from cached detections, and wrote `camera_class`/`ball_count` into `labels.json`.
  - In scope (fixed camera, single ball): 21/22 makes counted (95.5%), 0 false makes in 6 misses.
  - Out of scope: 137/222 makes, 5 false makes in 79 misses.
  - Measured disagreements with the "mostly fixed/single" expectation: aggie, video_test_5, lf_alan, artur and kyle all measure moving; bandits_01 measures single, not multi.
- **Gate A report now splits by camera class.** The in-scope gate passes; out-of-scope clips are a stress test without pass/fail. Full report: 158/244 makes (64.8%), 0/85 labeled misses scored MAKE, 5 spurious makes.

### 2026-11-06 — Line-through-the-rim method side by side with ShotVision (PLAN 2)

- Reimplemented the avishah3 "line through the rim" method from a description (no code copied) in `experiments/line_crossing_experiment.py`, with variants L0-L4 (all/best ball, gap limit, strict zone, arc) and hybrids H1-H3 (ShotVision plus a limited rescue). New tests in `tests/test_line_crossing.py`. 141 tests pass.
- Ran it against ShotVision on all 15 distinct labeled clips (244 makes, 85 misses) from cached detections.

| variant | makes | false makes / misses | spurious | 95% upper bound |
| --- | --- | --- | --- | --- |
| SV | 158/244 | 0/85 | 5 | 12.0% |
| L0 | 160/244 | 18/85 | 28 | 63.4% |
| L1 | 155/244 | 17/85 | 23 | 56.5% |
| L2 | 148/244 | 17/85 | 21 | 54.2% |
| L3 | 138/244 | 11/85 | 18 | 43.5% |
| L4 | 118/244 | 12/85 | 16 | 42.3% |
| H1 | 163/244 | 2/85 | 6 | 16.3% |
| H2 | 177/244 | 3/85 | 16 | 31.1% |
| H3 | 175/244 | 4/85 | 15 | 31.1% |

- Conclusion: the line method gains only 2 makes over SV (160 vs 158) but costs 18 false makes and 28 spurious. The gap limit and the arc do not remove those false makes. The most conservative hybrid H1 rescues 5 makes but adds 2 false makes and 1 spurious. No variant keeps 0 false makes, so the method is not safe to adopt.

### 2026-11-09 — PLAN_3 Part A: gate minimum, review sheets, rotation, live check

- **A1:** merged `exp/line-crossing` (merge 4c13da3), reran the experiment with the camera split (SV unchanged: 158/244, 0/85, 5 spurious), pasted the follow-up docs (8a1ac9e), removed the `../ShotVision-exp` worktree (branch kept).
- **A2:** in-scope Gate A needs at least 50 misses to PASS, otherwise `NOT ENOUGH MISSES TO JUDGE (6 < 50)` (90ef637). Only that verdict line changed; exit code is now 1. New `--min-misses` flag.
- **A3:** `experiments/review_sheets.py frames` built sheets for the 4 unlabelled Enosburg makes (41181e4). ffmpeg is not installed, so frames are read with cv2; the hoop boxes line up with the hoop on all 4 sheets.
- **A4:** `review_sheets.py camera` built hoop track sheets for the 5 "moving" GitHub clips and `lf_back` (60c518d). No tags were changed.
- **A5:** `FrameSource` now asks OpenCV to apply phone rotation metadata and exposes `rotation` (4eadeef). All 16 labelled clips have no rotation flag, and the scoreboard is identical. Rotation on a real flagged clip is unverified (no ffmpeg).
- **A6:** `experiments/live_check.py` (335b7cc): headless run with processing fps, latency and compare-to-replay. Not run by the agent; the owner runs it.
- **A7:** `docs/plans/PLAN_3_decisions.md` for the owner (f5d1694).
- Tests: 164 pass, 1 skipped (needs ffmpeg), 2 model tests deselected.

### 2026-11-12 — PLAN_3 Part B: owner review applied

- **Decisions:** the owner re-tagged 3 of 5 "moving" GitHub clips as fixed (`video_test_5`, `aggie_NathanBBall`, `artur_vid29`) and kept `lf_alan` and `kyle_test_video` as moving. The owner confirmed all 4 unlabelled Enosburg pipeline makes as real makes (start/end = frame -48/+6).
- **B2** (64d1fe8): camera tags and `camera_class_source` written to `labels.json`. Shots unchanged. Makes counted stayed 158/244, 0/85 + 5 spurious.
- **B3** (998757a): 4 MAKE labels added to the Enosburg clip. Makes counted 162/248, 0/85 labelled misses scored MAKE, 1 spurious make.
- **Final numbers:** in-scope (fixed/single) 55/60 makes (91.7%), 0/8 false makes, 95% upper bound 31.2%, NOT ENOUGH MISSES TO JUDGE (8 < 50), so 42 more in-scope misses are needed. Stress test 107/188 makes, 1/77 false makes.
- **Live check (owner):** file clip `COMPARE: SAME`, 122.92 fps processing against 30.00 source. Webcam 29.23 fps processing against 15.00 reported, 1 phantom shot resolved MISS. Follow-up, not fixed: the webcam reports 15 fps but delivers about 29, and shot-logic timings use the reported fps. Measure the real frame rate on device sources.
- **Source cast bug** (owner fix 0a5725d): the device index from config arrived as int and broke `FrameSource`; fixed before Part B.
- Correction to the 2026-11-09 entry: ffmpeg is now installed, so the rotation test runs. Tests: 165 pass, 2 model tests deselected, 0 skipped.

### 2026-11-13: PLAN_4: tidy-up, live frame rate, still-camera shot count

- **Step 1** (f85ff61): committed PLAN_4 and the ShotVision `HANDOVER.md`. Baseline matched: 165 tests, 162/248 makes, 0/85 + 1 spurious, in-scope 55/60 and 0/8.
- **Step 2** (2b3ce1d): `evaluate --report` no longer crashes when a lost make has no reason (prints `make lost: no reason recorded`). Report identical. 166 tests.
- **Step 3** (cd94818): removed the test-only `hasattr(self._cap, "set")` guard from `FrameSource`; `FakeCap` gets `set()`.
- **Step 4** (cea20f7): `FrameSource.measure_fps` (2 s, first frame not counted). `main.py` and `experiments/live_check.py` use it for device sources and print `Camera reports ... fps, measured ... fps; using measured.` Report identical. 168 tests. Not run live; the owner reruns the webcam check.
- **Step 5** (d9b7a1c): new `experiments/shot_camera_stillness.py` (report only, cached detections). Headline: `Still-camera misses outside fixed/single clips: 22 (false makes: 0)`; `If counted in scope: in-scope misses would be 8 + 22 = 30`. 119/248 makes and 30/85 misses were taken while the camera was still. 6 of 68 fixed/single shots are not still. 172 tests.
- **Step 6:** docs (this commit): `HANDOVER.md`, `CLAUDE.md`, this entry, `docs/tracking-research.md` section 0f, run log.
- Scoreboard unchanged: 162/248 makes, 0/85 labelled misses scored MAKE, 1 spurious make.

---

## Tools used

- Python 3.12
- `ultralytics` (YOLO) for ball + hoop detection
- Per-frame YOLO detection + gated nearest-neighbour ball association (ByteTrack removed 2026-11-03)
- `scripts/evaluate.py` + `sample_clips/labels.json` as the regression scoreboard
- OpenCV for video I/O and frame processing
- PyTorch on MPS (Apple Silicon) for inference
- `certifi` (SSL workaround, needed for model/weight downloads on macOS)
- `pytest` for testing

Roboflow is referenced as the intended path for a future licensed/custom dataset (see `scripts/finetune_roboflow.py`) but is **not yet in use**.

---

## Model / training status

**No in-house training has happened yet.** State this accurately — do not overclaim.

- `models/basketball_best.pt` is a community YOLOv8 ball+hoop fine-tune pulled directly from `avishah3/AI-Basketball-Shot-Detection-Tracker`. License unspecified upstream — local prototyping only, not for redistribution.
- `scripts/finetune_roboflow.py` is a ready-but-never-run follow-up script for fine-tuning on a properly licensed (e.g. CC BY 4.0) Roboflow dataset.

**Instruction to future self:** update this section the day real training is actually run, with dataset size/source and resulting metrics. Until then, this section should continue to say "no in-house training yet."
