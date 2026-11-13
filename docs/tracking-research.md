# Tracking Research: unblocking Phase 1 make/miss

Rewritten 2026-11-04. Earlier versions, from 2026-07-24 and 2026-08-12, diagnosed an arming or scoring bug. That diagnosis was later shown to be a downstream effect of ByteTrack dropping the fast ball, and it is superseded. They remain in git history (e.g. `git show 444544e:docs/tracking-research.md`).

**Update 2026-11-05:** Gate A on public footage fails, and the dominant failure there is the tracker following the wrong object (Section 0). Read that first.

**Bottom line (2026-11-04):** no new model is justified by the evidence today, and neither is more threshold tuning on third-party clips. The measured failures are makes lost while the ball is invisible at the rim. Every logic change that would rescue them is make-favourable, and the 8 distinct labeled misses we have cannot show such a change is safe. The highest-value next step is **better input plus a real miss set**: film our own camera at 60 fps with a fast shutter, using the shot list in "Do this next".

---

## 0. Gate A on public footage (2026-11-05) — FAIL

Run: `python scripts/evaluate.py --report` (duplicates excluded). Data is dev-only:
- the 11 legacy GitHub clips;
- one full CC BY 4.0 high-school game: elevated sideline broadcast camera, pans and zooms, 1080p60;
- two CC BY 3.0 practice clips: floor level, 60 fps.

Provenance is in `sample_clips/SOURCES.md`. The new labels are **Claude-made from contact sheets** (subagents, with Claude spot-checking every pipeline/label disagreement that involved a make). **No human has verified them.**

| | Result | Gate |
|---|---|---|
| Makes counted | **90/137 (65.7%)** | ≥ 90%: **fail** |
| False makes | **2 / 46 distinct misses** (exact 95% upper bound 13.1%), 0 spurious makes | 0: **fail** |
| Spurious shots | 13, all resolved MISS (the pipeline arming on lobs, passes and camera pans) | |

| Source | Makes counted | False makes / misses |
|---|---|---|
| Hardwick game (panning broadcast) | 21/43 | 1/31 |
| Bandits practice (multiple balls) | 13/31 | 1/7 |
| Legacy GitHub clips | 56/63 | 0/8 |

By miss type (misses / false makes): front_rim 20/0, back_rim 13/0, side_rim_out 6/0, airball 1/0, other 6/2. Both false makes are typed "other". There are no labeled in-and-outs, so the in-and-out exit is still unexercised on real footage.

**The two false makes (both checked frame by frame):**
- **Hardwick card 18 (f39311):** the ball hits the rim and bounces high above the backboard; the scoreboard stays 6-0. The pipeline scored MAKE at f39440 after the tracker followed a dark patch on the backboard.
- **Bandits 01 card 3 (f2251):** during a fast pan the ball falls away left of the rim. The pipeline scored MAKE at f2279 after the tracker followed **a man's head** under the hoop.

In both, the **tracker followed a non-ball object** below the rim, and the state machine took it for the ball dropping through. This is the same weakness iteration 6 patched for heads (track identity), now under a moving camera.

**Lost makes, by exit reason:** never armed 41, miss_occlusion_gap 3, miss_rim_out_sideways 2, miss_below_without_inner 1.

The never-armed makes on the public clips, by layer (`experiments/shot_diagnostics.py` logic):

| Layer | Count | What it means |
|---|---|---|
| **TRACKER** | 24 | the detector saw the ball above the rim at conf ≥ 0.15, but the tracker was following something else |
| DETECTOR | 8 | the ball is never confidently above the rim |
| LOGIC | 5 | followed above the rim, but no arm (descent/streak rule) |

The traced TRACKER cases share one mechanism: **the tracker locks onto another confident ball-like object and won't switch.**
- Examples are a ball resting on the floor or a rack (box width 72 px against the shot ball's ~20 px), or a second ball in a practice.
- The switch rule only lets go of a followed object that is weak or stale.
- The stationary filter can't catch a resting ball when the camera pans, because the ball moves on screen.
- The single-ball assumption, true on the solo-shooter clips we tuned on, fails with several balls, warm-ups, racks and a moving camera.

**What this changes:** the next fix is not detection, thresholds or 60 fps. It is **shot-centric ball selection**: choose or arm on the ball candidate that approaches the hoop, rather than one global "followed ball". It needs these guards:
- size consistency with the hoop (a 72 px object is not a 20 px ball near a 40 px rim);
- no adopting a below-rim object that wasn't seen coming from above (this is what produced both false makes);
- per-candidate tracks, so a second ball can't replace the shot ball.

This is a tracker change in the tested pipeline, so per the stage rules it was **not** made. It's the recommended next step, to be validated with this same Gate A report: 0 false makes is required, and the tracker change must not lower the legacy 56/63.

**Limits of this measurement:**
- **Labels:** made by Claude, not a human. 33 windows were marked can't-tell and dropped.
- **Miss count:** 46 distinct misses, short of the 50 target. Bandits 03 (98 cards) is unlabeled, and 20 more CC BY 4.0 Hardwick games are on Commons.
- **Candidate recall:** candidates come from the detector, so a make it never sees near the hoop gets no card and no label. That biases makes counted upward on the game, not downward.
- **Camera:** the game camera pans. It approximates "elevated, far from the hoop", but it is not the fixed camera Phase 1 targets.

### 0b. After the tracker fix (2026-11-05, commit 5670a1e onward)

You approved the fix. It adds shot-centric selection, size-consistent association using the median recent box width, and "no hoop, no shot" (§0). The evaluator now also matches each resolution to the label whose **end** is closest. Previously the first result in the window took it, and in multi-ball practice that was often another ball's.

| | Before fix | After fix |
|---|---|---|
| Makes counted (same 137 makes) | 90 | **107** |
| False makes (46 misses) | 2 | **0** |
| Legacy GitHub clips | 56/63 | 56/63 (every shot's outcome unchanged) |

**First clip not used in development: Bandits practice 03** (CC BY 3.0; 55 labeled makes, 11 misses). Labeled after the fix was written.
- Makes counted: 30/56.
- False makes: 0 on labeled misses, **1 spurious make**.
  - **f10473: a ball thrown close to the camera passes in front of the hoop.** It is 0.82–1.11× the hoop's width, against 0.43–0.50× for balls through the same hoop. It was first seen at rim level, armed for 7 frames and scored.
  - This is the 2D depth-ambiguity case the roadmap calls out. Measured on all 133 counted makes, neither fixed cue separates it:
    - ball/hoop width at the rim reaches 0.8–1.05 for real makes (the net inflates the box);
    - half of real makes are first seen ≤ 1 box height above the rim.
  - With one example, a threshold would be fitted to that example, so none was added. A real fix needs a depth cue (occlusion order: is the net drawn over the ball; or ball size compared with balls that went through this hoop) and more in-front examples.

**Totals with Bandits 03:** 132/193 makes (68.4%), 0/57 labeled misses scored MAKE, 1 spurious make (95% upper bound 8.1%). Gate A still **FAILS**, on make rate and on that 1 false make.

**Where makes are still lost:**
- Bandits 03 is a crowded practice with two or three balls at the rim at once.
- On the Hardwick game (23/43) the hoop is often lost or misdetected during pans. The no-hoop rule now cancels those shots rather than guessing.
- A wall mural produced a false "hoop". The confidence bar on shot-centric switches stops its "ball" from scoring.

### 0c. Split by camera class (2026-11-06)

Gate A now judges in-scope clips only (fixed camera, single ball). Each clip's camera is measured, not guessed, by `experiments/camera_profile.py` (hoop motion, zoom, multi-ball), and the class is stored as `camera_class`/`ball_count` in `labels.json`. Out-of-scope clips (panning broadcast, multi-ball practice) are a stress test without pass/fail.

| Camera class | Makes counted | Make rate | False makes / misses | 95% upper bound |
|---|---|---|---|---|
| fixed/single (in scope) | 21/22 | 95.5% | 0/6 | 39.3% |
| fixed/multi | 0/0 | 0.0% | 0/0 | 100.0% |
| moving/single | 84/136 | 61.8% | 4/62 | 14.2% |
| moving/multi | 53/86 | 61.6% | 1/17 | 25.0% |
| unclassified | 0/0 | 0.0% | 0/0 | 100.0% |

The in-scope gate passes (95.5% ≥ 90%, 0 false makes). The in-scope miss set is only 6, so the false-make rate cannot be shown to be low yet. All 5 out-of-scope false makes are spurious: 4 in the held-out Enosburg game and 1 in a Bandits practice.

### 0d. Line-through-the-rim side by side (2026-11-06)

Reimplemented the avishah3 "line through the rim" method from a description (no code copied) and ran it side by side with ShotVision on cached detections. The line method gains only 2 makes over ShotVision (160 vs 158) but costs 18 false makes and 28 spurious (95% upper bound 63.4%). The gap limit and the arc do not remove those false makes; only the strict make zone does, and it costs 10 makes. The most conservative hybrid (H1) rescues 5 makes but adds 2 false makes and 1 spurious. No variant is at 0 false makes, so the line method is not a safe rescue for the invisible-at-rim makes. Full results: `experiments/results/line_crossing_2026-11-06.md`.

### 0e. Phase 1 polish (PLAN_3 Part A, 2026-11-09)

The in-scope gate now needs at least 50 in-scope misses to pass, so with 6 it prints `NOT ENOUGH MISSES TO JUDGE (6 < 50)` instead of PASS (a false make or a make rate below 90% still prints FAIL). Review sheets (`experiments/review_sheets.py`) and a headless live check (`experiments/live_check.py`) now exist, and the owner's decisions on them are pending in `docs/plans/PLAN_3_decisions.md`.

Hoop movement evidence for the five GitHub clips tagged "moving" (and `lf_back` for comparison), printed by `review_sheets.py camera`:

| clip | frames_with_hoop | share_with_2plus_hoops | max_jump | camera_class |
|---|---|---|---|---|
| video_test_5.mp4 | 3165 | 0.0000 | 0.90 | moving |
| aggie_NathanBBall.mov | 776 | 0.0000 | 0.82 | moving |
| lf_alan.mp4 | 512 | 0.0000 | 1.81 | moving |
| artur_vid29.mp4 | 881 | 0.0000 | 2.31 | moving |
| kyle_test_video.mp4 | 353 | 0.0000 | 1.49 | moving |
| lf_back.mp4 | 1159 | 0.0000 | 0.18 | fixed |

**Owner review results (PLAN_3 Part B, 2026-11-12).** The owner re-tagged three of the five "moving" clips as fixed (`video_test_5`, `aggie_NathanBBall`, `artur_vid29`: background stays still). `lf_alan` (perspective shifts) and `kyle_test_video` (camera moves) stay moving. The owner confirmed all four unlabelled Enosburg pipeline makes (f35060, f125017, f201606, f207518) as real makes, and they were added as labels with start/end set to frame -48/+6 to match that game's other MAKE labels. Nothing changed in scoring, so only the grouping and the labels moved.

| camera class | makes counted/makes | make rate | false makes/misses | 95% UB |
|---|---|---|---|---|
| fixed/single | 55/60 | 91.7% | 0/8 | 31.2% |
| fixed/multi | 0/0 | 0.0% | 0/0 | 100.0% |
| moving/single | 54/102 | 52.9% | 0/60 | 4.9% |
| moving/multi | 53/86 | 61.6% | 1/17 | 25.0% |

All clips: 162/248 makes (65.3%), 0/85 labelled misses scored MAKE, 1 spurious make (Bandits practice). In-scope verdict: NOT ENOUGH MISSES TO JUDGE (8 < 50). Stress test: makes 107/188, false makes 1/77.

Live check (owner, 2026-11-12): recorded clip `lf_shot_detection.mp4` gave `COMPARE: SAME`, 122.92 processing fps against 30.00 source fps. The laptop webcam ran at 29.23 processing fps against a reported 15.00 source fps (no ball in view; 1 phantom shot resolved MISS). Follow-up, not fixed: the webcam reported 15 fps but delivered about 29, and shot-logic timings use the reported fps, so live windows would be about half as long as intended.

### 0f. Still-camera shots inside moving-camera clips (2026-11-13)

PLAN_4 step 5 (`experiments/shot_camera_stillness.py`, report only, cached detections). For every labelled MAKE or MISS it measured the camera in the window from 1.0 s before the label's start to 0.5 s after its end, with the clip-level hoop measures and thresholds applied to that window (`hoop_seen >= 0.8`, `move_p95 < 0.5`, `size_ratio < 1.3`). It changes no tag, label or gate. Full results with the list of every still miss: `experiments/results/shot_camera_stillness.md`.

**Table A: shots taken while the camera was still, by the clip's camera class**

| camera class | makes still / total | misses still / total |
| --- | --- | --- |
| fixed/single | 54/60 | 8/8 |
| moving/single | 8/102 | 9/60 |
| moving/multi | 57/86 | 13/17 |
| **all** | 119/248 | 30/85 |

**Table B: still shots only, by clip**

| clip | camera class | still makes counted / still makes | false makes / still misses |
| --- | --- | --- | --- |
| aggie_NathanBBall.mov | fixed/single | 4/4 | 0/1 |
| artur_vid29.mp4 | fixed/single | 2/2 | 0/1 |
| chonyy_one_score_one_miss.mp4 | fixed/single | 1/1 | 0/1 |
| chonyy_sample_video.mp4 | fixed/single | 1/1 | 0/0 |
| chonyy_two_score_three_miss.mp4 | fixed/single | 2/2 | 0/3 |
| kyle_test_video.mp4 | moving/single | 0/1 | 0/0 |
| lf_alan.mp4 | moving/single | 1/2 | 0/0 |
| lf_back.mp4 | fixed/single | 9/9 | 0/1 |
| lf_shot_detection.mp4 | fixed/single | 8/9 | 0/1 |
| public/commons_bandits/bandits_practice_02.webm | moving/multi | 26/28 | 0/6 |
| public/commons_bandits/bandits_practice_03.webm | moving/multi | 19/29 | 0/7 |
| public/commons_hardwick/hazen_girls_v_enosburg_2025-12-12.webm | moving/single | 2/3 | 0/4 |
| public/commons_hardwick/hazen_girls_v_lyndon_2026-02-04.webm | moving/single | 2/2 | 0/5 |
| video_test_5.mp4 | fixed/single | 22/26 | 0/0 |

**Table C: still misses by miss type**

| miss type | still misses | false makes |
| --- | --- | --- |
| back_rim | 6 | 0 |
| front_rim | 13 | 0 |
| other | 5 | 0 |
| side_rim_out | 6 | 0 |
| **all** | 30 | 0 |

Still-camera misses outside fixed/single clips: 22 (false makes: 0)  
If counted in scope: in-scope misses would be 8 + 22 = 30

Sanity checks: the totals match the scoreboard (248 makes, 85 misses). 6 of the 68 shots in `fixed/single` clips are not still (`video_test_5` 4 of 30, `aggie_NathanBBall` 1 of 6, `artur_vid29` 1 of 4); no threshold was changed. Owner decides whether these still-camera misses count towards the in-scope set.

---

## 1. Measured diagnosis

### How it was measured
`experiments/shot_diagnostics.py` replays the cached raw detections (`experiments/.cache/detections`; no model load with `--cache-only`) through the real `BallTracker`, `RimTracker` and `ShotStateMachine`, exactly as `scripts/evaluate.py` does. For each resolved shot it records:
- the exit path;
- the last 4 confirmed ball positions before resolution, in rim units: `rx` = offset from the hoop centre in hoop-box widths, `ry` = depth into the hoop box in box heights (0 = box top, 1 = box bottom);
- the number of no-ball frames just before resolution;
- the longest confirmed-ball gap while the shot was armed.

For every labeled shot it gets wrong, it prints a per-frame trace of the raw detection versus the followed ball versus the state, and names which layer lost the shot: detector, tracker or logic.

Data: 11 third-party clips, 75 labeled shots (65 makes, 10 misses), labels in `sample_clips/labels.json`. **The data is less independent than it looks:**
- `chonyy_two_score_three_miss` contains the 4 shots of `chonyy_two_score_two_miss`.
- `chonyy_one_score_one_miss`'s miss is near-identical to one of them.

That leaves about 71 distinct shots and **8 distinct misses (possibly 7)**.

### Results (baseline, current `main`)

| Exit path | Label | Got | Count |
|---|---|---|---|
| make_confirmed | MAKE | MAKE | 58 |
| miss_below_without_inner | MISS | MISS | 8 |
| miss_rim_out_sideways | MISS | MISS | 2 |
| miss_occlusion_gap | MAKE | MISS | 1 (vt5 f2597) |
| miss_occlusion_gap | (unmatched) | MISS | 1 (vt5 f3156: actually the f3104 make, resolved 27 frames after its label window, so the scorer counts it as unresolved plus a spurious shot) |
| miss_rim_out_sideways | MAKE | MISS | 1 (lf_shot f600) |
| any timeout path | — | — | **0** |
| never armed | MAKE | — | 4 (vt5 f211, vt5 f1906, lf_alan f624, kyle f88) |

- **All 10 labeled misses resolve with the ball in view.** They had 0 no-ball frames at resolution and were decided by a seen crossing outside the inner gate, or by the ball dropping below without one. The ball disappears only on makes.
- **On the 58 counted makes, the longest gap in confirmed ball while armed** has a median of 5 frames and a max of 21. In 40 of the 58, low-confidence "weak" boxes carried the shot through the net.

### The 7 failures, by cause

| Shot | What the trace shows | Layer |
|---|---|---|
| vt5 f211 | The ball is confidently seen on its descent to `rx` 1.18-1.34 above the rim, just outside the arming alignment window (abs `rx` ≤ 1.0). It then vanishes for 7 frames (blur over the backboard) and reappears inside the band at `rx` −0.2, dropping through. It never armed. | Detector gap + arming window |
| vt5 f1906 | The same pattern: one aligned, confident above-rim frame (2 are needed), then 10 frames with nothing. | Detector gap + arming rule |
| vt5 f2597 | Armed. The ball is lost at the rim. The tracker weak-continues onto a stationary false positive under the hoop. The real ball reappears confidently inside the hoop as **a new track id**, and the state machine (by design, iteration 6) discards other identities, so the shot ends occlusion-gap MISS. | Tracker identity |
| vt5 f3104 | Armed, last confirmed at the top of the hoop box inside the inner gate. It is never re-acquired on its identity after 1 weak frame, so the shot ends occlusion-gap MISS 25 frames later. | Detector gap (below the net) |
| lf_shot f600 | Armed. The ball is invisible for 13 frames inside the rim/net, then reappears at `rx` −0.5. The fitted crossing (−0.45) falls outside the inner gate (abs `rx` ≤ 0.35), so it resolves MISS sideways. The pre-gap path pointed the other way, so the net or rim deflected it. Ambiguous in 2D. | Logic (ambiguous) |
| lf_alan f624 | The ball enters from out of frame. 18 frames are missing, then 1 aligned above-rim frame, then it drops cleanly through. It never armed. | Framing + arming rule |
| kyle f88 | A huge, close, blurred ball, never detected above the rim at any confidence. First seen already below. | Detector |

### Your hypothesis, tested
> "The ball isn't detected in the frames where it passes through the rim, so the miss-biased state machine times out and defaults to MISS."

- **Half right.** Detection gaps at the rim are behind 6 of the 7 failures. Blur over the backboard and occlusion in or below the net cause them, and the measured gap lengths are 7-25 frames.
- **The mechanism is wrong.**
  - **0 shots resolve by timeout.**
  - 4 of the 7 never arm at all. Those makes are silently uncounted, not scored as misses.
  - 2 end through the occlusion grace (one of them because of a tracker identity switch).
  - 1 is a geometric call on a net-deflected ball.
- **Other parts of the summary are out of date.**
  - The "~11% detection rate" dates from the ByteTrack era. Ball coverage is now 38-81% of frames per clip and about 76% inside make windows.
  - The test count is now 111 passing, plus 2 that load the real checkpoint.

### Threshold tuning is exhausted on this data (measured)
These single-knob sweeps ran through `scripts/evaluate.py --set` on all 75 labeled shots:

| Change | Correct | False makes | Effect |
|---|---|---|---|
| baseline | 68/75 | 0 | |
| `align_tolerance_ratio` 1.0 → 1.5 | 68 | 0 | +vt5 f1906, −lf_shot f272 (a make turns into a sideways miss because the crossing fit changes) |
| `align_tolerance_ratio` → 2.0 | 69 | 0 | +f211, +f1906, −lf_shot f272 |
| `descent_min_frames` 2 → 1 | 69 | 0 | +f1906, +lf_alan, −lf_shot f272 |
| `prearm_max_missed_frames` 1 → 3 | 68 | 0 | no change (same 7 failures) |
| `occlusion_grace_frames` 12 → 20 | 68 | 0 | no change |
| `inner_bound_shrink` 0.15 → 0.05 | 66 | **2** | two real misses (aggie f66, lf_shot f959) become makes |

- Loosening arming wins one shot and loses another.
- Widening the inner gate immediately produces false makes. **Two of the 8 distinct misses sit right at the gate edge** (`rx` 0.36-0.45 at the crossing).
- The safety margin is thin, so "calibrate and tune thresholds" on these clips is not the answer either.

### One targeted logic change, measured
`experiments/track_adopt_experiment.py` lets an armed shot adopt a new tracker identity, but only when two conditions hold:
- the armed ball's last *confirmed* point was near the hoop;
- the new observation is confirmed and inside the hoop region.

Result: **69/75, 0 false makes.** It fired exactly once, on vt5 f2597, the case it targets. It is small and principled, but it is untested against misses: no labeled miss has an identity switch at the hoop. It is queued, not applied.

---

## 2. Per-source findings

**V** means verified (code, LICENSE file, paper or GitHub API read by a research subagent this session). **I** means inference. Licenses come from the subagents' API/LICENSE checks. I did not re-check them myself.

### Multi-frame heatmap ball detection (TrackNet family and WASB)

**What it does:** a heatmap regressor on 3-8 stacked consecutive frames, built for small, fast, blurred balls.

| Repo | License (V) | Basketball? | Framework / CUDA (V) |
|---|---|---|---|
| yastrebksv/TrackNet (unofficial V1, arXiv 1907.03698) | none: learn only | no (tennis) | PyTorch, `device='cuda'` hardcoded; plain Conv2d |
| TrackNetV4/TrackNetV4 (arXiv 2409.14543; not part of yastrebksv) | MIT | no (tennis, badminton) | TensorFlow/Keras |
| qaz812345/TrackNetV3 | MIT (text also covers checkpoints) | no (shuttlecock) | PyTorch; `predict.py` supports MPS, `test.py` has `.cuda()` calls |
| **nttcom/WASB-SBDT** (BMVC 2023) | **MIT** | **yes**: NBA set, 244k train frames | PyTorch; `detector.py` asserts CUDA and uses DataParallel; model is plain conv, so MPS port looks trivial (I) |

**Applies:**
- **WASB basketball numbers (V):** F1 80.6-82.6 at a 4 px threshold, about 22-30 FPS on a V100.
- **Basketball is its hardest sport**, and its own basketball failure example is a blurry ball.
- **Shot-window use:** it could run only in a rim crop during a shot window from a ~1 s frame buffer (I).

**Doesn't apply / blockers:**
- **The shipped basketball weights are trained on the SAM NBA dataset**, which is academic-only and available on request. Treat the weights as research-only.
- **Broadcast domain:** a panning camera with a tiny ball.
- **Speed:** unknown on an M2.
- **Gaps:** it would plausibly fill 6-10-frame blur gaps over a backboard, but not a ball inside the net (I).
- **False makes:** a heatmap always outputs a peak, and the hoop-ROI crop experiment on 2026-11-03 already showed that extra detections near the rim add false makes.
- **Retraining:** likely a few thousand labeled frames from our camera (I).

**Verdict:** not now. Revisit if capture settings and YOLO fine-tuning plateau.

### Make/miss clip classification (NohanJoemon/Basketball-video-classification)

**What it does (V, code read):** no rim crop and no temporal model. It takes 1 full frame per second, runs VGG16 features and a dense head, then averages. It was trained on 2,194 clips and scores 77.6% test accuracy, calling 14.8% of non-scoring clips scoring. Keras/TF.

**License:** none, so learn only.

**Applies:** the *idea* of a rim-crop clip classifier as a second opinion. It would be invoked only when an armed shot loses the ball near the rim, which is the measured failure. Under that design:
- it could **veto** makes freely;
- it could **confirm** a make only above a strict threshold;
- it would never overturn a seen miss.

**Lighter options (V licenses):** MobileNetV3 or EfficientNet with temporal pooling or TSM (BSD/MIT) avoids conv3d. That matters because conv3d on MPS has had correctness and speed bugs (PyTorch #197114, #192213). X3D (Apache-2.0) and MoViNet-A0 (MIT port) are viable.

**Doesn't apply:**
- **No published minimum dataset size** for rim-crop classifiers.
- **Public make/miss classifiers score 78-95%**, which is not safe enough to count makes alone.
- **Datasets:** PL-NBA (CC BY-NC) and BasketEvent are broadcast footage and non-commercial or unlicensed.

**Verdict:** later. It needs hundreds of labeled clips from our camera.

### Trajectory fitting (avishah3/AI-Basketball-Shot-Detection-Tracker, nvan21/Basketball-Shot-Detection)

**What they do (V, code read):**
- **avishah3** fits a 2-point line between the last point above the rim and the next buffered point. That point can be on the far side of any gap. It also adds a hard-coded 10 px "rebound zone" outside the rim, which is a false-make source.
- **nvan21** derives pixels-per-inch from a white backboard contour, fits velocity over the last 3 points, forward-simulates under gravity, and says "going in" if 15/1000 simulated points hit the rim box. It has no gap handling and no counting.

**License:** neither repo has one, so learn only. Our checkpoint comes from avishah3, which is why it has no clear license.

**Applies:**
- Both repos quietly bridge gaps with 2-point straight lines, and that is why they report high numbers on easy clips. **Our 0 false makes matters more than their claimed 95%.**
- The sound version is a pre-gap-only fit in time, with x(t) linear and y(t) quadratic under a gravity prior scaled from the rim size. Use it as a *check*: predict into the post-gap frames, and treat a large residual as rim or net contact, which falls back to MISS (I).

**Doesn't apply:**
- It never resolves depth, so front-of-rim versus through stays ambiguous.
- It breaks on rim or backboard contact and net drag, which is exactly where our gaps are.

**Verdict:** possible as a veto or consistency check inside a gap-bridging rule. It must never be the sole evidence for a make.

### Ball/hoop interaction and highlights (iamyb/shotcut)

**License:** MIT (V).

**What's there:** the repo is only a README, a LICENSE, images and a 445 MB Windows binary. There is no source, so nothing can be reused or learned.

**Highlights feature:** the future highlights feature needs no outside code. Every `ShotResult` already has a frame index, so cutting clips is I/O.

### Net motion as a signal

**Prior art (V):**
- NEX/HomeCourt patent US11157742B2 counts a make when there is "sufficient" hoop-net movement, even with the ball occluded. It finds pixel changes by background subtraction or a CNN, and treats a ball bouncing back above the hoop after net motion as "not finished".
- Ballogy's US11839805B2 uses orange ball pixels mixed with white net pixels, plus net shape change.
- ShotTracker's old net-accelerometer patent separates make impulses from rim rolls.
- No open-source implementation was found.
- **Both patents are close to this idea. Get advice before shipping anything near-identical.**

**Applies (I):**
- Frame differencing in a small net ROI costs under 1 ms. The ball's own box must be masked out, because a ball passing in front of the net also changes pixels there.
- Timing matters: net motion must *follow* an approach inside the inner gate.
- It targets exactly the in-net gaps we measured (vt5 f3104, lf_shot f600).

**Doesn't apply:**
- It does nothing without a net.
- A rim-out also shakes the net.
- It needs per-angle tuning.

**Verdict:** the best cheap *new signal*, but only as a gated gap-filler. Validate it on our own misses before it can upgrade anything to MAKE.

### Sources not on your list that matter
- **Capture settings (physics, I).** Motion blur depends on shutter time, not frame rate. At 1/30 s a ~5-7 m/s ball smears about 20 cm, close to its own 24 cm diameter. At 1/500 s it smears about 1 cm. 60 fps also halves the per-frame displacement, which helps association. This attacks the root cause of 4-5 of the 7 failures, and it costs nothing in code: it needs only a 60 fps config profile with the frame-count thresholds doubled.
- **Ultralytics fine-tuning guidance (V).** Its default augmentation has no motion blur, so an Albumentations `MotionBlur` must be added. Expect about 1-3k frames from our camera, weighted toward rim and backboard blur (I). This also replaces the unlicensed checkpoint.
- **Hiemann et al., Sensors 2021 (V).** YOLOv3 on small, fast volleyballs with a **frame-difference 4th input channel** reached F1 86-89. A cheap multi-frame cue without adopting TrackNet.
- **JadenS180/basketball-shot-tracker (MIT).** Already mined on 2026-11-03 for the hold, vetoes and stationary filter.
- **Licensing of the stack (V):** `ultralytics` is AGPL-3.0, and the checkpoint has no clear license. Both matter before anything ships.
- **Product practice (V, vendor claims only).** HomeCourt uses one phone camera and net motion (its patent). Noah uses a depth sensor above the rim. ShotTracker uses sensors, and Dr. Dish uses a mechanical switch. No independent accuracy numbers exist for any of them.

---

## 3. Ranked recommendations

Ranked by impact on the *measured* failure ÷ (effort + risk).

| # | Change | Fixes (of 7) | Effort | Risk | Confidence |
|---|---|---|---|---|---|
| 1 | **Capture at 60 fps, shutter ≤ 1/500 s**, with a 60 fps config profile (frame-count thresholds ×2) | blur gaps: vt5 ×3-4, kyle; partly lf_shot | low (camera setting + config) | low | medium. Physics plus the trace evidence, but **not measured**: we have no 60 fps footage |
| 2 | **Film and label our own misses** (≥100, weighted to front/back rim, in-and-outs) | none directly; it is what makes #3-#6 testable | medium (a filming session + labeling) | none | high that nothing below is trustworthy without it |
| 3 | **Track re-adoption at the hoop** (`experiments/track_adopt_experiment.py`) | vt5 f2597 (measured: 69/75, 0 false makes) | very low | low-medium (untested on misses) | medium |
| 4 | **Fine-tune the detector on our blurred frames**, auto-pre-labeled by interpolating the tracker across gaps, with motion-blur augmentation | blur gaps; also domain shift and the checkpoint license | medium-high | medium (new false positives near the rim) | medium |
| 5 | **Gated net-motion gap confirmer** (ball box masked; needs an approach inside the inner gate, then net motion, then reappearance below) | vt5 f3104, possibly lf_shot f600 | medium | **high** (make-favourable; patents nearby; no net = no signal) | medium-low until tested on our misses |
| 6 | Rim-crop clip classifier as veto/confirm | gaps generally | high (hundreds of clips) | medium | low for now |
| 7 | WASB/TrackNet heatmap detector in the shot window | blur gaps | high (port, fine-tune, M2 speed unknown, research-only weights) | medium | low |

**What would change this ranking:**
- If 60 fps footage from our camera still shows 7+ frame blur gaps at the rim, #4 moves up. If #4 then plateaus, #7 comes back.
- If our misses show front/back-rim outs scored as MAKE from half court (the depth problem), the priority becomes a *veto* signal (occlusion order, net motion) before any rescue rule.
- If our footage is almost failure-free at 60 fps, the remaining work is threshold re-validation per camera angle, not new signals.

### The strongest case against #1 (capture settings first)
1. **It isn't measured.** The physics is solid, but the evidence that blur is the cause comes from third-party clips at 30 fps. A phone in a dim gym may not be able to hold a 1/500 s shutter without heavy noise, which could hurt detection more than blur does.
2. **60 fps doubles detection cost.** Detection is about 5 ms per frame per the 2026-11-03 notes, which I did not re-measure. That is fine on the M2 for 60 fps, but the margin shrinks once Phase 3 pose runs.
3. **Every frame-count threshold was tuned at 30 fps.** Doubling them is a guess and needs its own validation.
4. **The ball can still be hidden for 13-25 frames inside the net**, because blur isn't the issue there. Two of the 7 failures (vt5 f3104, lf_shot f600) survive any shutter speed, so #1 cannot get us to 100%.
5. **Fine-tuning (#4) would fix blur *and* the license problem in one go**, and the strict ranking undervalues that.

Even so, #1 comes first: it is nearly free, it doesn't touch code, and the footage it needs is the same footage #2-#5 need anyway.

---

## 4. Do this next

**The change:** film our own camera at **60 fps with a fixed fast shutter (1/500 s or faster)**, and record a 30 fps / auto-exposure control set from the same position. Add a 60 fps config override (frame-count thresholds doubled) under `experiments/`. Then run `scripts/evaluate.py` and `experiments/shot_diagnostics.py` on both sets with the logic unchanged. The 30 fps vs 60 fps comparison measures how much of the blur problem the camera alone fixes. The misses give the first meaningful false-make number from our angle.

**Camera:**
- **Position A (primary):** elevated about 2.5-3.5 m, near the half-court line, facing the hoop. The whole hoop, backboard, shooter and floor are in frame, with room above the rim for the arc. Mount it rigidly; a bump invalidates the run.
- **Position B (angle check):** elevated, at the wing / 45°, roughly 6-8 m from the hoop.
- **Settings:**
  - 1080p (or 4K) at 60 fps;
  - shutter 1/500 s or faster, with exposure locked (needs good light);
  - focus locked on the rim.
- **Control:** the same Position A framing at 30 fps with auto exposure (the phone default).

**Shot list, Position A at 60 fps (the main set; about 45-60 minutes with a rebounder):**

| What | Count | Why |
|---|---|---|
| Clean makes (swish) | 30 | baseline |
| Makes touching rim or backboard (incl. bank shots) | 30 | the blur/deflection cases we fail on |
| Front-rim misses (ball bounces back toward the shooter) | 20 | depth-axis false-make risk from half court |
| Back-rim misses (bounces long, over or off the back) | 20 | same, and the most likely to pass the 2D gate |
| In-and-outs / rim-outs (ball rolls around and out) | 15 | `_passed_through` is never reset after a crossing, so an in-and-out that crosses the inner gate then drops can score MAKE (known code risk) |
| Side rim-outs | 10 | sideways path |
| Short airballs passing *in front of* the rim | 10 | ball in front of the rim/net in 2D |
| Long airballs / over the back | 5 | |
| Non-shots near the rim: rebounds, tips, passes under the basket, ball held up near the rim | 20 | spurious-shot check |

That is 60 makes, 80 misses and 20 non-shots.

**Also record:**
- **Position A at 30 fps / auto exposure:** 20 makes and 20 misses (front, back and in-and-out mixed), for the blur A/B.
- **Position B at 60 fps:** 20 makes and 20 misses (same mix), for the angle check.
- **No net:** if a netless rim is available (many outdoor courts), 20 makes and 20 misses at Position A. Otherwise note it as untested.
- **Held out:** keep one complete session (e.g. a second day) untouched for the Phase 1 exit check.

**Label as you go:** call out "make" or "miss, front/back/in-and-out" on the audio while filming. That makes labeling fast. The labeling page / `labels.json` workflow from 2026-11-03 then applies unchanged.

**How to read the result:**
- **0 false makes on 80 misses** gives a 95% bound of about 4%. This is the first real safety number.
- **If makes-counted at 60 fps is ≥ 95%:** move to the Phase 1 live test.
- **If not:** run `shot_diagnostics.py` on each failure and pick from #3-#5 above, based on the failure's layer.

---

## 5. Self-review

- **Interesting fix over boring fix?** The top recommendations are a camera setting, more footage, and a 10-line identity rule. TrackNet/WASB is ranked last, with reasons. The net-motion signal is the "interesting" one. It is ranked below fine-tuning because it is make-favourable and its main evidence is patents, not data.
- **From READMEs, papers or vendor pages rather than code or data I ran:**
  - every license (subagent API/LICENSE checks);
  - WASB/TrackNet accuracy and speed (the papers);
  - all product claims;
  - the blur physics and the 60 fps benefit;
  - dataset-size estimates;
  - the ~5 ms/frame detection speed (2026-11-03 notes, not re-measured).
- **Measured this session:**
  - the exit-path breakdown;
  - the per-failure traces;
  - the threshold sweeps;
  - the track-adoption experiment;
  - the 111 passing tests.
- **Assumed without checking:**
  - That the user's labels are right. Two lf_back makes were added by Claude on 2026-11-03.
  - That the cached detections still match the current checkpoint. The cache key is the weights *name*, not its hash.
  - That the 4 never-armed traces would resolve MAKE once armed. Partly verified by the align/descent sweeps, which rescued f211, f1906 and lf_alan as MAKE.
  - That blur, not some other detector weakness, explains the vt5 gaps. Based on the 2026-11-03 frame review, not re-viewed this session.
- **Valid conclusion check:** "No new model needed" holds *for now*. But the fix is not threshold tuning either. It is input quality (shutter and frame rate) and a miss set big enough to tune against safely.
