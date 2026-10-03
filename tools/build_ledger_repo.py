"""Build the public `arc-agi-3-ledger` repo from the local ARC-AGI-3 workspace.

WHY A CURATED COPY
    The workspace is ~1.1 GB and almost all of it is somebody else's code:
      * `starter/`            920 MB, 31 511 files -- the vendored competition starter + installed
                              packages (187 MB of `.pyc`, 53 MB of `.pyd`, 157 MB of `.py`);
      * `research/openworld`  144 MB, 4 903 files -- a vendored environment framework;
      * `research/aera-arc3-paper` 1.4 MB -- a third-party paper (not ours to republish);
      * `comp/`               42 MB -- competition data;
      * `arc-prize-2026-arc-*.zip` -- competition data at the root.
    Globbing would sweep all of that in. This script copies from an explicit allowlist and prints
    everything it refuses, so the content boundary is auditable.

WHAT ACTUALLY BELONGS HERE (all of it is ours)
    * `FINDINGS.md` (F1-F43) + `FINDINGS-F44.md` + `FINDINGS-F45.md` + `FINDINGS-F46.md` -- the ledger itself;
    * `STATUS.md`, `cm.txt` -- the running state and the metric-harness notes;
    * `agents/` -- the nine agents this project wrote (goose, goose-no-level-reset, hybrid,
      portfolio, novelty, cycle, planner, generic);
    * `tools/` -- twenty probe/solve/score utilities;
    * `work/` -- the probe kernels' scripts and their captured logs, i.e. the raw evidence behind
      the findings;
    * `lb3|lb4|lb5/` -- three public-leaderboard CSV snapshots at three timestamps. Small, and they
      are the only objective record of where the field stood on those dates. Unzipped, since git
      should store the text, not the archive.

Usage:  python build_ledger_repo.py [--check] [--repo DIR]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sys
import zipfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SRC = pathlib.Path(r"D:\kaggle\arc")
REPO_DEFAULT = pathlib.Path(r"D:\kaggle\arc-agi-3-ledger")

# directories that are vendored / third-party / data -- never copied
DROP_TOP = {"starter", "research", "comp", "data", ".git", "__pycache__", "work\\__pycache__"}

# ⚠️ SUBTREES THAT HOLD OTHER PEOPLE'S WORK. These were pulled from Kaggle while surveying the
# field and are NOT ours to republish -- the same rule applied to the CDA repo. Their *findings*
# are recorded in our own words in findings/F45-what-others-do.md, which is what belongs here.
#   work/duck9    -- the rank-5  "LB-9 arc3 duck v12 with Qwen 3.8 27B" notebook
#   work/nonduck  -- 8 more third-party notebooks (sovereign-agent, chimpanzee, milestone-1, ...)
#   work/pub_arc  -- further pulled public ARC notebooks
DROP_SUBTREES = ["work/duck9", "work/nonduck", "work/pub_arc",
                 # redundant: lb3/lb4/lb5 already ship three leaderboard snapshots as text
                 "work/lb",
                 # 65 zero-byte placeholder logs, no content
                 "tools/runs",
                 # ⚠️ never copy: a whole pip-installed venv + a downloaded wheel tree, and the
                 # captured probe log that once contained live kernel JWTs (now scrubbed, but the
                 # safe rule is to keep accelerator-probe output out of the published tree).
                 "work/kgvenv", "work/kgcli", "work/probe-nb-out",
                 "tools/__pycache__", "work/__pycache__"]

# our own top-level files, mapped to their destination path in the repo
ROOT_FILES: dict[str, str] = {
    "FINDINGS.md":            "findings/FINDINGS.md",
    "FINDINGS-F44.md":        "findings/F44-hardware-wall.md",
    "FINDINGS-F45.md":        "findings/F45-what-others-do.md",
    "FINDINGS-F46.md":        "findings/F46-accelerator-push-path.md",
    "STATUS.md":              "STATUS.md",
    "cm.txt":                 "findings/metric-harness-notes.md",
    "build_hybrid.py":        "tools/build_hybrid.py",
    "install_agent.py":       "tools/install_agent.py",
    "migrate_layout.py":      "tools/migrate_layout.py",
    "pin_dirs.py":            "tools/pin_dirs.py",
    "repair_findings.py":     "tools/repair_findings.py",
}

# whole directories copied verbatim under the repo root
COPY_DIRS = ["agents", "tools", "work"]

# names that must never appear in a published path
PII_PATTERNS = [r"\d{17}[\dXx]"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=pathlib.Path, default=REPO_DEFAULT)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    if not SRC.is_dir():
        print("!! source not found: %s" % SRC)
        return 2
    repo: pathlib.Path = a.repo

    kept: list[tuple[str, pathlib.Path, int]] = []
    skipped: list[tuple[str, str]] = []

    def consider(f: pathlib.Path, dest: str) -> None:
        if any(re.search(p, f.name) for p in PII_PATTERNS):
            skipped.append((str(f.relative_to(SRC)), "PERSONAL DATA IN FILENAME"))
            return
        if f.stat().st_size > 8 * 1024 * 1024:
            skipped.append((str(f.relative_to(SRC)), "too big (%.1f MB)" % (f.stat().st_size / 1e6)))
            return
        kept.append((dest, f, f.stat().st_size))

    for name, dest in ROOT_FILES.items():
        f = SRC / name
        if f.is_file():
            consider(f, dest)
        else:
            print("!! expected root file missing: %s" % f)

    drop_set = {s.replace("\\", "/") for s in DROP_SUBTREES}
    for d in COPY_DIRS:
        root = SRC / d
        if not root.is_dir():
            print("!! expected dir missing: %s" % root)
            continue
        for f in sorted(root.rglob("*")):
            if not f.is_file():
                continue
            rel = "%s/%s" % (d, str(f.relative_to(root)).replace("\\", "/"))
            top2 = "/".join(rel.split("/")[:2])
            if top2 in drop_set:
                skipped.append((str(f.relative_to(SRC)), "THIRD-PARTY / redundant subtree"))
                continue
            if any(part in rel for part in drop_set):
                skipped.append((str(f.relative_to(SRC)), "dropped subtree"))
                continue
            if "__pycache__" in f.parts or f.suffix in (".pyc", ".pyo"):
                skipped.append((str(f.relative_to(SRC)), "bytecode"))
                continue
            consider(f, rel)

    # leaderboard snapshots: unzip, do not ship the archives
    for d in ("lb3", "lb4", "lb5"):
        z = SRC / d / "arc-prize-2026-arc-agi-3.zip"
        if not z.is_file():
            print("!! leaderboard zip missing: %s" % z)
            continue
        with zipfile.ZipFile(z) as zf:
            for n in zf.namelist():
                if n.endswith("/"):
                    continue
                stem = pathlib.Path(n).stem
                stamp = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", stem)
                out = "leaderboard/%s.csv" % (stamp.group(1).replace(":", "") if stamp else stem)
                if a.check:
                    print("   would extract %s -> %s" % (n, out))
                    continue
                tmp = pathlib.Path(repo) / out
                tmp.parent.mkdir(parents=True, exist_ok=True)
                tmp.write_bytes(zf.read(n))
                kept.append((out, z, len(zf.read(n))))

    total = sum(s for _, _, s in kept)
    print("KEEP %d files, %.2f MB" % (len(kept), total / 1e6))
    top: dict[str, int] = {}
    for dest, _, _ in kept:
        top[dest.split("/")[0]] = top.get(dest.split("/")[0], 0) + 1
    for k in sorted(top):
        print("   %-14s %4d files" % (k, top[k]))
    print("\nSKIP %d entries" % len(skipped))
    agg: dict[str, int] = {}
    for _, why in skipped:
        key = why.split(" (")[0]
        agg[key] = agg.get(key, 0) + 1
    for k in sorted(agg, key=lambda x: -agg[x]):
        print("   %-28s %4d" % (k, agg[k]))

    if a.check:
        print("\n--check: nothing written.")
        return 0

    for dest, f, _ in kept:
        if dest.startswith("leaderboard/"):
            continue          # already written during extraction
        out = repo / dest
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f, out)
    print("\nwrote into %s" % repo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
