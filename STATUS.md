> # ⛔ 本页已过时 —— 见 [F47](findings/F47-score-is-22-48-not-0-18.md)
>
> **2026-10-06 核实：我们的公榜分数是 22.48、rank 862/3866，不是本页写的 0.18 / 2373。**
>
> 那条 **22.48** 是 **2026-10-04 04:11** 提交的（ref `56813776`，**描述字段为空**），
> 跑的是 `dfranzen/arc-agi-3-milestone-2-solution` 的副本 —— 用的是 **W4A16（int4）** 模型，
> **不需要 Blackwell**。⇒ 本页"为什么停在这里"整节、以及 F44 的"CLOSED"结论，
> **都建立在一条已被实测取代的推断上。**
>
> 本页以下内容作为**当时**的记录保留，不要当成现状。

# ARC Prize 2026 — ARC-AGI-3 — STATUS (2026-09-30 11:30Z)

Workspace: `D:\kaggle\arc\` (starter at `D:\kaggle\arc\starter\`, competition data at `D:\kaggle\arc\comp\`).
**Latest: F37/F38 — the 0.08 PROVED the hidden set is not the public 25, and local CV is not a proxy.**

## 🔜 READY TO SUBMIT at 00:00Z: kernel v4, the goose with its per-level learner reset REMOVED

⭐ **The next mechanism bet (F39), and it is structural rather than tuned.** Two measured facts point
the same way:

1. **Scoring is PER LEVEL and later levels weigh MORE** — level *i* counts *i* times (F38.2), so the
   score is in levels 2+.
2. ⚠️ **The goose discards its entire learner at every level boundary** — `goose_agent.py` lines
   310–321 call `experience_buffer.clear()`, `experience_hashes.clear()`, and construct a **brand-new
   randomly initialised `ActionModel` + optimizer**. So level 2 re-pays the full learning cost, even
   though it is *the same game, harder*.

⇒ `agents/goose_nolevel_cpu.py` keeps the buffer, model and optimizer across a level change. That is
the **only** difference from the official sample.

```
kernel   ppxl16/arc-prize-2026-arc-agi-3-starter  VERSION 4, enable_gpu FALSE, push had NO error field
status   COMPLETE  — but the SUBMISSION was REFUSED (HTTP 400): 1 submission/day, next slot 00:00Z
verify   the intended branch fires on a real level change ("KEPT experience buffer and action model
         across the level boundary") on r11l and sp80; model is built ONCE ("Built the action model
         (first level only)")
```

⚠️ **Do not rebuild the notebook before submitting** — `build_notebook.py` re-syncs `enable_gpu=True`
into the metadata (observed), which would hit the exhausted GPU quota. Submit `kernel_version=4` as
pushed, or set `enable_gpu` back to `False`.

⚠️ **A bug the first build had, worth knowing**: the level-change block is the **only** place upstream
constructs the model (`__init__` sets it to `None`), so deleting it outright left `action_model = None`
and **every** `choose_action` raised into the upstream's swallowed `except` — a silent 0.0000 on all 25
games that looked like a policy result. Caught only by running the file. The transform now asserts the
constructor appears exactly once.

`agents/goose_nolevel.py` (`MAX_ACTIONS = inf`, upstream-faithful, the clean one-variable experiment)
must wait for the GPU quota to refresh on **2026-10-03**.

## 🔴 READ THIS FIRST


```
0.18  official StochasticGoose        generic, learns online, no hand tuning   <-- OUR BEST, still on the board
0.14  hybrid (planner first, goose)                                           -0.04
0.08  portfolio of candidate orderings  (local 0.2693!)                       -0.10
```

**Three submissions, monotonically worse in exactly the order of how much hand-tuning was added.**
The platform keeps the **best**, so the board still reads **0.18** (`SubmissionCount 3`) — nothing was
lost. But:

* ⭐ **The 0.08 PROVED the hidden games are NOT the 25 public games.** `portfolio_agent.py` is
  **deterministic** (no RNG on the portfolio path; re-measured byte-identically before submitting),
  and a deterministic agent cannot score 0.2693 on a set and 0.08 on that same set. F35's open
  question is **closed by measurement**.
* ⇒ **Local CV on the public 25 is NOT a leaderboard proxy.** F24's "it was never a proxy" is true
  about the METRIC and false about the LEADERBOARD. In the one sample we have it was even
  **anti-predictive**: the best local score produced the worst hidden score.
* ⚠️ **~30 configurations were swept on the public 25 to pick that agent.** That sweep was fitting
  noise by construction. **Stop selecting on the local score.**

## ⭐⭐ The structural fact that governs everything: scoring is PER LEVEL

```
r11l  total=81  level_actions=[27, 54, 0, ...]  level_scores=[66.4, 0, ...]  baselines=[22, 33, 51, ...]
tn36  total=81  level_actions=[30, 51, 0, ...]  level_scores=[113.8, 0, ...] baselines=[32, 72, 26, ...]
```

`27 + 54 = 81` and `100*(22/27)**2 = 66.4` ⇒ **`actions_i` is the spend INSIDE level `i`, not
cumulative.** So: actions after a level completes are **free**; every level has its **own** budget;
and **later levels weigh MORE** (level *i* counts *i*).

⇒ **The competition is SEQUENTIAL LEVEL SOLVING, and level 1 — the only level any agent here ever
completes — is worth the LEAST.** One game solved at human speed through level 2 scores
`100/21 + 2*100/21 = 14.3`, i.e. **0.57 overall from ONE game**.

## ⚠️ Two "obvious fixes", both measured — one neutral, one HARMFUL

| fix | result |
|---|---|
| **raise the 80-action cap** (the goose uses `inf`) | ⚠️ **CHANGES NOTHING** — 0.1905 / 0.1905 / 0.1905 at caps 80 / 400 / 1200, with total actions rising 2025 → 30025. The agents finish level 1 inside 80 and never finish level 2, and an uncompleted level scores 0, so there is no level the extra actions could add to. **F37.3 was wrong in practice.** |
| **widen the click space** (goose uses 4096 cells, we use 12–16) | ⚠️ **HARMFUL** — 12 → **0.1905** (2 games), 16 → 0.0722 (1), 48 → **0.0000** (0). With no learner, success falls ~`1/|A|^k`, so widening multiplies the search. The goose affords 4096 coordinates only because it **learns a distribution over them**. |

## What is left, without optimism

* Our best hidden score is still **0.18**, from the **generic** baseline. Every hand-built deviation
  scored worse, and both obvious fixes are now measured as neutral/negative.
* **There is no valid local instrument**, so any further submission is a **mechanism bet**.
* The two bets with a real argument: **(1) a LEARNER, not a policy** — the goose wins by learning
  online from the frame-change signal; the exact-transition novelty model computes that same signal
  without learning and is the one cheap candidate never submitted. **(2) SEQUENTIAL LEVEL SOLVING** —
  the payoff is in levels 2+, which nothing here has ever completed.

## Board / limits

| | |
|---|---|
| Competition | ARC-AGI-3, code competition, **$850,000**, deadline **2026-11-02 23:59Z** |
| Daily submissions | **1** (next slot after 00:00Z) |
| ⭐ Our board | **Rank 2373 / 3497 · 0.18 · SubmissionCount 3** — the platform scores the BEST, verified twice |
| Board top / median | **45.33** / **0.32** — top 10 % needs **3.80** |
| ⚠️ User action before 2026-11-02 | **Ensure the `0.18` submission is the SELECTED one** (browser; the CLI has no `select`) — it now has to be picked out of four |

⚠️ **A CPU-only kernel push works while the weekly GPU quota is exhausted** (30.45/30.00 h,
account-wide, refreshing 2026-10-03) — which is how `56705048` shipped at all. Our agents are
numpy-only (25 games in 12 s) against the goose's 1009 s.

## 🛠️ Tooling

| script | what |
|---|---|
| `tools/score_local.py` | the shipped scorer against the real baselines — ⚠️ **scores the public 25, which are NOT the hidden games** |
| `agents/generic_agent.py` | ⭐ the F38 experiment: exact novelty, wide/narrow click prior, configurable cap |
| `agents/novelty_agent.py` | the F26 walk — 0.1265 local, **never submitted** |
| `agents/portfolio_agent.py` | the F36 submission (0.08) — kept as the counter-example |
| `work/probe_motion.py` / `work/probe_avatar.py` | the mechanics map; is a moving sprite trackable? |
| `work/mk_submission_agent.py` | bake env knobs into a standalone submission (the rerun has no env) |
| `install_agent.py` → `starter/scripts/build_notebook.py` → `kernels_push` → `competition_submit_code` | the submission path |

⚠️ **Use `OperationMode.OFFLINE`**; pass `data={"x","y"}` to `env.step` for ACTION6 (`set_data` alone is
only correct through `Agent.do_action_request`). ⚠️ **`env.step` can return a degenerate frame** — never
answer it with a constant action.

## ⚠️⚠️ Do not read a command's success from TRUNCATED output

**`Select-Object -First N` — and any early-terminating pipeline stage — KILLS the upstream process, so
PowerShell reports a non-zero exit code.** A truncation therefore looks *exactly* like a real failure.
Every command in this session was piped through `Select-Object` / `Select-String`, so the exit code was
never once checked. Two runs that showed a red *"exit code 1"* were re-run with output redirected to a
file — `work/inspect_ckpt.py` and `scripts/lb_ceiling.py` — and both returned **0 with empty stderr**;
the red was the pipe, not the command.

**The rule from here on:**
1. Redirect to a file and read the file (`cmd > out.txt 2> err.txt`); do not truncate the pipeline.
2. **Print `$LASTEXITCODE` explicitly** and say what it was, in the same message as the conclusion.
3. Read stderr even when stdout looks right, and prefer a **reproducibility check** (run twice, diff)
   over eyeballing — `inspect_ckpt.py`'s output was confirmed bit-identical across two runs.
4. This is the same bug class as the failed import, the dropped `ACTION6` coordinate and the refused
   `kernels_push`: **a silently-swallowed failure reported as success**, one level up.

