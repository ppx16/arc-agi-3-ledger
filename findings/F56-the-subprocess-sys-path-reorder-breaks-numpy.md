# F56. numpy 的根因定位到**子进程的 `sys.path` 重排** —— 父进程是好的，坏的是 SGLang 服务子进程

**日期**：2026-10-07
**结论**：F55 把失败点收窄到 `boot_main`。进一步定位：**`boot_main` 把 SGLang 服务作为【子进程】启动，
并给它一个把运行时目录移到 Kaggle 自带包【前面】的 `sys.path`。父进程 numpy 正常，子进程的坏了。**
这与 `numpy._core._multiarray_umath` 缺失 + "source directory" 守卫**完全吻合**。

---

## 1. 证据（`kernels/kernel-arc-duck18/...ipynb` **CELL 11**，逐字）

```python
# PYTHONPATH alone skips .pth files; sitecustomize adds the runtime as a site dir AHEAD of Kaggle's own torch.
"_new = [p for p in sys.path if p.startswith(_s)]\n"
"sys.path[:] = _new + [p for p in sys.path if not p.startswith(_s)]\n"
"PYTHONPATH": f"{BOOT}:{SITE}", "PYTHONNOUSERSITE": "1",
p = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT, env=server_env(), start_new_session=True)
```

⇒ **这行注释自己就说了**：*"adds the runtime as a site dir **AHEAD OF** Kaggle's own torch"*。
设计者**故意**把运行时前置（为了让它用自己的 torch）。
**代价是它同样把 Kaggle 的 numpy 挪到了后面**，而运行时那份 numpy 与 Python 3.13 的
`_multiarray_umath` 内部布局不匹配 ⇒ 子进程的 `import numpy` 崩。

## 2. 与父进程的证据完全一致

| 进程 | numpy 状态 | 证据 |
|---|---|---|
| **父进程（boot cell）** | ✅ **正常** | `[69.0s] NUMPY /usr/local/lib/python3.13/dist-packages/numpy/__init__.py`（我加的诊断） |
| **子进程（SGLang server）** | ❌ **坏** | `ModuleNotFoundError: No module named 'numpy._core._multiarray_umath'`，随后 `RuntimeError: V1458 SGLang did not become ready: errors=[]` |

⇒ **`errors=[]` 是误导性的**：父进程的 phase 表里没有错误，因为**崩的是子进程**，它的 traceback 只出现在 stdout 流里。

## 3. 修法（**尚未实施**，下一轮的明确动作）

**原则：让子进程的 numpy 仍是父进程那份。**

1. **在 `server_env()` 里传入父进程的 numpy 根**：
   `"ARC_NUMPY_ROOT": os.path.dirname(os.path.dirname(numpy.__file__))`
   （即 `/usr/local/lib/python3.13/dist-packages`）
2. **在 sitecustomize 的重排之后，把它插回最前**（放在 `_new` 之前或紧随其后）：
   ```python
   _nr = os.environ.get("ARC_NUMPY_ROOT")
   if _nr and _nr not in sys.path:
       sys.path.insert(0, _nr)
   ```
   这样运行时仍拿到它的 torch（`_new` 仍在前），**但 numpy 解析回系统那份**。
3. **加一行子进程侧诊断**：在子进程启动后立刻打印 `numpy.__file__` / `__version__` 与 `sys.path[:6]`
   —— **让"子进程看到的是哪个 numpy"变成读数**，而不是靠推断。

⚠️ **不要**改 numpy 版本、也不要为了绕开而动运行时的 torch 前置 —— 那两件事都会把
**一个顺序问题**伪装成**版本问题**，而后者会让这个 boot 更难修。

## 4. 失败的形状（记给下一次）

| 版本 | 死在 | 耗时 |
|---|---|---|
| 原始 | `unpack_sglang`（cp312 轮子） | **4 s** |
| `-fix` v1 | `unpack_sglang` → 已修 | 101 s（numpy） |
| `-fix` v2 | `boot_main` → **子进程 numpy** | 到 `boot_main` 才崩 |

⇒ **四道关已过（zstandard → CUDA toolkit → 父进程 numpy → 三个 patch 阶段）**，
**只剩子进程的环境这一道。** F53 的"每修一道后移一层"继续成立。

---

## 5. 已实施（同日晚些，`kernel-arc-duck18-fix` **v3**）

三处改动，`work/build_duck18_fix.py` 生成，**每处锚点必须恰好匹配一次否则 FATAL**：

| # | 位置 | 改动 |
|---|---|---|
| A | cell 10（我 F54 加的 numpy 检查之后） | `os.environ["ARC_NUMPY_ROOT"] = str(Path(_np).parent.parent)` —— 把**父进程解析出的** numpy 根交给子进程 |
| B | cell 11 的 `sitecustomize.py` 生成串 | 在**那次故意的运行时前置重排之后**，把 `ARC_NUMPY_ROOT` 插回 `sys.path[0]`；并**打印子进程实际看到的 numpy** |
| C | cell 11 的 `server_env()` | 透传 `"ARC_NUMPY_ROOT": os.environ.get("ARC_NUMPY_ROOT", "")` |

**设计要点**：运行时**仍然**在 `_new` 里靠前（**它的 torch 不能被换掉**），但 **numpy 解析回系统那份**。
⚠️ **刻意没做**：不改 numpy 版本、不动 torch 的前置 —— 那会把**顺序问题伪装成版本问题**。

**构建时验证（`work/verify_build.py`）**：50 个 cell 全在、**只有 cell 10/11 变化且都变大**、
`metadata` 逐字相同、**非 source 的 cell 字段零差异**、cell 10 的全部守卫在位。

⚠️ **一处如实记录**：v3 的文件字节数比 v2 **小了约 109 KB**，而内容**增加**了 5026 字符。
我用逐字节解析核对过**没有丢任何内容**（top-level 键、metadata、outputs、非 source 字段全部一致），
但**这个体积差的成因我没有查清**，因此写在这里而不是编一个解释。
**正确性的判据是 `kaggle kernels push` 是否接受 —— 它接受了（version 3）。**

