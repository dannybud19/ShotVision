"""Central configuration for ShotVision.

Loads shotvision/config/default.json, optionally merges a user-supplied JSON
override file, then applies dotted-key CLI overrides (e.g. "camera.source").
Nothing in the pipeline should hardcode a path, device, or threshold that
belongs here.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path(__file__).parent / "default.json"

# Every duration below is in SECONDS and every rate is PER SECOND, so the same
# config works at any frame rate. Components convert to frames with the
# clip's (or camera's) actual fps via `to_frames`. The values were tuned at
# 30 fps; the seconds are those frame counts / 30, so at 30 fps they convert
# back to exactly the tuned frame counts.
REFERENCE_FPS = 30.0


def to_frames(seconds: float, fps: float) -> int:
    """Seconds -> whole frames at `fps`, rounded half up. Tolerates the float
    error in values like 0.2667 s (= 8 frames at 30 fps)."""
    return int(math.floor(seconds * fps + 0.5))


def per_frame(rate_per_s: float, fps: float) -> float:
    """A per-second rate expressed per frame at `fps`."""
    return rate_per_s / fps


def ema_alpha_at(alpha_at_reference: float, fps: float) -> float:
    """Rescale a per-frame EMA factor tuned at REFERENCE_FPS so the smoothing
    has the same time constant at `fps` (exactly the tuned value at 30 fps)."""
    if fps == REFERENCE_FPS:
        return alpha_at_reference
    return 1.0 - (1.0 - alpha_at_reference) ** (REFERENCE_FPS / fps)


@dataclass
class CameraConfig:
    # Device index ("0"), video file path, or stream URL. Always a string;
    # capture.source resolves it to the right cv2.VideoCapture argument.
    source: str = "0"
    # Frame rate used to convert the second-based thresholds into frames.
    # 0 = use the rate the source reports (a file's fps; a webcam's nominal
    # rate). Set it when a live camera reports its rate wrongly.
    fps: float = 0.0


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
    # (gate_base_widths + gate_growth_widths_per_s * seconds_elapsed) ball
    # widths of the position predicted from that velocity. Without one (a
    # single recent point), within max_jump_widths_per_s * seconds_elapsed
    # widths of the last position.
    gate_base_widths: float = 1.5
    # 15/s (0.5/frame at 30 fps): measured, 1.0/frame let a shooter's head
    # 153px from the prediction (4 frames into a blur gap at the rim) in.
    gate_growth_widths_per_s: float = 15.0
    max_jump_widths_per_s: float = 90.0  # 3 widths/frame at 30 fps
    # After this long without an accepted detection the followed ball is
    # dropped and the most confident detection is (re)acquired.
    max_gap_s: float = 0.5
    # Velocity is estimated only from two points at most this far apart.
    velocity_max_span_s: float = 0.2667  # 8 frames at 30 fps
    # A followed ball's strength is its best confident conf over this window.
    strength_window_s: float = 0.3333  # 10 frames at 30 fps
    # Switch to a detection outside the gate only if it is at least this
    # confident AND the followed ball was itself weaker than switch_weak_conf
    # (e.g. the tracker latched onto a player's head, conf ~0.2, while the
    # real ball, conf ~0.8, flies) or has been unseen for switch_stale_s.
    # The stale wait must outlast the 2-4 frame motion-blur gap as the ball
    # drops through the rim: measured, a shooter's head (conf up to 0.69)
    # otherwise hijacks the track there and fakes a miss.
    switch_strong_conf: float = 0.5
    switch_weak_conf: float = 0.3
    switch_stale_s: float = 0.2667  # 8 frames at 30 fps
    # Stationary false positives (a round sign, a ball on the floor): ignore
    # a detection whose spot (within stationary_radius_widths ball widths)
    # produced detections on >= stationary_min_hits_s worth of frames, spread
    # over at least stationary_min_span_s, within the last
    # stationary_window_s.
    stationary_window_s: float = 6.0
    stationary_min_span_s: float = 3.0
    stationary_min_hits_s: float = 0.8333  # 25 frames at 30 fps
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
    # How long the ball must be seen descending above the rim to arm.
    descent_min_s: float = 0.0667  # 2 frames at 30 fps
    # Where the scoring line sits within the hoop box (0 = top, 1 = bottom).
    # The box spans rim + net; 0.5 (old default, `RimRegion.rim_y`) is mid-net.
    # Swept 0.5/0.4/0.3/0.2/0.1: 0.4 fixed one make and broke nothing; 0.2
    # broke a different make.
    scoring_line_fraction: float = 0.4
    # How long without a detection the pre-arm descent streak survives.
    prearm_max_missed_s: float = 0.0333  # 1 frame at 30 fps
    # How long the ball may go undetected before a shot is considered lost
    # to occlusion rather than failed (hand at release).
    occlusion_grace_s: float = 0.4  # 12 frames at 30 fps
    # The same, when the ball was last seen at the hoop: a ball in the net is
    # hidden for 11-19 frames (0.37-0.63 s) on measured footage.
    rim_occlusion_grace_s: float = 0.8  # 24 frames at 30 fps
    # Time since a shot armed before it's forced to resolve as a MISS.
    shot_timeout_s: float = 3.0  # 90 frames at 30 fps
    trajectory_buffer_s: float = 2.0  # 60 frames at 30 fps
    # The crossing x is fitted over the confirmed points of this window.
    crossing_fit_window_s: float = 0.1333  # 4 points at 30 fps
    # --- automatic rim tracking (shot_logic/rim_tracker.py) ---
    # Exponential-moving-average smoothing factor applied to the hoop box
    # each frame it's confirmed, AS TUNED AT 30 FPS; rescaled to the actual
    # fps (ema_alpha_at) so the smoothing time constant stays the same.
    # Higher = more responsive to real camera motion; lower = more resistant
    # to per-frame detection jitter.
    rim_ema_alpha: float = 0.25
    # How long without a hoop detection before the tracked rim is considered
    # lost (reverts to None) rather than just briefly occluded. Generous
    # given hoop detection measured ~89-96% at our tuned settings.
    rim_lost_grace_s: float = 1.0  # 30 frames at 30 fps
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
