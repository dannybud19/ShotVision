"""Side-by-side experiment: ShotVision vs the "line through the rim" method.

Method idea from avishah3/AI-Basketball-Shot-Detection-Tracker (no licence;
reimplemented from a description, no code copied).

See docs/plans/PLAN_2_line_crossing_experiment.md.

Variants: SV (ShotVision as is), L0 to L4 (the line/arc method with one change
per step), H1 to H3 (ShotVision plus a limited line-method rescue).

This module only creates new files and only reads the cached detections in
experiments/.cache/detections. It never loads the model.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import math
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import evaluate as ev  # noqa: E402
from shotvision.config.settings import load_config, to_frames  # noqa: E402
from shotvision.shot_logic.state_machine import (  # noqa: E402
    ResolutionReason,
    ShotOutcome,
    ShotResult,
)


@dataclass
class Point:
    """One detected box reduced to a centre plus size, tagged with its frame."""

    cx: float
    cy: float
    w: float
    h: float
    frame: int


@dataclass
class VariantSpec:
    id: str
    ball_points: str  # "all" | "best"
    gap_limit: bool
    method: str  # "line" | "arc"
    make_zone: str  # "±10" | "strict"


VARIANTS = {
    "L0": VariantSpec("L0", "all", False, "line", "±10"),
    "L1": VariantSpec("L1", "best", False, "line", "±10"),
    "L2": VariantSpec("L2", "best", True, "line", "±10"),
    "L3": VariantSpec("L3", "best", True, "line", "strict"),
    "L4": VariantSpec("L4", "best", True, "arc", "strict"),
}

VARIANT_IDS = ["SV", "L0", "L1", "L2", "L3", "L4", "H1", "H2", "H3"]


def _clean_hoop(hoop_pos: list[Point], fps: float) -> None:
    """Reject a hop/box that moved implausibly or is too skewed (spec 2.2)."""
    if len(hoop_pos) <= 1:
        return
    p1, p2 = hoop_pos[-2], hoop_pos[-1]
    moved = math.hypot(p2.cx - p1.cx, p2.cy - p1.cy)
    removed = False
    if moved > 0.5 * math.hypot(p1.w, p1.h) and (p2.frame - p1.frame) < to_frames(0.1667, fps):
        hoop_pos.pop()
        removed = True
    if not removed:
        if p2.w * 1.3 < p2.h or p2.h * 1.3 < p2.w:
            hoop_pos.pop()
    if len(hoop_pos) > 25:
        del hoop_pos[: len(hoop_pos) - 25]


def _clean_ball(ball_pos: list[Point], fps: float) -> None:
    """Reject a ball point that jumped implausibly or is too skewed (spec 2.3)."""
    if len(ball_pos) <= 1:
        return
    p1, p2 = ball_pos[-2], ball_pos[-1]
    moved = math.hypot(p2.cx - p1.cx, p2.cy - p1.cy)
    if moved > 4 * math.hypot(p1.w, p1.h) and (p2.frame - p1.frame) < to_frames(0.1667, fps):
        ball_pos.pop()
    elif p2.w * 1.4 < p2.h or p2.h * 1.4 < p2.w:
        ball_pos.pop()


def _line_cross_x(A: Point, B: Point, rim_line: float) -> float | None:
    """x where the straight line A->B crosses rim_line, or None if it cannot
    (a horizontal line). Vertical lines return A.cx (spec 2.5)."""
    if abs(B.cx - A.cx) < 1e-6:
        return A.cx
    m = (B.cy - A.cy) / (B.cx - A.cx)
    if m == 0:
        return None
    b = A.cy - m * A.cx
    return (rim_line - b) / m


def _record(
    outcome: ShotOutcome,
    down_frame: int,
    method: str,
    up_frame: int | None,
    gap: int | None,
    predicted_x: float | None,
    hx: float,
    hw: float,
    A: Point | None,
    B: Point | None,
) -> tuple[ShotResult, dict]:
    """Build a ShotResult plus its diagnostic record.

    The ShotResult.reason is a placeholder (MAKE_CONFIRMED / MISS_BELOW_WITHOUT_INNER)
    so score_clip and print_gate_report can run unchanged. The real decision path
    lives in the diagnostic "method" field.
    """
    reason = ResolutionReason.MAKE_CONFIRMED if outcome == ShotOutcome.MAKE else ResolutionReason.MISS_BELOW_WITHOUT_INNER
    result = ShotResult(outcome, down_frame, reason=reason)
    px_hoop = (predicted_x - hx) / hw if predicted_x is not None else None
    diag = {
        "frame_idx": down_frame,
        "outcome": outcome.value,
        "method": method,
        "up_frame": up_frame,
        "down_frame": down_frame,
        "gap_frames": gap,
        "predicted_x": predicted_x,
        "predicted_x_in_hoop_widths": px_hoop,
        "A": {"cx": A.cx, "cy": A.cy, "frame": A.frame} if A is not None else None,
        "B": {"cx": B.cx, "cy": B.cy, "frame": B.frame} if B is not None else None,
    }
    return result, diag


def _score(
    ball_pos: list[Point],
    hoop: Point,
    spec: VariantSpec,
    fps: float,
    up_frame: int,
    down_frame: int,
) -> tuple[ShotResult, dict]:
    hx, hy, hw, hh = hoop.cx, hoop.cy, hoop.w, hoop.h
    rim_line = hy - 0.5 * hh

    i = None
    for idx in range(len(ball_pos) - 1, -1, -1):
        if ball_pos[idx].cy < rim_line:
            i = idx
            break
    if i is None:
        return _record(ShotOutcome.MISS, down_frame, "no_above_point", up_frame, None, None, hx, hw, None, None)
    if i == len(ball_pos) - 1:
        return _record(ShotOutcome.MISS, down_frame, "no_point_after", up_frame, None, None, hx, hw, None, None)

    A = ball_pos[i]
    B = ball_pos[i + 1]
    gap = B.frame - A.frame
    if spec.gap_limit and gap > to_frames(0.5, fps):
        return _record(ShotOutcome.MISS, down_frame, "gap_too_long", up_frame, gap, None, hx, hw, A, B)

    predicted_x = None
    method = "line"
    if spec.method == "arc":
        pts = [p for p in ball_pos if p.cy < rim_line and A.frame - to_frames(0.5, fps) <= p.frame <= A.frame]
        pts.append(B)
        if len(pts) < 3:
            predicted_x = _line_cross_x(A, B, rim_line)
            method = "arc_fallback"
        else:
            t = np.array([p.frame for p in pts], dtype=float)
            x = np.array([p.cx for p in pts], dtype=float)
            y = np.array([p.cy for p in pts], dtype=float)
            xfit = np.polyfit(t, x, 1)
            yfit = np.polyfit(t, y, 2)
            a, b, c = float(yfit[0]), float(yfit[1]), float(yfit[2])
            if a <= 0:
                predicted_x = _line_cross_x(A, B, rim_line)
                method = "arc_fallback"
            else:
                roots = np.roots([a, b, c - rim_line])
                real_roots = sorted(float(r.real) for r in roots if abs(r.imag) < 1e-9 and r.real > A.frame)
                if not real_roots:
                    return _record(ShotOutcome.MISS, down_frame, "arc", up_frame, gap, None, hx, hw, A, B)
                root = real_roots[0]
                if root - A.frame > to_frames(0.5, fps):
                    return _record(ShotOutcome.MISS, down_frame, "gap_too_long", up_frame, gap, None, hx, hw, A, B)
                predicted_x = float(np.polyval(xfit, root))
                method = "arc"
    else:
        predicted_x = _line_cross_x(A, B, rim_line)

    if predicted_x is None:
        # horizontal line (m == 0): cannot cross, MISS.
        return _record(ShotOutcome.MISS, down_frame, method, up_frame, gap, None, hx, hw, A, B)

    left = hx - 0.4 * hw
    right = hx + 0.4 * hw
    if spec.make_zone == "±10":
        in_zone = left - 10 < predicted_x < right + 10
    else:
        in_zone = left < predicted_x < right
    outcome = ShotOutcome.MAKE if in_zone else ShotOutcome.MISS
    return _record(outcome, down_frame, method, up_frame, gap, predicted_x, hx, hw, A, B)


def run_line_method(dets, fps: float, spec: VariantSpec) -> tuple[list[ShotResult], list[dict]]:
    """Run the line/arc method over cached detections (spec sections 2.2 to 2.7).

    Returns (results, diagnostics) with results[i] paired with diagnostics[i].
    """
    hoop_pos: list[Point] = []
    ball_pos: list[Point] = []
    up = down = False
    up_frame = down_frame = None
    results: list[ShotResult] = []
    diags: list[dict] = []

    for frame_idx, frame_dets in enumerate(dets):
        hoops = [d for d in frame_dets if d.class_name == "hoop" and d.conf > 0.5]
        if hoops:
            d = max(hoops, key=lambda d: d.conf)
            x1, y1, x2, y2 = d.bbox
            hoop_pos.append(Point((x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1, frame_idx))
            _clean_hoop(hoop_pos, fps)
        if not hoop_pos:
            continue  # no current hoop: nothing else this frame

        hx, hy, hw, hh = hoop_pos[-1].cx, hoop_pos[-1].cy, hoop_pos[-1].w, hoop_pos[-1].h

        balls = [d for d in frame_dets if d.class_name == "ball"]
        cands: list[Point] = []
        for d in balls:
            x1, y1, x2, y2 = d.bbox
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            w, h = x2 - x1, y2 - y1
            in_region = (hx - hw < cx < hx + hw) and (hy - hh < cy < hy + 0.5 * hh)
            if d.conf > 0.3 or (d.conf > 0.15 and in_region):
                cands.append((d.conf, Point(cx, cy, w, h, frame_idx)))
        if spec.ball_points == "best":
            cands = [max(cands, key=lambda t: t[0])] if cands else []
        for _, p in cands:
            ball_pos.append(p)
            _clean_ball(ball_pos, fps)

        if ball_pos and frame_idx - ball_pos[0].frame > to_frames(1.0, fps):
            ball_pos.pop(0)

        newest = ball_pos[-1] if ball_pos else None
        if newest is not None:
            if not up and hx - 4 * hw < newest.cx < hx + 4 * hw and hy - 2 * hh < newest.cy < hy - 0.5 * hh:
                up = True
                up_frame = newest.frame
            if up and newest.cy > hy + 0.5 * hh:
                down = True
                down_frame = newest.frame

        step = to_frames(0.3333, fps)
        if frame_idx % step == 0:
            if up and down and up_frame < down_frame:
                result, diag = _score(ball_pos, hoop_pos[-1], spec, fps, up_frame, down_frame)
                results.append(result)
                diags.append(diag)
                up = down = False

    return results, diags


def _nearby_make_index(line_results: list[ShotResult], frame_idx: int, fps: float) -> int | None:
    for j, lr in enumerate(line_results):
        if lr.outcome == ShotOutcome.MAKE and abs(lr.frame_idx - frame_idx) <= to_frames(1.0, fps):
            return j
    return None


def apply_hybrid(
    sv_results: list[ShotResult],
    line_results: list[ShotResult],
    line_diag: list[dict],
    fps: float,
    add_new: bool,
    diag_by_id: dict | None = None,
) -> list[ShotResult]:
    """Rescue ShotVision results with the line method (spec section 3).

    For every SV result with reason MISS_OCCLUSION_GAP or MISS_TIMEOUT_OCCLUDED,
    if a line-method MAKE lies within 1.0 s of its frame, change it to MAKE
    (keeping SV's frame_idx). With add_new, also add every line MAKE that has no
    SV result within 1.0 s.

    Returns the result list (SV results first, then any added). If diag_by_id is
    a dict, rescued/added results get a diagnostic entry keyed by id(result).
    """
    results: list[ShotResult] = []
    for r in sv_results:
        if r.reason in (ResolutionReason.MISS_OCCLUSION_GAP, ResolutionReason.MISS_TIMEOUT_OCCLUDED):
            j = _nearby_make_index(line_results, r.frame_idx, fps)
            if j is not None:
                new_r = replace(r, outcome=ShotOutcome.MAKE, reason=ResolutionReason.MAKE_CONFIRMED)
                results.append(new_r)
                if diag_by_id is not None:
                    diag_by_id[id(new_r)] = {
                        "note": "rescued",
                        "frame_idx": new_r.frame_idx,
                        "outcome": "MAKE",
                        "gap_frames": line_diag[j].get("gap_frames"),
                        "predicted_x_in_hoop_widths": line_diag[j].get("predicted_x_in_hoop_widths"),
                        "method": line_diag[j].get("method"),
                    }
                continue
        results.append(r)

    if add_new:
        for j, lr in enumerate(line_results):
            if lr.outcome != ShotOutcome.MAKE:
                continue
            if any(abs(sv.frame_idx - lr.frame_idx) <= to_frames(1.0, fps) for sv in sv_results):
                continue
            results.append(lr)
            if diag_by_id is not None:
                diag_by_id[id(lr)] = {
                    "note": "added",
                    "frame_idx": lr.frame_idx,
                    "outcome": "MAKE",
                    "gap_frames": line_diag[j].get("gap_frames"),
                    "predicted_x_in_hoop_widths": line_diag[j].get("predicted_x_in_hoop_widths"),
                    "method": line_diag[j].get("method"),
                }
    return results


# ---------------------------------------------------------------------------
# Aggregation for the summary table and the report lists.
# ---------------------------------------------------------------------------


def _source_group(meta: dict, clip: str) -> str:
    return (meta.get(clip, {}).get("source") or {}).get("group") or ""


def build_summary(scores: dict[str, list], meta: dict) -> list[dict]:
    """One row per variant, using the same definitions as print_gate_report."""
    rows = []
    for vid in VARIANT_IDS:
        makes = counted = misses = false_makes = spurious_makes = 0
        in_makes = in_counted = in_false_spur = 0
        lg_makes = lg_counted = lg_false_spur = 0
        for sc in scores[vid]:
            clip = sc.clip
            m = meta.get(clip, {})
            g = _source_group(meta, clip)
            is_legacy = g.startswith("github:")
            is_in_scope = m.get("camera_class") == "fixed" and m.get("ball_count") == "single"
            for c in sc.checks:
                got = c.result.outcome.value if c.result is not None else None
                if c.label["outcome"] == "MAKE":
                    makes += 1
                    if is_in_scope:
                        in_makes += 1
                    if is_legacy:
                        lg_makes += 1
                    if got == "MAKE":
                        counted += 1
                        if is_in_scope:
                            in_counted += 1
                        if is_legacy:
                            lg_counted += 1
                else:
                    misses += 1
                    if got == "MAKE":
                        false_makes += 1
                        if is_in_scope:
                            in_false_spur += 1
                        if is_legacy:
                            lg_false_spur += 1
            for r in sc.spurious:
                if r.outcome.value == "MAKE":
                    spurious_makes += 1
                    if is_in_scope:
                        in_false_spur += 1
                    if is_legacy:
                        lg_false_spur += 1
        ub = ev.binomial_upper_bound(false_makes + spurious_makes, misses)
        rows.append(
            {
                "variant": vid,
                "makes": makes,
                "counted": counted,
                "misses": misses,
                "false_makes": false_makes,
                "spurious_makes": spurious_makes,
                "ub": ub,
                "in_makes": in_makes,
                "in_counted": in_counted,
                "in_false_spur": in_false_spur,
                "lg_makes": lg_makes,
                "lg_counted": lg_counted,
                "lg_false_spur": lg_false_spur,
            }
        )
    return rows


def _fmt_rate(counted: int, makes: int) -> str:
    return f"{counted}/{makes}"


def _summary_markdown(rows: list[dict]) -> str:
    lines = [
        "| variant | makes counted / makes | false makes / misses | spurious makes | 95% upper bound | in-scope makes counted | in-scope false+spurious | legacy GitHub clips |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        ub = f"{100 * r['ub']:.1f}%"
        in_scope_makes = f"{r['in_counted']}/{r['in_makes']}" if r["in_makes"] else "0/0"
        legacy = f"{r['lg_counted']}/{r['lg_makes']} makes, {r['lg_false_spur']} false+spur"
        lines.append(
            f"| {r['variant']} | {r['counted']}/{r['makes']} | {r['false_makes']}/{r['misses']} "
            f"| {r['spurious_makes']} | {ub} | {in_scope_makes} | {r['in_false_spur']} | {legacy} |"
        )
    return "\n".join(lines)


def _fmt_px(px: float | None) -> str:
    return "" if px is None else f"{px:.2f}"


def _fmt_gap(gap: int | None) -> str:
    return "" if gap is None else str(gap)


def collect_false_makes(scores: dict[str, list], diag_map: dict[str, dict]) -> list[dict]:
    """Every false make and spurious make, for every variant (spec 7.2)."""
    rows = []
    for vid in VARIANT_IDS:
        for sc in scores[vid]:
            clip = sc.clip
            for c in sc.checks:
                if c.label["outcome"] == "MISS" and c.result is not None and c.result.outcome.value == "MAKE":
                    di = diag_map[vid].get(id(c.result), {})
                    rows.append(
                        {
                            "variant": vid,
                            "clip": clip,
                            "card": c.label.get("card", ""),
                            "label_start": c.label["start"],
                            "label_end": c.label["end"],
                            "result_frame": c.result.frame_idx,
                            "gap_frames": di.get("gap_frames"),
                            "predicted_x": di.get("predicted_x_in_hoop_widths"),
                            "miss_type": c.label.get("miss_type") or "untyped",
                        }
                    )
            for r in sc.spurious:
                if r.outcome.value == "MAKE":
                    di = diag_map[vid].get(id(r), {})
                    rows.append(
                        {
                            "variant": vid,
                            "clip": clip,
                            "card": "spurious",
                            "label_start": "",
                            "label_end": "",
                            "result_frame": r.frame_idx,
                            "gap_frames": di.get("gap_frames"),
                            "predicted_x": di.get("predicted_x_in_hoop_widths"),
                            "miss_type": "spurious",
                        }
                    )
    rows.sort(key=lambda r: (r["clip"], r["result_frame"], r["variant"]))
    return rows


def _false_make_markdown(rows: list[dict]) -> str:
    if not rows:
        return "_None._"
    lines = [
        "| variant | clip | card | label frames | result frame | gap_frames | predicted_x (hoop widths) | miss type |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        label_frames = f"{r['label_start']}-{r['label_end']}" if r["label_start"] != "" else "spurious"
        lines.append(
            f"| {r['variant']} | {r['clip']} | {r['card']} | {label_frames} | {r['result_frame']} "
            f"| {_fmt_gap(r['gap_frames'])} | {_fmt_px(r['predicted_x'])} | {r['miss_type']} |"
        )
    return "\n".join(lines)


def collect_gains_losses(scores: dict[str, list]) -> tuple[dict[str, list], dict[str, list]]:
    """Makes gained over SV and lost compared with SV, per variant (spec 7.3/7.4)."""
    gained: dict[str, list] = {vid: [] for vid in VARIANT_IDS}
    lost: dict[str, list] = {vid: [] for vid in VARIANT_IDS}
    sv_scores = scores["SV"]
    for vid in VARIANT_IDS:
        if vid == "SV":
            continue
        for sv_sc, var_sc in zip(sv_scores, scores[vid]):
            clip = var_sc.clip
            for sv_c, var_c in zip(sv_sc.checks, var_sc.checks):
                if sv_c.label["outcome"] != "MAKE":
                    continue
                sv_make = sv_c.result is not None and sv_c.result.outcome.value == "MAKE"
                var_make = var_c.result is not None and var_c.result.outcome.value == "MAKE"
                if var_make and not sv_make:
                    sv_reason = sv_c.result.reason.value if sv_c.result is not None else "never armed"
                    gained[vid].append(
                        {
                            "clip": clip,
                            "card": var_c.label.get("card", ""),
                            "label_start": var_c.label["start"],
                            "label_end": var_c.label["end"],
                            "sv_reason": sv_reason,
                        }
                    )
                elif sv_make and not var_make:
                    lost[vid].append(
                        {
                            "clip": clip,
                            "card": var_c.label.get("card", ""),
                            "label_start": var_c.label["start"],
                            "label_end": var_c.label["end"],
                        }
                    )
    return gained, lost


def count_gap_arc(diags: dict[str, list]) -> dict[str, dict]:
    """How many L2-L4 shots were decided by gap_too_long and arc_fallback (spec 7.5)."""
    out = {}
    for vid in ("L2", "L3", "L4"):
        gap_too_long = sum(1 for d in diags[vid] if d.get("method") == "gap_too_long")
        arc_fallback = sum(1 for d in diags[vid] if d.get("method") == "arc_fallback")
        out[vid] = {"gap_too_long": gap_too_long, "arc_fallback": arc_fallback}
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Line-through-the-rim side-by-side experiment")
    p.add_argument("--out", help="Write the Markdown report here")
    p.add_argument("--json", help="Write every per-shot diagnostic here")
    p.add_argument("--clips", nargs="*", help="Only these clip filenames")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config()
    labels = ev.load_labels(split="all", include_duplicates=False)
    meta = ev.load_clip_meta()
    clips = [c for c in labels if not args.clips or c in args.clips]
    if not clips:
        print("No labeled clips to evaluate.")
        return 1

    scores: dict[str, list] = {v: [] for v in VARIANT_IDS}
    diags: dict[str, list] = {v: [] for v in VARIANT_IDS}
    diag_map: dict[str, dict] = {v: {} for v in VARIANT_IDS}
    hybrid_counts: dict[str, dict] = {"H1": {"changed": 0, "added": 0}, "H2": {"changed": 0, "added": 0}, "H3": {"changed": 0, "added": 0}}

    for clip in clips:
        path = ev.CLIPS_DIR / clip
        fps = ev.clip_fps(path)
        dets = ev.load_detections(path, config)
        sv = ev.replay(dets, config, fps=fps)
        sv_results = sv.results

        scores["SV"].append(ev.score_clip(clip, labels[clip], sv, 0.6, to_frames(0.2, fps), fps))
        for r in sv_results:
            diags["SV"].append(
                {
                    "clip": clip,
                    "frame_idx": r.frame_idx,
                    "outcome": r.outcome.value,
                    "reason": r.reason.value if r.reason else None,
                }
            )

        line_results: dict[str, list] = {}
        line_diags: dict[str, list] = {}
        for vid, spec in VARIANTS.items():
            results, d = run_line_method(dets, fps, spec)
            line_results[vid] = results
            line_diags[vid] = d
            for r, di in zip(results, d):
                diag_map[vid][id(r)] = di
                diags[vid].append({"clip": clip, **di})
            rep = ev.Replay(frames=sv.frames, results=sorted(results, key=lambda r: r.frame_idx))
            scores[vid].append(ev.score_clip(clip, labels[clip], rep, 0.6, to_frames(0.2, fps), fps))

        for hid, src, add_new in (("H1", "L3", False), ("H2", "L3", True), ("H3", "L4", True)):
            dbyid: dict = {}
            raw = apply_hybrid(sv_results, line_results[src], line_diags[src], fps, add_new, dbyid)
            changed = sum(1 for i in range(len(sv_results)) if raw[i] is not sv_results[i])
            added = len(raw) - len(sv_results)
            hybrid_counts[hid]["changed"] += changed
            hybrid_counts[hid]["added"] += added
            rep = ev.Replay(frames=sv.frames, results=sorted(raw, key=lambda r: r.frame_idx))
            scores[hid].append(ev.score_clip(clip, labels[clip], rep, 0.6, to_frames(0.2, fps), fps))
            for r in raw:
                di = dbyid.get(id(r))
                if di is not None:
                    diag_map[hid][id(r)] = di
                    diags[hid].append({"clip": clip, **di})
                else:
                    diags[hid].append(
                        {
                            "clip": clip,
                            "note": "unchanged",
                            "frame_idx": r.frame_idx,
                            "outcome": r.outcome.value,
                            "reason": r.reason.value if r.reason else None,
                        }
                    )

    summary_rows = build_summary(scores, meta)
    gained, lost = collect_gains_losses(scores)
    gap_arc = count_gap_arc(diags)
    false_rows = collect_false_makes(scores, diag_map)

    # Gate A block per variant (captured stdout).
    gate_blocks: dict[str, str] = {}
    for vid in VARIANT_IDS:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ev.print_gate_report(scores[vid], meta)
        gate_blocks[vid] = buf.getvalue()

    summary_md = _summary_markdown(summary_rows)

    # stdout summary table.
    print(summary_md)
    print()

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        sections = [
            "# Line-through-the-rim side by side (PLAN 2)\n",
            "## Summary\n",
            summary_md,
            "\n_In-scope columns are empty: labels.json has no camera_class / ball_count fields, so every clip reports as unclassified._\n",
            "## Gate A per variant\n",
            "_Note: the \"Lost makes by exit reason\" lines in the L0-L4 Gate A blocks are placeholders (all L0-L4 misses carry MISS_BELOW_WITHOUT_INNER and all makes MAKE_CONFIRMED). The real decision-path breakdown is in the section below and in the JSON._\n",
        ]
        for vid in VARIANT_IDS:
            sections.append(f"### {vid}\n```\n{gate_blocks[vid].strip()}\n```\n")
        sections.append("## False makes and spurious makes\n")
        sections.append(_false_make_markdown(false_rows))
        sections.append("\n## Makes gained over SV\n")
        for vid in VARIANT_IDS:
            if vid == "SV":
                continue
            g = gained[vid]
            sections.append(f"### {vid} ({len(g)})\n")
            if g:
                for row in g:
                    sections.append(
                        f"- {row['clip']} card {row['card']} [{row['label_start']}-{row['label_end']}]: SV {row['sv_reason']}\n"
                    )
            else:
                sections.append("_None._\n")
        sections.append("\n## Makes lost compared with SV\n")
        for vid in VARIANT_IDS:
            if vid == "SV":
                continue
            l = lost[vid]
            sections.append(f"### {vid} ({len(l)})\n")
            if l:
                for row in l:
                    sections.append(f"- {row['clip']} card {row['card']} [{row['label_start']}-{row['label_end']}]\n")
            else:
                sections.append("_None._\n")
        sections.append("\n## gap_too_long and arc_fallback counts (L2-L4)\n")
        sections.append("| variant | gap_too_long | arc_fallback |\n| --- | --- | --- |")
        for vid in ("L2", "L3", "L4"):
            sections.append(f"| {vid} | {gap_arc[vid]['gap_too_long']} | {gap_arc[vid]['arc_fallback']} |")
        sections.append("\n## Hybrid change/add counts\n")
        sections.append("| hybrid | changed | added |\n| --- | --- | --- |")
        for hid in ("H1", "H2", "H3"):
            sections.append(f"| {hid} | {hybrid_counts[hid]['changed']} | {hybrid_counts[hid]['added']} |")
        out.write_text("\n".join(sections) + "\n")

    if args.json:
        Path(args.json).write_text(
            json.dumps({"variants": diags, "hybrid_counts": hybrid_counts}, indent=1)
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
