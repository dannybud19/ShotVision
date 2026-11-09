"""Review sheets: pictures for the owner to look at. Read-only, never loads the model.

Detections come from the cache in experiments/.cache/detections (the script
refuses to run if a clip has no cache). Video frames are read from the clip.
This script draws what was detected. It never decides whether a shot was a
make or a miss.

Subcommands:
  frames  one contact sheet per target frame (a window of frames cropped around
          the hoop, detections drawn), plus a full-frame view of the target.
  camera  (added in step A4) hoop track plot, spread frames and jump frames.

Usage:
  python experiments/review_sheets.py frames --clip public/commons_hardwick/<clip>.webm \\
      --frames 35060 125017 [--before 1.5] [--after 0.5] [--step 0.1] [--out sample_clips/_review]
"""
from __future__ import annotations

import argparse
import json
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import evaluate as ev  # noqa: E402
from shotvision.config.settings import load_config  # noqa: E402

HOOP_CONF = 0.6
BALL_CONF = 0.3
GREEN = (0, 255, 0)
ORANGE = (0, 165, 255)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
TILE_WIDTH = 240
TILES_PER_ROW = 7
HEADER_HEIGHT = 40
FULL_WIDTH = 1280
LABEL_RANGE_S = 10.0
HEADER_NOTE = "pipeline: spurious MAKE"
DEFAULT_OUT = REPO_ROOT / "sample_clips" / "_review"


# ---------------------------------------------------------------------------
# Plain functions (no files, no cache): tested in tests/test_review_sheets.py
# ---------------------------------------------------------------------------


def window_frames(t: int, fps: float, before: float, after: float, step: float) -> list[int]:
    """Frame indices from t - round(before*fps) to t + round(after*fps), inclusive,
    every max(1, round(step*fps)) frames."""
    first = t - round(before * fps)
    last = t + round(after * fps)
    stride = max(1, round(step * fps))
    return list(range(first, last + 1, stride))


def crop_box(hoop_boxes: list[tuple], frame_shape: tuple) -> tuple[int, int, int, int]:
    """Crop around the median hoop: width 6 x median hoop width, height 5 x median
    hoop width, centred on the median hoop centre. The box is moved (not shrunk)
    to stay inside the image. With no hoop boxes, the full frame (0, 0, w, h)."""
    h, w = int(frame_shape[0]), int(frame_shape[1])
    if not hoop_boxes:
        return 0, 0, w, h
    cx = statistics.median((b[0] + b[2]) / 2 for b in hoop_boxes)
    cy = statistics.median((b[1] + b[3]) / 2 for b in hoop_boxes)
    hw = statistics.median(b[2] - b[0] for b in hoop_boxes)
    cw = min(w, max(1, round(6 * hw)))
    ch = min(h, max(1, round(5 * hw)))
    x1 = min(max(0, round(cx - cw / 2)), w - cw)
    y1 = min(max(0, round(cy - ch / 2)), h - ch)
    return x1, y1, x1 + cw, y1 + ch


def best_hoop(dets: list, conf: float = HOOP_CONF):
    """Highest-confidence hoop detection with conf >= conf, or None."""
    hoops = [d for d in dets if d.class_name == "hoop" and d.conf >= conf]
    return max(hoops, key=lambda d: d.conf) if hoops else None


# ---------------------------------------------------------------------------
# Reading and drawing
# ---------------------------------------------------------------------------


def read_frames(path: Path, indices: list[int], fps: float, total: int) -> dict[int, np.ndarray]:
    """Frames at the given indices. With ffmpeg: one seek per frame. Without:
    cv2, one seek to the first wanted frame and then sequential reads."""
    wanted = sorted({i for i in indices if 0 <= i < total})
    out: dict[int, np.ndarray] = {}
    if shutil.which("ffmpeg"):
        for i in wanted:
            cmd = ["ffmpeg", "-v", "error", "-ss", f"{i / fps:.4f}", "-i", str(path),
                   "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"]
            raw = subprocess.run(cmd, capture_output=True, check=True).stdout
            img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
            if img is not None:
                out[i] = img
        return out
    cap = cv2.VideoCapture(str(path))
    try:
        for i in wanted:
            pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
            if pos != i and not (0 <= i - pos <= 30):
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                pos = i
            while pos < i:  # short forward gaps: read on instead of seeking again
                if not cap.grab():
                    break
                pos += 1
            ok, img = cap.read()
            if ok:
                out[i] = img
    finally:
        cap.release()
    return out


def draw_text_box(img: np.ndarray, text: str, origin: tuple[int, int], scale: float, thickness: int) -> None:
    (tw, th), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
    x, y = origin
    cv2.rectangle(img, (x, y), (x + tw + 8, y + th + base + 8), BLACK, -1)
    cv2.putText(img, text, (x + 4, y + th + 4), cv2.FONT_HERSHEY_SIMPLEX, scale, WHITE, thickness, cv2.LINE_AA)


def draw_detections(img: np.ndarray, dets: list, thickness: int = 2) -> None:
    for d in dets:
        x1, y1, x2, y2 = (int(round(v)) for v in d.bbox)
        if d.class_name == "hoop" and d.conf >= HOOP_CONF:
            cv2.rectangle(img, (x1, y1), (x2, y2), GREEN, thickness)
        elif d.class_name == "ball" and d.conf >= BALL_CONF:
            cv2.rectangle(img, (x1, y1), (x2, y2), ORANGE, thickness)
            cv2.putText(img, f"{d.conf:.2f}", (x1, max(12, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, ORANGE, 2, cv2.LINE_AA)


def resize_to_width(img: np.ndarray, width: int) -> np.ndarray:
    h, w = img.shape[:2]
    return cv2.resize(img, (width, max(1, round(h * width / w))), interpolation=cv2.INTER_AREA)


def tile_grid(tiles: list[np.ndarray], per_row: int) -> np.ndarray:
    th, tw = tiles[0].shape[:2]
    rows = []
    for r in range(0, len(tiles), per_row):
        row = tiles[r:r + per_row]
        row += [np.zeros((th, tw, 3), np.uint8)] * (per_row - len(row))
        rows.append(np.hstack(row))
    return np.vstack(rows)


def header_strip(width: int, text: str) -> np.ndarray:
    strip = np.zeros((HEADER_HEIGHT, width, 3), np.uint8)
    cv2.putText(strip, text, (8, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.7, WHITE, 2, cv2.LINE_AA)
    return strip


# ---------------------------------------------------------------------------
# frames subcommand
# ---------------------------------------------------------------------------


def nearby_labels(labels: list[dict], t: int, fps: float) -> list[dict]:
    span = round(LABEL_RANGE_S * fps)
    return [
        {k: s.get(k) for k in ("start", "end", "outcome", "card")}
        for s in labels
        if s["start"] <= t + span and s["end"] >= t - span
    ]


def load_cached(clip: str, path: Path, config):
    if not ev._cache_path(path, config).exists():
        sys.exit(f"no detection cache for {clip}; this script never runs detection")
    return ev.load_detections(path, config)


def run_frames(args: argparse.Namespace) -> int:
    config = load_config()
    path = ev.CLIPS_DIR / args.clip
    if not path.exists():
        sys.exit(f"clip not found: {path}")
    dets = load_cached(args.clip, path, config)
    fps = ev.clip_fps(path)
    cap = cv2.VideoCapture(str(path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    labels = ev.load_labels(split="all", include_duplicates=True).get(args.clip, [])
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(args.clip).stem
    targets = []

    for t in args.frames:
        window = [f for f in window_frames(t, fps, args.before, args.after, args.step) if 0 <= f < min(total, len(dets))]
        images = read_frames(path, window + [t], fps, total)
        if t not in images or not all(f in images for f in window):
            sys.exit(f"could not read every frame for target f{t} from {path.name}")
        hoop_boxes = [b.bbox for f in window if (b := best_hoop(dets[f])) is not None]
        x1, y1, x2, y2 = crop_box(hoop_boxes, images[t].shape)
        tiles = []
        for f in window:
            img = images[f].copy()
            draw_detections(img, dets[f])
            tile = resize_to_width(img[y1:y2, x1:x2], TILE_WIDTH)
            draw_text_box(tile, f"f{f}", (0, 0), 0.5, 1)
            tiles.append(tile)
        head = header_strip(TILE_WIDTH * TILES_PER_ROW,
                            f"{stem}  target f{t}  {HEADER_NOTE}  window f{window[0]}-f{window[-1]}")
        sheet = np.vstack([head, tile_grid(tiles, TILES_PER_ROW)])
        sheet_path = out_dir / f"{stem}_f{t}.png"
        cv2.imwrite(str(sheet_path), sheet)

        full = images[t].copy()
        draw_detections(full, dets[t], thickness=3)
        draw_text_box(full, f"f{t}", (0, 0), 1.2, 2)
        full_path = out_dir / f"{stem}_f{t}_full.jpg"
        cv2.imwrite(str(full_path), resize_to_width(full, FULL_WIDTH))

        near = nearby_labels(labels, t, fps)
        targets.append({"frame": t, "nearby_labels": near, "sheet": sheet_path.name, "full": full_path.name})
        print(f"f{t}: {sheet_path.name}, {full_path.name}; labelled shots within +-{LABEL_RANGE_S:g} s:")
        for s in near:
            print(f"    start {s['start']}  end {s['end']}  {s['outcome']}  card {s['card']}")
        if not near:
            print("    (none)")

    (out_dir / f"{stem}_targets.json").write_text(json.dumps(targets, indent=2) + "\n")
    return 0


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Review sheets for the owner (read-only, never loads the model)")
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("frames", help="contact sheet of a frame window around each target frame")
    f.add_argument("--clip", required=True, help="clip path relative to sample_clips/")
    f.add_argument("--frames", type=int, nargs="+", required=True)
    f.add_argument("--before", type=float, default=1.5, help="seconds before the target")
    f.add_argument("--after", type=float, default=0.5, help="seconds after the target")
    f.add_argument("--step", type=float, default=0.1, help="seconds between tiles")
    f.add_argument("--out", default=str(DEFAULT_OUT))
    f.set_defaults(func=run_frames)
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
