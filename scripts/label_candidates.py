"""Turn any clip into a labeling page with one command, then merge the labels.

  python scripts/label_candidates.py CLIP                # build the page
  python scripts/label_candidates.py CLIP --cache-only   # never run detection
  python scripts/label_candidates.py merge EXPORT.json   # into sample_clips/labels.json

CLIP is a path, or a name relative to sample_clips/. Building the page:

1. Gets raw per-frame detections. It uses the scripts/evaluate.py cache; on a
   cache miss it runs the detector, which loads models/basketball_best.pt.
2. Replays them through the real tracker, rim tracker and state machine.
3. Finds candidate shot windows: every stretch where a ball (followed, or
   any confident raw detection) moves near the hoop, plus every shot the
   pipeline itself resolved. The finder is deliberately over-inclusive, so
   that makes the pipeline never armed on still get a card; mark the rest
   NOT A SHOT.
4. Writes sample_clips/_label/<clip stem>/: one contact sheet per candidate
   of at most 3 s (crops around the hoop, one frame per 0.1 s, with the frame number, the
   tracked ball in orange and the hoop box in green), a full-frame context
   thumbnail, candidates.json and index.html.

Open index.html in a browser. For each card, choose MAKE / MISS / NOT A SHOT,
pick a miss type, and adjust the start/end frames if needed. Then press
"Export labels", which downloads labels_<clip stem>.json. Progress is kept in
the browser's localStorage. The pipeline's own call is hidden by default so
it doesn't anchor the labeler.

Export / merge format (one clip per file; frames are 0-based, inclusive):
  {"clip": "<file name in sample_clips/>", "fps": 30.0,
   "labeled_by": "...", "split": "dev", "source": {...optional provenance...},
   "shots": [{"start": 258, "end": 292, "outcome": "MAKE"|"MISS"|"NOT_A_SHOT"|"IGNORE"|"?",
              "miss_type": "front_rim"|"back_rim"|"in_and_out"|"side_rim_out"|
                           "airball"|"other"|null,
              "note": "...", "card": 3}]}
`merge` keeps MAKE, MISS and IGNORE (a shot that can't be called from the
frames: evaluate.py neither scores it nor counts it as spurious), drops
NOT_A_SHOT, and refuses "?" unless
--allow-unlabeled is given (evaluate.py skips a clip that has any "?"). It
refuses to overwrite an existing clip entry unless --force is given.
For a MAKE, start/end should span the final approach to the rim through the
ball leaving the bottom of the net. For a MISS, they should span the approach
through the ball leaving the rim area.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

import cv2

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import evaluate as ev  # noqa: E402
from shotvision.config.settings import load_config  # noqa: E402

OUT_ROOT = ev.CLIPS_DIR / "_label"
MISS_TYPES = ["front_rim", "back_rim", "in_and_out", "side_rim_out", "airball", "other"]

# Candidate finder, in hoop-box widths (x) and heights (y) from the hoop box.
NEAR_RX = 2.5            # |x - hoop centre| <= 2.5 hoop widths
NEAR_RY = (-6.0, 2.5)    # from 6 box heights above the box top to 2.5 below it
JOIN_GAP_S = 0.6         # near-hoop detections closer than this are one episode
PAD_S = 0.35             # padding added to both ends of a window
MIN_SPAN_WIDTHS = 0.8    # the ball must move at least this far (hoop widths)
MAX_WINDOW_S = 4.0       # longer episodes are split at their biggest gap
MAX_CARD_S = 3.0         # longer windows (after merging) become several cards
SAMPLE_STEP_S = 0.1      # contact sheets show one frame per 0.1 s


def _rim_units(x, y, rim):
    h = rim.outer_bottom - rim.outer_top
    return (x - rim.center_x) / rim.outer_width, (y - rim.outer_top) / h


def near_hoop_points(dets, rep, conf):
    """(frame, x, y) of every followed or confident raw ball near the hoop."""
    pts = []
    for f, st in enumerate(rep.frames):
        rim = st.rim
        if rim is None:
            continue
        cands = []
        if st.obs is not None:
            cands.append((st.obs.x, st.obs.y))
        cands += [d.center for d in dets[f] if d.class_name == "ball" and d.conf >= conf]
        for x, y in cands:
            rx, ry = _rim_units(x, y, rim)
            if abs(rx) <= NEAR_RX and NEAR_RY[0] <= ry <= NEAR_RY[1]:
                pts.append((f, x, y, rim.outer_width))
                break
    return pts


def _split_long(ep, fps):
    if (ep[-1][0] - ep[0][0]) / fps <= MAX_WINDOW_S or len(ep) < 4:
        return [ep]
    gaps = [(ep[i + 1][0] - ep[i][0], i) for i in range(len(ep) - 1)]
    _, i = max(gaps)
    return _split_long(ep[: i + 1], fps) + _split_long(ep[i + 1:], fps)


def find_candidates(dets, rep, fps, conf):
    pts = near_hoop_points(dets, rep, conf)
    join = max(1, round(JOIN_GAP_S * fps))
    episodes, cur = [], []
    for p in pts:
        if cur and p[0] - cur[-1][0] > join:
            episodes.append(cur)
            cur = []
        cur.append(p)
    if cur:
        episodes.append(cur)
    episodes = [e for ep in episodes for e in _split_long(ep, fps)]

    pad = round(PAD_S * fps)
    n = len(rep.frames)
    windows = []
    for ep in episodes:
        xs, ys = [p[1] for p in ep], [p[2] for p in ep]
        width = sum(p[3] for p in ep) / len(ep)
        if len(ep) < 2 or max(max(xs) - min(xs), max(ys) - min(ys)) < MIN_SPAN_WIDTHS * width:
            continue  # a ball sitting still near the hoop, not a shot
        windows.append([max(0, ep[0][0] - pad), min(n - 1, ep[-1][0] + pad)])

    # Every shot the pipeline resolved gets a window too.
    for r in rep.results:
        lo = max(0, r.frame_idx - r.armed_frames - pad)
        hi = min(n - 1, r.frame_idx + pad)
        windows.append([lo, hi])

    windows.sort()
    merged = []
    for w in windows:
        if merged and w[0] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], w[1])
        else:
            merged.append(list(w))

    # A window that is still long (e.g. a false positive near the hoop kept it
    # open) is cut into consecutive cards so each card is sampled densely.
    card_len = round(MAX_CARD_S * fps)
    chunks = []
    for lo, hi in merged:
        while hi - lo + 1 > card_len:
            chunks.append([lo, lo + card_len - 1])
            lo += card_len - pad  # overlap by the padding so no shot is cut in two
        chunks.append([lo, hi])
    merged = chunks

    out = []
    for i, (lo, hi) in enumerate(merged):
        res = [r for r in rep.results if lo <= r.frame_idx <= hi]
        out.append({
            "card": i, "start": lo, "end": hi,
            "pipeline": [{"frame": r.frame_idx, "outcome": r.outcome.value,
                          "reason": r.reason.value if r.reason else None} for r in res],
        })
    return out


def _read_frames(path: Path, wanted: set[int]) -> dict[int, "cv2.Mat"]:
    frames, cap, f = {}, cv2.VideoCapture(str(path)), 0
    last = max(wanted) if wanted else -1
    while f <= last:
        ok, img = cap.read()
        if not ok:
            break
        if f in wanted:
            frames[f] = img
        f += 1
    cap.release()
    return frames


def _crop_box(rim, shape):
    h_img, w_img = shape[:2]
    w = rim.outer_width
    x0, x1 = rim.center_x - 3.5 * w, rim.center_x + 3.5 * w
    y0, y1 = rim.outer_top - 4.0 * w, rim.outer_top + 2.5 * w
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(w_img, int(x1)), min(h_img, int(y1))
    return x0, y0, x1, y1


def build_sheets(path, rep, cands, out_dir, fps, cell_w=240, cols=6):
    sample = {}
    step = max(1, round(SAMPLE_STEP_S * fps))
    for c in cands:
        sample[c["card"]] = list(range(c["start"], c["end"] + 1))[::step]
    wanted = {f for fs in sample.values() for f in fs} | {c["start"] for c in cands}
    imgs = _read_frames(path, wanted)
    import numpy as np

    for c in cands:
        cells = []
        ref_rim = next((rep.frames[f].rim for f in sample[c["card"]] if rep.frames[f].rim is not None), None)
        for f in sample[c["card"]]:
            img = imgs.get(f)
            if img is None or ref_rim is None:
                continue
            img = img.copy()
            rim = rep.frames[f].rim or ref_rim
            cv2.rectangle(img, (int(rim.outer_left), int(rim.outer_top)),
                          (int(rim.outer_right), int(rim.outer_bottom)), (0, 200, 0), 1)
            obs = rep.frames[f].obs
            if obs is not None:
                color = (0, 140, 255) if not obs.weak else (0, 200, 255)
                cv2.rectangle(img, (int(obs.left), int(obs.top)), (int(obs.right), int(obs.bottom)),
                              color, 2 if not obs.weak else 1)
            x0, y0, x1, y1 = _crop_box(ref_rim, img.shape)
            crop = img[y0:y1, x0:x1]
            scale = cell_w / max(1, crop.shape[1])
            crop = cv2.resize(crop, (cell_w, max(1, int(crop.shape[0] * scale))))
            cv2.putText(crop, f"f{f}", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
            cv2.putText(crop, f"f{f}", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cells.append(crop)
        if not cells:
            continue
        ch = max(cell.shape[0] for cell in cells)
        cells = [cv2.copyMakeBorder(cell, 0, ch - cell.shape[0], 0, 0, cv2.BORDER_CONSTANT) for cell in cells]
        while len(cells) % cols:
            cells.append(np.zeros_like(cells[0]))
        rows = [np.hstack(cells[i:i + cols]) for i in range(0, len(cells), cols)]
        cv2.imwrite(str(out_dir / f"card_{c['card']:03d}.jpg"), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])

        ctx = imgs.get(c["start"])
        if ctx is not None:
            ctx = ctx.copy()
            if ref_rim is not None:
                x0, y0, x1, y1 = _crop_box(ref_rim, ctx.shape)
                cv2.rectangle(ctx, (x0, y0), (x1, y1), (0, 200, 0), 2)
            s = 480 / ctx.shape[1]
            ctx = cv2.resize(ctx, (480, int(ctx.shape[0] * s)))
            cv2.imwrite(str(out_dir / f"ctx_{c['card']:03d}.jpg"), ctx, [cv2.IMWRITE_JPEG_QUALITY, 80])


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Label: __CLIP__</title>
<style>
:root{--bg:#fafaf8;--fg:#1b1b1b;--muted:#666;--card:#fff;--line:#ddd;--make:#1f7a3a;--miss:#b3261e;--na:#555}
@media (prefers-color-scheme:dark){:root{--bg:#141414;--fg:#eee;--muted:#aaa;--card:#1e1e1e;--line:#333;--make:#4cc070;--miss:#ff6b5f;--na:#999}}
body{background:var(--bg);color:var(--fg);font:14px/1.4 system-ui,sans-serif;margin:0;padding:16px}
header{position:sticky;top:0;background:var(--bg);padding:8px 0;border-bottom:1px solid var(--line);z-index:2}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;margin:16px 0;padding:12px}
.card.done{border-left:6px solid var(--make)}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:6px 0}
img{max-width:100%;height:auto;display:block}
button{padding:6px 12px;border-radius:6px;border:1px solid var(--line);background:var(--card);color:var(--fg);cursor:pointer}
button.on[data-o=MAKE]{background:var(--make);color:#fff}
button.on[data-o=MISS]{background:var(--miss);color:#fff}
button.on[data-o=NOT_A_SHOT]{background:var(--na);color:#fff}
input[type=number]{width:80px}
.muted{color:var(--muted)}
details{margin-top:6px}
</style></head><body>
<header><b>__CLIP__</b> <span class="muted">(__FPS__ fps, __N__ candidates)</span>
<span id="progress" class="muted"></span>
<button id="export">Export labels</button></header>
<p class="muted">Mark each card. Hoop box in green, tracked ball in orange (thin = weak). Change start/end if the window cuts the shot off. A card can hold two shots: mark the main one and note the other.</p>
<div id="cards"></div>
<script>
const DATA = __DATA__;
const KEY = "shotvision-labels:" + DATA.clip;
let saved = {};
try { saved = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
function save(){ try { localStorage.setItem(KEY, JSON.stringify(saved)); } catch (e) {} progress(); }
function progress(){
  const n = DATA.cands.filter(c => (saved[c.card]||{}).outcome).length;
  document.getElementById("progress").textContent = ` ${n}/${DATA.cands.length} labeled`;
}
const root = document.getElementById("cards");
for (const c of DATA.cands) {
  const s = saved[c.card] = Object.assign({start:c.start, end:c.end, outcome:null, miss_type:null, note:""}, saved[c.card]||{});
  const el = document.createElement("div"); el.className = "card"; el.id = "card"+c.card;
  const pid = String(c.card).padStart(3,"0");
  el.innerHTML = `<div class="row"><b>Card ${c.card}</b><span class="muted">frames ${c.start}-${c.end}</span></div>
    <img src="card_${pid}.jpg" loading="lazy" alt="hoop crops for card ${c.card}">
    <details><summary class="muted">full frame</summary><img src="ctx_${pid}.jpg" loading="lazy" alt="context"></details>
    <div class="row">
      <button data-o="MAKE">MAKE</button><button data-o="MISS">MISS</button><button data-o="NOT_A_SHOT">NOT A SHOT</button><button data-o="IGNORE">CAN'T TELL</button>
      <select class="mt"><option value="">miss type…</option>${DATA.missTypes.map(t=>`<option>${t}</option>`).join("")}</select>
      start <input type="number" class="st"> end <input type="number" class="en">
    </div>
    <div class="row"><input class="nt" placeholder="note" style="flex:1;min-width:200px"></div>
    <details><summary class="muted">pipeline's call (hidden so it doesn't bias you)</summary><pre>${JSON.stringify(c.pipeline)}</pre></details>`;
  root.appendChild(el);
  const btns = el.querySelectorAll("button[data-o]");
  const paint = () => { btns.forEach(b => b.classList.toggle("on", b.dataset.o === s.outcome)); el.classList.toggle("done", !!s.outcome); };
  btns.forEach(b => b.onclick = () => { s.outcome = b.dataset.o; paint(); save(); });
  const mt = el.querySelector(".mt"); mt.value = s.miss_type || ""; mt.onchange = () => { s.miss_type = mt.value || null; save(); };
  const st = el.querySelector(".st"); st.value = s.start; st.onchange = () => { s.start = +st.value; save(); };
  const en = el.querySelector(".en"); en.value = s.end; en.onchange = () => { s.end = +en.value; save(); };
  const nt = el.querySelector(".nt"); nt.value = s.note; nt.onchange = () => { s.note = nt.value; save(); };
  paint();
}
progress();
document.getElementById("export").onclick = () => {
  const shots = DATA.cands.map(c => Object.assign({card:c.card}, saved[c.card]))
    .filter(s => s.outcome).map(s => ({start:s.start, end:s.end, outcome:s.outcome,
      miss_type: s.outcome === "MISS" ? s.miss_type : null, note:s.note, card:s.card}));
  const out = {clip: DATA.clip, fps: DATA.fps, labeled_by: "labeling page", split: "dev", shots};
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(out, null, 1)], {type:"application/json"}));
  a.download = "labels_" + DATA.stem + ".json"; a.click();
};
</script></body></html>
"""


def build(args) -> int:
    path = Path(args.clip)
    if not path.exists():
        path = ev.CLIPS_DIR / args.clip
    if not path.exists():
        print(f"no such clip: {args.clip}")
        return 1
    config = load_config()
    if args.cache_only and not ev._cache_path(path, config).exists():
        print(f"[cache-only] no detection cache for {path.name}; not running the detector")
        return 2
    rel = path.resolve().relative_to(ev.CLIPS_DIR.resolve()) if path.resolve().is_relative_to(ev.CLIPS_DIR.resolve()) else path
    dets = ev.load_detections(path, config)
    fps = ev.clip_fps(path)
    rep = ev.replay(dets, config, fps=fps)
    cands = find_candidates(dets, rep, fps, config.model.conf)
    out_dir = OUT_ROOT / path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.jpg"):
        old.unlink()
    build_sheets(path, rep, cands, out_dir, fps)
    (out_dir / "candidates.json").write_text(json.dumps(
        {"clip": str(rel), "fps": fps, "frames": len(rep.frames), "cands": cands}, indent=1))
    data = {"clip": str(rel), "stem": path.stem, "fps": round(fps, 3), "cands": cands, "missTypes": MISS_TYPES}
    page = (PAGE.replace("__DATA__", json.dumps(data))
            .replace("__CLIP__", html.escape(str(rel)))
            .replace("__FPS__", f"{fps:.2f}")
            .replace("__N__", str(len(cands))))
    (out_dir / "index.html").write_text(page)
    print(f"{len(cands)} candidate windows -> {out_dir / 'index.html'}")
    return 0


def merge(args) -> int:
    data = json.loads(Path(args.export).read_text())
    clip = data["clip"]
    shots = []
    for s in data["shots"]:
        if s["outcome"] == "NOT_A_SHOT":
            continue
        if s["outcome"] not in ("MAKE", "MISS", "IGNORE") and not args.allow_unlabeled:
            print(f"card {s.get('card')} is '{s['outcome']}': label it, or pass --allow-unlabeled")
            return 1
        if s["outcome"] == "MISS" and s.get("miss_type") not in MISS_TYPES:
            print(f"warning: card {s.get('card')} is a MISS without a valid miss_type")
        shot = {"start": int(s["start"]), "end": int(s["end"]), "outcome": s["outcome"]}
        for k in ("miss_type", "note", "card"):
            if s.get(k) not in (None, ""):
                shot[k] = s[k]
        shots.append(shot)
    shots.sort(key=lambda s: s["start"])
    labels = json.loads(ev.LABELS_PATH.read_text())
    if clip in labels["clips"] and not args.force:
        print(f"{clip} already in labels.json; pass --force to replace it")
        return 1
    entry = {"verified": data.get("labeled_by", "labeling page"), "split": data.get("split", "dev")}
    if data.get("source"):
        entry["source"] = data["source"]
    entry["shots"] = shots
    labels["clips"][clip] = entry
    ev.LABELS_PATH.write_text(json.dumps(labels, indent=2) + "\n")
    n_make = sum(s["outcome"] == "MAKE" for s in shots)
    print(f"merged {clip}: {n_make} makes, {len(shots) - n_make} misses")
    return 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "merge":
        p = argparse.ArgumentParser(prog="label_candidates.py merge")
        p.add_argument("export")
        p.add_argument("--force", action="store_true")
        p.add_argument("--allow-unlabeled", action="store_true")
        return merge(p.parse_args(sys.argv[2:]))
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("clip")
    p.add_argument("--cache-only", action="store_true")
    return build(p.parse_args())


if __name__ == "__main__":
    sys.exit(main())
