"""Render the HUD overlay (rim box, ball trail, make/miss counter) to an mp4,
headlessly — so tracking smoothness can be watched, not just measured.

Uses the same cached detections and replay as scripts/evaluate.py, so it
shows exactly what the evaluator scored.

Usage:
  python scripts/render_overlay.py --clip chonyy_two_score_two_miss.mp4
  python scripts/render_overlay.py --clip chonyy_two_score_two_miss.mp4 --start 250 --end 300 --out make.mp4
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import CLIPS_DIR, REPO_ROOT, load_detections, replay  # noqa: E402

from shotvision.capture.source import FrameSource  # noqa: E402
from shotvision.config.settings import load_config  # noqa: E402
from shotvision.overlay.hud import Hud  # noqa: E402
from shotvision.shot_logic.state_machine import ShotState  # noqa: E402
from shotvision.stats.tracker import StatsTracker  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Render HUD overlay video for a clip")
    p.add_argument("--clip", required=True, help="Filename in sample_clips/")
    p.add_argument("--out", help="Output mp4 (default: sample_clips/_debug/<clip>.overlay.mp4)")
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--end", type=int, default=None)
    p.add_argument("--set", action="append", metavar="dotted.key=value")
    args = p.parse_args()

    config = load_config(cli_overrides=dict(i.partition("=")[::2] for i in (args.set or [])))
    clip = CLIPS_DIR / args.clip
    rep = replay(load_detections(clip, config), config, keep_trajectories=True)
    results = {r.frame_idx: r for r in rep.results}

    out = Path(args.out) if args.out else REPO_ROOT / "sample_clips" / "_debug" / f"{clip.stem}.overlay.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    hud, stats, writer = Hud(), StatsTracker(), None
    with FrameSource(str(clip)) as source:
        idx = 0
        while (frame := source.read()) is not None:
            if args.end is not None and idx > args.end:
                break
            if idx in results:
                stats.record(results[idx])
                hud.note_result(results[idx].outcome, idx)
            if idx >= args.start:
                fs = rep.frames[idx]
                state = ShotState.ARMED if fs.armed else ShotState.IDLE
                hud.draw(frame, fs.rim, rep.trajectories[idx], state, stats, idx, config.model.conf)
                if fs.obs is not None:
                    cv2.circle(frame, (int(fs.obs.x), int(fs.obs.y)), 3, (255, 255, 255), -1)
                cv2.putText(frame, f"f{idx}", (10, frame.shape[0] - 12), 0, 0.6, (255, 255, 255), 2)
                if writer is None:
                    h, w = frame.shape[:2]
                    writer = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"), source.fps or 30, (w, h))
                writer.write(frame)
            idx += 1
    if writer is not None:
        writer.release()
    print(f"Wrote {out}  ({stats.makes} makes, {stats.misses} misses)")


if __name__ == "__main__":
    main()
