"""What does one click DO in vc33? (a paint/toggle puzzle with 1-cell clicks)

WHY THIS QUESTION FIRST
    `click_map.py` showed every one of 1024 click positions changes exactly one cell of the frame.
    That is a strong, specific signal, but it does not yet say WHAT the change is. Before any planner
    can be written, three things must be pinned down, and all three are one experiment:

      1. Is the click a TOGGLE, or does it paint a fixed colour?
      2. Does clicking the same cell twice restore the original value? (toggle) or advance a cycle?
      3. Does the cell change depend on the cell's current value?

    Guessing any of these produces a planner that looks right and is wrong -- which is how the
    14-action LS20 answer happened.

Usage:
    .venv\\Scripts\\python.exe click_probe.py --game vc33
"""
from __future__ import annotations

import argparse
import logging
import sys
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

GLYPH = {0: " ", 1: ".", 2: ":", 3: "-", 4: " ", 5: "+", 6: "*", 7: "#", 8: "%",
         9: "@", 10: "&", 11: "$", 12: "O", 13: "X", 14: "Z", 15: "?"}


def frame_of(obs):
    a = np.asarray(obs.frame)
    return (a[-1] if a.ndim == 3 else a).astype(np.uint8)


def click(env, x, y):
    env.step(GameAction.RESET)
    a = GameAction.ACTION6
    a.set_data({"x": int(x), "y": int(y)})
    env.step(a)
    return frame_of(env.observation_space)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="vc33")
    ap.add_argument("--points", default="")   # "x:y,x:y"
    a = ap.parse_args()

    logging.disable(logging.CRITICAL)
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)
    env = arc.make(a.game)
    env.step(GameAction.RESET)
    base = frame_of(env.observation_space)
    bg = int(np.bincount(base.ravel()).argmax())
    print("game=%s background=%d  value counts=%s"
          % (a.game, bg, sorted(zip(*np.unique(base, return_counts=True)))))

    pts = []
    if a.points:
        for tok in a.points.split(","):
            x, y = tok.split(":")
            pts.append((int(x), int(y)))
    else:
        # sample a spread of positions, including several with different base values
        pts = [(0, 0), (5, 0), (16, 28), (38, 29), (60, 25), (39, 30), (10, 10), (50, 33)]

    print()
    print("--- single click from a fresh RESET: which cell changes, and to what ---")
    for (x, y) in pts:
        cur = click(env, x, y)
        d = np.argwhere(cur != base)
        if len(d) == 0:
            print("  click(%2d,%2d) -> NO change (base cell=%d)" % (x, y, base[y, x]))
            continue
        cell = d[0]
        print("  click(%2d,%2d) -> changed %d cell(s); cell(row=%2d,col=%2d) value %d -> %d"
              % (x, y, len(d), cell[0], cell[1], base[cell[0], cell[1]], cur[cell[0], cell[1]]))

    print()
    print("--- same cell clicked twice in a row (toggle test) ---")
    for (x, y) in pts[:4]:
        env.step(GameAction.RESET)
        a6 = GameAction.ACTION6
        a6.set_data({"x": int(x), "y": int(y)})
        env.step(a6); v1 = frame_of(env.observation_space)[y, x]
        env.step(a6); v2 = frame_of(env.observation_space)[y, x]
        env.step(a6); v3 = frame_of(env.observation_space)[y, x]
        print("  click(%2d,%2d) x3 -> base %d, then %d, %d, %d" % (x, y, base[y, x], v1, v2, v3))

    print()
    print("--- full frame ---")
    print("      " + "".join(str((c // 10) % 10) for c in range(64)))
    print("      " + "".join(str(c % 10) for c in range(64)))
    for r in range(64):
        print("  %3d " % r + "".join(GLYPH.get(int(v), "?") for v in base[r]))


if __name__ == "__main__":
    main()
