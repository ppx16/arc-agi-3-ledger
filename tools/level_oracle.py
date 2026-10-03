"""Run the BFS oracle on a SPECIFIC level by replaying a known prefix first.

WHY
    `solve_levels.py` always starts from level 1. To study level 2 on its own terms we need to arrive
    there first -- and level 1's optimal route is known and verified (F19), so replaying it is exact,
    not approximate.

    The oracle gives the true minimal action count for the level, which is the number a planner has to
    match. Comparing that with what the planner currently produces is the measurement that says
    whether the model is close or structurally wrong.

Usage:
    .venv\\Scripts\\python.exe level_oracle.py --game ls20 --level 2 --prefix 3331111444111
    .venv\\Scripts\\python.exe level_oracle.py --game ls20 --level 2 --prefix 3331111444111 --max-depth 12
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "starter"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor" / "ARC-AGI-3-Agents"))
import os as _os_for_dirs
_os_for_dirs.environ.setdefault("ENVIRONMENTS_DIR", str(ROOT / "environment_files"))
_os_for_dirs.environ.setdefault("RECORDINGS_DIR", str(ROOT / "recordings"))

import numpy as np                                        # noqa: E402
import arc_agi                                            # noqa: E402
from arc_agi import OperationMode                         # noqa: E402
from arcengine import GameAction, GameState               # noqa: E402


def frame_of(obs):
    a = np.asarray(obs.frame)
    return (a[-1] if a.ndim == 3 else a).astype(np.uint8)


def key(obs):
    return bytes(frame_of(obs).tobytes())


class G:
    """One env, replayed to any node. RESET restarts the CURRENT level, and the prefix walks us into
    the target level, so replay is exact (the engine is deterministic -- verified, FINDINGS F1)."""

    def __init__(self, arc, game):
        self.arc, self.env, self.steps = arc, arc.make(game), 0

    def goto(self, path):
        self.env.step(GameAction.RESET)
        self.steps += 1
        for (aid, x, y) in path:
            a = GameAction.from_id(aid)
            if aid == 6:
                a.set_data({"x": int(x), "y": int(y)})
            self.env.step(a)
            self.steps += 1
        return self.env.observation_space

    def step(self, spec):
        aid, x, y = spec
        a = GameAction.from_id(aid)
        if aid == 6:
            a.set_data({"x": int(x), "y": int(y)})
        self.env.step(a)
        self.steps += 1
        return self.env.observation_space


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="ls20")
    ap.add_argument("--level", type=int, default=2)
    ap.add_argument("--prefix", default="")
    ap.add_argument("--max-depth", type=int, default=12)
    ap.add_argument("--max-nodes", type=int, default=4000)
    ap.add_argument("--clicks", type=int, default=8)
    a = ap.parse_args()

    logging.disable(logging.CRITICAL)
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)
    g = G(arc, a.game)
    prefix = [(int(c), None, None) for c in a.prefix if c.strip()]
    obs = g.goto(prefix)
    print("prefix=%s -> block-level reached: levels_completed=%s state=%s"
          % (a.prefix or "(none)", obs.levels_completed, obs.state))
    start_level = int(obs.levels_completed or 0)

    def edges(o):
        out = []
        for v in (o.available_actions or []):
            v = int(v)
            if v == 6:
                gg = frame_of(o)
                bg = int(np.bincount(gg.ravel()).argmax())
                ys, xs = np.nonzero(gg != bg)
                for i in range(min(a.clicks, max(1, len(ys)))):
                    out.append((6, int(xs[i]), int(ys[i])))
            else:
                out.append((v, None, None))
        return out

    seen = {key(obs)}
    q = deque([prefix])
    nodes, t0 = 0, time.time()
    while q:
        path = q.popleft()
        if len(path) - len(prefix) >= a.max_depth:
            continue
        base = g.goto(path)
        for spec in edges(base):
            if nodes >= a.max_nodes:
                print("node budget exhausted (%d)" % nodes)
                q.clear()
                break
            g.goto(path)
            o = g.step(spec)
            nodes += 1
            if int(o.levels_completed or 0) > start_level:
                solved = [s[0] for s in path[len(prefix):] + [spec]]
                print("SOLVED level %d in %d actions: %s   (nodes=%d, %.0fs)"
                      % (start_level + 1, len(solved),
                         "".join(str(x) for x in solved), nodes, time.time() - t0))
                return
            if o.state is GameState.GAME_OVER:
                continue
            k = key(o)
            if k in seen:
                continue
            seen.add(k)
            q.append(path + [spec])
    print("NOT SOLVED within depth %d / %d nodes (%d distinct states, %.0fs)"
          % (a.max_depth, a.max_nodes, len(seen), time.time() - t0))


if __name__ == "__main__":
    main()
