"""Summarise a pulled notebook: what does it actually do, and what does it need at rerun time?

Prints, per cell: the type, and for markdown the text; for code a short head plus a scan for the
things that decide whether we can reuse it -- imports, any model/LLM reference, dataset reads, and
whether it writes a submission.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

KEYS = ("import ", "from ", "pip install", "Qwen", "qwen", "vllm", "transformers", "torch",
        "/kaggle/input", "dataset", "submission", "main.py", "duck", "MAX_ACTIONS", "llm",
        "openai", "cursor", "tinker")


def main() -> int:
    p = pathlib.Path(sys.argv[1])
    arg = sys.argv[2] if len(sys.argv) > 2 else "all"
    nb = json.loads(p.read_text(encoding="utf-8"))
    cells = nb.get("cells", [])
    print("notebook %s : %d cells" % (p.name, len(cells)))
    counts: dict[str, int] = {}
    for c in cells:
        counts[c.get("cell_type", "?")] = counts.get(c.get("cell_type", "?"), 0) + 1
    print("cell types: %s" % counts)
    hits: dict[str, int] = {}
    for c in cells:
        src = "".join(c.get("source", []))
        for k in KEYS:
            if k in src:
                hits[k] = hits.get(k, 0) + 1
    print("keyword cells: %s" % dict(sorted(hits.items(), key=lambda kv: -kv[1])))
    shown = 0
    for i, c in enumerate(cells):
        src = "".join(c.get("source", []))
        ct = c.get("cell_type")
        if arg == "md" and ct != "markdown":
            continue
        if arg == "code" and ct != "code":
            continue
        head = src.strip().splitlines()
        body = "\n".join(head[:12])
        if len(body) > 700:
            body = body[:700] + "\n    ..."
        print("\n----- cell %d [%s] (%d chars) -----\n%s" % (i, ct, len(src), body))
        shown += 1
        if shown >= 25:
            print("\n... (truncated)")
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
