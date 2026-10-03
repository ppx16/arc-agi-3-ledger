
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
