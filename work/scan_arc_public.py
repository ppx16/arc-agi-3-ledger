"""Sweep the public ARC-AGI-3 surface, including the top teams' own accounts.

WHY THIS SHAPE
    For Kaggriculture the same sweep found the single most useful lead of the day -- `aurax7`, the ONLY
    top-30 team with public notebooks -- because the leaderboard ships `TeamMemberUserNames`, so a top
    team can be mapped to a Kaggle account and its public kernels listed directly. That is a different
    search from "sort all notebooks by votes", and it is the one that finds a strong private-team
    artifact. Both are run here.

    ⚠️ And a lesson from the same sweep: a notebook TITLE is not evidence. `kaggriculture-2887-score-...`
    claimed 2887 and lost 10-2, `the-2950-peak-farm` lost 6-2. Titles only choose what to test.

Usage:
    python work/scan_arc_public.py [--top 30]
"""
from __future__ import annotations

import argparse
import csv
import pathlib
import sys
import zipfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from kaggle.api.kaggle_api_extended import KaggleApi

ROOT = pathlib.Path(__file__).resolve().parents[1]
COMP = "arc-prize-2026-arc-agi-3"
SEARCHES = ("arc agi 3", "arc-agi-3", "arcprize 2026", "arc agi")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=30)
    a = ap.parse_args()
    api = KaggleApi()
    api.authenticate()

    seen: set[str] = set()
    for label, kw in (("newest", dict(sort_by="dateRun")),
                      ("top-voted", dict(sort_by="voteCount"))):
        for q in SEARCHES:
            try:
                ks = api.kernels_list(search=q, page_size=40, **kw)
            except Exception as e:
                print("!! %s/%s failed: %s" % (label, q, type(e).__name__))
                continue
            new = [k for k in ks if (getattr(k, "ref", "") or "") not in seen]
            if not new:
                continue
            print("\n=== %s  search=%r  (%d new) ===" % (label, q, len(new)))
            for k in new:
                seen.add(getattr(k, "ref", "") or "")
                print("  %-19s v%-5s %-58s %s" % (str(getattr(k, "last_run_time", ""))[:19],
                                                  getattr(k, "total_votes", ""),
                                                  (getattr(k, "ref", "") or "")[:58],
                                                  (getattr(k, "title", "") or "")[:44]))

    # ── the top teams' own accounts ─────────────────────────────────────────────────────────────
    zips = sorted((ROOT / "lb5").glob("*.zip")) if (ROOT / "lb5").exists() else []
    if not zips:
        print("\n!! no cached ARC leaderboard under lb5/ -- run a leaderboard download first")
        return 0
    with zipfile.ZipFile(zips[-1]) as z:
        nm = [n for n in z.namelist() if n.endswith(".csv")][0]
        rows = list(csv.DictReader(z.read(nm).decode("utf-8-sig").splitlines()))
    rows.sort(key=lambda r: int(r.get("Rank", 10 ** 9)))
    print("\n=== TOP %d TEAMS' PUBLIC ARC NOTEBOOKS ===" % a.top)
    hits = 0
    for r in rows[: a.top]:
        users = [u.strip() for u in (r.get("TeamMemberUserNames") or "").replace('"', "").split(",")
                 if u.strip()]
        for u in users:
            try:
                ks = api.kernels_list(user=u, page_size=40)
            except Exception:
                continue
            rel = [k for k in ks
                   if "arc" in ((getattr(k, "ref", "") or "") + (getattr(k, "title", "") or "")).lower()]
            if not rel:
                continue
            hits += 1
            print("\n  rank %-5s score %-8s  %s" % (r["Rank"], r["Score"], u))
            for k in rel:
                print("     %-19s v%-5s %-54s %s" % (str(getattr(k, "last_run_time", ""))[:19],
                                                     getattr(k, "total_votes", ""),
                                                     (getattr(k, "ref", "") or "")[:54],
                                                     (getattr(k, "title", "") or "")[:40]))
    print("\nteams in the top %d with a public ARC notebook: %d" % (a.top, hits))
    return 0


if __name__ == "__main__":
    sys.exit(main())
