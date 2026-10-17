# F74 — 2026-10-12 — 三处修复全部生效并被实测确认；但反查出更深的一个 bug：`.pth` 把好 numpy 删了

## 1. ⭐ 判读点读数（`duck18-vd`，第一次同时拿到全部三个）

```
NUMPY_ROOT_FOR_SUBPROCESS  /usr/local/lib/python3.12/dist-packages
NUMPY_PTH_WRITTEN          /usr/local/lib/python3.12/dist-packages/zz_arc_numpy_fix.pth  True
[arc_numpy_fix] pruned ['/usr/local/lib/python3.12/dist-packages'] root None
```

逐条对应的结论：

| 读数 | 证明了什么 |
|---|---|
| 跑到了 cell 10 并写出日志 | ⭐ **F65 附件修复成立**（渲染不再死，笔记本真执行了） |
| `NUMPY_PTH_WRITTEN … True`，路径是 **dist-packages** | ⭐ **F69 的写入位置修正成立**（不再从 `numpy.__file__` 派生） |
| `NUMPY_ROOT_FOR_SUBPROCESS … dist-packages` | ⭐ **F67 的前提成立**，且**F68 担心的"从运行时解析"没有发生** |
| `[arc_numpy_fix] pruned …` 出现 | ⭐ **F72 的字符串修复成立** —— 那段代码第一次真正被执行 |
| **运行了 39 分钟**（`vb` 只有 2 分钟），并产出对局录像 `ar25-… / bp35-… / cn04-…` | **它真的开始玩游戏了** |

⇒ **四处修复全部被实测确认。** 这是这条高档线走得最远的一次。

## 2. ⚠️ 但它仍然失败，而原因现在很清楚

**`root None`。**

`.pth` 由 `site` 在**解释器启动时**执行，**看不到父进程设置的环境变量** ⇒
`os.environ.get('ARC_NUMPY_ROOT')` 返回 `None`。于是那段逻辑：

```python
r = None
bad = [p for p in sys.path if p and p != r and os.path.isdir(os.path.join(p,'numpy'))]
[sys.path.remove(p) for p in bad]                                  # 删掉【每一个】含 numpy 的路径
[sys.path.insert(0, r) if (r and r not in sys.path) else None]     # 什么都没插回去
```

⇒ ⭐⭐ **在唯一一次它真正执行的时候，它【删掉了唯一可用的 numpy】然后什么都不补 ——
比不执行这个修复还糟。**

⚠️ 这也解释了 F58 的原始推理里那个**未被检验的假设**：作者假设 `.pth` 能读到那个环境变量。
它读不到。**而在此之前，这段代码从未被执行过（v5 死在渲染），所以这条假设从未被检验。**

## 3. 修法：让 `.pth` 自包含（`duck18-ve`）

把 root **直接算出来**，不再依赖环境变量：

```
旧： import sys,os;r=os.environ.get('ARC_NUMPY_ROOT');
新： import sys,os,sysconfig;r=sysconfig.get_paths()['purelib'];
```

`sysconfig` 在启动时总是可导入 ⇒ `r` 永远是 dist-packages ⇒
`bad` 只剩**别的**含 numpy 的路径（运行时那个），然后正确目录被插到 index 0。
**这才是这段代码的原意。**

**单变量纪律**：`work/fix_pth_selfcontained.py` 只改 `.pth` 正文的头部；
并且按 F73 立的规矩，**写完【重新读盘】核对**（`re-read verified: True`），
另加 `cell 10` 的 `compile()` 门槛与 GBK/往返检查。

## 4. `duck18-ve` 已推，下一轮的判读键（收窄后）

| 观察 | 含义 |
|---|---|
| `[arc_numpy_fix] pruned [...] root /usr/local/lib/python3.12/dist-packages` | ⭐ **修法正确执行**：`bad` 里才是该删的，`root` 不再是 None |
| `bad` 是**空列表** | ⇒ **运行时 `sgl-site` 里其实没有 `numpy/`** ⇒ 那么 numpy 问题另有来源（与 F58 的假设不同） |
| `bad` 含 `/tmp/sgl/sgl-site`（或其它） | ⇒ F58 的假设成立，且这次真的把它删掉了 |
| 之后 numpy 正常 → 继续跑完 25 局并产出提交 | ⭐ **高档线解锁** ⇒ 动用当天名额 |

⚠️ **`bad` 为空并非失败** —— 它是一个**独立的测量**，会直接回答"`sgl-site` 里到底有没有 `numpy/`"
（F58 列为未验证项 #1，F67 只能测 #2）。**无论哪种取值都是净收获。**
