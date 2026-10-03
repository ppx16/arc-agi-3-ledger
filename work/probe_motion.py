"""Measure, for each of the 25 public games, whether the frame tells us the MECHANICS.

WHY THIS PROBE EXISTS
    F26 measured that blind exploration cannot solve these games, and F30 measured that no
    state-key fix rescues it (the whole board is redrawn every step, so raw hashing always
    yields a new state and the "novelty" walk degenerates into a random walk). F31 concluded
    the only un-falsified lever is an ACTIVE, PROCEDURE-SHAPED hypothesis. Before building
    one, this asks the cheapest question that can kill it:

        from a fresh RESET, does a single action move a SMALL, COMPACT, LOCALISED region
        of the frame -- i.e. is there an avatar whose displacement we can measure?

    If yes for most games, an empirical avatar/obstacle model is buildable from pixels with
    no game-specific constants (which is exactly what F32's hand-patterned LS20 planner was
    NOT, and why it regressed on the hidden set). If no, that lever is dead too and the
    record should say so.

WHAT IS MEASURED, AND THE TRAP IT AVOIDS
    The naive "did the frame change" is useless here: F30 measured that ls20 redraws
    4096 of 4096 cells on EVERY step. So "change" is not the signal. The signal is whether
    the change is CONCENTRATED (a compact blob moved) or DIFFUSE (the whole board redrew).

        changed_cells / 4096       -- how much of the board moved
        bbox area of the change    -- how concentrated the change is
        concentration = changed / bbox_area
        the changed region's own two-frame difference restricted to its bbox

    A moving sprite gives a small changed fraction (<10 %) with a high concentration.
    A global redraw gives changed ~1.0 and concentration ~1.0 as well (the bbox is the whole
    board), so the two are separated by the FRACTION, not by the concentration -- report both
    and read them together.

ALSO MEASURED, because it decides whether a planner is even reachable
    * how many connected non-background components exist, and their colours/sizes
      (a goal is usually a uniquely-coloured object that does NOT move)
    * which components MOVE when each action is pressed -- the avatar
    * whether an action is a NO-OP (identical frame) -- those can be deleted from the
      action vocabulary for free, which is pure budget savings under RHAE

Usage:
    .venv\\Scripts\\python.exe probe_motion.py                 # all 25 games
    .venv\\Scripts\\python.exe probe_motion.py --games ls20,vc33
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "starter"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor" / "ARC-AGI-3-Agents"))
import os as _os                                        # noqa: E402
_os.environ.setdefault("ENVIRONMENTS_DIR", str(ROOT / "environment_files"))
_os.environ.setdefault("RECORDINGS_DIR", str(ROOT / "recordings"))
_os.environ["OPERATION_MODE"] = "offline"

import numpy as np                                      # noqa: E402
import arc_agi                                          # noqa: E402
from arc_agi import OperationMode                       # noqa: E402
from arcengine import GameAction, GameState             # noqa: E402

WORK = Path(__file__).resolve().parents[1] / "work"


def grid_of(obs):
    if obs is None or getattr(obs, "frame", None) is None:
        return None
    a = np.asarray(obs.frame)
    return (a[-1] if a.ndim == 3 else a).astype(np.int16)


def components(g, max_area=2000):
    """4-connected same-colour components of non-background cells -> list of dicts."""
    vals, counts = np.unique(g, return_counts=True)
    bg = int(vals[int(np.argmax(counts))])
    h, w = g.shape
    seen = np.zeros((h, w), dtype=bool)
    out = []
    for r in range(h):
        for c in range(w):
            if seen[r, c] or g[r, c] == bg:
                continue
            colour = int(g[r, c])
            q = deque([(r, c)])
            seen[r, c] = True
            cells = []
            while q:
                y, x = q.popleft()
                cells.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and not seen[ny, nx] and g[ny, nx] == colour:
                        seen[ny, nx] = True
                        q.append((ny, nx))
            if 1 <= len(cells) <= max_area:
                ys = [p[0] for p in cells]
                xs = [p[1] for p in cells]
                out.append({"area": len(cells), "colour": colour,
                            "y0": min(ys), "y1": max(ys), "x0": min(xs), "x1": max(xs),
                            "cy": sum(ys) / len(ys), "cx": sum(xs) / len(xs)})
    return bg, out


def spec_of(aid, pts, i):
    if aid == 6:
        return GameAction.ACTION6, pts[i]
    return GameAction.from_id(aid), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", default="")
    ap.add_argument("--max-clicks", type=int, default=8)
    a = ap.parse_args()
    logging.disable(logging.CRITICAL)

    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE,
                         environments_dir=str(ROOT / "environment_files"),
                         recordings_dir=str(WORK / "recordings"))
    infos = {e.game_id.split("-")[0]: e for e in arc.get_environments()}
    ids = sorted(infos)
    if a.games:
        want = {x.strip() for x in a.games.split(",")}
        ids = [g for g in ids if g in want]

    report = {}
    for gid in ids:
        env = arc.make(gid)
        obs = env.reset()
        g0 = grid_of(obs)
        bg, comps = components(g0)
        acts = [int(v) for v in (obs.available_actions or [])]
        row = {"available_actions": acts, "bg": bg, "n_components": len(comps),
               "component_sizes": sorted([c["area"] for c in comps], reverse=True)[:8],
               "actions": []}

        # click candidates: centroids of the largest components, deterministic order
        pts = [(int(round(c["cx"])), int(round(c["cy"]))) for c in
               sorted(comps, key=lambda c: (-c["area"], c["colour"], c["cy"], c["cx"]))]
        seen, cpts = set(), []
        for p in pts:
            if p not in seen:
                seen.add(p)
                cpts.append(p)
        cpts = cpts[:a.max_clicks]

        for ai, aid in enumerate(acts):
            if aid == 6:
                cand = [(ai, "6@%d,%d" % p, p) for p in cpts]
            else:
                cand = [(ai, str(aid), None)]
            for (_, label, pt) in cand:
                env.reset()
                act = GameAction.ACTION6 if aid == 6 else GameAction.from_id(aid)
                # ⚠️ env.step() takes `data=` explicitly (local_wrapper.py:211 ->
                # ActionInput(id=action, data=data or {})). `set_data` alone is ONLY correct
                # through the framework's Agent.do_action_request, which forwards
                # action.action_data as data=. Calling env.step() directly with set_data and no
                # `data=` silently sends {} -- so EVERY candidate click became the same click.
                # This is why tools/solve_levels.py's click exploration must not be trusted.
                if aid == 6:
                    o = env.step(act, data={"x": int(pt[0]), "y": int(pt[1])})
                else:
                    o = env.step(act)
                g1 = grid_of(o)
                if g1 is None:
                    row["actions"].append({"action": label, "step_returned_none": True})
                    continue
                if g1.shape != g0.shape:
                    row["actions"].append({"action": label, "shape_change": list(g1.shape)})
                    continue
                d = (g0 != g1)
                ch = int(d.sum())
                if ch == 0:
                    row["actions"].append({"action": label, "changed": 0, "noop": True})
                    continue
                ys, xs = np.nonzero(d)
                bbox = (int(ys.max() - ys.min() + 1)) * (int(xs.max() - xs.min() + 1))
                row["actions"].append({
                    "action": label, "changed": ch,
                    "frac": round(ch / d.size, 4),
                    "bbox": [int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max())],
                    "bbox_area": bbox,
                    "concentration": round(ch / bbox, 3),
                    "state": str(o.state),
                    "levels": int(o.levels_completed or 0),
                })
            # aggregate per action id
        nonop = [r["action"] for r in row["actions"] if r.get("noop")]
        compact = [r for r in row["actions"] if r.get("frac") is not None and r["frac"] < 0.20]
        row["summary"] = {
            "n_candidates": len(row["actions"]),
            "n_noop": len(nonop),
            "n_compact_change": len(compact),
            "min_frac": min([r["frac"] for r in row["actions"] if "frac" in r], default=None),
        }
        report[gid] = row
        s = row["summary"]
        print("%-5s acts=%-16s comps=%-3d cand=%-3d noop=%-3d compact(<20%%)=%-3d minfrac=%s"
              % (gid, ",".join(str(x) for x in acts), row["n_components"], s["n_candidates"],
                 s["n_noop"], s["n_compact_change"], s["min_frac"]), flush=True)

    out = WORK / "probe_motion.json"
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print("wrote %s" % out)


if __name__ == "__main__":
    main()
