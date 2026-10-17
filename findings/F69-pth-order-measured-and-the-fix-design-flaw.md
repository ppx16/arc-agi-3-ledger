# F69 — 2026-10-11 — F68 被实测证实：`.pth` 按【site 目录加入顺序】执行，所以"装错目录"会静默失效

## 1. 实测（`ppxl16/arc-pth-order`，纯 CPU，无数据集，不占 GPU 名额）

把两个伪造的 site 目录各放一个打标记的 `.pth`，按两种顺序 `site.addsitedir`：

```
ORDER A  runtime-then-dist     先打印 MARK_RUNTIME_SITE_PTH    ← 危险顺序
ORDER B  dist-then-runtime     先打印 MARK_DIST_PACKAGES_PTH
```

⇒ ⭐ **`.pth` 的执行顺序 = site 目录被加入 `sys.path` 的顺序**，**不是按路径名排序**。

## 2. 为什么这条决定了修法的成败

F58 的修法**全部价值**在于"dist-packages 的 `.pth` 排在 sgl-site 之后执行"。
而 duck 线里 sgl-site 是通过 **`site.addsitedir("/tmp/sgl/sgl-site")` 在运行时加入的**（cell 11）。

⇒ **若那个 `.pth` 被写进 sgl-site**（F68 的假设：`ARC_NUMPY_ROOT` 当时指向 sgl-site），
它就会**先**执行 ⇒ **修法会执行、日志里会有 `pruned`、一切看起来正常，却什么都没修好。**

**⇒ F68 的隐蔽失效模式：从"假设"变成"实测成立"。**

## 3. ⇒ 修正后的修法（可执行，明确）

F58 原文是 `_pth = Path(_np).parent.parent / "zz_arc_numpy_fix.pth"` ——
**把写入位置从一个"会漂移的量"（numpy 当时解析到哪）派生出来，就是缺陷本身。**

正确做法：
1. **写入位置必须显式**：用 `sysconfig.get_paths()["purelib"]`（本仓已实测它就是
   `/usr/local/lib/python3.13/dist-packages`，且**可写**，见 F67）——**不要**从 `numpy.__file__` 推；
2. **断言它落在了 dist-packages**，否则**直接 raise**（宁可不跑，也不要"看起来跑了"）；
3. **同时断言 dist-packages 的 `.pth` 确实存在**（写完读回来），因为这是 F67 那条
   "看不见执行 = 不知道有没有跑"的同一族要求；
4. 顺手把 F67 发现的**第二个含 numpy 的 site 目录**（`/usr/lib/python3/dist-packages`）也纳入
   修剪范围 —— F58 的"只修剪真的含 `numpy/` 的路径"天然覆盖它，但要**保持**这个写法。

## 4. 本轮净产出

| # | 产出 |
|---|---|
| 1 | **F68 由假设升格为实测**：`.pth` 顺序 = site 目录加入顺序 |
| 2 | 指出了 F58 修法的**根因缺陷**：写入位置从 `numpy.__file__` 派生 ⇒ 会漂移 |
| 3 | 给出四条**可执行的修正**（显式路径 + 两条断言 + 保留"只修剪含 numpy 的路径"） |
| 4 | ⭐ 全程**零 GPU 名额**（第二次用"CPU 内核切分问题"的手法推进主攻线） |
