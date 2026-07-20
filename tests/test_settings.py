from shotvision.config.settings import Config, load_config


def test_load_config_defaults():
    cfg = load_config()
    assert isinstance(cfg, Config)
    assert cfg.camera.source == "0"
    assert cfg.model.device == "auto"
    assert cfg.model.conf == 0.15
    assert cfg.model.imgsz == 960
    assert cfg.model.track_conf == 0.10
    assert cfg.model.track_conf < cfg.model.conf  # recovery floor stays below confirmation bar
    assert cfg.shot_logic.occlusion_grace_frames == 12


def test_cli_overrides_apply_and_coerce_types():
    cfg = load_config(
        cli_overrides={
            "camera.source": "sample_clips/test.mp4",
            "model.conf": "0.5",
            "shot_logic.shot_timeout_frames": "120",
        }
    )
    assert cfg.camera.source == "sample_clips/test.mp4"
    assert cfg.model.conf == 0.5
    assert isinstance(cfg.model.conf, float)
    assert cfg.shot_logic.shot_timeout_frames == 120
    assert isinstance(cfg.shot_logic.shot_timeout_frames, int)


def test_override_file_merges_over_defaults(tmp_path):
    override_path = tmp_path / "override.json"
    override_path.write_text('{"model": {"conf": 0.7}}')
    cfg = load_config(override_path=override_path)
    assert cfg.model.conf == 0.7
    # Untouched sections/fields keep their defaults
    assert cfg.model.device == "auto"
    assert cfg.camera.source == "0"


def test_unknown_keys_in_json_are_ignored():
    cfg = load_config(cli_overrides={"model.nonexistent_field": "x"})
    assert not hasattr(cfg.model, "nonexistent_field")
