"""Tests for experiments/release_error.py with hand-made files (no cache, no model).

Four scored shots (errors 0, +2, -3, +6 frames; the last at 60 fps), one owner
shot where the finder gave no release, one owner shot with no finder record.
"""
import json

import pytest

from experiments.release_error import build_report, count_cant_tell, join_rows, main, summarise

LABELS = {
    "_doc": "test",
    "shots": [
        {"clip": "a.mp4", "label_start": 10, "label_end": 40, "release_frame": 100, "note": ""},
        {"clip": "a.mp4", "label_start": 50, "label_end": 80, "release_frame": 200, "note": ""},
        {"clip": "b.mp4", "label_start": 10, "label_end": 40, "release_frame": 300, "note": ""},
        {"clip": "b.mp4", "label_start": 50, "label_end": 80, "release_frame": 400, "note": ""},
        {"clip": "c.mp4", "label_start": 10, "label_end": 40, "release_frame": 500, "note": ""},
        {"clip": "d.mp4", "label_start": 10, "label_end": 40, "release_frame": 600, "note": ""},
    ],
}


def _rec(clip, start, end, frame, fps=30.0, stop="residual"):
    return {"clip": clip, "label_start": start, "label_end": end, "release_frame": frame,
            "fps": fps, "stop_reason": stop}


MOMENT = [
    _rec("a.mp4", 10, 40, 100),
    _rec("a.mp4", 50, 80, 202, stop="gap"),
    _rec("b.mp4", 10, 40, 297, stop="curvature"),
    _rec("b.mp4", 50, 80, 406, fps=60.0, stop="ran_out"),
    {"clip": "c.mp4", "label_start": 10, "label_end": 40, "release_frame": None, "reason": "no_apex"},
    # d.mp4 has no record at all
]


def test_join_splits_scored_no_finder_and_unmatched():
    scored, no_finder, unmatched = join_rows(LABELS, MOMENT)
    assert [r["error"] for r in scored] == [0, 2, -3, 6]
    assert [r["clip"] for r in no_finder] == ["c.mp4"]
    assert no_finder[0]["reason"] == "no_apex"
    assert [r["clip"] for r in unmatched] == ["d.mp4"]


def test_error_is_finder_minus_owner_and_ms_uses_the_shot_fps():
    scored, _, _ = join_rows(LABELS, MOMENT)
    assert scored[1]["error_ms"] == pytest.approx(2 * 1000 / 30)
    assert scored[3]["error_ms"] == pytest.approx(100.0)  # +6 frames at 60 fps


def test_summary_numbers():
    scored, _, _ = join_rows(LABELS, MOMENT)
    s = summarise(scored)
    assert s["n"] == 4
    assert s["median_abs_frames"] == pytest.approx(2.5)
    assert s["p90_abs_frames"] == pytest.approx(5.1)
    assert s["median_abs_ms"] == pytest.approx((200 / 3 + 100) / 2)
    assert s["within_2"] == 2
    assert s["within_5"] == 3
    assert s["signed_mean_frames"] == pytest.approx(1.25)
    assert s["signed_mean_ms"] == pytest.approx((0 + 200 / 3 - 100 + 100) / 4)
    assert [(w["clip"], w["error"], w["stop_reason"]) for w in s["worst"]] == [
        ("b.mp4", 6, "ran_out"),
        ("b.mp4", -3, "curvature"),
        ("a.mp4", 2, "gap"),
    ]


def test_empty_input_does_not_crash():
    assert summarise([]) == {"n": 0}
    assert "No rows to score." in build_report([], [], [], 0)


def test_count_cant_tell(tmp_path):
    f = tmp_path / "decisions.md"
    f.write_text(
        "| # | Clip | Label | Outcome | Finder | Owner | Note |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| 1 | a.mp4 | 10-40 | MAKE | 100 | 100 | |\n"
        "| 2 | a.mp4 | 50-80 | MISS | 202 | CANT_TELL | |\n"
        "| 3 | b.mp4 | 10-40 | MAKE | 297 | CANT_TELL | |\n"
    )
    assert count_cant_tell(f) == 2
    assert count_cant_tell(tmp_path / "missing.md") is None


def test_main_writes_the_report(tmp_path, capsys, monkeypatch):
    labels, moment, decisions, out = (tmp_path / n for n in ("l.json", "m.json", "d.md", "out.md"))
    labels.write_text(json.dumps(LABELS))
    moment.write_text(json.dumps(MOMENT))
    decisions.write_text("| 1 | a.mp4 | 10-40 | MAKE | 100 | CANT_TELL | |\n")
    monkeypatch.setattr("sys.argv", ["release_error", "--labels", str(labels), "--moment", str(moment),
                                     "--decisions", str(decisions), "--out", str(out)])
    assert main() == 0
    text = out.read_text()
    assert "Owner rows scored: 4" in text
    assert "Owner rows where the finder gave no release: 1" in text
    assert "Owner rows with no finder record: 1" in text
    assert "CANT_TELL rows: 1" in text
    assert "| ±2 frames | 2/4 | 50% |" in text
    assert "| ±5 frames | 3/4 | 75% |" in text
    assert "ran_out" in text
