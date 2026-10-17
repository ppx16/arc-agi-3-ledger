# F65 — 2026-10-11 — 高档线其实已经在我们手里；渲染阻塞已【修好并验证】，只差一个 GPU 名额

## 1. 我先纠正一个方向性错误

今天早些时候我 fork 了 `fabioolival/arc-agi-3-v21-taaf-27b`（FP8），并把它当成"最强的可复现杠杆"。

**但我们的 ARC 仓里早就有更高档的那条线**：

```
ppxl16/arc-agi-3-duck-18-1gc        (本地 arc/kernels/kernel-arc-duck18{,-fix,-live})
dataset_sources : keithtyser/duck-qwen38-nvfp4-mtp-vllm-smoke-v1
                  keithtyser/qwen38-flash-next-vllm-nvfp4-runtime-v1
                  sirikilohit/sglang-penny-build-qwen        ← sglang，不只是 vLLM
model_sources   : keithtyser/qwen3-8-flash-next-nvfp4/…      ← NVFP4
                  woochangsim/qwen38-flash-next-w4a16-autoround-4c67bf6/…  ← W4A16（双模型）
machine_shape   : NvidiaRtxPro6000
```

⇒ **`duck-18` 是我们的 NVFP4+W4A16+sglang 版**，比 fabioolival 那本 FP8 更新。
⚠️ **教训**：动手前应该先 `grep` 自己仓库里的资产 —— 我又犯了一次"去外面找一个家里就有的东西"。

## 2. ⭐ 渲染阻塞：已定位、已修、已验证

**F59 的结论**是 v5 **死在 nbconvert 渲染**，不是 boot：
`InvalidNotebook: missing attachment: tufa_labs.png`

**本轮实测**（新工具 `work/fix_missing_attachments.py`，`--check`）：

| notebook | 悬空附件 |
|---|---|
| 正在跑的 `arc-duck-taaf`（fabioolival） | **无** ✅ 干净（我先前担心它也会死，是多余的） |
| **`arc-agi-3-duck-18-1gc-submit`（高档线）** | **cell 1 引用 `tufa_labs.png` 而无附件** ⛔ **正是 F59 那个** |

**修法**：`--embed` 往那个 markdown cell 塞一个 1×1 PNG（保留占位、不改任何代码）。

**验证（这是关键）**：修完的 `kernel-arc-duck18-va` 与原件的 **50/50 格 source 逐字节相同**
（`work/diff_nb.py`：`notebooks are cell-for-cell IDENTICAL in content`）⇒
**唯一的改动就是那一个 attachments 条目** ⇒ **这是一次真正的单变量编辑**。
另：`ascii-only YES` / `GBK-decodable YES` / 往返一致 / 悬空 = **0**。

## 3. ⭐ 为什么这一修特别值钱

F59 §4 明确记着：**v5 没跑到 boot，所以 F58 那个 `.pth` 修法【从未被验证】。**

⇒ **渲染一过，我们就第一次能真正检验那条 `.pth` 修法** —— 也就是 F53 所说"一个 boot bug 挡住整条高档线"是否已被解开。

**⇒ 这一修同时解锁两件事**：(a) 高档线能不能跑；(b) F58 的修法到底对不对。

## 4. 唯一的阻塞：GPU 名额

```
Kernel push error: Maximum batch GPU session count of 2 reached.
```
两个名额被**我们自己的**内核占着（RUNNING 的 `arc-duck-taaf` + QUEUED 的 `arc-vllm-probe`）。
**CLI 没有 cancel 动词** ⇒ **等一个名额释放后立刻推 `kernel-arc-duck18-va`。**

⚠️ **记录一个优先级判断**：`arc-vllm-probe`（T4 路线）在 F49 解锁 sm_120 之后**已经降级**；
它现在占着一个名额却不带来最高价值。**下一个名额释放时，若可能，优先推 `duck18-va`。**

## 5. 本轮净产出

| # | 产出 |
|---|---|
| 1 | **方向纠偏**：高档线是自己的 `duck-18`，不是外面那本 FP8 |
| 2 | **F59 渲染阻塞已定位到具体 cell 并修好**（单变量、逐格验证） |
| 3 | 修好后第一次具备**验证 F58 `.pth` 修法**的条件 |
| 4 | 记录名额争用与优先级（`duck18-va` > `vllm-probe`） |
