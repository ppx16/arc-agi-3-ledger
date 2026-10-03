# ARC Prize 2026 — ARC-AGI-3 · 实验台账

这是我在 **ARC Prize 2026 / ARC-AGI-3** 上的完整工作记录：做过什么、量到了什么、什么被证伪了、以及为什么最终停在哪里。

**不是教程，是台账。** 里面大部分内容是否定结果 —— 而那正是它存在的理由：让下一个接手的人不必重走同样的路。

---

## 现状（截至 2026-10-01 的公榜快照）

| | |
|---|---|
| 我们的最好成绩 | **0.18**（`StochasticGoose` 去掉逐关学习器重置） |
| 提交次数 | 4 |
| 公榜队数 | **3524** |
| 公榜中位数 | **0.33** |
| 第 1 名 | **50.65**（Tufa Labs） |
| 我们之上 | **约 2/3 的队**（≤0.18 的占 32.2%） |

```
前 5 名        50.65 · 40.97 · 27.89 · 24.54 · 23.84
中位数         0.33
我们           0.18
```

⚠️ **而且前沿还在快速移动**：第 1 名在两天内从 **45.33 → 45.33 → 50.65**。这与同时期的 RSNA Knee 完全不同 —— 那边公开天花板冻结在 0.943 且无人能突破。

### 四次提交全部撞在天花板上

| ref | 分数 | 方法 |
|---|---|---|
| `56641359` | **0.18** | 官方 `StochasticGoose` CNN 基线（Tufa Labs / Dries S…） |
| `56666561` | 0.14 | Hybrid：先规划、失败回落 goose |
| `56705048` | 0.08 | Portfolio explorer：dense + rare + xy + area 候选排序 |
| `56744057` | **0.18** | `StochasticGoose` **去掉逐关学习器重置** |

**四种不同的通用机制，天花板与基线一模一样。** 这是台账里最重要的一个否定事实：**问题不是策略。**

---

## 为什么停在这里：公开前沿在一堵硬件墙后面

### 公开生态基本只有一种方法（200 个内核的普查）

| 家族 | 内核数 |
|---|---|
| **DUCK harness (TAAF)** | **92** |
| **Qwen3.8 / flash-next** | **55** |
| TAAF（非 duck 命名） | 33 |
| eval / harness / probe | 27 |
| thui 变体 | 13 |
| milestone-2（dfranzen / richardcsaky 系） | 11 |
| world-model / neural | 6 |
| agent（泛用命名） | 6 |
| baseline / starter | 5 |

⇒ 约一半的公开内核按名字就是 **TAAF 的 "The Duck" harness**，其余多数是**换掉模型的同一套 harness**。**没有第二个有分数的独立方法。**

### ⚠️ 而所有有分数的都申请同一张卡

拉取 8 个最有意思的**非-Duck** notebook 的 metadata：

| notebook | `machine_shape` | 模型 |
|---|---|---|
| `amanatar/arc-agi-3-hybrid-repl-agent` | **NvidiaRtxPro6000** | qwen3-8-flash-next-nvfp4 |
| `bang1850/arc-prize-2026-sovereign-agent` | **NvidiaRtxPro6000** | 3 个（含私有 MoE） |
| `iamjasonfeng/chimpanzee-1-1-eval` | **NvidiaRtxPro6000** | —（2 私有数据集） |
| `mbmmurad/…LB 0.86 3rd place candidate…` | **NvidiaRtxPro6000** | `google/gemma-4-31b-it` |
| `nihilisticneuralnet/arc-agi-3-retained-reasoning` | **NvidiaRtxPro6000** | qwen3-8-flash-next-nvfp4 |
| `huikang/`**`milestone-1`**`-4th-place` | gpu=False | 无 |
| `ruichardliu/`**`milestone1`**`-2nd-solution` | gpu=False | — |

⇒ **硬件闸门不是某个配方的怪癖，而是常态。** 唯二不需要 GPU 的公开作品是 **Milestone 1** 的 —— **比赛的另一个阶段**，不迁移。

### 六道闸门，全部实测

我们**实测**过（三次探针内核，跑完即删）：

| # | 闸门 |
|---|---|
| 1 | **`machine_shape` 被静默忽略** —— 请求 `NvidiaRtxPro6000`，推送成功、运行、COMPLETE，**拿到的却是 2× Tesla T4（cc 7.5）** |
| 2 | 配方**自己断言 GPU 型号**（TAAF 的 `setup_commands.json`：`rtx-pro-6000`/`h100`/`l4`），T4 当场断言失败 |
| 3 | `flashinfer==0.6.6` 要 **sm_80+**，Turing 不在支持列表 |
| 4 | 模型是 **FP8**（`Qwen3.8-27B-FP8`），要 cc ≥8.9 |
| 5 | 官方 vLLM **装不上**：`vllm._C_stable_libtorch` 链 `libcudart.so.13`，镜像只有 CUDA 12.8（`.so.12`） |
| 6 | 三个社区 ARC wheelhouse **离线装不上**（pip rc=1） |

⇒ **1–4 已经是结构性的。** 第 1 条是**硬件权限**限制：第 1–5 名在跑 RTX Pro 6000 / H100，而 Kaggle 交给我们什么卡，我改不了。

⚠️ **租卡也救不了**：提交是 Kaggle **复跑**的 notebook，必须跑在 Kaggle 机器上。

---

## 台账索引

| 文件 | 内容 |
|---|---|
| [`findings/FINDINGS.md`](findings/FINDINGS.md) | **主台账 F1–F43**（约 1900 行）：环境勘测、度量 harness、逐关学习器、十几次证伪 |
| [`findings/F44-hardware-wall.md`](findings/F44-hardware-wall.md) | 六道闸门的完整证据链，以及**为什么这次每个探针都跑在建东西之前** |
| [`findings/F45-what-others-do.md`](findings/F45-what-others-do.md) | 200 个公开内核的方法普查 + 非-Duck 作品的硬件实测 |
| [`findings/metric-harness-notes.md`](findings/metric-harness-notes.md) | 离线复刻比赛度量的记录 |
| [`STATUS.md`](STATUS.md) | 当时的运行状态 |

### 几个值得一读的具体发现
* **F30**：原始像素网格是噪声，**语义抽象才携带游戏信息** —— 这一条后来被 "The Duck" 自己的文档独立印证（*"the raw numeric grid is intentionally hidden from the Python tool"*）。
* **F38.2**：评分是**逐关**的，第 *i* 关权重是 *i* 倍 ⇒ 分数在**第 2 关以后**。
* **F40**：逐关学习器重置**不是**瓶颈 —— 改掉它，分数**分毫未动**。
* **F41/F42**：顶级队在复跑里跑**本地 LLM**（vLLM），模型是 Qwen3.8 "Flash Next" 家族。
* **F42.4**：**我们的 0.18 是"没有语言模型"的地板，不是方法的上限。**

---

## 仓库结构

```
findings/      台账（主台账 + 专题）
agents/        本项目写的九个智能体
tools/         二十五个探针 / 求解 / 计分工具
work/          探针内核的脚本与捕获日志 —— 即结论背后的原始证据
leaderboard/   三份公榜快照（三个时间戳，CSV）
```

⚠️ **脱敏记录**（两处，均为第三方信息，不是我们的）：

1. 三个快照里有 2 位用户的**公榜显示名本身就是邮箱地址**（`kwonj0815@gmail.com`、`macleonjinkan@hotmail.com`，各 3 次，共 6 处），已替换成**同一行的战队 slug**（`kwonj0815gmailcom` / `macleon`）—— 行内其余字段一字未动，信息无损，但不再二次分发他人邮箱。
2. `work/taaf/preamble.txt` 是从 Kaggle 内核日志里捕获的 harness 配置，其中一条 `local_server_repo_dir` 带了**原作者的本地绝对路径**，已替换为 `<redacted-local-path>`。

**除此之外，这些捕获文件与来源原样一致。** 需要逐字复核的人可以从对应 Kaggle 内核重新拉取。

### ⛔ 这个仓库里**没有**什么，以及为什么

| 排除项 | 原因 |
|---|---|
| `starter/`（920 MB）、`research/openworld`（144 MB） | **依赖树**，不是我们的代码（187 MB `.pyc`、53 MB `.pyd`） |
| `comp/`、根目录的 `*.zip` | **比赛数据**，不该进 git |
| `research/aera-arc3-paper` | **第三方论文**，不是我们能再发布的 |
| `work/duck9`、`work/nonduck`、`work/pub_arc` | ⚠️ **从 Kaggle 拉下来的别人的 notebook**（rank-5 的 Duck、sovereign-agent、chimpanzee、milestone-1 …）—— 它们的**结论**已用自己的话记在 F45 里，**作品本身不转载** |

整理脚本 [`tools/../build_ledger_repo.py`](tools/build_ledger_repo.py) 用**显式白名单**拷贝，并打印每一条被拒绝的文件和原因 —— 内容边界是可审计的。

---

## 还剩下什么

1. **唯一没测过的路：绕开 vLLM 走 `llama.cpp`。** TAAF bundle 自带 `configs/inference.local.llama.json`，说明 harness 有这个后端，而 **GGUF Q4 在 Turing 上能跑**。代价是换 GGUF 量化模型 + 打补丁绕过 harness 那句 GPU 断言。**它有真实的机会死在 harness 的别的假设上。**
2. **`mbmmurad` 那个 "LB 0.86 (3rd place candidate)"** —— 唯一不用 Qwen、不用 Duck 的自称高位作品（Gemma-4 31B），且挂载列表为空。值得弄清是哪个 milestone、什么量纲。
3. **如果哪天能拿到 Blackwell 级硬件**，F42/F43 里的公开配方是全的（数据集、模型 ref、harness、服务配置、gateway 细节），可以照着复现。

---

## 一条我认为最该留下的教训

F44 和 F40 是对照组。

**F40**：先烧掉一次完整运行，才发现那个改动毫无效果。
**F44**：每个探针都是**能证伪整个计划的最便宜实验**，而且**全部跑在建任何东西之前** —— 三次，各 4–10 分钟。

两者代价差两个数量级，区别只在于**先问"哪个假设一旦错了，后面全白做"**。
