> # ⛔ 本页的"现状"与"为什么停下"两节都已过时 —— 见 [F47](findings/F47-score-is-22-48-not-0-18.md)
>
> **2026-10-06 核实：我们是 22.48、rank 862/3866，不是 0.18 / 2373。**
> 那条 22.48 提交于 **2026-10-04 04:11**（台账收笔之后，描述为空），
> 用的是 **W4A16（int4）** 配方，**不需要 Blackwell** —— 所以下面"硬件墙"那一节对这条路不成立。
>
> 现场仍是活的：**1 次提交/天、截止 2026-11-02、榜首 55.89 ⇒ 余量 2.48 倍。**

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

> ### ⚠️ 这一整节在 2026-10-03 被更正了
>
> **"硬件墙"的承重那一句——"我们的账号只配 2×T4"——是错的。**
>
> 真相是：**CLI push 这条路径根本申请不到现代加速器**，它会把请求静默替换成默认卡；
> 而 **RTX Pro 6000 是通过 notebook 编辑器 UI 分配的**（这正是 Tufa Labs 那句
> *"you will have to manually select the proper GPU"* 的意思）。
>
> 我们全程用 CLI 推送，于是把**一条路径的失败**读成了**账号的天花板**。
> 详见 **[F46](findings/F46-accelerator-push-path.md)**。下面的内容作为**当时**的记录保留。

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
| [`findings/F46-accelerator-push-path.md`](findings/F46-accelerator-push-path.md) | ⚠️ **对 F44 的更正**：CLI push 路径申请不到现代加速器，RTX Pro 6000 只能在编辑器 UI 里选 |
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

> ### ⭐⭐⭐ 第一步：一次点击，解锁整个高档位（2026-10-06 已把工具准备好）
>
> 我建好了一个**探针 notebook**，它只做一件事——打印 `nvidia-smi`、PyTorch 的 CUDA 版本、
> 以及**计算能力（sm_XX）**，并直接判 `BLACKWELL/RTX-Pro-6000 OK` 还是 `OLD CARD`：
>
> **`https://www.kaggle.com/code/ppxl16/arc-agi-3-gpu-probe`**
>
> ⭐⭐ **2026-10-06 用户反馈，这条改变了整个判断**：那个探针的编辑器里**没有** RTX Pro 6000 选项，
> 而 **`ARC-AGI-3 Milestone 2 Solution`（我们有比赛源的那本）有**。
>
> ⇒ **加速器选项是跟着【比赛源】给的**：比赛提供 RTX Pro 6000，所以只有挂了
> `competition_sources: ['arc-prize-2026-arc-agi-3']` 的内核才会出现这个选项。
> 我原来的探针**没挂比赛源**，所以下拉里根本没有它。
>
> **已修**：探针 v2 现在挂了比赛源 + `machine_shape: NvidiaRtxPro6000`，重新推了。
>
> ⚠️⚠️ **由此产生一个很可能成立、且价值极大的推论**：
> **评分复跑是按【提交时那份 notebook 的元数据】分配加速器的**，而**交互式推送运行**才走那条
> "静默替换成 T4" 的路径。**如果是这样，那高分配方现在就已经能用了** ——
> 我们的 **22.48** 正是来自一本**挂着比赛源、且声明 `NvidiaRtxPro6000`** 的 notebook
> （`ppxl16/arc-agi-3-milestone-2-solution`，目前最后一次运行 10-03）。
> **必须用一次真实提交去证实或否证**，而平台保留最好成绩 ⇒ **这次测量是免费的**。

> ### ✅ 已解决（2026-10-06，见 [F48](findings/F48-api-can-request-rtx-pro-6000.md)）——**不需要你手点**
>
> **A/B 实测**：两本探针**只差 `machine_shape` 一个字段**，都挂比赛源 ——
> 不写的那本**约 1 分钟跑完，2×T4**；写了 `NvidiaRtxPro6000` 的那本**排队 50+ 分钟等卡，从未被替换**。
> ⇒ **API 推送能申请 RTX Pro 6000。** F46 那条"只能编辑器选"是**错的**，缺的那一环是**比赛源**。
> ⇒ **Python 侧已经接管，用户不需要在浏览器里操作。**
>
> ⚠️ 边界：**会排队**（长度未知，排队不烧额度）；且**"评分复跑是否继承加速器"仍未验证**，
> 那才是决定高位配方能不能用的那一步 —— **用一次提交去测，平台保留最好成绩 ⇒ 免费**。
>
> **以下是当时（尚未解决时）写的步骤，保留作记录。**

> **请在浏览器里**：打开它 → 右侧 **Settings → Accelerator**，确认现在是否出现 **RTX Pro 6000**；
> 若出现就选它 → 右上 **Save & Run All**。跑完告诉我，我重读日志。
>
> ⚠️ **2026-10-06 13:23Z 实测（这次是【推送触发】的运行，不是编辑器那次）**：
> 拿到 **2 × Tesla T4，`sm_75`（cc 7.5）**，探针自判 `OLD CARD (cc 7.5) -- NOT the RTX Pro 6000`。
> ⇒ **CLI 推送上不了现代卡，这是第 4 次实测**（F46 三次 + 本次）。
> **它没有回答"编辑器里选 RTX Pro 6000 会不会生效"** —— 那条路径仍然只差你那一跑。
>
> **为什么必须是浏览器**：F46 实测三次（script、notebook 内层 `accelerator`、`--accelerator` 参数，
> 客户端 2.1.2 与 2.2.2）**全部拿到 2×Tesla T4** —— **CLI push 这条路申请不到现代加速器，
> 且静默替换、不报错**。编辑器 UI 是唯一入口。
>
> **为什么这一步值钱**：顶级公开配方（Tufa Labs 自家、`sirikilohit` 的 v18、`foysalemonshanto`）
> **全部声明 `NvidiaRtxPro6000` 并用 NVFP4 / FP8 模型**。拿到 sm_120 ⇒ F44 的第 2–5 道闸门
> （显卡断言、`flashinfer` sm_80+、FP8 cc≥8.9、vLLM CUDA 13）**一次性全部消失**。
> **我们现在 22.48，榜首 55.89 —— 那 2.48 倍的差距主要就是这一档。**
>
> ⚠️ **仍然未知**：编辑器里选的卡**能不能带进"提交-评分复跑"那次运行**（F46 §4）。
> 探针回答的是"UI 能不能选到现代卡"；**复跑是否继承**是第二个、独立的问题，
> 要用一次真实提交去测（而平台保留最好成绩 ⇒ **这次测量是免费的**）。

1. **若第 1 步成立**：F42/F43 里记的公开配方是全的（数据集、模型 ref、harness、服务配置、gateway 细节），
   而 F44 的闸门 2–5 会**自动消失**。
2. **若第 1 步不成立**：回到 F44，走唯一没测过的路 —— 绕开 vLLM 用 `llama.cpp`
   （TAAF bundle 自带 `configs/inference.local.llama.json`，GGUF Q4 在 Turing 上能跑）。
   ⚠️ 但**注意**：`dfranzen` 那本（W4A16）**已经在推得到的卡上拿到了 22.48**（见 F47），
   所以"T4 上完全没戏"这个说法本身也是错的。
3. **`mbmmurad` 那个 "LB 0.86 (3rd place candidate)"** —— 唯一不用 Qwen、不用 Duck 的自称高位作品（Gemma-4 31B），
   且挂载列表为空。值得弄清是哪个 milestone、什么量纲。
4. ⚠️ **复制公开 notebook 到本账号目前会被 403 拒绝**（2026-10-06 实测）：不是依赖问题
   （清空 dataset/model/docker 仍 403）、不是 GPU 额度、不是 notebook 内部残留的 `metadata.kaggle`。
   最小 script 与最小 notebook **都能正常推** ⇒ **是那些 308–555 KB 内核自身的某个内容**。
   **未解决**，下次要复制重型公开内核时先解决它。

---

## 一条我认为最该留下的教训

F44 和 F40 是对照组。

**F40**：先烧掉一次完整运行，才发现那个改动毫无效果。
**F44**：每个探针都是**能证伪整个计划的最便宜实验**，而且**全部跑在建任何东西之前** —— 三次，各 4–10 分钟。

两者代价差两个数量级，区别只在于**先问"哪个假设一旦错了，后面全白做"**。
