"""Final content scan over everything staged for the ledger repo."""
import pathlib
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

files = subprocess.run(["git", "diff", "--cached", "--name-only"],
                       capture_output=True, text=True).stdout.split()
files = [f for f in files if f.endswith((".md", ".py", ".txt", ".json", ".csv", ".log", ".jsonl"))]
print("scanning %d text files" % len(files))

PATS = {
    "hardcoded key":    r"(?i)(api[_-]?key|auth[_-]?token|secret|password)\s*[:=]\s*[\"'][A-Za-z0-9_\-]{16,}",
    "windows userpath": r"[A-Za-z]:[\\/]+Users[\\/]+[A-Za-z0-9_.\-]+",
    "ID number":        r"(?<![0-9A-Za-z])\d{17}[\dXx](?![0-9A-Za-z])",
    "github token":     r"gh[pousr]_[A-Za-z0-9]{20,}",
    "kaggle token":     r"KGAT_[A-Za-z0-9]{20,}",
}

hits = {k: [] for k in PATS}
for f in files:
    try:
        t = pathlib.Path(f).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    for k, p in PATS.items():
        for m in re.finditer(p, t):
            hits[k].append((f, m.group(0)[:70]))

for k, v in hits.items():
    print("%-18s %d" % (k, len(v)))
    for f, s in v[:5]:
        print("      %s : %s" % (f, s))
