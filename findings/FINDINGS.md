# ARC-AGI-3 — measured findings

Workspace `D:\kaggle\arc\`. Every claim below was measured locally, not read off a page.

---

## F1. Determinism is real — verified, not assumed

Three independent runs of the same game and the same 13-action sequence produced **byte-identical**
frames:

| trial | initial frame sha256[:16] | after sequence | levels |
|---|---|---|---|
| 0 | `cfe5196fb75182bb` | `4412df0168a89497` | 1 |
| 1 | `cfe5196fb75182bb` | `4412df0168a89497` | 1 |
| 2 | `cfe5196fb75182bb` | `4412df0168a89497` | 1 |

⇒ A solution found locally is a solution, and a replay is safe *within a level*. This is the opposite
of the Kaggriculture situation, where a fixed replay was the bug — here determinism is **measured**, and
that measurement is what licenses a replay.

## F2. ⚠️ `RESET` restarts the CURRENT LEVEL, not the game

```
fresh RESET            -> cfe5196fb75182bb
after 21 actions       -> levels=1
RESET after deep play  -> 4412df0168a89497   <-- NOT the fresh state
```

So "RESET + replay a prefix" only returns to the start **while the search stays inside one level**.
Any harness that treats RESET as "go back to the game start" is silently wrong once a level has been
completed. Our first level-by-level solver made exactly that assumption; it is only saved by returning
the instant a level completes.

## F3. LS20 is a deterministic Sokoban-like block puzzle

The board (64x64, one layer, int8) contains a **5x5 movable block**: two rows of colour 12 (`O`) over
three rows of colour 9 (`@`). Isolated single actions from a fresh reset:

| action | effect |
|---|---|
| `ACTION1` | move block **UP** |
| `ACTION2` | move block **DOWN** (no effect at the start — blocked) |
| `ACTION3` | move block **LEFT** |
| `ACTION4` | move block **RIGHT** |

Movement is constrained by the maze: the block only travels where there is a passage. Other colours:
`3` = wall, `4` = background, `5` = a `+`-filled panel, `8` = `%` marker, `11` = `$` band, `1` = two
isolated cells.

The level completes when the block reaches its pad. At completion the pad area turns into a
`+`-filled panel carrying the same `@` glyph pattern that the panel near the top of the board showed
from the start — i.e. the panels are **level indicators**, not the objective.

## F4b. LS20's geometry, measured exactly

The block is a **5x5 stamp** and every action moves it **exactly 5 pixels** -- one cell of a 5-pixel
lattice anchored at its start. Tracked through the verified solution (`block_track.py`):

| step | action | block top-left (row, col) |
|---|---|---|
| init | — | (45, 34) |
| 1–3 | `ACTION3` x3 | col 34 → 29 → 24 → **19** |
| 4–7 | `ACTION1` x4 | row 45 → 40 → 35 → 30 → **25** |
| 8–10 | `ACTION4` x3 | col 19 → 24 → 29 → **34** |
| 11–13 | `ACTION1` x3 | row 25 → 20 → 15 → **LEVEL COMPLETE** |

The path is *left, up, right, up* -- a detour, not a straight line -- because the shaft up to the goal
is only open at one column. **That is the whole point:** the solution is a **maze path on the cell
lattice**, so the planner is a lattice BFS computed *inside the agent*, at **zero env-step cost**.
That is the shape RHAE demands.

⚠️ **A measurement bug worth remembering.** The first block finder matched on colour 12 or 9 and
reported a `50x36` bounding box that never moved -- it was measuring the whole board, because colour 9
also draws the `@` patterns inside the level-indicator panels. Matching the block's **exact 5x5
template** (two rows of 12 directly above three rows of 9) is what made the geometry visible.
A statistic that does not move when the thing it claims to measure moves is not a measurement.

## F4. Level 1's minimal solution is 13 actions, and it is provably minimal

BFS over observed frames (state key = the raw frame bytes) finds

```
ACTION3 x3, ACTION1 x4, ACTION4 x3, ACTION1 x3      =  "3331111444111"   ->  LEVEL 1
```

in **1,777 nodes**. Because BFS expands in order of path length, 13 is the **shortest** action
sequence that completes the level. For RHAE (`(human/ai)**2`, capped at 1.15) that is the best
achievable score on this level regardless of how clever a policy is.

⚠️ **A bug that produced a fake 14-action answer.** The first version of the level-by-level solver
positioned the env once per node with `goto()` and then stepped the whole candidate action list in
sequence, so every action after the first was applied to the wrong parent state. It explored a
different graph and reported 14. Re-positioning before **every** action restored 13. Two BFS
implementations disagreed and the disagreement was the signal — the same shape as
`validate_harness.py` in the sibling project.

## F8. First survey of all 25 games (bounded oracle) — and the tool's own blind spot

`solve_levels.py --max-depth 10 --max-nodes 2500` over all 25 public games:

| game | level 1 | actions | sequence |
|---|---|---|---|
| **sp80** | ✅ | **4** | `4445` |
| **cd82** | ✅ | **5** | `32245` |
| the other 23 | ✗ within budget | — | — |

⚠️ **That table is mostly about the BUDGET, not about the games.** `ls20` shows ✗ here although its
true optimum is 13 actions, because the depth cap was 10. So "not found" means "not found within
10 actions and 2500 nodes", and nothing more. Two results survive that caveat and are real: **`sp80`
is solvable in 4 actions and `cd82` in 5**, and both are provably minimal (BFS order).

⚠️⚠️ **A genuine blind spot, found by reading the env-step counts.** Six games accept **only
`ACTION6`** (the click). The solver hard-codes the click at `(32, 32)` -- the centre -- so for those
games it explores exactly **one** click position forever:

| game | env steps used | why |
|---|---|---|
| `tn36`, `ft09`, `lp85` | **3** | click-only; one position tried |
| `su15` | 5 | `[6,7]` |
| `sc25` | 11 | |
| `vc33`, `r11l`, `s5i5` | 66 | click-only; state space exhausted after ~66 identical-centre clicks |

⇒ **The oracle cannot see the six click-only games at all.** That is a fixable defect, not a property
of the games, and it must be fixed before any survey result about them means anything. The lesson is
the same one this project keeps meeting: *an instrument that reports a number confidently while
being structurally unable to measure is worse than no instrument.*

Cheap games worth knowing about: `tn36`, `ft09`, `lp85` (3 steps), `su15` (5), `sc25` (11) barely
change state at all under the current probe.

## F9. The click games are NOT one family — two distinct mechanics, measured

Fixing the oracle's ACTION6 handling (a path element is now `(action_id, x, y)`, so two different
clicks from one frame are two different edges; click candidates come from object centroids) left
`ls20` at its correct **13 actions**, so the refactor is sound. Re-probing the click-only games then
required asking a better question than "which click solves it": **which clicks change anything at
all?** `click_map.py` sweeps all 4096 positions from a fresh reset.

**Result: they split into two behaviours, and neither is what "click-only" suggested.**

| game | positions tried | changed the frame | reading |
|---|---|---|---|
| `tn36` | 1024 (stride 2) | **0** | a single click does nothing at all |
| `ft09` | 1024 (stride 2) | **0** | a single click does nothing at all |
| `vc33` | 1024 (stride 2) | **1024 — every one** | each click changes exactly **1 cell** |

* **`vc33` is a paint/toggle puzzle, not a maze.** Every click mutates exactly one cell, so the
  objective must be a *pattern* built over many clicks — which RHAE's quadratic penalty punishes hard
  unless the required pattern is small. It is now a well-posed planning problem: read the target from
  the frame, click only the cells that need changing.
* **`tn36` and `ft09` ignore single clicks entirely.** So `ACTION6` there is not a direct state
  change: the game needs a *sequence*, or a click only counts in some context. "Click-only" was a
  statement about `available_actions`, and I had been treating it as a statement about the mechanic.
  That conflation is what made the first survey's zeros look like failures of the games.

⚠️ **`click_map.py` cost 1024 env steps per game and is worth every one of them** — it converted
"these games appear unsolvable" into "these games have two different structures, and one of them is a
planning problem I can state precisely". Guessing the mechanic was the expensive path.

⚠️ **The same format-string bug I had just fixed in the RSNA kernel reappeared here**, in
`click_map.py`: a **4-tuple printed with 3 specifiers**. It was caught immediately because the output
truncated at the print — but it is the second instance of this exact class in two projects in one
session, and both were on the first line of new diagnostics.

## F10. `vc33` ignores the click coordinates entirely — row 0 is a countdown, not a canvas

Two experiments pinned this down, and the first one was misleading on its own.

**Experiment 1 (`click_probe.py`)** — one click from a fresh RESET, at eight widely spread positions
`(0,0) (5,0) (16,28) (38,29) (60,25) (39,30) (10,10) (50,33)`:

> **every one of them changed the same single cell** — `(row 0, col 63)`, value `7 -> 4`.

So the coordinate is **ignored**. ⚠️ And I first checked the schema in case I was sending the click
wrong: `set_data({'x': 7, 'y': 9}).model_dump()` round-trips to `{'x': 7, 'y': 9}`, and
`GameAction.ACTION6.is_complex()` is `True`. **The call is correct and the game discards it.**

⚠️ **Experiment 1 also had a flaw that would have produced a wrong conclusion.** `click_map.py`
called `RESET` before every probe, so all 1024 "changing" positions were really just *the same first
click* — it measured one event 1024 times. "Every click changes the frame" was true and useless.

**Experiment 2 (sustained clicks, no reset)** — this is what showed the mechanic:

| click | cells changed | cell(s) |
|---|---|---|
| 1 | 1 | (0, **63**) 7→4 |
| 2 | 2 | (0, **61**), (0, **62**) |
| 3 | 1 | (0, **60**) |
| 4 | 1 | (0, **59**) |
| 5 | 1 | (0, **58**) |
| 6 | 2 | (0, **56**), (0, **57**) |
| … | | marching **right to left** along row 0 |

⇒ **Row 0 is a countdown bar**, and a click consumes one or two of its cells regardless of where it
lands. Roughly **48 clicks** exhaust it (`~64 cells ÷ ~1.33 per click`).

⇒ **`vc33` is not a paint puzzle after all.** The "every click changes exactly 1 cell" reading from
F9 was an artefact of resetting between probes. What is actually observable is: *coordinate-free
clicks drain a bar*. Whether the bar is an **action budget** (you must achieve something before it
empties) or a **score** (you are meant to drain it) is not yet established, and it is the next
question — but the planner for this game is **not** "click the cells that need changing", which is
what F9 concluded and what a planner built on F9 would have done.

⚠️ **The general lesson, and it is the third time this session:** a probe that resets between samples
measures a *sequence* as if it were a *state function*. F9's "1024 of 1024 positions change the
frame" and this F10 are the same data read two ways, and only the version *without* the reset tells
you what the action does.

## F11. `vc33`'s row 0 is an ACTION BUDGET — 50 clicks, then GAME_OVER

Clicking repeatedly (no reset) until something terminal happens:

| clicks | row-0 cells remaining | state |
|---|---|---|
| 0 | 64 | NOT_FINISHED |
| 10 | 51 | NOT_FINISHED |
| 25 | 32 | NOT_FINISHED |
| 40 | 13 | NOT_FINISHED |
| 45 | 6 | NOT_FINISHED |
| **50** | **0** | **⚠️ GAME_OVER** |

⇒ **It is a budget, not a score.** `vc33` grants roughly **50 actions** and the run ends when the bar
empties. Combined with F10 (the coordinate is discarded) this is a hard statement:

> 50 clicks at a fixed position, and 1024 distinct positions from a fresh reset, all produce **only**
> budget consumption. **Nothing in `vc33` responds to where you click.**

⚠️ **So the mechanic is not reachable through `available_actions` as I have been using it.** Something
about the click is still wrong — most likely it is not a raw `(x, y)` on the 64x64 grid, even though
the schema accepts it and echoes it back. The honest state is: **`vc33` is not solved, and it is not
"solved by clicking the right cell" either.** I have a budget, a countdown, and no control channel.

⚠️ Also note what this cost: F9 concluded *"a paint/toggle puzzle — read the target and click the
cells that need changing"*. That was wrong, and it was wrong in the most expensive way — a **specific,
plausible, buildable plan** derived from a probe that reset between samples. F10 and F11 both came
from the same tool run *without* the reset. **The reset was the bug.**

## F20. ⚠️ The model does NOT transfer to level 2 — and the failure is informative

`play_levels.py` applies the identical planner to each level in turn and replays it:

| level | actions | planned | `$` | collectibles found | replay |
|---|---|---|---|---|---|
| **1** | **13** | `3331111444111` | 84→100 | `[(30, 19)]` | **OK** |
| 2 | 37 | `1411111442422222211111113333332232222` | 100→40 | `[(45, 49)]` | **FAILED** |

**So the model is level-1-specific.** Level 2's frame shows why, and the diagnosis is specific
rather than vague:

* **The goal rule looks right.** The `@` panel has moved to rows 38–46, cols 12–20, and the rule
  returns `(40,14)` — the single lattice cell inside it. Same structure, new place.
* **The collectible rule is wrong.** Level 2 contains a 2-pixel `.` object at **rows 47–48, cols
  22–23**, which lies inside lattice cell **`(45,19)`** — but the rule returned **`(45,49)`** instead.
  Since `plan` requires *every* detected pickup to be taken before the goal opens, one spurious
  pickup derails the whole 37-action plan.
* Level 2 also contains **`$` boxes** (rows 16–18 cols 16–18 as `$$$`/`$-$`/`$$$`, and row 51
  cols 14–16) that level 1 did not have — a second, different kind of object the rule has no concept
  of.

## ⚠️ F20a. CORRECTION: the collectible rule was NOT wrong — my reading was

The two bullets above were written from a **truncated render** (`Select-Object -First 60` cut the frame
at row 51) and they are **false**. Measuring the colour-1 pixels directly:

```
LEVEL 2 colour 1 pixels: [(47, 50), (48, 51)]
LEVEL 2 colour 0 pixels: [(46, 51), (47, 51), (47, 52)]
collectibles rule says:  [(45, 49)]
```

`(47,50)` and `(48,51)` lie inside lattice cell **(45,49)** — so **the detector is right**, and there
is **no object at cols 22–23 at all**; I mis-mapped a cropped column index onto absolute coordinates.

⇒ **What survives:** level 2's plan really does fail (that is measured, not read off a picture). What
does **not** survive is the explanation I attached to it. The collectible detector is correct on both
levels; the cause of level 2's failure is **still unknown**.

⚠️ **This is the fifth instance of the same failure shape in this session, and the most embarrassing
one**, because it is the only one where I wrote a *false diagnosis into the record* rather than a false
measurement. The rule I keep re-learning: **a truncated view is not a view.** When a render is clipped,
any coordinate read off it is an artefact of the clipping — and here that artefact sent me looking for
a bug in a component that was working.

Level 2 does contain `$` boxes (rows 51–53, cols 41–43 as `$$$`/`$-$`/`$$$`, and rows 16–18) which
level 1 lacks, and those remain an untested candidate for why the plan fails.

## F22. ⭐ The planner is now a real `MyAgent`, and it solves LS20 level 1 in the optimal 13 actions

`agent/my_planner_agent.py` (copied to `my_agent.py` for the notebook build; the submitted
StochasticGoose baseline is preserved as `goose_agent.py`). Run through the framework's own loop:

```
levels_completed: 1
actions used   : 81
agent report   : {'planned': 2, 'failed': 0, 'fallback_actions': 30}
  level 1 completed at action 13
```

**13 actions is the BFS-proven optimum**, produced by a real agent inside the competition's own
harness — not by an offline script. That is the deliverable this turn was for.

How it works, and where it gives up:

* On every level change it **re-plans from the current frame** (`RESET` is per-level, F2, so this is
  safe and cheap) and then executes the plan, spending actions only on execution.
* `planned: 2` is honest and instructive: it planned level 1 (13 actions, worked) **and level 2**
  (37 actions, did not). `failed: 0` only because `_plan` returned a list — **"a plan was produced" is
  not "the plan works"**, and F20/F21 are the record of it not working.
* After both plans are exhausted it falls back to a legal-action novelty walk (30 actions).

⚠️⚠️ **DO NOT SUBMIT THIS ALONE — it would probably regress.** Two measured facts point the same way:

1. The competition rerun plays a **hidden** game set (F6), not the 25 public games. The planner's
   rules are verified on **one level of one game**; on anything else it falls back.
2. The fallback is a **novelty walk, which scores 0 levels locally**, whereas the shipped
   StochasticGoose CNN scored **0.18** on the hidden set (`56641359`, rank 2346/3454). So on the hidden
   set the fallback is what runs, and it is weaker than what we already have.

⇒ **The correct move is a HYBRID**: use the planner when it produces a plan, otherwise delegate to the
StochasticGoose CNN. That is strictly better than either alone — it keeps the 13-action optimum where
the model applies and keeps the 0.18 fallback where it does not — and it is the natural next
engineering step. Submitting the planner on its own would trade a measured 0.18 for an unmeasured
hope, which is exactly the trade this project keeps refusing to make.

## F21. Level 2's true optimum is beyond 14 actions — measured, and it narrows the gap

`level_oracle.py` runs the BFS oracle on a **specific level** by first replaying a known prefix. With
level 1's verified 13-action route as the prefix:

```
prefix=3331111444111 -> levels_completed=1
NOT SOLVED within depth 14 / 6000 nodes (310 distinct states, 84s)
```

⇒ **Level 2 needs more than 14 actions.** That matters twice over:

1. The planner's 37-action attempt is **not obviously wrong in magnitude** — level 2 is simply a
   bigger puzzle than level 1, so its failure is not "the plan is absurd" but "the plan is wrong
   somewhere".
2. **Level 1's optimum (13) was found at depth 14 and level 2's was not** — so the level-1 result sat
   close to the depth limit all along, and generalising needs a deeper, slower search. The
   replay-based oracle costs O(depth) env steps per node, which is why this was not pushed further in
   one sitting.

⚠️ **The stale prose that used to sit here is deleted, because F20a disproved it.** The earlier text
claimed *"the rule is wrong … level 2 has more objects and the rule is wrong"* and proposed a
contiguous-component fix for the object detector. **The detector was never wrong on level 2** — that
was a mis-mapping of a cropped column index onto absolute coordinates (F20a). The deleted text was a
false diagnosis with a confident fix attached, which is the worst thing to leave in a findings file,
because a later reader would implement a fix for a non-existent bug.

**Where the LS20 investigation stands, completely:**

| component | status | evidence |
|---|---|---|
| lattice (5 px, anchored at the block) | ✅ | F4b |
| passability (>= 20 wall in the 5x5 footprint) | ✅ 144/144 edges | F13 |
| goal (unique cell in an enclosed colour-5 box) | ✅ level 1; structurally consistent on level 2 | F14 |
| collectible (`find_collectibles`, colour-based) | ✅ correct on **both** levels | F20a |
| budget (`$` = 2/action, 82; a collect is free) | ✅ | F17/F18 |
| state = (cell, set of collectibles) | ✅ | F15/F18 |
| **level 1 solved optimally, verified end to end** | ✅ **13 actions** | F19 |
| **level 2** | ❌ cause still unknown; needs **> 14** actions | F21 |

⚠️ **Honest summary of the last three turns:** I claimed the collectible rule was broken on level 2,
then **disproved my own claim by measuring**. So the component I "fixed" was working, and the real
cause of level 2's failure is still unidentified. What those turns actually produced is a **corrected
record**, a **colour-based detector verified on two levels**, and a **measured lower bound** — not a
diagnosis.


## F19. ⭐⭐⭐ END-TO-END: the planner solves LS20 level 1 optimally, from pixels, at zero action cost

```
goal cells found from the frame:   [(10, 34)]
collectibles found from the frame: [(15, 34), (30, 19)]
planned actions: 3331111444111   (13 actions)   goal=(10, 34)
after replaying them: levels_completed=1
⇒ PLAN WORKS — the level completed
```

**`3331111444111` is the same 13-action sequence BFS found to be provably minimal** — and the planner
found it with **zero engine calls**, from the frame alone, against a budget of **82 `$` cells (41
actions)**. This is the shape F5 demanded: *searching costs actions; planning does not.*

**The full model, everything measured:**

| component | rule | evidence |
|---|---|---|
| lattice | 5-pixel steps anchored at the block | F4b, block tracked move by move |
| passability | 5x5 footprint has **>= 20** wall pixels, or it is the block's own cell | F13, 36/36 cells and 144/144 edges |
| goal | the unique lattice cell inside a colour-5 region **enclosed by colour 3** | F14, exactly one candidate |
| collectibles | lattice cells containing a pixel of the **object colour** (colour 1 here); **entering is free and advances the panel** | F18 + F20a |
| budget | `$` = 2 cells per action, 82 total; a collect costs 0 | F17 |
| **state** | **(cell, set of collectibles taken)** — not the cell alone | F15, two routes to `(15,34)` behave differently |

⚠️ **The object detector was rewritten after F19, and this is the record of it.** F19’s version flagged any cell with `20 <= wall < 25`, which also caught `(15,34)` — wall-dominant because of *panel* pixels, not an object. The current detector is **colour-based** (`object_colours=(1,)`): both levels contain exactly two pixels of colour 1 and only that colour marks the object. It is correct on **both** levels (F20a), which the geometric version was not shown to be.

⭐ **What made this work, in one line:** every time the model mispredicted, the response was to
**replay it on the engine and diff**, not to adjust the model by taste. That produced F15 (the state
is not the position), F16 (the extra state is drawn far from the block), F17 (the budget), and F18
(the anomaly that forced the 20-pixel threshold was a collectible) — and each of those looked like an
unrelated loose end while it was being chased.

## F18. ⭐⭐⭐ RESOLVED: LS20 is "*collect the item, then reach the goal*" — the hidden state is a pickup

Walking the 13-action optimum one step at a time and diffing the panel after **every** move isolates
the single special moment:

| step | action | block | `$` | panel |
|---|---|---|---|---|
| 1–5 | A3,A3,A3,A1,A1 | … | −2 each | same |
| **6** | **A1** | **(30,19)** | **±0 — FREE** | **CHANGED, 8 cells** |
| 7–12 | A1,A4,A4,A4,A1,A1 | … | −2 each | same |
| 13 | A1 | goal | — | **LEVEL 1 COMPLETE** |

Panel change at step 6: rows 57–58, cols 3–4 and 7–8, `9 → 5` and `5 → 9` — **the `@` markers move**.

⭐ **And `(30,19)` is exactly the cell whose signature was `{0:3, 1:2, 3:20}`** — the one that broke
the strict "uniformly wall" rule in F13 and forced the `>= 20` threshold. **The anomaly that made the
rule a threshold was a collectible, not noise.**

⇒ **The complete model of LS20:**

1. **Lattice** anchored at the block; a cell is **passable** iff its 5x5 footprint has **>= 20** wall
   pixels, or it is the block's own cell.
2. **Collectibles** are cells containing a non-wall object (here 2 pixels of colour 1). **Entering one
   collects it, costs NO `$`, and advances the bottom-left panel.**
3. **The goal** — the unique lattice cell inside an enclosed colour-5 box — **only opens once the
   collectible is taken.** That is why F15's straight route was refused: it never visited `(30,19)`.
4. **`$` is the action budget**: 2 cells per action, 82 cells total, **except a collect is free**.

⚠️ **This closes F15, F16 and F17 at once, and it is a much better ending than "the model is
incomplete".** The three earlier findings were each correct and each incomplete:

* F15 said the state is not the block position — **true**, and the extra variable is *has the
  collectible been taken*.
* F16 said the extra state is a global display far from the block — **true**, but the display is an
  *effect* of the pickup, not the state itself.
* F17 said `$` is 2 per action — **true**, with the exception that a pickup is free, which is exactly
  the row that looked anomalous ("blocked but cost 0") and which F17 explicitly flagged as unexplained.

⭐ **The reusable lesson:** the anomaly I could not explain at each stage — the extra reachable cell,
the distant changing panel, the free blocked move — was **the same single mechanism seen from three
angles**. Chasing each anomaly instead of filing it as noise is what produced the model.

## F17. ⭐ The `$` bar is the ACTION BUDGET: exactly 2 cells per action, ~41 actions per level

`region_diff.py` applies exactly ONE action from several fixed states and diffs three regions:

| from state | action | block | bottom-left panel | `$` bar |
|---|---|---|---|---|
| start | A1 | (45,34)→(40,34) | unchanged | **82 → 80** |
| start | A2 | **blocked** | unchanged | **82 → 80** |
| start | A3 | (45,34)→(45,29) | unchanged | 82 → 80 |
| 1 | A1 | (40,34)→(35,34) | unchanged | 80 → 78 |
| 1 | A2 | (40,34)→(45,34) | unchanged | 80 → 78 |
| 1,1,1,1,1,1 | A1 | **blocked** | unchanged | **70 → 70** |

⇒ **Each action costs exactly 2 `$` cells.** The bar holds **82**, so a level grants about **41
actions**. That is the real budget, and it is **drawn in the frame**, so an agent can read how many
actions it has left instead of guessing.

⚠️ **Two things the table does NOT settle, stated so they are not mistaken for settled:**

1. **Blocked moves usually still cost 2** (`start` + A2 consumed 2 while moving nothing), **but the last
   row cost 0** (A1 at (15,34) was blocked and consumed nothing). So "blocked" is not one thing; some
   blocked moves are charged and at least one is not. Unexplained.
2. **The bottom-left panel was `unchanged` after every single move tested** — yet F16 showed it
   *differed* between the straight route and the detour. So it changes only on *particular* moves
   (the detour's `A4` at row 25–29 is not among those tested here). The panel is therefore **not** a
   per-move counter, and what drives it is still open.

⭐ **What this buys:** the budget is now a **measured, frame-readable quantity**. An agent that can
read `$` knows its remaining actions, and any planner can be scored against "does it finish before
the bar runs out" — a concrete constraint that was previously invisible.

## F16. ⭐⭐ The hidden state is a GLOBAL DISPLAY, and it is visible in the frame

`state_diff.py` replays both routes to `(15,34)`, stops them there, and diffs the boards:

| route | actions | block | then UP |
|---|---|---|---|
| A straight | 6 | (15,34) | **refused** |
| B detour | 12 | (15,34) | **level complete** |

**18 cells differ, and they are nowhere near the block** — rows **57–62**, cols **3–23**:

```
   A (6 actions)        B (12 actions)
 ++@@@@@@++           ++@@@@@@++
 ++@@@@@@++           ++@@@@@@++
 ++@@++++++           ++++++@@++    <<< changed
 ++@@++++++           ++++++@@++    <<< changed
 ++@@++@@++           ++@@++@@++
 ++@@++@@++           ++@@++@@++
 +------$$$$$$$$       +-----------$$$$    <<< 10 cells of $ turned to wall
```

⇒ **Two structures move together, neither of them the block:**

1. **The bottom-left panel's `@` pattern changes** (rows 57–58: `@@` moves from cols 3–4 to cols 7–8).
2. **The `$` (colour 11) bar loses 10 cells**, which become wall (colour 3).

So the state is **(block position, the bottom-left `@` pattern, the `$` bar)** — a *global progress
display*, not just where the block stands. That is why a position-only planner produced a 7-action
plan the engine refuses, and why the 144/144 edge check could not see it (F15).

⭐ **The encouraging half:** every one of those variables is **drawn in the frame**. The agent does not
need to be told about them — it can read them. What it lacks is the **transition rule** for them
(which block moves change the panel, and how many `$` each move costs), and that is now a
well-posed, narrow question rather than a vague "the model is wrong".

**⇒ The next measurement, concretely:** replay a single block move from a fixed state and diff the
whole board. If one move consistently changes exactly one `@` position and consumes a fixed number of
`$` cells, the panel is a positional counter over the block's path and the rule is extractable. If the
mapping is irregular, the display encodes something else and each of the 36 reachable cells needs its
own measurement — which is exactly the kind of thing the oracle can enumerate offline.

## F15. ⚠️⚠️ The board is NOT memoryless — the same block position behaves differently

**The failure that exposed it.** With the passability rule (F13) and the goal rule (F14) both in
place, the planner emits

```
1111111   (7 actions, straight UP)
```

and the engine **refuses it**. Tracing both routes:

| straight `UP` x7 | the 13-action optimum |
|---|---|
| U1..U6 → block rises 45→40→35→30→25→20→**15** | L,L,L then U,U,U,U → also reaches **(15,34)** |
| **U7 → the block DOES NOT MOVE** | A1 from (15,34) → **LEVEL COMPLETE** |

⇒ **Two paths reach the identical block position `(15,34)` and the game behaves differently there.**
So the state is **not** the block's position: what the block painted on the way in matters too.

⚠️ **Why the 144/144 edge check did not catch this.** Each of those edges was measured from a
position reached by one *specific* path (the BFS path), so every edge that was checked was valid *for
that path*. The check verified the graph **as a tree of specific paths**, and I read it as verifying a
**memoryless position graph**. Those are different claims, and the weaker one passed while the
stronger one is false. **An ablation that shares the bug it is testing for cannot find it.**

⚠️ **And it invalidates the "state = position" assumption behind `build_graph`/`plan`**, which is why
the planner produced a plan the engine rejects. The 7 < 13 discrepancy was the only signal, and it is
exactly the kind of signal that a "planned actions: N" line would happily report as a success if the
replay step were missing.

**What is still solid:** the passability rule (footprint >= 20 wall, plus the block's own cell) and
the goal rule (the unique lattice cell inside an enclosed colour-5 box) both hold on the evidence
gathered — F13's 33/33-then-36/36 separation and F14's unique goal. What is now in doubt is only the
**composition** of those edges into a path.

**⇒ The next measurement is well-defined:** replay the *straight-up* route and the *detour* route and
diff the boards at the moment both sit on `(15,34)`. Whatever differs is the hidden state variable,
and it must be modelled before any planner can be trusted. Concretely: the straight route paints
column 34 on the way up; the detour paints column 19 and row 25-29. Find which of those differences
gates the final move.

## F14. The goal rule is NOT yet identified — and my own scan grid was wrong

The passability rule (F13) is verified. The remaining gap for LS20 is **which cell completes the
level**, and it is not simply "the colour-5 panel cell":

| candidate | colour-5 count | verdict |
|---|---|---|
| `(10,34)` — the real goal | 19 | panel-dominant, but **not unique** |
| `(45,0) … (0,0)`, col 0 | **20 each** | the `++++` left border also scores 20 |

⚠️ **And the scan that produced that table had a bug of its own.** It enumerated lattice cells at
**multiples of 5** (`range(0,60,5)`), which is wrong: the lattice is **anchored at the block's start**
(45, 34), so its columns are **34, 29, 24, 19, …** — congruent to `4 mod 5`, not `0 mod 5`. The
correct goal `(10,34)` therefore never appeared; the scan reported `(10,35)` and `(10,30)` instead.
**The rule being sought and the grid searching for it were on different lattices.**

⇒ **Status, stated plainly:** LS20's *movement* is solved and verified to 144/144 edges; its *goal* is
not. Colour-5 dominance does not single it out. The next question to put to the instrument is whether
the goal is identified by the **panel border** (the goal cell is enclosed by colour 3 on the panel's
rim, which no col-0 cell is) — that is a concrete, testable difference between `(10,34)` and the
`colour5=20` cells in column 0, and it is the obvious thing to measure next.

**Lesson, and it is the fourth instance of this shape this session:** I checked the *rule* carefully
and not the *frame of reference it was evaluated in*. Anchoring a lattice at an object (the block)
rather than at the image origin is the kind of detail that silently makes every downstream number
meaningless while still producing a clean-looking table.

## F13. ⭐⭐ LS20's movement rule, derived from pixels and verified to 144/144 edges

This is the first **complete, verified game model** in this workspace, and it was derived **from the
frame alone** with **zero engine calls** in the planner path.

**The rule.** Anchor a 5-pixel lattice at the block's start. A lattice cell is **passable** iff its
5x5 footprint contains **at least 20 pixels of colour 3** (wall) — plus the block's own current cell.
`ACTION1/2/3/4` step the block one cell up/down/left/right.

**How it was found, in the order that mattered:**

| step | what | result |
|---|---|---|
| 1 | `lattice_graph.py` — walk the engine and record every real edge | **36** reachable cells out of a 7x8 lattice; the graph is **UNDIRECTED**, so the trail the block paints is *not* a barrier |
| 2 | colour at each cell's **top-left pixel** | useless — `3` for almost every cell, reachable or not |
| 3 | `cell_signature.py` — colour counts over the whole **5x5 footprint** | **the rule separates cleanly** |
| 4 | strict "uniformly wall" | **33/33 passable, 0 false positives**, but missed 2 cells |
| 5 | the 2 misses were `{3:20, 5:5}` and `{0:3, 1:2, 3:20}` — **exactly 20 of 25** | ⇒ threshold, not uniformity |
| 6 | `>= 20 wall` | 36/36 cells, **141/144 edges** |
| 7 | 3 misses were all moves **into the start cell** (whose footprint holds the block) | ⇒ vacating paints wall, so the block can always step back |
| 8 | `>= 20 wall` **OR** the block's own cell | **36/36 cells, 144/144 edges — 1.000** |

⚠️ **The inversion is the whole trick and it is why guessing was hopeless:** in LS20 the *drawn wall
is the corridor* and the *open background is the void*. A planner built on "move through the
background" would be exactly backwards, and it would look reasonable the whole way.

⭐ **And step 5 is the general lesson**: the first rule had **zero false positives** and still missed
two cells. A rule can be *safe* and *incomplete*, and only a cell-by-cell diff against ground truth
distinguishes "nearly right" from "right". Both misses were the same shape — 20 of 25 — which is what
made the threshold obvious; had they been arbitrary, the same diff would have said so.

⇒ **The planner is now `build_graph(frame)` + BFS: pure computation, no engine steps**, so it costs
**0 of the 80 actions** to find the 13-action optimum. That is the shape F5 demands, and the rule is
verified rather than asserted.

## F12. The method that works, stated once so it is reused

Every wrong turn this session came from the same shape, so the corrected procedure is:

1. **Never reset between samples when asking what an action DOES.** A reset turns a *sequence* into a
   *state function* and silently measures one event many times (F10).
2. **Sweep the parameter space from a fresh reset when asking what an action ACCEPTS.** That is what
   `click_map.py` is for, and it is a different question from (1).
3. **Play to a terminal state to find budgets and failure modes** (F11). A bar that only ever
   decreases is a budget; a bar that gates progress is an objective.
4. **Re-position before every candidate action in any search** — F4's 14-vs-13 bug.
5. **A statistic that does not move when the thing it measures moves is not a measurement** — the
   50x36 block bbox in F4b.

## F5. ⭐⭐ The binding constraint: search costs ACTIONS, and RHAE is quadratic

This is the fact that determines the whole approach, and it rules out the obvious method:

* BFS to solve level 1 cost **1,777 env steps**. The agent's budget is **`MAX_ACTIONS = 80` per game**,
  and *every env step during a search is an action that RHAE charges for*.
* Even a perfect 13-action solution scores `(human/13)**2`; a 300-action solution scores ~0.001.

⇒ **A search-at-runtime agent cannot score**, even if it is guaranteed to win. The agent must derive
the game's rule from the observed frame and **plan** the minimal sequence analytically, spending
actions only on execution.

⇒ Consequently the useful work is **per-game rule extraction**, and the local BFS is not the agent —
it is the **ground-truth oracle** that tells us the number to beat. A planner is correct exactly when
its action count matches what BFS says is minimal. That gives us, for the first time, a **local,
quantitative target** for ARC-AGI-3 (`solve_levels.py`), which is what the project was missing.

## F6. The public game set is 25 games; the competition set is hidden

`play_local.py --list` enumerates exactly **25** public environments:

```
cd82  ar25  ka59  tn36  tu93  s5i5  vc33  dc22  ls20  m0r0  g50t  ft09  sk48
lf52  lp85  sc25  wa30  sp80  cn04  sb26  tr87  su15  bp35  r11l  re86
```

The starter's own comment says the competition rerun plays the **hidden** game set, so a replay table
keyed by these ids is **not** a submission strategy — it is only a way to develop and verify a planner.

⚠️ **`available_actions` is per game and often restrictive** (measured across all 25): six games accept
**only `ACTION6`** (the click), and the rest take various subsets of 1–7. The shipped starter picks
uniformly from **every** `GameAction`, so on those six games roughly **six of every seven actions are
commands the game discards**.

## F7. Tooling that works (all in `starter/`)

| script | what |
|---|---|
| `probe.py` | render a game's frame + one-shot action diffs, from a fresh RESET |
| `watch.py` | render a **labelled crop** before/after each step of a sequence — the microscope |
| `solve.py` | first BFS (creates an env per node: correct but slow) |
| `solve_levels.py` | BFS **level by level** on one reused env; the oracle and the minimal-action target |
| `bench.py` | run any agent across all 25 games (levels completed, actions) |

⚠️ **Use `OperationMode.OFFLINE`, not `NORMAL`.** `NORMAL` re-fetches the environment list from the ARC
API on every `Arcade()` construction, so a transient network failure turns a local reverse-engineering
tool into a failing network client. The game sources are cached under `environment_files/`, and OFFLINE
runs the identical engine with no network at all.

---

## F23. The rerun is ONLINE against a gateway — no simulator, no game source, no LLM

Read from `starter/scripts/build_notebook.py` and the shipped framework, not inferred. The submission
notebook's rerun branch writes this `.env` and then runs the agent:

```
OPERATION_MODE=online
ENVIRONMENTS_DIR=            # ← EMPTY
ARC_BASE_URL=http://gateway:8001/
ARC_API_KEY=test-key-123
```

`main.py` fetches the game list from `{ARC_BASE_URL}/api/games`, and `Arcade.make()` in ONLINE mode builds
a `RemoteEnvironmentWrapper` — so **every hidden game runs server-side behind the gateway**. The notebook
also has `isInternetEnabled: False`.

⇒ Three whole families of approach are dead, and it is worth stating so nobody spends a day on them:

1. **Search on a forked copy.** There is no local environment for a hidden game, so an agent cannot
   `arc.make()` a second copy and BFS it. (We *can* do that for the 25 public games, which is exactly why
   offline action counts are free and do NOT transfer — see F26.)
2. **Reading the hidden games' source.** `_download_game()` fetches `{base}/api/games/{id}/source`, but that
   is the NORMAL-mode path; the rerun is ONLINE. `metadata.json`/`baseline_actions`/`tags` *are* reachable
   through the gateway's metadata endpoint, the source is not (and a probe would cost a submission — see F27).
3. **LLM agents.** `vendor/ARC-AGI-3-Agents/agents/templates/` ships `llm_agents.py`, `reasoning_agent.py`,
   `multimodal.py`, `langgraph_thinking/`, `smolagents.py`. All need an external model API and there is no
   internet. Any plan whose first step is "call a model" is not implementable.

## F24. ⭐⭐⭐ The competition metric IS computable offline — it was never a proxy

**F7 and `bench.py`'s own docstring carried a FALSE claim: "the human baselines that turn it into a score
are not public". They are public.** Every downloaded game ships them:

```
environment_files/<game>/<hash>/metadata.json → {"baseline_actions": [...]}
    ls20 [22,123,73,84,96,192,186]     sp80 [39,58,25,148,96,152]     vc33 [7,18,44,61,131,34,152]
    cd82 [55, 8,41,21,23, 23]          g50t [78,175,179,230,96,54,67]  wa30 [71,119,...]
```

And `Arcade.close_scorecard()` in OFFLINE mode calls
`EnvironmentScorecard.from_scorecard(scorecard, self.available_environments)`, where
`available_environments` is scanned from those same `metadata.json` files. So the **shipped scorer** runs
locally against the **real** baselines. We reuse it rather than reimplementing it, because a
reimplementation that silently disagrees with the leaderboard is the one thing a local CV must not do.

`tools/score_local.py` is that harness. It pins `ENVIRONMENTS_DIR` to an absolute path, forces OFFLINE,
drives any agent file over all 25 games through one scorecard, and prints the per-game table plus
`OVERALL score` — the leaderboard number.

⚠️ Bug found while writing it: on the normal scoring path `EnvironmentScoreCalculator.to_score()` builds its
`EnvironmentScore` **without an `id`** (only the early-return paths set one), so `run.id` is `None` and
`run.id.split("-")[0]` crashes. Use `env_score.id`.

## F25. ⭐ The scoring arithmetic says LEVEL 1 IS THE WHOLE GAME

From `arc_agi/scorecard.py`:

```
per level i :  completed → score_i = min(100 * (baseline_i / actions_i)**2, 115),  else 0
per game    :  game_score = sum(score_i * i) / sum(i)        over all levels i of that game
overall     :  score = mean(game_score over games)
```

Level 1 carries weight 1 of `sum(1..L)`. The public games have L = 6..10, so `sum(1..L)` = 21..55 and
**completing level 1 alone at human efficiency is worth 100/21 = 4.76 down to 100/55 = 1.82** per game.
Across the 25 public games that averages ≈ **3.1**, against a published **top-10 % cut of 3.80** and a
**median of 0.32**. We do not need to solve these games — we need to finish **level 1** of as many as
possible inside 80 actions.

Also load-bearing, and each one silently taxes score:
* **Beating the human is possible and caps at 115.** LS20 L1: human 22, our proven optimum 13.
* **`Card.inc_reset_count` bumps `actions` too**, so a non-full RESET is charged to whichever level it
  lands in. But GAME_OVER is recoverable by RESET, which is strictly better than ending the game at 0.
* The human baseline is a *human*, not an optimum: sp80 L1 is solvable in **4** actions against a baseline
  of **39**; cd82 L1 in **5** against **55**. Humans spend most of the budget learning the controls.

## F26. ⚠️⚠️ MEASURED NEGATIVE RESULT: novelty exploration cannot solve these games

`agents/novelty_agent.py` is a model-based explorer with no learning: it keeps a transition model keyed by
the frame hash and prefers (tier 0) never-tried `(state, action)` pairs, else (tier 1) the least-visited
successor, then (tier 2) known no-ops, then (tier 3) pairs that caused GAME_OVER. Ties inside tier 0 are
broken by a shuffle seeded with the state hash, so action *order* varies per state while the run stays
exactly reproducible. ACTION6's free `(x,y)` is handled as one action key per candidate coordinate
(centroids of connected components of non-background colour).

Scored through `score_local.py`:

| agent | budget | level 1 solved | overall |
|---|---|---|---|
| StochasticGoose | 80 | 0 / 25 | **0.00** |
| novelty | 80 | 0 / 25 | **0.00** |
| novelty | **2000** | **2 / 25** (sp80, r11l) | 0.15 |

⇒ **The failure is ALGORITHMIC, not budgetary.** Offline actions are free, so giving the walk 25× the real
budget isolates the variable cleanly: 2000 actions buys 2 games. Blind exploration over raw-frame states
does not solve these levels, and no amount of tuning the same family of rule will change that.

⚠️ **The goose scores 0.00 locally, and that is consistent with its 0.18 on the hidden set** — the 0.18 is a
sliver of partial credit, i.e. the incumbent is also effectively solving nothing. That is the calibration
that validates this harness as a predictor, and it means **any** local score above ~0 is a genuine gain.

⚠️ **Also corrects a standing assumption:** `bench.py` was believed to have measured the goose locally. It
had not. `torch` was never installed in `starter/.venv`, so `--agent goose` always died at
`ModuleNotFoundError: No module named 'torch'`. Installed now (`torch 2.14.0+cpu`, CPU wheels).

## F27. The public games: three families, and level-1 baselines of 7..78

`tags` come from the same `metadata.json` and are reachable at rerun time via the metadata endpoint, so a
family-keyed strategy is legitimately general (it keys on a tag, not on a game id).

| family | games | n |
|---|---|---|
| `click` | lf52 lp85 r11l s5i5 su15 tn36 vc33 | 7 |
| `keyboard` | g50t ls20 tr87 | 3 |
| `keyboard_click` | ar25 bp35 cd82 cn04 dc22 ka59 m0r0 re86 sb26 sc25 sk48 sp80 tu93 wa30 | 14 |
| *(untagged)* | ft09 | 1 |

Level count L = 6..10; **level-1 human baselines run 7 (vc33) to 78 (g50t)**, median ≈ 30.

## F28. Frame format, and the two cheap wins already banked

Measured (`tools/probe_frame.py`, `tools/trace_policy.py`):

* `frame` is **`(1, 64, 64)` int8 colour indices 0..15** — one 2-D grid, not one-hot planes.
* `win_levels` is in every frame (ls20 7, sp80 6, cd82 6, vc33 7): the level count is known, not guessed.
* `available_actions` arrives as **raw ints** — `[1,2,3,4]` for ls20, `[6]` **alone** for vc33.
* The goose **already** honours `available_actions` (`_sample_from_combined_output(..., available_actions)`),
  so F6's "six of every seven actions are discarded" concern is handled — do not "fix" it again.
* The goose's training signal is literally `reward = 1.0 if frame_changed else 0.0`, and it refits a CNN
  every `train_frequency` actions *within a single 80-action episode*. It is a novelty detector fitted on
  ≤80 labels. **That is the diagnosis of why the incumbent is at 0.18** — and it is precisely why an
  *explicit* transition model should dominate it, once the model can actually plan (F26).

## F29. Where that leaves the LS20 planner

The planner (F19–F22) is a **method demonstration, not a scoring path**: it is verified on one level of one
git-public game, and the rerun is a hidden set (F23). Its value now is that it is the existence proof for
the only thing F26 leaves standing — *derive the mechanics from pixels, then plan offline and spend actions
only on execution*. Generalising that, not repairing LS20 level 2, is the work.

---

## F30. ⚠️ FALSIFIED: the "mask the HUD / status bar" fix does nothing here

`ARC-AGI-3 SOTA Methodologies Analysis` and the openworld harness notes both assert that a UI
counter changes on ~every step, so hashing the raw frame makes every step a new state and
exploration "explodes" — and that the fix is to detect cells changing on >95 % of steps and zero
them before hashing. That claim is load-bearing and **it is false for this game set.**

I implemented it as `ARC_SIG_MODE=masked` in `agents/novelty_agent.py` (per-cell change counts,
mask at >0.95 with ≥10 observations, reset per level). Result at 2000 actions on 8 games:

| mode | level-1 solves | overall |
|---|---|---|
| `raw` (control) | 4 / 8 | 0.9700 |
| `masked` | 4 / 8 | **0.9700 — byte-identical, every game, same action counts** |
| `objects` | 3 / 8 | 0.0702 |

Identical outcomes to four decimal places are only possible if the mask never changed a decision, so
`tools/mask_probe.py` measured the premise directly instead of arguing about it. It replays a
deterministic cycle through each game's legal actions and counts, per cell, how often it changes:

| what | measured |
|---|---|
| games with **any** cell changing on >95 % of steps | **0 / 25** (the 2 non-zero rows, `bp35`/`cn04`, ran 2–5 steps before ending) |
| masked/raw distinct-state ratio | **0.98–1.00** on every keyboard game |
| `ls20` cells changed per step | **4096 of 4096 — the entire board is redrawn** |
| `raw_states` over 60 steps | 42–61, i.e. **one new state per step** |

⇒ **There is no small status-bar counter to mask.** The frame is fully redrawn every step, so the
raw-frame state explosion is *intrinsic*, and a change-frequency mask removes ~0–2 % of states. The
borrowed diagnosis was right that raw hashing explodes and wrong about why, and therefore wrong
about the cure. ⚠️ Fixing state identity here needs **semantic** abstraction (what the objects *are*),
not denoising (which pixels *flicker*).

⚠️ **`objects` is also falsified as an improvement** (3/8 vs 4/8): hashing only components of ≤64
cells drops the large structures — walls, panels, the goal — that carry the position information, so
`cd82` loses its solve and `r11l` loses a level. The subagent's recommendation to port
`e125/objstate.py` was worth testing and did not survive the test.

⚠️ **Probe artifact, stated so it is not misread as a finding:** `ft09`, `lp85`, `su15`, `tn36` show
1 distinct state, because the probe calls `env.step(action)` with no `data` for `ACTION6`, so every
click lands at (0,0) and is a no-op. Those four rows are uninformative about click games, not
evidence that click games have one state.

**Ablation detail worth keeping** (2000 actions, the subset was chosen to include the winnable games,
so it flatters everything): `r11l` level 1 ≈ 27 actions and `vc33` level 2 ≈ 23 actions — *inside* the
80-action budget — while `cd82` level 1 needed ≈ 848 and `r11l` level 2 ≈ 233. So cheap solutions do
exist; the walk simply cannot aim at them, and it only reaches the cheap ones by luck.

## F31. What the open research corpus actually contains, and why its numbers do not transfer

`research/openworld` was cloned as reference (gitignored). Its ARC-AGI-3 paper corpus was read in
full; the honest summary is that **~90 % of it is unimplementable here and the headline numbers are
not comparable to this harness**:

* **Six of nine ranked systems need an external LLM API** (baseline1, DreamTeam, TELL, Vision-CL,
  MAP, a-evolve, OpenClaw, Read-Grep-Bash) — dead under `isInternetEnabled: False`. Their budgets are
  real: `e149_discovery_cost.json` records **22.75 M tokens / $44.45 per solved game** (Fable) and
  **81.25 M / $67.22** (Opus), against 11,652 Bash calls and 1,757 Writes.
* **The "25/25 solved" atlas is an OFFLINE, UNBOUNDED-RESET, EXECUTED-PLAN result** and the repo says
  so itself — `arc3_solves.json:67`: *"union of ≥1-level REPLAY-VERIFIED solves under an offline
  protocol (determinism + unbounded resets), NOT the live-agent/RHAE leaderboard protocol."* The
  banked full-game paths run **17–602 actions**, and the shortest full solve in the whole archive
  (`ft09`) is **exactly 80** — the entire budget, for one game.
* ⚠️ `arc3_rhae.json` reports `our_actions = 3` for `r11l` L1 (baseline 22) and claims all 25 games at
  score 100. Three files in that directory give three different solve counts (25 / 2 / 16) and none
  are reconciled. **Treat every number in `arc3_rhae*.json` as an upper bound on a pre-computed plan.**
* **Their own post-mortem is the strongest evidence available.** `e146_retrieve_discover_summary.json`
  is a frozen negative: 3,068 lines, 57 callables, 13 candidate generators (lattice corridors, phase
  corridors, detours, sandbox frontiers, macro tournaments, go-explore archives, hidden-click-state
  probes, semiring macro search) — **"None produced a replay-verified level gain on any unsolved
  frontier."** And `e148_strategy_space.json` correlates levels reached with `simulate` **0.247** and
  `goal_infer` **0.189**, but with `search` **−0.004** and `state_graph` **−0.136**.
* The one *real* solves reported live are **mechanically periodic** — `vc33` L1 = a click triple
  repeated, `lp85` L1 = a click pair repeated (`SOLVING_LOG.md`). And `e119` shows four different
  7–8 B SLMs produced **byte-identical action sequences to the model-free search arm**: the model was
  a no-op wrapper. The SLM/TRM/RTTC/TTT/SOAR document is entirely ARC-AGI-1/2 static-grid work and
  should be discarded.

⇒ Combined with F26 and F30: **blind exploration is a dead end and it has been exhaustively tried by
others at 40–1000× our budget.** The only lever the corpus identifies that also fits 80 actions and is
not yet falsified is an *active, procedure-shaped* hypothesis (the wins are ordered protocols, not
reachable frame configurations), not a better state key.

⚠️ Note `env.step(GameAction.ACTION6)` needs `data={"x","y"}` **when calling the env directly**;
inside this framework `GameAction.set_data({"x","y"})` is correct, because `Agent.do_action_request`
reads `action.action_data` and forwards it as `data=`. Both my agent and the goose use `set_data`.

---

## F32. ⚠️ The hybrid REGRESSED — 0.14 vs the goose's 0.18 — and the planner line is now closed on measurement

```
56641359  COMPLETE  0.18   Official StochasticGoose CNN baseline (Tufa Labs)
56666561  COMPLETE  0.14   Hybrid: planner first, StochasticGoose fallback
```

**The hybrid is 0.04 WORSE than the baseline it was built on top of.** This is the outcome F28 named
and then chose to test anyway, so the record should say plainly which way it went: on the hidden set the
planner's rules **cost** score rather than adding it.

**Why, mechanistically.** The planner was verified on **one level of one public game** (LS20 L1, F19),
and the rerun plays a **hidden set** (F23). So on the hidden games the planner's rule chain
(`_find_block` on an exact 5×5 stamp, `_find_goal` on an enclosed colour-5 region, `_find_collectibles`
on colour-1 lattice cells) fires on **whatever happens to match the pattern** and emits a confident,
wrong plan — and an agent that spends its first actions executing a wrong 13–37 step plan is worse than
one that spends them exploring. F22's own warning (*"a plan was produced" is not "the plan works"*) is
the precise failure, and the fallback could not recover the actions already spent.

⇒ **The planner line is CLOSED**, and closed on a measurement rather than on a prediction. Anything
further on ARC-AGI-3 has to beat 0.18 with a mechanism that is not game-specific.

## F33. ⭐ The leaderboard was read directly, and the regression did NOT displace our score

The public leaderboard downloads fine once the Windows colon problem is handled — the zip entry is named
`arc-prize-2026-arc-agi-3-publicleaderboard-<ISO timestamp>.csv`, and **`Expand-Archive` cannot create a
filename containing `:`, so it fails with `无法处理无效的存档条目`** while `zipfile` in Python reads it
without complaint. Worth knowing, because the failure looks like a corrupt archive and is not.

```
Rank  TeamId     TeamName   LastSubmissionDate      Score  SubmissionCount  TeamMemberUserNames
2357  16978478   p pxl16    2026-09-29 07:08:37     0.18   2                ppxl16
```

⭐ **The board reads 0.18 with `SubmissionCount = 2`** — i.e. it is scoring our **better** submission,
not the newest one. So the 0.14 hybrid did **not** cost us anything on the public board, and no action is
needed now. It also means the safety property we were relying on (the platform picks the better of our
submissions, not the latest) is **verified rather than assumed** for this competition.

| | |
|---|---|
| our rank / score | **2357 / 3477 · 0.18** (was 2346 / 3454 at the same score when the board was smaller) |
| board top | **45.33** (Tufa Labs, 149 submissions) · 36.73 · 26.55 |
| ⚠️ before the deadline | **ensure the 0.18 submission is the one selected.** The CLI has no `select`, so that is a browser action — and it matters precisely because a worse submission (0.14) now exists in the list. |

---

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

---

## F35. ⚠️⚠️ The goose is NON-DETERMINISTIC — so "0.00 local vs 0.18 hidden" was never a calibration

Written 2026-09-30, immediately after F34. This is the most consequential correction in the file,
because **two earlier findings rest on it** and both are now unsupported.

### The measurement

Same agent (`agents/goose_agent.py`, the official StochasticGoose sample), same budget
(`MAX_ACTIONS = 80`), same engine and same `seed=0` per game — two runs:

| run | games | sp80 | OVERALL | wall |
|---|---|---|---|---|
| `--games ls20,r11l,sp80` | 3 | **level 1 solved, level score 115 (the CAP)** | **1.5873** | ~120 s |
| all 25 | 25 | **0.00, level 1 not solved** | **0.0000** | 1009 s |

`score 115` means the goose beat the **human** baseline of 39 actions on `sp80` level 1. In the 25-game
run **the same game produced a flat zero**, and `games with >=1 level: 0 / 25`.

**Why the two runs differ:** the goose has **no seed anywhere in its path** — it initialises a CNN,
refits it every `train_frequency` actions, and samples from its output. Which run reaches `sp80` matters,
because `sp80` is the **19th** game in the 25-game sweep and the **3rd** in the subset, so the global
RNG state on arrival is different. The behaviour is a function of **game order**, not of the agent.

### ⚠️ What this invalidates

1. **F24/F26's calibration claim.** *"The goose scores 0.00 locally, and that is consistent with its
   0.18 on the hidden set … That is the calibration that validates this harness as a predictor"* — the
   0.00 is **one draw from a distribution**, and we have now observed a second draw at **1.59** on a
   subset containing the same game. Two draws cannot calibrate anything, and they do not agree.
2. **The "we beat the goose locally" line.** Our novelty walk's 0.1265 is *deterministic and
   reproducible*; the goose's local number is not a number at all, it is a random variable. Comparing
   a fixed 0.1265 against a single 0.00 draw was comparing a measurement to a sample.

### ⭐ Why it matters strategically: the main argument for "the hidden set is different" is GONE

F6/F23 concluded the rerun plays a **hidden** game set, and the only empirical support was the goose's
`0.00 local` vs `0.18 hidden`. **Run-to-run variance now explains that gap with no need to posit a
different game set at all** — 0.18 is `≈ 4.76/25`, exactly one game's level 1 at human efficiency, which
is what a single lucky draw of this process looks like.

* ⚠️ This does **not** prove the sets are the same. The starter's own comment still says otherwise, and
  the goose is stochastic under *both* hypotheses.
* But it means the project has been treating a **non-reproduction** as evidence, and the honest state is
  that **the question is open** — not settled in either direction.
* It is worth a lot: if the sets are the same, offline oracles are legal at rerun time and the ceiling
  changes completely. If not, only a general mechanism counts, and F34.4 failed to find one.

⇒ **A control submission settles it**, and it is the highest-value ARC experiment available. The design
that actually discriminates: an agent whose **local** score is a known, reproducible number under a
policy that cannot score by accident. If it reads the same on the hidden board, the sets behave alike;
if it reads ~0.18, the hidden set is scoring something our local run does not see.

### ⚠️ Methodology note, and it is the third one today

The 25-game goose run took **1009 s** and, under a `Select-Object -Last N` pipeline, produced **no
output at all** until it finished — an earlier instance was killed at 35 minutes as "hung" when it was
merely slow. **A buffered pipeline makes a working long job indistinguishable from a dead one.**
`-u` plus a background job, or reading the JSON the tool writes, avoids it.

And this is the third correction in one session produced by the same discipline: **re-measure the
number, against the artifact that is actually in the tree, twice, and check it against a known target.**

---

## F36. Submitted `56705048` — and the honest wall behind it: EVERY generic policy solves 1–2 of 25

Written 2026-09-30. Submitted as **`56705048`** (kernel `ppxl16/arc-prize-2026-arc-agi-3-starter`
**version 3, CPU-only**). The user's prompt was that the v2 hybrid reads **0.14** against v1's **0.18**
— correct, it does — and asked for a way to raise it.

### 36.1 ⚠️ The wall: six different mechanisms, all 1–2 games

Every generic policy this project has built, scored through the shipped scorer on all 25 public games
at `MAX_ACTIONS = 80`:

| mechanism | score | games ≥1 level |
|---|---|---|
| novelty walk `1` | 0.1265 | 1 |
| fixed orbit, `rare` / `yx` | 0.1429 / 0.0128 | 1 / 1 |
| **restart search**, K=12 / 20 / 30 / 40 | 0.1429 / 0.1343 / 0.0791 / 0.0521 | 1 / 1 / 1 / 1 |
| portfolio of orbits | 0.1712 – 0.1829 | 2 |
| ⭐ portfolio incl. **dense** coverage | **0.2693** | **2** |
| `dense` alone | 0.0000 | 0 |

**Six families, one ceiling: 2 games out of 25.** That is the real result of this session, and it is
worth stating plainly rather than dressing as progress: *nothing generic we can build in a session
solves more than two of these levels.*

### 36.2 ⭐ Why the goose can beat that: a learned 4096-way coordinate head

Read from `agents/goose_agent.py`, not inferred. Its `ActionModel` has a **coordinate head**
(`coord_conv1..4`, `coord_logits.view(B, -1)` over `64*64 = 4096` cells), and
`_sample_from_combined_output` samples jointly from "5 direction actions + 4096 cells", masked by
`available_actions`. So the goose can click **any cell on the board**, guided by a CNN refit every
`train_frequency = 5` actions with `reward = 1.0 if frame_changed else 0.0`.

**Our agents only ever click 12–16 object centroids.** On `ft09` and `sc25` F34.3 measured that
**every** object-centroid click is a **no-op** — so those two games are unreachable for our agents by
construction, while the goose can still click anywhere. That is a concrete, fixable asymmetry, and it
is the first explanation of the goose's edge that is mechanical rather than "it is stochastic".

⚠️ But fixing it is not obviously a win: the `dense` ordering (64 distinct cells) scores **0.0000
alone**, and only helps as one phase of a portfolio. Coverage of the click space is necessary and
nowhere near sufficient.

### 36.3 The restart mechanism, tested: levels PERSIST across RESET, and it is still only parity

`solve_levels.py` established that **RESET restarts the CURRENT level, not the game** (after finishing
level 1 the reset hash is `4412df0168a89497`, not the fresh `cfe5196fb75182bb`). So completed levels
survive a RESET and the 80-action budget can buy **several independent attempts** instead of one
walk that is stuck where it wandered. `agents/cycle_agent.py --policy restart` implements it:
ARC_K randomized actions, then RESET, with each attempt's candidate order shuffled by attempt number.

Measured: **K=12 → 0.1429, K=20 → 0.1343, K=30 → 0.0791, K=40 → 0.0521.** The score *falls* as K
grows, exactly as the mechanism predicts — `actions_i` is the cumulative count at completion, so
failed attempts inflate the denominator in `100*(baseline/actions)^2`. **Restarts buy independence and
pay for it in RHAE.** Net: parity with a single walk, not an improvement.

### 36.4 The avatar probe: a one-cell sprite IS measurable and trackable

`work/probe_avatar.py` — from a fresh reset, the action whose frame change is smallest
**non-zero** and localised, then 8 presses of it, printing the changed region's centroid:

```
ls20   2:2    62,13 62,14 62,15 62,16 62,17 62,18 62,19 62,20   touched=16
lf52   1:1     0,0  0,1  0,2  0,3  0,4  0,5  0,6  0,7            touched=8
bp35   7:1    63,0 63,1 63,2 63,3 63,4 63,5 63,6 63,7            touched=8
cd82   1:1    63,63 - 63,62 63,61 - 63,60 - 63,59                touched=5
g50t   1:0      - 63,63 - 63,62 - 63,61 - 63,60                  touched=4
```

`ls20` action 2 moves a blob **one column per press, monotonically, mid-board** — a tracked avatar
obtainable in one action with no game-specific constant. ⚠️ **But four of the five march along a
BOARD EDGE** (`lf52` row 0, `bp35`/`cd82`/`g50t` row 63) which is what a UI **cursor** looks like, not
an avatar. So the probe confirms the measurement works and does **not** confirm that what it measures
is the player. That distinction has to be settled before a coverage-navigator is worth building.

⚠️ **Probe bug fixed in passing:** picking the *minimum* diff selects a **no-op** action (diff 0) on
`ar25` and `sb26`; it must be the minimum **non-zero** localised diff.

### 36.5 ⚠️ The overfitting statement, which belongs in the record

**Roughly thirty configurations were scored against the SAME 25 public games, and the best was then
read off.** That is selection bias by construction — the exact error the project's own rule
(*"只在意公榜的分数会对公榜过拟合…要做好本地交叉验证"*) exists to prevent. Two things stop it from being
pure curve-fitting, and neither makes the headline honest:

* the phase **order** matters as much as the set (`dense,rare,xy,area` = **0.2693** vs
  `rare,dense,xy,area` = **0.1429**), so the configurations are genuinely different policies rather
  than relabellings;
* the chosen one solves **2 games**, the joint most of any configuration.

⇒ **The deployed expectation is the family's ~0.15–0.27, NOT the 0.2693 headline.**

### 36.6 SUBMITTED `56705048` — and the CPU route around the GPU quota

```
ref       56705048          PENDING, submitted 2026-09-30 10:40:32Z
kernel    ppxl16/arc-prize-2026-arc-agi-3-starter  VERSION 3, enable_gpu: FALSE
agent     agents/portfolio_agent.py  (sha256[:16] 2f6167ba18888567)
          POLICY=portfolio  ARC_PHASE=20  PORTFOLIO=dense,rare,xy,area   baked as DEFAULTS
verify    the baked file re-scored with NO env vars: OVERALL 0.2693, 2/25 — identical to the sweep
```

⚠️ **The knobs had to be baked in.** `cycle_agent.py` reads its policy from the ENVIRONMENT, and the
rerun has none — so a submission of the raw file would have silently run the `cycle` policy, which
scores **0.0000**. `work/mk_submission_agent.py` rewrites exactly three default lines and asserts each
pattern matched once.

⭐ **The CPU route is the useful discovery here.** Kaggle's weekly **GPU quota is exhausted**
(30.45 h of 30.00, refreshing 2026-10-03) and it is **account-wide**, so a new GPU kernel version
cannot be pushed for *either* project. This agent is numpy-only — 25 games in **12 s** — so it was
pushed with `enable_gpu: false`, and the push returned **no error field**. The goose by contrast needs
torch and took **1009 s** locally. **A CPU-only push is the way to keep shipping ARC kernels while the
RSNA GPU work is frozen.**

⚠️ **What this submission does and does not buy.** The public board keeps our **better** submission
(F33), so the existing **0.18** is not at risk from a weaker one — that makes this a free option on
the public score. It is *not* free on the final selection, which is a browser action, so **the user
must ensure the best of the three is the one selected before 2026-11-02.**

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

---

---
## F39. ⭐ The next mechanism bet: the goose DISCARDS its learner at every level boundary

Written 2026-09-30. F37 proved local CV is not a leaderboard proxy, so nothing here may be chosen by
a local score; it has to be justified by structure. Two structural facts point the same way.

### The two facts

**1. Scoring is PER LEVEL, and later levels weigh MORE.** From F38.2, measured through the shipped
scorer:

```
r11l  total=81  level_actions=[27, 54, 0, ...]  level_scores=[66.4, 0, ...]
```

`27 + 54 = 81` and `100*(22/27)**2 = 66.4`, so `level_actions[i]` is the spend **inside** level *i*.
The game score is `sum(score_i * i) / sum(i)`, so **level *i* counts *i* times** — level 2 is worth
twice level 1, level 3 three times. **The score is in the later levels.**

**2. ⚠️ The goose throws its entire learner away at every level boundary.** `agents/goose_agent.py`,
on every `levels_completed` change (lines 310–321):

```python
self.experience_buffer.clear()
self.experience_hashes.clear()
print("Cleared experience buffer - new level reached")
# Reset network and optimizer for new level
self.action_model = ActionModel(input_channels=self.num_colours, grid_size=self.grid_size).to(self.device)
self.optimizer = optim.Adam(self.action_model.parameters(), lr=0.0001)
print("Reset action model and optimizer for new level")
```

**Level 2 therefore begins with a brand-new, randomly initialised CNN** — exactly what level 1 began
with — despite being *the same game, harder*, sharing its mechanics. Every level re-pays the full
learning cost, and the levels that cost the most to re-learn are the ones worth the most.

### The change, and it is the ONLY change

`work/mk_goose_nolevel.py` removes the two `clear()` calls and the model/optimizer reconstruction,
and prints a marker so the behaviour is observable:

```
if self.action_model is None:   # build ONCE
    self.action_model = ActionModel(...).to(self.device)
    self.optimizer = optim.Adam(self.action_model.parameters(), lr=0.0001)
    print("Built the action model (first level only)")
else:
    print("KEPT experience buffer and action model across the level boundary")
```

`prev_frame` / `prev_action_idx` are **still** reset to `None`, because across a level the frame
changes completely and an `(old_frame, action) -> new_frame` transition would be a lie; that one
transition is dropped and everything learned before it is kept.

**Nothing else is touched**: same `ActionModel`, same reward (`frame_changed`), same
`train_frequency`, same 4096-way coordinate head, same `MAX_ACTIONS`, same sampling.

### ⚠️ The bug the first attempt had, and why it is worth recording

The first build removed the reset block **outright**. That block is also the **only place upstream
ever constructs the model** — `__init__` sets `self.action_model = None` (line 153) and line 315 is
the sole assignment. So `self.action_model` stayed `None`, `self.action_model(...)` raised on **every**
`choose_action`, and the upstream `except` swallowed it into a fallback. The run scored **0.0000 on
every game** and looked like a policy result.

**It was caught only because the file was executed before being believed**, and the crash line
(`[DEBUG] choose_action CRASHED`) had to be *looked for* — it is printed, not raised. The corrected
transform now asserts `self.action_model = ActionModel(` occurs **exactly once**, which is the check
whose absence made the first version silently wrong.

### Verified, and then stated honestly

Sanity run on 5 public games with the mechanism firing:

```
cd82  Built the action model (first level only)
ls20  Built the action model (first level only)
r11l  Built ... / KEPT experience buffer and action model across the level boundary   levels=1
sp80  Built ... / KEPT experience buffer and action model across the level boundary   levels=1
vc33  Built the action model (first level only)
OVERALL score = 1.2017  (5 games)
```

⚠️ **That 1.2017 is NOT evidence.** F37 established that this instrument does not predict the hidde
score — it is *anti*-predictive in the one sample we have. What the run establishes is only that the
change **executes and the intended branch is taken on a real level change**. The bet is read from the
leaderboard.

### Two files, so no reading is confounded

| file | `MAX_ACTIONS` | why |
|---|---|---|
| `agents/goose_nolevel.py` | `inf` (upstream) | the **one-variable** experiment. Needs a GPU kernel push, so it must wait for the quota to refresh on **2026-10-03**. |
| `agents/goose_nolevel_cpu.py` | `1000` | CPU-safe, so it can ship now. Measured cost: the goose is **0.498 s/action** here, so ~8 min/game and ~3.4 h for 25 games; 1000 actions comfortably covers a full game. |

Both differ from upstream in the **same one respect**; they differ from each other only in the cap,
so the pair also prices the cap as a side effect.

### 39.1 State at 2026-09-30 11:45Z

* Kernel **version 4** of `ppxl16/arc-prize-2026-arc-agi-3-starter` is built, pushed CPU-only
  (`enable_gpu: false`, push returned **no error field**) and is **COMPLETE**. It carries
  `agents/goose_nolevel_cpu.py`.
* ⚠️ **The submission was REFUSED with HTTP 400** — the competition allows **one submission per day**,
  and today's slot went to `56705048`. The next slot opens at **00:00Z**. So v4 is *ready*, not sent.
* ⚠️ When submitting, do **not** rebuild the notebook: `build_notebook.py` **re-syncs `enable_gpu=True`**
  into the metadata (observed in this session), which would hit the exhausted GPU quota. Either set it
  back to `False` after any rebuild, or submit `kernel_version=4` exactly as pushed.

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

---
## F41. ⭐⭐ Why we are stuck at 0.18: the top teams run a LOCAL LLM (vLLM) inside the rerun

Written 2026-10-01. Found by sweeping the public surface **including the top teams' own accounts** -- the
same search that found Kaggriculture's `aurax7`. The leaderboard ships `TeamMemberUserNames`, so a top
team maps to a Kaggle account and its public kernels can be listed directly. **Nobody had looked here.**

### F41.1 The top teams have PUBLIC notebooks

| rank | score | user | notebook |
|---|---|---|---|
| **3** | **27.89** | `dfranzen` | `dfranzen/arc-agi-3-milestone-2-solution` (v107) |
| **5** | **23.84** | `lordhansolo` | `lordhansolo/arc-agi-3-milestone-2` (v21) |
| **6** | **22.53** | `sirikilohit` | `sirikilohit/arc-agi-3-duck-18-1gc-submit` (v23) |
| 8 | 20.00 | `richardcsaky` | `richardcsaky/arc-agi-3-milestone-2-submission` (v20) |
| 8 | 20.00 | `cmechevalier` | `face-of-agi-arc-agi-3-rtx6000` |
| 16 | 10.64 | `thomasferraz` | TD-JEPA |

**Every one of those is 55–150× our 0.18.** And the recurring ingredient across the public list is a
**"duck harness + Qwen3-8B"** family (`foysalemonshanto/lb-9-arc3-duck-v12-with-qwen-3-8-27b`,
`chiakazirim/duck-qwen3-8-tuned`, `wuliao0/duck-qwen3-8-anim-base`,
`keithtyser/duck-qwen3-8-flash-next-nvfp4-mtp`) -- i.e. **an LLM**.

### F41.2 ⭐ The mechanism, read out of the rank-5 notebook

`lordhansolo/arc-agi-3-milestone-2` is **generated by the Tufa ARC-AGI Framework (TAAF)** -- *"an
open-source deployment harness from Tufa Labs for running ARC-AGI-3 solvers reproducibly on Kaggle"*.
Its own config cell:

```python
DATASET_SOURCES: list[str] = ["lordhansolo/taaf-kaggle-source", "lordhansolo/vllm-main-e975732-arc3"]
ENABLE_GPU = True
RUN_AS_SUBMISSION = RUN_AS_SUBMISSION or _env_bool("KAGGLE_IS_COMPETITION_RERUN", False)
...
# cell 0: "installs the ARC runtime, makes the bundled TAAF source snapshot importable, runs any
#          solver setup commands, loads the pickled benchmark, and writes results to /kaggle/working"
#          "Kaggle's KAGGLE_IS_COMPETITION_RERUN flag always wins and switches the run into submission mode"
```

**⇒ The competition's winning method is a LOCAL LLM served by vLLM inside the rerun, on a GPU.** The
solver arrives as a **pickled benchmark** plus a source snapshot (`taaf-kaggle-source`), the inference
engine is a **purpose-built vLLM wheel** (`vllm-main-e975732-arc3`), and the run needs
`ENABLE_GPU = True`.

⚠️ **This retro-explains every ARC result this project has:**
* the four submissions (goose 0.18, hybrid 0.14, portfolio 0.08, goose-no-reset 0.18) are all
  **hand-written policy agents with no model in them**;
* F31's open-corpus reading already said **six of the nine ranked systems need an external LLM API**,
  and concluded LLM agents were dead because `isInternetEnabled: False` -- **which was right about the
  INTERNET and wrong about the conclusion**: the model does not have to be called over a network, it
  can be **mounted and served locally**, which is exactly what these notebooks do;
* so the ceiling we kept hitting is not algorithmic at all. It is the absence of a language model.

### F41.3 ⚠️ The blocker, and why it is only a 3-day blocker

**A GPU kernel version cannot be pushed: the weekly GPU quota is 0.00 h account-wide and refreshes
2026-10-03.** `ENABLE_GPU = True` is not optional for a vLLM run -- an 8B model on CPU would not finish
a rerun. So this cannot be started today.

**⇒ The plan once the quota refreshes (and by then 19 days remain before the 2026-11-02 deadline):**
1. pull `lordhansolo/taaf-kaggle-source` and `lordhansolo/vllm-main-e975732-arc3`, and find the model
   dataset the solver loads;
2. reproduce the rank-5 notebook exactly -- **attaching public datasets and re-running a public
   harness is not a trick, it is the intended use**, and it is the same shape as everything we did in
   Kaggriculture;
3. submit, and read the number.

⚠️ **Honest limits, stated before the attempt:** (a) an 8B model in a code-competition rerun is heavy
and may hit the rerun's time budget, which is why the harness carries a `SOFT_DEADLINE_BUFFER_S`; (b)
`dfranzen` (rank 3) and `sirikilohit` (rank 6) use a *different* solver bundle, so "reproduce rank 5"
is one point in a family, not the ceiling; (c) nothing here has been run yet -- this is a read of
public artifacts, and the next step is to make it execute.

### F41.4 What this does to the existing plan

The exact-novelty walk, the F38 mechanism map and the F39/F40 goose experiments are not wasted -- they
are the reason we can say **with evidence** that hand-written policies cap at 0.18 here. But they are
now a **floor, not a path**. The path is the mounted-model one.

---
## F42. ⭐⭐⭐ The complete public recipe: "The Duck" -- an LLM that writes Python, served by local vLLM

Written 2026-10-01. F41 found that the top teams run a local LLM inside the rerun; this is the recipe,
read out of the artifacts rather than inferred. **Every component is public and downloadable.**

### F42.1 What the solver is

`lordhansolo/taaf-kaggle-source` ships `src/ARC3-Inference/README.md`, whose first lines are:

> **# The Duck 🦆** — *the ARC3 inference harness in this repo: a **tool-using solver** that plays
> ARC-AGI-3 games through TAAF. It ties together: TAAF `Benchmark`/`GameAPI` execution; **a local
> OpenAI-compatible vLLM server**, or OpenRouter; **the duck's single `python` tool** with per-game
> saved modules; structured run artifacts for scoring, viewing, and trace export.*

The loop, from the same README: *"the solver gives the duck the latest game state, valid actions,
history, and a Python tool. **The duck inspects the board, writes small bits of code to reason about
it, and calls `action(...)` from inside Python to execute real game actions.**"* The observations it
reasons over are **structured, not pixels**:

* `current_frame.segmentation` -- connected components, object hashes, boundaries, containment,
  adjacency (the *preferred* view);
* `current_frame.ascii` -- a compact symbolic grid for small checks;
* `history`, `previous_frame`, `transitions`, `last_transition` -- before/after reasoning;
* `valid_actions`, and `last_action_result` with `changed_pixels`, `largest_changed_regions`,
  `level_completed`, `game_over`, `run_complete`.

⚠️ *"The raw numeric grid is intentionally hidden from the Python tool."* **That is F30's finding,
independently arrived at**: raw the frame is noise, semantic abstraction is what carries the game.

### F42.2 The model and the serving config

From the bundle's own `preamble.txt`:

```
benchmark.solver: HarnessSolver(label='duck-harness', model='local', analyzer_timeout=900.0,
                    max_runtime_s_per_game=3918.0, concurrency=14,
                    start_local_server=False, local_server_repo_dir='/app/ARC3-Inference')
benchmark.games : 25
git: ARC3-Inference          ca1bd02  clean  solution-improve-qwen38-flash-next
     tufa-arc-agi-framework  ca1bd02  clean  solution-improve-qwen38-flash-next
```

⇒ **the model is a Qwen3.8 variant ("Flash Next")**, matching the public family
`foysalemonshanto/lb-9-arc3-duck-v12-with-qwen-3-8-27b` (**LB-9**, Qwen 3.8 **27B**),
`keithtyser/duck-qwen3-8-flash-next-nvfp4-mtp`, `chiakazirim/duck-qwen3-8-tuned`,
`wuliao0/duck-qwen3-8-anim-base`. Serving, from the README: `server.max_model_len` **81,920** tokens,
`shared.context_window` **73,728**, `analyzer.target_context` **55,296** estimated input tokens,
**14 concurrent games**, and the Kaggle path is documented as *"model=local, 16 concurrent games,
75 minutes per game, and a 90-minute Kaggle"* budget.

### F42.3 Everything needed is public

| component | where | size |
|---|---|---|
| solver source + pickled benchmark | `lordhansolo/taaf-kaggle-source` (20 files: `benchmark_initial.pkl`, `setup_commands.json`, `src/ARC3-Inference/**`) | small |
| vLLM build for ARC-AGI-3 | `lordhansolo/vllm-main-e975732-arc3` (13 files, `apply_vllm_main_e975732_arc3.py` + layer blobs + `runtime-manifest.json`) | ~7 GB |
| the model | a Qwen3.8-Flash-Next dataset (to be identified) | ~15–55 GB depending on quantisation |
| the harness notebook | `lordhansolo/arc-agi-3-milestone-2` (rank 5, 23.84) | pulled |

⚠️ **The GPU quota is still the blocker**: `ENABLE_GPU = True`, a 27B-class model cannot run on CPU,
and the weekly quota is **0.00 h account-wide until 2026-10-03**. That is 2 days, against a deadline of
**2026-11-02**.

### F42.4 What this means for the project, stated once

**Our 0.18 is a floor produced by the absence of a language model, not by a limit of method.** Four
submissions built every generic mechanism this repo could invent -- a novelty walk, a portfolio of
candidate orderings, the official CNN baseline, and the baseline with its learner lifecycle changed --
and the ceiling was identical to the baseline every time. The top teams are 55–150× above that, and
**what they have that we do not is a model that reads a structured board description and writes code.**
The next action is not another policy; it is to reproduce the public stack.

---

## F43. ⭐⭐⭐ The Duck stack is fully identified — and ⚠️ `machine_shape` is SILENTLY IGNORED

Written 2026-10-04, after re-reading the project. Supersedes the "wait for the GPU quota on 10-03"
framing in `STATUS.md`: **quota was never the blocker.**

### F43.1 The complete recipe, read out of the rank-5 notebook

Pulled `foysalemonshanto/lb-9-arc3-duck-v12-with-qwen-3-8-27b` (`work/duck9/`). Its metadata:

```
dataset_sources    ['jakobbrggen/taaf-kaggle-source-anim-20260807-anim',
                    'driessmit1/arc3-vllm-h100-wheelhouse-v3']
model_sources      ['foysalemonshanto/qwen3-8-27b-fp8-repacked-v1/PyTorch/hf-fp8/1']
machine_shape      NvidiaRtxPro6000
enable_gpu         True
```

and cell 3 pins the rest:

```python
QWEN_MODEL_PATH = Path("/kaggle/input/models/foysalemonshanto/qwen3-8-27b-fp8-repacked-v1/"
                       "pytorch/hf-fp8/1")
QWEN_SERVED_MODEL_NAME = "Qwen/Qwen3.8-27B-FP8"
os.environ["HF_HUB_OFFLINE"] = "1"; os.environ["TRANSFORMERS_OFFLINE"] = "1"
```

* **vLLM is started by the bundle's own `setup_commands.json`** (run as shell), not by notebook code.
* The public eval is **25 games × 1 pass**, `concurrency 28`, `max_runtime_s_per_game 7920.0`.
* On a real rerun the notebook switches to Kaggle's live gateway
  (`ARC_BASE_URL=http://gateway:8001/`, `OPERATION_MODE=competition`) and waits up to 600 s for it.
* Everything is public: the TAAF bundle (`jakobbrggen/…anim-20260807-anim`, and also
  `lordhansolo/taaf-kaggle-source`), the vLLM wheelhouse, and the model.

### F43.2 ⚠️ WE CANNOT GET THE HARDWARE — measured, not assumed

A probe kernel (`work/probe-gpu/`, `ppxl16/arc-gpu-probe`) requested
`machine_shape: NvidiaRtxPro6000` and **pushed successfully, ran, and COMPLETE**. What it got:

```
machine: x86_64 | python: 3.13.15
torch: 2.11.0+cu128  cuda avail: True
  dev0 Tesla T4  14.6 GB  cc=7.5
  dev1 Tesla T4  14.6 GB  cc=7.5
```

⇒ **`machine_shape` is accepted by the push and then silently ignored.** Our account is entitled to
**2× Tesla T4 only**. No RTX Pro 6000, no H100.

**This kills the FP8/NVFP4 variants outright, for two independent reasons:** a 27B FP8 model is ~27 GB
against 14.6 GB per device, and **cc 7.5 does not support FP8 at all** (it needs cc ≥ 8.9) — plus the
wheelhouse is literally named `…h100-wheelhouse…`. ⚠️ **It is the same failure class this repo keeps
paying for: a field that is accepted and discarded, with no error.**

### F43.3 What still fits — the quantization is the constraint, not the model

The model catalog is rich. Filtering it by what cc 7.5 can actually execute:

| candidate | note | T4? |
|---|---|---|
| `ugvfpdcuwfnh/qwen3-8-27b-ud-q4-k-xl` | **GGUF Q4_K_XL**, 27B ≈ 16 GB | ✅ not FP8 — and the TAAF source ships **`configs/inference.local.llama.json`**, i.e. llama.cpp is a supported backend |
| `josephayanda/qwen3-8-27b-gptq-w4a16`, `ram2121/qwen3-8-flash-next-gptq-4bit` | **GPTQ W4A16** | ✅ vLLM supports it; GPTQ kernels need cc ≥ 6.0 |
| `dfranzen/intel-qwen3.8-flash-next-w4a16-autoround`, `woochangsim/…w4a16-autoround` | AutoRound W4A16 | ✅ vLLM supports it |
| `keithtyser/…nvfp4`, `nvidia/qwen3-8-flash-next-nvfp4`, `lordhansolo/…mixed-nvfp4-fp8` | NVFP4 | ❌ **Blackwell only** |
| `qwen-lm/qwen3-coder`, `manojkumarcs28/qwen3-8b` | 8B class | ✅ at 4-bit **one T4 is enough** |

⚠️ Two T4s are **separate devices with no NVLink**, so a 27B at 4-bit needs `tensor_parallel_size=2`
over PCIe — workable but slow, and vLLM's Turing path is its least-tested.

### F43.4 The move, stated once

**F42.4's claim is that what we lack is "a model that reads a structured board description and writes
code" — not specifically a 27B model.** The Duck harness is model-agnostic (`analyzer_model` is an env
var). So the tractable version of the public stack is: **the same harness, the same TAAF bundle, with
the largest quantization that actually executes on 2× T4** — a GPTQ/AutoRound W4A16 27B, or an 8B
coder at 4-bit on a single card.

That is a real project (get vLLM up on cc 7.5, confirm the harness's local-server path, run the 25
public games offline, then submit), and it is the only route this repo has found that is not another
policy tweak on a 0.18 floor.

⚠️ **Known-before-starting risks, recorded so they are not rediscovered mid-build:**
1. **`driessmit1/arc3-vllm-h100-wheelhouse-v3` may not import on cc 7.5 at all** — that is the first
   thing to test, not the last.
2. **T4 has no bfloat16** (this session found that independently on the RSNA side: `AMP_PREF='bf16'`
   on a T4). vLLM must be pinned to `float16`.
3. **ARC-AGI-3 allows 1 submission/day**, so the offline 25-game run is the only cheap iteration loop.

