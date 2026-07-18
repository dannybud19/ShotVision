import cv2

from shotvision.shot_logic.calibration import (
    ClickCollector,
    load_calibration,
    save_calibration,
)
from shotvision.shot_logic.rim import RimRegion


def test_click_collector_gathers_up_to_required_points():
    collector = ClickCollector(required_points=4)
    for x, y in [(10, 10), (20, 10), (10, 30), (20, 30), (99, 99)]:
        collector.on_click(cv2.EVENT_LBUTTONDOWN, x, y, 0, None)

    assert collector.points == [(10, 10), (20, 10), (10, 30), (20, 30)]
    assert collector.is_complete is True


def test_click_collector_ignores_non_click_events():
    collector = ClickCollector()
    collector.on_click(cv2.EVENT_MOUSEMOVE, 5, 5, 0, None)
    assert collector.points == []
    assert collector.is_complete is False


def test_click_collector_reset():
    collector = ClickCollector()
    collector.on_click(cv2.EVENT_LBUTTONDOWN, 1, 1, 0, None)
    collector.reset()
    assert collector.points == []


def _sample_rim():
    return RimRegion.from_points(
        [(100, 50), (200, 50), (100, 70), (200, 70)], inner_bound_shrink=0.15
    )


def test_load_calibration_returns_none_when_file_missing(tmp_path):
    path = tmp_path / "calibrations.json"
    assert load_calibration(path, "file:/some/clip.mp4") is None


def test_save_then_load_round_trip(tmp_path):
    path = tmp_path / "calibrations.json"
    rim = _sample_rim()
    save_calibration(path, "file:/some/clip.mp4", rim)

    loaded = load_calibration(path, "file:/some/clip.mp4")
    assert loaded == rim


def test_load_calibration_returns_none_for_unknown_source_key(tmp_path):
    path = tmp_path / "calibrations.json"
    save_calibration(path, "file:/some/clip.mp4", _sample_rim())

    assert load_calibration(path, "file:/other/clip.mp4") is None


def test_save_calibration_preserves_other_source_keys(tmp_path):
    path = tmp_path / "calibrations.json"
    rim_a = _sample_rim()
    rim_b = RimRegion.from_points(
        [(0, 0), (50, 0), (0, 20), (50, 20)], inner_bound_shrink=0.1
    )

    save_calibration(path, "file:/clip_a.mp4", rim_a)
    save_calibration(path, "file:/clip_b.mp4", rim_b)

    assert load_calibration(path, "file:/clip_a.mp4") == rim_a
    assert load_calibration(path, "file:/clip_b.mp4") == rim_b


def test_recalibrating_same_source_key_overwrites(tmp_path):
    path = tmp_path / "calibrations.json"
    rim_a = _sample_rim()
    rim_b = RimRegion.from_points(
        [(0, 0), (50, 0), (0, 20), (50, 20)], inner_bound_shrink=0.1
    )

    save_calibration(path, "file:/clip.mp4", rim_a)
    save_calibration(path, "file:/clip.mp4", rim_b)

    assert load_calibration(path, "file:/clip.mp4") == rim_b
