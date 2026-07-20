"""Ball-detection tuning harness.

Measures ball-detection rate across a corpus of clips as a function of
inference image size (`imgsz`) and confidence threshold (`conf`), to pick
better defaults than the untuned 640/0.35 (which detected the ball in only
~11% of frames on video_test_5.mp4).

Efficient design: the confidence dimension is collapsed into post-processing.
For each imgsz we run the detector ONCE at a very low floor confidence and
record, per sampled frame, the highest ball-detection confidence seen (0 if
none). Detection rate at any threshold is then just the fraction of frames
whose max-confidence >= that threshold — no re-inference per conf value.

Reuses the real Detector so class canonicalization matches production.

Caveat: detection *rate* is recall-ish, not precision. Lowering conf always
raises it while also admitting more false positives, which this harness can't
score without labelled boxes. Sample annotated frames are saved so false
positives can be eyeballed; final choice should balance rate against those.

Usage:
  python scripts/tune_detection.py
  python scripts/tune_detection.py --imgszs 640 960 1280 --sample-every 3 --max-frames 250
"""
from __future__ import annotations

import argparse
import glob
import os
import time

import cv2

from shotvision.config.settings import load_config
from shotvision.detection.detector import BALL, Detector
from shotvision.detection.device import log_device_choice, resolve_device

FLOOR_CONF = 0.05  # run inference this low; threshold higher in post-processing
CONF_GRID = [0.05, 0.10, 0.15, 0.20, 0.25, 0.35]
DEBUG_DIR = "sample_clips/_debug"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Tune ball detection imgsz/conf")
    p.add_argument("--clips-glob", default="sample_clips/*.mp4")
    p.add_argument("--extra-glob", default="sample_clips/*.mov")
    p.add_argument("--imgszs", type=int, nargs="+", default=[640, 960, 1280])
    p.add_argument("--sample-every", type=int, default=3, help="process every Nth frame")
    p.add_argument("--max-frames", type=int, default=250, help="cap sampled frames per clip")
    p.add_argument("--save-samples", action="store_true", help="save annotated debug frames")
    return p.parse_args()


def gather_clips(args) -> list[str]:
    clips = sorted(glob.glob(args.clips_glob) + glob.glob(args.extra_glob))
    return [c for c in clips if not os.path.basename(c).startswith("_")]


def scan_clip(detector: Detector, path: str, imgsz: int, sample_every: int, max_frames: int):
    """Returns (list of per-frame max ball confidence, inference seconds, frame count)."""
    detector.imgsz = imgsz
    cap = cv2.VideoCapture(path)
    max_confs: list[float] = []
    infer_seconds = 0.0
    frame_i = 0
    while len(max_confs) < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_i % sample_every != 0:
            frame_i += 1
            continue
        t0 = time.perf_counter()
        detections = detector.predict(frame)
        infer_seconds += time.perf_counter() - t0
        ball_confs = [d.conf for d in detections if d.class_name == BALL]
        max_confs.append(max(ball_confs) if ball_confs else 0.0)
        frame_i += 1
    cap.release()
    return max_confs, infer_seconds


def detection_rate(max_confs: list[float], conf: float) -> float:
    if not max_confs:
        return 0.0
    return 100.0 * sum(1 for c in max_confs if c >= conf) / len(max_confs)


def save_debug_frame(detector: Detector, path: str, imgsz: int, conf: float) -> None:
    os.makedirs(DEBUG_DIR, exist_ok=True)
    detector.imgsz = imgsz
    detector.set_conf(conf)
    cap = cv2.VideoCapture(path)
    # Grab a frame from ~40% into the clip (likelier to contain action).
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * 0.4))
    ok, frame = cap.read()
    cap.release()
    if not ok:
        return
    for d in detector.predict(frame):
        x1, y1, x2, y2 = (int(v) for v in d.bbox)
        color = (255, 0, 0) if d.class_name == BALL else (0, 200, 200)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, f"{d.class_name} {d.conf:.2f}", (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
    name = os.path.splitext(os.path.basename(path))[0]
    cv2.imwrite(f"{DEBUG_DIR}/{name}_imgsz{imgsz}_conf{conf}.jpg", frame)


def main() -> None:
    args = parse_args()
    config = load_config()
    device, reason = resolve_device(config.model.device)
    log_device_choice(device, reason)

    detector = Detector(config.model, device)
    detector.set_conf(FLOOR_CONF)
    print(f"Weights: {detector.weights_path}\n")

    clips = gather_clips(args)
    print(f"Corpus: {len(clips)} clips, sampling every {args.sample_every} frame(s), "
          f"cap {args.max_frames}/clip\n")

    # results[imgsz][clip] = list of per-frame max ball confidence
    results: dict[int, dict[str, list[float]]] = {}
    ms_per_frame: dict[int, float] = {}

    for imgsz in args.imgszs:
        results[imgsz] = {}
        total_seconds = 0.0
        total_frames = 0
        print(f"--- imgsz={imgsz} ---")
        for path in clips:
            max_confs, secs = scan_clip(detector, path, imgsz, args.sample_every, args.max_frames)
            results[imgsz][path] = max_confs
            total_seconds += secs
            total_frames += len(max_confs)
            rate = detection_rate(max_confs, 0.15)
            print(f"  {os.path.basename(path):38s} {len(max_confs):4d} frames  "
                  f"det@0.15={rate:5.1f}%")
        ms_per_frame[imgsz] = 1000.0 * total_seconds / total_frames if total_frames else 0.0
        print(f"  -> {ms_per_frame[imgsz]:.1f} ms/frame\n")

    # Aggregate matrix: mean over clips of per-clip detection rate.
    print("=" * 78)
    print("Mean ball-detection % (averaged across clips)")
    print("=" * 78)
    header = "imgsz \\ conf | " + " ".join(f"{c:>6.2f}" for c in CONF_GRID) + " |  ms/frame"
    print(header)
    print("-" * len(header))
    for imgsz in args.imgszs:
        cells = []
        for conf in CONF_GRID:
            rates = [detection_rate(mc, conf) for mc in results[imgsz].values()]
            mean_rate = sum(rates) / len(rates) if rates else 0.0
            cells.append(f"{mean_rate:6.1f}")
        print(f"{imgsz:>11} | " + " ".join(cells) + f" |  {ms_per_frame[imgsz]:7.1f}")

    print("\nBaseline (imgsz=640, conf=0.35) is the top-right-ish cell.")
    print("Higher imgsz + lower conf should move detection rate up (watch ms/frame).")

    if args.save_samples:
        print(f"\nSaving annotated sample frames to {DEBUG_DIR}/ for FP eyeballing...")
        best_imgsz = args.imgszs[-1]
        for path in clips:
            save_debug_frame(detector, path, best_imgsz, 0.15)
        print("Done.")


if __name__ == "__main__":
    main()
