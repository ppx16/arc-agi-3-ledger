# F60 — 2026-10-11 — Long-range restart: the honest state, the reproducibility probe, and one bet shipped

**Trigger**: the user pointed out that work stopped at 14:00 instead of being planned long-range.
A cross-competition plan now exists at `D:\kaggle\PLAN-2026-10-11-longrange.md`.

## 1. Where ARC-AGI-3 actually stands (measured, 2026-10-11T13:45Z)

| | |
|---|---|
| Teams | **4139** |
| Our best | **24.53** (ref `56883490`) — rank **1155** |
| Second try | 23.67 (ref `56909422`, the same recipe re-run) |
| Board top | **62.96** (Yi-Chia Chen) · 56.52 (Tufa Labs) · 45.00 (mtg) |
| Median | 0.91 |
| **Bronze = top 10%** | **29.92** ⇒ **we are −5.4 short** |
| Deadline / budget | 2026-11-02 23:59Z (**22.4 days**) · **1 submission/day** |

⚠️ **The two rows 24.53 and 23.67 come from the SAME recipe.** ARC grading replays against a
**live** game set, so the score is stochastic per run and the platform keeps our best. Two
consequences that govern everything below:
1. re-submitting a recipe is **upside-only** (nothing is lost);
2. a single number is **not** a measurement of a recipe — it is one draw.

## 2. What our 24.53 is

It is a copy of `dfranzen/arc-agi-3-milestone-2-solution` (F47 corrected this page's ancestor
from the stale 0.18 era). **We are running someone else's recipe** — the same starting position
RSNA was in before we forked our way from 0.950 to 0.954.

## 3. Reproducibility probe of the public surface (the C119 rule, applied to ARC)

Every candidate was pulled and its dataset slugs inspected for the **empty-slug tell** (an empty
slug = an invisible private dataset, FACTS C119/C132):

| kernel | datasets | verdict |
|---|---|---|
| `jeroencottaar/tufa-labs-duck-harness-june-30-milestone-winner` | 3, **2 EMPTY** | ⛔ **NOT reproducible** |
| `dfranzen/arc-agi-3-milestone-2-solution` | 2, clean | ✅ reproducible (= what we already run) |
| `rajrajak99/cprs-arc-agi-3-super-agent-v23-apex` | 2, clean | ✅ reproducible |
| `hitarthjain0/arc-agi-3-apex-cognitive-superstack` | 2, clean | ✅ reproducible |
| `kozykappa/arc-agi-3-flashnext-duck-audited-submission` | 2, clean | ✅ reproducible |
| **`fabioolival/arc-agi-3-v21-taaf-27b`** | **2, clean** | ✅ **reproducible** |

⭐ **The structural finding**: almost every reproducible ARC kernel attaches **the same two
datasets** (`dfranzen/pennyroyal-v253` + `dfranzen/taaf-kaggle-source-bundle-copy`) — i.e. they
are all **variations on the recipe we already run**, so they cannot be a step change.

⭐ **The one exception is the duck-harness family** (Tufa Labs — board #2), and the canonical
Tufa notebooks are **private**. `fabioolival/arc-agi-3-v21-taaf-27b` is the **only reproducible
member**: it is the duck harness + a Qwen3.8 27B served through vLLM, from two public datasets
(`keithtyser/taaf-duck-qwen38-serving-v1`, `driessmit1/arc3-vllm-h100-wheelhouse-v3`), needing
**no internet**.

## 4. The bet shipped

`work/make_arc_duck_kernel.py` → `kernels/kernel-arc-duck` → **`ppxl16/arc-duck-taaf` v1 pushed**
(17 cells, round-trip identical, GBK-safe, `machine_shape: NvidiaRtxPro6000`).

⚠️ **Its own cell 0 warns us**: this readable version has **not** reproduced the authors'
milestone-winning score ("unfortunately, we haven't had the same **lucky** result with this one").
⇒ **It is a bet, not a guarantee** — which is precisely why it deserves one daily submission
rather than a rebuild. It is also the strongest reproducible harness on the board, and the
downside is bounded because the platform keeps our best.

## 5. Standing rules for the ARC workstream

1. **Never select on the local 25** (F37/F38: local CV was *anti*-predictive).
2. **File-probe before believing a title** — including scores and "winner" claims (C119/C132).
3. **One variable per submission**, pre-registered, then read the server number.
4. Recall that the number is **one draw from a live set**; do not over-read small differences.
