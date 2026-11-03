"""Resolves the ball/hoop detection checkpoint: use it if already cached
under models/, download the default fine-tune if not, or fall back to a
stock COCO checkpoint (which ultralytics downloads/caches itself) if the
download fails.
"""
from __future__ import annotations

import logging
import hashlib
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
# SHA256 of the checkpoint at DEFAULT_CHECKPOINT_URL as first downloaded and
# validated (2026-11-03). A .pt file is a pickle, and loading one can run
# code, so a download that doesn't match is discarded instead of loaded.
# Only downloads are checked: your own weights at model.weights load as-is.
DEFAULT_CHECKPOINT_SHA256 = "72c1e7c64cc6054db3dc5429385630f81c2136f5935fed546e6887bfe158d306"


class ChecksumMismatch(Exception):
    pass


def _download(url: str, dest: Path, sha256: str | None = DEFAULT_CHECKPOINT_SHA256) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_dest = dest.with_suffix(dest.suffix + ".part")
    digest = hashlib.sha256()
    with urllib.request.urlopen(url, context=_SSL_CONTEXT, timeout=60) as response:
        with open(tmp_dest, "wb") as f:
            while chunk := response.read(1 << 20):
                digest.update(chunk)
                f.write(chunk)
    if sha256 is not None and digest.hexdigest() != sha256:
        tmp_dest.unlink(missing_ok=True)
        raise ChecksumMismatch(
            f"downloaded checkpoint SHA256 {digest.hexdigest()} != expected {sha256}"
        )
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
            "back to COCO checkpoint '%s' — it has no hoop class, so the rim "
            "can't be located and shot logic won't run.",
            exc,
            model_config.fallback_weights,
        )
        return model_config.fallback_weights
