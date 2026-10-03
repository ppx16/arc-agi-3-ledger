"""BFS the OBSERVED state graph of an ARC-AGI-3 game to find a minimal level solution.

WHY BFS AND NOT LEARNING
    RHAE scores `(human_actions / ai_actions) ** 2` per level. A learner that eventually finishes in
    300 actions scores ~0.001; a search that finishes in the human's 12 actions scores ~1.0. The
    mechanic here is deterministic movement, so the frame itself is a state key and the shortest
    action sequence to `levels_completed >= 1` is exactly the highest-scoring sequence available.

    This is the honest, cheap version of "understand the game": do not model it, search it -- and
    measure how far the search gets.

WHAT THE BRANCHING COSTS
    Branching is len(available_actions); each node needs one env step. BFS is therefore worth running
    only while the shortest solution stays short. `--max-nodes` makes that budget explicit rather
    than letting a hopeless search run for an hour.

Usage:
    .venv\\Scripts\\python.exe solve.py --game ls20 --max-depth 30 --max-nodes 20000
    .venv\\Scripts\\python.exe solve.py --all --max-depth 12 --max-nodes 1500
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


def key(obs):
    a = np.asarray(obs.frame)
    return bytes((a[-1] if a.ndim == 3 else a).astype(np.uint8).tobytes())


def solve(game, max_depth, max_nodes, verbose=False):
    """Return (actions, levels, nodes, seconds) for the first goal found, else (None, best, ...)."""
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)
    env = arc.make(game)
    if env is None:
        return None, 0, 0, 0.0
    env.step(GameAction.RESET)
    obs = env.observation_space
    if obs.levels_completed:
        return [], int(obs.levels_completed), 0, 0.0

    start = key(obs)
    seen = {start}
    q = deque([(start, [])])
    nodes = 0
    best_levels = 0
    t0 = time.time()

    while q:
        state, path = q.popleft()
        if len(path) >= max_depth:
            continue
        for aid in [int(x) for x in (obs.available_actions or [])]:
            if nodes >= max_nodes:
                return None, best_levels, nodes, time.time() - t0
            # replay the path so the env is at `state`, then take one more action.
            env = arc.make(game)
            env.step(GameAction.RESET)
            for a in path:
                env.step(GameAction.from_id(a))
            act = GameAction.from_id(aid)
            if act is GameAction.ACTION6:
                act.set_data({"x": 32, "y": 32})
            env.step(act)
            o = env.observation_space
            nodes += 1
            lv = int(o.levels_completed or 0)
            if lv > best_levels:
                best_levels = lv
            if lv > 0:
                return path + [aid], lv, nodes, time.time() - t0
            if o.state is GameState.GAME_OVER:
                continue
            k = key(o)
            if k in seen:
                continue
            seen.add(k)
            q.append((k, path + [aid]))
            if verbose and nodes % 200 == 0:
                print("    nodes=%d frontier=%d depth=%d best=%d" % (nodes, len(q), len(path), best_levels))
    return None, best_levels, nodes, time.time() - t0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--max-depth", type=int, default=20)
    ap.add_argument("--max-nodes", type=int, default=6000)
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()

    logging.disable(logging.CRITICAL)
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)
    games = [a.game] if a.game else [e.game_id.split("-")[0] for e in arc.get_environments()]
    if not a.all and not a.game:
        games = games[:1]

    print("%-8s %8s %8s %8s  %s" % ("game", "levels", "nodes", "secs", "solution"))
    print("-" * 78)
    for g in games:
        acts, lv, nodes, secs = solve(g, a.max_depth, a.max_nodes, a.verbose)
        shown = "".join(str(x) for x in acts) if acts else "-"
        print("%-8s %8d %8d %8.1f  %s" % (g, lv, nodes, secs, shown[:52]))


if __name__ == "__main__":
    main()
