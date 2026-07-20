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
    # Confidence floor fed into model.track() (ByteTrack), separate from and
    # below `conf`. Matches bytetrack.yaml's default track_low_thresh so
    # ByteTrack's own low-confidence recovery (designed to sustain a track
    # through partial occlusion, e.g. a ball partly hidden by net cords) gets
    # the full population of candidate boxes instead of having them filtered
    # out before it ever sees them. Never surfaced as a confirmed observation
    # by itself — only `conf`-and-above detections are.
    track_conf: float = 0.10
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
    tracker_yaml: str = "bytetrack.yaml"


@dataclass
class ShotLogicConfig:
    # Inner scoring gate is the rim's inner width shrunk by this fraction on
    # each side (false-positive-averse: a stricter gate than the visible rim).
    inner_bound_shrink: float = 0.15
    # How far outside the rim's horizontal span (as a ratio of rim width) the
    # ball may still be considered "aligned" while approaching from above.
    align_tolerance_ratio: float = 0.6
    descent_min_frames: int = 2
    # Consecutive missing-detection frames tolerated before a shot is
    # considered lost to occlusion rather than failed (hand at release, net).
    occlusion_grace_frames: int = 12
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
