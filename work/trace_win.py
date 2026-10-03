"""Trace exactly what a winning agent DID on the games it wins.

WHY
    F34 measured that our agents solve 1-2 of 25 games, and F34.4 showed that replacing the
    novelty walk with a fixed orbit is no better. What no one has looked at is the *trajectory* of
    the wins we already have: r11l L1 is solved at action 27 (level score 66), and the portfolio
    also takes tn36. If those winning sequences have a readable SHAPE, a policy can aim at it
    deliberately instead of hoping; if they do not, that closes the "protocol" lever for good.

    This prints, per step: the action, the size of the frame change, whether the frame was
    unchanged (a no-op), and the instant a level completes -- so the sequence that actually won is
    visible rather than inferred.

Usage:
    .venv\\Scripts\\python.exe trace_win.py <agent.py> <game[,game...]> [--max-steps 80]
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
import os as _os                                        # noqa: E402
_os.environ["OPERATION_MODE"] = "offline"
_os.environ.setdefault("ENVIRONMENTS_DIR", str(ROOT / "environment_files"))

import numpy as np                                      # noqa: E402
import arc_agi                                          # noqa: E402
from arc_agi import OperationMode                       # noqa: E402
from arcengine import GameAction                        # noqa: E402

WORK = Path(__file__).resolve().parents[1] / "work"


def grid(o):
    if o is None or getattr(o, "frame", None) is None:
        return None
    a = np.asarray(o.frame)
    if a.ndim == 3:
        a = a[0]
    return a.astype(np.int16) if a.size else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("agent")
    ap.add_argument("games")
    ap.add_argument("--max-steps", type=int, default=80)
    a = ap.parse_args()
    logging.disable(logging.CRITICAL)

    spec = importlib.util.spec_from_file_location("traced", a.agent)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cls = mod.MyAgent
    cls.MAX_ACTIONS = a.max_steps

    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE,
                         environments_dir=str(ROOT / "environment_files"),
                         recordings_dir=str(WORK / "recordings"))
    card = arc.open_scorecard(tags=["trace"])
    for gid in a.games.split(","):
        gid = gid.strip()
        env = arc.make(gid, seed=0, scorecard_id=card)
        ag = cls(card_id=card, game_id=gid, agent_name="trace.%s" % gid,
                 ROOT_URL="http://localhost", record=False, arc_env=env, tags=["trace"])
        prev = None
        log = []
        lvl0 = 0
        try:
            for step in range(a.max_steps + 1):
                if ag.is_done(ag.frames, ag.frames[-1] if ag.frames else None):
                    break
                if not ag.frames:
                    break
                act = ag.choose_action(ag.frames, ag.frames[-1])
                data = act.action_data.model_dump() if getattr(act, "action_data", None) else {}
                raw = ag.arc_env.step(act, data=data)
                fr = ag._convert_raw_frame_data(raw)
                ag.append_frame(fr)
                ag.action_counter += 1
                g = grid(fr)
                ch = "-" if (g is None or prev is None) else str(int((prev != g).sum()))
                lv = int(getattr(fr, "levels_completed", 0) or 0)
                mark = ""
                if lv > lvl0:
                    mark = "   <<<< LEVEL %d COMPLETE at action %d" % (lv, ag.action_counter)
                    lvl0 = lv
                spec_s = str(int(act.value)) if act is not GameAction.ACTION6 else \
                    "6@%s,%s" % (data.get("x"), data.get("y"))
                log.append("%3d %-10s changed=%-5s lv=%d%s" % (ag.action_counter, spec_s, ch, lv, mark))
                prev = g
                if lv > 0 and lvl0 >= 1 and mark:
                    pass
        except Exception as e:
            log.append("  EXC %s: %s" % (type(e).__name__, e))
        print("=" * 78)
        print("%s  (actions=%d, levels=%d)" % (gid, ag.action_counter, lvl0))
        for line in log:
            print("   " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
