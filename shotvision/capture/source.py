"""Camera-agnostic frame source: device index, video file, or stream URL.

The rest of the pipeline reads frames through this one interface, so the
exact same code path runs against a recorded test clip and a live camera —
only `source` (a config value) changes.
"""
from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np

DEVICE = "device"
FILE = "file"
URL = "url"


def _classify_source(source: str) -> str:
    if source.isdigit():
        return DEVICE
    if "://" in source:
        return URL
    return FILE


class FrameSource:
    def __init__(self, source: str, loop: bool = False):
        # Config may coerce "0" to the int 0; device indices arrive either way.
        source = str(source)
        self.source = source
        self.loop = loop
        self.type = _classify_source(source)

        if self.type == DEVICE:
            cap_arg: int | str = int(source)
        elif self.type == FILE:
            path = Path(source)
            if not path.exists():
                raise FileNotFoundError(f"Video file not found: {source}")
            cap_arg = str(path)
        else:
            cap_arg = source
        self._cap_arg = cap_arg

        self._cap = cv2.VideoCapture(cap_arg)
        if not self._cap.isOpened():
            raise RuntimeError(f"Could not open video source: {source}")

        # Phones store portrait video as landscape pixels plus a rotation flag.
        # Ask OpenCV to apply the flag so the pipeline always sees the picture upright.
        if self.type != DEVICE and hasattr(cv2, "CAP_PROP_ORIENTATION_AUTO"):
            self._cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1)

    @property
    def is_file(self) -> bool:
        return self.type == FILE

    @property
    def fps(self) -> float:
        fps = self._cap.get(cv2.CAP_PROP_FPS)
        return fps if fps and fps > 0 else 30.0

    def measure_fps(self, seconds: float = 2.0, clock=time.monotonic) -> float:
        """Read and discard frames for about `seconds` and return the real
        delivery rate. For live devices, whose reported CAP_PROP_FPS can be
        wrong. The first frame is not counted (cameras often stall on start)."""
        first = self.read()
        if first is None:
            return self.fps
        start = clock()
        frames = 0
        while clock() - start < seconds:
            if self.read() is None:
                break
            frames += 1
        elapsed = clock() - start
        return frames / elapsed if frames > 0 and elapsed > 0 else self.fps

    @property
    def rotation(self) -> int:
        """Rotation flag stored in the file, in degrees (0 when absent or unsupported)."""
        if not hasattr(cv2, "CAP_PROP_ORIENTATION_META"):
            return 0
        meta = self._cap.get(cv2.CAP_PROP_ORIENTATION_META)
        return int(meta) if meta and meta > 0 else 0

    @property
    def source_key(self) -> str:
        """Stable identity used to key rim calibration. Each distinct file,
        device, or URL gets its own saved calibration."""
        if self.type == FILE:
            return f"file:{Path(self.source).resolve()}"
        if self.type == DEVICE:
            return f"device:{self._cap_arg}"
        return f"url:{self.source}"

    def read(self) -> np.ndarray | None:
        ok, frame = self._cap.read()
        if not ok:
            if self.loop and self.is_file:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = self._cap.read()
                if not ok:
                    return None
            else:
                return None
        return frame

    def read_first_frame(self) -> np.ndarray | None:
        """Peek the first frame for rim calibration. For file sources this
        rewinds playback afterward so the calibration read isn't consumed."""
        if self.is_file:
            pos = self._cap.get(cv2.CAP_PROP_POS_FRAMES)
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            frame = self.read()
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
            return frame
        return self.read()

    def release(self) -> None:
        self._cap.release()

    def __enter__(self) -> "FrameSource":
        return self

    def __exit__(self, *exc) -> None:
        self.release()
