"""Tests for scripts/evaluate.py's Gate A report split by camera class.

Builds fake ClipScore objects in memory (no cache, no model) and checks only
that the in-scope gate (fixed camera, single ball) is what decides pass/fail.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import evaluate
from shotvision.shot_logic.state_machine import ShotOutcome, ShotResult


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
    assert evaluate.print_gate_report([in_scope, out_of_scope], meta) is True


def test_in_scope_gate_fails_on_in_scope_false_make():
    in_scope = evaluate.ClipScore(
        clip="fixed_one",
        checks=[_check("MAKE", "MAKE") for _ in range(10)] + [_check("MISS", "MAKE")],
        spurious=[],
    )
    meta = {"fixed_one": {"camera_class": "fixed", "ball_count": "single"}}
    assert evaluate.print_gate_report([in_scope], meta) is False
