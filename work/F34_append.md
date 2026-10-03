## F34. Three corrections and one tested hypothesis — the protocol lever does NOT confirm

Written 2026-09-30. Everything below is measured on the 25 public games through
`tools/score_local.py` (the shipped scorer + real `baseline_actions`), budget `MAX_ACTIONS = 80`,
and it **corrects F26, F30 and `tools/solve_levels.py`**.

### 34.1 ⚠️ F26's 80-action row is WRONG: the novelty walk scores 0.1265, not 0.00

F26 records:

```
| novelty | 80 | 0 / 25 | 0.00 |
```

Re-measured twice, deterministically, with the agent as it stands in the repo:

```
agent=novelty_agent.py  steps=80  games=25
r11l      3.16       1       81 22+33+51+26+52+49  66 0 0 0 0 0
...
OVERALL score = 0.1265    games with >=1 level: 1 / 25
```

**`r11l` level 1 is solved at action 27** (level score **66** = `100*(22/27.1)**2`), so the row is
`1 / 25` and **0.1265**, not `0 / 25` and `0.00`. The run is reproducible and takes **12 s**.
⇒ F26's *conclusion* (blind exploration cannot solve these games) survives at 1/25; its *number* does
not, and the "novelty scores exactly 0.00" calibration line is gone. Any comparison against F26 was
being made against a stale baseline that understated the incumbent by 0.13.

⚠️ The likely cause is that F26 predates F30's change to the same file (`ARC_SIG_MODE`, default
`masked`). The lesson is the cheap one this project keeps re-learning: **the number attached to an
agent must be re-measured against the agent that is actually in the tree**, because a later edit to a
shared filename silently orphans the earlier reading.

### 34.2 ⚠️⚠️ `env.step()` DROPS click coordinates — `tools/solve_levels.py`'s click oracle is broken

`tools/solve_levels.py` explores ACTION6 as:

```python
a = GameAction.from_id(aid)
if aid == 6: a.set_data({"x": int(x), "y": int(y)})
self.env.step(a)                      # <-- coordinates are DISCARDED here
```

That is **wrong for a direct env call**. `arc_agi/local_wrapper.py:211`:

```python
def step(self, action, data: Optional[dict[str, Any]] = None, reasoning=None):
    action_input = ActionInput(id=action, data=data or {}, reasoning=reasoning)
```

`set_data` is only correct **through the framework**, because `Agent.do_action_request` reads
`action.action_data` and forwards it as `data=`. So every candidate click in `solve_levels.py`
collapsed to **one** click, and the tool's own v2 changelog — *"A path element is now `(action_id, x,
y)`, so two different clicks from the same frame are two different edges"* — was **not true of the
code that ran**. The six ACTION6-only games (`vc33 lp85 r11l s5i5 tn36 ft09`) were explored at a
single fixed coordinate, and F30's "probe artifact" note had already seen a variant of this.

Measured effect of the fix (`work/probe_motion.py`, before → after passing `data=`):

| game | no-op candidates | compact (<20 %) changes |
|---|---|---|
| `lp85` | 8/8 → **6/8** | 0 → **2** |
| `su15` | 9/9 → **4/9** | 0 → **5** |
| `bp35` | 0 → 0 | 3 → **11** |
| `lf52` | 0 | 5 → **13** |
| `cn04` | 0 → 3 | 5 → **9** |

⇒ **Any conclusion about a click-only game that rests on `solve_levels.py` must be re-derived.**
In particular F25's *"sp80 L1 is solvable in 4 actions, cd82 L1 in 5"* came from that oracle and is
**unverified** — `sp80` is not click-only, but the same code path was used for its ACTION6 branch.
This is the fourth instance of one bug class in this project: a call that silently accepts a wrong
argument, fails quietly, and reports a confident number.

### 34.3 The mechanics map: localised dynamics DO exist in 23 of 25 games

`work/probe_motion.py` → `work/probe_motion.json`. From a fresh RESET, each candidate action is
applied once and the frame difference is decomposed:

```
changed cells / 4096        how much of the board moved
bbox area of the change     how concentrated it is
```

The reason this is the right question: F30 measured that `ls20` redraws **4096 of 4096** cells on
every step, so "the frame changed" carries no information — the discriminator has to be whether the
change is **localised**.

| game | actions | no-op cands | cands with <20 % change | min changed fraction |
|---|---|---|---|---|
| `ls20` | 1,2,3,4 | 0 | **4** | 0.0005 (2 cells) |
| `sp80` | 1..6 | 0 | **12** | 0.0005 |
| `cd82` | 1..6 | 0 | **13** | 0.0002 |
| `tr87` `tu93` `re86` | 1..4 / 1..5 | 0 | 4 / 4 / 5 | 0.0032 / 0.0002 / 0.0007 |
| `r11l` `tn36` `s5i5` `vc33` | 6 | 0 | 8 | 0.0002 |
| `ft09` | 6 | **8/8** | 0 | — |
| `sc25` | 1,2,3,4,6 | **12/12** | 0 | — |
| `ar25` | 1..7 | 9/14 | 5 | 0.0002 |
| `sb26` | 5,6,7 | 8/10 | 2 | 0.0002 |

**23 of 25 games have at least one action whose change is localised** (`ft09` and `sc25` are the
exceptions) — the cleanest being `ls20` action 2, which changes **exactly 2 cells at (61,13) and
(62,13)**: a one-cell avatar moving down.
That is an empirically *measurable* avatar, obtainable in one action, with no game-specific constant —
which is exactly what F32's hand-patterned LS20 planner was not. It makes a general
"detect the avatar by differencing, then plan" agent *buildable*; it does not by itself make it work,
because the goal is still unknown.

⚠️ And `ft09`/`sc25` have **no non-no-op candidate at all** among object centroids, so for those two
the click-target heuristic itself is wrong (a blind lattice is the fallback, and it did not help
either — see 34.4).

### 34.4 ⭐ The ordered-protocol hypothesis (F31's only un-falsified lever) was TESTED — and it does not confirm

F31 concluded the only live lever was *"an active, procedure-shaped hypothesis (the wins are ordered
protocols, not reachable frame configurations)"*, on the evidence that the recorded live wins are
mechanically periodic (`vc33` L1 = a click triple repeated, `lp85` L1 = a click pair repeated). The
argument for testing it: the novelty walk re-ranks candidates from the **current** frame every step,
and F30 showed the frame is fully redrawn every step, so its action order is effectively random and
its chance of emitting a specific 3-long cycle is ~`1/|candidates|^3`.

`work/cycle_agent.py` removes exactly that randomness: the candidate list is computed **once per
level, from the level's first frame**, then emitted in a fixed cyclic orbit, so a cycle of length `N`
is emitted `floor(80/N)` times deterministically.

**Fixed orbits** (`ARC_POLICY=cycle`, 5 orderings × 3 dwells):

| ordering | dwell 1 | dwell 2 | dwell 3 |
|---|---|---|---|
| `xy` (reading order) | 0.0000 | 0.0000 | 0.0000 |
| `yx` | 0.0128 | 0.0123 | 0.0215 |
| `rare` (rarest colour first) | **0.1429** | 0.0000 | 0.1429 |
| `area` | 0.0000 | 0.0000 | 0.0000 |
| `colour` | 0.0000 | — | — |

**Portfolios** (phasic, each phase a different ordering). ⚠️ These were re-run after the delegation
bug in 34.4b was found and fixed; the numbers below are the corrected ones.

| policy | score | games ≥1 level |
|---|---|---|
| `novelty` standalone (incumbent, re-measured) | **0.1265** | 1 / 25 |
| ⚠️ `novelty` **through this agent's delegation**, as a self-check | **0.1265** ✅ | 1 / 25 |
| `hybrid` rare-orbit then novelty, K=20 / K=40 | 0.1429 | 1 / 25 |
| portfolio `rare,xy,colour,novelty` @20 | 0.1429 | 1 / 25 |
| portfolio `rare,novelty` @40 | 0.1429 | 1 / 25 |
| portfolio `rare,colour,lattice,novelty` @20 | 0.1429 | 1 / 25 |
| portfolio `rare,colour,xy,area,novelty` @16 | 0.1712 | 2 / 25 |
| portfolio `rare,xy,area,colour` @20 | 0.1770 | 2 / 25 |
| portfolio `rare,colour,xy,area,yx,novelty` @13 | **0.1829** | 2 / 25 |

⚠️ **Adding a `novelty` phase does not help** — the three best configurations are the ones that are
mostly fixed orbits, and every hybrid (orbit → novelty) lands at 0.1429, i.e. *on the orbit phase's
own result*. The gains come from the orbit phases, not from the model-based walk.

### 34.4b ⚠️ A swallowed exception faked the first version of this whole table

The first version of the portfolio table reported `0.1829 / 0.1728 / 0.1770` and *looked* like a
result. It was not. Two independent silent failures were in the path:

1. `from agents.novelty_agent import MyAgent` **never resolved**: the name `agents` on `sys.path` is
   the *vendor* package (`starter/vendor/ARC-AGI-3-Agents/agents`), which has no `novelty_agent`
   module. The `ImportError` was swallowed by `choose_action`'s blanket `except Exception`.
2. After switching to a file-path import, the delegation still failed — with
   **`NameError: name 'frames' is not defined`**, because `_choose(self, latest_frame)` has no
   `frames` in scope. **Also swallowed**, and it degraded to "always play the first legal action".

So every portfolio/hybrid number that contained a `novelty` phase was produced by a policy that
always played action 1. It was caught **only** because the delegation was given a known target:
running *novelty-only through the delegation* must reproduce the standalone **0.1265**, and it
returned **0.0000** — twice.

⇒ Two changes are now permanent in `agents/cycle_agent.py`: the error path **prints once**, and the
`novelty`-phase result is only trusted because the self-check passes. This is the same failure class
as 34.2 and as the `kernels_push` refusal that surfaces as a 404: **a call that fails quietly and
reports a confident number.** It is now the single most common way this project has produced a wrong
conclusion, and the countermeasure that works is a **known-answer self-check**, not care.

**⇒ The hypothesis is NOT confirmed, and the sweep is not evidence of a winner.**

1. **A fixed orbit is no better than the random walk it replaced** — four of five orderings score
   exactly **0.0000**, i.e. worse than novelty. A periodic protocol is only periodic; the *order* has
   to be the game's order, and we have no way to know it.
2. The portfolio's gain (0.1265 → 0.18) comes from **1–2 games**, and `0.1829` vs `0.1770` vs
   `0.1712` is a difference of **one game's level score**. That is luck, not a ranking.
3. ⚠️ **Fifteen-plus configurations were scored against the same 25 games, and the best was then
   read off.** That is textbook public-set overfitting — the exact error the project's own rule
   ("只在意公榜的分数会对公榜过拟合…要做好本地交叉验证") exists to prevent. The honest statement is
   that **all of these policies are equivalent within luck, and the family as a whole sits at
   ~0.13–0.18 driven by 1–2 lucky level-1 solves.** No configuration here should be shipped as
   "the best"; at most, the portfolio shape is a slightly better *coverage* heuristic.

### 34.5 ⚠️ The question that now dominates this project: does the hidden set differ from the public 25?

Everything above is measured on the 25 public games, and F6/F23 assume the rerun plays a **hidden**
set. The only evidence for that is (a) the starter's own comment and (b) the goose scoring **0.00
locally but 0.18 on the hidden board**.

That second piece of evidence is **weaker than it has been treated as being.** `0.18` is
`≈ 4.76/25` — i.e. *exactly one game's level 1 at human efficiency* on a 6-level game — and the goose
refits a CNN every `train_frequency` actions with **no seed set anywhere in the path**, so its local
0.00 is a **single draw from a non-deterministic process**. A different game set and run-to-run
variance both explain the gap, and nothing in this repo distinguishes them.

It matters more than any of the above: **if the hidden set IS the 25 public games, then offline
oracles are legal at rerun time and the project's ceiling changes completely** (the BFS oracle already
solves levels that the walk cannot reach). If it is not, then per-game work is worthless and only a
general mechanism counts — which is what 34.4 just failed to find. Deciding this is the highest-value
ARC experiment available, and the cheap way in is a **control submission**: an agent whose local score
is a known 0.00 under a policy that cannot accidentally score, run against the hidden set, to see
whether it reads 0.00 or ~0.18.
