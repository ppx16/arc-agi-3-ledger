# F66 — 2026-10-11 — `duck18-va` 的**预先注册判读键**：运行前就写好该在日志里找什么

## 1. 这一枪到底是什么（单变量链）

```
kernel-arc-duck18-va  =  kernel-arc-duck18-fix (v5)  +  【附件修复】
                         └── v5 携带 F58 §3 的 zz_arc_numpy_fix.pth 修法
```

* **v5 的 `.pth` 修法从未被执行过** —— F59 证明它死在 nbconvert **渲染**（`missing attachment: tufa_labs.png`）。
* **本轮的附件修复是逐格验证的单变量编辑**（50/50 格 source 与原件的 **逐字节相同**，
  `work/diff_nb.py` 报 `cell-for-cell IDENTICAL`），唯一 delta 是那一个 `attachments` 条目。
* ⇒ **所以这一枪第一次真正执行 F58 的修法。**

## 2. ⭐ 判读键（运行前写下，免得事后编故事）

查 `ppxl16/arc-duck18-va` 的内核日志，按顺序找：

| 观察 | 含义 | 下一步 |
|---|---|---|
| **`InvalidNotebook: missing attachment`** | 附件修复**没生效** | 我改错了 notebook/版本；回到 `--check` 复核 |
| **日志里没有 `[arc_numpy_fix] pruned`** | `.pth` **没有执行** | F58 §3 的两个未验证项：① dist-packages **不可写**；② 路径不对（Python 3.13 的 site 目录可能不是 `/usr/local/lib/python3.13/dist-packages`）⇒ 先只验证"能不能写、写到哪" |
| **有 `[arc_numpy_fix] pruned …`，但 numpy 仍报 `should not try to import numpy from its source directory`** | **F58 的机制判断有误**：被修剪的路径之外还有第二个 numpy 源 | 打印**最终 `sys.path` 与每个含 `numpy/` 的路径**（v4 那个单行 JSON 探针就是这么破的案） |
| **有 `pruned`，且 numpy 正常** | ⭐ **F58 的修法成立** ⇒ **高档线（NVFP4+W4A16+sglang）解锁** | 让它跑完 25 局 → 若产出提交 → 动用当天名额 |
| **numpy 正常但死在别处** | 关卡前进了一格 | 读现场，按 F56/F57 的方式只改一个变量 |

## 3. 已知的两个未验证前提（F58 §3 自己列的）

1. **`/tmp/sgl/sgl-site` 里到底有没有 `numpy/`** —— 运行时是 4 GB 的 tar，从文件列表看不到；
2. **`/usr/local/lib/python3.13/dist-packages` 是否可写**。

⇒ **这两条无论结果如何都会被这一枪回答**，所以即使失败也是净收获。

## 4. 本轮其他动作（可核验）

* **自动名额等待器**：`work/push_when_slot_frees.py`，已在后台运行。
  它只把 `Maximum batch GPU session count / weekly quota / TPU session` 当作**等待态**，
  **其它任何失败都立即停止**（避免在真 bug 上空转）；调用的是同一个带守卫的 `push_kernel.py`。
  ⇒ **名额一释放就自动推 `kernel-arc-duck18-va`，不需要人再回来看。**
* **优先级判断已记录**：`arc-vllm-probe`（T4 路线）在 F49 解锁 sm_120 之后已降级，
  但它仍占着一个名额 ⇒ **它是当前唯一挡在 `duck18-va` 前面的东西**，而 CLI 没有 cancel 动词。
