# ShotVision

A computer-vision make/miss shot counter for a single basketball shooter.
**Phase 1** of a larger vision (court mapping, shot-type classification,
multi-player stats, shot-quality analysis) — this build is scoped to a
reliable make/miss counter only, with clean module boundaries so those
later phases can be added without a rewrite.

## Project structure

```
shotvision/
  config/       dataclass config, default.json, calibrations.json
  capture/      FrameSource — video file / device / stream URL, one interface
  detection/    device auto-detect, checkpoint resolution, YOLO wrapper
  tracking/     ByteTrack-based ball tracking + trajectory buffer
  shot_logic/   rim geometry, rim calibration, make/miss state machine
  stats/        makes/misses/attempts/percentage + per-shot log
  overlay/      HUD: rim box, trajectory trail, counters
  main.py       wires the pipeline, keyboard loop
scripts/
  finetune_roboflow.py   fine-tuning follow-up (not run this session)
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
detects the ball as a generic `sports ball` and has no hoop class at all
(the rim then comes entirely from manual calibration).

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
| `r`   | Force rim recalibration |
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

## Rim calibration

On first run against a given camera source (file path, device index, or
URL), a window opens on the first frame and waits for **4 clicks** around
the rim, defining its bounding region. The result is saved to
`shotvision/config/calibrations.json`, keyed by that exact source, so it
isn't needed again on subsequent runs of the same source. Press `r` at any
time to force recalibration (e.g. after moving the camera).

The 4 points define an axis-aligned bounding box (order doesn't matter).
Internally this becomes two regions: the **outer box** (used for
above/at/below-rim tests) and a narrower **inner horizontal gate**
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
with it horizontally, and descending for a few consecutive frames. It
resolves **MAKE** only if the ball then passes through the rim's inner
horizontal gate while in the rim's vertical band, and continues below the
rim without bouncing back up above rim height. Every ambiguous case —
rim-out, upward bounce, skipping the band without ever registering inside
the inner gate, or the shot never resolving — is scored **MISS**, never
MAKE.

A brief gap in ball detection (hand at release, ball hidden in the net)
doesn't fail a shot by itself — only a gap longer than
`shot_logic.occlusion_grace_frames` does. This is frame-count based and
doesn't look at the net at all, so it behaves the same for netted and
net-less rims.

## Known limitations

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
properly-licensed model first. `scripts/finetune_roboflow.py` documents
fine-tuning on a Roboflow dataset (many are CC BY 4.0) as the accuracy *and*
licensing follow-up — also the path to a model tuned for your specific
camera angle and ball, since the ball detection rate on a quick smoke test
against a third-party clip was only ~11% of frames (the hoop, by contrast,
was detected in ~99.8% of frames — ByteTrack and the occlusion-tolerant
state machine are what make the sparser ball detections still usable).

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
