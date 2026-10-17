# F68 — 2026-10-11 — `duck18-va` 的第二个判读点：`NUMPY_ROOT_FOR_SUBPROCESS` 必须指向 dist-packages

F67 说"没看到 `pruned` 时，先核 v5 往哪个路径写，别再怀疑权限"。**这一轮把那个路径核出来了。**

## 1. 核到的代码（cell 10 逐字）

```python
def _np_ok():
    try:
        import numpy as _np
        return _np.__file__                 # <- 返回的是 numpy/__init__.py 的路径
    except Exception as _e:
        return f"ERR {type(_e).__name__}: {_e}"

...  # 先做一次 repair：修剪含 numpy 的路径，再重新 _np_ok()
os.environ["ARC_NUMPY_ROOT"] = str(Path(_np).parent.parent)
log("NUMPY_ROOT_FOR_SUBPROCESS", os.environ["ARC_NUMPY_ROOT"])

_pth = Path(_np).parent.parent / "zz_arc_numpy_fix.pth"
```

**路径算术核对**：若 `_np = …/dist-packages/numpy/__init__.py`，则
`parent = …/dist-packages/numpy`、`parent.parent = …/dist-packages` ✅ **正确**。
⇒ **我原先怀疑的"`.parent.parent` 少了一层"是错的 —— 这个写法是对的。**

## 2. ⚠️ 但由此暴露真正的风险（新的、可判读的）

**正确性完全依赖"那一刻 numpy 是从 dist-packages 解析出来的"。** 而已知运行时会用
`site.addsitedir("/tmp/sgl/sgl-site")` 把 sgl-site 加成一个 site 目录（cell 11）。

⇒ **若 repair 之后 numpy 仍从 `/tmp/sgl/sgl-site` 解析**，那么：
* `ARC_NUMPY_ROOT` = `/tmp/sgl/sgl-site`
* `.pth` 被写进 **`/tmp/sgl/sgl-site/zz_arc_numpy_fix.pth`**
* ⚠️ 而 **sgl-site 在 dist-packages【之前】被处理** ⇒ **F58 赖以成立的"晚执行"这一性质被完全抵消**
  ⇒ 修法**看起来装上了、也确实会执行，但排在被它要压倒的那一方之前** ⇒ **仍然无效**。

⇒ ⭐ **这比"没装上"更难发现**：日志里会有 `pruned`，会一切正常，但 numpy 依旧坏。

## 3. ⇒ 判读点（加进 F66 的键）

**跑起来后，在日志里找这一行：**

```
NUMPY_ROOT_FOR_SUBPROCESS <path>
```

| 观察 | 含义 | 下一步 |
|---|---|---|
| `…/usr/local/lib/python3.13/dist-packages` | ✅ **写入位置正确**，`.pth` 会晚执行 | 看 numpy 是否恢复；若没恢复，说明要修的是别的 numpy 源（F67 发现 `/usr/lib/python3/dist-packages` 也有一个） |
| **`/tmp/sgl/sgl-site`** | ⚠️ **修法装错了地方，顺序优势消失** | **不要**再跑；改成**硬编码** dist-packages 路径写 `.pth`，或改成"写到**所有** site 目录里、并断言 dist-packages 的那一份存在" |

⚠️ **这条预期是纯本地代码读出来的，不占用任何 GPU 名额** —— 与 F67 的 CPU 探针同一手法：
**把问题里不需要 GPU 的那一半先结掉。**

## 4. 本轮净产出

| # | 产出 |
|---|---|
| 1 | **核掉一个可疑点**：`.parent.parent` 的写法是**对的**（我原先的怀疑不成立） |
| 2 | **发现一个更隐蔽的失效模式**：修法可能装进 sgl-site ⇒ 会执行但顺序无效 ⇒ 日志一切正常而问题依旧 |
| 3 | 给出**一个新判读点**（`NUMPY_ROOT_FOR_SUBPROCESS`）与两种取值各自的下一步 |
