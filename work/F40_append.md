
---

## F40. The per-level learner reset is NOT the goose's bottleneck — the change scored exactly 0.18

Written 2026-10-01. `56744057` — the goose with its per-level learner reset removed (F39) — returned
**0.18**, and the board reads **rank 2393 · 0.18 · `SubmissionCount 4`**.

### F40.1 The result, and what it settles

| ref | agent | hidden |
|---|---|---|
| `56641359` | official **StochasticGoose**, unmodified | **0.18** |
| `56666561` | hybrid: planner first, goose fallback | 0.14 |
| `56705048` | portfolio of candidate orderings (local 0.2693) | 0.08 |
| **`56744057`** | **goose, per-level learner reset REMOVED** | **0.18** |

⭐ **The change is exactly NEUTRAL.** F39's argument was structural and measured — scoring is per level,
level *i* counts *i* times, and the goose clears its buffer and rebuilds a randomly initialised CNN on
every level change — and **it bought nothing.** So the per-level reset is **not** what caps the goose.

⚠️ **This falsifies F39's hypothesis, stated plainly.** It is the third mechanism bet on this
competition and the first that neither helped nor hurt: the two rule-based agents scored *below* the
baseline (0.14, 0.08) and this one matched it exactly. **Nothing this project has built has ever beaten
0.18.**

### F40.2 What the four results say together

Sorted by how much hand-built machinery each submission added:

```
0.18   official goose, unmodified                        <- zero hand-built machinery
0.18   goose + one structural change (no level reset)    <- one change to the learner's lifecycle
0.14   goose + a hand-written planner in front of it     <- a rule chain deciding first
0.08   a hand-built policy, no learning at all           <- no learner
```

**Every hand-built rule made it worse, and the one change that touched the LEARNER rather than
replacing it was neutral.** With the F37 finding (the hidden games are not the public 25) this is a
consistent picture: **the goose's online learning is doing the work, and rules written here do not
transfer to games nobody has seen.**

### F40.3 ⚠️ Two candidate bets the result does NOT rule out

1. ⭐ **Narrow the goose's COORDINATE space instead of widening it.** F38.3 measured that widening a
   rule-based agent's click set from 12 → 48 candidates cost the whole score (0.1905 → 0.0000),
   because without a learner the search multiplies. The goose has the opposite problem: **4096
   coordinate logits and a learner so weak that it refits on a near-constant `frame_changed` reward.**
   Restricting its clicks to the object centroids our own agents use — keeping its online learning —
   gives the learner a far better prior. That is a change to the *prior*, not a replacement of the
   learning, which is precisely the category that has survived here.
2. **A stochastic draw is still a draw.** The goose is unseeded, so two submissions are two samples.
   ⚠️ But `56641359` and `56744057` both returned **exactly 0.18**, which is evidence the hidden rerun
   is much more stable than the local one (0.0000 on 25 games vs 1.5873 on a 3-game subset), so more
   copies are unlikely to be a cheap lottery here. **Do not assume variance that has not been seen.**
