from shotvision.config.settings import ModelConfig
from shotvision.detection import model_registry


def test_resolve_weights_uses_existing_file(tmp_path):
    weights_path = tmp_path / "basketball_best.pt"
    weights_path.write_bytes(b"fake-weights")
    cfg = ModelConfig(weights=str(weights_path), fallback_weights="yolo11n.pt")

    result = model_registry.resolve_weights(cfg)

    assert result == str(weights_path)


def test_resolve_weights_downloads_when_missing(tmp_path, monkeypatch):
    weights_path = tmp_path / "basketball_best.pt"
    cfg = ModelConfig(weights=str(weights_path), fallback_weights="yolo11n.pt")

    def fake_download(url, dest):
        dest.write_bytes(b"downloaded-weights")

    monkeypatch.setattr(model_registry, "_download", fake_download)

    result = model_registry.resolve_weights(cfg)

    assert result == str(weights_path)
    assert weights_path.read_bytes() == b"downloaded-weights"


def test_resolve_weights_falls_back_on_download_failure(tmp_path, monkeypatch):
    weights_path = tmp_path / "basketball_best.pt"
    cfg = ModelConfig(weights=str(weights_path), fallback_weights="yolo11n.pt")

    def failing_download(url, dest):
        raise ConnectionError("no network")

    monkeypatch.setattr(model_registry, "_download", failing_download)

    result = model_registry.resolve_weights(cfg)

    assert result == "yolo11n.pt"
    assert not weights_path.exists()
