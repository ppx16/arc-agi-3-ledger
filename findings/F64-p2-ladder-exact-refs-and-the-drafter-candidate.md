# F64 — 2026-10-11 — P2 阶梯的**精确 ref**（实测取出，不是猜），以及一条更好的候选

F63 给出的是阶梯的**形状**。本轮把每一档的 `model_sources` / `dataset_sources`
**从真实使用者的 metadata 里取出来**，所以 P2 现在是可以直接照抄的，不需要再猜。

## 1. 取到的三份实测配置

| 来源内核 | `model_sources` | `dataset_sources` | shape |
|---|---|---|---|
| **`kozykappa/arc-agi-3-flashnext-duck-audited-submission`** | `dfranzen/albucino-qwen3-8-flash-next-drafter/Transformers/default/1` **+** `dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/Transformers/default/1` | `dfranzen/pennyroyal-v253` + `dfranzen/taaf-kaggle-source-bundle-copy` | `NvidiaRtxPro6000` |
| **`keithtyser/duck-qwen3-8-flash-next-nvfp4-mtp`** | `keithtyser/qwen3-8-flash-next-nvfp4/PyTorch/radixark-modelopt-fp4/1` | `keithtyser/duck-qwen38-nvfp4-mtp-vllm-smoke-v1` + `keithtyser/qwen38-flash-next-vllm-nvfp4-runtime-v1` | `NvidiaRtxPro6000` |
| **`amanatar/arc-agi-3-hybrid-repl-agent`** | 同上（NVFP4） | 同上（NVFP4） | `NvidiaRtxPro6000` |

⇒ ⭐ **`amanatar` 与 `keithtyser` 用的是同一份 NVFP4 配置** ⇒ 那是**一个**配置，不是一个谱系。

## 2. ⭐⭐ 更好的候选：**在【我们现有的栈】上只加一个 drafter**

`kozykappa` 的第一行：它的 `dataset_sources` **与我们的 24.53 完全相同**
（`dfranzen/pennyroyal-v253` + `dfranzen/taaf-kaggle-source-bundle-copy`），
而 `model_sources` 是**我们那个 W4A16 模型 + 一个 `…flash-next-drafter`**。

⇒ **drafter 是推测解码（speculative decoding）用的小模型** ⇒ **同样的时间预算能解码更多步**
⇒ 在"分数取决于预算内玩到哪一步"的度量下（F38.2），**这是直接对着计分机制的杠杆**。

⇒ **这是目前最干净的单变量**：**加一个 model ref，其他一字不动。**
（对比 D1/D2 那种"换整档量化"，它连数据集的依赖图都不改。）

## 3. 修正后的 P2 阶梯（按"单变量纯度"排序）

| 优先级 | 变量 | 配置 | 预注册判据 |
|---|---|---|---|
| **A（最纯）** | 我们的栈 **+ drafter** | 见 §1 第一行 | **> 24.53** 即保留；平台保留最好 ⇒ 免费 |
| **B** | 换 **NVFP4** 整档 | 见 §1 第二行 | 同上 |
| **C（今天已在跑）** | 换 **FP8** 整档 | `keithtyser/taaf-duck-qwen38-serving-v1` + `driessmit1/arc3-vllm-h100-wheelhouse-v3` | 同上 |
| **D** | W4A16 在 sm_120 上（对照） | `dfranzen/intel-…w4a16-autoround` 单独 | 同上 |

⚠️ **A 与 B/C 的差别值得写明**：B/C 同时换了**模型**与**它的运行时/转轮舱**（两个变量），
而 **A 只换一个 model ref**。⇒ **在解释结果时，A 的结论最干净**，B/C 只能说"这一档比那一档好"。

## 4. 本轮净产出

* P2 阶梯从"形状"变成**可照抄的精确 ref**；
* 发现并排定了一个**更纯的单变量**（drafter）为最高优先级；
* 顺带把"B/C 是两个变量"这件事写在预注册里 —— 免得结果出来后把"整档差异"误读成"模型差异"。
