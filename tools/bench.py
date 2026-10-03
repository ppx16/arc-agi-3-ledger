"""Run any ARC-AGI-3 agent across ALL 25 games and tabulate levels completed.

WHY: counts levels completed and actions per game. This is the coarse sweep.

⚠️ SUPERSEDED FOR SCORING by `score_local.py` -- use that one for any decision.
The paragraph that used to sit here claimed the human baselines are "not public",
which is FALSE: every game ships `environment_files/<game>/<hash>/metadata.json`
with `baseline_actions`, so the real competition metric is computable offline.
See FINDINGS F24/F25. This tool is still handy for a fast levels/actions sweep,
but it cannot rank two agents by score and must not be used as if it could.

⚠️ `--agent goose` needs `torch` in starter/.venv. It was missing for a long time,
so earlier "goose was measured locally" conclusions were never actually measured.

Usage:
    .venv\\Scripts\\python.exe bench.py --agent mine
    .venv\\Scripts\\python.exe bench.py --agent random
"""
from __future__ import annotations

import argparse
import importlib.util
import logging
import sys
import time
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

import arc_agi                                            # noqa: E402
from arc_agi import OperationMode                         # noqa: E402


def load_class(which: str):
    paths = {"mine": ROOT / "agent" / "my_agent.py",
             "goose": ROOT / "agent" / "goose_agent.py"}
    if which in paths:
        spec = importlib.util.spec_from_file_location(
            "user_agent_module_%s" % which, paths[which])
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.MyAgent
    if which == "random":
        from agents.templates.random_agent import Random
        return Random
    raise SystemExit("--agent must be mine|goose|random")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--agent", default="mine", choices=["mine", "goose", "random"])
    p.add_argument("--max-steps", type=int, default=80)
    p.add_argument("--games", default="")
    a = p.parse_args()

    logging.basicConfig(level=logging.ERROR)              # silence per-action spam
    logging.getLogger().setLevel(logging.ERROR)

    arc = arc_agi.Arcade(operation_mode=OperationMode.NORMAL)
    envs = arc.get_environments()
    ids = [e.game_id.split("-")[0] for e in envs]
    if a.games:
        want = {g.strip() for g in a.games.split(",")}
        ids = [g for g in ids if g in want]

    cls = load_class(a.agent)
    cls.MAX_ACTIONS = a.max_steps

    total_levels = 0
    total_actions = 0
    rows = []
    t0 = time.time()
    for i, gid in enumerate(ids, 1):
        env = arc.make(gid)
        if env is None:
            rows.append((gid, -1, 0, "NO_ENV"))
            continue
        ag = cls(card_id="bench", game_id=gid, agent_name=f"bench.{a.agent}.{gid}",
                 ROOT_URL="http://localhost", record=False, arc_env=env, tags=["bench"])
        try:
            ag.main()
        except Exception as e:
            rows.append((gid, -1, 0, "EXC %s" % type(e).__name__))
            continue
        fin = ag.frames[-1]
        rows.append((gid, fin.levels_completed, ag.action_counter, str(fin.state)))
        total_levels += int(fin.levels_completed or 0)
        total_actions += ag.action_counter

    print()
    print("agent=%-7s max_steps=%-3d  %d games  %.0f s"
          % (a.agent, a.max_steps, len(ids), time.time() - t0))
    print("%-8s %8s %8s  %s" % ("game", "levels", "actions", "state"))
    print("-" * 52)
    for gid, lv, ac, st in rows:
        print("%-8s %8d %8d  %s" % (gid, lv, ac, st))
    print("-" * 52)
    print("TOTAL levels=%d  actions=%d  (over %d games)"
          % (total_levels, total_actions, len(ids)))


if __name__ == "__main__":
    main()
