# F53. 整条高阶线的失败被收敛成【一个】可修的启动 bug —— 两个死法是互补的

**日期**：2026-10-07
**结论**：`duck18-live0/live1`、`size-50/150/300/600`、`cells-1/4/50` 全部 **ERROR**，
唯一 **COMPLETE** 的是 `arc-gpu-ctrl`（也就是我们 24.53 来源那一支）。
把它们逐一看过之后，失败**不是散乱的**，而是**两个互补的死法**——因此**一个修复即可解锁整条线**。

---

## 1. 两个死法

| 情形 | 症状 | 判定 |
|---|---|---|
| **拿不到 Pro 6000**（分到 T4） | `RuntimeError: wrong accelerator, expected RTX PRO 6000: Tesla T4, 580.178.04, 15360 MiB` | ✅ **预期行为**——它**响亮拒绝**，而不是在错配置上跑出一个假分数 |
| **拿到 Pro 6000** | `PHASE_ERROR unpack_sglang` → `zstandard-0.25.0-cp312-...whl is not a supported wheel on this platform` → 36 s 后 `FileNotFoundError: /tmp/sgl/sgl-site/...`（**F52**） | ❌ **这才是要修的**；而且它以"缺文件"的样子收场，**误导性极强** |

证据（逐字）：
- `arc-duck18-live1`：`RuntimeError: wrong accelerator, expected RTX PRO 6000: Tesla T4, ...`
- `ppxl16/arc-agi-3-duck-18-1gc`（**拿到了** `NVIDIA RTX PRO 6000 Blackwell Server Edition, 97887 MiB`）：`PHASE_ERROR unpack_sglang` + `cp312 ... not a supported wheel`

⇒ **两者合起来说明：加速器那条路是通的（F48/F49 已证），卡住的只有 boot 的依赖解析。**

---

## 2. 为什么这值得优先修

⭐ **我们已有一条"算力换分"的实测证据**：`56883490 = 24.53` 与 `56813776 = 22.48` 是**同一个内核**，
**唯一改动是加速器** ⇒ **换到 Pro 6000 直接 +2.05**。⇒ **这个 agent 是算力受限的**，
所以"让它跑在 Pro 6000 上"是**已被验证会加分**的方向，而不是猜测。

当前榜单（`arc-prize-2026-arc-agi-3-publicleaderboard-2026-10-07T03:03:44.csv`，3900 队）：

| | |
|---|---|
| 我们 | **rank 838 / 24.53 / 6 次提交**（78.5 百分位） |
| 榜首 Tufa Labs | **55.89**（155 次提交） |
| 中位数 | 0.675 |

⇒ **空间 24.53 → 55.89 = +31.36（2.28×）**，而我们对 ARC 的投入只有 6 次提交。
**对照 RSNA：0.944 已顶到公开 notebook 天花板，两个方向都按证据关闭。**
⇒ **剩余价值在 ARC 这边。**

---

## 3. 修法（按代价排序，尚未执行）

1. **先做（零风险、秒级）**：在 boot 最前面加**版本断言** —— 比 `python -V` 与所需轮子的 `cpXY` 标签，
   不匹配就**立刻响亮退出**。它不赚分，但把"4 秒死 + 6.75 小时排队"变成"0 秒死 + 一句可读的话"，
   而且**每次调试迭代都省一次排队**。F52 已推荐。
2. **可能的真修**：那个 `pip install --no-index --no-deps --target /tmp/zst <cp312 whl>` 的轮子**来自数据集**。
   检查同一数据集里是否有 **cp313** 轮子；或确认镜像里**已带** `zstandard`（若已带，这一步可以跳过）。
   ⚠️ **未验证** —— 需要先看那条 `pip` 命令指向的确切文件名。
3. **备选**：换一个 Python 3.12 的运行环境来跑这个 clone（但那样大概率就拿不到 Pro 6000，回到死法一）。

⚠️ **不要把 F52/F53 记成"Pro 6000 路线不可行"**：硬件拿到了、断言过了，死因是纯依赖解析。

---

## 4. 复现

```bash
kaggle kernels logs ppxl16/arc-agi-3-duck-18-1gc     # 拿到 Pro 6000 后死在 unpack_sglang
kaggle kernels logs ppxl16/arc-duck18-live1          # wrong accelerator, expected RTX PRO 6000
```
产物：`state/arc_clone_result.json`、`state/klog_raw.json`。
