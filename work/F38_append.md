
---

## F38. ⚠️ F37.3 is FALSIFIED as a lever, and the real structural fact is the PER-LEVEL accounting

Written 2026-09-30, immediately after F37. `agents/generic_agent.py` was built to fix the two defects
F37 identified. **One of them turns out not to matter, and the other turns out to be harmful.** Both
are recorded here rather than quietly dropped.

### 38.1 ⚠️ Raising the action cap changes NOTHING — measured, three widths x three caps

F37.3 argued that our self-imposed 80-action cap is a limitation, since the goose sets
`MAX_ACTIONS = inf`. Tested directly:

| click prior | cap 80 | cap 400 | cap 1200 |
|---|---|---|---|
| 12 candidates | **0.1905** (2 games) | **0.1905** | **0.1905** |
| 16 candidates | 0.0722 (1) | 0.0722 | 0.0722 |
| 48 candidates | 0.0000 (0) | 0.0000 | 0.0000 |

**Byte-identical scores at every cap** (and `total actions` rises 2025 → 10025 → 30025, so the extra
actions really are being spent). The reason is now obvious and it is the important part:

> The agents complete **level 1** inside 80 actions and **never complete level 2**. Extra actions are
> spent inside an *uncompleted* level, and §38.2 shows an uncompleted level contributes nothing. So
> there is no level whose score the extra actions could add to.

⇒ **The cap is self-imposed but not binding on the outcome.** F37.3's "an uncapped agent can still
earn partial credit" is **wrong in practice**: partial credit needs a level to *complete*, and the
budget was never what stopped it. Corrected in place; the 1200 default stays because it is free, not
because it helps.

### 38.2 ⭐⭐ The structural fact that actually governs everything: scoring is PER LEVEL

Through the shipped scorer on the two public games our agent wins:

```
r11l   total=81   level_actions=[27, 54, 0, ...]   level_scores=[66.4, 0, ...]   baselines=[22, 33, 51, 26, 52, 49]
tn36   total=81   level_actions=[30, 51, 0, ...]   level_scores=[113.8, 0, ...]  baselines=[32, 72, 26, 40, 30, 55, 62]
```

`27 + 54 = 81`, and `100*(22/27)**2 = 66.4`. So **`level_actions[i]` is the spend INSIDE level i, not
a running total**, and `score_i` depends only on that. Three consequences:

1. Actions burned **after** a level completes do **not** reduce its score.
2. Every level has its **own** budget, so reaching level 5 is not penalised by what level 1 cost.
3. **Later levels weigh MORE** (level *i* counts *i* of `sum(1..L)`).

⇒ **The competition is SEQUENTIAL LEVEL SOLVING, and level 1 — the only level any agent here ever
completes — is worth the LEAST.** A game where an agent does level 1 at human speed and level 2 at
human speed scores `100/21 + 2*100/21 = 14.3` for that game, i.e. **0.57 overall from ONE game**;
three such games would be ~1.7, or ~20× our current score. That is where the score is, and it is why
"a sliver of partial credit" (0.18) is all a level-1-only agent can ever reach.

### 38.3 ⚠️ A wider click space HURTS unless the agent LEARNS — so F36.2's "fix" is not one

F36.2 observed that the goose's coordinate head spans all `64x64 = 4096` cells while our agents click
12–16 object centroids, and proposed widening ours. Measured, at the same cap:

| candidates | score | games |
|---|---|---|
| **12** | **0.1905** | 2 |
| 16 | 0.0722 | 1 |
| **48** (centroids ∪ lattice) | **0.0000** | 0 |

**Monotonically worse as the space widens.** The mechanism is clear in hindsight: with no learning
signal, the walk's success probability falls roughly as `1/|A|^k` for a k-long required sequence, so
widening the action space multiplies the search. **The goose can afford 4096 coordinates precisely
because it LEARNS a distribution over them** — that is the thing we do not have, and adding the
coordinates without the learner is strictly negative.

⇒ Recorded as a **falsified fix**, not a silent revert.

### 38.4 What this leaves, stated without optimism

* Our best hidden score is still **0.18**, from the **generic** official baseline. Every hand-built
  deviation has scored **worse** (0.14 hybrid, 0.08 portfolio), and the two "obvious fixes" are now
  measured to be neutral and negative respectively.
* **There is no valid local instrument** (F37), so further submissions can only be *mechanism bets*.
* The two mechanism bets with an actual argument behind them are:
  1. **a learner, not a policy** — the goose wins because it learns online from the frame-change
     signal; matching that class is the only measured way to reach its level, and the exact
     transition model (F26's mechanism, which computes the same signal without learning) is the one
     cheap candidate that has not been submitted;
  2. **sequential level solving** — per §38.2 the payoff is in levels 2+, which no agent here has
     ever completed, so anything that carries knowledge *across* a level boundary is worth more than
     another level-1 policy.
* ⚠️ **Do not spend submissions on locally-tuned policies.** The 0.2693 that looked like the best
  agent this project ever built was the worst submission it ever made.
