# F46. ⭐⭐⭐ 为什么别人能用别的卡 —— 我们 F44 的"硬件墙"是**自伤**，不是账号权限

**日期**：2026-10-03
**起因**：一个直接的问题 —— "为啥别人能用的别的卡"。
**结论**：**因为别人是在 notebook 编辑器 UI 里选的卡，而我们全程用 CLI 推送。这两条是
不同的代码路径，push 那条路根本申请不到现代加速器，而且失败方式是静默替换。**

---

## 1. 我们 F44 到底错在哪

F44 原文写的是：

> `machine_shape` is accepted by the push and then silently ignored. Our account is entitled to
> **2× Tesla T4 only**. No RTX Pro 6000, no H100.

**第一句对，第二句是过度推断。** 我们只测了一件事（"用某个 `machine_shape` 字符串 push → 拿到 T4"），
却得出了一个强得多的结论（"账号权限只配 T4"）。这两者之间没有证据链——
而 F44 的整个"结构性的、我改不了的硬件限制"叙事，正是架在这句过度推断上的。

---

## 2. 外部证据：Kaggle 官方自己的 issue

| 来源 | 内容 |
|---|---|
| [kaggle-cli #1196](https://github.com/Kaggle/kaggle-cli/issues/1196) | 标题即结论：**"`machine_shape` has no documented value for the 'GPU T4 ×2' option shown in the notebook editor"**。`kagglesdk` 的 `ApiCreateKernelSessionRequest.machine_shape` docstring **只列了三个值**：`NvidiaTeslaT4 \| NvidiaTeslaP100 \| Tpu1VmV38`。编辑器 UI 提供 T4×2，而 push API 没有对应值。 |
| [kaggle-cli #1197](https://github.com/Kaggle/kaggle-cli/issues/1197) | 用 `enable_tpu` + TPU `machine_shape` push：**"accepted without error、跑完，但环境是错的"**。同一个 notebook 在编辑器里选好、点 **"Save & Run All" 就能正确分配到卡**。原话：**"the push-based API path and the interactive session path diverge in a way that fails silently, no error, no warning, just the wrong environment."** |
| [kaggle-cli #1156](https://github.com/Kaggle/kaggle-cli/pull/1156)（Kaggle 官方 agent） | 确认 **RTX Pro 6000 是真实存在的 Kaggle 卡**：*"newer PyTorch was needed for **Blackwell / RTX Pro 6000 sm_120** GPUs"*。 |
| [kaggle-cli #1192](https://github.com/Kaggle/kaggle-cli/pull/1192)（2026-09-11 合入） | 专门加警告：**retired 的 `machine_shape` 会被服务器静默替换**。同一个失败模式。 |
| ARC Prize 官方文档 [GPT OSS on Kaggle](https://docs.arcprize.org/partner_templates/gpt-oss-kaggle) | **"the competition's RTX Pro 6000 accelerator"**；提交步骤写着 **"Enable the accelerator — Set the accelerator to RTX Pro 6000 in the notebook settings."** |
| Tufa Labs 公开 notebook 内文 | *"if you make a copy of this notebook, you will have to **manually select the proper GPU (RTX Pro 6000)**."* |

⇒ **RTX Pro 6000 是这个比赛的官方卡，通过编辑器 UI 分配。CLI push 拿不到。**

---

## 3. 我们自己的三次实测（全部 T4）

| # | 形态 | 请求方式 | 客户端 | 实际拿到 |
|---|---|---|---|---|
| 1 | script | `enable_gpu: true`（无 `machine_shape`） | 2.1.2 | **2× Tesla T4, cc 7.5** |
| 2 | script | `machine_shape: "NvidiaRtxPro6000"` | 2.1.2 | **2× Tesla T4, cc 7.5** |
| 3 | **notebook** | 内层 `metadata.kaggle.accelerator = "nvidiaRtxPro6000"` **且** 推送时显式 `--accelerator NvidiaRtxPro6000` | **2.2.2** | **2× Tesla T4, cc 7.5** |

第 3 次是本次新做的（`work/probe-nb/`，跑完即删），一次性排除了两个变量：
"是不是 script 与 notebook 的差别"和"是不是旧客户端 2.1.2 的 bug"。**都不是 —— 是 push 这条路本身。**

---

## 4. 修正后的结论

**错的说法**：我们的账号只被授予 2× Tesla T4。

**对的说法**：**CLI push 路径只能申请一小撮旧卡；申请其它加速器时服务器静默替换成默认卡，
不报错。** 账号权限从未被证伪 —— 我们只是**用错了路径**，然后把这个路径的失败当成了账号的天花板。

这条修正的意义在于：**F44 的"六道闸门"里，第 1 道（结构性的、我改不了的那道）塌了。**
剩下的第 2–5 道（TAAF 断言 GPU 型号、`flashinfer` 要 sm_80+、模型是 FP8 要 cc≥8.9、
vLLM 链 CUDA 13）**都只在 T4 上成立**。一旦真的拿到 RTX Pro 6000（sm_120、大显存），
这些闸门**自动全部消失**。

⚠️ **但有一条我们仍未亲自验证**：**编辑器里选的加速器，能不能带进"提交-评分复跑"那次运行。**
#1197 说的是交互式 "Save & Run All" 正确分配；比赛评分复跑是另一条路径。
**在亲眼看到一次 RTX Pro 6000 的 `nvidia-smi` 之前，不要把这个当既成事实。**

---

## 5. 所以现在该做什么

1. **在 Kaggle 编辑器里**打开 ARC notebook → Settings → Accelerator → **RTX Pro 6000** →
   Save & Run All，跑一个只打印 `nvidia-smi` 的最小 notebook。
   **这一步必须在浏览器里点，CLI 做不到**（#1196 已说明 pull 回来的 `machine_shape`
   只反映最后一次 API push，与 UI 当前选择无关）。
2. 若确认拿到 sm_120 卡，则 **F42/F43 里记的公开配方（TAAF/Duck 全栈）重新可用**：
   FP8 模型、flashinfer 0.6.6、官方 vLLM 全部解锁。
3. 若确认拿不到，才回到 F44 的结论，并改走 `llama.cpp`。

**在此之前，ARC 项目不应被视为已关闭。** 我们当初停下的理由（"硬件墙，我改不了"）建立在
一句未经验证的推断上。

---

## 6. 方法教训（比结论更重要）

同一个失败模式在这个项目里已经出现第 N 次：**一个被接受、被丢弃、不报错的字段，
被我们读成了"系统告诉我此路不通"，而实际上它什么都没说。**

区别在于这次我们**从"字段被忽略"直接跳到了"账号没权限"**，中间那一步（push 路径 vs UI 路径）
从来没被写出来、也没被检验过。**观测到"我没拿到 X"时，缺的从来不是"我为什么没资格拿到 X"的
解释，而是"我请求 X 的方式，是不是一条能表达 X 的方式"。**
