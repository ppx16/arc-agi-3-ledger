
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
