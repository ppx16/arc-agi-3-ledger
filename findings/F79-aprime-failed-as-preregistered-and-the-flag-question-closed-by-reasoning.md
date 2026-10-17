# F79 — 2026-10-13 — A′（NVFP4）按预登记的方式失败；并**逻辑上关掉** F77 的悬案

## 1. A′ 的结果：ERROR，原因正是我预登记的那条

**内核** `ppxl16/arc-agi-3-m2-nvfp4` v1（只把 cell 4 的 `MODEL_DIR` 从 W4A16-int4 换成 NVFP4）。
跑完 **ERROR**，日志逐字：

```
taaf.kaggle: TRUE_SUBMISSION=False
...
  File ..., line 264, in <module>
    assert q.get("quant_method") == "auto-round" and q.get("bits") == 4, \
        "MODEL_DIR must be the Intel/albucino AutoRound INT4 checkpoint"
AssertionError: MODEL_DIR must be the Intel/albucino AutoRound INT4 checkpoint
```

**⇒ notebook 对 `MODEL_DIR` 硬断言「必须是 AutoRound INT4」** ⇒
换量化格式**必须同时改量化启动参数**（同一格里 `--quantization auto-round`、`--load-format safetensors` 等都写死了）
⇒ **不再是单变量**。**A′ 这条设计关闭**（这正是我在推它之前写下的预登记读法：*"跑完第一件事是看 COMPLETE 还是 ERROR；ERROR 本身就是有用的答案"*）。

⚠️ **顺带一条对"目标阶梯"的更正**：F77/STATUS 里把「换被服务的模型」列为 `A′`，
**但这条路在本 notebook 上不是"一个变量"** —— 换模型 ⇒ 必须同时换量化后端 ⇒ **至少两个变量**。
⇒ **如果还想走模型侧，正确做法是先把量化后端参数化，再谈"换模型"**（那本身就是一次更大的改动，需要自己的单变量设计）。

## 2. ⭐ F77 的悬案（`TRUE_SUBMISSION` 在评分复跑里是否为 True）——**逻辑上关掉**

**① 为什么无法直接观测**：`kaggle kernels output` 给的是 **Save 跑**的日志（本次就是，显示 `TRUE_SUBMISSION=False`）；
而**竞赛评分复跑的那份日志拿不到** —— `list_kernel_session_output` 对运行中的批处理内核返回 `files: 0` 且无 log 条目（F77 §7 的负结果）。
⇒ **直接读数这条路不存在。**

**② 但可以从行为反推，而且结论是确定的**：
notebook 的 cell 9 里，两条分支的**产物完全不同**：

```python
if TRUE_SUBMISSION:
    ... _wait_for_gateway(...); bm.games = _competition_games()      # 打 live 竞赛 Arcade
else:
    bm.games = _offline_games(...)                                    # 打离线捆绑环境
    ...
    pd.DataFrame([["1_0","1",True,1]], ...).to_parquet(...)           # 【只写 1 行占位】
```

⇒ **若评分复跑里 `TRUE_SUBMISSION=False`，notebook 会写那个 1 行占位件 ⇒ 分数≈0。**
⇒ **同族几十本笔记本都拿 24–34 ⇒ 评分路径必然走 `True` 分支。**（反证法，无需观测。）

**③ ⇒ 三个推论**：
- **(a)** `TRUE_SUBMISSION` 在评分时**确实是 True**；
- **(b)** 因此 cell 16 里那个 `else:` 分支的 `max_runtime_s_per_game`（v2 的 `25*60` vs v3 的按并发切分）**在评分时都不执行** ⇒ **v2 与 v3 在评分路径上等价**；
- **(c)** 结合 F77 §3f 第 1 条（`cmp_all_cells` 证明**全 23 格只差 2 格**：一处 markdown 标签 + 那一行），
  **⇒ "24.53 vs 同族 29–31"的差距【不可能来自 notebook 源码】**。剩下的只有**运行期/重放**因素。

## 3. 至此，关于那条差距我们已经把"能查的"查完了

| 假设 | 状态 |
|---|---|
| fork 丢了 `model_sources` / `machine_shape` | ⛔ 证伪（我们自己那本 metadata 与作者逐字段相同） |
| v2/v3 那一行时间预算是根因 | ⛔ 证伪（在 `else:` 分支；评分走 `True` 分支 —— 本节 2 反证） |
| 还有别的 cell 差异被漏看 | ⛔ 证伪（全 23 格穷举，只差 2 格） |
| **同族逐次重放的分布**（本族 24–34，原样副本 29–31） | ✅ **唯一还站着的解释** |

**⇒ 战略结论（写死）**：**这条赛道上"找根因"的边际收益已经见底；正确动作是把每天的 1 次提交用满。**
（评分对 live 游戏集重放、逐次随机、平台保留最好；我们开赛约 100 天只交了 9 次。）

## 4. 附带：一个潜在坑与一条读文件规则（工具体检时翻出来的）

`work/` 下有 **6 个旧文件带 UTF-8 BOM**：`duckcells.py` · `ducknb.py` · `probelog.py` ·
`vllm2log.py` · `vllm3log.py` · `vllmlog.py`。
用 `open(p, encoding='utf-8')` 读再 `ast.parse` 会报 `invalid non-printable character U+FEFF`。

⚠️ **那是【我这个检查】的假阳性，不是文件真的坏**：Python 的源码加载器会剥掉开头的 BOM，
所以它们大概照常能跑 —— **但我没有实际执行过去确认**，这点如实写明。

**真正的风险在别处**：任何**程序化读取**这些文件再把内容拼进别处的地方（例如把源码拼进 payload 的构建器）
会把 BOM 当成一个普通字符带进去 ⇒ 正是本项目在 ARC 上踩过的
`SyntaxError: unterminated string literal`（F71–F73）**那一族**。

**⇒ 写死的规则**：**凡是要把文件内容拼进别处的，一律用 `encoding='utf-8-sig'` 读**（它会剥 BOM）。
实测：`work/` 下 49 个脚本里，按 `utf-8` 读无法解析的就是上述 6 个，其余 43 个正常。

## 5. ⚠️ 调度约束（与时间无关，但决定"什么时候推"）

**同族里存在两种 notebook 结构，Save 跑的时长差两个数量级：**

| 结构 | 行为 | Save 跑时长 | 实例 |
|---|---|---|---|
| **纯打包器** | 只打包，日志写 `V3 packaging complete; competition rerun executes the full solver.` | **~4 分钟** | `heliosli/try-merging-it…`（我们的 `arc-agi-3-helio-merge`） |
| **带离线跑** | 非提交跑**去打离线捆绑环境**（cell 9 的 `else:` 分支） | **~9 小时** | `dfranzen/arc-agi-3-milestone-2-solution`（我们的 `…m2-franzen-verbatim`） |

**机制**：franzen 那本在 `else` 里把 `soft_end` 设为 `target.max_runtime_s − min(600, budget/2)`，
而 `target.max_runtime_s == 32400`（notebook 自己有断言）⇒ **Save 跑会玩满 ~8h50m**。

**⇒ 两条推论**：
1. **内核版本要等 Save 跑 COMPLETE 才能提交**（`CreateCodeSubmission` 的前置条件）
   ⇒ **有截止日的提交必须【当天早推】**，否则会撞上 ~9 小时的等待。2026-10-13 我们 09:30Z 推的 franzen，
   最早 ~18:30Z 才可用 —— 那还在 00:00Z 的额度重置之前，安全，但**再晚几小时就来不及了**。
2. **想缩短等待，就 fork 那种"纯打包器"结构的同族 notebook**（例如 heliosli 那本，4 分钟即可提交状态）。
   ⇒ 这给了一条**真正的调度杠杆**：**手里常备一本已 COMPLETE 的打包器版本**，每天那次额度就不会被 Save 跑卡住。

### 由此得到的每日决策（写死，避免临场犹豫）

每天那 1 次额度，按**这个顺序**选目标（"平台保留最好"⇒ 选错也不损失，但选对能多一次更好的抽样）：

1. **`arc-agi-3-m2-franzen-verbatim`**（作者 34.30，本族最高）—— **前提是它已 COMPLETE**；
2. 否则 **`arc-agi-3-helio-merge`**（作者 32.60）—— **它 2026-10-13 就已经 COMPLETE**，
   所以它是一条**随时可用的兜底**，保证"想交的时候手里一定有可交的东西"。
   ⚠️ **同一版本再交一次是允许的**（每次提交是独立的复跑），而这在"逐次重放"的评分下就是**又一次抽样**。

⇒ **净效果**：**从今天起，每天的额度都不会因为"Save 跑还没跑完"而落空。**
