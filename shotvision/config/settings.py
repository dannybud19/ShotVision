"""Central configuration for ShotVision.

Loads shotvision/config/default.json, optionally merges a user-supplied JSON
override file, then applies dotted-key CLI overrides (e.g. "camera.source").
Nothing in the pipeline should hardcode a path, device, or threshold that
belongs here.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path(__file__).parent / "default.json"


@dataclass
class CameraConfig:
    # Device index ("0"), video file path, or stream URL. Always a string;
    # capture.source resolves it to the right cv2.VideoCapture argument.
    source: str = "0"


@dataclass
class ModelConfig:
    weights: str = "models/basketball_best.pt"
    fallback_weights: str = "yolo11n.pt"
    device: str = "auto"  # auto | cuda | mps | cpu
    # Tuned across the sample-clip corpus: imgsz 960 + conf 0.15 roughly
    # doubled ball-detection rate vs the untuned 640/0.35 at negligible extra
    # compute (see scripts/tune_detection.py). `conf` is the *confirmation*
    # threshold — the bar a detection must clear to count as a real ball
    # observation for the state machine.
    conf: float = 0.15
    imgsz: int = 960
    # Raw candidate floor passed to the per-frame predict() in BallTracker,
    # separate from and below `conf`. Lower-confidence boxes are returned to
    # callers (rim tracking applies its own stricter `rim_conf`) but never
    # become confirmed ball observations by themselves — only
    # `conf`-and-above detections do.
    # 0.03: low-confidence boxes recover the ball faintly visible through the
    # net; they are only ever used for weak continuation (ball_tracker.py).
    track_conf: float = 0.03
    # Confirmation threshold for HOOP detections feeding automatic rim
    # tracking (shot_logic/rim_tracker.py). Stricter than ball `conf` by
    # design: a false hoop reading corrupts the scoring geometry itself,
    # which is higher-stakes than a missed ball frame. Set from
    # scripts/tune_detection.py's hoop sweep at imgsz=960: mean hoop
    # detection is 89.4% at conf=0.50 and 88.6% at conf=0.60 — the curve is
    # gentle enough to afford the stricter bar for well under 1% of detection
    # rate, and the rim tracker's own occlusion tolerance covers brief gaps.
    rim_conf: float = 0.60


@dataclass
class TrackerConfig:
    # Ball association (tracking/ball_tracker.py). ByteTrack was dropped: its
    # IoU association can't follow a ball moving ~half its own width per
    # frame. See ball_tracker.py for the full rules.
    #
    # With a velocity estimate, a detection must fall within
    # (gate_base_widths + gate_per_frame_widths * frames_elapsed) ball widths
    # of the position predicted from that velocity. Without one (a single
    # recent point), within max_jump_ball_widths * frames_elapsed widths of
    # the last position.
    gate_base_widths: float = 1.5
    # 0.5/frame: measured, 1.0/frame let a shooter's head 153px from the
    # prediction (4 frames into a blur gap at the rim) into the gate.
    gate_per_frame_widths: float = 0.5
    max_jump_ball_widths: float = 3.0
    # After this many frames without an accepted detection the followed ball
    # is dropped and the most confident detection is (re)acquired.
    max_gap_frames: int = 15
    # Switch to a detection outside the gate only if it is at least this
    # confident AND the followed ball was itself weaker than switch_weak_conf
    # (e.g. the tracker latched onto a player's head, conf ~0.2, while the
    # real ball, conf ~0.8, flies) or has been unseen for switch_stale_frames.
    # The stale wait must outlast the 2-4 frame motion-blur gap as the ball
    # drops through the rim: measured, a shooter's head (conf up to 0.69)
    # otherwise hijacks the track there and fakes a miss.
    switch_strong_conf: float = 0.5
    switch_weak_conf: float = 0.3
    switch_stale_frames: int = 8
    # Stationary false positives (a round sign, a ball on the floor): ignore
    # a detection whose spot (within stationary_radius_widths ball widths)
    # produced >= stationary_min_hits detections spread over at least
    # stationary_min_span_frames within the last stationary_window_frames.
    stationary_window_frames: int = 180
    stationary_min_span_frames: int = 90
    stationary_min_hits: int = 25
    stationary_radius_widths: float = 0.6
    # Weak continuation (rule 5 in ball_tracker.py): a sub-threshold box may
    # continue the followed ball inside weak_gate_scale x the normal gate,
    # at a width within weak_size_ratio of the followed ball's.
    weak_gate_scale: float = 0.6
    weak_size_ratio: float = 1.6


@dataclass
class ShotLogicConfig:
    # Inner scoring gate is the rim's inner width shrunk by this fraction on
    # each side (false-positive-averse: a stricter gate than the visible rim).
    inner_bound_shrink: float = 0.15
    # How far outside the rim's horizontal span (as a ratio of rim width) the
    # ball may still be considered "aligned" while approaching from above.
    # 1.0 (was 0.6): measured, real makes are often last seen above the rim
    # just outside the 0.6 span; arming looseness can't create a make by
    # itself (scoring still needs an inner-gate crossing).
    align_tolerance_ratio: float = 1.0
    descent_min_frames: int = 2
    # Missing-detection frames the pre-arm descent streak survives.
    prearm_max_missed_frames: int = 1
    # Consecutive missing-detection frames tolerated before a shot is
    # considered lost to occlusion rather than failed (hand at release).
    occlusion_grace_frames: int = 12
    # The same, when the ball was last seen at the hoop: a ball in the net is
    # hidden for 11-19 frames on measured footage.
    rim_occlusion_grace_frames: int = 24
    # Frames since a shot armed before it's forced to resolve as a MISS.
    shot_timeout_frames: int = 90
    trajectory_buffer_len: int = 60
    # --- automatic rim tracking (shot_logic/rim_tracker.py) ---
    # Exponential-moving-average smoothing factor applied to the hoop box
    # each frame it's confirmed. Higher = more responsive to real camera
    # motion; lower = more resistant to per-frame detection jitter.
    rim_ema_alpha: float = 0.25
    # Consecutive no-hoop-detection frames tolerated before the tracked rim
    # is considered lost (reverts to None) rather than just briefly occluded.
    # Generous given hoop detection measured ~89-96% at our tuned settings.
    rim_lost_grace_frames: int = 30
    # A new hoop reading is rejected if its box area differs from the
    # current smoothed estimate by more than this ratio — a real hoop's
    # on-screen size changes gradually with camera motion, not in one frame;
    # guards against a stray misclassification corrupting the scoring
    # geometry.
    rim_size_jump_max_ratio: float = 1.6


@dataclass
class Config:
    camera: CameraConfig = field(default_factory=CameraConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    tracker: TrackerConfig = field(default_factory=TrackerConfig)
    shot_logic: ShotLogicConfig = field(default_factory=ShotLogicConfig)


_SECTION_TYPES = {
    "camera": CameraConfig,
    "model": ModelConfig,
    "tracker": TrackerConfig,
    "shot_logic": ShotLogicConfig,
}


def _dataclass_from_dict(cls, data: dict) -> Any:
    kwargs = {}
    valid_fields = {f.name for f in fields(cls)}
    for key, value in data.items():
        if key in valid_fields:
            kwargs[key] = value
    return cls(**kwargs)


def _merge_dict(base: dict, overrides: dict) -> dict:
    merged = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def _config_from_dict(data: dict) -> Config:
    sections = {}
    for name, cls in _SECTION_TYPES.items():
        section_data = data.get(name, {})
        sections[name] = _dataclass_from_dict(cls, section_data)
    return Config(**sections)


def _apply_dotted_override(data: dict, dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    cursor = data
    for part in parts[:-1]:
        cursor = cursor.setdefault(part, {})
    cursor[parts[-1]] = value


def _coerce_value(raw: str) -> Any:
    """Best-effort type coercion for CLI-supplied override values."""
    lowered = raw.lower()
    if lowered in ("true", "false"):
        return lowered == "true"
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def load_config(
    override_path: str | Path | None = None,
    cli_overrides: dict[str, str] | None = None,
) -> Config:
    """Load default.json, merge an optional override JSON file, then apply
    dotted-key CLI overrides (e.g. {"camera.source": "clip.mp4"})."""
    with open(DEFAULT_CONFIG_PATH) as f:
        data = json.load(f)

    if override_path is not None:
        override_path = Path(override_path)
        if override_path.exists():
            with open(override_path) as f:
                data = _merge_dict(data, json.load(f))

    if cli_overrides:
        for dotted_key, raw_value in cli_overrides.items():
            _apply_dotted_override(data, dotted_key, _coerce_value(raw_value))

    return _config_from_dict(data)
