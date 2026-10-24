# F93 — 公开面**全部**关着一个文献公认的核心机制：`ARC3_MEMORY_SECTIONS=off`

写于 2026-10-24。这是接手 ARC 以来第一条**同时具备**"文献背书 + 一行配置 + 公开面无人做过"的候选。

## 1. 代码自己怎么说的

harness patch 里有一个 `_memory_sections_disabled()`，它的 docstring 逐字：

> *"`ARC3_MEMORY_SECTIONS=off` **removes the persistent-memory mechanic entirely**: no carried block,
> no section guidance, no nudges, no parsing, and the world-model lines drop out of the system prompt too.
> **The model is left to reason from history alone, which is what an unmodified run does before any of this
> machinery existed.**"*

⇒ **`off` = 回到"这套机制还不存在"的裸状态。** 也就是说：**harness 作者专门做了一个跨回合的持久世界模型机制，然后把它关掉了当默认值。**

## 2. 机制本身（从代码读出来的）

| 模式 | 携带的分区 |
|---|---|
| `off` | 无（裸跑） |
| **`slim`** | **`World model` + `Plan`** —— 代码注释：*"the two the model actually maintains"*、*"ages far better than `Recent findings:` or `Open questions:`"* |
| `medium` | `World model` + `Plan` + `Action model` |
| 其它任何值 | 全部分区（World model / Goal model / … / Cross-level notes） |

开启后增加：**carried block**（跨回合携带的文本块）、**section guidance**（怎么写这些分区的说明）、**nudges**（提醒模型更新）、**parsing**（从回复里解析出分区）。
`World model:` 的定义逐字：*"durable RULES of the environment that will still be true many actions from now (mechanics, what objects/colors mean, movement rules, win conditions) - never current positions, events, or what just happened."*

## 3. 为什么这条值得一次抽样

1. **文献一致**：ARC-AGI-3 的公开研究几乎都指向同一件事 —— **给 agent 一个显式、可维护的世界模型**
   （[OPINE-World](https://browse-export.arxiv.org/abs/2607.01531)、[Tycho](https://export.arxiv.org/abs/2607.28287)、
   [Sensi](https://browse-export.arxiv.org/abs/2603.17683)、[Executable World Models](https://dl.acm.org/doi/10.1007/978-3-032-33195-3_15)）。
   我们这个 harness 里**已经有这个机制的实现**，但它是关的。
2. **公开面无人开过**：我们与 32.60 / 33.55 两本的 `setup_env` 逐键相同（F91 的 diff：只差 `n_passes` 与 `demo_excluded_games`）
   ⇒ **1638 位公开参赛者用的是同一个"裸跑"配置。**
3. **改动面最小**：**只改 `setup_env` 里的一个字符串**，不插入代码、不改补丁、不动模型 ⇒ 崩溃风险
   远低于 pri-dprime（那是插入 8.3 KB 的 monkey-patch，F92 证明它线上会死）。

## 4. 反面（必须一起写）

- **它增加每动作的 token 成本**（携带块 + 指导 + 提示），而 F88 已证明**预算才是瓶颈**：
  最难的游戏在 `[13, 94, 0, 0, …]` 就断掉。⇒ **每动作更贵 ⇒ 动作更少 ⇒ 可能更差。**
- 这是**两个方向的合理推断**，而按本项目的记录，机制说得通的方向**五次里错了五次**（C195/C197/C201/C203/C204）。
- 我们的离线标尺还不可信（F90），所以**没有免费的办法判断方向**。

## 5. 决定与顺序

**候选改动排序（下一天的那一抽给谁）**：
1. **`ARC3_MEMORY_SECTIONS='slim'`** —— 首选。理由如上：文献背书、公开面无人做、一行改动、崩溃风险最低。
   选 `slim` 而不是全开，是因为代码注释说这两节是"模型真正会维护的"、且更难退化。
2. `ARC3_MEMORY_SECTIONS='medium'` —— 若 slim 有信号再进一步。
3. 退回原版只抽不改。

**⚠️ 与 F92 的关系**：即便如此，**任何内核改动都可能换来一次 0.00**。所以这一抽的期望是：
`P(明显提升) × 收益 − P(崩掉) × 一次抽样`。**若当天是最后几次之一，就不该试；现在还剩 8 次，可以试 1 次。**

**判据（预先写下）**：
- ≥ 30.88（铜线）⇒ 立即扶正，剩余全用;
- 29.34 ~ 30.87 ⇒ 与最好持平，**不算成功**（因为 sd 2.7 内无法与抽样区分），退回原版;
- ≤ 27 或 0.00 ⇒ 关闭这条轴，剩余只抽不改。

---

## 6. ⚠️ 侦察结果对本文的修正（2026-10-24，recon 交付）

econ 普查了 **27 本 ≥30 分的公开笔记本**（rc/recon/RECON.md），结论对本文有三处修正：

1. **"没人开"是事实**：**0/27** 本开启 ARC3_MEMORY_SECTIONS（25 本显式 off，2 本不用 setup_env）。
2. **但"没人想到"是错的**：我们 patch 里 _memory_section_labels() 的 docstring **记录了 25 局的 section 写入频次**
   —— World model 351 次、Plan 255、Open questions 25、Action model 10、Goal model 9、
   **Cross-level notes 0**，并说明被丢的正是"写一次就不再更新却被当现状 re-inject"的陈旧项。
   ⇒ **off 更像是【试过、量过、主动关掉】，而不是遗漏。** 这条把我的先验从"弱正"降到"未知偏负"。
3. 另有 6 个 WM 相关 knob（ARC3_WM_WIPE_ON_LEVEL / WM_WIPE_ON_GAME_OVER / WM_REVISE_NUDGES /
   WM_REBUILD_NUDGE / WM_NUDGE_TURNS / MEMORY_SECTION_MAX_CHARS）**我们的 patch 全支持、只是 setup_env 没列**
   ⇒ 要试是**纯 knob 实验**（不插代码），风险低于 F92 那种补丁。

**⇒ 本文第 5 节的排序因此下调**：slim 不再是首选，让位给 F94 的**模式判定修复**（那条直接保护剩余抽样）。
