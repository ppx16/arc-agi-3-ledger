# F70 — 2026-10-11 — 把 F69 的修正**写进了内核**：`duck18-vb`，并在名额释放时优先推它

## 1. 做了什么

F69 证明 F58 的修法有一个**会静默失效的根因缺陷**：写入位置从 `Path(_np).parent.parent`
派生 —— 而 `_np` 是"当时 numpy 解析到哪"，所以一旦 numpy 从运行时的 `/tmp/sgl/sgl-site`
解析，`.pth` 就会写进 sgl-site，**先于 dist-packages 执行** ⇒ 顺序优势消失、日志却一切正常。

`work/patch_pth_target.py` 把那**一个赋值**换成显式 + 带断言的目标：

```python
import sysconfig as _sc
_pth_dir = Path(_sc.get_paths()["purelib"])          # 显式，不从 numpy.__file__ 推
assert _pth_dir.is_dir(), f"purelib is not a directory: {_pth_dir}"
log("PTH_TARGET_DIR",  str(_pth_dir))                 # 报告目标
log("PTH_NUMPY_ROOT",  str(Path(_np).parent.parent))  # 同时报告 numpy 当时解析到哪
_pth = _pth_dir / "zz_arc_numpy_fix.pth"
...
assert _pth.is_file(), "the .pth was not written"     # 写完读回来断言
```

**单变量纪律**：`work/diff_nb.py` 核对为 **只有 cell 10 变化**（14371 → 14989 字节）。
另：`ascii-only YES` / `GBK-decodable YES` / 50 格往返一致。

⭐ **它还顺带把两个事实分开报告**（`PTH_TARGET_DIR` 与 `PTH_NUMPY_ROOT`）——
F68 的判读点原本只有一个量（`NUMPY_ROOT_FOR_SUBPROCESS`），现在**写入位置与 numpy 来源各自独立可见**，
所以"装错地方"这个失效模式**下一次运行就能直接看出来，不用再推理**。

## 2. 名额：把等待器改指向修正版

* 旧的等待器（推 `duck18-va`）**已终止**；
* 新的等待器在后台跑，**目标改为 `kernel-arc-duck18-vb`**（10 小时窗口 / 每 8 分钟重试）。

⇒ **名额一释放就推的是修正版，而不是那个带已知缺陷的版本。**
`kernel-arc-duck18-va` 保留在原地，作为"未修正"的对照，不再推。

## 3. 本轮的判读键（合并 F66 / F68 / F69）

`duck18-vb` 跑起来后，日志里按顺序看：

| 观察 | 含义 |
|---|---|
| `missing attachment` | 附件修复没生效（不该发生，50/50 格已核对） |
| **`PTH_TARGET_DIR …/dist-packages`** 且 **`PTH_NUMPY_ROOT /tmp/sgl/sgl-site`** | ⭐ **F68/F69 的假设成立**：numpy 确实从运行时解析 ⇒ 旧写法会装错，**修正版把它掰回来了** |
| 有 `[arc_numpy_fix] pruned …` 且 numpy 正常 | ⭐ **F58+F69 成立 ⇒ 高档线解锁** ⇒ 跑完 25 局就动用当天名额 |
| 有 `pruned` 但 numpy 仍坏 | 机制还差一层 ⇒ 打最终 `sys.path` 与所有含 `numpy/` 的路径（F67 已知有两个源） |
| `AssertionError: purelib is not a directory` / `the .pth was not written` | 修正版自己的断言触发了 —— **这正是它设计的目的**：宁可不跑，也不要"看起来跑了" |

## 4. 本轮净产出

| # | 产出 |
|---|---|
| 1 | **F69 的修正落到内核里**（`duck18-vb`，单 cell 变更，已核） |
| 2 | 判读点从"一个量"变成"两个独立可见的量"，**把"装错地方"变成可直读** |
| 3 | **等待器改指向修正版**，避免把稀缺名额花在带已知缺陷的版本上 |
| 4 | 全程零 GPU 名额（第三次用 CPU/本地手段推进主攻线） |
