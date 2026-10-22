"""Calibrate the offline benchmark against the leaderboard.

The whole research plan depends on one question: does a Save run's benchmark.json produce a number that
tracks the leaderboard score? If it does, we can A/B prompt and scaffold changes for free (GPU time only) and
spend a draw only on the winner. If it does not, every experiment costs a draw and the program is dead.

We have one calibration point: the kernel last ran on 2026-10-13 and our submissions on 10-13 and 10-14
scored 23.51 and 26.41. So compute several candidate aggregates from the saved benchmark.json and see which
lands in that neighbourhood. It is one point, so agreement is suggestive and not proof -- but disagreement
would be decisive.

Reads scratch/diag/benchmark.json; writes nothing.
"""
import collections
import json
import statistics as st
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
P = r'D:\kaggle\arc\scratch\diag\benchmark.json'
d = json.load(open(P, encoding='utf-8'))
runs = d['game_runs']
print('label=%s solver=%s n_passes=%s runs=%d' % (d.get('label'), d.get('solver_label'),
                                                 d.get('n_passes'), len(runs)))
print('started %s ended %s' % (d.get('start_time'), d.get('end_time')))

# group by pass: the runs are ordered, n_passes passes over the same games
by_game = collections.defaultdict(list)
for r in runs:
    by_game[r['game_id']].append(r)

n_games = len(by_game)
n_passes = len(runs) // n_games if n_games else 0
print('distinct games=%d  passes=%d' % (n_games, n_passes))

levels = [(r.get('levels_completed') or 0, r.get('number_of_levels') or 0) for r in runs]
frac = [a / b for a, b in levels if b]

candidates = {
    'mean(levels_completed)': st.mean([a for a, _ in levels]),
    'mean(levels/number_of_levels)': st.mean(frac) if frac else 0,
    'sum(levels)/sum(number_of_levels)': (sum(a for a, _ in levels) / sum(b for _, b in levels)
                                          if any(b for _, b in levels) else 0),
    'mean(final_score)': st.mean([r.get('final_score') or 0 for r in runs]),
    'sum(final_score) per pass': sum(r.get('final_score') or 0 for r in runs) / max(n_passes, 1),
}
print('\ncandidate aggregates:')
for name, val in candidates.items():
    print('  %-38s %.3f' % (name, val))

print('\nleaderboard, same period: 57376299? no -- 10-13 = 23.51, 10-14 = 26.41')

# the 0-100 reading: if levels/number_of_levels is the per-game fraction, is the score its mean*100?
if frac:
    print('\nif the submission score is 100 x mean(levels/number_of_levels): %.2f' % (100 * st.mean(frac)))
    per_pass = []
    for p in range(n_passes):
        chunk = [r for i, r in enumerate(runs) if i // n_games == p]
        f = [(c.get('levels_completed') or 0) / (c.get('number_of_levels') or 1) for c in chunk]
        per_pass.append(100 * st.mean(f) if f else 0)
    print('per pass: %s' % ', '.join('%.2f' % x for x in per_pass))
    print('mean of passes: %.2f   sd: %.2f' % (st.mean(per_pass), st.stdev(per_pass) if len(per_pass) > 1 else 0))
