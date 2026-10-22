"""Read what the agent said about the games it cannot solve.

The per-game diagnostics in benchmark.json carry the solver's own notes. Four or five games score near zero
on every pass (F84), and the useful question is not "which parameters differ" but "is there a systematic
reason" -- a tool that errors, a rule the prompt states wrongly, a game type the scaffold mishandles. That
would be fixable; a merely hard game is not.

Reads scratch/diag/benchmark.json; writes nothing.
"""
import collections
import json
import re
import statistics as st
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
d = json.load(open(r'D:\kaggle\arc\scratch\diag\benchmark.json', encoding='utf-8'))
runs = d['game_runs']

by_game = collections.defaultdict(list)
for r in runs:
    by_game[r['game_id']].append(r)

# rank games by how badly they do
rows = []
for g, rs in by_game.items():
    lv = [r.get('levels_completed') or 0 for r in rs]
    nl = rs[0].get('number_of_levels') or 0
    rows.append((st.mean(lv) / nl if nl else 0, g, lv, nl))
rows.sort()

print('%-14s %-6s %-16s %s' % ('game', 'maxlv', 'levels per pass', 'mean fraction'))
for frac, g, lv, nl in rows:
    print('%-14s %-6s %-16s %.2f' % (g, nl, str(lv), frac))

worst = [g for frac, g, lv, nl in rows if frac < 0.25]
print('\ngames below 25%% of their levels: %d  -> %s' % (len(worst), ', '.join(worst)))

print('\n' + '=' * 96)
for g in worst:
    rs = by_game[g]
    print('\n### %s   levels per pass %s   of %d' % (g, [r.get('levels_completed') for r in rs], rs[0].get('number_of_levels')))
    for r in rs[:1]:
        note = (r.get('solver_note') or '').strip()
        note = re.sub(r'\s+', ' ', note)
        print('  note: %s' % (note[:600] if note else '(empty)'))
        hints = (r.get('hint') or '')
        hints = re.sub(r'\s+', ' ', hints) if isinstance(hints, str) else str(hints)
        print('  hint: %s' % hints[:200])
        acts = r.get('actions_per_level')
        print('  actions per level: %s' % str(acts)[:160])
