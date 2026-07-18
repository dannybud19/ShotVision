import cv2
import numpy as np
import pytest

from shotvision.capture.source import FrameSource, _classify_source


def _write_test_clip(path, num_frames=5, size=(64, 48), fps=10):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, size)
    for i in range(num_frames):
        frame = np.full((size[1], size[0], 3), i * 10, dtype=np.uint8)
        writer.write(frame)
    writer.release()


def test_classify_source():
    assert _classify_source("0") == "device"
    assert _classify_source("2") == "device"
    assert _classify_source("rtsp://192.168.1.5/stream") == "url"
    assert _classify_source("http://example.com/live.mjpg") == "url"
    assert _classify_source("clips/shot1.mp4") == "file"


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        FrameSource("does_not_exist.mp4")


def test_file_source_reads_frames_and_reports_metadata(tmp_path):
    clip_path = tmp_path / "clip.mp4"
    _write_test_clip(clip_path, num_frames=5, fps=10)

    src = FrameSource(str(clip_path))
    try:
        assert src.is_file is True
        assert src.fps == pytest.approx(10.0, abs=1.0)
        assert src.source_key == f"file:{clip_path.resolve()}"

        frames = []
        while True:
            frame = src.read()
            if frame is None:
                break
            frames.append(frame)
        assert len(frames) == 5
        assert src.read() is None  # exhausted, no loop
    finally:
        src.release()


def test_file_source_loops_when_requested(tmp_path):
    clip_path = tmp_path / "clip.mp4"
    _write_test_clip(clip_path, num_frames=3, fps=10)

    src = FrameSource(str(clip_path), loop=True)
    try:
        read_count = 0
        for _ in range(7):  # more than num_frames, should wrap at least once
            frame = src.read()
            assert frame is not None
            read_count += 1
        assert read_count == 7
    finally:
        src.release()


def test_read_first_frame_does_not_consume_playback(tmp_path):
    clip_path = tmp_path / "clip.mp4"
    _write_test_clip(clip_path, num_frames=4, fps=10)

    src = FrameSource(str(clip_path))
    try:
        first = src.read_first_frame()
        assert first is not None

        frames = []
        while True:
            frame = src.read()
            if frame is None:
                break
            frames.append(frame)
        assert len(frames) == 4  # first_frame peek didn't consume frame 0
    finally:
        src.release()


def test_source_key_distinguishes_device_and_url(monkeypatch):
    class FakeCap:
        def isOpened(self):
            return True

        def get(self, prop):
            return 30.0

        def release(self):
            pass

    monkeypatch.setattr(cv2, "VideoCapture", lambda arg: FakeCap())

    device_src = FrameSource("0")
    assert device_src.source_key == "device:0"

    url_src = FrameSource("rtsp://cam.local/stream")
    assert url_src.source_key == "url:rtsp://cam.local/stream"
