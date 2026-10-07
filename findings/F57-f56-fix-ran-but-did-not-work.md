# F57. F56 的修法**执行了但没用** —— 假设被证伪，而病因必须由子进程自己说出来

**日期**：2026-10-07
**结论**：v3 的补丁**完全按设计运行**（环境变量传到、sitecustomize 执行、dist-packages 插回 `sys.path[0]`），
**而 numpy 仍然坏，错误逐字不变。** ⇒ **F56 的"运行时前置把 numpy 挤到后面"是错的假设。**
病因是**某种"把 dist-packages 放到最前也无法覆盖"的机制**。

---

## 1. 证据（`kernel-arc-duck18-fix` v3，逐字）

```
[87.6s] NUMPY /usr/local/lib/python3.13/dist-packages/numpy/__init__.py        <- 父进程: 正常
[87.6s] NUMPY_ROOT_FOR_SUBPROCESS /usr/local/lib/python3.13/dist-packages      <- 我传的根: 正确
[88.2s] PHASE_START boot_main
[sitecustomize] NUMPY BROKEN ImportError Error importing numpy: you should not try to import numpy from
         ModuleNotFoundError: No module named 'numpy._core._multiarray_umath'
         RuntimeError: V1458 SGLang did not become ready: errors=[]
```

**三件事同时成立**：
1. `ARC_NUMPY_ROOT` **确实传进了子进程**（`NUMPY_ROOT_FOR_SUBPROCESS` 是父进程打的，值是系统 dist-packages）
2. `[sitecustomize] NUMPY BROKEN` **是子进程打的** ⇒ **sitecustomize 执行了**，我的 `sys.path.insert(0, _nr)` **跑过了**
3. **而 numpy 还是坏，且错误一字不差** —— 连 "should not try to import numpy from ... source directory" 这句守卫都还在

⇒ **"把系统 dist-packages 放到最前"这个动作，不足以修好它。**

---

## 2. 这意味着病因是什么（候选，尚未证实）

numpy 那句守卫的触发条件是：**从一份 numpy 源码树里导入**。
既然 dist-packages 已在 `sys.path[0]`，那么剩下的可能只有几种：

- **`sys.path[0]` 不是它以为的那个** —— 对 `python -m`，`sys.path[0]` 是 **cwd**，
  而 sitecustomize 是在 `site` 导入时执行的，**cwd 的插入可能发生在我之后**；
  ⇒ 若 cwd 里有 `numpy/`，它就会赢。**这是当前首要嫌疑。**
- **`.pth` / `sitecustomize` 的执行顺序**：运行时可能还有**它自己的** sitecustomize 或 `.pth`，
  在我的之后执行并把运行时目录再插到前面。
- **`numpy` 已被部分导入**：错误里同时有 `numpy._core._multiarray_umath` 缺失，
  说明**某个 numpy 包被找到但装的是不匹配的构建**（版本/ABI 错配），而不是完全找不到。

⚠️ **我不猜。** v3 的探针本想打印 `sys.path[:6]`，但**那段没落进日志行**（numpy 的 ImportError 是多行的，
日志把条目切开了）。

---

## 3. v4 已推：把子进程的现场打成**一行 JSON**

改动（`work/build_duck18_fix.py`）：子进程侧的探针从"多行 print"改成**单行 JSON**，
并**加上 `cwd`**（上面第一条嫌疑的关键输入）：

```
[sitecustomize] NUMPY_BROKEN {"err": ..., "msg": ..., "cwd": ..., "path": [前10项], "nr": ...}
```

成功后也改成单行：`[sitecustomize] NUMPY_OK <file> <version>`。

**⇒ 下一次运行会直接给出"哪个目录赢了、cwd 是什么"，而不是让我从多行报错里拼。**

---

## 4. 进度账（这道关是**唯一**剩下的）

| 版本 | 结果 |
|---|---|
| 原始 | `unpack_sglang` 4 秒死（cp312 轮子） |
| v1 | 父进程 numpy（已修：回退到系统 zstandard） |
| v2 | 子进程 numpy —— **首次把病因定位到子进程** |
| v3 | 子进程 numpy —— **假设被证伪**（插回 dist-packages 无效） |
| **v4** | **等一次运行，让子进程自己报出 `cwd` + `path`** |

⇒ **zstandard / CUDA toolkit / 父进程 numpy / 三个 patch 阶段 全部已过。**
**只剩子进程的环境这一道，而它现在是"缺一个读数"的状态，不是"缺一个想法"的状态。**

⚠️ 如实记：**我连续两轮（F54、F56）的假设都被自己的诊断否证**。
这不是浪费 —— **两次否证各自排除了一整类原因**（F54 排除"父进程被污染"，F56 排除"顺序问题"），
而这正是"先打印、再修"相对"直接改"的价值。
