"""Score ANY ARC-AGI-3 agent with the COMPETITION's OWN scorer, offline, on the 25 public games.

WHY THIS EXISTS
    `bench.py` measured only "levels completed", and its docstring asserted that
    "the human baselines that turn it into a score are not public". THAT WAS WRONG.
    Every downloaded game ships `environment_files/<game>/<hash>/metadata.json`
    containing `baseline_actions` -- the per-level human action counts:

        ls20: [22, 123, 73, 84, 96, 192, 186]      sp80: [39, 58, 25, 148, 96, 152]
        cd82: [55,  8, 41, 21, 23,  23]            vc33: [ 7, 18, 44,  61, 131, 34, 152]

    With those, the competition metric is exactly computable locally, and it is the
    metric the leaderboard uses -- not a proxy. `Arcade.close_scorecard()` in OFFLINE
    mode runs `EnvironmentScorecard.from_scorecard(scorecard, available_environments)`,
    and `available_environments` is scanned from those same metadata.json files. So we
    reuse the *shipped* scorer rather than reimplementing it (a reimplementation could
    silently disagree with the leaderboard, which is the one thing a local CV must not do).

THE METRIC (read from arc_agi/scorecard.py, not guessed)
    per level i (1-indexed):
        completed : score_i = min( 100 * (baseline_i / actions_i) ** 2 , 115 )
        not       : score_i = 0
    per game:
        game_score = sum(score_i * i) / sum(i)          over all levels i of that game
        (clamped to max_weights/total_weights*100, which only binds if everything is solved)
    overall:
        score = mean(game_score over games)

    Consequences that drive strategy:
      * `actions_i` includes RESETS that are not full resets (Card.inc_reset_count also
        bumps `actions`), so RESET-then-retry silently taxes whichever level it lands in.
      * Level 1 carries weight 1 of sum(1..L). For a 7-level game that is 1/28, so
        completing ONLY level 1 at human efficiency is worth 100/28 = 3.57 -- and the
        published top-10% cut is 3.80. Solving level 1 of every game is the whole game.
      * Beating the human baseline is possible and caps at 115 (LS20 L1: human 22, optimum 13).

Usage:
    .venv\\Scripts\\python.exe score_local.py --agent goose
    .venv\\Scripts\\python.exe score_local.py --agent installed --games ls20,sp80
    .venv\\Scripts\\python.exe score_local.py --agent ..\\agents\\planner_agent.py --max-steps 80
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import sys
import time
from pathlib import Path

# ⚠️ This tool lives in tools/ but drives the vendored upstream clone in starter/.
ROOT = Path(__file__).resolve().parents[1] / "starter"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor" / "ARC-AGI-3-Agents"))

# Pin directories to ABSOLUTE paths and force OFFLINE: the engine defaults
# environments_dir to the cwd-relative "environment_files", and NORMAL/ONLINE
# re-fetch the game list from the API on every Arcade(), which fails on a network
# hiccup and makes a local CV non-reproducible.
ENV_DIR = ROOT / "environment_files"
WORK = Path(__file__).resolve().parents[1] / "work"
import os as _os  # noqa: E402
_os.environ["OPERATION_MODE"] = "offline"
_os.environ["ENVIRONMENTS_DIR"] = str(ENV_DIR)

import arc_agi                                            # noqa: E402
from arc_agi import OperationMode                         # noqa: E402

ALIASES = {"installed": ROOT / "agent" / "my_agent.py",
           "goose": ROOT / "agent" / "goose_agent.py"}


def load_class(which: str):
    """Load `MyAgent` from an alias or a file path. Agents use `from agents.agent import
    Agent`, which needs starter/vendor/ARC-AGI-3-Agents on sys.path (done above)."""
    p = ALIASES.get(which)
    if p is None:
        p = Path(which)
        if not p.is_absolute():
            p = (Path(__file__).resolve().parent / p).resolve()
    if not p.exists():
        raise SystemExit("agent not found: %s  (aliases: %s)" % (p, sorted(ALIASES)))
    spec = importlib.util.spec_from_file_location("scored_agent_module", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.MyAgent, p


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="goose",
                    help="alias (installed|goose) or path to a .py exposing MyAgent")
    ap.add_argument("--games", default="", help="comma-separated subset, e.g. ls20,sp80")
    ap.add_argument("--max-steps", type=int, default=80,
                    help="MAX_ACTIONS; the competition ships 80 (Agent.MAX_ACTIONS)")
    ap.add_argument("--json", default="", help="also write full per-level detail here")
    a = ap.parse_args()

    logging.disable(logging.CRITICAL)          # the engine logs per action; 25 games is deafening

    cls, path = load_class(a.agent)
    cls.MAX_ACTIONS = a.max_steps

    arc = arc_agi.Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=str(ENV_DIR),
        recordings_dir=str(WORK / "recordings"),
    )
    infos = {e.game_id.split("-")[0]: e for e in arc.get_environments()}
    ids = sorted(infos)
    if a.games:
        want = {g.strip() for g in a.games.split(",")}
        ids = [g for g in ids if g in want]
    if not ids:
        raise SystemExit("no games selected; available: %s" % sorted(infos))

    card_id = arc.open_scorecard(tags=["score_local", a.agent])
    print("agent=%s  steps=%d  games=%d  card=%s" % (path.name, a.max_steps, len(ids), card_id))

    t0 = time.time()
    rows = []
    for i, gid in enumerate(ids, 1):
        env = arc.make(gid, seed=0, scorecard_id=card_id)
        if env is None:
            rows.append((gid, "NO_ENV", 0, 0, ""))
            print("  [%2d/%2d] %-5s NO_ENV" % (i, len(ids), gid), flush=True)
            continue
        ag = cls(card_id=card_id, game_id=gid, agent_name="score_local.%s" % gid,
                 ROOT_URL="http://localhost", record=False, arc_env=env, tags=["score_local"])
        err = ""
        try:
            ag.main()
        except Exception as e:                                  # a crash must not void the sweep
            err = "%s: %s" % (type(e).__name__, e)
        fin = ag.frames[-1] if ag.frames else None
        lv = int(getattr(fin, "levels_completed", 0) or 0)
        st = str(getattr(fin, "state", "?"))
        rows.append((gid, st, lv, ag.action_counter, err))
        print("  [%2d/%2d] %-5s levels=%d actions=%-3d %s %s"
              % (i, len(ids), gid, lv, ag.action_counter, st, err[:60]), flush=True)

    esc = arc.close_scorecard(card_id)
    if esc is None:
        raise SystemExit("close_scorecard returned None -- scorecard was not populated")

    # ── the number the leaderboard would show ────────────────────────────────
    print()
    print("=" * 78)
    print("%-6s %7s %7s %8s %10s   %s" % ("game", "score", "levels", "actions", "baseline", "per-level scores"))
    print("-" * 78)
    detail = {}
    for env_score in sorted(esc.environments, key=lambda e: e.id):
        # ⚠️ Use env_score.id, NOT run.id: `EnvironmentScoreCalculator.to_score()` builds its
        # EnvironmentScore without an `id` (only the early-return paths set one), so `run.id`
        # is None on the normal path and `run.id.split(...)` crashed the first version.
        run = max(env_score.runs, key=lambda r: r.score)
        gid = env_score.id.split("-")[0]
        base = run.level_baseline_actions or []
        lsc = run.level_scores or []
        detail[gid] = {"score": run.score, "levels_completed": run.levels_completed,
                       "actions": run.actions, "level_scores": lsc,
                       "level_actions": run.level_actions,
                       "level_baseline_actions": base}
        print("%-6s %7.2f %7d %8d %10s   %s"
              % (gid, run.score, run.levels_completed, run.actions,
                 "+".join(str(b) for b in base) or "-",
                 " ".join("%.0f" % s for s in lsc) or "-"))
    print("-" * 78)
    solved = [d for d in detail.values() if d["levels_completed"]]
    print("OVERALL score = %.4f    (competition metric, mean over %d games)"
          % (esc.score, len(esc.environments)))
    print("games with >=1 level: %d / %d      total levels: %d      total actions: %d"
          % (len(solved), len(esc.environments), esc.total_levels_completed, esc.total_actions))
    print("wall time: %.0f s" % (time.time() - t0))

    if a.json:
        outp = Path(a.json)
        if not outp.is_absolute():
            outp = WORK / outp
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(json.dumps({"agent": str(path), "max_steps": a.max_steps,
                                    "overall_score": esc.score, "games": detail},
                                   indent=2), encoding="utf-8")
        print("wrote %s" % outp)


if __name__ == "__main__":
    main()
