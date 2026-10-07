# F55. 我的 numpy 假设被**自己的诊断否证**了 —— numpy 在 boot 里是好的，坏在 `boot_main` 里

**日期**：2026-10-07
**结论**：F54 推测"某个 `sys.path` 项遮住了系统 numpy"。**加了诊断之后，这个推测被证伪。**
`numpy` 在 t=69.0s **导入正常**，而失败发生在 `boot_main` 里。**诊断先于修法，这次是对的。**

---

## 1. 证据（`kernel-arc-duck18-fix` v2，逐字）

```
[  3.0s] PHASE_START unpack_sglang
[  3.0s] ZSTD_WHL ['zstandard-0.25.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl']
[  3.3s] ZSTD_INSTALL FAILED (continuing to the system copy): ERROR: ... is not a supported wheel on this platform.
[  3.3s] ZSTD_IMPORT ok from /usr/local/lib/python3.13/dist-packages/zstandard/__init__.py
[ 48.6s] PHASE_START unpack_cuda_toolkit
[ 69.0s] SETUP_OK True CUDA_HOME /tmp/cuda-root/usr/local/cuda-13.0
[ 69.0s] SYSPATH ['/tmp/zst', '/kaggle/input/duck-qwen38-nvfp4-mtp-vllm-smoke-v1/src/ARC3-Inference',
                  '/kaggle/input/.../src/tufa-arc-agi-framework', '/kaggle/input/duck-qwen38-nvfp4-mtp...']
[ 69.0s] NUMPY /usr/local/lib/python3.13/dist-packages/numpy/__init__.py        <-- 好的
[ 69.6s] PHASE_START patch_loader_prefetch_once
[ 69.6s] PHASE_START patch_ple_parallel_copy
[ 69.6s] PHASE_START patch_gptq_moe_scale_dtype
[ 69.6s] PHASE_START boot_main
         ModuleNotFoundError: No module named 'numpy._core._multiarray_umath'
         ImportError: Error importing numpy: you should not try to import numpy from ... its source directory
[  ...  ] RuntimeError: V1458 SGLang did not become ready: errors=[]
```

**两点：**
1. ⭐ **`NUMPY` 那行打印出了正确的系统路径** ⇒ **numpy 当时是好的**，`NUMPY_REPAIR` 未触发（设计如此：只在导入失败时修）。
2. **`/tmp/zst` 确实在 `sys.path[0]`，但它没有造成伤害** —— 因为 F54 的补丁让那次 `pip --target` 失败了，**该目录是空的**。

---

## 2. 因此新的定位：坏在 `boot_main`，且是在三个 monkey-patch 之后

顺序是 `patch_loader_prefetch_once` → `patch_ple_parallel_copy` → `patch_gptq_moe_scale_dtype` → **`boot_main`**。

`numpy._core._multiarray_umath` 是 **numpy 2.x 的内部模块**；它缺失 + "source directory" 那句守卫，通常意味着
**有一个不同版本/半成品的 numpy 在之后进入了 `sys.modules` 或 `sys.path`**。

⚠️ **谁是嫌疑，我不猜**。下一步应当是**把诊断推进到这些阶段内部**：
在 `boot_main` 入口、以及三个 patch 各自之后，各打一次 `NUMPY`（`numpy.__file__` + `numpy.__version__`）
与 `SYSPATH`。**哪一个把 numpy 换掉，就一目了然。** 这仍然是"打印 → 再修"，与 F54 同一套模式。

---

## 3. 这一轮的进展怎么算

| | 修前（v1） | 现在（v2） |
|---|---|---|
| zstandard | 4 秒死 | ✅ **回退成功，`unpack_sglang` 通过** |
| CUDA toolkit | 未到达 | ✅ `SETUP_OK True`，`CUDA_HOME` 正常 |
| numpy（我加的诊断） | 无 | ✅ **t=69s 正常** |
| 失败点 | 4 s | **`boot_main` 内**（三个 patch 之后） |
| 我的假设 | 遮蔽（F54） | ❌ **被自己的诊断否证** ✅ *这是好事* |

⇒ **boot 链已经走过 4 道关，失败点落在最后一阶段。** F53 那句"一串独立的依赖/路径问题，每修一道后移一层"**被完整证实**。

---

## 4. 复现

```bash
python work/watch_duckfix.py        # D:\kaggle\arc\ 下；成功与失败都读诊断行
# 原始日志：state/duckfix_v2.log（31432 字符）
```
