"""Tests for experiments/court_map.py. Maths only: no image, no window, no model."""
import cv2
import numpy as np
import pytest

from experiments.court_map import COURTS, fit_homography, is_three, to_court


def _fake_camera():
    """A made-up perspective view: court rectangle (metres) -> image quad (pixels)."""
    court_corners = np.float32([[-7, -1.5], [7, -1.5], [7, 9], [-7, 9]])
    image_corners = np.float32([[300, 700], [1000, 690], [880, 250], [420, 260]])
    return cv2.getPerspectiveTransform(court_corners, image_corners)


def _project(H_court_to_image, court_pts):
    pts = np.asarray(court_pts, dtype=np.float64).reshape(-1, 1, 2)
    return cv2.perspectiveTransform(pts, H_court_to_image.astype(np.float64)).reshape(-1, 2)


def test_fit_homography_recovers_court_points_within_1_cm():
    court_pts = [(-5, 0), (5, 0), (-4, 6), (4, 6), (0, 4.225), (2.5, 1.0)]
    image_pts = _project(_fake_camera(), court_pts)
    H = fit_homography(image_pts, court_pts)
    for (ix, iy), (cx, cy) in zip(image_pts, court_pts):
        got_x, got_y = to_court(H, ix, iy)
        assert abs(got_x - cx) < 0.01 and abs(got_y - cy) < 0.01
    # A point that was not used in the fit maps back too.
    extra_court = (-3.0, 3.0)
    extra_image = _project(_fake_camera(), [extra_court])[0]
    got_x, got_y = to_court(H, *extra_image)
    assert abs(got_x - extra_court[0]) < 0.01 and abs(got_y - extra_court[1]) < 0.01


def test_fewer_than_four_points_raises():
    with pytest.raises(ValueError):
        fit_homography([(0, 0), (1, 0), (1, 1)], [(0, 0), (1, 0), (1, 1)])


def test_is_three_fiba_arc():
    assert is_three((0.0, 6.0)) is False  # 6.0 m in front of the rim
    assert is_three((0.0, 7.0)) is True  # 7.0 m
    assert is_three((0.0, 6.75)) is False  # exactly on the arc counts as two
    assert is_three((0.0, 6.75), court="fiba") is False


def test_is_three_fiba_corner():
    assert is_three((6.7, 0.5)) is True  # beyond the 6.60 m corner line, inside the arc radius
    assert is_three((6.5, 0.5)) is False
    assert is_three((-6.7, 0.5)) is True  # the other corner
    assert is_three((6.60, 0.5)) is False  # exactly on the corner line counts as two


def test_is_three_nba_uses_its_own_distances():
    assert COURTS["nba"]["arc_radius"] == 7.24
    assert is_three((0.0, 7.0), court="nba") is False  # inside the NBA arc, outside the FIBA one
    assert is_three((0.0, 7.5), court="nba") is True
    assert is_three((6.8, 0.5), court="nba") is True
