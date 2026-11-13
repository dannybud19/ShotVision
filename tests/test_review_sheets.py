"""Unit tests for experiments/review_sheets.py's plain functions.

No files, no cache, no model: only the frame-window and crop maths.
"""
from dataclasses import dataclass

import pytest

from experiments.review_sheets import (
    HEADER_NOTE,
    build_header_text,
    camera_stats,
    crop_box,
    parse_args,
    spread_indices,
    window_frames,
)


@dataclass
class _Det:
    class_name: str
    conf: float
    bbox: tuple


def test_window_frames_at_60_fps_defaults():
    frames = window_frames(600, 60, 1.5, 0.5, 0.1)
    assert len(frames) == 21
    assert frames[0] == 510
    assert frames[-1] == 630
    assert {b - a for a, b in zip(frames, frames[1:])} == {6}


def test_crop_box_centres_on_median_hoop():
    # hoop width 40, centre (500, 300); frame 1000 x 1000 (h, w, channels)
    boxes = [(480, 280, 520, 320)] * 5
    x1, y1, x2, y2 = crop_box(boxes, (1000, 1000, 3))
    assert (x2 - x1, y2 - y1) == (240, 200)  # 6 x 40 by 5 x 40
    assert ((x1 + x2) / 2, (y1 + y2) / 2) == (500, 300)


def test_crop_box_clamps_at_the_left_edge():
    boxes = [(10, 280, 50, 320)] * 5  # centre x 30, so a centred crop would start at -90
    x1, y1, x2, y2 = crop_box(boxes, (1000, 1000, 3))
    assert x1 == 0
    assert (x2 - x1, y2 - y1) == (240, 200)  # size kept, box moved inside the image


def test_crop_box_uses_the_median_not_one_odd_box():
    boxes = [(480, 280, 520, 320)] * 4 + [(100, 100, 140, 140)]
    x1, y1, x2, y2 = crop_box(boxes, (1000, 1000, 3))
    assert ((x1 + x2) / 2, (y1 + y2) / 2) == (500, 300)


def test_crop_box_with_no_hoop_is_the_full_frame():
    assert crop_box([], (480, 640, 3)) == (0, 0, 640, 480)


def test_camera_stats_flags_the_frame_with_a_second_far_hoop():
    still = _Det("hoop", 0.9, (100, 100, 140, 140))
    far_and_surer = _Det("hoop", 0.95, (500, 400, 540, 440))
    dets = [[still] for _ in range(10)]
    dets[5] = [still, far_and_surer]
    stats = camera_stats(dets)
    assert stats["frames_with_hoop"] == 10
    assert stats["share_with_2plus_hoops"] == pytest.approx(1 / 10)
    assert 5 in stats["jump_frames"]
    assert stats["jump_frames"][0] == 5  # the biggest jump comes first
    assert stats["max_jump"] > 5


def test_camera_stats_still_hoop_has_no_jump_and_ignores_low_confidence():
    dets = [[_Det("hoop", 0.9, (100, 100, 140, 140)), _Det("hoop", 0.4, (500, 400, 540, 440))] for _ in range(6)]
    stats = camera_stats(dets)
    assert stats["share_with_2plus_hoops"] == 0.0
    assert stats["max_jump"] == 0.0


def test_camera_stats_with_no_hoop_at_all():
    stats = camera_stats([[] for _ in range(5)])
    assert stats["frames_with_hoop"] == 0
    assert stats["jump_frames"] == []


def test_spread_indices_cover_the_clip():
    idx = spread_indices(1000)
    assert len(idx) == 8
    assert idx[0] == 0 and idx[-1] == 999


def test_frames_header_uses_the_default_note_unless_label_is_given():
    base = ["frames", "--clip", "x.mp4", "--frames", "100"]
    default_args = parse_args(base)
    assert default_args.label == HEADER_NOTE == "pipeline: spurious MAKE"
    assert "pipeline: spurious MAKE" in build_header_text("x", 100, default_args.label, 90, 110)

    custom_args = parse_args(base + ["--label", "release candidate"])
    text = build_header_text("x", 100, custom_args.label, 90, 110)
    assert text == "x  target f100  release candidate  window f90-f110"
    assert "spurious MAKE" not in text
