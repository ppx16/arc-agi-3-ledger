# F73 — 2026-10-12 — 字符串断裂已修，`cell 10` 现在能编译；高档线推上 `duck18-vd`

## 1. 找到了真正的断裂形态

F72 只说了"缺一个引号"，这一轮看清了**实际形态**：字符串在**换行处**被切断，而且续行**多了一个前导引号**。

```
错误形态：
    "print('[arc_numpy_fix] pruned',bad,'root',r,flush=True)
", encoding="utf-8")

正确形态：
    "print('[arc_numpy_fix] pruned',bad,'root',r,flush=True)",
    encoding="utf-8")
```

⇒ 我第一版 `fix_missing_quote.py` **只补引号、没动那个前导引号**，所以修完**仍然** `unterminated`。
`work/fix_pth_string_break.py` 用**两行换两行**的精确替换解决，并且：
* **硬门槛只对被我编辑的那一格**（`cell 10`）—— 因为 `cell 45: 'await' outside function` 是
  `compile()` 对顶层 await 的**误报**，IPython/papermill 是允许的；
* **断言产出的 `.pth` 正文仍是一行、且以 `import` 开头**（F58 依赖的性质），实测长度 287、`startswith('import') == True`。

## 2. ⚠️ 顺带修掉我自己的一个"静默无操作"

第一版 `fix_missing_quote.py` 在发现**别的**格有语法错时**先 `return 1` 再写文件** ——
⇒ **它报告"已修 1 处"，磁盘上却一个字节都没改。**

**⇒ 这是本项目第 N 次"看起来做了、实际没做"**（A170 检查点、A183 slug、F58 执行顺序、F71 我的补丁）。
**这次的形态最阴**：工具**自己的输出说它修了**，而它没写盘。
⇒ 规矩：**"修了"必须由【重新读取磁盘】来证明**，不能由工具自己的打印来证明。
本轮已按此做：修完立刻重新加载 notebook、重新 `compile()`、并打印修复后的源码行。

## 3. 三处修复现在都在 `duck18-vd` 里（只动 cell 10，+61 字节）

| # | 修复 | 出处 |
|---|---|---|
| 1 | **附件内嵌**（渲染不再死） | F65 / F70，已由 F71 证实生效 |
| 2 | **`.pth` 写入位置显式取 dist-packages**（不再从 `numpy.__file__` 派生） | F69 |
| 3 | **字符串断裂修复**（cell 10 现在能编译） | **本轮** |

`ppxl16/arc-duck18-vd` **v1 已推**，状态由监视器跟。

## 4. 推起来之后要读什么（判读键，合并 F66/F68/F69/F72）

| 观察 | 含义 | 下一步 |
|---|---|---|
| 仍 `missing attachment` | 附件修复没生效 | 复核（不该发生） |
| 仍 `SyntaxError` | 还有断裂的字符串 | 用 `fix_pth_string_break.py` 的同一手法逐处核 |
| `PTH_TARGET_DIR …/dist-packages` + `PTH_NUMPY_ROOT /tmp/sgl/sgl-site` | ⭐ F68/F69 假设成立：numpy 确实从运行时解析，而修正版已把它掰回 | 看 numpy 是否恢复 |
| **有 `[arc_numpy_fix] pruned …` 且 numpy 正常** | ⭐ **F58+F69+F72 全部成立 ⇒ 高档线解锁** | 跑完 25 局 → 动用当天名额 |
| 有 `pruned` 但 numpy 仍坏 | 机制还差一层 | 打最终 `sys.path` 与**所有**含 `numpy/` 的路径（F67 已知两个源） |

## 5. 本轮净产出

| # | 产出 |
|---|---|
| 1 | **看清并修好字符串断裂**（两行换两行），`cell 10` 现在 `compile()` 通过 |
| 2 | 补上**只对被编辑格强制**的门槛（避免被 `cell 45` 的误报挡住） |
| 3 | 发现并修正**"工具说修了、磁盘没改"**这一新形态的静默失败，并立规矩：**以重新读盘为证** |
| 4 | `duck18-vd` 已推，三处修复齐备 |
