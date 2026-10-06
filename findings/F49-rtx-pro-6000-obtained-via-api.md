# F49. ⭐⭐⭐ **拿到 RTX PRO 6000 了**：`sm_120`、102 GB —— 全部经 **API 推送**，无需任何人点浏览器

**日期**：2026-10-06
**证据**：`ppxl16/arc-agi-3-gpu-probe` **v2** 的日志，逐字：

```
=== ARC-AGI-3 ACCELERATOR PROBE ===
Tue Oct  6 17:32:41 2026
NVIDIA-SMI 580.178.04   Driver Version: 580.178.04   CUDA Version: 13.0
  0  NVIDIA RTX PRO 6000 Blac...   Off   00000000:05:00.0
     N/A  30C  P0  46W / 600W   0MiB / 97887MiB   0%   Default

torch 2.11.0+cu128 | cuda 12.8 | available True
DEVICE : NVIDIA RTX PRO 6000 Blackwell Server Edition
CC     : sm_120
VRAM   : 102.0 GB
VERDICT: BLACKWELL/RTX-Pro-6000 OK
```

## 1. 结论

**`machine_shape: NvidiaRtxPro6000` + 挂上比赛源 ⇒ API 推送就会为该卡排队，并且真的拿到。**
**不需要编辑器、不需要任何人点。** 排队约 **1 小时**（21:37Z 推 → 22:37Z 起排 → 17:32Z 跑… 实际等待约一小时量级）。

⇒ **F46 被彻底推翻**（它说"只能编辑器选"），**F48 的 A/B 推论由真实的卡证实**。

## 2. 为什么这条值钱

F44 的六道闸门里，**第 2–5 道全部只在 T4 上成立**：

| # | 闸门 | 在 sm_120 上 |
|---|---|---|
| 2 | 配方自己断言 GPU 型号（TAAF `setup_commands.json`: `rtx-pro-6000`/`h100`/`l4`） | ✅ **现在断言通过** |
| 3 | `flashinfer==0.6.6` 要 **sm_80+** | ✅ 满足 |
| 4 | 模型是 **FP8**，要 **cc ≥ 8.9** | ✅ 满足（sm_120） |
| 5 | 官方 vLLM 链 `libcudart.so.13` 而镜像 CUDA 12.8 | ⚠️ 仍需实测（但 CUDA 13.0 驱动已在位） |

⇒ **F45 普查里那一整档高位公开配方（NVFP4 / FP8）现在都可用了。**

## 3. ⚠️ 三个仍然成立的边界

1. **F46 §4 那个问题仍未回答**：**"评分复跑"会不会继承加速器**。
   探针证明的是**推送/交互运行**能拿到卡；评分复跑是另一条路径。
   **正在用一次真实提交测它**：`56883490`（14:42Z，用的正是声明了 `NvidiaRtxPro6000` 的 22.48 内核），
   截至 17:37Z 仍 PENDING。**平台保留最好成绩 ⇒ 这次测量免费。**
2. **拿卡 ≠ 拿分**：ARC 的分取决于时间预算内玩到哪一步，快卡只是让同样的预算能玩更多。
3. ⚠️ **"克隆别人的重型 notebook" 仍被空的 403 挡住**（换 id、清依赖、剥附件都试过）。
   **这仍然是把高位配方拿进来用的主要障碍**，只是**现在它不再是硬件问题，而是推送问题**。

## 4. 顺带修掉的一个小坑

`work/watch_probe.py` 崩在最后一步：`FileNotFoundError: state\arc_gpu_probe_result.json`
—— **`D:\kaggle\arc` 下没有 `state/` 目录**，而该脚本假定它存在（RSNA 仓里有，ARC 仓里没有）。
**结果因此没落盘**，是我事后直接重取内核日志才拿到的。**已建目录**。
⚠️ 教训：**跨仓库复用脚本时，"输出目录存在"是一个未经验证的假设**。
