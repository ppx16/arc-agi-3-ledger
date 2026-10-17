# F77 — 2026-10-13 — 🎯 公开面普查命中：作者当前版 **34.30**，我们只抽到 24.53；**我提的两个"根因"都被自己证伪**，剩下的是分布问题

> **一句话**：作者的 `arc-agi-3-milestone-2-solution`（我们抄的对象）历史最高 **34.30**，同族约 20 本 fork 落在 **27–32**，而我们那一枪只有 **24.53**。
> ⇒ **这是一个 24–34 的分布，我们抽到了低端**；铜线 30.12。
> **行动**：把作者当前版逐字节 fork（`ppxl16/arc-agi-3-m2-franzen-verbatim` v1，RUNNING），**并且每天用满那 1 次提交**——平台保留最好。
>
> **⚠️ 本文件保留了两次被证伪的假设（"环境字段"与"时间预算那一行"），因为"理由错了但结论蒙对"是必须留下证据的事故。**

## 1. 怎么发现的（把 RSNA 那个真正奏效的打法搬到 ARC）

`work/census.py`（新，零 GPU、零提交）：先 `GET https://www.kaggle.com/competitions` 拿 XSRF cookie，
再 `POST https://www.kaggle.com/api/i/kernels.KernelsService/ListKernels`，body 里
`kernelFilterCriteria.listRequest.competitionId = 133468`、`sortBy` 三种各翻页，
读每条的 **`bestPublicScore`** —— **每个公开笔记本真实拿到过的最高公榜分**。

⚠️ 这条路 `kaggle` SDK 走不通：它的响应模型**没有 `bestPublicScore` 字段**，会静默丢掉（RSNA 侧记在 FACTS C142）。

**读数：1349 个公开笔记本，564 个有真实分。**

| notebook | 真实分 | 票 |
|---|---|---|
| **`dfranzen/arc-agi-3-milestone-2-solution`** | **34.30** | 810 |
| `jingshuifu/arc3-m2-solution` | 33.22 | 61 |
| `heliosli/try-merging-it-you-might-get-lucky-and-win-gold` | 32.60 | 73 |
| `greenalgeria/arc-agi-3-milestone-green-02` | 32.38 | 0 |
| `sujanmajhisuzan/arc-agi-3-m2-top-submission` | 31.93 | 85 |
| `zhangyues0000/arc-agi-3-m2-franzen-fork` | 31.76 | 12 |
| `shiiin9/affectify-arc-31-54-in-a-single-sub` | 31.54 | 71 |
| …另有约 20 本 franzen 的 fork 落在 27–32… | | |

## 2. 关键事实：那一本**正是我们抄的对象**

我们的 `56883490`（**24.53**）是 `dfranzen/arc-agi-3-milestone-2-solution` 的副本。
**⇒ 同一个配方，作者手上 34.30，我们手上 24.53，差 9.77。** 而铜牌线是 **30.12**（rank 423 / N=4234）
⇒ **这个配方本身就够铜牌，是我们的副本弱了。**

## 3. ⭐⭐⭐ 根因：【一行代码】的时间预算 —— 不是环境，不是噪声

**我先提出了"fork 丢了环境字段"的假设，然后把它【证伪】了，最后找到了真正的原因。三步都要留下。**

### 3a. 证伪：我们那本的环境与作者原版**逐字段相同**

`kaggle kernels pull ppxl16/arc-agi-3-milestone-2-solution -m`（**我们的** 24.53 那本）：

```
machine_shape  : "NvidiaRtxPro6000"          <- 与作者相同
docker_image   : ...python@sha256:57e612b4...  <- 与作者相同
dataset_sources: ["dfranzen/pennyroyal-v253", "dfranzen/taaf-kaggle-source-bundle-copy"]
model_sources  : ["dfranzen/albucino-qwen3-8-flash-next-drafter/Transformers/default/1",
                  "dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/Transformers/default/1"]
```

⇒ **两个 `model_sources` 都在，`NvidiaRtxPro6000` 也在。** "fork 丢了模型挂载"**不成立**。

### 3b. 真正的差别：我们的副本是【旧版本 v2】

两份 notebook 的**文件尺寸完全相同（都是 569095 字节）**，但 sha256 不同（作者 `88a379f1…` / 我们 `71f18dfe…`）。
线性字节 diff（⚠️ **不要用 `difflib.SequenceMatcher`——A190 已记过它在 500 KB 上是 O(n²)，我这次又踩了一次并把命令跑挂**）
把差异定位到了正文第一句：

```
作者 : "### About this notebook\n\n**Update (v3):** This version reruns the open-sourced submission (v1) ...
我们 : "# About this notebook\n\n**Update (v2):** This version reruns the open-sourced submission ...
```

**⇒ 我们 10-06 提交的是 v2；作者之后发布了 v3，而 `bestPublicScore` 记的是他整个提交历史上的最高分（34.30）。**

### 3c. v3 到底改了什么：**一格，一行** —— 但这一行**在评分跑里不生效**

`work/cmp_cells.py` 逐代码格比对：**11 个代码格里 10 个逐字节相同**，只有 **cell 16** 不同，而且只差一行：

```python
v3（作者当前） : bm.solver.max_runtime_s_per_game = 532*60 * bm.solver.concurrency // 110
v2（我们的副本）: bm.solver.max_runtime_s_per_game = 25*60   #532*60 * bm.solver.concurrency // 110
```

### 3d. ⛔ **我先把这一行宣布成根因，随后自己把它证伪了**

**cell 16 有两个分支，而差异那行在 `else:`（非提交）分支里**。逐字打出两版的这一格（28 行，只差 line 20）：

```python
if TRUE_SUBMISSION:            # overrides for contest run   <-- 评分复跑走这里
    bm.solver.save_request_logs = False
    bm.n_passes = 1
    if USE_PRIORITY_SCHEDULING:
        bm.solver.concurrency = 120          # game count should be 110
        bm.solver.max_runtime_s_per_game = 532*60        # <-- v2 与 v3 【完全相同】
else:                          # 非提交跑（push 的 Save 跑）
    if USE_PRIORITY_SCHEDULING:
        bm.solver.concurrency = (25 - len(demo_excluded_games)) * bm.n_passes
        bm.solver.max_runtime_s_per_game = 532*60 * bm.solver.concurrency // 110   # v3
        #                                = 25*60                                     # v2  <-- 唯一的差异
```

而 `TRUE_SUBMISSION = os.environ.get("KAGGLE_IS_COMPETITION_RERUN", ...) in {"1","true"}` —— **notebook 自己的注释写着"True only inside a real competition rerun"**。

**⇒ 在真正的竞赛评分复跑里，v2 与 v3 的行为【完全一致】（都是 `n_passes=1`、`concurrency=120`、`max_runtime_s_per_game=532*60`）。**
**⇒ "时间预算这一行是 24.53 vs 34.30 的根因"【被证伪】。**

**⚠️⚠️ 教训（写死的）**：**发现一处差异 ≠ 找到根因。必须再问一句"这一行在【被评分的那个路径】上会执行吗"。**
我上一版把 `34.30` 与 `25*60 → 532*60*concurrency//110` 的"方向一致"当成了证明 —— 那是**叙事上的自洽，不是路径上的可达**。
与 A186/A190/C151 同族：**看起来对，不等于在正确的路径上对。**

### 3e. 那么 34.30 从哪来？—— 三个仍然活的可能，按可信度排

1. **⭐ 同族配方的逐次重放方差（最可能）**：普查里 **约 20 本 franzen fork 落在 27–32**，而我们只抽到 **24.53**。
   ⇒ **这个家族的分数区间大致是 24–34，我们那一枪偏低。**
   （F50 早就记过："ARC 的评分复跑跑的是 live 比赛 Arcade 的游戏，每次面对的题目集合可能不同"，且"两者我无法从现有数据区分"。）
2. **`bestPublicScore` 是【整个 kernel 历史】的最高分**，可能来自 **v1**（markdown 里说的 *"the open-sourced submission (v1)"*），
   而作者后来把它重跑成 v2/v3 —— 那么 v1 与 v2/v3 的差别可能不止那一行。
3. 别的环境/时机差异（未证实）。

**⇒ 无论哪一条成立，行动是同一个：把当前版本跑出来并提交，且【每天用满那次额度】——
因为平台保留最好，而在一个 24–34 的分布上反复抽样，命中铜线 30.12 完全可能。**

### 3f. ⭐⭐ 最硬的一条证据：**原样副本的区间是 29–31，而我们在区间之外**

普查在 **26.0–34.5** 这段里找到 **36 本**笔记本，其中**好几本就是 `arc-agi-3-milestone-2-solution` 的原样副本**（标题都一样）：

| notebook | 真实分 | 票 | 更新 |
|---|---|---|---|
| `dfranzen/arc-agi-3-milestone-2-solution`（作者本尊） | **34.30** | 810 | 10-03 |
| `jingshuifu/arc3-m2-solution` | 33.22 | 61 | 10-11 |
| `heliosli/try-merging-it-you-might-get-lucky-and-win-gold` | 32.60 | 73 | 10-13 |
| `sujanmajhisuzan/arc-agi-3-m2-top-submission` | 31.93 | 85 | 10-12 |
| `skarin/arc-agi-3-27-80-lb-100-trajectory-audit` | 31.66 | 54 | **10-04** |
| `jinhaozhu2/arc-agi-3-milestone-2-solution`（**原样副本**） | 31.40 | 2 | 10-08 |
| `sigeward/arc-agi-3-milestone-2-solution`（**原样副本**） | 31.27 | 11 | **10-04** |
| `amatlas/dfranzen-fork-d-prime` | 30.82 | 10 | 10-05 |
| `ouyangruize/arc-agi-3-milestone-2-solution`（**原样副本**） | 30.74 | 0 | 10-13 |
| `dhruvb2028/arc-agi-3-milestone-2-solution`（**原样副本**） | 29.69 | 1 | 10-07 |
| `feili6458/arc-agi-3-milestone-2-solution`（**原样副本**） | 29.31 | 1 | 10-06 |
| **我们 `ppxl16/arc-agi-3-milestone-2-solution`** | **24.53 / 22.48** | — | 10-06 / 10-04 |

**⇒ 原样副本的区间是 29.31–31.40；同一时期（10-04）别人拿 31.27/31.66，我们拿 22.48/24.53。**
**⇒ 这不是"家族的正常方差"，而是我们的运行【系统性偏低】。** 这一条比我前面两个被证伪的假设都硬，而且它**重新把"我们的运行与别人的运行有实质差别"带回桌面** ——
只是差别**不在 metadata（3a 已证伪）**、**不在 cell 16 那一行（3d 已证伪）**。

**⇒ 下一步该查的方向（按可查性排序）**：
1. ~~作者原版与我们的副本还有别的差异~~ —— **已查完并排除**：`work/cmp_all_cells.py` 把**全部 23 格**（含 markdown 与 outputs）逐格比过，
   **只有 2 格不同**：**cell 0**（正文的 `Update (v2)` vs `Update (v3)` 标签）与 **cell 16**（3d 已证在评分路径上不生效的那一行）。
   `nb metadata` 完全相同；**source-only digest 不同只由这两处造成**。⇒ **源码层面没有隐藏差异。**
2. ⭐ **`TRUE_SUBMISSION` 在评分复跑里到底是不是 True —— 这是唯一还没被排除的机械解释，而且【正在跑的那一枪会自己打印出来】。**
   notebook 在第 4 格里就 `print(f"taaf.kaggle: TRUE_SUBMISSION={TRUE_SUBMISSION}")`，第 16 格还会 `print('benchmark.solver:', bm.solver)`。
   ⇒ **跑完 COMPLETE 后，第一件事就是读日志找这两行。**
   · 若 **True** ⇒ v2/v3 等价成立 ⇒ 差距只能是**逐次重放的随机性**（那就走"每天抽满"）；
   · 若 **False** ⇒ v2 的 `25*60` 生效 ⇒ **正好解释 22–24 vs 29–31**，那就等于 3d 的结论**在评分路径上其实成立**（我证伪得太早：我证伪的是"v3 更好"，而不是"那一行在评分时生效"）。
3. 别的（镜像/模型挂载时机、`is_private`）。

## 4. 已做的处置

按"**整份继承上游 metadata、只覆盖 `id/title/code_file/is_private`，并逐字段断言其余未变**"（C139/A183 的规矩）
fork 了作者**当前（v3）**的 notebook：

| | |
|---|---|
| 内核 | **`ppxl16/arc-agi-3-m2-franzen-verbatim` v1**（已推，RUNNING） |
| notebook | 569095 → **569053 B**，sha256 `2786fc872071e497…`；**唯一改动**是两个非 ASCII 字符（`—`、`’`）换成 ASCII —— 本机 `kaggle kernels push` 按 GBK 读代码文件 |
| 继承并**已回读核验** | `dataset_sources` / `model_sources` / `docker_image` / `machine_shape` / `enable_*` **逐字段与本地一致**；notebook 字节服务端 == 本地 |
| 构建器 | `work/fork_kernel.py`（从 RSNA 侧复用） |

**预注册的读法**（今天那次 ARC 提交额度未用，跑完 COMPLETE 即提交）。
⚠️ **注意：因为 v2/v3 在评分路径上等价，这一枪【不再是对任何假设的检验】——它是同一个分布的又一次抽样。**

| 结果 | 判读 | 下一步 |
|---|---|---|
| **≥30.12** | 抽到高端 ⇒ **进铜牌区**（rank 1260 → ≤423） | 采纳；继续每天抽，并同时去查 **v1**（作者 markdown 里说的 *"open-sourced submission (v1)"*，34.30 有可能来自它） |
| **27–30** | 接近但没过线 | 采纳（平台保最好），继续每天抽；同时把同族高分 fork（31–33 那几本）也逐一分诊，看它们的差异在哪 |
| **≈24** | 又是低端抽样 | 仍然采纳；这一枪的价值在于**再确认一次分布**，然后决定是否换配方（不再纠结 v2/v3） |
| **ERROR** | 读日志 | 最可能是那个 `57e612b4…` BYOD 镜像或两个模型挂载的可用性 |

**⚠️ 由此得到一条更重要的战略结论**：**这个赛道上"找根因"的收益低于"多抽几次"**。
因为 (i) 评分是对 live 游戏集重放、逐次随机；(ii) 平台保留最好；(iii) 每天有 1 次额度而到今天为止我们**用掉的极少**（8 次提交 vs 开赛约 100 天）。
⇒ **把每天的额度用满，比再花一轮去找一个可能不存在的"那一行"更值。**

## 5. 附带纠正（我的第二次同类错误）

我在 `work/recon.py` 第一版里用 `'ppxl' in team.lower()` 找自己 —— **找不到**，因为队名是 **`p pxl16`**，
中间的**空格**让 `ppxl` 不是子串。**这正是 RSNA 侧 FACTS A184 记录的那类错误（用子串匹配显示标签）**，
我在另一个竞赛里又犯了一次。改为按 `TeamMemberUserNames` 含 `ppxl16` 定位后，真实读数：
**rank 1260 / 24.53 / 铜牌需 30.12（差 +5.59）**。
另：`kaggle competitions submissions --csv` 会在 header **之前**打一行 `Warning:`，直接 `DictReader` 会把警告当表头、每行都读成空 —— recon 里已改成先跳到 `ref,` 那一行。

## 6. 方法论（值得复用）

**"同名同尺寸 ≠ 同一版本。"** 我们的副本与作者当前版**都是 569095 字节**，只看尺寸会以为一致；
**只有 sha256 + 逐格比对**才能发现 (a) 是 v2 不是 v3，(b) 差别只有一行（而且那一行在评分路径上不生效）。
⇒ 与 RSNA 侧 C145（"尺寸相同只能说明同架构，同权重必须靠哈希"）是**同一条规矩的第四次应用**，
而这次多了一层：**同一份文件的不同【版本】也要靠哈希去分**。

## 7. 工具与一条负结果

- `work/census.py` —— 公开笔记本真实分普查（本文件 §1 的来源）。
- `work/cmp_cells.py` / `work/cmp_all_cells.py` / `work/byte_diff.py` —— 逐格与逐字节比对
  （⚠️ **都不要用 `difflib.SequenceMatcher`**：A190 已记过它在 500 KB 上是 O(n²)，本次又踩了一次并把命令跑挂 10 分钟）。
- `work/live_log.py`（新）—— 想读**运行中**内核的 stdout，走 `kernels.kernels_api_client` 的
  `get_kernel_session_status` / `list_kernel_session_output`（请求字段是 **`user_name` + `kernel_slug`**，不是 `owner_slug`）。
  **⚠️ 负结果：对一个 RUNNING 的批处理内核，它返回 `session status: RUNNING` 但 `files: 0`、无 `log` 条目**
  ⇒ **运行中的日志拿不到，`TRUE_SUBMISSION=` 只能等跑完再读。** 该脚本仍可用于查会话状态。
- ⚠️ 该脚本第一次跑挂在 `api.authenticate()` 的 **SSL EOF**（A189 那个已知的传输层故障）——
  **认证调用本身也要重试**，否则"读不到日志"会被误读成"日志是空的"。
