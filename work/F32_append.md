
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
