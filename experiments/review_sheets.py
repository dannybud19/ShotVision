"""Review sheets: pictures for the owner to look at. Read-only, never loads the model.

Detections come from the cache in experiments/.cache/detections (the script
refuses to run if a clip has no cache). Video frames are read from the clip.
This script draws what was detected. It never decides whether a shot was a
make or a miss.

Subcommands:
  frames  one contact sheet per target frame (a window of frames cropped around
          the hoop, detections drawn), plus a full-frame view of the target.
  camera  per clip: hoop track plot, 8 spread frames and the 4 biggest hoop jumps.

Usage:
  python experiments/review_sheets.py frames --clip public/commons_hardwick/<clip>.webm \\
      --frames 35060 125017 [--before 1.5] [--after 0.5] [--step 0.1] [--out sample_clips/_review]
  python experiments/review_sheets.py camera --clips video_test_5.mp4 lf_back.mp4 [--out sample_clips/_review]
"""
from __future__ import annotations

import argparse
import json
import math
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
PLOT_W, PLOT_H = 1200, 360
SHEET_W = 1600
SPREAD_FRAMES = 8
JUMP_FRAMES = 4
CAMERA_FRAME_W = 400
BLUE = (255, 0, 0)  # BGR
RED = (0, 0, 255)
DARK_GREEN = (0, 150, 0)


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


def hoop_series(dets: list[list], conf: float = HOOP_CONF) -> dict:
    """Per frame with a hoop (conf >= conf), the highest-confidence one, as offsets
    from the clip's median hoop in median-hoop-width units:
    dx, dy = (centre - median centre) / median width, s = width / median width."""
    rows = []
    for f, frame in enumerate(dets):
        b = best_hoop(frame, conf)
        if b is not None:
            x1, y1, x2, y2 = b.bbox
            rows.append((f, (x1 + x2) / 2, (y1 + y2) / 2, x2 - x1))
    if not rows:
        return {"frames": [], "dx": [], "dy": [], "s": []}
    med_cx = statistics.median(r[1] for r in rows)
    med_cy = statistics.median(r[2] for r in rows)
    med_w = statistics.median(r[3] for r in rows)
    return {
        "frames": [r[0] for r in rows],
        "dx": [(r[1] - med_cx) / med_w for r in rows],
        "dy": [(r[2] - med_cy) / med_w for r in rows],
        "s": [r[3] / med_w for r in rows],
    }


def camera_stats(dets: list[list], conf: float = HOOP_CONF, n_jump: int = JUMP_FRAMES) -> dict:
    """Printed evidence for the camera sheet. share_with_2plus_hoops is the share of
    ALL frames with two or more hoop detections at conf >= conf. jump_frames are the
    n_jump frames with the largest hypot(dx, dy), biggest first."""
    series = hoop_series(dets, conf)
    jumps = [(math.hypot(dx, dy), f) for f, dx, dy in zip(series["frames"], series["dx"], series["dy"])]
    jumps.sort(key=lambda j: (-j[0], j[1]))
    two_plus = sum(1 for frame in dets if sum(1 for d in frame if d.class_name == "hoop" and d.conf >= conf) >= 2)
    return {
        "frames": len(dets),
        "frames_with_hoop": len(series["frames"]),
        "share_with_2plus_hoops": two_plus / len(dets) if dets else 0.0,
        "max_jump": jumps[0][0] if jumps else 0.0,
        "jump_frames": [f for _, f in jumps[:n_jump]],
        "jump_values": {f: v for v, f in jumps[:n_jump]},
    }


def spread_indices(n_frames: int, count: int = SPREAD_FRAMES) -> list[int]:
    """count frame indices evenly spaced from the first to the last frame."""
    if n_frames <= 0:
        return []
    return sorted({round(i * (n_frames - 1) / (count - 1)) for i in range(count)})


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


def build_header_text(stem: str, target: int, note: str, first: int, last: int) -> str:
    return f"{stem}  target f{target}  {note}  window f{first}-f{last}"


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
                            build_header_text(stem, t, args.label, window[0], window[-1]))
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


# ---------------------------------------------------------------------------
# camera subcommand
# ---------------------------------------------------------------------------


def draw_track_plot(series: dict, n_frames: int) -> np.ndarray:
    """dx (blue), dy (red) and s - 1 (green) against frame index, in hoop widths.
    Reference lines at -0.5, 0 and +0.5. Values beyond +-1.5 sit on the edge.
    Frames without a hoop leave a gap."""
    img = np.full((PLOT_H, PLOT_W, 3), 255, np.uint8)
    span = 1.5  # hoop widths shown above and below zero
    margin = 52

    def y_of(v: float) -> int:
        v = max(-span, min(span, v))
        return round(PLOT_H / 2 - v / span * (PLOT_H / 2 - 8))

    def x_of(f: int) -> int:
        return margin + round(f / max(1, n_frames - 1) * (PLOT_W - margin - 8))

    for v, label in ((-0.5, "-0.5"), (0.0, "0"), (0.5, "+0.5")):
        y = y_of(v)
        cv2.line(img, (margin, y), (PLOT_W - 8, y), (170, 170, 170), 1 if v else 2)
        cv2.putText(img, label, (6, y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, BLACK, 1, cv2.LINE_AA)
    for i, (name, colour) in enumerate((("dx", BLUE), ("dy", RED), ("size - 1", DARK_GREEN))):
        cv2.putText(img, name, (margin + 10 + i * 90, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, colour, 2, cv2.LINE_AA)
    cv2.putText(img, "hoop widths from the median hoop (axis +-1.5, clipped)", (margin + 300, 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (90, 90, 90), 1, cv2.LINE_AA)
    frames = series["frames"]
    for key, colour, offset in (("dx", BLUE, 0.0), ("dy", RED, 0.0), ("s", DARK_GREEN, -1.0)):
        segment: list[tuple[int, int]] = []
        previous = None
        for f, v in zip(frames, series[key]):
            if previous is not None and f != previous + 1 and segment:
                cv2.polylines(img, [np.array(segment, np.int32)], False, colour, 1, cv2.LINE_AA)
                segment = []
            segment.append((x_of(f), y_of(v + offset)))
            previous = f
        if segment:
            cv2.polylines(img, [np.array(segment, np.int32)], False, colour, 1, cv2.LINE_AA)
    return img


def draw_hoops_all(img: np.ndarray, frame_dets: list) -> None:
    """Every hoop detection with conf >= HOOP_CONF in green; the highest one thicker."""
    best = best_hoop(frame_dets)
    for d in frame_dets:
        if d.class_name == "hoop" and d.conf >= HOOP_CONF and d is not best:
            x1, y1, x2, y2 = (int(round(v)) for v in d.bbox)
            cv2.rectangle(img, (x1, y1), (x2, y2), GREEN, 2)
    if best is not None:
        x1, y1, x2, y2 = (int(round(v)) for v in best.bbox)
        cv2.rectangle(img, (x1, y1), (x2, y2), GREEN, 6)


def camera_tile(frame: np.ndarray, frame_dets: list, f: int, extra: str = "") -> np.ndarray:
    img = frame.copy()
    draw_hoops_all(img, frame_dets)
    tile = resize_to_width(img, CAMERA_FRAME_W)
    draw_text_box(tile, f"f{f}" + (f"  {extra}" if extra else ""), (0, 0), 0.5, 1)
    return tile


def pad_to_width(img: np.ndarray, width: int, colour=BLACK) -> np.ndarray:
    h, w = img.shape[:2]
    if w >= width:
        return img[:, :width]
    return np.hstack([img, np.full((h, width - w, 3), colour, np.uint8)])


def run_camera(args: argparse.Namespace) -> int:
    config = load_config()
    meta = ev.load_clip_meta()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for clip in args.clips:
        path = ev.CLIPS_DIR / clip
        if not path.exists():
            sys.exit(f"clip not found: {path}")
        dets = load_cached(clip, path, config)
        fps = ev.clip_fps(path)
        stats = camera_stats(dets)
        series = hoop_series(dets)
        entry = meta.get(clip, {})
        profile = entry.get("camera_profile", {})
        spread = spread_indices(len(dets))
        cap = cv2.VideoCapture(str(path))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        wanted = spread + stats["jump_frames"]
        images = read_frames(path, wanted, fps, min(total, len(dets)))
        missing = [f for f in wanted if f not in images]
        if missing:
            sys.exit(f"could not read frames {missing} from {path.name}")

        spread_tiles = [camera_tile(images[f], dets[f], f) for f in spread]
        jump_tiles = [camera_tile(images[f], dets[f], f, f"jump {stats['jump_values'][f]:.2f}")
                      for f in stats["jump_frames"]]
        head = header_strip(
            SHEET_W,
            f"{clip}   hoop_move_p95 {profile.get('hoop_move_p95')}   hoop_size_ratio "
            f"{profile.get('hoop_size_ratio')}   camera_class {entry.get('camera_class')}",
        )
        parts = [head, pad_to_width(draw_track_plot(series, len(dets)), SHEET_W, (255, 255, 255))]
        for tiles in (spread_tiles[:4], spread_tiles[4:], jump_tiles):
            if tiles:
                parts.append(pad_to_width(tile_grid(tiles, 4), SHEET_W))
        sheet_path = out_dir / f"camera_{Path(clip).stem}.png"
        cv2.imwrite(str(sheet_path), np.vstack(parts))
        rows.append((clip, stats, entry.get("camera_class")))

    print(f"{'clip':<26}{'frames_with_hoop':>17}{'share_with_2plus_hoops':>24}{'max_jump':>10}  camera_class")
    for clip, stats, cls in rows:
        print(f"{clip:<26}{stats['frames_with_hoop']:>17}{stats['share_with_2plus_hoops']:>24.4f}"
              f"{stats['max_jump']:>10.2f}  {cls}")
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
    f.add_argument("--label", default=HEADER_NOTE, help="header text in place of the default note")
    f.add_argument("--out", default=str(DEFAULT_OUT))
    f.set_defaults(func=run_frames)
    c = sub.add_parser("camera", help="hoop track plot, spread frames and jump frames per clip")
    c.add_argument("--clips", nargs="+", required=True, help="clip paths relative to sample_clips/")
    c.add_argument("--out", default=str(DEFAULT_OUT))
    c.set_defaults(func=run_camera)
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
