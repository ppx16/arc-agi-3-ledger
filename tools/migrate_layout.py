"""Give the ARC workspace its own repo and move the tools out of the upstream clone.

WHY
    `D:\kaggle\arc\starter\` is a CLONE of arcprize/ARC-AGI-3-Kaggle-Starter, so it is the only git
    repo in the tree. Every commit I made went there, which had two consequences I did not notice
    until a commit staged nothing:

      1. `D:\kaggle\arc\FINDINGS.md` and `STATUS.md` are OUTSIDE that repo and were **never
         committed** -- 16 KB of measured results sitting untracked next to the code that produced
         them.
      2. My own tools were being committed INTO a third-party clone, mixing my work with upstream's
         history so `git log` no longer separates them.

    The fix mirrors the sibling `kaggriculture` workspace: the workspace root becomes its own repo,
    the upstream clone is vendored and ignored, and our tools live in `tools/` with an explicit
    pointer at the starter they drive.

Usage:
    D:\\python\\python.exe migrate_layout.py
"""
from __future__ import annotations

import pathlib
import re
import shutil
import sys

ARC = pathlib.Path(__file__).resolve().parent
STARTER = ARC / 'starter'
TOOLS = ARC / 'tools'

MOVED = ['probe.py', 'watch.py', 'solve.py', 'solve_levels.py', 'bench.py',
         'block_track.py', 'click_map.py', 'click_probe.py', 'fetch_public_outputs.py']

# The scripts locate the starter via ROOT = the directory they sit in. Once they move to tools/,
# ROOT must point at ../starter instead. This is a targeted rewrite: it replaces the two-line
# header that every tool shares, and REFUSES if the pattern is not found, so a silent half-migration
# cannot happen.
HEADER_RE = re.compile(
    r'ROOT = Path\(__file__\)\.resolve\(\)\.parent\n'
    r'sys\.path\.insert\(0, str\(ROOT\)\)\n'
    r'sys\.path\.insert\(0, str\(ROOT / "vendor" / "ARC-AGI-3-Agents"\)\)\n'
)
NEW_HEADER = (
    '# ⚠️ This tool lives in tools/ but drives the vendored upstream clone in starter/.\n'
    '# ROOT is the STARTER directory on purpose: the scripts reference ROOT/agent/my_agent.py,\n'
    '# ROOT/vendor/... and ROOT/environment_files, all of which belong to the starter kit.\n'
    'ROOT = Path(__file__).resolve().parents[1] / "starter"\n'
    'sys.path.insert(0, str(ROOT))\n'
    'sys.path.insert(0, str(ROOT / "vendor" / "ARC-AGI-3-Agents"))\n'
)


def main() -> int:
    TOOLS.mkdir(exist_ok=True)
    moved, skipped = [], []
    for name in MOVED:
        src, dst = STARTER / name, TOOLS / name
        if not src.is_file():
            skipped.append(name)
            continue
        text = src.read_text(encoding='utf-8')
        new, n = HEADER_RE.subn(NEW_HEADER, text)
        if n != 1:
            print('!! %-24s header pattern matched %d times -- NOT moved' % (name, n))
            skipped.append(name)
            continue
        # assert the import order still holds after the rewrite
        assert 'sys.path.insert' in new and 'ARC-AGI-3-Agents' in new, name
        dst.write_text(new, encoding='utf-8')
        src.unlink()
        moved.append(name)

    print('moved  : %s' % ', '.join(moved) if moved else 'moved  : (none)')
    print('skipped: %s' % (', '.join(skipped) if skipped else '(none)'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
