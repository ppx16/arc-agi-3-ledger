# RULER — 离线标尺的可重复性判定 + 无模型调度模拟器

写于 2026-10-24。任务 = shared task-3。数据全部来自既有 `benchmark.json`（只读），写入只落在
`D:\kaggle\arc\exp\`，没有改内核、没有提交、没有碰 `arc-agi-3-ledger/` 与 `rsna-knee/`。

---

## 0. 一句话结论

**在"只保留 10 个非排除游戏 + 每轮单独统计"的子集上，标尺的噪声没有降到可用水平：轮间 sd =
4.6 分（子集）/ 5.5 分（全 25 游戏），都 > 3；而子集均值已经到 90/100、历史最好 94.17，天花板只剩
5.8–10 分。⇒ 这份标尺不能用于我们关心的 2–5 分改动的 A/B。** 能读得出来的最小效应是：
同一配置两臂各 4 轮离线跑，`|Δ| ≥ 6.5 分`（子集）/ `≥ 7.8 分`（全 25）；`n_passes=1` 时
`|Δ| ≥ 13.1 分`（子集）/ `≥ 15.6 分`（全 25）。前提还必须是"没有基础设施故障轮"（下面 §4 给检测规则）。

**F90 的 11.24 分差距已被定位到一次可检测的启动故障**（不是游戏集噪声）：diag2 第 0 轮 25 个
game-run 全部 `solver_note = "analyzer failed 11 times consecutively"`、wallclock 只有 1171–3507 s
（正常约 29 000 s）、tokens = 0。把这**一个**坏轮剔除后，同配置重跑的子集读数是 88.78 vs 91.66，
差 2.88 分（SE 3.38，z = 0.85）—— 即在噪声内。⇒ 标尺的问题具体是三条：**故障轮（可检测）、
每个 pass 4.6–5.5 分的波动、子集天花板**，而不是"它完全随机"。

**调度模拟器（无模型）的结论：** 用两份真实 trace 抽出每游戏每关的动作/token 成本，按 harness 的
gate 机制（10 个槽、fresh-first、tail fade、上下文 trim 后 handover）模拟固定 token 预算下的分配：

| 场景 | base 总通关 | dprime 总通关 | Δ |
|---|---|---|---|
| 线上 110 游戏 × 1 pass（B = 19.7M tokens） | 464.6 | 378.6 | **−86.0（−18.5%）** |
| 我们的离线 25 游戏 × 4 pass（B = 17.9M） | 449.2 | 396.3 | **−52.9（−11.8%）** |

dprime 在所有 8 个敏感性场景里都更差（−38 到 −87 关），P(dprime > base) = 0.00。原因是
`PRICE_FRESH=1`：dprime 公式给"从未开始的游戏"的定价（≈17.0–18.6k）低于"已开始且已通关过一关的
游戏"，于是它不再像 base 那样把 110 个游戏轮流各跑一段，而是集中喂已开始的游戏——线上有 **41.4/110
个游戏一次都没轮到**（base 只有 2.2 个），直接丢掉这些游戏的 4–5 关。**换公式本身没用**
（`dprime_band` = 保留 fresh-first 只用 dprime 公式：+0.8 关），**去掉 fresh-first 才是效应来源**。
反过来，一个"知道难度配方"的 greedy 优先级能把线上总通关提高 **+38.7 到 +46.8（+8.3%–10.1%）**，
oracle 上界 **+23%** ⇒ 调度**确实有**可挖空间，但**不是**公开的 dprime 这条规则。

> 注意：模拟器只说"在这种无模型分配模型下"，不含"模型在同一个游戏上连续跑会更聪明"这一唯一可能让
> dprime 翻盘的通道（这条通道离线没有数据可标定）。所以它是"dprime 的期望效应大概率为负"的证据，
> 不是"dprime 一定负"的证明；但它足以把"按 33.55 的同向相关去押注 dprime"这件事降级为**不该花抽样**。

---

## 1. 数据、配置与两处必须先纠正的事实

### 1.1 用了哪两份 benchmark.json

| 文件 | 运行 | 配置 | 校验 |
|---|---|---|---|
| `arc/scratch/diag/benchmark.json` | 2026-10-13 09:40:53 → 17:52:44（8h12m） | 25 游戏 × 4 pass = 100 game-run，concurrency=100 | F87/F90 的"原基线" |
| `arc/scratch/diag2/benchmark.json` | **2026-10-22 13:20:53 → 21:29:33（8h09m）** | 同上 | **就是 F90 的"同配置重跑"**（起止时间逐秒吻合） |

**`arc/scratch/pdiag/benchmark.json` 不存在**，下载不完整：目录里只有
`ar25-0c556536_p0_requests.jsonl`（56 MB，完整）与 `ar25-..._p1_requests.jsonl`（0 字节），
没有 `artifacts/`、没有汇总 JSON。所以"新的那份"用 `diag2`，它与 F90 引用的重跑是同一个文件。
`benchmark.json` 的 label 都是 `duck-harness-kaggle`，`n_passes=4`，每份 100 条 `game_runs`。

聚合口径（F87 定义，未改）：
`每 pass 分 = 100 × mean_over_games(levels_completed / number_of_levels)`；
`game_runs` 是 pass-major（每 25 条一个 pass，已 assert 四个 chunk 的游戏集合相同）。

### 1.2 我们的 Save run 与那本 33.55 的 Save run **不是同一个配置**（逐字核对 notebook cell 16）

`kernels/kernel-arc-agi-3-m2-franzen-verbatim/...ipynb` cell 16（我们）:

```python
bm.solver.concurrency = 10; bm.n_passes = 4; demo_excluded_games = []
if TRUE_SUBMISSION:
    bm.n_passes = 1; concurrency = 120; max_runtime_s_per_game = 532*60
else:
    if USE_PRIORITY_SCHEDULING:
        bm.solver.concurrency = (25 - len(demo_excluded_games)) * bm.n_passes   # 100
        bm.solver.max_runtime_s_per_game = 532*60 * bm.solver.concurrency // 110  # 29018 s
```

`scratch/meta_tantan0327_arc3_franzen_dprime/arc3-franzen-dprime.ipynb` cell 16（33.55 那本）:

```python
bm.n_passes = 1
demo_excluded_games = ['bp35','cd82','cn04','dc22','g50t','ka59','lf52','ls20','m0r0',
                       's5i5','sk48','sp80','su15','tn36','wa30']     # 恰好 15 个
...
    bm.solver.concurrency = (25 - 15) * 1                                  # 10
    bm.solver.max_runtime_s_per_game = 25*60  #532*60 * concurrency // 110 # 硬编码 25 分钟
```

⇒ 那本的真实离线配置是 **10 个 game-run、每个 25 分钟、1 轮**（总 GPU 时间 ≈ 250 game-run·分钟），
我们的是 **100 个 game-run、每个 8h03m、4 轮**（≈ 48 300 game-run·分钟）。**"10 个游戏"只是游戏过滤
相同，预算/并发/轮数完全不同。** 所以下面 §3 从我们两份 25×4 数据算出的"子集版"分数（≈90）**不是**
那本离线标尺的读数；那本要单独跑才知道（一次约 25 分钟 GPU，重复性见 §5.3 的模拟估计）。

### 1.3 我们 Save run 的实际机制（这是理解噪声的前提）

同 notebook cell 4/2 的事实（均可逐字核对）：

* `USE_PRIORITY_SCHEDULING = True`，`ARC3_MAX_ACTIVE_STREAMS = 10`，
  `ARC3_PRIORITY_REFRESH_QUEUE=1`、`_PACE=0`、`_TAIL_FADE=1`、`_TAIL_FADE_FRACTION=0.2`、
  `_TAIL_LOOKUP=remaining`、`_SCORE_NORMALIZATION=1`。
* harness patch 里的 `_PriorityGate` 用 10 个槽；**一个 game session 从开始持有槽位，直到它的上下文
  第一次被 trim 才 handover**（patch 注释自述"measurements put 30 to 50 turns in"）。fresh 游戏在
  base 公式下拿 `2,000,000 - queue_position`，永远高于任何已 trim 游戏的重算优先级 ⇒
  **base 的调度 = fresh-first 轮转：先把每个 game-run 各跑一段（一个 prefix），才轮到第二个 prefix。**
* 实测吻合：每份 run 每个 pass 的 25 个 session 共约 1 100 次 LLM 调用（≈44 次/session），
  每 session 平均 ≈179k generated tokens（8h 总 4.4–5.6M tokens/pass，全 run 17.9M），
  与"100 个 game-run 各跑一个 ~30–50 turn prefix"一致。8h03m 的 `max_runtime` 正好覆盖整轮
  ⇒ **每个 game-run 的预算是 ~179k tokens ≈ 一个 prefix，两轮之间没有"第二次机会"。**

> 这条对 A/B 很重要：我们的 25×4 配置有 **100 个 session 抢 10 个槽**，调度规则**真的起作用**；
> 而那本的 10×1 配置是 **10 个 session / 10 个槽**，没有排队，见 §5.2。

---

## 2. 子集版可重复性（digital ruler 的实测数字）

子集 10 个游戏 = 25 − 15 个排除项 = `ar25 ft09 lp85 r11l re86 sb26 sc25 tr87 tu93 vc33`。

### 2.1 每轮聚合分（每 pass 单独统计）

| run | 全 25 游戏 4 轮 | 子集 10 游戏 4 轮 |
|---|---|---|
| 2026-10-13（diag） | 62.49 / 57.99 / 55.49 / 57.86 | **92.50 / 80.67 / 90.12 / 91.81** |
|  | mean **58.46**，sd **2.92** | mean **88.78**，sd **5.49** |
| 2026-10-22（diag2） | **0.00** / 54.49 / 69.75 / 64.65 | **0.00** / 87.76 / 93.06 / 94.17 |
|  | mean **47.22**，sd **32.11** | mean **68.75**，sd **45.92** |
| diag2 去掉坏轮（第 0 轮） | 54.49 / 69.75 / 64.65 → mean 62.96，sd 7.77 | 87.76 / 93.06 / 94.17 → mean **91.66**，sd **3.43** |
| 两 run 合并（去掉坏轮，7 passes） | mean 60.39，sd **5.50**（pooled within-run 5.41） | mean **90.01**，sd **4.62**（pooled within-run 4.77） |

* 坏轮判定见 §4.1：diag2 第 0 轮 25 个 run 全部 `analyzer failed 11 times consecutively`，
  wallclock 1171–3507 s、tokens 0、levels 0。**这是可 post-hoc 检测的启动故障，不是游戏难度。**
* 注意 diag2 第 1 轮还有 **5 个 run** 被同一故障杀掉（`sk48 tn36 m0r0 bp35 cn04`——**全在排除名单里**），
  所以子集版第 1 轮（87.76）没受损、全 25 版第 1 轮（54.49）受损。
* 两种"剔除坏轮"口径的 between-run 差异（诚实列出，不挑好看的）：
  * 只剔"整轮 0"的坏轮：全 25 Δ = +4.50，SE 4.72（z=0.96）；子集 Δ = **+2.88**，SE 3.38（z=0.85）。
  * 凡包含 analyzer 故障 session 的 pass 全剔（严格）：全 25 Δ = +8.74，SE 2.94（z=2.97，但重跑只剩 2 个 pass）；
    子集 Δ = +4.84，SE 2.80（z=1.73，重跑剩 2 个 pass）。
  ⇒ **"同配置重跑是否一致"取决于故障轮怎么处理，现有 2 个 run 分不清；能确定的是：11.24 分的差距不是
  游戏集造成的，是一个可识别的故障轮造成的。**

### 2.2 噪声下限与最小可检测效应（MDE）

单轮读数 sd（7 个非故障 pass，含 run 间水平差）：子集 **4.62**，全 25 **5.50**；若只算 run 内波动
（pooled），子集 4.77、全 25 5.41。下面用较大的 7-pass 口径。按"两个配置各跑一次、每次 n_passes 轮取均值，
2σ 判据"：

| 读数方式 | 子集 10 | 全 25 |
|---|---|---|
| 单 pass 读数（那本 33.55 的 `n_passes=1` 就是这种） | MDE ≈ **13.1 分** | MDE ≈ **15.6 分** |
| 4 pass 均值（我们的 Save run） | MDE ≈ **6.5 分** | MDE ≈ **7.8 分** |

（MDE = 2√2 × sd/√n，n = 每臂轮数。）

### 2.3 子集的天花板（比噪声更致命）

* 子集 pass 分数：`92.50 80.67 90.12 91.81 87.76 93.06 94.17`（7 个非故障 pass，mean **90.01**，
  sd 4.62）；严格只留 6 个无故障 pass 时 mean **90.39**，max **94.17**。
* 其中 **ar25 / ft09 / lp85 三个游戏每一轮都是满分**（8/8、6/6、8/8），贡献固定的 30 分；
  方差集中在 vc33（sd_frac 0.305）、sb26（0.189）、sc25（0.150）、r11l（0.131）（去掉坏轮后的分层 sd）。
* ⇒ **子集只有 100−94.17 = 5.8 分的向上余量**；任何 "把 90 分再提高 6 分以上" 的真实改进会在读数上饱和。
  反过来，负向改动（比如调度把某些游戏饿死）会在子集上被放大（§6.3：模拟的 dprime 在子集读数上是 −14.1 分，
  但全 25 读数只有 −3.3 分——因为被排除的 15 个难游戏基线本来就接近 0，饿死它们几乎不扣分）。

---

## 3. 判定：这份标尺能否用于 A/B？以及必须在什么条件下

### 3.1 判定（按任务给的阈值 sd > 3）

**不能。** 子集版单轮 sd = **4.62**（全 25 = 5.50）> 3；且子集均值 90/100、向上余量只剩 5.8 分。
对照我们要测的改动量级（F88 的 token 成本类改动最好情况值几个点）：**信噪比 < 1**。

| 用途 | 能否 | 条件 |
|---|---|---|
| 作为"提交前预测线上分" | ❌ | 离线 ≈90（子集）/58（全 25）vs 线上 19.83–29.34（F77/F85），不是同一个量（F87 已立） |
| A/B 调度/优先级类改动 | ❌ | ① 噪声 4.6–5.5 分 > 预期效应；② 那本 10×1 配置**结构上测不到**调度（§5.2）；③ 子集还有天花板 |
| A/B "大改动"（预期 ≥ 7.8 分，全 25 口径） | ⚠️ 有条件可用 | 见 3.2 的 5 条 |
| 崩溃/完成性检查（"Save run COMPLETE"） | ⚠️ | 只能证明"能导入并跑完小基准"，**不能证明比赛重跑不崩**（F92） |
| 用同一 run 同时回答两个问题 | ❌ | 一次 run 只回答一个预登记问题，否则 p 值不可信 |

### 3.2 如果一定要用它（预登记条件）

任何"通过/可用"的结论都必须写明它**在什么条件下**通过（F92 第 5 条教训）：

1. **基础设施门控**：一个 pass 只有在"没有任何 run 的 `solver_note` 含 `analyzer failed`，且
   `sum(levels_completed) > 0`"时才计入。整轮 0 + 全员 analyzer-failed + wallclock ≪ 正常时长 ⇒ 整轮作废
   （规则见 §4.1）；部分 run 被杀 ⇒ 该 pass 作废或整 run 重跑。按现有 8 个 pass 的经验，
   **每 4 轮 run 里至少出现 1 个坏 pass 的概率约 41%**（1/8 的样本太小，只当量级参考），所以 A/B 要预留重跑预算。
2. **预登记效应阈值**：4 pass/臂 ⇒ `|Δ| ≥ 6.5`（子集）/ `7.8`（全 25）；1 pass/臂 ⇒ `13.1` / `15.6`。
   低于阈值的差异一律写"无差异"，不许解释成"有方向"。
3. **天花板**：子集只用于"负向/大负向"检查或相对诊断；要测正向改进用全 25 口径（mean ~60，无天花板）
   或直接在线上测。子集读数与全 25 读数**不可互换**（见 §6.3 的 −14.1 vs −3.3）。
4. **一次只改一处 + 同 notebook/同内核版本**：现有两 run 的 kernel 版本不同（F90：v1 vs v2），
   所以"同配置"的结论依赖 F90 的"逐字节同 notebook"声明；**跨版本差异与改动效应不可分**。
5. **离线读数只是相对指标**：离线上/线下相关性只有 F87 的一对点，没有建立过相关性；离线"通过"不能
   推出线上提升。任何离线 A/B 若真的要花 GPU，先按本文 §3.2 预登记，并且**只当方向筛选**。

一句话：**这份标尺可以当"体温计"（有没有正常跑完、有没有大崩），不能当"天平"（分辨 2–5 分的改动）。**

---

## 4. 附录式的两条硬事实（写进复现脚本里）

### 4.1 故障轮检测规则（精确、可复用）

```python
def classify_pass(chunk):                       # chunk = 该 pass 的 25 条 game_runs
    n_analyzer = sum("analyzer failed" in str(r.get("solver_note") or "") for r in chunk)
    total_levels = sum(r.get("levels_completed") or 0 for r in chunk)
    if total_levels == 0 and n_analyzer == len(chunk): return "full_outage"
    if n_analyzer > 0:                                 return "partial"
    return "clean"
```

diag2 证据：pass 0 的 25 条全部命中 `full_outage`（wallclock 1171/1172/…/3507 s，tokens=0，
`levels_completed=0`）；正常 pass 的 wallclock ≈ 29 000 s。pass 1 的 5 条（全为排除游戏）命中 `partial`。

### 4.2 每 pass 的 token/动作量（模拟器的预算口径）

| run/pass | generated tokens | 环境动作数 | LLM turns | tokens/turn | actions/turn |
|---|---|---|---|---|---|
| diag pass0–3 | 4.21–4.74 M | 4 735–5 780 | 1 008–1 109 | 4 172–4 386 | 4.6–5.2 |
| diag2 pass1–3（clean） | 4.34–5.61 M | 5 312–6 764 | 1 161–1 412 | 3 734–3 974 | 4.6–4.8 |

⇒ 100 个 session 的整 run generated-token 吞吐 = **17.9 M / 29 018 s = 617 tokens/s**（一个 GPU，
10 个活跃槽）。线上 532 min 的预算是同一块 GPU ⇒ 线上总 token 预算 ≈ 617 × 31 920 s ≈ **19.7 M**
（110 个游戏 ⇒ 每游戏 ≈179k，与我们 Save run 的每 session ≈179k 相同——这是"离线预算与线上相当"的
量化依据，也是模拟器选预算的依据）。

---

## 5. 那本 33.55 的"10 游戏"配置：两个必须说清的点

### 5.1 我们的子集数字 ≠ 那本离线标尺的读数

如上 §1.2，那本是 **10 session × 25 min × 1 pass**，每个 session 的预算远小于我们的 179k tokens/8h
（按 §4.2 的吞吐折算 ≈ 93k tokens/session ≈ 20 turns）。所以**不要**把我们算出的子集 ≈90 当成"那本
离线标尺的分数"；它只是"同样 10 个游戏在我们 25×4 配置下"的读数。

### 5.2 那本 10×1 配置 **结构上测不到调度改动**（这是本节最重要的结论）

10 个 game-run、`ARC3_MAX_ACTIVE_STREAMS = 10` ⇒ 10 个 session 恰好占满 10 个槽 ⇒ **没有等待队列**，
priority 函数永远没有可分配的对象。模拟器确认：同一份配方下 base vs dprime 在这种配置里
**总通关 43.6 vs 43.5，差 0.1 关**（10 个 run 的随机差异级别）。⇒ **想用那本 ruler 去 A/B
"调度优先级/活跃流数"这类改动，等于用一把没有刻度的尺：效应恒为 0（被构造性屏蔽）。**
那本 notebook 里 dprime 细胞的自述也说得对：它调的是 `_PriorityGate` 的排队规则——而那本自己的
离线配置根本没有排队。

（能测的是"每动作 token 成本"类 knob：`MAX_OUTPUT`、`THINKING`、`TOOL_OUTPUT_TOKENS` 等，
它们改变 25 分钟内能做多少事；但那本 25 min 的读数只在 ≈61 分附近，噪声见下。）

### 5.3 那本 ruler 的重复性（模拟估计，不是实测）

用同一套 game profiles 模拟该配置（10 个 session / 10 个槽、预算 = 617 tokens/s × 时长）：

| 配置 | 子集读数（模拟） | 同配置重跑 sd（模拟） | 2√2·sd |
|---|---|---|---|
| 10 游戏 × 1 pass × 25 min（= 那本 cell 16 逐字配置） | 61.62 | **3.55** | 10.0 分 |
| 10 游戏 × 1 pass × 50 min（时长翻倍对照） | 93.85 | 2.90 | 8.2 分（且已近天花板） |

这是**模型内噪声的下界**（只有 token/turn 抖动与每关成本抖动，没有模型行为方差）。真实 sd 只会更大：
实测 100-session 配置的模型行为方差是 4.6 分。⇒ **那本 ruler 的真实 MDE 至少 10 分，大概率 ≥13 分**，
且 25 min 版分数与线上不可比、50 min 版直接顶到天花板。

---

## 6. 无模型调度模拟器（交付件）

### 6.1 是什么 / 不是什么

* 输入：每个游戏的（已通关数、已耗动作数、已耗 token、总关卡数、每关动作成本、每关 token 成本）
  —— 全部从两份 `benchmark.json` 的 `history`/`actions_per_level`/`solver_note` 抽出，**不需要模型**。
* 机制：按 harness 真实代码复刻 —— 10 个槽、`_PriorityGate` 的排队/刷新、fresh-first 的
  `2e6 − queue_position` 带、上下文 trim 后的 handover、tail fade 的 `phi`、base 与 dprime 两个
  priority 函数（逐行对照 cell 2 与 cell 17 实现）。
* 输出：固定 token 预算下"最终总通关数"的期望（多种子均值/方差）、每游戏通关数、从未被调度的
  session 数、每关平均 token 成本、以及 oracle 上界。
* **不是**分数预测器：它不模拟模型决策。它只回答"**在已知这些游戏的 token→动作→关卡成本的前提下，
  哪种调度规则能多通关**"。

### 6.2 成本模型与校验

* 每关动作需求 = 4 个 clean pass 上观测到的"通关动作数"中位数（未观测到的关用 `base_actions_per_level`
  × 该游戏中位比例插补；全局中位比例 0.683，即我们的 agent 每关用的动作数约为游戏自带参考值的 68%）。
* 每 token 的动作数由游戏级 `tokens/action` 决定；每 turn 的 token 数按 lognormal（σ=0.85）抽；
  每关成本再乘 lognormal（σ=0.35）抖动。
* **leave-one-pass-out 校验**（170 个 held-out session，用其余 pass 的配方预测某 pass 的通关数）：
  bias **+0.29** 关/ session，MAE **0.99** 关，RMSE 1.36，corr **0.848**；总通关 752 观测 vs 801 预测（+6.5%）。
  用 base 策略重放我们的 25×4 配置：**449.2 关 vs 观测 416 关（+8.0%）** ⇒ 绝对关卡数偏高约 8%，
  **只能读 Δ，不能读绝对值**。

### 6.3 主结果（`--seeds 100`；线上 110 游戏 × 1 pass，B = 19.7 M tokens，10 槽）

| 策略 | 总通关 | Δ vs base | score | 从未被调度 | 0 关 session |
|---|---|---|---|---|---|
| **base**（我们现在的提交） | **464.6** | — | 59.20 | 2.2/110 | 3.5 |
| **dprime**（公开公式 + PRICE_FRESH=1） | **378.6** | **−86.0** | 52.74 | **41.4** | 41.5 |
| dprime_band（dprime 公式，但保留 fresh-first） | 465.4 | +0.8 | 59.27 | 2.0 | 3.4 |
| base_priced_fresh（base 公式 + 给 fresh 定价） | 435.4 | −29.3 | 57.96 | 22.1 | 22.4 |
| greedy_next（配方感知，参考） | 503.4 | +38.7 | 63.96 | 24.8 | 25.7 |
| greedy_game（配方感知，参考） | 511.5 | +46.8 | 64.44 | 31.0 | 31.4 |
| oracle（最便宜关卡优先，上界） | 572 | +107 | — | — | — |

同一套表在**我们的离线 25×4 配置**（B = 17.9 M，100 session）：base 449.2 → dprime 396.3
（**−52.9**），dprime_band 450.2（+1.1），greedy_next 478.2（+29.0），greedy_game 494.1（+44.9），
oracle 542。**离线模拟里 dprime 对"子集 10 读数"的效应是 −14.1 分、对全 25 是 −3.3 分** ——
方向为负，且子集口径会放大负效应（§2.3）。

敏感性（线上）：预算 15 M/25 M ⇒ Δ = −68.6/−38.1；prefix 配额 ×0.75/×1.25 ⇒ −75.4/−66.1；
每关成本抖动 σ=0.15/0.60 ⇒ −86.8/−80.4。**8 个场景全部为负，P(dprime > base) = 0.00。**

### 6.4 机制（为什么是负的）

1. **fresh-first 是 base 的"公平/覆盖项"**：base 的 100–110 个 session 各跑一个 prefix，每个 prefix
   ~44 turns / ~179k tokens；每个 session 平均 4.3 关（7 个 clean pass：752 关 / 7 / 25 = 4.30；
   单 pass 4.0–5.0）。
2. **dprime 的 `PRICE_FRESH=1` 把这个覆盖项拆了**：fresh 游戏被定价 **17 000（n=10）–18 619（n=6）**；
   而"已通关过 1 关、pace 便宜"的已开始游戏可以到 **18 363**（level=2, a=40, t=10k, pace=10k）、
   打到 level=5 的甚至 **18 573**；反过来，没通关过又花掉 180k token 的游戏只有 **16 080**。
   ⇒ 排序稳定地把 fresh 排到后面，fresh 游戏永远排不上。线上 **41.4/110 个游戏 0 次调度** =
   直接丢掉它们的 4–5 关。
3. **为什么集中并不划算**：25 个游戏的 profile 里，第一关平均只需 **24.7 个动作**，第 9 关要 **172 个**
   （L1–L9 均值 24.7/41.0/48.7/51.7/83.4/83.6/94.7/102.3/172.1）⇒ "每个游戏各跑第一段"的边际
   收益高于"少数游戏连跑 2–4 段"。oracle 也只敢在"最便宜关卡"上集中（+23%），而不是"最便宜的已开始游戏"。
4. **公式本身（A·M·C）几乎不影响**：`dprime_band` 与 base 只差 +0.8 关。效应全在 fresh 定价规则上。
   （这也解释了为什么公开 notebook 的 `ours` 参数族要靠他们自己的 `sched_sim.py` 调——调参的对象
   正是这条 fresh 定价；`dprime` 这个"发表版"在他们的三套实现里并不一定是最优那套。）

### 6.5 局限（用之前必须知道）

* 不含"模型行为"通道：同一个游戏连续跑、上下文更暖、prompt 更连贯 ⇒ 可能让 dprime 的集中更值钱。
  这是**唯一**可能翻盘的机制，离线无数据可标定；本模拟器对它零权重。
* 只有 25 个本地游戏的 profile；线上 110 个游戏的混合用 bootstrap（有放回抽 25 个 profile）近似。
  线上实际游戏集未知（F92：Save 的 25 个本地游戏 ≠ 线上 110 个街机网关游戏）。
* prefix 配额（"上下文第一次 trim 前花掉多少 token"）只能从 trace 反推（gave_up session 的 token 分布，
  中位 195k、均值 209k），已用 ×0.75/×1.25 做敏感性；预算 19.7 M 的依据见 §4.2。
* 每关成本来自我们的 4 个 clean pass 的观测中位数；未观测到的关靠 `base_actions_per_level` 比例插补，
  个别游戏的后期关卡（lf52/re86 的第 7–10 关）可信度低。
* 结论是**方向性+量级**，不是"线上会掉 18.5%"。

### 6.6 复现

```powershell
cd D:\kaggle\arc\exp
python ruler_analysis.py          # -> out/ruler_numbers.json, out/subset_per_game.csv
python extract_profiles.py        # -> out/game_profiles.json, out/profile_dump.txt
python sched_sim.py --seeds 100   # -> out/sched_sim_results.json / .md, out/cost_model_validation.json
python sched_sim.py --validate-only   # 只跑 leave-one-pass-out 成本模型校验（<1 s）
```

* 换新数据：把 `ruler_analysis.py` / `extract_profiles.py` 顶部的 `RUNS` 路径改到新的
  `benchmark.json` 即可；若新增的 run 超过 2 个，`aggregate_table` 会自动按 run 分组。
* 加新调度策略：在 `sched_sim.py` 的 `POLICIES` 里加一项
  `{"fresh_band": bool, "fn": "base"|"dprime"|"greedy_next"|"greedy_game", "fade": float}`；
  新的 priority 函数按 `(level, actions, tokens, pace, total_levels, phi) -> int` 写即可。
* 复现全部数值的机器可读版本：`out/ruler_numbers.json`、`out/sched_sim_results.json`。

---

## 7. 建议（给 Lead 的下一步）

1. **不要按 33.55 的相关性押 dprime。** 依据：F92 线上 0.00 + 本模拟器 8/8 场景期望为负 + 现有数据无法
   做它的离线 A/B（子集 sd 4.6 > 3）。若仍要验证一次，必须在预登记里写明"这是一次未知风险的抽样"。
2. **如果要继续做调度，先做"配方感知"的优先级**（greedy_next / greedy_game 在模拟里 +8–10% 通关，
   oracle +23%），而不是公开 dprime。注意这需要难度配方，线上不可得；可行的近似是用
   `base_actions_per_level`（游戏自带的每关参考动作数，benchmark 和线上 metadata 都有）做优先级。
   这条线值得一次离线探索 + 一次模拟筛选，再决定是否花抽样。
3. **不要把那本 10×1 的 Save run 当调度 A/B 工具**（10 session = 10 槽，构造性屏蔽，§5.2）。
   它只能当"每动作成本类 knob"的粗略相对指标，且 MDE ≥10 分（§5.3）。
4. **要真做离线分 A/B**，唯一能承载的方向是"只测大改动"：≥7.8 分（全 25 口径，4 轮/臂，约 8 h GPU/臂），
   否则同样 8 h GPU 会被 4.6–5.5 分的噪声吃掉。按 F90 的结论，这条路线仍不建议启动。
5. **把 §4.1 的故障轮检测规则加进所有 Save run 的判读**：F90 的 11.24 分"重跑失败"有 1/8 概率量级的
   启动故障成分；以后任何离线读数先过这个门控再谈差异。

---

## 8. 文件清单

| 文件 | 作用 |
|---|---|
| `arc/exp/RULER.md` | 本文档 |
| `arc/exp/ruler_analysis.py` | 两份 benchmark.json → 子集/全量每轮聚合、sd、故障轮分类、MDE |
| `arc/exp/extract_profiles.py` | 两份 benchmark.json → 每游戏每关动作/token 成本 profile |
| `arc/exp/sched_sim.py` | 无模型调度模拟器（base/dprime/dprime_band/base_priced/greedy/oracle） |
| `arc/exp/out/ruler_numbers.json` | 标尺分析的全部数字（机器可读） |
| `arc/exp/out/subset_per_game.csv` | 子集 10 游戏的逐轮 levels |
| `arc/exp/out/game_profiles.json` | 25 个游戏的调度模拟输入 |
| `arc/exp/out/profile_dump.txt` | profile 的人读版 |
| `arc/exp/out/sched_sim_results.json` / `.md` | 模拟器全部场景结果 |
| `arc/exp/out/cost_model_validation.json` | leave-one-pass-out 校验的逐条明细 |
| `arc/exp/_scratch/` | 只读分析用的中间抽取（notebook 的 cell 2/4/16/17 原文，便于逐字复核） |

* 输入文件（只读）：`arc/scratch/diag/benchmark.json`、`arc/scratch/diag2/benchmark.json`；
  `arc/kernels/kernel-arc-agi-3-m2-franzen-verbatim/...ipynb`（我们的 cell 4/16）；
  `arc/scratch/meta_tantan0327_arc3_franzen_dprime/arc3-franzen-dprime.ipynb`（33.55 那本 + dprime cell 17）。
* 未改动：内核、`arc-agi-3-ledger/`、`rsna-knee/`；没有 git 提交。
