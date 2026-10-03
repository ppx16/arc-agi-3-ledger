"""Drive any agent one action at a time against one game and log what each action did.

`Agent.main()` is a black box: it runs to the cap and reports a total. That is useless for
diagnosing WHY a policy fails, so this reimplements the loop with per-action instrumentation:

    action#, action, key, frame changed?, pixels changed, levels_completed, state

Usage:
    .venv\\Scripts\\python.exe trace_policy.py --game sp80 --steps 40
    .venv\\Scripts\\python.exe trace_policy.py --game ls20 --agent ..\\agents\\novelty_agent.py
"""
from __future__ import annotations

import argparse
import importlib.util
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "starter"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor" / "ARC-AGI-3-Agents"))
import os as _os  # noqa: E402
_os.environ["OPERATION_MODE"] = "offline"
_os.environ["ENVIRONMENTS_DIR"] = str(ROOT / "environment_files")

import numpy as np                                        # noqa: E402
import arc_agi                                            # noqa: E402
from arc_agi import OperationMode                         # noqa: E402
from arcengine import GameState                           # noqa: E402


def load_class(which: str):
    p = Path(which)
    if not p.is_absolute():
        p = (Path(__file__).resolve().parent / p).resolve()
    spec = importlib.util.spec_from_file_location("traced_agent", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.MyAgent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True)
    ap.add_argument("--agent", default="..\\agents\\novelty_agent.py")
    ap.add_argument("--steps", type=int, default=40)
    a = ap.parse_args()

    logging.disable(logging.CRITICAL)
    cls = load_class(a.agent)
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE,
                         environments_dir=str(ROOT / "environment_files"),
                         recordings_dir=str(ROOT.parent / "work" / "recordings"))
    env = arc.make(a.game, seed=0)
    ag = cls(card_id="trace", game_id=a.game, agent_name="trace",
             ROOT_URL="http://localhost", record=False, arc_env=env, tags=["trace"])

    print("game=%s  agent=%s  start state=%s levels=%s"
          % (a.game, Path(a.agent).name, env.observation_space.state,
             env.observation_space.levels_completed))
    print("%4s %-9s %-14s %-7s %7s %6s  %s"
          % ("#", "action", "key", "changed", "pixels", "levels", "state"))
    print("-" * 74)

    prev = np.array(env.observation_space.frame)
    lv0 = int(env.observation_space.levels_completed or 0)
    solved_at = None
    for i in range(1, a.steps + 1):
        raw = ag._convert_raw_frame_data(env.observation_space)
        action = ag.choose_action(ag.frames, raw)
        key = getattr(action, "reasoning", "") or ""
        frame = ag.take_action(action)
        if frame is None:
            print("  take_action returned None -- stopping")
            break
        ag.append_frame(frame)
        ag.action_counter = i
        cur = np.array(env.observation_space.frame)
        changed = not np.array_equal(prev, cur)
        npix = int((prev != cur).sum()) if changed else 0
        lv = int(env.observation_space.levels_completed or 0)
        if lv > lv0 and solved_at is None:
            solved_at = i
        print("%4d %-9s %-14s %-7s %7d %6d  %s"
              % (i, action.name, key[:14], "yes" if changed else "no", npix, lv,
                 env.observation_space.state))
        prev = cur
        if env.observation_space.state is GameState.WIN:
            print("  *** WIN ***")
            break
        if ag.is_done(ag.frames, frame):
            print("  agent called is_done() -> True")
            break

    print("-" * 74)
    print("solved level 1 at action: %s" % (solved_at if solved_at else "NEVER"))
    for k in ("levels", "states", "resets", "game_overs", "level_actions", "error"):
        if hasattr(ag, "novelty_report") and k in ag.novelty_report:
            print("  %-14s %s" % (k, ag.novelty_report[k]))


if __name__ == "__main__":
    main()
