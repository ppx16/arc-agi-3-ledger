"""Install a tracked agent into the vendored starter's agent/ slot, so the notebook build picks it up.

WHY THIS EXISTS
    `starter/` is a CLONE of the upstream kit and is gitignored, so anything living there is NOT
    committed -- and `agent/my_planner_agent.py` was written straight into it, meaning the one artifact
    this whole investigation produced would have been invisible to git. (Same failure family as the
    root repo not existing at all: the work is real but untracked.)

    So the authoritative copy lives in `agents/` (tracked) and this script copies it into
    `starter/agent/my_agent.py`, which is the single file `scripts/build_notebook.py` splices into the
    submission notebook.

Usage:
    D:\\python\\python.exe install_agent.py planner_agent.py
    D:\\python\\python.exe install_agent.py planner_agent.py --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent
AGENTS = ROOT / 'agents'
TARGET = ROOT / 'starter' / 'agent' / 'my_agent.py'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('name', nargs='?', default='planner_agent.py')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    src = AGENTS / a.name
    if not src.is_file():
        print('!! no such agent: %s' % src)
        return 2
    payload = src.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()[:16]
    TARGET.parent.mkdir(parents=True, exist_ok=True)

    if a.dry_run:
        print('would install %s -> %s  (sha256[:16]=%s, %d bytes)'
              % (src.name, TARGET, digest, len(payload)))
        return 0

    shutil.copyfile(src, TARGET)
    # assert the property that matters: the installed file is byte-identical to the tracked one
    got = hashlib.sha256(TARGET.read_bytes()).hexdigest()[:16]
    assert got == digest, 'installed copy differs: %s != %s' % (got, digest)
    print('installed %s -> %s  (sha256[:16]=%s)' % (src.name, TARGET, digest))
    print('build the notebook with:  starter/.venv/Scripts/python scripts/build_notebook.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
