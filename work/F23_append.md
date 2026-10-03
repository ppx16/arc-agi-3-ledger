
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
