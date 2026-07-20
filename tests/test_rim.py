import pytest

from shotvision.shot_logic.rim import RimRegion


def _sample_rim(shrink=0.15):
    # Rim box from x=100..200, y=50..70 -> width 100, height 20
    points = [(100, 50), (200, 50), (100, 70), (200, 70)]
    return RimRegion.from_points(points, inner_bound_shrink=shrink)


def test_from_points_computes_outer_and_inner_bounds():
    rim = _sample_rim(shrink=0.15)
    assert rim.outer_left == 100
    assert rim.outer_right == 200
    assert rim.outer_top == 50
    assert rim.outer_bottom == 70
    # shrink = 100 * 0.15 = 15 on each side
    assert rim.inner_left == 115
    assert rim.inner_right == 185


def test_from_points_is_order_independent():
    scrambled = [(200, 70), (100, 50), (200, 50), (100, 70)]
    rim = RimRegion.from_points(scrambled, inner_bound_shrink=0.15)
    assert rim.outer_left == 100
    assert rim.outer_right == 200
    assert rim.outer_top == 50
    assert rim.outer_bottom == 70


def test_from_points_requires_exactly_four():
    with pytest.raises(ValueError):
        RimRegion.from_points([(0, 0), (1, 1)], inner_bound_shrink=0.15)


def test_center_x_and_outer_width():
    rim = _sample_rim()
    assert rim.outer_width == 100
    assert rim.center_x == 150


def test_is_aligned_within_and_outside_tolerance():
    rim = _sample_rim()  # center_x=150, half-width=50
    assert rim.is_aligned(150, tolerance_ratio=0.0) is True
    assert rim.is_aligned(199, tolerance_ratio=0.0) is True  # within outer box
    assert rim.is_aligned(260, tolerance_ratio=0.0) is False  # 110 > half-width 50
    # tolerance_ratio=0.6 widens allowed span to 50 * 1.6 = 80
    assert rim.is_aligned(225, tolerance_ratio=0.6) is True  # 75 <= 80
    assert rim.is_aligned(260, tolerance_ratio=0.6) is False  # 110 > 80


def test_is_inside_inner_bounds():
    rim = _sample_rim(shrink=0.15)  # inner 115..185
    assert rim.is_inside_inner_bounds(150) is True
    assert rim.is_inside_inner_bounds(115) is True
    assert rim.is_inside_inner_bounds(185) is True
    assert rim.is_inside_inner_bounds(110) is False
    assert rim.is_inside_inner_bounds(190) is False


def test_vertical_position_checks():
    rim = _sample_rim()  # top=50, bottom=70
    assert rim.is_above(40) is True
    assert rim.is_above(60) is False
    assert rim.is_in_band(50) is True
    assert rim.is_in_band(60) is True
    assert rim.is_in_band(70) is True
    assert rim.is_in_band(30) is False
    assert rim.is_below(80) is True
    assert rim.is_below(60) is False


def test_to_dict_and_from_dict_round_trip():
    rim = _sample_rim(shrink=0.15)
    restored = RimRegion.from_dict(rim.to_dict())
    assert restored == rim


def test_from_bbox_matches_from_points():
    from_bbox = RimRegion.from_bbox((100, 50, 200, 70), inner_bound_shrink=0.15)
    from_points = _sample_rim(shrink=0.15)
    assert from_bbox == from_points
