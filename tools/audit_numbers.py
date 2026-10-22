"""Audit the ARC ledger for stale "best score" claims -- with a self-test so it cannot pass vacuously.

The first version of this file examined zero claims and reported success, which is the exact instrument
failure LESSONS.md describes: a check that cannot fail is not a check. So this version (a) matches both word
orders, (b) proves on a built-in probe that it does match, and (c) refuses to report a clean result unless it
examined at least one real claim.

Reads the submissions table for the truth; writes nothing.
Exit 0 = clean and actually performed, exit 1 = contradiction, exit 2 = the audit itself did not work.

Usage: python work/audit_numbers.py
"""
import csv
import io
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = Path(__file__).resolve().parents[1]
# this script lives in the WORKING directory (D:\kaggle\arc), not in the ledger repository, so parents[1]
# points at the working tree and the first run scanned five unrelated files and reported "examined nothing".
# The ledger is a separate checkout; point at it explicitly rather than inferring from __file__.
LEDGER = Path(r'D:\kaggle\arc-agi-3-ledger')
if not (LEDGER / 'findings').is_dir():
    raise SystemExit('the ledger checkout is not at %s -- fix LEDGER before trusting any verdict' % LEDGER)

BESTY = re.compile(r'(best|最高|top score|our score)', re.I)
SCORE = re.compile(r'\b([2-6]\d\.\d{1,2})\b')
HISTORY = re.compile(r'(此前|当时|曾|previous|earlier|was |历史|old |then |第\s*\d+\s*次|draw\s*\d|抽样|'
                     r'superseded|before the)', re.I)

PROBES = [
    ('our best is 28.98 now', True),
    ('最高 26.41', True),
    ('the eleven draws: 22.48 24.53 29.34', False),
    ('best public score = 29.34', True),
]


def truth() -> dict:
    r = subprocess.run(['kaggle', 'competitions', 'submissions',
                        '-c', 'arc-prize-2026-arc-agi-3', '--csv'],
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=900)
    lines = ((r.stdout or '') + (r.stderr or '')).splitlines()
    start = next((i for i, l in enumerate(lines) if l.lstrip('\ufeff').startswith('ref,')), None)
    if start is None:
        raise SystemExit('cannot read the submissions table')
    rows = list(csv.DictReader(io.StringIO('\n'.join(lines[start:]))))
    scored = [(float(x['publicScore']), x['ref']) for x in rows if (x.get('publicScore') or '').strip()]
    pend = [(x['ref'], (x.get('status') or '').replace('SubmissionStatus.', ''))
            for x in rows if 'PENDING' in (x.get('status') or '')]
    return {'best': max(scored)[0], 'best_ref': max(scored)[1], 'n': len(rows),
            'pending': pend, 'scores': sorted({s for s, _ in scored}, reverse=True)}


def is_claim(line: str) -> bool:
    return bool(BESTY.search(line) and SCORE.search(line))


def self_test() -> int:
    bad = 0
    for text, want in PROBES:
        got = is_claim(text)
        flag = 'ok  ' if got == want else 'FAIL'
        if got != want:
            bad += 1
        print('  %s is_claim(%-42r) = %s (wanted %s)' % (flag, text, got, want))
    return bad


def main() -> int:
    print('self-test:')
    if self_test():
        print('RESULT: the matcher does not behave on known probes -- fix it before trusting any verdict')
        return 2

    t = truth()
    print('\ntruth: best %.2f (%s), %d submissions, pending=%s'
          % (t['best'], t['best_ref'], t['n'], t['pending'] or 'none'))
    print('scores on record: %s' % ', '.join('%.2f' % s for s in t['scores'][:8]))

    # Only live documents are instructions. A finding called F60-... or a STATUS dated 10-14 is a record of
    # what was true then; quoting that day's best score is not an error, it is the point of a log. Two
    # narrower filters also matter: a number only counts as a claim about OUR best if it is one of the scores
    # we actually recorded, and other people's maxima (34.30 on franzen's notebook) are not our claims at all.
    files = [LEDGER / 'README.md', LEDGER / 'STATUS.md']
    ours = {round(s, 2) for s in t['scores']}
    files = [p for p in files if p.is_file()]
    examined = 0
    problems = 0
    for p in files:
        try:
            txt = p.read_text(encoding='utf-8', errors='replace')
        except Exception:  # noqa: BLE001
            continue
        bad = []
        for line_no, line in enumerate(txt.splitlines(), 1):
            if not is_claim(line):
                continue
            examined += 1
            for m in SCORE.finditer(line):
                val = float(m.group(1))
                if abs(val - t['best']) < 1e-9:
                    continue
                if round(val, 2) not in ours:   # not one of our scores -> not a claim about us
                    continue
                if HISTORY.search(line):
                    continue
                bad.append((line_no, val, line.strip()))
                break
        if bad:
            problems += 1
            print('\n!! %s' % p.relative_to(LEDGER))
            for line_no, val, line in bad[:5]:
                print('   L%-5d says %s where the best is %.2f  %s' % (line_no, val, t['best'], line[:120]))

    print('\nclaims examined: %d across %d documents' % (examined, len(files)))
    if examined == 0:
        print('RESULT: examined nothing -- the matcher is too narrow to be a check (exit 2)')
        return 2
    if problems:
        print('RESULT: %d document(s) state a score other than %.2f without marking it as history'
              % (problems, t['best']))
        return 1
    print('RESULT: every best-score claim either matches %.2f or is marked as history' % t['best'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
