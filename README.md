# ShotVision

A computer-vision make/miss shot counter for a single basketball shooter.
**Phase 1** of a larger vision (court mapping, shot-type classification,
multi-player stats, shot-quality analysis) — this build is scoped to a
reliable make/miss counter only, with clean module boundaries so those
later phases can be added without a rewrite.

## Project structure

```
shotvision/
  config/       dataclass config, default.json
  capture/      FrameSource — video file / device / stream URL, one interface
  detection/    device auto-detect, checkpoint resolution, YOLO wrapper
  tracking/     per-frame detection + gated nearest-neighbour ball tracking
  shot_logic/   rim geometry, automatic rim tracking, make/miss state machine
  stats/        makes/misses/attempts/percentage + per-shot log
  overlay/      HUD: rim box, trajectory trail, counters
  main.py       wires the pipeline, keyboard loop
scripts/
  evaluate.py            scoreboard: score the pipeline against labeled clips
  render_overlay.py      write the HUD overlay to an mp4 (watch the tracking)
  diagnose_shots.py      per-shot trace of how each shot resolved
  tune_detection.py      imgsz x conf detection sweep
  finetune_roboflow.py   fine-tuning follow-up (not run yet)
tests/          pytest suite, one file per module
models/         downloaded checkpoints (gitignored)
```

## Setup

Requires Python 3.11+ (built and tested on 3.12; the venv here uses
3.12 since 3.11 wasn't available on this machine).

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt        # or requirements-dev.txt for pytest too
```

On first run, `shotvision.detection.model_registry` downloads the default
basketball checkpoint (~6MB) to `models/basketball_best.pt` automatically —
no Roboflow account needed. If that download fails, it falls back to a
stock COCO checkpoint (`yolo11n.pt`, auto-downloaded by ultralytics), which
detects the ball as a generic `sports ball` and has **no hoop class at
all** — since rim location is now fully automatic (see Rim tracking below)
and there's no manual fallback, the fallback path can locate the ball but
not the rim, and shot logic won't run. The basketball checkpoint download
succeeding is effectively required for this to work end-to-end.

### macOS SSL note

If you're on a python.org-installed Python (not Homebrew/conda), HTTPS
downloads can fail with a certificate verification error. This project
works around it by using `certifi`'s bundle explicitly in
`model_registry.py`, so no manual `Install Certificates.command` step
should be needed — `certifi` is in `requirements.txt`.

## Running

Same pipeline, whether the source is a recorded clip or a live camera —
only `camera.source` changes:

```bash
# Against a recorded clip (build/tune against this first)
python -m shotvision.main --source path/to/clip.mp4

# Loop a short clip while tuning thresholds
python -m shotvision.main --source path/to/clip.mp4 --loop

# Live camera (device index — e.g. a phone streamed as a virtual webcam
# via Continuity Camera or Iriun Webcam appears as a normal device index)
python -m shotvision.main --source 0

# IP-camera style stream URL
python -m shotvision.main --source rtsp://192.168.1.50/stream
```

Any config value can be overridden from the CLI without editing
`config/default.json`:

```bash
python -m shotvision.main --source clip.mp4 --set model.conf=0.5 --set shot_logic.shot_timeout_frames=120
```

Or point at a JSON file of overrides with `--config path/to/overrides.json`.

### Keyboard controls

| Key   | Action |
|-------|--------|
| `q`   | Quit |
| `r`   | Force the rim tracker to drop its estimate and reacquire |
| `[` / `]` | Decrease / increase detection confidence threshold |
| `space` | Pause / resume |

## Device selection

At startup, `shotvision.detection.device` probes hardware in
`cuda > mps > cpu` priority order and prints what it picked and why, e.g.:

```
[ShotVision] Using device: mps — Apple Silicon GPU (MPS) available
```

On CPU-only hardware, the COCO fallback path also selects a smaller model
size (`n` vs `s`) to keep frame rate usable; the default basketball
checkpoint is a fixed fine-tune independent of device.

## Detection tuning

The ball is small and fast, and the default checkpoint's out-of-the-box
detection rate at `imgsz=640`/`conf=0.35` was low (~11% of frames on the test
clip). `scripts/tune_detection.py` sweeps `imgsz` × `conf` across the sample
clips and reports detection rate and ms/frame for **both** the ball and the
hoop (they come from the same inference pass, so measuring both costs
nothing extra):

```bash
python scripts/tune_detection.py                       # full sweep + both matrices
python scripts/tune_detection.py --save-samples        # also dump annotated frames
```

Based on that sweep the ball defaults are **`imgsz=960`, `conf=0.15`** (mean
ball-detection across the corpus 32% → 51%, at ~14 ms/frame on MPS vs ~13.5 at
640). `imgsz=1280` added little on average, cost ~25% more compute, and was
unstable across clips, so 960 was chosen. Note the trade-off: raising `imgsz`
improves small-ball detection but slows inference; lowering `conf` recovers
faint detections but admits more false positives (mitigated by ByteTrack and
the descent/alignment gating in the state machine). `--save-samples` writes
annotated frames to `sample_clips/_debug/` so false positives can be eyeballed.
These are config values (`model.imgsz`, `model.conf`) — re-tune against your own
footage with the same script and update `config/default.json`.

Hoop detection at imgsz=960 is far more reliable than the ball ever was
(89.4% at conf=0.50, 88.6% at conf=0.60 — a gentle curve), so
`model.rim_conf` is set much stricter (**0.60**) than ball `conf`: a false
hoop reading corrupts the scoring geometry itself, which is higher-stakes
than a missed ball frame, and the gentle curve means little detection rate
is sacrificed for that safety margin.

## Ball tracking

`shotvision.tracking.ball_tracker.BallTracker` runs plain per-frame detection
(`model.predict()`) and links the ball across frames itself. It does **not** use
ByteTrack (`model.track()`): ByteTrack links boxes by overlap and only outputs
confirmed tracks, and a ball in flight moves about half its own width per frame,
so ByteTrack never confirmed it and dropped the ball for its whole flight above
the rim. That was the root cause of every "missing make" before 2026-11-03.

Association rules (thresholds in the `tracker` config section):

- **Gate around the predicted position.** The next detection must lie near
  where the ball's recent velocity says it should be, or near its last
  position (the net stops a ball abruptly). The gate is sized by the followed
  ball's width and grows slowly with frames since it was last seen.
- **Stationary objects are ignored.** A spot that keeps producing ball
  detections for seconds (a round sign on the hoop pole, a ball on the floor)
  is not the ball in play.
- **Guarded switching.** The tracker jumps to a confident detection outside the
  gate only if the followed ball has been weak recently or unseen for
  `switch_stale_frames`. A shooter's dark hair is detected as a ball at up to
  conf 0.69 on real footage and would otherwise take over while the real ball
  blurs at the rim. Each switch starts a new track identity, and a shot only
  scores the identity it started on.
- **Weak continuation.** Boxes between `model.track_conf` (0.03) and
  `model.conf` (0.15) may continue an already-followed ball near its predicted
  path, e.g. the ball faintly visible through the net. They keep a shot alive
  but never start, cross or resolve one.

## Rim tracking

The rim is located **automatically** from the model's own hoop detections —
there's no manual calibration step. `shotvision.shot_logic.rim_tracker.RimTracker`
consumes the same per-frame detections `BallTracker` already computes (no
extra inference cost) and turns a raw hoop box into a stable `RimRegion`:

- **Confirmation gate**: only hoop detections at or above `model.rim_conf`
  count.
- **EMA smoothing** (`shot_logic.rim_ema_alpha`, default 0.25) damps
  per-frame jitter while still tracking real camera motion — several of the
  sample clips pan or zoom, so a one-time snapshot wouldn't stay correct.
- **Occlusion tolerance** (`shot_logic.rim_lost_grace_frames`, default 30):
  a frame with no hoop detection keeps the last good rim rather than
  failing immediately; beyond that many consecutive misses, the rim is
  considered lost and reacquired fresh from the next confident reading.
- **Size-jump sanity gate** (`shot_logic.rim_size_jump_max_ratio`, default
  1.6×): a real hoop's on-screen size changes gradually with camera motion,
  not in one frame — a sudden large jump is more likely a stray
  misclassification than the real hoop, and is rejected (treated like a
  missed detection) rather than corrupting the tracked geometry.

Shot-logic evaluation simply doesn't start until the rim tracker first locks
on (typically within the first few frames given the detection rates above);
main.py's HUD and the make/miss state machine tolerate a `None` rim
gracefully during that window. Press `r` at any time to force the tracker to
drop its current estimate and reacquire (e.g. if the camera setup changes
significantly mid-run).

Internally the tracked hoop box becomes two regions: the **outer box** (used
for above/at/below-rim tests) and a narrower **inner horizontal gate**
(`shot_logic.inner_bound_shrink` in config, default 15% shrink per side) —
a make requires the ball to pass through the middle of the rim, not clip an
edge. This is deliberately false-positive-averse: rim-outs and near-misses
are worse to miscount than a shot that goes uncounted.

## Make/miss logic

See `shotvision/shot_logic/state_machine.py` for the full logic and
`tests/test_state_machine.py` for the behavior it's tested against (clean
makes, rim-outs, upward bounces off the rim, occlusion within/beyond grace,
net occlusion, timeouts, misaligned motion).

Summary: a shot arms when the ball is seen above the rim, roughly aligned
with it horizontally (`align_tolerance_ratio`), and descending for
`descent_min_frames` frames; one missed frame doesn't reset that count. Scoring is
then **trajectory-crossing based**: we track the ball's path and test whether
the *segment* between two consecutive observed positions crosses the scoring
line, and where. The model's hoop box spans the rim *and the net*, so the line
sits `scoring_line_fraction` (0.4) of the way down the box, near the rim, not
at the box's midline in the middle of the net. It resolves **MAKE** only if that
crossing falls inside the rim's inner horizontal gate **and** the whole ball
(its bounding-box top edge) then reaches below the outlined rim without
bouncing back up. Every ambiguous case — crossing outside the inner gate
(rim-out), the whole ball reaching below without a valid crossing, the ball
coming back above the rim after crossing inside it (in-and-out,
`miss_in_and_out`), or the shot never resolving — is scored
**MISS**, never MAKE.

Why crossing instead of "did a detection land inside the rim band": a
descending ball, especially at a modest detection rate, jumps over a thin rim
band between frames and is often occluded by the net exactly as it passes
through — so requiring a detection to land *inside* the band misses real makes.
Interpolating the crossing between the last position above the rim and the
first below it recovers the make regardless of band thickness or a detection
gap through the net. (This replaced the earlier band-membership approach, which
scored 0 makes on a test clip whose rim happened to calibrate to a 3px-tall
band; the crossing approach scores those makes correctly.)

A brief gap in ball detection (hand at release, ball hidden in the net)
doesn't fail a shot by itself — only a gap longer than
`shot_logic.occlusion_grace_frames` (12) does, or `rim_occlusion_grace_frames`
(24) when the ball was last seen at the hoop, since a ball in the net is hidden
for 11-19 frames on measured footage. The crossing test spans such gaps.
It doesn't look at the net at all, so it behaves the same for netted and
net-less rims.

## Evaluating changes

`sample_clips/labels.json` holds ground truth for 11 clips (75 shots: 65 makes,
10 misses), and `scripts/evaluate.py` scores the whole pipeline against it:

```bash
python scripts/evaluate.py                    # all labeled clips; exit 0 only if all pass
python scripts/evaluate.py -v --clips lf_back.mp4
python scripts/evaluate.py --set shot_logic.scoring_line_fraction=0.3   # try a setting
python scripts/render_overlay.py --clip lf_back.mp4   # sample_clips/_debug/lf_back.overlay.mp4
```

It reports correct shots, **false makes**, missed makes, unlabeled ("spurious")
shots, and a smoothness check on each make (share of frames with the ball, and
the longest gap). Detections are cached in `experiments/.cache/`, so changes to
tracking or shot logic replay in seconds; changing `model.*` settings re-runs
the model. Clips aren't committed: download them per `sample_clips/SOURCES.md`.

Current score (2026-11-03): **68/75 shots correct, 0 false makes**. The 7
misses are makes the detector can't see well enough, mostly heavy motion blur
over the backboard or below the net. See `docs/PROJECT_LOG.md`.

## Known limitations

**Motion blur.** The default checkpoint misses a dark, motion-blurred ball over
the backboard or below the net, sometimes for 10+ frames, at any confidence
or image size tried. Those makes go uncounted. A detector fine-tuned on blurred
frames from your own camera is the fix (`scripts/finetune_roboflow.py`).

**Few labeled misses.** The evaluation set has only 10 misses, so the
false-make rate is weakly tested. Filming and labeling misses (rim-outs,
airballs, in-and-outs) from your own camera is the most valuable next step.

**Depth ambiguity.** A single fixed camera can't fully distinguish "ball
passed through the rim" from "ball passed in front of/behind the rim" — a
shot that clips the front rim and continues past a rim mounted farther from
camera can look identical to a clean make in 2D. Mounting the camera above
or behind the backboard, angled down through the rim, meaningfully reduces
this ambiguity by aligning the camera's view axis with the vertical path a
made shot actually takes. This is a real limitation of any single-camera
setup and isn't solved in code here.

**Default ball/hoop model.** `models/basketball_best.pt` is a community
YOLOv8 fine-tune (ball + hoop classes) pulled directly from
[avishah3/AI-Basketball-Shot-Detection-Tracker](https://github.com/avishah3/AI-Basketball-Shot-Detection-Tracker)
— no Roboflow account needed, but its license is unspecified upstream.
Fine for local prototyping; **do not redistribute** without sourcing a
properly-licensed model first. Downloads are checked against a pinned SHA256
(`model_registry.DEFAULT_CHECKPOINT_SHA256`), since a `.pt` file is a pickle
and loading one can run code. Also note that `ultralytics` itself is
**AGPL-3.0**, which matters if this project is ever distributed or offered
as a network service. `scripts/finetune_roboflow.py` documents
fine-tuning on a Roboflow dataset (many are CC BY 4.0) as the accuracy *and*
licensing follow-up — also the path to a model tuned for your specific
camera angle and ball. With per-frame detection the ball is found in roughly
40-80% of frames on the sample clips (the hoop in ~99%), and the gaps are
concentrated exactly where scoring happens: motion blur at the rim and the
net hiding the ball.

**No court mapping, pose, multi-player, or shot-quality analysis** — all
explicitly out of scope for this phase; the module boundaries
(`capture`/`detection`/`tracking`/`shot_logic`/`stats`/`overlay`) exist so
those can be layered in later without touching this code.

## Testing

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

Each module has its own test file. Detection/tracking tests that need the
real checkpoint are skipped automatically if
`models/basketball_best.pt` isn't present (`pytest.mark.skipif`).
