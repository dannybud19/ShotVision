# PLAN_3 decisions (owner fills this in, then runs Part B)

Review images are in `sample_clips/_review/` (open in Finder). Fill every Owner cell. Part B refuses to start while any Owner cell is empty.

## 1. Enosburg: pipeline makes with no label

Sheets: `hazen_girls_v_enosburg_2025-12-12_f<frame>.png` (and `_full.jpg`). Choose one:
- `REAL_MAKE`: the ball went through the rim; the labelling missed it. Also give the label's start and end frames (start = ball's final approach, end = ball clear below the net; frame numbers are printed on each tile).
- `FALSE_MAKE`: the ball did not go through the rim. The pipeline made a false make.
- `CANT_TELL`: the frames don't show it clearly.

| Frame | Nearby labels (±10 s) | Owner: call | Owner: start | Owner: end | Owner: note |
| --- | --- | --- | --- | --- | --- |
| 35060 | none | | | | |
| 125017 | 124450-124492 IGNORE (card 71) | | | | |
| 201606 | none | | | | |
| 207518 | none | | | | |

## 2. Camera tags

Sheets: `camera_<clip>.png`. `lf_back` is a known fixed camera, for comparison. Choose `fixed` (the camera doesn't move; any box movement is the detector jumping) or `moving` (the camera pans, zooms or shakes).

| Clip | Current tag | hoop_move_p95 | hoop_size_ratio | 2+ hoops share | Owner: tag | Owner: reason |
| --- | --- | --- | --- | --- | --- | --- |
| video_test_5.mp4 | moving | 0.764 | 1.168 | 0.0000 | | |
| aggie_NathanBBall.mov | moving | 0.713 | 1.062 | 0.0000 | | |
| lf_alan.mp4 | moving | 1.75 | 1.387 | 0.0000 | | |
| artur_vid29.mp4 | moving | 2.151 | 1.12 | 0.0000 | | |
| kyle_test_video.mp4 | moving | 1.17 | 1.728 | 0.0000 | | |

## 3. Live check (owner runs these on the Mac, then pastes the output)

These load the model, which is why the agent didn't run them.

```bash
# a) recorded clip, compared with the cached replay. Expect COMPARE: SAME
.venv/bin/python experiments/live_check.py --source sample_clips/lf_shot_detection.mp4 --compare-to-replay --results-out experiments/results/live_check_file.json

# b) live camera for 60 s (phone as webcam, or laptop camera pointed at a screen playing a clip)
.venv/bin/python experiments/live_check.py --source 0 --seconds 60 --results-out experiments/results/live_check_camera.json
```

Owner: paste the `=== Live check ===` block of (a):

```
```

Owner: paste the `=== Live check ===` block of (b):

```
```

Owner: anything else Part B should know (or "none"):
