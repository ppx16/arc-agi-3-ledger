# F58. 决定性读数：我的 `sys.path` 插入**被覆盖了**，运行时目录赢在**执行顺序**上

**日期**：2026-10-07
**结论**：v4 的单行 JSON 探针给出了完整现场。**F56/F57 的争点解决了**：
`sitecustomize` 里的 `insert(0, ...)` **确实执行了，但之后运行时的 `.pth` 又把它挤到 index 6**。
⇒ **在 sitecustomize 里修永远太早。** 正确机制是**晚于运行时 `.pth` 执行**的东西。

---

## 1. 决定性证据（v4，子进程自己打的单行 JSON）

```json
{"err": "ImportError",
 "msg": "Error importing numpy: you should not try to import numpy from its sourc",
 "cwd": "/kaggle/working",
 "path": ["/tmp/sgl/sgl-site/nvidia_cutlass_dsl/dsl_packages",   <- 0
          "/tmp/sgl/sgl-site",                                   <- 1  ⭐ 运行时
          "/tmp/sgl/boot",                                       <- 2
          "/usr/lib/python313.zip",
          "/usr/lib/python3.13",
          "/usr/lib/python3.13/lib-dynload",
          "/usr/local/lib/python3.13/dist-packages",              <- 6  ⭐ 我插的在这里
          "/kaggle/input/.../tufa-arc-agi-framework/src",
          "/kaggle/input/.../tufa-arc-agi-framework",
          "/kaggle/input/.../ARC3-Inference"],
 "nr": "/usr/local/lib/python3.13/dist-packages"}
```

**两条硬结论：**

1. ⭐ **`/usr/local/lib/python3.13/dist-packages` 在 index 6，不在 0** ⇒
   我的 `sys.path.insert(0, _nr)` **被后续动作覆盖**。F57 里"插回最前却无效"的谜团解开：
   **不是插入没用，是插入被执行顺序推翻了。**
2. ⭐ **`/tmp/sgl/sgl-site` 在 index 1，排在 dist-packages 之前** ⇒
   若它内部有 `numpy/`（**首要嫌疑，尚未证实**），numpy 就从那里解析 ⇒ 触发
   *"should not try to import numpy from its source directory"*。
3. **`cwd` = `/kaggle/working`** ⇒ 不是 cwd 的锅（F57 列的第一嫌疑**可以排除了**）。

## 2. 为什么在 `sitecustomize` 里修没用（机制）

`sitecustomize` 在 **`site` 模块导入期间**执行；而 **`.pth` 文件的处理也在 `site` 里，且按 `sys.path` 里的
site 目录顺序进行**。运行时的 `.pth`（在 `sgl-site` 里）**排在我的代码之后**把它的目录插到前面。
⇒ **任何在 sitecustomize 里做的"插到最前"，都会被随后的 `.pth` 覆盖。**

## 3. 修法（明确、可执行，尚未实施）

**在 dist-packages 里写一个 `.pth`，让它在 sgl-site 的 `.pth` 之后执行**（`.pth` 按 site 目录顺序处理，
dist-packages 在 sgl-site 之后）：

```python
# /usr/local/lib/python3.13/dist-packages/zz_arc_numpy_fix.pth
import sys, os
_r = os.environ.get("ARC_NUMPY_ROOT")
_o = [p for p in list(sys.path) if p != _r and os.path.isdir(os.path.join(p, "numpy"))]
for _p in _o:
    sys.path.remove(_p)
if _r and _r not in sys.path:
    sys.path.insert(0, _r)
```

**要点：**
- **只移除【真的含 `numpy/` 的】路径**，其余（运行时的 torch 等）**原样保留** ⇒ 不会打断 SGLang
- 名字以 `z` 开头，保证同目录内也排在后面
- **保留一行诊断**：把移除掉的路径打出来（`[arc_numpy_fix] pruned ...`），这样下一次能**确认它跑了**
  —— v4 的教训就是"看不见执行就等于不知道有没有跑"

⚠️ **未验证项（必须下次运行确认）**：
1. `/tmp/sgl/sgl-site` 里到底有没有 `numpy/`（**运行时是 4 GB 的 tar，从文件列表看不到**）
2. dist-packages 是否可写

## 4. 这一轮的净进展

| | |
|---|---|
| 排除 | cwd 污染（v4 的 `cwd` 读数） |
| 排除 | "插入无效"这个解释 —— **真相是执行顺序覆盖** |
| 得到 | **修复机制**：不能改 sitecustomize，要写晚执行的 `.pth` |
| 累计已过 | zstandard / CUDA toolkit / 父进程 numpy / 三个 patch 阶段 |

⇒ **同一道关（子进程环境），但这一轮把它从"不知道怎么回事"变成了"知道机制、知道修法"**。
F54/F56 两次假设被否证，第三次（F58）**有子进程自报的现场作证**。
