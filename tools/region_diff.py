"""What does ONE block move change outside the block? (the panel and the $ bar)

THE QUESTION (FINDINGS F16)
    Two routes reach the same block position (15,34) and the game behaves differently there, because a
    GLOBAL display also moved: the bottom-left panel's `@` pattern and the `$` (colour 11) bar. Those
    are drawn in the frame, so an agent can READ them -- but only if we know what a move does to them.

    This takes fixed states, applies exactly ONE legal action, and diffs the whole board in three
    regions: the block, the bottom-left panel (rows 53-62, cols 1-10), and the `$` bar.

    If each move changes exactly one `@` position and consumes a fixed number of `$`, the display is a
    positional counter over the block's path and the rule is extractable. If it is irregular, the
    display encodes something else and the 36 reachable cells need enumerating individually.

Usage:
    .venv\\Scripts\\python.exe region_diff.py --game ls20
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

PANEL = (53, 63, 1, 11)      # rows, cols of the bottom-left display box
BAR = (61, 63, 12, 54)       # rows, cols of the $ bar
BLOCK = (0, 64, 0, 64)       # full board, to locate the block


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


def render(g, r0, r1, c0, c1):
    G = {0: " ", 1: ".", 2: ":", 3: "-", 4: " ", 5: "+", 6: "*", 7: "#", 8: "%",
         9: "@", 10: "&", 11: "$", 12: "O", 13: "X", 14: "Z", 15: "?"}
    return ["".join(G.get(int(v), "?") for v in g[r, c0:c1]) for r in range(r0, r1)]


def region(g, box):
    r0, r1, c0, c1 = box
    return g[r0:r1, c0:c1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="ls20")
    ap.add_argument("--paths", default=";".join(["", "1", "3", "1,1", "3,3", "1,1,1,1,1,1"]))
    a = ap.parse_args()

    logging.disable(logging.CRITICAL)
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)

    def play(actions):
        env = arc.make(a.game)
        env.step(GameAction.RESET)
        for x in actions:
            env.step(GameAction.from_id(x))
        return env, frame_of(env.observation_space)

    print("%-16s %-11s %-9s %-24s %s" % ("from state", "action", "block", "PANEL rows 53-62", "$ bar"))
    print("-" * 96)
    for tok in a.paths.split(";"):
        prefix = [int(x) for x in tok.split(",") if x.strip()]
        _, g0 = play(prefix)
        b0 = find_block(g0)
        p0, s0 = region(g0, PANEL), region(g0, BAR)
        n_dollar0 = int((s0 == 11).sum())
        for aid in (1, 2, 3, 4):
            env, g1 = play(prefix + [aid])
            b1 = find_block(g1)
            p1, s1 = region(g1, PANEL), region(g1, BAR)
            n_dollar1 = int((s1 == 11).sum())
            pcell = int((p0 != p1).sum())
            note = ""
            if pcell:
                d = np.argwhere(p1 != p0)
                note = " panel changed %d cells: %s" % (
                    pcell, [(int(y + PANEL[0]), int(x + PANEL[2]), int(p0[y, x]), int(p1[y, x]))
                            for y, x in d[:4]])
            print("%-16s %-11s %-9s %-24s $ %d -> %d%s"
                  % (tok or "(start)", "A%d" % aid,
                     "%s->%s" % (b0, b1) if b1 != b0 else "blocked",
                     "%d cells differ" % pcell if pcell else "unchanged",
                     n_dollar0, n_dollar1, note))

    print()
    print("--- the panel itself, at the start (rows 53-62, cols 1-10) ---")
    _, g = play([])
    for i, line in enumerate(render(g, 53, 63, 1, 11)):
        print("   row %2d |%s|" % (53 + i, line))
    print("--- the $ bar (rows 61-62, cols 12-53) ---")
    for i, line in enumerate(render(g, 61, 63, 12, 54)):
        print("   row %2d |%s|" % (61 + i, line))


if __name__ == "__main__":
    main()
