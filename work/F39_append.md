
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
