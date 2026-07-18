from shotvision.detection.device import resolve_device, select_model_size


def test_explicit_device_is_passed_through():
    device, reason = resolve_device("cpu")
    assert device == "cpu"
    assert "explicitly configured" in reason


def test_auto_resolves_to_a_real_device():
    # On any machine this should resolve to one of the three, never crash.
    device, reason = resolve_device("auto")
    assert device in ("cuda", "mps", "cpu")
    assert reason


def test_select_model_size_favors_speed_on_cpu():
    assert select_model_size("cpu") == "n"
    assert select_model_size("mps") == "s"
    assert select_model_size("cuda") == "s"
