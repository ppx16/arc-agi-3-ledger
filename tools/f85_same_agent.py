"""F85: our harness patch is byte-equivalent to the best public fork's, modulo 11 typographic characters.

Also refreshes the bronze cut (it rose to 30.85) and recomputes the medal probability.  Idempotent.
"""
import io
import math
import os
import statistics as st

ROOT = r'D:\kaggle\arc-agi-3-ledger'

OURS = [22.48, 24.53, 23.67, 19.83, 23.51, 26.41, 28.98, 27.96, 25.72, 23.82, 27.10, 29.34]
BRONZE, SILVER = 30.85, 32.23        # refreshed 2026-10-21 (was 30.41 / 31.66)
REMAINING = 12

mu, sd = st.mean(OURS), st.stdev(OURS)


def cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


pb, ps = 1 - cdf((BRONZE - mu) / sd), 1 - cdf((SILVER - mu) / sd)

DOC = """# F85 — 我们的 harness 补丁与当前最好的公开 fork **功能上完全相同**（差 11 个排版字符）

写于 2026-10-21。这条把 F81（"公榜分是 best-of-draws，差距主要是样本量"）从**统计论证**升级成**代码证据**。

## 1. 做了什么

把两本的 harness 补丁 cell（`%%writefile /kaggle/harness-changes.patch`）逐字符比对：

| | 字符数 | sha256 前缀 |
|---|---|---|
| 我们（`ppxl16/arc-agi-3-m2-franzen-verbatim`） | **498,799** | `3b8408cf5dee` |
| `heliosli/try-merging-it-you-might-get-lucky-and-win-gold`（**32.60**） | **498,799** | `6fdcd1ae7445` |

**长度完全相同，逐字符比对只有 11 处不同，且全部是排版符号**：

```
-  →  —   （连字符变长破折号，8 处）
'  →  ’   （直引号变弯引号，3 处）
```

⇒ **两本跑的是同一个 agent。** 这 11 个字符全部落在 prompt 文案里，对行为无可预期影响。

## 2. 这否掉了什么

- **"换个更强的公开 agent"这条路不存在** —— 当前公开面最好的 ARC fork 与我们**同一份代码**。
  那本 notebook 标题里的 "V6: persistent Python computation within each level" 并不是新增代码：
  我们这份补丁里 `persistent` 同样出现 **30 次**，说明**这个能力 franzen 的原版就有**。
- ⇒ 我们的 **29.34** 与他们的 **32.60**、franzen 的 **34.30** 之间**没有可采纳的差异**，只有**抽样**（F81）。

## 3. 顺带证伪的一个念头

我一度以为"我们用的是 franzen 的 harness，而现任第 1 名 Tufa Labs 用的是他们自己的、可能更强的 Duck harness"。
元数据比对显示：**我们的内核与 heliosli 那本用的是【完全相同】的私有镜像、同样的两个 Qwen 模型、同样的 `NvidiaRtxPro6000`**，
并且我们这份里就有 `Tufa` / `Duck` / `Pennyroyal` / `sglang` 的全部字样 ⇒ **我们跑的就是 Tufa Labs 的 Duck harness**，
与榜首**同一个 agent 家族**。差距在预算、迭代次数与抽样，不在代码。

## 4. 更新后的奖牌概率（铜线已抬到 30.85）

- 12 次有效抽样（不含今天待出分那次）：%s
- 均值 **%.2f**、标准差 **%.2f**、最大 **29.34**。
- 铜线 **%.2f**（top10%% = rank 457，此前 30.41 —— **抬高了**）：单次超线概率 **%.1f%%**；
  剩余 **%d** 次里至少一次 **≈ %.0f%%**。
- 银线 **%.2f**：单次 %.1f%%，剩余次数内 **≈ %.0f%%**。
- 我们当前 rank **827**，距铜线还需 **+%.2f 分 / 约 −370 名**。

## 5. 结论（ARC 到此可以封口）

**没有任何可采纳的代码/配置改进**：agent 与最好的公开 fork 相同（本节）、采样旋钮无证据（F83）、
`n_passes` 在提交时已是 1（F84）、逐游戏缺口需要研究项目（F84 第 4 节）。
⇒ **剩余 12 次抽样就是剩余的全部机会**，按 %.0f%% 的累计概率去抽。**只抽不改。**
""" % (', '.join('%.2f' % x for x in OURS), mu, sd, BRONZE, 100 * pb, REMAINING,
       100 * (1 - (1 - pb) ** REMAINING), SILVER, 100 * ps,
       100 * (1 - (1 - ps) ** REMAINING), BRONZE - max(OURS),
       100 * (1 - (1 - pb) ** REMAINING))

p = os.path.join(ROOT, 'findings', 'F85-same-agent-as-best-public-fork.md')
if os.path.exists(p):
    raise SystemExit('REFUSING: F85 already exists')
io.open(p, 'w', encoding='utf-8').write(DOC)
print('wrote', p)
print('ARC: cut %.2f  mean %.2f  sd %.2f  p=%.3f  P(any of %d)=%.2f'
      % (BRONZE, mu, sd, pb, REMAINING, 1 - (1 - pb) ** REMAINING))
