"""Entry point: wires capture -> detection -> tracking -> shot_logic ->
stats -> overlay into one run loop, against a video file or a live camera —
same pipeline either way, `camera.source` is the only thing that changes.

The rim is located automatically from the model's own hoop detections
(shot_logic/rim_tracker.py) — no manual calibration step. Shot-logic
evaluation simply doesn't run until the rim tracker first locks on.

Keyboard controls:
  q       quit
  r       force the rim tracker to drop its estimate and reacquire
  [ / ]   decrease / increase detection confidence
  space   pause / resume
"""
from __future__ import annotations

import argparse

import cv2

from shotvision.config.settings import Config, load_config
from shotvision.capture.source import FrameSource
from shotvision.detection.detector import Detector
from shotvision.detection.device import log_device_choice, resolve_device
from shotvision.overlay.hud import Hud
from shotvision.shot_logic.rim_tracker import RimTracker
from shotvision.shot_logic.state_machine import ShotState, ShotStateMachine
from shotvision.stats.tracker import StatsTracker
from shotvision.tracking.ball_tracker import BallTracker

WINDOW_NAME = "ShotVision"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ShotVision — make/miss shot counter")
    parser.add_argument("--source", help="Video file path, device index, or stream URL")
    parser.add_argument("--config", help="Path to a JSON file of config overrides")
    parser.add_argument(
        "--loop", action="store_true", help="Loop a video file source when it ends"
    )
    parser.add_argument(
        "--set",
        action="append",
        metavar="dotted.key=value",
        help="Override a config value, e.g. --set model.conf=0.5 (repeatable)",
    )
    return parser.parse_args()


def build_cli_overrides(args: argparse.Namespace) -> dict[str, str]:
    overrides: dict[str, str] = {}
    if args.source is not None:
        overrides["camera.source"] = args.source
    for item in args.set or []:
        key, _, value = item.partition("=")
        overrides[key] = value
    return overrides


def run(config: Config, loop: bool = False) -> None:
    device, reason = resolve_device(config.model.device)
    log_device_choice(device, reason)

    detector = Detector(config.model, device)
    ball_tracker = BallTracker(detector, config.tracker, config.shot_logic.trajectory_buffer_len)
    rim_tracker = RimTracker(config.model, config.shot_logic)
    stats = StatsTracker()
    hud = Hud()
    state_machine: ShotStateMachine | None = None

    with FrameSource(config.camera.source, loop=loop) as source:
        cv2.namedWindow(WINDOW_NAME)
        paused = False
        frame_idx = 0

        while True:
            if not paused:
                frame = source.read()
                if frame is None:
                    print("[ShotVision] Source exhausted.")
                    break

                detections = ball_tracker.update(frame)
                rim = rim_tracker.update(detections)

                if rim is not None:
                    if state_machine is None:
                        state_machine = ShotStateMachine(rim, config.shot_logic)
                        print("[ShotVision] Rim acquired — shot tracking active.")
                    else:
                        state_machine.rim = rim

                if state_machine is not None:
                    result = state_machine.update(ball_tracker.current_frame_ball_obs, frame_idx)
                    if result is not None:
                        stats.record(result)
                        hud.note_result(result.outcome, frame_idx)
                        print(f"[ShotVision] Shot #{stats.attempts}: {result.outcome.value}")

                hud.draw(
                    frame,
                    rim,
                    ball_tracker.trajectory,
                    state_machine.state if state_machine is not None else ShotState.IDLE,
                    stats,
                    frame_idx,
                    detector.conf,
                )
                cv2.imshow(WINDOW_NAME, frame)
                frame_idx += 1

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("r"):
                rim_tracker.reset()
                print("[ShotVision] Rim tracker reset — reacquiring.")
            elif key == ord("["):
                detector.set_conf(detector.conf - 0.05)
                print(f"[ShotVision] Confidence threshold: {detector.conf:.2f}")
            elif key == ord("]"):
                detector.set_conf(detector.conf + 0.05)
                print(f"[ShotVision] Confidence threshold: {detector.conf:.2f}")
            elif key == ord(" "):
                paused = not paused

        cv2.destroyAllWindows()

    print(
        f"[ShotVision] Final: {stats.makes} makes, {stats.misses} misses "
        f"({stats.percentage:.0f}%)"
    )


def main() -> None:
    args = parse_args()
    config = load_config(override_path=args.config, cli_overrides=build_cli_overrides(args))
    run(config, loop=args.loop)


if __name__ == "__main__":
    main()
