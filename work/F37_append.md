
---

## F37. ⭐⭐ The 0.08 ANSWERED the open question: the hidden set is NOT the public 25, and local CV is not a leaderboard proxy

Written 2026-09-30. `56705048` (the F36 portfolio) returned **0.08**. The submission history is now:

| ref | agent | local (25 public games) | hidden |
|---|---|---|---|
| `56641359` | official **StochasticGoose** | 0.0000 (one draw) | **0.18** |
| `56666561` | hybrid: planner first, goose fallback | — | **0.14** |
| `56705048` | **portfolio of candidate orderings** | **0.2693** (deterministic) | **0.08** |

### 37.1 ⭐ The proof, and it is airtight

**`agents/portfolio_agent.py` is DETERMINISTIC.** On the `portfolio` path there is no RNG at all: the
candidate list is built by a deterministic component sweep and a deterministic sort, and the action is
`plan[(action_counter // DWELL) % len(plan)]`. Its two level completions (`r11l`, `tn36`) are the same
on every run — re-measured byte-identically before submitting.

> **A deterministic agent cannot score 0.2693 on a game set and 0.08 on that same game set.**
> ⇒ **The rerun's hidden games are NOT the 25 public games.** F35's open question is now **closed by
> measurement** rather than argued.

**Consequences, stated plainly:**

* ⭐ **Local CV on the 25 public games is NOT a valid instrument for this competition.** F24 —
  *"the competition metric IS computable offline … it was never a proxy"* — is **true about the METRIC
  and false about the LEADERBOARD**: the formula and the baselines are real, but they are attached to a
  different game set, so a local gain is not evidence of a hidden gain.
* ⚠️ **Every local-tuning decision this project made is therefore unvalidated**, including F34's
  mechanics map and F36's portfolio. Worse, this one is **anti-predictive in the observed sample**:
  the *best* local score (0.2693) produced the *worst* hidden score (0.08).
* ⚠️ **~30 configurations were swept on the public 25 to pick that agent.** With the game set differing,
  that sweep was fitting noise by construction — the outcome F36 flagged as a risk and could not rule
  out. It is now the measured result.

### 37.2 ⚠️⚠️ Every deviation from the generic baseline has made it WORSE

```
0.18  official StochasticGoose  (generic: online CNN novelty + 4096-way click head, no hand tuning)
0.14  hybrid    = planner first, goose fallback   (-0.04)
0.08  portfolio = hand-built candidate orderings  (-0.10)
```

Three submissions, monotonically decreasing, in exactly the order of how much hand-tuning was added.
**The correlation is the finding: on unseen games, the generic learner generalises and our fixed
policies do not.**

Mechanically that makes sense. The goose's `ActionModel` carries a **coordinate head over all
`64*64 = 4096` cells** (F36.2) and **learns online**, refitting every 5 actions. Our agents click
**12–16 object centroids** chosen by a rule fixed in advance, and **learn nothing**. On a game set we
have never seen, "a rule fixed in advance" is just a prior, and the learned distribution beats it.

### 37.3 ⭐ Two concrete, fixable defects found while explaining the drop

1. ⭐ **Our agents self-impose an 80-action cap; the goose does not.** `agents/agent.py:22` sets
   `MAX_ACTIONS: int = 80`, but it is consulted **only inside the agent's own `main()` loop**
   (lines 74 and 179) — the harness does not enforce it. `agents/goose_agent.py:122` overrides it with
   **`MAX_ACTIONS = float('inf')`**, so the goose keeps playing per game while every agent we have
   written stops dead at 80. On a game we have not solved by action 80 we therefore score **exactly 0**,
   where an uncapped agent can still earn partial credit — which is precisely the *"sliver of partial
   credit"* F26 used to describe the goose's 0.18.
2. ⚠️ **A degenerate frame can pin our agent on one action forever.** `work/probe_avatar.py` crashed on
   **`sp80`** with `ValueError: operands could not be broadcast together with shapes (64,64) (0,)` —
   so `env.step` demonstrably returns a **reshaped/empty** frame on at least one public game. In
   `cycle_agent`, `_as_grid` returns `None` for such a frame and `_choose` then returns
   `GameAction.from_id(legal[0])` — **the same action every step for the rest of the game**, i.e. a
   guaranteed ~0 on any hidden game that trips this. That is a *bug*, not a strategy weakness, and it
   is the most likely single explanation of a score as low as 0.08.

### 37.4 The board kept the good one, so nothing was lost

```
Rank 2373 / 3497   Score 0.18   SubmissionCount 3   LastSubmissionDate 2026-09-30 10:40:32
```

**The platform scores the BEST of our submissions, not the newest** — verified a second time (F33 was
the first). The 0.08 cost us nothing on the public board. ⚠️ It is still the *selection* that decides
the final placement, so **the user must ensure the 0.18 submission is the selected one before
2026-11-02** — and the browser is the only way to do it.

### 37.5 What the next submission must be, on this evidence

Not another locally-tuned policy. The measured ordering says the generic learner wins, so the work is:

1. **Fix the two defects** (remove the self-imposed cap; never fall back to a constant action) — both
   are unconditional improvements with no tuning and no local-fit risk.
2. **Prefer mechanisms that learn at rerun time over rules fixed in advance**, since the game set is
   unseen by construction.
3. ⚠️ **Stop using the public-25 score to choose.** It has now been shown to be non-predictive, and the
   next submission must be justified by mechanism, not by a local number.
