"""Resolves the ball/hoop detection checkpoint: use it if already cached
under models/, download the default fine-tune if not, or fall back to a
stock COCO checkpoint (which ultralytics downloads/caches itself) if the
download fails.
"""
from __future__ import annotations

import logging
import shutil
import ssl
import urllib.request
from pathlib import Path

import certifi

from shotvision.config.settings import ModelConfig

logger = logging.getLogger(__name__)

# macOS python.org builds ship without a wired-up CA bundle, which makes
# urllib fail SSL verification for otherwise-valid HTTPS downloads. Use
# certifi's bundle explicitly instead of relying on the system default.
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

# Community YOLOv8 fine-tune with 'Basketball' + 'Basketball Hoop' classes,
# from avishah3/AI-Basketball-Shot-Detection-Tracker. No Roboflow account
# needed. Upstream license is unspecified — fine for local prototyping; see
# README for the fine-tuning-on-a-CC-BY-dataset follow-up before any
# redistribution.
DEFAULT_CHECKPOINT_URL = (
    "https://raw.githubusercontent.com/avishah3/"
    "AI-Basketball-Shot-Detection-Tracker/master/best.pt"
)


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_dest = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url, context=_SSL_CONTEXT, timeout=60) as response:
        with open(tmp_dest, "wb") as f:
            shutil.copyfileobj(response, f)
    tmp_dest.rename(dest)


def resolve_weights(model_config: ModelConfig) -> str:
    """Returns a path/name that ultralytics' YOLO() can load directly."""
    weights_path = Path(model_config.weights)
    if weights_path.exists():
        return str(weights_path)

    logger.info(
        "Basketball checkpoint not found at %s, downloading default...",
        weights_path,
    )
    try:
        _download(DEFAULT_CHECKPOINT_URL, weights_path)
        logger.info("Downloaded default basketball checkpoint to %s", weights_path)
        return str(weights_path)
    except Exception as exc:
        logger.warning(
            "Could not download default basketball checkpoint (%s). Falling "
            "back to COCO checkpoint '%s' — ball detection near the floor "
            "will be less reliable, and hoop detection will rely solely on "
            "manual rim calibration.",
            exc,
            model_config.fallback_weights,
        )
        return model_config.fallback_weights
