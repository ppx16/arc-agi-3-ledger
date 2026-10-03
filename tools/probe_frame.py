"""Print the raw frame format for a few games: shape, dtype, value range, layer count.

Needed before writing any pixel-level agent: whether `frame` is (H,W) colour indices or
(L,H,W) one-hot planes decides how a state signature and a click-candidate finder must work.
"""
from __future__ import annotations

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


def main() -> None:
    logging.disable(logging.CRITICAL)
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE,
                         environments_dir=str(ROOT / "environment_files"),
                         recordings_dir=str(ROOT.parent / "work" / "recordings"))
    for gid in (sys.argv[1:] or ["ls20", "sp80", "vc33", "cd82"]):
        env = arc.make(gid, seed=0)
        if env is None:
            print("%-6s NO ENV" % gid)
            continue
        o = env.observation_space
        f = np.array(o.frame)
        print("%-6s frame.shape=%-14s dtype=%-8s min=%-4s max=%-4s nlayers=%d"
              % (gid, f.shape, f.dtype, f.min(), f.max(), len(o.frame)))
        print("        state=%s levels=%s win_levels=%s full_reset=%s guid=%s"
              % (o.state, o.levels_completed, o.win_levels, o.full_reset, str(o.guid)[:8]))
        print("        available_actions=%s" % (o.available_actions,))
        if f.ndim == 3:
            print("        per-layer unique counts: %s"
                  % [len(np.unique(l)) for l in f])
            print("        layer0 uniques=%s" % (np.unique(f[0])[:20],))
        else:
            u, c = np.unique(f, return_counts=True)
            print("        uniques=%s" % dict(zip(u.tolist()[:20], c.tolist()[:20])))
        # one step, to see whether an action changes the frame and how `full_reset` behaves
        o2 = env.step(GameAction.from_id(1))
        f2 = np.array(o2.frame)
        print("        after A1: shape=%s changed=%s levels=%s state=%s"
              % (f2.shape, not np.array_equal(f, f2), o2.levels_completed, o2.state))


if __name__ == "__main__":
    main()
