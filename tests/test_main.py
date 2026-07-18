import argparse

import pytest

from shotvision import main as main_module
from shotvision.shot_logic.rim import RimRegion


def _args(source=None, config=None, loop=False, set_=None):
    return argparse.Namespace(source=source, config=config, loop=loop, set=set_)


def test_build_cli_overrides_with_source_only():
    overrides = main_module.build_cli_overrides(_args(source="clip.mp4"))
    assert overrides == {"camera.source": "clip.mp4"}


def test_build_cli_overrides_with_set_flags():
    overrides = main_module.build_cli_overrides(
        _args(set_=["model.conf=0.5", "shot_logic.shot_timeout_frames=120"])
    )
    assert overrides == {
        "model.conf": "0.5",
        "shot_logic.shot_timeout_frames": "120",
    }


def test_build_cli_overrides_combines_source_and_set():
    overrides = main_module.build_cli_overrides(
        _args(source="0", set_=["model.device=cpu"])
    )
    assert overrides == {"camera.source": "0", "model.device": "cpu"}


def test_build_cli_overrides_empty_when_nothing_given():
    assert main_module.build_cli_overrides(_args()) == {}


class _FakeSource:
    def __init__(self, first_frame):
        self._first_frame = first_frame
        self.source_key = "file:/fake/clip.mp4"

    def read_first_frame(self):
        return self._first_frame


def _sample_rim():
    return RimRegion.from_points(
        [(100, 50), (200, 50), (100, 70), (200, 70)], inner_bound_shrink=0.15
    )


def test_obtain_rim_uses_existing_calibration(monkeypatch):
    from shotvision.config.settings import load_config

    config = load_config()
    saved_rim = _sample_rim()
    monkeypatch.setattr(
        main_module, "load_calibration", lambda path, key: saved_rim
    )
    called = {"recalibrate": False}
    monkeypatch.setattr(
        main_module, "_recalibrate", lambda *a, **k: called.update(recalibrate=True)
    )

    rim = main_module._obtain_rim(config, _FakeSource(first_frame="unused"))

    assert rim == saved_rim
    assert called["recalibrate"] is False


def test_recalibrate_raises_if_no_frame_available():
    from shotvision.config.settings import load_config

    config = load_config()
    with pytest.raises(RuntimeError, match="Could not read a frame"):
        main_module._recalibrate(config, _FakeSource(first_frame=None))


def test_recalibrate_raises_if_calibration_cancelled(monkeypatch):
    from shotvision.config.settings import load_config

    config = load_config()
    monkeypatch.setattr(main_module, "run_calibration_ui", lambda *a, **k: None)

    with pytest.raises(RuntimeError, match="cancelled"):
        main_module._recalibrate(config, _FakeSource(first_frame="frame"))


def test_recalibrate_saves_and_returns_rim_on_success(monkeypatch):
    from shotvision.config.settings import load_config

    config = load_config()
    rim = _sample_rim()
    monkeypatch.setattr(main_module, "run_calibration_ui", lambda *a, **k: rim)
    saved = {}
    monkeypatch.setattr(
        main_module,
        "save_calibration",
        lambda path, key, r: saved.update(path=path, key=key, rim=r),
    )

    result = main_module._recalibrate(config, _FakeSource(first_frame="frame"))

    assert result == rim
    assert saved["rim"] == rim
    assert saved["key"] == "file:/fake/clip.mp4"
