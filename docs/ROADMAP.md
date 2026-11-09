# ShotVision Roadmap

ShotVision is a single-camera basketball analytics system. Each phase is described by **what it must do**. Tools and libraries are chosen when that phase starts, based on what was learned up to then.

**Rule for the whole roadmap: no phase starts until the one before it is reliable on real footage from our own camera.** "Reliable" means the phase's exit criteria below, measured on a held-out set that was never used for tuning.

Status (2026-11-06): Phase 1 in progress. Gate A is judged on in-scope clips (fixed camera, single ball): 21/22 makes counted (95.5%), 0 false makes in 6 misses. The in-scope gate needs at least 50 misses before it can pass, so it currently reports NOT ENOUGH MISSES TO JUDGE. Out-of-scope clips are tracked as a stress test without pass/fail: 137/222 makes, 5 false makes in 79 misses. Details: `docs/tracking-research.md` §0. History: `docs/PROJECT_LOG.md`.

---

## Camera assumptions and single-camera limits

The goal is for the system to work **from any angle where the hoop, the ball and the shooter are visible**. Setup is already angle-independent: the hoop is found automatically every frame and there is no manual rim calibration. Accuracy is not angle-independent, and the roadmap must not pretend otherwise:

- **One camera sees a 2D projection.** Whether the ball passes *through* the rim or *in front of / behind* it is a depth question, and depth is along the camera's line of sight. The typical setup is **elevated near half court, facing the hoop**. That puts the front-rim/back-rim direction on the camera axis, which is the hardest view for this question. A camera at the wing or baseline sees that direction side-on. From half court, front-rim and back-rim misses are the main false-make risk.
- **The ball is small at the rim from half court**: about 20-30 px at 1080p, about 12-20 px at 720p. Motion blur at 30 fps already causes most of the remaining failures on closer cameras.
- **2D cues that do carry depth**: whether the rim/net is drawn over the ball (occlusion order), whether the net moves, whether the ball slows down in the net, and where it comes out below. None is perfect alone. Ball size is too noisy at these sizes to measure depth.
- **Per-angle thresholds**: the scoring line sits at a fraction of the detected hoop box (currently 0.4). That fraction depends on camera elevation, so every new camera position needs its own measured score before we trust it.
- **Frame rate**: all shot-logic thresholds are counted in frames and tuned at 30 fps. A 60 fps camera needs a config profile with frame counts scaled to match.

Each phase's "single-camera limit" note says what this means for that phase.

---

## Phase 1: Make/miss (current, blocked)

**Must do:** for a single shooter, reliably decide whether each shot went in. A make counts only if the ball actually passes through the rim. Rim-outs (including in-and-outs), balls passing in front of the rim, and near misses must not count. It must work with and without a net, from the camera positions we support, in real time on a live camera.

**Depends on:** nothing earlier.

**Where it stands:** the pipeline runs end to end: capture, per-frame ball/hoop detection, gated ball association, rim tracking, a MISS-biased shot state machine, stats and an overlay. A labeled-clip scoreboard (`scripts/evaluate.py`) is in place, and the per-shot diagnostic is `experiments/shot_diagnostics.py`. On the 11 third-party clips: 68/75 correct, 0 false makes. All 7 failures are makes that were not counted. 6 of them involve the ball being invisible for 7-25 frames at the rim, and 0 are timeouts. Gate A is judged on in-scope clips (fixed camera, single ball, measured per clip and stored as `camera_class`/`ball_count` in `labels.json`); out-of-scope clips are tracked as a stress test without pass/fail.

**Work, in order:**
1. **Film our own footage** (spec in `docs/tracking-research.md`, "Do this next"). Until then, every number is from other people's cameras, and there are only 8 distinct labeled misses.
2. **Measure with settings unchanged** on that footage, and keep one session held out.
3. **Improve on measured failures only.** One change at a time, re-run everything, and keep a change only if false makes stay at 0. Candidates, ranked in the research doc: capture settings (60 fps, fast shutter), track re-adoption at the hoop, fine-tuning the detector on our blurred frames, a gated net-motion confirmer.
4. **Live test**: phone as webcam, compare the on-screen count to a manual tally, and check that it keeps up in real time.

**Hardest technical risk:** proving **0 false makes from the half-court angle**. Front-rim and back-rim misses can look like makes in 2D. Every rule that rescues the remaining missed makes is make-favourable, so it trades directly against this risk. A small miss set can't show the trade is safe: with 0 false makes in N misses, the 95% upper bound on the false-make rate is about 3/N, so 10 misses → ≤ 26%, 100 → ≤ 3%, 300 → ≤ 1%.

**Data / footage needed:**
- At least 100 misses of every kind, weighted toward front-rim, back-rim, in-and-out and short shots in front of the rim. Grow this to ~300 over time for a <1% bound.
- About as many makes, half of them touching the rim or backboard.
- Non-shot moments near the rim: rebounds, tips, passes under the basket.
- With a net and, if possible, without one.
- The primary half-court position, plus at least one other angle.
- 60 fps with a fast shutter, and a 30 fps control session.

**Exit criteria (to agree before tuning on our footage), on held-out footage from our camera:**
- 0 false makes, on at least ~100 misses;
- at least 95% of makes counted;
- no spurious shots from non-shot moments;
- a live session's count matches a manual tally.

---

## Phase 2: Shot value (2PT vs 3PT)

**Must do:**
- **Release moment:** for every shot Phase 1 counts, find when the ball left the shooter's hands and where the shooter was standing. A two-or-three call is impossible without this, so it belongs here rather than in Phase 3.
  - Trace the ball back from the shot Phase 1 armed on to the frame it separated from the shooter.
  - Identify the shooter: the person the ball left.
  - Take their floor position from the last frame with feet on the floor (take-off), not the release frame.
- **Court calibration:** a one-time setup per court, where known court points are marked so any on-screen floor position maps to a real floor position.
- **Two or three:** from the shooter's floor position, compute the distance from the hoop and classify the shot.
- Court dimensions and line distances vary (NBA, FIBA, college, high school, park courts), so calibration and the 3PT line are per court.

**Depends on:** Phase 1 (the shot and its outcome; the ball track that armed it).

**Hardest technical risk:** the shooter's feet at the release are often in the air or hidden by other players. A floor mapping is valid only for points on the floor, so a jumping player's feet must come from the take-off frame. That frame is set by the release-moment step, so its error goes straight into the two/three call. The release itself can also be hard to pin down: on a quick shot, or when a defender's hand is near the ball, it isn't obvious when the ball leaves the hands. Shots taken near the line are inherently uncertain. They must be flagged "uncertain" rather than guessed, in the same spirit as the MISS bias.

**Single-camera limit:** the floor mapping needs enough visible court markings, and they must stay visible. Camera bumps invalidate it, so we need a check that warns when the court no longer lines up. The camera must see the shooter's feet *and* the rim with enough ball resolution for Phase 1. That framing decision is shared with Phase 1 and should be tested with Phase 1's footage.

**Data / footage needed:** shots from known, measured floor spots (tape marks at fixed distances), including many within ~0.5 m of the 3PT line. Each needs a labeled release frame and take-off frame. Footage from at least two courts with different dimensions. Include jump shots, set shots and catch-and-shoot, so release timing varies.

**Exit criteria:**
- release frame within a few frames (about 0.1 s) of the label, and shooter position within an agreed distance (e.g. 0.3 m) on held-out shots;
- at least 97% correct 2/3 calls on shots not flagged uncertain;
- shots near the line flagged rather than wrong.

---

## Phase 3: Shot type

**Must do:** read the shooter's body movement through the shot to classify its type: layup, pull-up jumper, catch-and-shoot, fade-away two, fade-away three, and others. Rare or unclear shots go into an "unknown" bucket. It builds on Phase 2's release moment and shooter position rather than finding them again. Start with simple rules on body movement. Examples: a fade-away moves the body away from the hoop at release; a layup is a close, low release after a gather. Move to a learned classifier once enough labeled clips of each type exist.

**Depends on:** Phase 1 (which shots exist) and Phase 2 (release moment, shooter identity, distance from the hoop, floor position).

**Hardest technical risk:** body keypoints from one camera at half-court distance are noisy and get hidden by defenders. Classes such as "fade-away" depend on motion toward or away from the hoop, which can be along the camera axis and so hard to measure from half court. Classes also blur into each other, and labeled examples of rare types accumulate slowly.

**Single-camera limit:** motion toward or away from the camera is poorly measured. Shot-type rules should lean on the floor mapping (Phase 2) for movement over the floor rather than raw image motion.

**Data / footage needed:** labeled clips per shot type. Rules need roughly 20-30 per type to validate. A learned classifier needs on the order of 100+ per type.

**Exit criteria:** a per-type confusion matrix on held-out clips, with an agreed minimum accuracy per type.

---

## Phase 4: Multiple players

**Must do:** follow every player across a game with consistent identities, credit each shot to whoever released it, and keep running per-player makes, misses and points. Players are tagged by name once at session start.

**Depends on:** Phase 1 (outcomes), Phase 2 (points, and the release moment and shooter for each shot), and Phase 3 (body keypoints, to settle attribution when players are close).

**Hardest technical risk:** **identity through occlusion**. In pickup games, players in similar clothing cross, screen and cluster under the basket, and a single camera loses them behind each other. One identity swap wrongly credits every later shot. Attribution at the release is a second risk when two players are close to the ball.

**Single-camera limit:** players hide each other far more from a single elevated viewpoint than from multiple cameras. The system needs a cheap way to correct a swap, plus a confidence flag on uncertain attributions.

**Data / footage needed:** multi-player pickup footage with per-shot shooter labels and identity labels at intervals. Include sessions with similar jerseys. Get consent from everyone filmed.

**Exit criteria:** the correct player credited on at least ~95% of shots, and identity swaps rare and correctable in the UI.

---

## Future (not yet scoped)

| Feature | What it needs to do | Depends on | Hardest part |
|---|---|---|---|
| Shot selection analysis | Flag poor decisions, e.g. a contested fade-away when a better shot was available. The long-term differentiator. | Phases 2-4, defender positions, a definition of a "better shot" | Needs every defender's position and a model of shot quality. This is the hardest piece. |
| Hot zones and tendencies | Make % and shot mix by court location. | Phases 2-3 | Enough shots per zone to mean anything. |
| Possession tracking | Passes vs shots vs turnovers. | Phase 4, ball possession over time | Ball ownership while it is in a player's hands, hidden. |
| Replays, highlights, clips | Cut clips around makes and big moments in pickup games. | Phase 1 (cheapest win: every shot already has a frame index); richer with Phases 3-4 | Mostly I/O and storage. |
| Full pickup-game analytics | Box scores for real games. | Phases 2-4 | Everything above, together. |

---

## Applies to every phase

- **Measure first:** each phase gets its own labeled set, a scoreboard like `scripts/evaluate.py`, and a held-out set.
- **Prefer no answer to a wrong one:** "uncertain" or "not counted" beats a confident error. This covers makes, 2/3, shot type and player credit.
- **Real time on the Mac** (M2 Pro, MPS, no CUDA). Run expensive models only around shot attempts. Flag any hard CUDA dependency before adopting a tool.
- **Licensing:** check every repo, model and dataset before using it. No license means learn from it, don't copy it. The current ball/hoop checkpoint has no clear license, and `ultralytics` is AGPL-3.0. Both matter before anything ships.
- **Privacy:** pickup-game features record other people. Get consent and keep footage local by default.
