"""Experiment (not wired into the pipeline): let an armed shot adopt a new
tracker identity when the ball is re-acquired at the hoop after a gap.

Motivation (measured by experiments/shot_diagnostics.py): on video_test_5 f2597
the armed ball (track 9) is lost at the rim, the tracker weak-continues onto a
stationary false positive under the hoop, then the real ball reappears
confidently inside the hoop box as track 10. The state machine discards
other-identity observations (iter 6 guard against following a shooter's head),
so the shot ends MISS_OCCLUSION_GAP although the ball visibly drops through.

Rule tested: while ARMED, an observation with a different track_id is adopted
only if (a) the armed ball's last *confirmed* point was near the hoop
(|x - cx| <= outer_width, y >= outer_top - 2h; weak frames don't count, since
measured weak continuation can latch onto a stationary false positive), and
(b) the new observation is itself confirmed and inside the hoop region
(|x - cx| <= outer_width, outer_top - h/2 <= y <= outer_bottom + h).

Usage: python experiments/track_adopt_experiment.py   (replays caches only)
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import evaluate as ev  # noqa: E402
from shotvision.config.settings import load_config  # noqa: E402
from shotvision.shot_logic.state_machine import ShotStateMachine  # noqa: E402


class AdoptingStateMachine(ShotStateMachine):
    adoptions: list[tuple[int, int, int]] = []

    def _update_armed(self, obs, frame_idx):
        if (
            obs is not None
            and not obs.weak
            and obs.track_id is not None
            and self._armed_track_id is not None
            and obs.track_id != self._armed_track_id
            and self._recent
        ):
            rim = self.rim
            h = rim.outer_bottom - rim.outer_top
            last = self._recent[-1]
            last_near_hoop = (abs(last.x - rim.center_x) <= rim.outer_width
                              and last.y >= rim.outer_top - 2 * h)
            if (last_near_hoop and abs(obs.x - rim.center_x) <= rim.outer_width
                    and rim.outer_top - h / 2 <= obs.y <= rim.outer_bottom + h):
                AdoptingStateMachine.adoptions.append((frame_idx, self._armed_track_id, obs.track_id))
                self._armed_track_id = obs.track_id
        return super()._update_armed(obs, frame_idx)


def run(machine_cls) -> tuple[int, int, int, int, list[str]]:
    ev.ShotStateMachine = machine_cls
    config = load_config()
    correct = shots = false_makes = spurious = 0
    bad = []
    for clip, labels in ev.load_labels().items():
        fps = ev.clip_fps(ev.CLIPS_DIR / clip)
        rep = ev.replay(ev.load_detections(ev.CLIPS_DIR / clip, config), config, fps=fps)
        score = ev.score_clip(clip, labels, rep, 0.6, 6, fps)
        shots += len(score.checks)
        false_makes += score.false_makes
        spurious += len(score.spurious)
        for c in score.checks:
            ok = c.result is not None and c.result.outcome.value == c.label["outcome"]
            correct += ok
            if not ok:
                got = "unresolved" if c.result is None else f"{c.result.outcome.value} ({c.result.reason.value})"
                bad.append(f"{clip} {c.label['outcome']} [{c.label['start']}] -> {got}")
    return correct, shots, false_makes, spurious, bad


def main() -> int:
    for name, cls in (("baseline", ShotStateMachine), ("adopt-at-hoop", AdoptingStateMachine)):
        AdoptingStateMachine.adoptions = []
        correct, shots, fm, sp, bad = run(cls)
        print(f"{name}: {correct}/{shots} correct, false makes {fm}, spurious {sp}")
        for b in bad:
            print(f"   BAD {b}")
        if cls is AdoptingStateMachine:
            print(f"   adoptions (frame, old id, new id): {AdoptingStateMachine.adoptions}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
