# F78 — 2026-10-13 — 两枪同时上膛；以及"推送回执丢失 ≠ 推送失败"的第二次实测

## 1. 现在有两条 ARC 腿在跑（并行上限 2，正好用满）

| 内核 | 来源 | 那本的**真实公榜分** | 状态 |
|---|---|---|---|
| `ppxl16/arc-agi-3-m2-franzen-verbatim` | `dfranzen/arc-agi-3-milestone-2-solution` 的**逐字节 fork**（作者当前版） | **34.30**（家族 29–34） | RUNNING |
| `ppxl16/arc-agi-3-helio-merge` | **`heliosli/try-merging-it-you-might-get-lucky-and-win-gold`** 的逐字节 fork | **32.60** | RUNNING |

两者都继承同一套环境（`NvidiaRtxPro6000`、`57e612b4…` 镜像、同两个 dataset、**同两个 `model_sources`**），
都**没有空 slug**（F77 §1 的普查读数 + 本轮的 metadata 实拉）。

**为什么值得同时推两本**：ARC 是「对 live 游戏集重放、逐次随机、平台保留最好」，
所以**同族多次抽样本身就是策略**（F77 §3e/§3f）。而且**每天只有 1 次提交**，
两腿并行只是为了**手里随时有一本可提交的产物**，不是一次交两枪。

## 2. ⚠️ 推送回执丢失了一次，但推送**成功了** —— 第二次实测，已核实

`python work/push_kernel.py kernels/kernel-arc-agi-3-helio-merge` 的输出是：

```
Expecting value: line 1 column 1 (char 0)
PUSH FAILED (rc=1) -- no 'successfully pushed' in output
```

**但 `kaggle kernels status ppxl16/arc-agi-3-helio-merge` 立刻回 `KernelWorkerStatus.RUNNING`。**

⇒ **空响应（`Expecting value: line 1 column 1 (char 0)`）就是本项目早已记过的传输故障**，
**不是推送失败**。（`submit_kernel.py` 里早已为此写了"传输故障 ⇒ 去对账，不要重推"的分支；
`push_kernel.py` **还没有**这一分支，所以它把成功报成了失败。）

**核实方式（不信工具自己的打印）**：`kaggle kernels pull` 把服务端那份拉回来，
逐字段比 metadata、逐字节比 notebook —— **7/7 字段 OK、598837 B 完全一致** ⇒ **推送确实落地且内容正确。**

⚠️ **待修**：`fork`/`push` 工具都要有"回执为空 ⇒ 用 `kernels status` + 回读来判定"的分支，
**否则下一次我会因为一条假失败而重推，浪费一个 GPU 槽**。

## 3. 下一轮的动作

1. 两腿任一 COMPLETE ⇒ **读它的日志**（找 `taaf.kaggle: TRUE_SUBMISSION=` 与 `benchmark.solver:`）—— 这是 F77 §3f 第 2 条那个唯一未排除的机械解释。
2. 用掉**今天那 1 次 ARC 提交**（未用；最近一次是 10-12 的 `57106427` = 19.83）。
3. 之后**每天用满 1 次**：平台保留最好，而我们开赛约 100 天只交了 8 次。
