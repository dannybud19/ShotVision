import argparse

from shotvision import main as main_module


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
