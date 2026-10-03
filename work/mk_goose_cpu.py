"""Build the two submission variants of the goose-no-level-reset agent (F39).

WHY TWO
    `agents/goose_nolevel.py` keeps upstream's `MAX_ACTIONS = float('inf')`, which is exactly right
    but needs the accelerator the submission ran on. Our kernel currently has to be pushed with
    `enable_gpu: false`, because **Kaggle's weekly GPU quota is exhausted (30.45 h of 30.00,
    account-wide, refreshing 2026-10-03)** and a GPU kernel version cannot be created until then.

    ⚠️ CPU is not free: the official goose measured **0.498 s per action** here (25 games x 81
    actions = 1009 s). Unbounded on CPU is therefore hours, so the CPU variant bounds the game.

    ⇒ two files, so that no reading is confounded:
       `goose_nolevel.py`      MAX_ACTIONS = inf    -- the ONE-VARIABLE experiment vs upstream.
                                                    Submit once the GPU quota refreshes (>= 10-03).
       `goose_nolevel_cpu.py`  MAX_ACTIONS = 1000   -- CPU-safe. At 0.498 s/action that is
                                                    ~8 min/game, ~3.4 h for 25 games, and 1000
                                                    actions comfortably covers a full game (the
                                                    public games' per-level human baselines are
                                                    7-78 across 6-10 levels, so ~300-800 total).

    Both differ from upstream in the SAME one respect (the per-level learner reset); they differ
    from each other only in the cap, so the pair also measures the cap as a side effect.

Usage:
    python work/mk_goose_cpu.py
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "agents" / "goose_nolevel.py"
OUT = ROOT / "agents" / "goose_nolevel_cpu.py"
CAP = 1000


def main() -> int:
    src = SRC.read_text(encoding="utf-8")
    out, n = re.subn(r"^\s*MAX_ACTIONS\s*=\s*float\('inf'\)\s*$",
                     "    MAX_ACTIONS = %d          # CPU-safe bound; see work/mk_goose_cpu.py" % CAP,
                     src, count=1, flags=re.M)
    if n != 1:
        raise SystemExit("!! could not find the MAX_ACTIONS = float('inf') line (matched %d)" % n)
    out = out.replace(
        "Upstream: the official ARC-AGI-3 sample agent",
        "CPU-BOUND build (MAX_ACTIONS=%d). Upstream: the official ARC-AGI-3 sample agent" % CAP,
        1)
    OUT.write_text(out, encoding="utf-8")
    compile(out, str(OUT), "exec")
    for line in out.splitlines():
        if "MAX_ACTIONS" in line and "=" in line and "inf" not in line:
            print("   " + line.strip())
    print("wrote %s (%d bytes)" % (OUT, len(out)))
    assert "float('inf')" not in out
    return 0


if __name__ == "__main__":
    sys.exit(main())
