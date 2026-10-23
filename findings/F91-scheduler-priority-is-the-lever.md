# F91 — 找到了"饿死"的正解：**调度优先级**（不是模型，不是补丁，不是参数）

写于 2026-10-23。这是转向 ARC 后第一个**有独立理由、可移植、且别人已经验证过方向**的改动。

## 1. 先排除了两个看起来最有希望的方向

| 方向 | 结论 |
|---|---|
| **换更大的模型（27B）** | **排除。** 公开面有 `qwen3-8-27b-fp8` 等若干镜像，但**榜上 33.55 / 33.22 / 32.59 那三本挂的模型与我们完全相同**（`dfranzen/intel-qwen3.8-flash-next-w4a16-autoround` + 同一个 drafter）。头部都在用小模型 ⇒ **模型不是差异所在**，33.55 与 29.34 之间主要是抽样（F81）。 |
| **换更好的 harness 补丁** | **排除。** `tantan0327/arc3-franzen-dprime`（**33.55**）的 patch cell 与我们的**同为 498,799 字符、只差 11 个排版字符**（与 F85 对 heliosli 的结论一模一样）。 |

**而且两本在【提交路径】上的配置完全相同**：`concurrency=120`、`max_runtime_s_per_game=532*60`、`n_passes=1`（`TRUE_SUBMISSION` 分支里都强制）。

## 2. ⭐ 差异在一个我没想到的地方：**哪个游戏拿到下一个 LLM 槽位**

那本比我们**多一个 8.3 KB 的 cell**，自述逐字：

> *"What it replaces: **ONLY the number the scheduler uses to decide which waiting game gets a freed LLM slot**
> (`tool_agent.priority_value`, called by `_PriorityGate._snapshot_priority`), the per-game pace tracker it reads
> (`tool_agent.ProgressPace`), and optionally the rule that never-started games always jump the queue."*

公式来自 Osaka Metropolitan **"Affectify"（shiiin9）** 的公开笔记本：**`priority = A·M·C + B·phi`**。
cell 里带三套实现：`base`（franzen 原式）、`dprime`（上述公式）、`ours`（他们自己在**离线调度模拟器** `sched_sim.py` 上调参的参数族）。

**⇒ 这正是 F88/F89 量化到的失效模式**：110 个游戏抢 **10** 条活跃流，`lf52` / `g50t` / `wa30` 的**每关动作数是 `[13, 94, 0,0,0,…]`** —— 不是打不动，**是没轮到**。
⇒ **修法不是加算力，是换分配规则。** 这是本项目第一次找到"针对已观测失效模式的直接修法"。

## 3. 顺带解开了 F90 的谜

他们离线用的是 **`n_passes = 1`** 且 **`demo_excluded_games` 排除 15 个最难的游戏**（只跑 10 个）；我们跑满 **25 个 × 4 轮**。
⇒ **我们把那些必然 0 分的游戏也平均进离线分**，这就是同配置重跑能从 58.46 掉到 47.22、还有一轮整体 0.00 的来源。
⇒ **F90 的结论不变（离线分不能当标尺），但原因更具体了：不是标尺坏，是我们喂给它的样本里塞了必然失败的项。**

## 4. 已做与计划

- **`ppxl16/arc-pri-dprime` 已构建并跑完**：**只插入那一个 cell**（逐格逐字节审计：23→24 格，其余全等），
  cell 逐字复制、`ARC3_PRIORITY_FORM='dprime'` 由它自己设置。**状态 COMPLETE ⇒ 无异常 ⇒ 崩溃检查通过。**
- **今天那抽（`57544435`）= 26.02** 已用完（交的是原版内核）。⇒ **pri-dprime 的线上一枪要等 UTC 00:00 额度重置。**
- **每 2 小时的自动刷新已挂上**（`schedule`，因为我没有自我唤醒能力，回合结束后台任务就随之结束 —— 这是"卡住"的真正原因）。

## 5. 判据（预先写下）

pri-dprime 的线上结果是**一次抽样**，与基线分布（13 次：mean 25.26、sd 2.71）比较：
- **≥ 30.85**（铜线）⇒ 立刻成为主内核，剩余抽样都用它;
- **≥ 29.34**（追平最好）⇒ 视为"不差"，再给一次抽样;
- **≤ 27** ⇒ 与"调度不是问题"一致，退回原版，剩余抽样只抽不改。

**⚠️ 一次抽样无法证明一个改动有效** —— 这只是"值得花一次去试"的依据（独立理由 + 别人的 33.55 与之同向），不是"已知更好"。
