# F54. zstandard 回退**成功了** —— 失败点从 4 秒推进到 101 秒，换成了 numpy 被弄坏

**日期**：2026-10-07
**结论**：F52/F53 的 boot 补丁**按设计生效并解决了原问题**。`unpack_sglang` 现在**通过**。
新的、且是**另一个**障碍：CUDA toolkit 解包之后 **numpy 导入失败**。

---

## 1. 证据（逐字，来自 `ppxl16/arc-agi-3-duck-18-1gc-fix` v1，跑满 2 小时才报 ERROR）

```
[  4.9s] ZSTD_WHL ['zstandard-0.25.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl']
[  5.2s] ZSTD_INSTALL FAILED (continuing to the system copy): ERROR: zstandard-0.25.0-cp312-... is not a supported wheel on this platform
[  5.2s] ZSTD_IMPORT ok from /usr/local/lib/python3.13/dist-packages/zstandard/__init__.py
[ 50.7s] PHASE_START unpack_cuda_toolkit
[ 75.4s] SETUP_OK True CUDA_HOME /tmp/cuda-root/usr/local/cuda-13.0
[ 75.4s] CUDA_LIB_REPAIR {'lib64': 'symlink -> /tmp/cuda-root/.../lib', 'libcudart_resolves': '...'}
[101.4s] ModuleNotFoundError: No module named 'numpy._core._multiarray_umath'
[101.4s] ImportError: Error importing numpy: you should not try to import numpy from
[101.6s] RuntimeError: V1458 SGLang did not become ready: errors=[]
```

**三点必须记牢：**

1. ⭐ **`ZSTD_INSTALL FAILED` + `ZSTD_IMPORT ok`** —— 这正是补丁设计的路径。
   钉死的 cp312 轮子在 Python 3.13 上装不上（**F52 的原病**），**系统副本接手并成功**。
   ⇒ **F52 的诊断与修法都被证实**：那个轮子**从来就不需要**，它只是被写死了。
2. **新增的两行诊断在 t≈5s 就把想要的、手上的都说了** —— F52 推荐的那条"廉价保险"确实买到了东西：
   以前这个坑要 4 秒死 + **6.75 小时排队**才发现，现在一行可读。
3. **失败点后移到 101s**，且**原因完全不同**：`numpy._core._multiarray_umath` 缺失。

---

## 2. 新的障碍：numpy 在哪一步被弄坏的

**顺序很关键**：`unpack_sglang`（成功）→ **`unpack_cuda_toolkit`** → `SETUP_OK True` → **numpy 导入失败**。
⇒ 坏掉的时间窗口**在 CUDA toolkit 解包这一段**（或紧随其后）。

⚠️ **两条最可能的机制，都还没验证**：
- **`pip install --target` 目录被留在 `sys.path` 前面**，遮住了系统 numpy（`--no-deps` 本该避免拉 numpy，但 `--target` 本身会把目录放进优先级更高的位置）
- **CUDA toolkit 解包带进了不完整的 numpy**，或改了 `numpy` 的 `.pth`/路径

⚠️ 报错文案里的 *"you should not try to import numpy from its source directory"* 是 numpy 的**源码树守卫**，
说明它**在某个包含 numpy 源码/半成品的目录下被导入**了 —— 与上面第一条一致。

---

## 3. 下一步（按代价排序，尚未执行）

1. **先确认，不要猜**：在 boot 里 `unpack_cuda_toolkit` 之后加一行
   `log("SYSPATH", sys.path[:6])` 与 `log("NUMPY", np.__file__)`（若可导入）——
   **把"谁在 sys.path 前面"变成读数**。零风险，且下一次运行就能定位。
2. **若确认是 `--target` 遮蔽**：把 `zdir` / toolkit 目录移到 `sys.path` **末尾**，
   或在 `import numpy` 之前**先 `import numpy` 成功再改 sys.path**（"先取后改"）。
3. ⚠️ **不要**为了绕过而改 numpy 版本 —— 那会把一个**路径问题**伪装成一个**版本问题**，
   而 `SETUP_OK True` 说明 CUDA 那一段本身是好的。

---

## 4. 为什么这一轮仍然算进展

| | 修前 | 修后 |
|---|---|---|
| 死在 | **4 s**（`unpack_sglang`） | **101 s**（numpy，在 CUDA toolkit 之后） |
| 症状可读性 | `FileNotFoundError: /tmp/sgl/sgl-site/...`（**误导成"缺文件"**） | `ModuleNotFoundError: numpy._core._multiarray_umath` + 两行明确诊断 |
| 根因 | 钉死的 cp312 轮子 | **另一个**（路径遮蔽，待确认） |

⇒ **F53 那句"一个 boot 修复解锁整条线"被证实为方向正确，但不是一个修复就够** —— 启动链上还有**至少一道**独立的依赖/路径问题。**每修一道，失败点就往后移，这是正常的推进。**
