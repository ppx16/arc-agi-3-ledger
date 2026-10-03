"""Bake the measured portfolio knobs into a standalone agent file for submission.

WHY: `agents/cycle_agent.py` reads ARC_POLICY / ARC_PORTFOLIO / ARC_PHASE from the ENVIRONMENT, and
the competition rerun has none. A submission therefore has to carry the settings as DEFAULTS, or it
silently runs the `cycle` policy (which scores 0.0000) instead of the portfolio.

⚠️ And the honest caveat that must travel with this file: roughly THIRTY configurations were scored
against the SAME 25 public games, and the winner was then read off. That is selection bias. The
chosen config is the best MEASURED, and two independent facts make it the defensible pick rather
than the argmax alone -- it solves 2 games (the joint most of any config), and it is a portfolio of
four distinct candidate orderings rather than a single fragile trick. But the deployed expectation
is the family's ~0.15-0.27, NOT the 0.2693 headline.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "agents" / "cycle_agent.py"
OUT = ROOT / "agents" / "portfolio_agent.py"

SUB = [
    (r'^POLICY = os\.environ\.get\("ARC_POLICY", "cycle"\)$',
     'POLICY = os.environ.get("ARC_POLICY", "portfolio")'),
    (r'^ARC_PHASE = int\(os\.environ\.get\("ARC_PHASE", "20"\)\)$',
     'ARC_PHASE = int(os.environ.get("ARC_PHASE", "20"))'),
    (r'^PORTFOLIO = \(os\.environ\.get\("ARC_PORTFOLIO", "rare,xy,area,colour"\) or ""\)\.split\(","\)$',
     'PORTFOLIO = (os.environ.get("ARC_PORTFOLIO", "dense,rare,xy,area") or "").split(",")'),
]


def main() -> int:
    src = SRC.read_text(encoding="utf-8")
    header = (
        '"""SUBMISSION AGENT: dense+rare+xy+area portfolio, 20 actions per phase.\n\n'
        'Measured through tools/score_local.py (the SHIPPED scorer against the real baselines),\n'
        'MAX_ACTIONS=80, all 25 public games: OVERALL 0.2693, 2/25 games with >=1 level.\n'
        '\n'
        'Generated from agents/cycle_agent.py by work/mk_submission_agent.py; the ONLY differences are\n'
        'the three baked-in defaults below. See FINDINGS F34 for the family and its caveats.\n'
        '"""\n'
    )
    out = src
    for pat, rep in SUB:
        out, n = re.subn(pat, rep, out, count=1, flags=re.M)
        if n != 1:
            raise SystemExit("!! pattern did not match exactly once: %s" % pat)
    # replace the module docstring with the submission header
    out = re.sub(r'^""".*?"""\n', header, out, count=1, flags=re.S)
    OUT.write_text(out, encoding="utf-8")
    compile(out, str(OUT), "exec")
    print("wrote %s (%d bytes)" % (OUT, len(out)))
    for line in out.splitlines():
        if line.startswith(("POLICY =", "ARC_PHASE =", "PORTFOLIO =")):
            print("   " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
