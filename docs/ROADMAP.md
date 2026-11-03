# ShotVision Roadmap

ShotVision's long-term goal is a single-camera basketball analytics system: make/miss, shot value, shot type, multiple players, then decision-level analysis. Each stage builds on the one before it, so **a stage starts only when the previous one meets its exit criteria**. Everything downstream assumes make/miss detection is reliable, and that is still the current blocker.

Status as of 2026-11-03 (PR #1 merged): **68/75 labeled shots correct, 0 false makes** on 11 third-party clips. See `docs/PROJECT_LOG.md` for how we got here.

---

## Stage 1 (current): Make it work: testing and make/miss accuracy

The goal is to prove the counter is reliable **on our own camera**, then make it as accurate as possible. So far everything has been tuned and tested on other people's footage, and only 10 of the 75 labeled shots are misses.

### 1.1 Label tooling in the repo
- Move the candidate-shot finder and contact-sheet generator used for the labeling page into `scripts/label_candidates.py`, so any new clip becomes a labeling page in one command.
- Labels keep flowing into `sample_clips/labels.json` and are scored by `scripts/evaluate.py`.

### 1.2 Film our own test footage
- **Camera:** fixed position, whole hoop in frame with room above it for the ball's arc. **60 fps if possible**, since motion blur causes most remaining failures. Good lighting.
- **Shots to capture:** about 30 makes and **about 30 misses of every kind** (rim-outs, in-and-outs, front rim, back rim, airballs, bank shots), plus non-shots (rebounds, dribbling or holding the ball near the rim).
- Film on **more than one day or angle** if possible, so one session can serve as a held-out test.
- Think ahead to Stage 2: if possible, also try a framing that shows the shooter's feet (see 2.0).

### 1.3 Measure before changing anything
- Label the new footage and run `scripts/evaluate.py` **with the current settings unchanged**. This is the honest test of whether the settings tuned on third-party clips hold up on ours.
- Keep at least one session as a **held-out test set** that is never used for tuning.

### 1.4 Improve accuracy: the shot-tracking loop
- Same discipline as the 2026-11-03 loop: evaluate, diagnose each failure from its frames, make one change, re-run everything, and keep the change only if nothing regresses and false makes stay at 0.
- Candidate techniques from the open-source research (in rough priority):
  - a short make-confirmation hold for in-and-outs;
  - size and steepness checks that can only veto a make (ball passing in front of the rim);
  - re-tuning the hoop-aware occlusion grace for our camera.

### 1.5 Fine-tune the ball detector
- Most remaining misses are a **motion-blurred ball the detector never sees**. No confidence, resolution or crop setting fixed it, so the model itself needs training.
- **Pre-label automatically:** where the tracker follows the ball on both sides of a blurred stretch, interpolate its box through the gap. We then correct the boxes instead of drawing them all.
- Train with `scripts/finetune_roboflow.py` on our frames, plus a CC-BY dataset if useful. Validate on the held-out session.
- This also **replaces the current checkpoint, whose license is unclear**.

### 1.6 Live test
- Run `python -m shotvision.main --source 0` with a phone as a webcam during a real session, and compare the on-screen count to a manual tally.
- Check it keeps up in real time (detection is about 5 ms per frame on the Mac today) and recovers if the camera is bumped (the `r` key re-acquires the rim).

### Stage 1 exit criteria (proposed, to agree before starting)
On the held-out footage from our camera:
- **0 false makes**, or an agreed tiny rate on a large sample;
- at least **95% of makes counted**;
- no spurious shots from non-shot moments;
- a live session count matches the manual tally.

---

## Phase 2: Shot value (2PT vs 3PT)

**What it does:** a one-time setup where you mark a few known points on the court, so the system can translate any spot on screen into a real position on the floor. When you release a shot, it checks where your feet were, works out your distance from the hoop, and decides whether it was a two or a three.

**How it fits the code:**
- **2.0 Camera framing:** the make/miss camera is framed tightly on the hoop, but this phase needs to see the shooter's feet and enough floor to map. Decide early between one wider camera (smaller ball, so harder make/miss detection) and two cameras (one on the hoop, one on the court).
- **Court calibration:** mark 4 or more known floor points once per setup (baseline corners, free-throw lane corners, points on the 3PT arc). This computes a **floor-plane mapping (homography)** from screen to court coordinates. It is stored per camera position, like a one-time version of the old rim calibration, and only valid for points on the floor.
- **Release moment:** taken from the ball tracker, when the ball separates from the shooter just before the upward flight that later arms the shot.
- **Feet position:** the shooter's foot points from pose estimation, or the bottom-center of their person box as a first version. The detector already returns a `person` class.
- **3PT line:** configurable per court (NBA, FIBA, NCAA, high school).
- **Close to the line:** feet within a margin of the line get flagged "uncertain" instead of guessed, in the same spirit as the miss bias.
- **Where it lives:** new `court/` module, plus a field on each `ShotResult` and `StatsTracker` points.

**Exit criteria:** on labeled footage, 2/3 classification is correct on at least about 97% of shots that aren't flagged uncertain, and shots near the line are flagged rather than wrong.

---

## Phase 3: Shot type

**What it does:** the system reads your body's movement during the shot (arms, shoulders, hips, knees) to tell shot types apart: layups, pull-up jumpers, fade-away twos and threes, and so on. It starts with simple rules (e.g. a fade-away is when your body moves away from the hoop as you shoot, a layup is a close, low release), then later learns from clips of you doing each shot type once you've collected enough.

**How it fits the code:**
- **Pose estimation:** keypoints per frame from a pose model, run only around shot attempts to save compute. Options include YOLO-pose (same library, AGPL) and MediaPipe (Apache-2.0).
- **Rules first:** use features such as release height, distance to the hoop (from Phase 2), body motion relative to the hoop at release, jump and gather timing, and dribble before the shot.
- **Learning later:**
  - collect labeled clips per shot type, using the same labeling-page workflow with a shot-type field;
  - train a small classifier on keypoint sequences;
  - keep the rules as a fallback.
- **Where it lives:** new `pose/` and `shot_type/` modules, plus a `shot_type` field on `ShotResult`.

**Exit criteria:** a per-type confusion matrix on held-out clips, with an agreed minimum accuracy per type. Rare types are allowed an "unknown" bucket.

---

## Phase 4: Multiple players

**What it does:** the system follows every player on the court and keeps track of who is who throughout the game. When a shot goes up, it gives credit to whoever had the ball at release, then keeps a running tally of each player's makes, misses, and points. Players get tagged by name once at the start of the session.

**How it fits the code:**
- **Player tracking:** this is where a multi-object tracker (ByteTrack or BoT-SORT) is the right tool. Players are large and move slowly between frames, the opposite of the ball problem that made us drop ByteTrack for the ball.
- **Keeping identities:** add appearance features (jersey color or number, re-identification) so identities survive occlusions and players crossing.
- **Shot credit:** the player whose hands or body are closest to the ball at the release moment (Phase 2 release detection plus Phase 3 hand keypoints).
- **Name tagging:** click or select each player once at session start to attach a name to their track.
- **Stats:** `StatsTracker` becomes per player.
- **Where it lives:** extend `tracking/` with a player tracker; new `players/` module for identity and attribution.

**Exit criteria:** on labeled pickup footage, the shot credited to the correct player at least about 95% of the time, and identity swaps rare and correctable.

---

## Future roadmap

| Feature | What it does | Depends on |
|---|---|---|
| Shot selection analysis | Flags poor decisions, like taking a fade-away when a better shot was available. The main differentiator, but the hardest part, since it needs to know where every defender is. | Phases 2–4, defender positions, a definition of "better shot" |
| Hot zones and tendencies | Shows where on the court you shoot best and worst, and what shots you lean on. | Phases 2–3 |
| Passes vs shots vs turnovers | Tracks what happens with each possession, not just shots. | Phase 4, ball possession tracking |
| Replays and highlights | Automatically clips makes and big moments from pickup games. | Stage 1 (clip around each make); richer with Phases 3–4 |
| Pickup game analytics | Full stat breakdowns for real games, not just solo practice. | Phases 2–4 |

Replays and highlights is the cheapest win once Stage 1 is reliable: every `ShotResult` already has a frame index, so cutting a clip around each make is mostly I/O.

---

## Applies to every stage

- **Measure everything:** each stage gets its own labeled set and a scoreboard like `scripts/evaluate.py`, with a held-out set, before any tuning.
- **Prefer missing a result over getting it wrong:** when unsure, the system should say "uncertain" or count nothing rather than produce a confident wrong answer. That goes for makes, 2/3, shot type and player credit.
- **Module boundaries:** keep `capture/`, `detection/`, `tracking/`, `shot_logic/`, `stats/` and `overlay/` separate, and add new stages as new modules rather than rewrites.
- **Performance:** stay real-time on the Mac. Pose and player tracking are the expensive additions, so run them only around shot attempts where possible.
- **Licensing:**
  - the current ball/hoop checkpoint has no clear license (Stage 1.5 replaces it);
  - `ultralytics` is AGPL-3.0;
  - check any pose or re-identification model's license before adopting it.
- **Privacy:** pickup-game features record other people. Get consent before filming them and keep footage local by default.
