"""Does the "HUD counter changes every step" problem actually exist, per game?

WHY: the openworld harness notes claim a status-bar counter changes on ~every step, so hashing
the raw frame makes every step a brand-new state and exploration degenerates into a random walk.
That claim is load-bearing -- it is the stated reason raw-frame novelty search "explodes" -- and
`ARC_SIG_MODE=masked` produced BYTE-IDENTICAL results to `raw` on 8 games, which is only possible
if the mask never engaged. So measure it instead of believing it, per game.

Method: play a deterministic cycle through the game's legal actions, tracking per-cell change
frequency between consecutive frames. Report the number of cells that change on >95% of steps
(candidate HUD) and, crucially, the number of DISTINCT states under a raw hash vs a masked hash.
If they are equal, masking buys nothing on that game.

Usage:
    .venv\\Scripts\\python.exe mask_probe.py --steps 60
"""
from __future__ import annotations

import argparse
import hashlib
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
from arcengine import GameAction, GameState               # noqa: E402

FREQ = 0.95


def h(b: bytes) -> str:
    return hashlib.blake2b(b, digest_size=8).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=60)
    ap.add_argument("--games", default="")
    a = ap.parse_args()

    logging.disable(logging.CRITICAL)
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE,
                         environments_dir=str(ROOT / "environment_files"),
                         recordings_dir=str(ROOT.parent / "work" / "recordings"))
    ids = sorted(e.game_id.split("-")[0] for e in arc.get_environments())
    if a.games:
        want = {g.strip() for g in a.games.split(",")}
        ids = [g for g in ids if g in want]

    print("%-6s %-16s %5s %6s %8s %8s %6s  %s"
          % ("game", "available_actions", "steps", "hud", "raw_st", "msk_st", "ratio", "changed_any"))
    print("-" * 92)
    for gid in ids:
        env = arc.make(gid, seed=0)
        if env is None:
            continue
        acts = [GameAction.from_id(int(v)) for v in (env.observation_space.available_actions or [1])]
        prev = np.asarray(env.observation_space.frame)[0].astype(np.int16)
        chg = np.zeros(prev.shape, dtype=np.int32)
        raw_seen, msk_seen = set(), set()
        raw_seen.add(h(prev.tobytes()))
        obs = 0
        for i in range(a.steps):
            act = acts[i % len(acts)]
            o = env.step(act)
            if o is None:
                break
            cur = np.asarray(o.frame)[0].astype(np.int16)
            obs += 1
            chg += (prev != cur)
            prev = cur
            raw_seen.add(h(cur.tobytes()))
            m = (chg.astype(np.float32) / obs) > FREQ
            masked = np.where(m, np.int16(-1), cur)
            msk_seen.add(h(masked.tobytes()))
            if o.state is GameState.GAME_OVER:
                env.step(GameAction.RESET)
                prev = np.asarray(env.observation_space.frame)[0].astype(np.int16)
        m = (chg.astype(np.float32) / max(obs, 1)) > FREQ
        print("%-6s %-16s %5d %6d %8d %8d %6.3f  %s"
              % (gid, str([int(x) for x in (env.observation_space.available_actions or [])]),
                 obs, int(m.sum()), len(raw_seen), len(msk_seen),
                 (len(msk_seen) / len(raw_seen)) if raw_seen else 0.0,
                 int((chg > 0).sum())))


if __name__ == "__main__":
    main()
