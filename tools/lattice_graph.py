"""Map LS20's lattice graph by probing the engine, so the movement RULE can be read off.

THE QUESTION
    The block moves exactly 5 px per action, but the optimal solution goes L,L,L,U,U,U,U,R,R,R,U,U,U
    -- it moves LEFT three times before going UP, even though a single ACTION1 already lifts the block
    from row 45 to row 40 at the start. So `UP` is legal in some columns and not others, and "wall"
    alone cannot explain it: at row 40 both column 19 and column 34 are drawn as wall (`-`), yet the
    block climbs at 19 and not at 34.

    Guessing that rule is exactly how the 14-action answer happened. So measure the graph.

METHOD
    Walk the lattice with the engine and record every legal (from -> to) edge, then print the graph
    as a picture with each lattice cell marked by its colour under the block's footprint and whether
    it was reachable. Probing costs env steps, but this runs OFFLINE where steps are free -- the
    agent cannot do this at competition time, which is the whole point of extracting a rule.

Usage:
    .venv\\Scripts\\python.exe lattice_graph.py --game ls20
"""
from __future__ import annotations

import argparse
import logging
import sys
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

MOVES = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}     # action -> (drow, dcol) in cells


def frame_of(obs):
    a = np.asarray(obs.frame)
    return (a[-1] if a.ndim == 3 else a).astype(np.uint8)


def find_block(g, top=12, bottom=9, w=5, htop=2, hbot=3):
    H, W = g.shape
    for r in range(H - (htop + hbot) + 1):
        for c in range(W - w + 1):
            if np.all(g[r:r + htop, c:c + w] == top) and np.all(g[r + htop:r + htop + hbot, c:c + w] == bottom):
                return r, c
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="ls20")
    ap.add_argument("--max-nodes", type=int, default=400)
    a = ap.parse_args()

    logging.disable(logging.CRITICAL)
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)
    env = arc.make(a.game)
    env.step(GameAction.RESET)
    g0 = frame_of(env.observation_space)
    start = find_block(g0)
    print("block starts at (row=%d, col=%d)  background=%d"
          % (start[0], start[1], int(np.bincount(g0.ravel()).argmax())))

    # BFS over block positions. A node is reached by replaying its path, so the graph is measured
    # under exactly the conditions the agent would experience.
    def goto(path):
        env.step(GameAction.RESET)
        for aid in path:
            env.step(GameAction.from_id(aid))
        return frame_of(env.observation_space)

    edges = {}
    seen = {start}
    q = deque([(start, [])])
    nodes = 0
    level_at = {}
    while q and nodes < a.max_nodes:
        pos, path = q.popleft()
        for aid in [1, 2, 3, 4]:
            goto(path)
            env.step(GameAction.from_id(aid))
            o = env.observation_space
            nodes += 1
            g = frame_of(o)
            nb = find_block(g)
            if nb is None or nb == pos:
                continue
            edges.setdefault(pos, set()).add((nb, aid))
            if int(o.levels_completed or 0) > 0:
                level_at[pos] = (nb, aid)
                continue
            if o.state is GameState.GAME_OVER:
                continue
            if nb not in seen:
                seen.add(nb)
                q.append((nb, path + [aid]))

    print("probed %d env steps; %d distinct block positions reached" % (nodes, len(seen)))
    print()
    rows = sorted({p[0] for p in seen})
    cols = sorted({p[1] for p in seen})
    print("reachable lattice rows: %s" % rows)
    print("reachable lattice cols: %s" % cols)
    print()
    print("--- adjacency (from -> to via action) ---")
    for pos in sorted(edges):
        outs = sorted(edges[pos])
        print("  (%2d,%2d) -> %s" % (pos[0], pos[1],
              "  ".join("A%d->(%2d,%2d)" % (aid, nb[0], nb[1]) for nb, aid in outs)))
    print()
    if level_at:
        print("*** LEVEL COMPLETE edges: %s" % level_at)
    # what colour sits under each reachable cell, to help infer the rule
    print()
    print("--- the frame's colour at each reachable cell's TOP-LEFT pixel ---")
    for pos in sorted(seen):
        r, c = pos
        print("  (%2d,%2d) colour=%d" % (r, c, int(g0[r, c])))


if __name__ == "__main__":
    main()
