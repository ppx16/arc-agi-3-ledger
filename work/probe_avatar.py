"""Is an avatar measurable from pixels, and can it be TRACKED over a run?

WHY THIS PROBE EXISTS (it decides whether the next agent is worth building)
    F34.4 tested the "ordered protocol" lever and it did NOT confirm: a fixed orbit is no better
    than the random walk it replaced. F34.3's mechanics map is what is left -- 23 of 25 games have
    at least one action whose frame change is LOCALISED, the cleanest being ls20 action 2, which
    changes exactly 2 cells (a one-cell sprite moving).

    If that generalises, a genuinely different agent becomes buildable, and it does NOT need to
    know the goal -- which is what killed F32's planner (it pattern-matched LS20 and mis-fired on
    hidden games):

        calibrate  -> find the action that moves a small blob
        track      -> follow that blob by frame differencing, every step
        map        -> cells the blob never enters are walls
        COVER      -> walk the reachable region systematically

    A level-1 that is "get the avatar to the goal" is then solved by COVERAGE, with no goal
    detector at all. Coverage is also far more action-efficient than a random walk at *reaching*
    every cell, and RHAE charges every action.

WHAT IS MEASURED HERE, per game
    * for each legal direction action, the changed-cell count from a fresh reset
    * whether a single action gives a small (<=8 cell) change -- the "avatar action"
    * pressing that action 8 times: the changed-cell CENTROID each step, and whether it marches
      (a tracked sprite) or stalls/repeats (not a moving sprite)
    * how much of the 64x64 board is ever touched, i.e. whether a covering walk is affordable

Usage:
    .venv\\Scripts\\python.exe probe_avatar.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "starter"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor" / "ARC-AGI-3-Agents"))
import os as _os                                        # noqa: E402
_os.environ.setdefault("ENVIRONMENTS_DIR", str(ROOT / "environment_files"))
_os.environ.setdefault("RECORDINGS_DIR", str(ROOT / "recordings"))
_os.environ["OPERATION_MODE"] = "offline"

import numpy as np                                      # noqa: E402
import logging                                          # noqa: E402
import arc_agi                                          # noqa: E402
from arc_agi import OperationMode                       # noqa: E402
from arcengine import GameAction                        # noqa: E402

WORK = Path(__file__).resolve().parents[1] / "work"


def grid(obs):
    if obs is None or getattr(obs, "frame", None) is None:
        return None
    a = np.asarray(obs.frame)
    return (a[-1] if a.ndim == 3 else a).astype(np.int16)


def main():
    logging.disable(logging.CRITICAL)
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE,
                         environments_dir=str(ROOT / "environment_files"),
                         recordings_dir=str(WORK / "recordings"))
    ids = sorted(e.game_id.split("-")[0] for e in arc.get_environments())
    print("%-6s %-14s %-22s %s" % ("game", "actions", "best(smallest) diff", "8 presses of that action"))
    for gid in ids:
        env = arc.make(gid)
        obs = env.reset()
        g0 = grid(obs)
        acts = [int(v) for v in (obs.available_actions or [])]
        dirs = [a for a in acts if a != 6]
        if not dirs:
            print("%-6s %-14s %-22s %s" % (gid, ",".join(map(str, acts)), "(click-only)", "-"))
            continue
        sizes = {}
        for a in dirs:
            env.reset()
            o = env.step(GameAction.from_id(a))
            g1 = grid(o)
            sizes[a] = int((g0 != g1).sum()) if g1 is not None else -1
        best = min(sizes, key=lambda k: sizes[k])
        if sizes[best] > 8:
            print("%-6s %-14s %-22s %s" % (gid, ",".join(map(str, acts)),
                                           "%d:%d" % (best, sizes[best]), "no localised action"))
            continue
        # press `best` eight times from a fresh reset and watch the changed region's centroid
        env.reset()
        prev = g0
        cents, touched = [], set()
        for _ in range(8):
            o = env.step(GameAction.from_id(best))
            g1 = grid(o)
            if g1 is None:
                break
            d = (prev != g1)
            ys, xs = np.nonzero(d)
            if len(ys) == 0:
                cents.append(None)
            else:
                cents.append((int(round(ys.mean())), int(round(xs.mean())), int(d.sum())))
                for y, x in zip(ys.tolist(), xs.tolist()):
                    touched.add((y, x))
            prev = g1
        track = " ".join("-" if c is None else "%d,%d" % (c[0], c[1]) for c in cents)
        print("%-6s %-14s %-22s %s | touched=%d" % (gid, ",".join(map(str, acts)),
                                                    "%d:%d" % (best, sizes[best]), track,
                                                    len(touched)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
