# F63 — 2026-10-11 — P1 收口：ARC 生态只有一种方法，所以 P2 是一条"换模型"的单变量阶梯

## 1. P1 完成：度量口径 + 24.53 的构成 + 公开谱系（全部有据）

**① 度量**：per-level 计分，**第 i 关计 i 倍**，且
`level_score = 100 * (baseline_i / actions_i) ** 2`（`100*(22/27)**2 = 66.4`，F38.2 / STATUS.md）。
⇒ **分数在第 2 关及以后**，而**第 1 关（唯一被完成过的关）权重最低**。

**② 我们 24.53 的构成**（F47 + F50）：`ppxl16/arc-agi-3-milestone-2-solution`
= **`dfranzen/arc-agi-3-milestone-2-solution` 的副本**（社区第 3、287 票，基于 Tufa Labs 的 Duck harness），
挂的模型是 **`dfranzen/intel-qwen3.8-flash-next-w4a16-autoround`（W4A16 = int4）**。
⇒ **我们本来就是"Duck harness + 4-bit"**，差的只是模型档位。

**③ 公开谱系（F45，普查 200 个内核）**：
| 家族 | 数量 |
|---|---|
| **DUCK harness (TAAF)** | **92** |
| Qwen3.8 / flash-next | 55 |
| TAAF（非 Duck 命名） | 33 |
| milestone-2 血统 | 11 |
| 其余（eval/probe/world-model/baseline…） | 其余 |

> 逐字：*"Roughly half of all public kernels are the TAAF Duck harness by name, and most of the
> rest are that harness with a different model swapped in. **There is no meaningful second method
> with a score.**"*

⇒ ⭐⭐ **唯一的杠杆是"换模型"。** 而 F49 实测：**`NvidiaRtxPro6000`（sm_120 / 102 GB）现在真的拿得到**
⇒ **FP8 / NVFP4 这一整档被解锁**（F49 §2：六道闸门里第 2–5 道只在 T4 上成立）。

## 2. P2 = 单变量阶梯（一天一枪，全部预先注册）

**固定不变**：harness（TAAF Duck）+ 比赛源 + `machine_shape: NvidiaRtxPro6000` +
`analyzer_model` 走环境变量。
**每天只动一个变量 = 那个模型**（必要时连带它要求的 `float16`/`tensor_parallel` 配置）。

| 天 | 模型（单一变量） | 依据 | 预注册判据 |
|---|---|---|---|
| **D1 = 今天** | **FP8 27B**（`keithtyser/taaf-duck-qwen38-serving-v1` 内的 `Qwen/Qwen3.8-27B-FP8`） | F42.2 记录的高位配方；sm_120 满足 cc≥8.9 | 只要 **> 24.53** 就保留；平台保留最好 ⇒ 免费 |
| D2 | **NVFP4 27B**（`keithtyser/…nvfp4` 或 `nvidia/qwen3-8-flash-next-nvfp4`） | F45 表里 `amanatar` 那本用的就是它 | 同上 |
| D3 | **W4A16 27B**（`dfranzen/intel-…w4a16-autoround`）在 **sm_120** 上跑 | 与 D1/D2 构成"档位对照"，且**这是我们 24.53 现在用的那一档** | 同上：**这一枪同时是 D1/D2 的对照组** |
| D4+ | 8B coder / 其它量化 / 模型代际 | F43.3 的目录表 | 同上 |

⚠️ **不变量**：**不调 harness、不改游戏集、不调 concurrency/预算**——那些一动，
"是模型还是调度"就分不清了（本仓 C86 那条规矩）。

## 3. 仍未测的边界（每次提交都在测它）

**"评分复跑是否继承加速器"** 只有 F50 的**支持性证据**（同内核 22.48→24.53），**不是决定性证据**。
⇒ **D1 的提交同时也是对这一条的又一次抽样**，而平台保留最好成绩 ⇒ **零成本**。

## 4. 本轮的净产出

* P1 **收口**：度量、24.53 的构成、公开谱系三者都有了有据的答案；
* P2 **从"探索"变成一张带预注册判据的日更阶梯**；
* 顺带跑完 RSNA 的每日巡检：**rank 301 / 0.954 / 铜线 575 / 余量 +274**，tick 不动。
