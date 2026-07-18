from pathlib import Path

import numpy as np
import pytest

from shotvision.config.settings import ModelConfig
from shotvision.detection.detector import BALL, HOOP, PERSON, Detector, _canonicalize

BASKETBALL_WEIGHTS = Path("models/basketball_best.pt")


def test_canonicalize_maps_known_names():
    assert _canonicalize("Basketball") == BALL
    assert _canonicalize("basketball hoop") == HOOP
    assert _canonicalize("sports ball") == BALL
    assert _canonicalize("Person") == PERSON
    assert _canonicalize("Hoop") == HOOP


def test_canonicalize_unknown_name_returns_none():
    assert _canonicalize("skateboard") is None


class _FakeBoxes:
    def __init__(self, cls, conf, xyxy, ids):
        self.cls = cls
        self.conf = conf
        self.xyxy = xyxy
        self.id = ids

    def __len__(self):
        return len(self.cls)


class _FakeResult:
    def __init__(self, boxes):
        self.boxes = boxes


def _make_detector_shell():
    """Builds a Detector-like object with canonicalization tables set up,
    without loading a real YOLO model — parse_result only depends on those
    tables plus the raw-name dict, both cheap to fake directly."""
    detector = Detector.__new__(Detector)
    detector._raw_names = {0: "Basketball", 1: "Basketball Hoop"}
    detector._id_to_canonical = {0: BALL, 1: HOOP}
    return detector


def test_parse_result_with_track_ids():
    detector = _make_detector_shell()
    boxes = _FakeBoxes(
        cls=[0, 1],
        conf=[0.42, 0.61],
        xyxy=[[10.0, 20.0, 30.0, 40.0], [100.0, 100.0, 150.0, 150.0]],
        ids=[7, 12],
    )
    detections = detector.parse_result(_FakeResult(boxes))

    assert len(detections) == 2
    assert detections[0].class_name == BALL
    assert detections[0].track_id == 7
    assert detections[0].bbox == (10.0, 20.0, 30.0, 40.0)
    assert detections[0].center == (20.0, 30.0)
    assert detections[1].class_name == HOOP
    assert detections[1].track_id == 12


def test_parse_result_without_track_ids():
    detector = _make_detector_shell()
    boxes = _FakeBoxes(
        cls=[0], conf=[0.5], xyxy=[[0.0, 0.0, 10.0, 10.0]], ids=None
    )
    detections = detector.parse_result(_FakeResult(boxes))

    assert len(detections) == 1
    assert detections[0].track_id is None


def test_parse_result_handles_no_boxes():
    detector = _make_detector_shell()
    detections = detector.parse_result(_FakeResult(boxes=None))
    assert detections == []


@pytest.mark.skipif(
    not BASKETBALL_WEIGHTS.exists(), reason="basketball checkpoint not downloaded"
)
def test_detector_loads_real_basketball_checkpoint_and_predicts():
    cfg = ModelConfig(weights=str(BASKETBALL_WEIGHTS), conf=0.35, imgsz=640)
    detector = Detector(cfg, device="cpu")

    assert detector.has_hoop_class is True
    assert set(detector._id_to_canonical.values()) == {BALL, HOOP}

    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    detections = detector.predict(blank_frame)
    assert isinstance(detections, list)  # blank frame: no detections expected
