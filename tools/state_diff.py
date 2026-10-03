"""Diff the board at a block position reached two different ways, to expose hidden state.

THE QUESTION (FINDINGS F15)
    Two routes both put the block on (15,34):
      straight : UP x6                      <- then UP is REFUSED
      detour   : L,L,L,U,U,U,U,R,R,R,U,U    <- then UP COMPLETES the level

    So the block's position is not the state. Something the block painted on the way in gates the
    final move. This replays both routes, stops them at the same block position, and diffs the boards
    cell by cell -- the difference IS the hidden variable, or at least the thing to explain.

Usage:
    .venv\\Scripts\\python.exe state_diff.py --game ls20 --target 15,34
"""
from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter
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
from arcengine import GameAction                          # noqa: E402

GLYPH = {0: " ", 1: ".", 2: ":", 3: "-", 4: " ", 5: "+", 6: "*", 7: "#", 8: "%",
         9: "@", 10: "&", 11: "$", 12: "O", 13: "X", 14: "Z", 15: "?"}

ROUTE_A = [1] * 6                                          # straight up to (15,34)
ROUTE_B = [3, 3, 3, 1, 1, 1, 1, 4, 4, 4, 1, 1]             # detour to (15,34)


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


def play(arc, game, actions):
    env = arc.make(game)
    env.step(GameAction.RESET)
    for aid in actions:
        env.step(GameAction.from_id(aid))
    return env, frame_of(env.observation_space), env.observation_space


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="ls20")
    ap.add_argument("--rows", default="20:36")
    ap.add_argument("--cols", default="12:48")
    a = ap.parse_args()
    r0, r1 = (int(x) for x in a.rows.split(":"))
    c0, c1 = (int(x) for x in a.cols.split(":"))

    logging.disable(logging.CRITICAL)
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)

    envA, gA, oA = play(arc, a.game, ROUTE_A)
    envB, gB, oB = play(arc, a.game, ROUTE_B)
    print("route A (straight, %d actions): block=%s levels=%s state=%s"
          % (len(ROUTE_A), find_block(gA), oA.levels_completed, oA.state))
    print("route B (detour,   %d actions): block=%s levels=%s state=%s"
          % (len(ROUTE_B), find_block(gB), oB.levels_completed, oB.state))

    # what happens to the next UP from each
    for tag, acts in (("A", ROUTE_A), ("B", ROUTE_B)):
        env, _, _ = play(arc, a.game, acts)
        env.step(GameAction.from_id(1))
        o = env.observation_space
        print("  %s + UP -> block=%s levels=%s state=%s"
              % (tag, find_block(frame_of(o)), o.levels_completed, o.state))

    diff = np.argwhere(gA != gB)
    print()
    print("boards differ in %d cells" % len(diff))
    if len(diff):
        ys, xs = diff[:, 0], diff[:, 1]
        print("bounding box rows %d-%d cols %d-%d" % (ys.min(), ys.max(), xs.min(), xs.max()))
        print("  A-only colours:", dict(Counter(int(gA[y, x]) for y, x in diff)))
        print("  B-only colours:", dict(Counter(int(gB[y, x]) for y, x in diff)))
        print()
        print("--- the differing region, A vs B (rows %d-%d, cols %d-%d) ---" % (r0, r1 - 1, c0, c1 - 1))
        print("   A" + " " * (c1 - c0) + "B")
        for r in range(r0, r1):
            ra = "".join(GLYPH.get(int(v), "?") for v in gA[r, c0:c1])
            rb = "".join(GLYPH.get(int(v), "?") for v in gB[r, c0:c1])
            mark = "  <<<" if (gA[r, c0:c1] != gB[r, c0:c1]).any() else ""
            print("  %s | %s%s" % (ra, rb, mark))
    else:
        print("⇒ The boards are IDENTICAL at this position, so the hidden state is NOT in the frame.")
        print("   That would mean the engine tracks something invisible -- check whether the next")
        print("   action depends on the ACTION HISTORY rather than on anything drawn.")


if __name__ == "__main__":
    main()
