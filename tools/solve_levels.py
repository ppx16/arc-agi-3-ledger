"""Solve an ARC-AGI-3 game LEVEL BY LEVEL with BFS, exploring ACTION6 click coordinates.

WHAT CHANGED FROM THE FIRST VERSION, AND WHY IT MATTERED
    v1 stored the path as bare action ids and always sent ACTION6 to (32, 32) -- the centre. Six of
    the 25 public games accept ONLY ACTION6, so for those games the oracle explored exactly one click
    position and reported "unsolvable". It was not measuring those games at all. Two fixes:

    1. A path element is now `(action_id, x, y)`, so two different clicks from the same frame are two
       different edges. Storing only the id silently collapsed them into one.
    2. Click candidates are derived from the FRAME: centroids of the connected non-background regions
       first, then a coarse lattice to fall back on. Clicking the middle of a coloured object is far
       more likely to do something than clicking empty space, and the earlier hand probe showed the
       blind lattice makes the frame change while solving nothing.

    ⚠️ Reset semantics: `RESET` restarts the CURRENT LEVEL, not the game (measured: after finishing
    level 1 the reset hash is 4412df0168a89497, not the fresh cfe5196fb75182bb). Replay is still
    sound because the engine is deterministic, but only while the search stays inside one level --
    which it does, because we return the moment a level completes.

Usage:
    .venv\\Scripts\\python.exe solve_levels.py --game ls20 --max-depth 16
    .venv\\Scripts\\python.exe solve_levels.py --games vc33,tn36 --clicks object
    .venv\\Scripts\\python.exe solve_levels.py            # all 25
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from collections import deque
from pathlib import Path

# ⚠️ This tool lives in tools/ but drives the vendored upstream clone in starter/.
# ROOT is the STARTER directory on purpose: the scripts reference ROOT/agent/my_agent.py,
# ROOT/vendor/... and ROOT/environment_files, all of which belong to the starter kit.
ROOT = Path(__file__).resolve().parents[1] / "starter"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor" / "ARC-AGI-3-Agents"))
import os as _os_for_dirs                      # noqa: E402  (added by pin_dirs.py)
# ⚠️ The engine defaults environments_dir to the RELATIVE "environment_files", so it resolves
# against the cwd. These tools live in tools/ while the cache lives in starter/, so pin both
# directories to ABSOLUTE paths here rather than chdir-ing (which would move every other
# relative path in the process). Found the hard way: arc.make() returned None and surfaced as
# "AttributeError: 'NoneType' object has no attribute 'step'".
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


def click_candidates(g, mode="object", lattice=8, max_pts=24):
    """Where to try clicking. Object centroids first: a coloured blob is far more likely to be
    interactive than empty background, which is what a blind lattice mostly hits."""
    pts = []
    if mode in ("object", "both"):
        bg = int(np.bincount(g.ravel()).argmax())
        mask = g != bg
        if mask.any():
            # cheap connected-component-ish grouping on a coarse lattice
            ys, xs = np.nonzero(mask)
            buckets = {}
            for y, x in zip(ys.tolist(), xs.tolist()):
                buckets.setdefault((y // 8, x // 8), []).append((y, x))
            groups = sorted(buckets.values(), key=len, reverse=True)
            for grp in groups[:max_pts]:
                arr = np.asarray(grp)
                pts.append((int(arr[:, 1].mean()), int(arr[:, 0].mean())))
    if mode in ("lattice", "both"):
        for y in range(lattice // 2, 64, lattice):
            for x in range(lattice // 2, 64, lattice):
                pts.append((x, y))
    # de-duplicate, preserve order
    seen, out = set(), []
    for p in pts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out[:max_pts]


class Game:
    def __init__(self, arc, game):
        self.arc, self.name = arc, game
        self.env = arc.make(game)
        self.steps = 0

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

    def step_action(self, spec):
        aid, x, y = spec
        a = GameAction.from_id(aid)
        if aid == 6:
            a.set_data({"x": int(x), "y": int(y)})
        self.env.step(a)
        self.steps += 1
        return self.env.observation_space


def edges(obs, click_mode, n_clicks):
    ids = [int(v) for v in (obs.available_actions or [])]
    out = []
    for aid in ids:
        if aid == 6:
            for (x, y) in click_candidates(frame_of(obs), click_mode, max_pts=n_clicks):
                out.append((aid, x, y))
        else:
            out.append((aid, None, None))
    return out


def bfs_level(g: Game, prefix, max_depth, max_nodes, click_mode, n_clicks, verbose=False):
    obs = g.goto(prefix)
    start_level = int(obs.levels_completed or 0)
    seen = {key(obs)}
    q = deque([[]])
    nodes = 0
    t0 = time.time()
    while q:
        path = q.popleft()
        if len(path) >= max_depth:
            continue
        base = g.goto(prefix + path)
        specs = edges(base, click_mode, n_clicks)
        for spec in specs:
            if nodes >= max_nodes:
                return None, obs, nodes, time.time() - t0
            # ⚠️ Re-position before EVERY candidate. v1 positioned once per node and then stepped the
            # whole list in sequence, applying every action after the first to the WRONG parent --
            # it explored a different graph and confidently returned a 14-action answer where the
            # true optimum is 13.
            g.goto(prefix + path)
            o = g.step_action(spec)
            nodes += 1
            if int(o.levels_completed or 0) > start_level:
                return path + [spec], o, nodes, time.time() - t0
            if o.state is GameState.GAME_OVER:
                continue
            k = key(o)
            if k in seen:
                continue
            seen.add(k)
            q.append(path + [spec])
        if verbose and nodes % 500 == 0:
            print("      nodes=%d frontier=%d depth=%d" % (nodes, len(q), len(path)), flush=True)
    return None, obs, nodes, time.time() - t0


def solve_game(arc, game, max_depth, max_nodes, click_mode, n_clicks, verbose=False):
    g = Game(arc, game)
    prefix, levels = [], 0
    t0 = time.time()
    total_nodes = 0
    for _ in range(12):
        suffix, obs, nodes, secs = bfs_level(g, prefix, max_depth, max_nodes, click_mode, n_clicks, verbose)
        total_nodes += nodes
        if suffix is None:
            break
        prefix += suffix
        levels = int(obs.levels_completed or 0)
        print("    level %d: +%d actions -> %s  (nodes=%d, %.1fs)"
              % (levels, len(suffix), "".join(str(s[0]) for s in suffix), nodes, secs), flush=True)
        if obs.state is GameState.WIN:
            break
    return prefix, levels, total_nodes, time.time() - t0, g.steps


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="")
    ap.add_argument("--games", default="")
    ap.add_argument("--max-depth", type=int, default=14)
    ap.add_argument("--max-nodes", type=int, default=4000)
    ap.add_argument("--clicks", default="object", choices=["object", "lattice", "both"])
    ap.add_argument("--n-clicks", type=int, default=16)
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()

    logging.disable(logging.CRITICAL)
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)
    if a.games:
        games = [x.strip() for x in a.games.split(",") if x.strip()]
    elif a.game:
        games = [a.game]
    else:
        games = [e.game_id.split("-")[0] for e in arc.get_environments()]

    print("clicks=%s n_clicks=%d depth=%d nodes=%d" % (a.clicks, a.n_clicks, a.max_depth, a.max_nodes))
    for gname in games:
        try:
            acts, lv, nodes, secs, steps = solve_game(arc, gname, a.max_depth, a.max_nodes,
                                                      a.clicks, a.n_clicks, a.verbose)
        except Exception as e:
            print("== %-6s FAILED %s %s" % (gname, type(e).__name__, str(e)[:90]), flush=True)
            continue
        print("== %-6s levels=%d actions=%d nodes=%d %.0fs" % (gname, lv, len(acts), nodes, secs), flush=True)


if __name__ == "__main__":
    main()
