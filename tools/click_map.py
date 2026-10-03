"""Find WHERE a click does something, in a game whose only action is ACTION6.

WHY
    `solve_levels.py` terminated after ~12 nodes on `tn36`/`ft09`/`lp85`: every object-centroid click
    left the frame identical, so BFS had no new states and stopped. That says object centroids are the
    wrong guess -- it does NOT say the games are unsolvable. This sweeps all 4096 click positions from
    a fresh reset and reports which ones actually change the frame, so the real clickable targets can
    be read off instead of guessed.

    Cost: 4096 env steps, seconds locally. This is the cheap way to stop guessing.

Usage:
    .venv\\Scripts\\python.exe click_map.py --game tn36
    .venv\\Scripts\\python.exe click_map.py --game tn36 --stride 1
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
from arcengine import GameAction                          # noqa: E402


def frame_of(obs):
    a = np.asarray(obs.frame)
    return (a[-1] if a.ndim == 3 else a).astype(np.uint8)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True)
    ap.add_argument("--stride", type=int, default=1)
    ap.add_argument("--show", type=int, default=40)
    a = ap.parse_args()

    logging.disable(logging.CRITICAL)
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)
    env = arc.make(a.game)
    env.step(GameAction.RESET)
    base = frame_of(env.observation_space)
    bg = int(np.bincount(base.ravel()).argmax())
    print("game=%s  frame=%s  background colour=%d" % (a.game, base.shape, bg))
    print("available_actions = %s" % env.observation_space.available_actions)

    hits = []
    tried = 0
    for y in range(0, 64, a.stride):
        for x in range(0, 64, a.stride):
            env.step(GameAction.RESET)
            act = GameAction.ACTION6
            act.set_data({"x": int(x), "y": int(y)})
            env.step(act)
            cur = frame_of(env.observation_space)
            tried += 1
            if not np.array_equal(cur, base):
                n = int((cur != base).sum())
                hits.append((x, y, n, int(env.observation_space.levels_completed or 0)))
                if env.observation_space.levels_completed:
                    print("  *** click (%d,%d) COMPLETES the level ***" % (x, y))
            if env.observation_space.levels_completed:
                break
        else:
            continue
        break

    print("tried %d positions; %d changed the frame" % (tried, len(hits)))
    if hits:
        print("first %d changing positions (x, y, cells changed, levels):" % min(a.show, len(hits)))
        for h in hits[:a.show]:
            print("   (%2d,%2d)  %4d cells  levels=%d" % h)
        xs = Counter(h[0] for h in hits)
        ys = Counter(h[1] for h in hits)
        print("column histogram: %s" % sorted(xs.items())[:20])
        print("row histogram   : %s" % sorted(ys.items())[:20])
    else:
        print("⇒ NO single click changes the frame at all, at stride %d." % a.stride)
        print("   So ACTION6 is not a direct state change here: the game needs a SEQUENCE,")
        print("   or the click must be accompanied by something else.")


if __name__ == "__main__":
    main()
