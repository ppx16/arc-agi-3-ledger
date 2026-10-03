"""Make the moved tools location-independent by pinning the engine's data directories.

WHY
    `Arcade(environments_dir=...)` defaults to the RELATIVE path `"environment_files"`, so it resolves
    against the current working directory. The cached game sources live in `starter/environment_files`,
    so every tool broke the moment it moved to `tools/`: `arc.make()` returned None and the failure
    surfaced as `AttributeError: 'NoneType' object has no attribute 'step'` -- a message that says
    nothing about directories, which is why it is worth fixing at the source.

    Both directories are overridable by environment variable, so the tools set them to ABSOLUTE paths
    derived from the starter location. That is better than `os.chdir()`, which would silently change
    where every other relative path in the process resolves.

Usage:
    D:\\python\\python.exe pin_dirs.py
"""
from __future__ import annotations

import pathlib

TOOLS = pathlib.Path(__file__).resolve().parent / 'tools'
ANCHOR = 'sys.path.insert(0, str(ROOT / "vendor" / "ARC-AGI-3-Agents"))\n'
INJECT = (
    'import os as _os_for_dirs                      # noqa: E402  (added by pin_dirs.py)\n'
    '# ⚠️ The engine defaults environments_dir to the RELATIVE "environment_files", so it resolves\n'
    '# against the cwd. These tools live in tools/ while the cache lives in starter/, so pin both\n'
    '# directories to ABSOLUTE paths here rather than chdir-ing (which would move every other\n'
    '# relative path in the process). Found the hard way: arc.make() returned None and surfaced as\n'
    '# "AttributeError: \'NoneType\' object has no attribute \'step\'".\n'
    '_os_for_dirs.environ.setdefault("ENVIRONMENTS_DIR", str(ROOT / "environment_files"))\n'
    '_os_for_dirs.environ.setdefault("RECORDINGS_DIR", str(ROOT / "recordings"))\n'
)


def main() -> int:
    done, skipped = [], []
    for p in sorted(TOOLS.glob('*.py')):
        t = p.read_text(encoding='utf-8')
        if 'ENVIRONMENTS_DIR' in t:
            skipped.append(p.name + ' (already pinned)')
            continue
        if ANCHOR not in t:
            skipped.append(p.name + ' (no anchor)')
            continue
        t2 = t.replace(ANCHOR, ANCHOR + INJECT, 1)
        assert 'ENVIRONMENTS_DIR' in t2
        compile(t2, str(p), 'exec')          # syntax gate before writing
        p.write_text(t2, encoding='utf-8')
        done.append(p.name)
    print('pinned : %s' % (', '.join(done) if done else '(none)'))
    print('skipped: %s' % (', '.join(skipped) if skipped else '(none)'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
