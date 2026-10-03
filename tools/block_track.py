"""Track LS20's movable block through a known-good solution, to learn the real geometry.

WHY
    The planner cannot be written from a guess about the grid. What we actually know is that one
    ACTION3 moved the block from cols 34-38 to cols 29-33 -- i.e. a shift of 5, the block's own
    width -- and that the vacated cells became wall (colour 3). That suggests the board is a grid of
    5x5 cells and one action = one cell, but "suggests" is not good enough to build on, because a
    planner built on a wrong geometry produces a confident wrong answer (exactly how the 14-action
    bug happened).

    So: play the verified 13-action solution and print, at every step, the block's bounding box, the
    cell it occupies under a candidate lattice, and whether the destination area was background.

Usage:
    .venv\\Scripts\\python.exe block_track.py --game ls20
    .venv\\Scripts\\python.exe block_track.py --game ls20 --seq 3,3,3,1
"""
from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter
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

SOLVED = [3, 3, 3, 1, 1, 1, 1, 4, 4, 4, 1, 1, 1]


def grid(obs):
    a = np.asarray(obs.frame)
    return a[-1] if a.ndim == 3 else a


def block_bbox(g, top=12, bottom=9, w=5, htop=2, hbot=3):
    """Locate the movable BLOCK by its exact template, not by colour alone.

    ⚠️ Matching on colour 12 or 9 alone is wrong: colour 9 also draws the `@` patterns inside the
    level-indicator panels (rows 11-13 and 53-60), so the naive bounding box came out 50x36 and
    never moved -- it was measuring the whole board. The block is a specific 5x5 stamp: two rows of
    `top` directly above three rows of `bottom`.
    """
    H, W = g.shape
    for r in range(H - (htop + hbot) + 1):
        for c in range(W - w + 1):
            if not np.all(g[r:r + htop, c:c + w] == top):
                continue
            if not np.all(g[r + htop:r + htop + hbot, c:c + w] == bottom):
                continue
            return r, r + htop + hbot - 1, c, c + w - 1
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="ls20")
    ap.add_argument("--seq", default="")
    a = ap.parse_args()
    seq = [int(x) for x in a.seq.split(",") if x.strip()] or SOLVED

    logging.disable(logging.CRITICAL)
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)
    env = arc.make(a.game)
    env.step(GameAction.RESET)
    g = grid(env.observation_space)
    bg = Counter(g.flatten().tolist()).most_common(1)[0][0]
    print("background colour = %d" % bg)
    bb = block_bbox(g)
    print("%-5s %-28s %-14s %s" % ("step", "block bbox (r0,r1,c0,c1)", "size", "note"))
    print("-" * 76)
    print("%-5s %-28s %-14s %s" % ("init", str(bb), "%dx%d" % (bb[1] - bb[0] + 1, bb[3] - bb[2] + 1), ""))

    prev = bb
    for i, aid in enumerate(seq, 1):
        env.step(GameAction.from_id(aid))
        o = env.observation_space
        g = grid(o)
        bb = block_bbox(g)
        dr = dc = None
        if bb and prev:
            dr = bb[0] - prev[0]
            dc = bb[2] - prev[2]
        note = ""
        if bb and prev:
            note = "delta row %+d col %+d" % (dr, dc)
        print("%-5d %-28s %-14s %s" % (i, str(bb),
                                       "%dx%d" % (bb[1] - bb[0] + 1, bb[3] - bb[2] + 1) if bb else "-",
                                       note))
        prev = bb
        if o.levels_completed:
            print("      *** LEVEL %d COMPLETE at step %d ***" % (o.levels_completed, i))
            break
        if o.state is GameState.GAME_OVER:
            print("      *** GAME OVER ***")
            break

    print()
    print("final colours:", dict(Counter(grid(env.observation_space).flatten().tolist()).most_common()))


if __name__ == "__main__":
    main()
