"""YOLO detection wrapper that canonicalizes whatever class names the
loaded checkpoint uses down to {ball, hoop, person}, so the rest of the
pipeline never has to know whether the basketball fine-tune or the COCO
fallback is active.
"""
from __future__ import annotations

from dataclasses import dataclass

from ultralytics import YOLO

from shotvision.config.settings import ModelConfig
from shotvision.detection.model_registry import resolve_weights

BALL = "ball"
HOOP = "hoop"
PERSON = "person"

_CLASS_NAME_ALIASES = {
    "basketball": BALL,
    "sports ball": BALL,
    "ball": BALL,
    "basketball hoop": HOOP,
    "hoop": HOOP,
    "rim": HOOP,
    "person": PERSON,
}


def _canonicalize(raw_name: str) -> str | None:
    return _CLASS_NAME_ALIASES.get(raw_name.strip().lower())


@dataclass
class Detection:
    class_name: str  # canonical 'ball' | 'hoop' | 'person', or raw name if unmapped
    conf: float
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2
    track_id: int | None = None

    @property
    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return (x1 + x2) / 2, (y1 + y2) / 2


class Detector:
    def __init__(self, model_config: ModelConfig, device: str):
        self.weights_path = resolve_weights(model_config)
        self.model = YOLO(self.weights_path)
        self.device = device
        self.conf = model_config.conf
        self.imgsz = model_config.imgsz
        # Lower floor for ByteTrack's own recovery logic — see
        # ModelConfig.track_conf. Only BallTracker uses this (passed to
        # model.track()); predict() below still gates on the confirmation
        # threshold, self.conf.
        self.track_conf = model_config.track_conf

        self._raw_names: dict[int, str] = self.model.names
        self._id_to_canonical = {
            cls_id: _canonicalize(name) for cls_id, name in self._raw_names.items()
        }
        self.has_hoop_class = HOOP in self._id_to_canonical.values()

    def set_conf(self, conf: float) -> None:
        self.conf = max(0.01, min(0.99, conf))

    def predict(self, frame) -> list[Detection]:
        results = self.model.predict(
            frame, conf=self.conf, imgsz=self.imgsz, device=self.device, verbose=False
        )
        return self.parse_result(results[0])

    def parse_result(self, result) -> list[Detection]:
        """Parses one ultralytics Results object (from .predict() or
        .track()) into canonical Detection objects. Public so the tracking
        module can reuse it for .track() results without duplicating the
        class-name canonicalization logic."""
        detections: list[Detection] = []
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return detections

        ids = boxes.id
        for i in range(len(boxes)):
            cls_id = int(boxes.cls[i])
            raw_name = self._raw_names.get(cls_id, str(cls_id))
            canonical = self._id_to_canonical.get(cls_id) or raw_name
            conf = float(boxes.conf[i])
            x1, y1, x2, y2 = (float(v) for v in boxes.xyxy[i])
            track_id = int(ids[i]) if ids is not None else None
            detections.append(Detection(canonical, conf, (x1, y1, x2, y2), track_id))
        return detections
