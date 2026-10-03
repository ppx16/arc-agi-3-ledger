"""Find what distinguishes a PASSABLE lattice cell from a blocked one, using the frame alone.

THE PROBLEM
    The lattice graph is known (36 reachable positions out of a 7x8 lattice), but the colour at a
    reachable cell's top-left pixel is `3` -- the same as everywhere else. So the naive "wall colour"
    reading does not separate them, and a planner built on "is it background?" would be wrong.

    This compares the FULL 5x5 footprint of every lattice cell -- reachable and not -- and reports a
    signature per cell, so the discriminating feature can be identified instead of assumed.

Usage:
    .venv\\Scripts\\python.exe cell_signature.py --game ls20
"""
from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter, deque
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


def find_block(g, top=12, bottom=9, w=5, htop=2, hbot=3):
    H, W = g.shape
    for r in range(H - (htop + hbot) + 1):
        for c in range(W - w + 1):
            if np.all(g[r:r + htop, c:c + w] == top) and np.all(g[r + htop:r + htop + hbot, c:c + w] == bottom):
                return r, c
    return None


def sig(g, r, c):
    """Signature of the 5x5 footprint: how many of each colour, plus the centre value."""
    blk = g[r:r + 5, c:c + 5]
    cnt = Counter(int(v) for v in blk.ravel())
    return cnt


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="ls20")
    ap.add_argument("--max-nodes", type=int, default=600)
    a = ap.parse_args()

    logging.disable(logging.CRITICAL)
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)
    env = arc.make(a.game)
    env.step(GameAction.RESET)
    g0 = frame_of(env.observation_space)
    start = find_block(g0)

    def goto(path):
        env.step(GameAction.RESET)
        for aid in path:
            env.step(GameAction.from_id(aid))
        return frame_of(env.observation_space)

    seen = {start}
    q = deque([(start, [])])
    nodes = 0
    while q and nodes < a.max_nodes:
        pos, path = q.popleft()
        for aid in (1, 2, 3, 4):
            goto(path)
            env.step(GameAction.from_id(aid))
            o = env.observation_space
            nodes += 1
            nb = find_block(frame_of(o))
            if nb is None or nb == pos:
                continue
            if int(o.levels_completed or 0) > 0 or o.state is GameState.GAME_OVER:
                continue
            if nb not in seen:
                seen.add(nb)
                q.append((nb, path + [aid]))

    rows = sorted({p[0] for p in seen})
    cols = sorted({p[1] for p in seen})
    print("reachable rows %s cols %s  (block at %s)" % (rows, cols, start))
    print()
    print("--- signature per lattice cell (5x5 footprint colour counts) ---")
    print("%-11s %-6s %s" % ("cell", "class", "colour counts inside the 5x5 footprint"))
    groups = {}
    for r in range(start[0] - 30, start[0] + 1, 5):
        for c in range(14, 50, 5):
            if not (0 <= r <= 59 and 0 <= c <= 59):
                continue
            cnt = sig(g0, r, c)
            key = tuple(sorted(cnt.items()))
            groups.setdefault(key, []).append((r, c, (r, c) in seen))
    for key, cells in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        reach = [c for c in cells if c[2]]
        block = [c for c in cells if not c[2]]
        print("  signature %-34s reachable=%-3d blocked=%-3d" % (str(dict(key))[:34], len(reach), len(block)))

    print()
    print("--- per-cell detail ---")
    for r in sorted({p[0] for p in seen} | set()):
        pass
    for r in range(start[0] - 30, start[0] + 1, 5):
        line = []
        for c in range(14, 50, 5):
            cnt = sig(g0, r, c)
            marker = "R" if (r, c) in seen else "."
            line.append("%s%s" % (marker, "".join("%d:%d " % (k, v) for k, v in sorted(cnt.items()))))
        print("  row %2d | %s" % (r, " | ".join(line)))


if __name__ == "__main__":
    main()
