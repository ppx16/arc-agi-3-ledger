"""Reverse-engineer ONE ARC-AGI-3 game: render the frame, then diff each action.

WHY
    RHAE scores `(human_actions / ai_actions) ** 2` per level, so guessing is doubly punished:
    you score 0 if you never finish, and near-0 if you flail. The only way to score is to know what
    the actions DO. This tool is the microscope for that: it prints the 64x64 colour grid as readable
    ASCII with a legend, then applies each legal action from a fresh reset and shows exactly which
    cells changed.

    It is deliberately state-less across actions (each action starts from a fresh RESET) so that a
    diff is attributable to that action alone.

Usage:
    .venv\\Scripts\\python.exe probe.py --game ls20
    .venv\\Scripts\\python.exe probe.py --game ls20 --seq 1,1,2,2      # follow a sequence instead
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

# One glyph per colour value; colour 0 is the background and prints as a space.
GLYPH = {0: " ", 1: ".", 2: ":", 3: "-", 4: "=", 5: "+", 6: "*", 7: "#", 8: "%",
         9: "@", 10: "&", 11: "$", 12: "O", 13: "X", 14: "Z", 15: "?"}


def grid(obs):
    a = np.asarray(obs.frame)
    return a[-1] if a.ndim == 3 else a


def render(g, indent="    "):
    bg = Counter(g.flatten().tolist()).most_common(1)[0][0]
    out = []
    for row in g:
        out.append(indent + "".join(GLYPH.get(int(v), "?") if v != bg else " " for v in row))
    return "\n".join(out), bg


def legend(g, bg):
    c = Counter(g.flatten().tolist())
    parts = []
    for val, n in c.most_common():
        tag = " (background)" if val == bg else ""
        parts.append("%s=%d x%-4d%s" % (GLYPH.get(int(val), "?"), val, n, tag))
    return "  ".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True)
    ap.add_argument("--seq", default="", help="comma-separated action ids to follow instead of one-shot diffs")
    ap.add_argument("--maxlen", type=int, default=6, help="cap on sequence length when following --seq")
    a = ap.parse_args()

    logging.disable(logging.CRITICAL)
    # ⚠️ OFFLINE, not NORMAL. NORMAL re-fetches the game list from the ARC API on every Arcade()
    # construction, and that call fails with ConnectionResetError whenever the network hiccups --
    # which turned a local reverse-engineering tool into a network client. The game sources are
    # already cached under environment_files/, so OFFLINE runs the identical engine with no network.
    arc = None
    for mode in (OperationMode.OFFLINE, OperationMode.NORMAL):
        try:
            arc = arc_agi.Arcade(operation_mode=mode)
            probe = arc.make(a.game)
            if probe is not None:
                break
        except Exception as e:
            print("  mode %s failed: %s" % (getattr(mode, "name", mode), type(e).__name__))
            arc = None
    if arc is None:
        raise SystemExit("could not construct an Arcade in OFFLINE or NORMAL mode")
    env = arc.make(a.game)
    if env is None:
        raise SystemExit("no env for %r" % a.game)

    obs = env.observation_space
    g0 = grid(obs)
    txt, bg = render(g0)
    print("=" * 78)
    print("GAME %s | state=%s levels=%s win_levels=%s actions=%s"
          % (a.game, obs.state, obs.levels_completed, obs.win_levels, obs.available_actions))
    print("frame %s | colours: %s" % (g0.shape, legend(g0, bg)))
    print("=" * 78)
    print(txt)
    print()

    avail = [int(x) for x in (obs.available_actions or [])]

    if a.seq:
        ids = [int(x) for x in a.seq.split(",") if x.strip()][:a.maxlen]
        prev = g0
        for i, aid in enumerate(ids, 1):
            act = GameAction.from_id(aid)
            if act is GameAction.ACTION6:
                act.set_data({"x": 32, "y": 32})
            env.step(act)
            cur = grid(env.observation_space)
            diff = np.argwhere(cur != prev)
            print("--- step %d: ACTION%d -> %d cells changed, state=%s levels=%s"
                  % (i, aid, len(diff), env.observation_space.state,
                     env.observation_space.levels_completed))
            if len(diff):
                ys, xs = diff[:, 0], diff[:, 1]
                print("    bbox rows %d-%d cols %d-%d" % (ys.min(), ys.max(), xs.min(), xs.max()))
                for (y, x) in diff[:12]:
                    print("      (%2d,%2d) %d -> %d" % (y, x, prev[y, x], cur[y, x]))
            prev = cur
            if env.observation_space.levels_completed:
                print("    *** LEVEL COMPLETE ***")
                break
            if env.observation_space.state is GameState.GAME_OVER:
                print("    *** GAME OVER ***")
                break
        return

    # one-shot: fresh RESET, then a single action, diffed against the post-RESET frame
    for aid in avail:
        env2 = arc.make(a.game)
        env2.step(GameAction.RESET)
        base = grid(env2.observation_space)
        act = GameAction.from_id(aid)
        if act is GameAction.ACTION6:
            act.set_data({"x": 32, "y": 32})
        env2.step(act)
        cur = grid(env2.observation_space)
        diff = np.argwhere(cur != base)
        print("--- ACTION%d: %d cells changed (from a fresh RESET)  state=%s levels=%s"
              % (aid, len(diff), env2.observation_space.state,
                 env2.observation_space.levels_completed))
        if len(diff):
            ys, xs = diff[:, 0], diff[:, 1]
            print("    bbox rows %d-%d cols %d-%d   (ROW=vertical, COL=horizontal)"
                  % (ys.min(), ys.max(), xs.min(), xs.max()))
            for (y, x) in diff[:10]:
                print("      row %2d col %2d : %d -> %d" % (y, x, base[y, x], cur[y, x]))


if __name__ == "__main__":
    main()
