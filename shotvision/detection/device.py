"""Inference device auto-detection: cuda > mps > cpu, with graceful fallback."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def resolve_device(configured: str = "auto") -> tuple[str, str]:
    """Returns (device, reason). `configured` is 'auto', 'cuda', 'mps', or 'cpu'
    from ModelConfig.device; 'auto' probes hardware in that priority order."""
    if configured != "auto":
        return configured, f"device explicitly configured as '{configured}'"

    try:
        import torch
    except ImportError:
        return "cpu", "torch is not installed"

    if torch.cuda.is_available():
        name = torch.cuda.get_device_name(0)
        return "cuda", f"CUDA GPU available ({name})"

    try:
        mps_available = torch.backends.mps.is_available()
    except Exception:
        mps_available = False

    if mps_available:
        return "mps", "Apple Silicon GPU (MPS) available"

    return "cpu", "no CUDA or MPS GPU detected — running on CPU"


def select_model_size(device: str) -> str:
    """YOLO size suffix ('n' vs 's') for the COCO fallback path only. The
    default basketball checkpoint is a fixed fine-tune, independent of
    device — this only matters if we've fallen back to a stock COCO model."""
    return "n" if device == "cpu" else "s"


def log_device_choice(device: str, reason: str) -> None:
    logger.info("Selected inference device: %s (%s)", device, reason)
    print(f"[ShotVision] Using device: {device} — {reason}")
