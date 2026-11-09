"""Unit tests for experiments/review_sheets.py's plain functions.

No files, no cache, no model: only the frame-window and crop maths.
"""
from experiments.review_sheets import crop_box, window_frames


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
