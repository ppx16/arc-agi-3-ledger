"""Extract the paths, solver references and install commands from a pulled notebook."""
from __future__ import annotations

import json
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PATS = [
    r"/kaggle/input/[^\s\"')]+",
    r"[A-Za-z_./]*solver[A-Za-z_./]*",
    r"pickle[^\n]{0,100}",
    r"subprocess\.run\(\[[^\]]{0,220}",
    r"pip install[^\n]{0,160}",
    r"bm\.[A-Za-z_]+",
]


def main() -> int:
    nb = json.loads(open(sys.argv[1], encoding="utf-8").read())
    txt = "\n".join("".join(c.get("source", [])) for c in nb.get("cells", []))
    print("total source chars: %d" % len(txt))
    for p in PATS:
        print("\n=== %s ===" % p)
        seen = []
        for m in re.findall(p, txt):
            if m not in seen:
                seen.append(m)
            if len(seen) >= 14:
                break
        for s in seen:
            print("   %s" % s[:190])
    return 0


if __name__ == "__main__":
    sys.exit(main())
