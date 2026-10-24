# RECON — ARC Prize 2026 / ARC-AGI-3：公开面 ≥30 分笔记本逐本 diff

写于 2026-10-24（Asia/Shanghai）。只读侦察：**没有提交任何 Kaggle 提交，没有改内核，没有写 `arc-agi-3-ledger/` 或 `rsna-knee/`。**
本目录（`arc/recon/`）是唯一写入点。

---

## 0. 一句话结论

**27 本公开笔记本里，20 本的 498 KB harness patch 与我们的逐字节同源（归一化排版后 sha 完全相同；另有 2 本把 patch 内嵌成字符串，
文件集与作者声明相同），唯一被广泛改动的“评分路径”部件是调度优先级（dprime/D′ 家族，9 本，正是 Lead 在 F92 试过并 0.00 的那类）；
除此之外公开面有 5 个我们还没试过的改动，其中价值最高的是两个“防 0.00”而非“提分”的改动：
(1) 用**网关可达性**兜底 `TRUE_SUBMISSION` 判定（weitaoguo，且其记录与我们 10-22 那次 0.00 同日同因），
(2) **启动保活**（mayankraaz：/health 等待 + 定期免费 RESET，防网关 15 分钟无动作判死）。
真正的“新能力”里最干净可移植的是 **solved-level memory**（lalalia9/mayankraaz，来自 rellik13/sirikilohit 的 M85 写-up，作者自称 +2.8）。
`ARC3_MEMORY_SECTIONS`：**27 本中没有任何一本开它**（25 本显式 `'off'`，2 本不用 setup_env），F93 的前提“可能有人偷偷开着”不成立。

---

## 1. 方法与可复现物

| 步 | 做什么 | 产物 |
|---|---|---|
| 1 | 用 Lead 的 census 仪器（web endpoint，带 `bestPublicScore`，SDK 会丢这个字段）重扫竞赛全部公开 notebook | `census_fresh.py` → `public_scores_fresh.json`（1,532 本，619 本有真分，**27 本 ≥30**） |
| 2 | `kaggle kernels pull <ref> -p nb/<slug> -m`，拿 ipynb + kernel-metadata | `pull_all.py` → `nb/<slug>/`（27/27 成功；旧 census 里的 `greenalgeria/…green-02` 已 404，最新的同分笔记本是 `up-arc-3`；`jinhaozhu2/…` 403 私有/删除） |
| 3 | 结构化抽取：cell 清单、patch 指纹、`setup_env`（AST 解析+常量求值）、`os.environ` 赋值、`bm.*` 配置、kernel-metadata | `analyze.py` → `analysis/*.json`、`analysis/_summary.json` |
| 4 | 逐本 diff：typography 归一化后按 cell 对齐；patch 按文件拆开做“新增行集合”差；env 键级 diff | `summarize.py` → `summary_report.txt`；`deepdive.py`；`factsheet.py` → `factsheets.txt` |
| 5 | 特殊形态（patch 藏在字符串里 / 没有 patch cell）单独处理 | `special.py` → `special.log` |
| 6 | 跨本 union：任何 ≥30 笔记本设置、而我们 baseline 没设（或设了别的值）的 env 键 | `compare.py` → `compare.log`、`extracted/` |
| 7 | F93 专项：`ARC3_MEMORY_SECTIONS` 全表 + 每个新键在我们的 patch 里是否有读取方 | `f93.py` → `f93.log` |

**关键口径/陷阱（都已在代码里处理）**：
- `bestPublicScore` 是 **max-over-draws**（F81）⇒ 分数不是 agent 强度，本报告只做“它改了什么”的判断。
- `kaggle kernels pull` 拉的是**最新版本**，不一定等于产生 `bestPublicScore` 的那一版。`census.updated` = 版本创建日期，已放进表里供判断。
- 我们 kernel 的 patch 与 dfranzen 原版的差别是 **11 个排版字符**（em-dash/弯引号）；不做归一化会把每一本都误报成“patch 被改过”。
  归一化后：`body_sha_norm = 09936e0be261a77e`，body 长度 498,757，16 个文件。
- 有 3 本不能靠 `%%writefile` 首行识别 patch（laimer 把 patch 存成 Python 字符串、prvsiyan 把多个版本压成 inert 文本、leoprovorov 根本没有 harness patch）。

---

## 2. 一览表：27 本 ≥30 分笔记本

“Δ vs us” 一列是**相对我们当前内核**（`ppxl16/arc-agi-3-m2-franzen-verbatim` v1）的实质差异。
分数 = 2026-10-24 重扫的 bestPublicScore。粗体前缀是新机制标记。

| # | notebook | 分 | votes | 版本 | cells | patch 指纹 | Δ vs us（实质） | 有我们没试过的？ |
|---|---|---|---|---|---|---|---|---|
| 1 | `dfranzen/arc-agi-3-milestone-2-solution` | 34.30 | 1092 | 10-03 | 23 | SAME | 无（我们就是它的 fork） | 基线 |
| 2 | `tantan0327/arc3-franzen-dprime` | 33.55 | 62 | 10-22 | 24 | SAME | +1 cell：dprime 优先级（8,366 chars，`ARC3_PRIORITY_FORM='dprime'`，并把未开局游戏也按公式定价） | 否 —— Lead 已试，F92 = 0.00 |
| 3 | `jingshuifu/arc3-m2-solution` | 33.22 | 132 | 10-11 | 23 | SAME | 只有离线 knob：`n_passes=1`、demo `max_runtime=600s` | 否（不进入评分路径） |
| 4 | `weitaoguo/affectify-arc-dfranzen-form-d1` | 32.61 | 43 | 10-23 | 26 | SAME | +D′ install_d（11,050 chars）+ **网关可达性兜底 TRUE_SUBMISSION** | **是**：gateway probe |
| 5 | `heliosli/try-merging-it-…-win-gold` | 32.60 | 119 | 10-23 | 24 | SAME | 与 tantan 同一个 dprime cell（8,366，逐字相同） | 否（dprime 类） |
| 6 | `jingshuifu/arc3-m2-solution-v3` | 32.60 | 40 | 10-13 | 23 | SAME | **`ARC3_PRIORITY_PACE: '0'→'1'`**（一行 knob，其余全同） | 是（一行 knob，证据弱） |
| 7 | `dennis6886/arc3-d-prime-public-base` | 32.59 | 41 | 10-19 | 26 | SAME | +D′ install_d；**额外 dataset `destinyfire1/arc3-cpython312-runtime`（7 段 tar，sha 校验）** | 是（py3.12 runtime，属基建） |
| 8 | `greenalgeria/up-arc-3` | 32.38 | 10 | 10-20 | 21 | SAME | **launcher：`MEMFRAC 0.96→0.99`、`SPEC_STEPS 3→4`** | **是**（吞吐 knob，最便宜） |
| 9 | `amatlas/dfranzen-fork-d-prime` | 32.12 | 27 | 10-05 | 24 | SAME | +D′ 移植（17,931 chars，来自 shiiin9） | 否（dprime 类） |
| 10 | `sujanmajhisuzan/arc-agi-3-m2-top-submission` | 31.93 | 87 | 10-13 | 23 | **DIFF** 616,169 / 28 files | +CONFIGURATION.md（483 行整本 knob 手册）+`world_model.py`/tests +tools +第二份 `und-changes.patch`（base85+gzip，UND 子系统）+Apex 优先级注入（15,328 chars cell）+预写 submission.parquet+try/finally | **是**（重：world-model / UND / apex / 输出契约） |
| 11 | `habanwer/arcaid3-lexicon-view-dfranzen-m2` | 31.90 | 37 | 10-17 | 27 | SAME | **+ARCAID3 lexicon 107,386 chars cell**：`current_frame.code/.objects/.native/.changes_since()/.rules`，并改写“frame 只暴露 …”的 prompt 锚点 | **是**（改变模型“看见什么”） |
| 12 | `zhangyues0000/arc-agi-3-m2-franzen-fork` | 31.76 | 23 | 10-17 | 25 | SAME | **+R3 game-over ledger**（7.5 KB，monkeypatch：把本关每次死亡的前缀账本钉进 user message）+mount resolver | **是**（死亡账本跨轮可见） |
| 13 | `leoprovorov/fable-astra-play-arc-3-handbook-harness` | 31.73 | 76 | 10-15 | 44 | 无 patch cell | 是**手册 notebook**（自己的 dataset，无 GPU、无 harness patch）：Fable layer 24 KB 核心 +15.7 KB harness patch（`ARC3_FABLE_LAYER`，指标注记/等级日志/步数预算） | 名义上是；作者自述“未测出增益” |
| 14 | `skarin/arc-agi-3-27-80-lb-100-trajectory-audit` | 31.66 | 55 | 10-04 | 37 | SAME | 14 个新增 cell 全是**审计/可视化**（100 条轨迹分析），无 agent 改动 | 否 |
| 15 | `lwq255/arc3-dfranzen-m2-guarded` | 31.65 | 0 | 10-23 | 26 | SAME | capability guard：只有 `TRUE_SUBMISSION 且 Blackwell` 才跑重活；交互跑秒出占位 parquet | 否（且会放大 env-flag 误判风险） |
| 16 | `shiiin9/affectify-arc-31-54-in-a-single-sub` | 31.54 | 74 | 10-04 | 26 | SAME | +D′ install_d（11,050，D′ 公式的公开源头） | 否（dprime 类） |
| 17 | `lalalia9/arc3-franzen-v19` | 31.46 | 17 | 10-20 | 24 | SAME | **只有 SOLVED-LEVEL MEMORY（9,960 chars）**，其余逐字 = dfranzen | **是**（最干净的新机制） |
| 18 | `sigeward/arc-agi-3-milestone-2-solution` | 31.27 | 15 | 10-04 | 25 | SAME | 可靠性硬化：启动 12→7 min、输入存在性检查、spec fallback、**submission 也留 120s teardown 的 soft_end**、provenance json | 是（基建/防 0.00） |
| 19 | `manwithacat/digital-mouse-qwen-genome-baseline` | 31.07 | 3 | 10-03 | 25 | SAME | py3.12 runtime（dataset 里的 `python312.tar.gz.bin`）、GPU 断言、离线只跑 3 局 | 基建 |
| 20 | `yongjiehishi/arc3-duck-lab-t06` | 31.05 | 0 | 10-20 | 25 | SAME | +D′ 17,931 + mount resolver | 否（dprime 类） |
| 21 | `yukailiu/arc-agi-3-champion-solution` | 30.80 | 44 | 10-20 | 23 | SAME | 路径解析 + **libcuda 强制指向宿主驱动** + 清空 sitecustomize + 离线 knob | 基建（对应我们 F52–F74 的 numpy/sitecustomize 史） |
| 22 | `spark328/arc-prize-2026-arc-agi-3-franzen-v1` | 30.75 | 3 | 10-09 | 23 | SAME | 仅离线 knob（n_passes=1 / demo 25 min） | 否 |
| 23 | `ouyangruize/arc-agi-3-milestone-2-solution` | 30.74 | 18 | 10-24 | 26 | **DIFF** 499,294（+537，net +17 行） | **动画感知的 no-op/stale 守卫**（transient animation 算“真变化”，batch-noop 不误杀）+7 个 env knob（yield-resume 面）+D′ | **是**（最外科手术的 patch 级改动） |
| 24 | `prvsiyan/arc-agi-3-stock-taaf-action7-shadow` | 30.65 | 10 | 10-19 | 119 | 内嵌（16 files，作者称未改） | 巨型工作台：A/B arm（baseline vs adaptive）、V15/V17 基建（输入检查、9h 看门狗、checked export、commit gate、per-stream timing） | 部分（方法是可借的：**A/B 同抽**） |
| 25 | `laimerbotrolenk/candidate-g-lb-score-30-58` | 30.58 | 2 | 10-22 | 32 | 内嵌字符串（16 files） | patch/setup_env 与我们**完全相同**，但：docker_image 换 py3.12 镜像、`HISTORY_ASSISTANT_TURNS=0`、**“adaptive” profile**（观察推导已解等级证据、跨 trim 的 JSON memory、部件级点击点、UCS/A* 搜索、精确 toggle、计划逐步校验） | **是**（agent 能力套件；作者自述未上分测过） |
| 26 | `guangyuanwangkaggle/arc-agi-3solution-basedondaniel-franzen` | 30.46 | 0 | 10-24 | 30 | **DIFF** 512,157（net +213 行） | **`recall()`/`recall_frame` 帧记忆**（REPL 内召回 + 每动作存 settled/animation 帧，cap 256）+**`_assert_analyzer_endpoint()` 起不来就大声失败**+D′ | **是**（帧召回 + fail-loud 健康检查） |
| 27 | `mayankraaz/arc-agi-3-neural-bfs-episodic-solver` | 30.01 | 11 | 10-22 | 27 | SAME | **SOLVED-LEVEL MEMORY + STARTUP KEEPALIVE（/health 等待 + 每 8 分钟一次免费 RESET）** + animation 空 schema 修补 + D′ | **是**（保活是最直接防 0.00） |

> 表中 #23 `ouyangruize` 与 #26 `guangyuanwang` 的 patch 是 **我们 patch 的严格超集**（文件清单相同、只多行），
> 这两本 + `sujan` 是公开面仅有的三个“改了 harness 代码”的；其余全部是“同 patch + 额外 cell / knob”。

### 2.1 patch 指纹的精确结论

- `body_sha_norm` 与我们相同（`09936e0be261a77e`）、文件清单相同（16 个）：**20 本可逐字节验证**；
  另有 `laimerbotrolenk` / `prvsiyan` 两本把 patch 存成内嵌字符串（无法直接比 sha），但其 16 文件清单与作者声明都与我们相同（prvsiyan 的 setup_env 我已单独解析：47 键与我们逐键相同）。
- 不同的只有：
  - `sujan`：616,169 chars / **28 files**（+12 个新文件；本报告 §5 有完整清单与提取物）。
  - `guangyuanwang`：512,157 chars / 16 files（net +213 新增行）。
  - `ouyangruize`：499,294 chars / 16 files（net +17 新增行）。
  - `laimerbotrolenk`：patch 作为 Python 字符串内嵌（16 files，文件集相同；`ORIGINAL_HARNESS_PATCH` 509 KB 字符串）。
  - `prvsiyan`：patch 被保留在 inert/压缩文本里（作者自述未改），setup_env 与我们逐键相同。
  - `leoprovorov`：**没有 harness patch**（手册 notebook，用现成 dfranzen 输出做分析）。
- 所有“排版差异”正好是 **11 个字符**（我们 vs dfranzen 原文），与 F85/F91 一致。

### 2.2 评分路径配置：公开面**没有**第二套

- 所有有配置 cell 的笔记本，`TRUE_SUBMISSION` 分支里的 `concurrency=120`、`max_runtime_s_per_game=532*60`、`n_passes=1` 都相同（我们与全部 fork 一致）；
  差异只出现在**离线演练分支**（n_passes、demo 排除集、5–25 min 上限），这些不进入评分。
- 例外只有两处，且都不是“调度参数”：
  - `weitaoguo` 改的是 **`TRUE_SUBMISSION` 的判定方式**（见 §4.1）；
  - `greenalgeria` 改的是 **serving 参数**（`MEMFRAC`、`SPEC_STEPS`，见 §4.5）。
- `machine_shape`：所有 GPU 笔记本都是 `NvidiaRtxPro6000`（无差异）。
- `dataset_sources / model_sources`：25 本与 dfranzen 相同；额外挂载只有 3 本（dennis 的 cpython312 runtime、manwithacat 的 python312.bin、leoprovorov 自己的 dataset）。
- `docker_image`：多数是 `gcr.io/kaggle-private-byod/python@sha256:57e612…`（= dfranzen 当前环境）；`heliosli / shiiin9 / yukailiu / leoprovorov` 用 `gcr.io/kaggle-images/python@sha256:e5452ce6…`；
  `dennis / laimer / manwithacat` 用 `…python@sha256:2757e0c7…`（py3.12 相关）。这更像是“保存会话时 Kaggle 默认镜像不同”，不是刻意改动；但 laimer 明确利用了 py3.12 镜像规避 cp312 wheel 问题。

---

## 3. F93 专项：`ARC3_MEMORY_SECTIONS` 全表（Lead 指定，最高优先级）

| notebook | score | `ARC3_MEMORY_SECTIONS` | 其它被改动的 `ARC3_*` / `LOCAL_ANALYZER_*` 键 |
|---|---|---|---|
| **我们（ppxl16 verbatim）** | 34.30(ours) | **`'off'`** | —（基线） |
| dfranzen（原文） | 34.30 | `'off'` | — |
| tantan0327 | 33.55 | `'off'` | —（dprime 在 cell 里设 `os.environ`，非 setup_env） |
| jingshuifu | 33.22 | `'off'` | — |
| weitaoguo | 32.61 | `'off'` | — |
| heliosli | 32.60 | `'off'` | — |
| jingshuifu v3 | 32.60 | `'off'` | `ARC3_PRIORITY_PACE: '0'→'1'` |
| dennis6886 | 32.59 | `'off'` | — |
| greenalgeria/up-arc-3 | 32.38 | `'off'` | — |
| amatlas | 32.12 | `'off'` | — |
| sujanmajhisuzan | 31.93 | `'off'` | `ARC3_WORLD_MODEL_SIM=1`、`ARC3_UND*=1`（8 个）、`ARC3_PRIORITY_ACTION_PADDING='0.0'`、`ARC3_NOOP_REPEAT_GUARD=1`、`ARC3_DEATH_LEDGER=1`、`ARC3_DEATH_REPEAT_GUARD=1`（这些键我们的 patch **没有**读取方，见 §3.1） |
| habanwer | 31.90 | `'off'` | — |
| zhangyues0000 | 31.76 | `'off'` | `ARC3_R3_GAMEOVER_LEDGER=1`（其自带 patch 读取） |
| leoprovorov | 31.73 | **不用 setup_env**（手册 notebook，无 harness） | — |
| skarin | 31.66 | `'off'` | — |
| lwq255 | 31.65 | `'off'` | — |
| shiiin9 | 31.54 | `'off'` | — |
| lalalia9 | 31.46 | `'off'` | — |
| sigeward | 31.27 | `'off'` | — |
| manwithacat | 31.07 | `'off'` | — |
| yongjiehishi | 31.05 | `'off'` | — |
| yukailiu | 30.80 | `'off'` | — |
| spark328 | 30.75 | `'off'` | — |
| ouyangruize | 30.74 | `'off'` | `ARC3_YIELD_RESUME_PROMPT='short'`、`ARC3_YIELD_RESUME_TONE='minimal'`、`ARC3_RESUME_PROMPT_IMAGES='0'`、`ARC3_STUB_DEAD_REASONING='1'`、`ARC3_REPEAT_STATE_GUARD='1'`、`ARC3_DEATH_REPEAT_GUARD='1'`、`LOCAL_ANALYZER_YIELD_TOKENS 2048→6144`（**全部在我们的 patch 里有读取方**，见 §4.4） |
| prvsiyan | 30.65 | `'off'`（setup_env 与我们逐键相同，嵌在 inert/raw cell 里） | — |
| laimerbotrolenk | 30.58 | `'off'` | `ARC3_HISTORY_ASSISTANT_TURNS='0'`（os.environ，在 setup_env 之后覆盖） |
| guangyuanwang | 30.46 | `'off'` | — |
| mayankraaz | 30.01 | `'off'` | — |

**答 F93：没有任何一本 ≥30 分笔记本把 `ARC3_MEMORY_SECTIONS` 从 `off` 改成 `slim`/`medium`/其它值。**
27 本里 25 本显式 `'off'`，2 本（leoprovorov 手册、prvsiyan 内嵌版）根本不走我们这套 setup_env —— 后者的 setup_env 与我们逐键相同（也是 `off`）。

**补充证据（比“没人试过”更强）**：我们自己的 patch 里就写着为什么关：
- `_memory_sections_disabled()`：`off` 会移除整条持久记忆机制（carried block/section guidance/nudges/parsing 全没，world-model 行也从 system prompt 消失）。
- `_memory_section_labels()` 的 docstring 记录了**25 局实测的 section 写入频次**：World model 351、Plan 255、Open questions 25、Recent findings 11、Action model 10、Goal model 9、Cross-level notes **0**；
  并说被丢掉的 section 也正是“写一次就不再更新、却被当成现状反复 re-inject”的陈旧项（有“一个已回答的问题被挂了一整局”的观察）。
  ⇒ `'off'` 更像**作者试过并主动关掉**的选择，不是遗漏。
- 另外 `ARC3_WM_WIPE_ON_LEVEL`、`ARC3_WM_WIPE_ON_GAME_OVER`、`ARC3_WM_REVISE_NUDGES`、`ARC3_WM_REBUILD_NUDGE`、`ARC3_WM_NUDGE_TURNS`、`ARC3_MEMORY_SECTION_MAX_CHARS` **这 6 个 knob 我们的 patch 都支持**（只是 setup_env 没列）；如果 Lead 仍要试“开记忆”，这是纯 knob 实验（不加代码），但应按“我们是第一个”的未知风险对待。

### 3.1 公开面所有“我们 baseline 没设”的 env 键，以及我们的 patch 认不认

| 键 | 我们的 patch 是否认识 | 谁在用 |
|---|---|---|
| `ARC3_DEATH_LEDGER` / `ARC3_DEATH_REPEAT_GUARD` / `ARC3_NOOP_REPEAT_GUARD` / `ARC3_REPEAT_STATE_GUARD` / `ARC3_STUB_DEAD_REASONING` | **认**（有读取方） | sujan、ouyangruize |
| `ARC3_YIELD_RESUME_PROMPT` / `ARC3_YIELD_RESUME_TONE` / `ARC3_RESUME_PROMPT_IMAGES` | **认** | ouyangruize |
| `ARC3_PRIORITY_PACE`（我们='0'，他们='1'） | **认** | jingshuifu v3 |
| `ARC3_PRIORITY_ACTION_PADDING` | 不认 | sujan |
| `ARC3_UND` / `ARC3_UND_*`（8 个） | 不认（要第二份 patch） | sujan |
| `ARC3_WORLD_MODEL_SIM` | 不认（要新模块 `world_model.py`） | sujan |
| `ARC3_R3_GAMEOVER_LEDGER` | 不认（自带 monkeypatch） | zhangyues0000 |

⇒ 也就是说：**ouyangruize 的全部 env 改动，我们都能一行 knob 复刻**；sujan 的那批必须搬代码。

---

## 4. 候选改动（我们没试过的），按“值一次抽样风险”的可能性排序

> 排序依据：① 是否有**独立于分数的机制理由**；② 改动大小/可逆性；③ 公开面证据强度（几本在用、有没有自述的对照）。
> F92 的规则照旧：任何新内核实测=一次未知风险的抽样；下面每条都标注风险与“先离线验什么”。

### 4.1 ★ 用「网关可达性」兜底 `TRUE_SUBMISSION` 判定 —— `weitaoguo`（32.61）
**它改了什么**（cell 5 ≠ patch，纯 notebook 改动）：
```python
_ENV_FLAG = os.environ.get("KAGGLE_IS_COMPETITION_RERUN","").strip().lower() in {"1","true"}
_GW = False if _ENV_FLAG else _arc_gateway_reachable()  # 轮询 http://gateway:8001/，最长 900s
TRUE_SUBMISSION = _ENV_FLAG or _GW
```
**依据（这条最强）**：weitaoguo 的注释原文：*“2026-10-22 的评分 rerun 里 `KAGGLE_IS_COMPETITION_RERUN` 没被读到，笔记本走了离线演练分支，
只跑 1 个环境并提交‘一行占位 parquet’→ 官方 0.00。”*
而我们的 F86 记的是：`57502063`，**2026-10-22 00:09Z 提交、原版内核 version 1、未做任何改动、0.00**。
**同一天、同一个失效模式、两本互不相关的笔记本** —— 这足以把“我们 10-22 的 0.00”重新解释为**模式判定失败**，而不是 agent/模型失败。
**为什么对我们特别值钱**：F82 说目标是尾部；F86 说每次 0.00 烧掉一次抽样。这是**防 0.00** 的改动，不是提分改动，但它保护的是我们唯一稀缺的资源。
**怎么改**：只动 cell 4 的一行判定；把 probe 超时从他们的 900s 降到 **120–180s**（否则交互 Save&Run 会白等 15 分钟才回退离线）。网关不存在时行为与现在完全一致（失败即离线）。
**风险**：低。唯一的“新行为”是在 env flag 缺失但网关在的情况下改走提交分支——这正是我们要的。
**离线先验**：本地跑一遍交互分支，确认 probe 在无网关时按 120s 超时回退、且 `TRUE_SUBMISSION=False` 的路径仍能出占位 parquet。

### 4.2 ★ Solved-level memory（已解关卡记忆）—— `lalalia9`（31.46）/ `mayankraaz`（30.01），源头 `rellik13/sirikilohit` M85
**它改了什么**：一个 ~10 KB 的 cell（**不改 harness patch**），monkeypatch `ToolAgent` 四个方法：
`analyze`（开局前：从 runtime_state 抽本关“已解等级”的事实）、`_build_user_prompt`（在接下来两轮里要模型写一行 `Rule for level N:`）、
`_note_history_evicted`（在上下文 drain 时把记录块写进 system prompt 末尾）、`_trim_messages_for_context`（让新 system prompt 随 drain 一起生效）。
记录内容 = 等级号、动作数、通关那次尝试的最后 30 个动作、通关那一轮 reasoning 的尾部；pin 成 system prompt 末尾一个块，最多 3 关全量、更早只留一行。
**依据**：lalalia9 的注释说这是 **“rellik13/sirikilohit Milestone 2 写-up 里唯一真正帮上忙的文字改动（+2.8）”**，并解释了机制理由：
dfranzen 每局一条滚动对话，118k→~59k drain；一个关卡的回合通常塞满窗口 ⇒ 第一次 drain 之后 agent 忘掉上一关怎么解的、重新推导已会的机制。
这正好是 F89/F91 那条“不是打不动，是知识被丢掉”的失效模式的**另一条修法**（不换调度，换记忆）。
**可移植性（我已核对我们 patch）**：四个 hook + `runtime_state.load_runtime_state` + `_history_messages/_last_step_summary/_system_prompt` **全部存在**；
lalalia9 的 cell 其余部分是逐字的 dfranzen 自定义 cell，可直接替换成我们 cell 16 + 追加该机制。
**风险**：中。它改 system prompt 尾部（cache 上他们论证过：只在 drain 时写，服务端本来就要重读）；每关多一次“请写一行规则”的模型输出。
**离线先验**：跑 2–3 局，确认 ① hook 都装上（有 `SOLVED_LEVEL_MEMORY_PATCH on` 打印）② 块确实只在 drain 时刷新 ③ token 用量不爆 `ARC3_CONTEXT_DRAIN_TOKENS`。

### 4.3 ★ 启动保活（/health 等待 + 定期免费 RESET）—— `mayankraaz`（30.01）
**它改了什么**：一个 2.8 KB cell，monkeypatch `_HarnessGameSession._play_inner`：在进入某局 play 循环前先等 `http://127.0.0.1:8001/health`；
等待期间由“owner”那一局立刻发一次 RESET、之后每 8 分钟一次（**开局时 RESET 在 competition 模式免费：不算步数、不算动作**），从而不让网关的“15 分钟没有动作就判死”生效。
**依据**（他们注释里给了两条可核对的事实）：网关 15 分钟无动作即结束（discussion 750173）；Kaggle 模型盘有时极慢，**他们三次跑测到权重加载 257s / 599s / >30min**，
而 dfranzen 的设计是 12 分钟就放 harness + 只发一次 warmup RESET ⇒ 每局 900s 请求 grace 烧完、整本 0.00。
**可移植性**：`_HarnessGameSession._play_inner` / `_execute_auto_reset` / `should_stop` 都在我们 patch 里（已核对）。
**风险**：中低。它只在我们“模型服务还没起来”时动作；对正常快启动无影响。是 4.1 的**互补**（4.1 修“判定错”，4.3 修“服务慢”）。
**离线先验**：本地起服务前先跑，确认 keepalive 打印 `STARTUP_KEEPALIVE RESET`、服务起来后立即停止本机制；确认不会把 RESET 计入动作数（离线看 `levels_completed`/动作日志）。

### 4.4 动画感知的 no-op / stale-state 守卫 + 同源的 knob 包 —— `ouyangruize`（30.74）
**它改了什么**：
1. patch 净 +17 行（**我们 patch 的严格超集**）：`python_tool_sandbox.py` / `tool_agent.py` / `solver.py` 里，把 `animation.transient_pixels>0` 视为“真变化”——
   动画中间帧变了但终帧复位的动作，**不应**被 batch-noop/stale-state 守卫判成 no-op（否则 snippet 的信念/守卫会被错误推进，或合法动作被拦）。
2. env（我们的 patch 全部支持）：`ARC3_YIELD_RESUME_PROMPT='short'`、`ARC3_YIELD_RESUME_TONE='minimal'`、`ARC3_RESUME_PROMPT_IMAGES='0'`、
   `ARC3_STUB_DEAD_REASONING='1'`、`ARC3_REPEAT_STATE_GUARD='1'`、`ARC3_DEATH_REPEAT_GUARD='1'`、`LOCAL_ANALYZER_YIELD_TOKENS 2048→6144`（让模型一次输出更多再 yield）。
**依据**：这是**唯一一个直接改“守卫在什么情况下拦动作”的公开改动**；F89 的机制清单里 guards 正是会**阻止**合法动作的一类。改动面小、可逆、可离线验证。
**风险**：中低（patch 级）。**但**：若只想花一次抽样，可以**先只上 knob 包**（零 patch）——那也是我们没试过的组合，风险更低。
**离线先验**：构造“动画变化但终帧相同”的动作（公开环境里不少），确认改动前后守卫行为差异；再统计被拦动作数量。

### 4.5 ARCAID3 lexicon view（把画面变成“对象/规则”结构化视图）—— `habanwer`（31.90）
**它改了什么**：一个 107 KB cell（**不改 patch**），给每个 frame 加：
`current_frame.code`（真分辨率的对象列表 + 图标 legend + 放置）、`.objects`（symbol/row/col/size/可点击的屏幕坐标）、`.native`（真实网格，如 16×16 而非 64×64）、
`.changes_since(frame)`、`.rules`（从本关最近步数用规则语法学 “when <action> … then <change>”，带 right/wrong 计数）＋ 按关卡的 scale lock ＋ 视觉对象永续。
它**专门为 dfranzen 的 harness 做过端口**（注释：三个 prompt 锚点已按 dfranzen 版调整），我们 patch 的锚点与之一致。
**依据与教训**：v1 加了视图但**模型 0/1130 次工具调用用它**；v2 才去改 harness 里“frame 只暴露 `.ascii/.step/.level`”的三处 prompt 行——
**能力加了但 prompt 不说，就没用**。这对我们做任何“加能力”的实验都是现成的教训。
**风险**：中高（代码量大、prompt 锚点必须精确、每请求多 token）。但它是唯一一个**改变模型“看见什么”**的公开部件，而不是调度/记忆。
**离线先验**：先只验 prompt 锚点命中（它自己会打印 READY 哪些编辑生效）+ 一局沙箱自测；再谈上分。

### 4.6 其它值得知道但不建议优先的（按理由给一行）

| 改动 | 谁 | 为什么不上榜 |
|---|---|---|
| dprime / D′ / Apex 优先级家族（`ARC3_PRIORITY_FORM='dprime'`、`install_d()`、Apex 注入） | tantan、heliosli、amatlas、yongjiehishi、weitaoguo、dennis、shiiin9、ouyangruize、guangyuanwang、mayankraaz、sujan | **同一类干预**：替换 `tool_agent.priority_value`/`ProgressPace`，并且都取消“未开局游戏先跑”。Lead 已试（F92）→ 0.00。9 本在用只说明“这是流行 fork 的默认装饰”，不构成独立证据。**不要只因为 33.55 再试一次。** |
| `ARC3_PRIORITY_PACE='1'`（一行） | jingshuifu v3（32.6，同作者 v2 是 33.22 且为 '0'） | 同作者的两次分数无法区分（max-over-draws，sd≈2.7）；一行可试但证据弱，优先级低于 4.1–4.4 |
| R3 death ledger（跨轮死亡账本） | zhangyues0000（31.76） | 机制合理、代码 7.5 KB 可移植（`_summarize_step_sequence` + user-message builder 两个 seam 都在我们 patch 里），但我们的 patch **已经有** `death_ledger`/`game_over_trace`（42/5 处），边际收益不确定；可排 4.2 之后 |
| Fable layer（指标注记/等级日志/步数预算） | leoprovorov（31.73） | 作者自己写“未测出增益、不改变体也 31.73”，且不是 fork notebook（无 patch）；**不作为候选** |
| 预写 `submission.parquet` + try/finally（输出契约） | sujan、laimer、prvsiyan | ARC-AGI-3 的分数由 gateway 算，不是读我们的 parquet（prvsiyan 原文也说 rerun 里不写提交文件）；它防的是“交互跑没有产出文件”，**不防 0.00**。别把它当 0.00 解药。 |
| `MEMFRAC 0.99` / `SPEC_STEPS 4`（serving） | greenalgeria（32.38） | 唯一一个改**吞吐**的公开改动：更多 spec steps ⇒ 更快出 token ⇒ 同预算更多动作/关。纯 launcher 参数、零 patch、可逆，**很便宜**；但只 1 本、无法从分数区分。可作为“零风险抽一次”的备选。 |
| CPython3.12 runtime（dataset/镜像/sitecustomize/libcuda） | dennis、manwithacat、laimer、yukailiu | 只在我们真的遇到 wheel/驱动/sitecustomize 故障时才有意义（对应 F52–F74）；不是提分项 |
| 输入挂载路径自适应（`v15_input` / `resolve_path` / `_find_input`） | laimer、dennis、mayankraaz、yukailiu、yongjiehishi、zhangyues0000 | 只是让 notebook 在两种 `/kaggle/input` 布局下都能跑；我们没有这个问题 |

---

## 5. `sujanmajhisuzan` 的 616 KB patch：公开面唯一一份“整本 knob 手册”

它比我们多 12 个文件（已提取到 `extracted/sujanmajhisuzan_…/`）：

```
ARC3-Inference/CONFIGURATION.md          <- 483 行：整条 fork 血统的完整改动清单 + 每个 knob 的默认值（高价值文档）
ARC3-Inference/Makefile
ARC3-Inference/configs/inference.json
ARC3-Inference/configs/inference.openrouter.json
ARC3-Inference/inference/agent/test_sandbox_simulator.py
ARC3-Inference/inference/tools/eval.py
ARC3-Inference/inference/tools/significance.py
ARC3-Inference/inference/tools/traces.py
ARC3-Inference/inference/utils/test_world_model.py
ARC3-Inference/inference/utils/world_model.py     <- DF-WM：SimFrame/compare_grids/check_sim/BFS search/act_checked
ARC3-Inference/pyproject.toml
ARC3-Inference/uv.lock
```
外加第二份 `/kaggle/und-changes.patch`（base85+gzip 内嵌）：ARC3_UND 子系统（undo 观测/digest/shadow/timer/tools/hooks/collapse）。
它自己的 markdown 把配方列成：DF-WM world model + “Apex Deep-Level Persistence Priority” + 超弹性重试（180s read timeout / zero yield / 64 连接池）+ action guards + 预写提交契约。
**判断**：机制上最有野心，但 (a) 它 31.93 并不比基线高；(b) 所有零件都没有对照测量；(c) 搬到我们这里要动 patch（重、风险高）。
**唯一建议单独取用的**：`CONFIGURATION.md` 就是一份 knob 默认值清单（第 10 节列出我们 §3 里那组 WM knob 的默认值），可当作后续 knob 实验的字典。

---

## 6. 我还没能验证的 / 明确的限制

1. **版本漂移**：`kaggle kernels pull` 给的是最新版；`bestPublicScore` 可能来自旧版本。比如 `leoprovorov` 现在这本是手册（无 GPU、无 harness），31.73 几乎肯定来自另一个版本，不能按“手册本身”理解。
2. **无法看评分 rerun 日志**（F86 已记录）：所以 4.1 的因果链是“同一天 + 同一失效描述 + 我们未改动内核也 0.00”，是强关联，**不是**直接观测。
3. **27 本以外的 ≥30 笔记本**：census 只覆盖公开且 `bestPublicScore` 可见的；已删除/私有的（如 `jinhaozhu2` 403）拉不到。旧 census（10-14）里 16 本 ≥30，本次重扫 27 本，说明 10 天内新增了 11 本。
4. 我只做了静态 diff；**没有**在离线环境跑任何一本别人的 notebook（也没有提交任何东西）。§4 的“离线先验”是建议，不是已做。
5. `habanwer` 的 `docker_image` 拉下来是空字符串（元数据缺失），不影响 patch/env 结论，但“它跑在哪个镜像”不可考。

---

## 7. 文件清单（本目录）

| 文件 | 内容 |
|---|---|
| `RECON.md` | 本报告 |
| `census_fresh.py` / `public_scores_fresh.json` / `census_fresh.log` | 全量公开 notebook 的真实 bestPublicScore 重扫 |
| `pull_all.py` / `pull_all.log` / `nb/<slug>/` | 27 本 ≥30 的 ipynb + kernel-metadata |
| `analyze.py` / `analysis/*.json` / `_baseline.json` | 结构化抽取 + 与我们 baseline 的 cell/env/metadata diff（typography 归一化） |
| `summarize.py` / `summary_report.txt` | 逐本 compact 报告（人读版） |
| `factsheet.py` / `factsheets.txt` | 逐本 delta 事实表（含每个新增 cell 的头、env 键、knob 行） |
| `compare.py` / `compare.log` / `extracted/<slug>/` | 跨本 env 键 union；非标准 patch 的逐文件差 + `CONFIGURATION.md` / `world_model.py` 等新文件原文提取 |
| `special.py` / `special.log` | 3 本“patch 不在 `%%writefile` cell 里”的特殊扫描 |
| `f93.py` / `f93.log` | F93 表 + “我们的 patch 认不认这些键” |
| `cell_*.txt` | 候选机制 cell 原文（tantan dprime / weitaoguo D′ / lalalia9 SLM / mayankraaz keepalive / zhangyues R3 / habanwer lens / 以及 sujan 的 delta） |
| `peek.py` / `cells.py` / `deepdive.py` | 小工具 |
