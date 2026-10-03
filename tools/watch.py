"""Watch one ARC-AGI-3 game region-by-region as actions are applied.

WHY
    `probe.py` shows a diff, but a diff of a sliding mechanism is unreadable as a list of cells.
    This renders a CROP (the part of the board that actually moves) before and after each action, so
    the mechanic is visible as a picture.

Usage:
    .venv\\Scripts\\python.exe watch.py --game ls20 --seq 4,4,3 --rows 36:64 --cols 8:56
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

GLYPH = {0: " ", 1: ".", 2: ":", 3: "-", 4: " ", 5: "+", 6: "*", 7: "#", 8: "%",
         9: "@", 10: "&", 11: "$", 12: "O", 13: "X", 14: "Z", 15: "?"}


def grid(obs):
    a = np.asarray(obs.frame)
    return a[-1] if a.ndim == 3 else a


def show(g, r0, r1, c0, c1, label):
    print("  %s   (rows %d-%d, cols %d-%d)" % (label, r0, r1 - 1, c0, c1 - 1))
    print("      " + "".join(str((c // 10) % 10) for c in range(c0, c1)))
    print("      " + "".join(str(c % 10) for c in range(c0, c1)))
    for r in range(r0, r1):
        print("  %3d " % r + "".join(GLYPH.get(int(v), "?") for v in g[r, c0:c1]))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True)
    ap.add_argument("--seq", default="")
    ap.add_argument("--rows", default="0:64")
    ap.add_argument("--cols", default="0:64")
    ap.add_argument("--reset-first", action="store_true", default=True)
    a = ap.parse_args()
    r0, r1 = (int(x) for x in a.rows.split(":"))
    c0, c1 = (int(x) for x in a.cols.split(":"))

    logging.disable(logging.CRITICAL)
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)
    env = arc.make(a.game)
    if a.reset_first:
        env.step(GameAction.RESET)
    obs = env.observation_space
    print("=" * 100)
    print("GAME %s state=%s levels=%s win=%s avail=%s"
          % (a.game, obs.state, obs.levels_completed, obs.win_levels, obs.available_actions))
    show(grid(obs), r0, r1, c0, c1, "INITIAL")

    for i, tok in enumerate([t for t in a.seq.split(",") if t.strip()], 1):
        aid = int(tok)
        act = GameAction.from_id(aid)
        if act is GameAction.ACTION6:
            act.set_data({"x": 32, "y": 32})
        env.step(act)
        o = env.observation_space
        print()
        show(grid(o), r0, r1, c0, c1,
             "after step %d: ACTION%d  state=%s levels=%s" % (i, aid, o.state, o.levels_completed))
        if o.levels_completed:
            print("  *** LEVEL COMPLETE at step %d ***" % i)
            break
        if o.state is GameState.GAME_OVER:
            print("  *** GAME OVER at step %d ***" % i)
            break


if __name__ == "__main__":
    main()
