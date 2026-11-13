"""Tests for scripts/evaluate.py's Gate A report split by camera class.

Builds fake ClipScore objects in memory (no cache, no model) and checks only
that the in-scope gate (fixed camera, single ball) is what decides pass/fail.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import evaluate
from shotvision.shot_logic.state_machine import ResolutionReason, ShotOutcome, ShotResult


def _check(label_outcome: str, result_outcome: str) -> evaluate.ShotCheck:
    return evaluate.ShotCheck(
        label={"outcome": label_outcome, "start": 0, "end": 10},
        result=ShotResult(outcome=ShotOutcome[result_outcome], frame_idx=0),
    )


def test_in_scope_gate_passes_despite_out_of_scope_false_make():
    in_scope = evaluate.ClipScore(
        clip="fixed_one",
        checks=[_check("MAKE", "MAKE") for _ in range(10)],
        spurious=[],
    )
    out_of_scope = evaluate.ClipScore(
        clip="moving_multi",
        checks=[_check("MISS", "MAKE")],  # a false make, but out of scope
        spurious=[],
    )
    meta = {
        "fixed_one": {"camera_class": "fixed", "ball_count": "single"},
        "moving_multi": {"camera_class": "moving", "ball_count": "multi"},
    }
    # min_misses=0: this test is about scope, not sample size.
    assert evaluate.print_gate_report([in_scope, out_of_scope], meta, min_misses=0) is True


def test_in_scope_gate_fails_on_in_scope_false_make():
    in_scope = evaluate.ClipScore(
        clip="fixed_one",
        checks=[_check("MAKE", "MAKE") for _ in range(10)] + [_check("MISS", "MAKE")],
        spurious=[],
    )
    meta = {"fixed_one": {"camera_class": "fixed", "ball_count": "single"}}
    assert evaluate.print_gate_report([in_scope], meta) is False


_IN_SCOPE_META = {"fixed_one": {"camera_class": "fixed", "ball_count": "single"}}
_IN_SCOPE_LINE = "GATE A (in scope: fixed camera, single ball): "


def _lost_make() -> evaluate.ShotCheck:
    """A labeled MAKE the pipeline resolved as MISS (the report reads the reason of a lost make)."""
    check = _check("MAKE", "MISS")
    check.result.reason = ResolutionReason.MISS_BELOW_WITHOUT_INNER
    return check


def _in_scope_report(checks, capsys):
    clip = evaluate.ClipScore(clip="fixed_one", checks=checks, spurious=[])
    result = evaluate.print_gate_report([clip], _IN_SCOPE_META)
    return result, capsys.readouterr().out


def test_not_enough_misses_is_not_a_pass(capsys):
    checks = [_check("MAKE", "MAKE") for _ in range(10)]
    result, out = _in_scope_report(checks, capsys)
    assert result is False
    assert "NOT ENOUGH MISSES TO JUDGE (0 < 50)" in out


def test_pass_with_enough_misses(capsys):
    checks = [_check("MAKE", "MAKE") for _ in range(10)] + [_check("MISS", "MISS") for _ in range(50)]
    result, out = _in_scope_report(checks, capsys)
    assert result is True
    assert _IN_SCOPE_LINE + "PASS" in out


def test_false_make_fails_even_with_few_misses(capsys):
    checks = (
        [_check("MAKE", "MAKE") for _ in range(10)]
        + [_check("MISS", "MAKE")]
        + [_check("MISS", "MISS") for _ in range(4)]
    )
    result, out = _in_scope_report(checks, capsys)
    assert result is False
    assert _IN_SCOPE_LINE + "FAIL" in out
    assert "NOT ENOUGH" not in out


def test_low_make_rate_fails_even_with_few_misses(capsys):
    checks = (
        [_check("MAKE", "MAKE") for _ in range(8)]
        + [_lost_make() for _ in range(2)]
        + [_check("MISS", "MISS") for _ in range(3)]
    )
    result, out = _in_scope_report(checks, capsys)
    assert result is False
    assert _IN_SCOPE_LINE + "FAIL" in out


def test_lost_make_without_reason_does_not_crash(capsys):
    check = evaluate.ShotCheck(
        label={"outcome": "MAKE", "start": 0, "end": 10},
        result=ShotResult(outcome=ShotOutcome.MISS, frame_idx=0),  # no reason passed
    )
    clip = evaluate.ClipScore(clip="fixed_one", checks=[check], spurious=[])
    evaluate.print_gate_report([clip], _IN_SCOPE_META, min_misses=0)
    assert "make lost: no reason recorded" in capsys.readouterr().out
