"""Play LS20 level after level using the planner, verifying each level end to end.

THE QUESTION
    Everything in F13-F19 was measured on LEVEL 1. A model that explains one level and not the next
    is a curve fit, not a rule. This applies the identical planner -- lattice, `>= 20 wall`
    passability, enclosed-panel goal, interior-object collectibles -- to each level in turn, replays
    the plan on the engine, and reports what actually happened.

    It also reports the `$` budget spent per level, because that is the quantity the competition
    scores against.

Usage:
    .venv\\Scripts\\python.exe play_levels.py --game ls20 --max-levels 7
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "starter"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor" / "ARC-AGI-3-Agents"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import os as _os_for_dirs
_os_for_dirs.environ.setdefault("ENVIRONMENTS_DIR", str(ROOT / "environment_files"))
_os_for_dirs.environ.setdefault("RECORDINGS_DIR", str(ROOT / "recordings"))

import numpy as np                                        # noqa: E402
import arc_agi                                            # noqa: E402
from arc_agi import OperationMode                         # noqa: E402
from arcengine import GameAction, GameState               # noqa: E402

from plan_ls20 import find_block, find_goal, find_collectibles, plan, frame_of   # noqa: E402

D = 5


def dollars(g):
    """How many `$` (colour 11) cells are left -- the action budget, read from the frame."""
    return int((g == 11).sum())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="ls20")
    ap.add_argument("--max-levels", type=int, default=7)
    a = ap.parse_args()

    logging.disable(logging.CRITICAL)
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)
    env = arc.make(a.game)
    env.step(GameAction.RESET)
    g = frame_of(env.observation_space)
    print("start: levels=%s state=%s  $=%d" % (env.observation_space.levels_completed,
                                               env.observation_space.state, dollars(g)))
    print()
    print("%-6s %-8s %-14s %-9s %-22s %-11s %s"
          % ("level", "actions", "planned", "budget $", "collectibles", "replay", "block start"))
    print("-" * 104)

    total = 0
    for lvl in range(1, a.max_levels + 1):
        start = find_block(g)
        if start is None:
            print("  level %d: no block found -- stopping" % lvl)
            break
        goals = find_goal(g, start)
        picks = find_collectibles(g, start)
        acts, goal, _ = plan(g, start)
        planned = "".join(str(x) for x in acts) if acts else "-"
        before = dollars(g)
        if not acts:
            print("%-6d %-8s %-14s %-9d %-22s %-11s %s"
                  % (lvl, "-", planned, before, sorted(picks), "NO PLAN", start))
            break
        for aid in acts:
            env.step(GameAction.from_id(aid))
        o = env.observation_space
        g = frame_of(o)
        after = dollars(g)
        ok = int(o.levels_completed or 0) >= lvl
        total += len(acts)
        print("%-6d %-8d %-14s %-9s %-22s %-11s %s"
              % (lvl, len(acts), planned, "%d->%d" % (before, after), sorted(picks),
                 "OK" if ok else "FAILED", start))
        if not ok:
            print("   ⇒ level %d did NOT complete; levels_completed=%s state=%s"
                  % (lvl, o.levels_completed, o.state))
            break
        if o.state is GameState.WIN:
            print("   *** GAME WON ***")
            break

    print()
    print("total planned actions: %d   (budget was %d $ for the first level => ~41 actions)"
          % (total, before if 'before' in dir() else 0))


if __name__ == "__main__":
    main()
