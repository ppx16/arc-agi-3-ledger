# INTERNALS — ARC-AGI-3 内核（498 KB harness patch）计分路径内部清单

写于 2026-10-24。只读分析，未改动任何内核/未提交。写作用域：`arc/internals/`。
数据源（全部本机可复现）：

| 源 | 位置 | 用途 |
|---|---|---|
| 内核 notebook | `arc/scratch/inspect/arc-agi-3-m2-franzen-verbatim.ipynb`（23 cells） | cell 2 = harness patch（498,799 chars），cell 4 = `setup_env` 总开关，cell 12 = SGLang launcher，cell 16 = `bm`/`bm.solver`，cell 20 = 运行入口 |
| patch 拆分 | `arc/internals/_work/patch_parts/00..15`（16 个文件段，`+8405 −197` 行） | 逐文件读；tool_agent.py 占 314 KB / +5339 行 |
| 引擎（**判分就在这一层**） | `arc/starter/.venv/Lib/site-packages/arcengine/{base_game.py,enums.py}`（0.9.3） | `levels_completed` / RESET / level_transfer / ACTION7 的**真实**语义 |
| 计分器 | `.../arc_agi/{scorecard.py,api.py,wrapper.py,base.py}`（0.9.9；竞赛 zip 里同源 0.9.8） | scorecard 怎么记账、动作怎么计、best-of-plays |
| 公开 25 个游戏源码 | `arc/starter/environment_files/<game>/<hash>/<game>.py`（就是竞赛 zip 里的 environment_files） | 验证 ACTION7/边界/HUD 等具体事实 |
| 提取产物（可复跑） | `arc/internals/_work/{cell4_setup_env.py,cell12_launcher.py,cell16_hook.py,cell20_run.py,knobtable.txt,...}` | 每个结论下面的行号都指这些文件 |

**拿不到的两样东西**（所有推断的边界）：① 打补丁前的原始 bundle（`/kaggle/input/.../taaf-kaggle-source-bundle-copy` 不在本机）——所以 patch 只有 context/`-` 行可见，未改动的原函数体看不到；② `taaf` / `inference.framework.run` 的完整源码（patch 只 `git apply --include=ARC3-Inference/*`）。凡是依赖这两者的地方，下文都标 **[推断]**。

---

## 0. 一句话结论（先看这个）

1. **计分发生在引擎/网关侧，不在 notebook 里**：`levels_completed` 是 `arcengine.ARCBaseGame._score`，只能由游戏自己的 `next_level()` 增加；harness 做不了任何“多算一关”的事。比赛重跑时游戏跑在
   `http://gateway:8001/`（cell 20 的 `TRUE_SUBMISSION` 分支），因此 **cell 4 里那个 `ONLY_RESET_LEVELS=true` 只对离线 Save 生效，线上无效** —— 这是 F92「Save ≠ 重跑」的又一条具体机制，见 §1.5。
2. **F89 的面板没错，但它只覆盖了“cell 4 里写了什么”，没区分“是否真的生效”**：cell 4 的 3 个守卫（`ARC3_GUARDS_FROM_LEVEL=2`、`ARC3_BATCH_NOOP_BLOCK=1`、`ARC3_STALE_STATE_BLOCK=1`）才是活的；而 patch 里另外 4 个 repeat/death 类守卫（`ARC3_NOOP_REPEAT_GUARD` / `ARC3_DEATH_REPEAT_GUARD` / `ARC3_DEATH_GUARD_LOOKAHEAD` / `ARC3_DEATH_LEDGER` / `ARC3_REPEAT_STATE_GUARD`）**默认全 False 且 cell 4 没有设置 ⇒ 本轮是死代码**（§2.2、§3.2）。
3. **“守卫拦掉合法动作”确实存在，但只发生在同一个 Python snippet 内部**，而且**不消耗引擎动作**：`STALE_STATE_BLOCK` 会拒绝“某动作已执行但只是边框/HUD 变化”之后的**下一个任意动作**（不只是重复动作），抛可捕获的 `StaleStateActionError`；因为 stale 标记只在新 snippet 或下一次真实变化时清空，**同一个 snippet 内无法自愈，只能等下一个 turn/tool 往返**。`BATCH_NOOP_BLOCK` 不拒绝，只是把“已执行的那个 no-op”之后的批内动作截断。二者都是 **turn 成本，不是 action 成本**。
4. **“一个动作算几次”= 恰好 1 次**，refused 动作算 0 次；RESET 也记 1 个动作（首局建 play 的 RESET 除外）。batch/多次 `action()`/action echo/action trace 都不会重复计分（§4）。
5. **调度部分是唯一能“分配算力”的确定性机制**，且 F89 的读法基本正确，但有一个更精确的版本：`_PriorityGate` 只有 `ARC3_MAX_ACTIVE_STREAMS=10` 个槽；**槽只在“该游戏第一次上下文裁剪”时移交**（≈30–50 turns），未裁剪游戏站在 `2,000,000` 的固定高优先级带上、按 `game_index` 排队；裁剪后按 `priority_value()`（深度优先）重新竞争。SGLang 那边 `--max-running-requests 10` 才是真正的并发上限 —— 两个 10 是**不同的 10**，见 §6。
6. **上下文裁剪**：cell 4 把历史带压到 ≈**59k–118k token** 的锯齿带（128k 窗口 − 12k 输出预留，drain 58k），首剪在 ~30–50 turn，剪一次掉一半历史；图片 ~402 token/张、每 turn 1–2 张；工具输出按“头 2/3 + 尾 1/3”中间截断。`HISTORY_ASSISTANT_TURNS=150` 在这个带宽下**基本不 binding**（推断）。细节 §5。

**关于分数的口径必须写在最前面（影响所有优先级判断）**：

- **任务/Lead 口径（本文按它排优先级）**：分数 = 每个游戏 `levels_completed / number_of_levels` 的均值 ×100（所以“关卡数”是唯一分子；每关等权；完成第 1 关和完成第 8 关在分数上一样值钱，但第 1 关便宜得多 ⇒ **理论上 breadth-first**）。
- **arc_agi 自带的 `EnvironmentScorecard` 口径（RHAE）**：`level_score = min(1.15, (baseline_i/actions_i)^2)`，按 1-based 关卡号加权平均、再对游戏取均值（`scorecard.py` L146–183 / L185–217）。本地 `tools/score_local.py` 用的是这个，所以它和公榜数（22–34）量纲不同（F25 的 3.8 分线 vs 公榜 30+ 线就是这个原因）。**如果线上其实用 RHAE，那么“浪费的动作”是直接乘进分数的；如果是 levels 口径，浪费动作只通过预算影响分数。** 我在每条建议里把这两种情况分开写。
- ⚠️ 而且**在 notebook 的环境里这个 RHAE 计分器根本记不上账**：cell 4 的 `ONLY_RESET_LEVELS=true` 会让本地 wrapper 的“建局 RESET”变成 `level_reset`（`full_reset=False`），于是 scorecard 永远不会 `new_play` ⇒ 本地计分器输出 `environments: []`。本机实测见 §1.6。**离线能用的分数只有 taaf 的 benchmark 关卡统计，不是 scorecard。**

---

## 1. 计分路径：分数到底读的是什么

### 1.1 引擎侧：`levels_completed` 怎么涨、怎么掉

`arcengine/base_game.py`（0.9.3，与竞赛 zip 里的 0.9.3 wheel 一致）：

```python
# L412-418
def next_level(self) -> None:
    self._score += 1
    if not self.is_last_level(): self._next_level = True
    else: self.win()

# L188-260 perform_action(): ...
frame_raw.levels_completed = self._score      # L244
```

- 只有游戏自己调 `next_level()` 才会 `_score += 1`；最后一关时 `next_level()` 直接 `win()`，**不发一帧 completed 的 level-up**，状态变 `WIN`。
- `full_reset()`（L318–324）：`_score = 0`、回第 0 关、`_full_reset=True`。
- `level_reset()`（L326–329）：只重置当前关，**`_score` 保留**。
- `handle_reset()`（L305–316）：
  ```python
  if os.getenv("ONLY_RESET_LEVELS") == "true" and self._state != GameState.WIN:
      self.level_reset()
  elif self._action_count == 0 or self._state == GameState.WIN:
      self.full_reset()
  else:
      self.level_reset()
  ```
  ⇒ 有 `ONLY_RESET_LEVELS=true` 时，**非 WIN 状态的 RESET 一律 level_reset，已通关卡数不丢**；WIN 状态下的 RESET 会 full_reset 并把 `_score` 清零（但见 1.2 的 best-of-plays，清零不伤最终分：它会开一个新 play，卡面取 max）。
- `_action_count`（L268–280）：**只有非 RESET 的动作 +1**；`set_level()`（L147–165）会把它清零。这个计数在 `api.py` 里被用于一个特殊分支（1.3）。

⇒ **harness 无法改变关卡计数**。harness 能做的是：让模型更快/更少浪费地通关、别在通关后被 RESET 清零（后者由 `ONLY_RESET_LEVELS` 保障，见 1.5）。

### 1.2 scorecard 侧：一局怎么记账、多次尝试怎么取最高

`arc_agi/scorecard.py`：

- **动作计数**（L834–858 `update_scorecard`）：`action_input.id.value in [1..7]` → `take_action`（actions+1）；`id==0`(RESET) 且 `full_reset` → `new_play`（**新开一个 play**），否则 `reset`（`inc_reset_count`：**resets+1 且 actions+1**）。⇒ **RESET 也算一个动作**。
- **关卡变化只在“值变了”时追加一条**（L706–714）：
  ```python
  def set_levels_completed(self, guid, current):
      if current != existing: self.actions_by_level[idx].append((current, self.actions[idx]))
      self.levels_completed[idx] = current      # ← 覆盖，不是 max
  ```
- **一局多 play 取 max**：`Card.most_levels_completed = max(levels_completed)`（L667–668）；`Scorecard.levels_completed = sum(most_levels_completed)`（L815–816）；`EnvironmentScorecard.from_scorecard` 先选 `best_idx = argmax(levels_completed)` 再用它算分（L567–600）。⇒ `best-of-plays` 是**同一 submission 内**的机制，也是 F81 “公榜是 best-of-draws”在平台层的同族逻辑。
- **每个 play 的 `levels_completed` 是被覆盖的**：一个 play 内 WIN 之后如果又发 RESET（full_reset→`_score=0`），这个 play 会被改成 0；但卡面上还有别的 play 时取 max 就没事。**只有一个 play 时这会让整局分归零**——线上的 `n_passes=1` 下，是否会发生取决于 taaf 在 WIN 后是否再发 RESET；cell 20 的 launcher 只会在 GAME_OVER 后自动 RESET（见 1.4），WIN 后 run 结束，所以**正常路径不会碰到**。**[推断：taaf 部分不可见]**
- RHAE 口径下还有两个细节（若线上用 RHAE）：① 未完成关卡的动作全部记到“下一个未完成关”的 `level_actions`（`_calculate_score` L470–491），但因为该关 `completed=False` ⇒ 0 分，**浪费只会毁掉“本关”的效率，不会毁掉已完成的关**；② 每关的 `actions_i` 是“上一关完成到本关完成之间累计的引擎动作数”，**包含失败尝试和 RESET**。

### 1.3 API 层：`full_reset` 与那个 “第一动 RESET” hack

`arc_agi/api.py`：

- `RestAPI.level_reset_only = os.getenv("ONLY_RESET_LEVELS") == "true"`（L42）—— **这是服务端进程读的**。
- 新环境第一次 `RESET` → `_get_or_create_environment` 返回 `full_reset=True` → **不执行 step**，直接回 `g.observation_space`，然后（仅当 `level_reset_only`）`scorecard.update_scorecard(guid, response, True)` 建 play（L347–354）。⇒ 首 RESET 不花动作。
- 已存在的环境再发 RESET，且 `competition_mode` 且 `g._game._action_count == 0` 时（L316–334）：**这次 RESET 被吞掉**（不 step），但仍 `update_scorecard(..., False)` ⇒ `inc_reset_count`：**白扣 1 个动作**。否则正常 `g.step(RESET)` → 引擎 `handle_reset()`。
- `wrapper.py` 才真正写 scorecard（L186–200）：`if resp.guid and len(resp.frame) > 0: update_scorecard(..., resp.full_reset)`。⇒ 空帧（GAME_OVER/WIN 之后的非 RESET 动作）不会记账。
- ⚠️ 上面这些 `api.py` 分支只在**服务端**（在线 / competition_mode）存在；离线走 `LocalEnvironmentWrapper`，不经过 `RestAPI` ⇒ **离线根本不会出现“RESET 被吞”这条路径**，这是又一条 Save-vs-rerun 差异。

### 1.4 harness 侧：`level_completed` / `game_over` / auto-reset 是怎么产生的

`solver.py`（patch part 10）：

```python
# part10 L750-782
gameplay_changed = _interior_gameplay_changed(previous_grid, new_grid)
level_completed = bool(new_state.just_won_level and raw_state != arcengine.GameState.WIN)  # L780
```
- `just_won_level` 来自 `taaf.game.GameState`（**源码不可见**；语义=“本次动作刚好让 levels_completed 上升且还没 WIN”）**[推断]**。最后一关通关 ⇒ `level_completed=False`、`done/run_complete=True`。
- GAME_OVER：`_play_inner` 循环里 `_is_engine_game_over()` → `_execute_auto_reset()`（part10 L461–476 附近）⇒ **自动发一次 RESET**（= 1 个引擎动作，记到当前关的动作里），然后同一局的 `levels_completed` 不变（因为 `ONLY_RESET_LEVELS`；见 1.5 的线上差异）。
- 模型侧看到的是 `game_over` 标志 + 一大段“BAR RULE”诊断提示（part07 L4287–4365），并被告知“completed levels are kept”——**这句话在线上是否成立取决于网关的 `ONLY_RESET_LEVELS`，不在我们手里**。

### 1.5 ★ 线上 vs 离线：一个确定性的“开关失效”

cell 4 第 45 行：

```python
os.environ["ONLY_RESET_LEVELS"] = "true"   # "Pin arc_agi's cached level_reset_only before its client is built (RESET keeps the level)"
```

- 它被读的位置：`arcengine/base_game.py` 的 `handle_reset()` + `arc_agi/api.py` 的 `RestAPI.__init__`。
- 线上（`KAGGLE_IS_COMPETITION_RERUN=1`）：cell 20 的 `TRUE_SUBMISSION` 分支把 games 换成 `taaf.game_api.GameAPI(ArcadeSpec(operation_mode=COMPETITION, arc_base_url=os.environ["ARC_BASE_URL"]))`，`ARC_BASE_URL=http://gateway:8001/` ⇒ **引擎与 RestAPI 都跑在 gateway 服务里，读到的是 gateway 自己的环境变量**；notebook 里的 `os.environ` 只影响 notebook 进程。
- ⇒ **`ONLY_RESET_LEVELS` 在线上基本是死开关**；离线 Save 时它是活的。这带来两个后果：
  1. F92 又一条：任何“依赖于 RESET 保留关卡”的行为（死亡后不丢已通关卡数、在关卡起始发 RESET 不倒退）**离线验证过的结论不能外推到线上**；线上到底怎样取决于竞赛方 gateway 的配置（很可能也是 true，因为这是官方比赛行为，但**我们没有证据**）。
  2. 反过来，如果线上是 `false` 且模型在“关卡刚切换、`_action_count==0`”时发 RESET，就会 `full_reset` 把 `_score` 清零并把该 play 的卡面改成 0 —— 但 `EXPOSE_RESET` 默认 `off` 且 cell 4 没开，模型**发不出合法 RESET**（不在 valid_actions ⇒ `step_env` 报 "not valid right now"）。所以这条风险被 `EXPOSE_RESET=off` 挡掉了。**如果哪天有人把 `EXPOSE_RESET` 打开，这就是一个确定性的丢分口子。**
- 顺带：`EXPOSE_UNDO='on'`（cell 4）是**客户端侧**（`action_names.py`），线上有效。公开 25 个游戏里有 4 个真的实现 ACTION7（`ar25`/`sb26`/`sk48`/`su15`）：`ar25` 里 `ACTION7` 是 `pop` 一个历史状态（真 undo）；`sk48`/`su15`/`sb26` 也有 ACTION7 分支。⇒ 对这批游戏，UNDO 是“花 1 个动作撤一步”，比死亡+自动 RESET（2 个动作 + 重开一关）便宜。

### 1.6 本机验证实验（可复跑，结论比推断硬）

两个探针都在 `arc/internals/_work/` 下，用 `arc/starter/.venv` 的 python（arc_agi 0.9.9 + arcengine 0.9.3 + 同一份 25 个游戏源码）跑：

**(1) `engine_probe.py` —— RESET 语义（引擎层）**

```powershell
& D:\kaggle\arc\starter\.venv\Scripts\python.exe D:\kaggle\arc\internals\_work\engine_probe.py true    # ONLY_RESET_LEVELS=true
& D:\kaggle\arc\starter\.venv\Scripts\python.exe D:\kaggle\arc\internals\_work\engine_probe.py false
```

| 步骤 | `ONLY_RESET_LEVELS=true` | `false` |
|---|---|---|
| 连升 3 关后 | `score=3` | `score=3` |
| **关卡起始（action_count=0）发 RESET** | **`levels_completed=3`（保住）**、`full_reset=False` | **`levels_completed=0`、`full_reset=True`（全部丢）** |
| WIN 后发 RESET | `levels_completed=0`、`full_reset=True`（会开新 play，卡面取 max，不伤最终分） | 同左 |

⇒ ① 该 flag 的真实作用就是“**非 WIN 的 RESET 永不丢已通关卡**”；② 没有它时，“关卡刚切换就 RESET”是**确定性丢光整局**的动作（这也解释了为什么必须配 `EXPOSE_RESET=off`：模型根本发不出 RESET，见 1.5）；③ WIN 后 RESET 会 full_reset，但只会新开一个 0 分 play，`most_levels_completed` 取 max ⇒ 不伤分（§1.2）。

**(2) `offline_probe.py` —— 本地 scorecard 在 notebook 环境下是否记账**

```powershell
& D:\kaggle\arc\starter\.venv\Scripts\python.exe D:\kaggle\arc\internals\_work\offline_probe.py true    # 其余环境与 cell 4 相同
& D:\kaggle\arc\starter\.venv\Scripts\python.exe D:\kaggle\arc\internals\_work\offline_probe.py false
```

| | `ONLY_RESET_LEVELS=true`（= 我们的 cell 4） | `false` |
|---|---|---|
| 建局首帧 | `state=NOT_FINISHED levels=0 full_reset=False` | `full_reset=True` |
| 打 8 个动作后关 scorecard | **`environments: []`、`total_actions: 0`、`total_levels: 0`** | `environments: [ls20]`、`actions=8`、`levels=0`、`level_baseline_actions=[22,123,73,84,96,192,186]` |

⇒ **在 cell 4 的环境下，本地 `arc_agi` 计分器完全是空账**（因为建局 RESET 不再产生 `full_reset=True`，`new_play` 从不被调用）：
- 任何想用 notebook 环境跑 `EnvironmentScorecard`/`tools/score_local.py` 的离线标定都会得到 0，且**不会报错**；
- notebook 的离线 Save 本来也不读 scorecard（cell 20 只写一个假 `submission.parquet` + 打 benchmark 诊断），所以这个空账一直没被发现；
- 线上不受影响：游戏在 gateway 进程里，scorecard 也在服务端（cell 20 `TRUE_SUBMISSION` 分支）。但这又是**一条“离线看得见的东西 ≠ 线上的东西”**（F92 同族）。

### 1.7 level_transfer（升级那一瞬）信息流

模型在“升级”时拿到什么、拿不到什么，直接决定它在新关卡浪费多少动作：

| 通道 | 状态 | 代码 |
|---|---|---|
| `level_completed` 标志（per action） | ✅ 只在“非 WIN 的升级”为 True；最后一关是 `done/run_complete` | solver part10 L780–782、part07 L3042–3043 |
| 新关卡的启动提示 | ✅ `ARC3_LEVEL_TRANSFER_GUIDANCE=1` ⇒ `LEVEL_START_USER_PROMPT`（“build a new plan / 保留上一个关卡的机制 / 优先小测试”） | part04 L18–31、part07 L4274–4280 |
| 跨关卡 diff 图 | ❌ 被主动抑制（“cross-level diff has no meaning”） | part07 L3336–3344 |
| 跨关卡 object inventory（上一关 START vs 本关 START） | ❌ `ARC3_LEVEL_INVENTORY` 默认 False、cell 4 未设 | part07 L1159、L3590–3652 |
| 每 turn 的“上一 turn → 本 turn”diff 图 | ✅ `ARC3_DIFF_IMAGE=1`（值相同才发；升级 turn 会被抑制） | part07 L3351–3360 |
| 升级动作的动画帧 | ✅ `ARC3_ANIMATION=1` 时可查（`last_animation_frames/timeline`） | part07 L3816–3918、part05 L327–397 |
| 旧的 world model | ❌ `ARC3_MEMORY_SECTIONS=off`；且 `_WM_WIPE_ON_LEVEL=1`（即使开着也会在升级时清掉“跨关保留”以外的部分） | part07 L3239、L1366–1396 |

⇒ **升级是“冷启动”**：除了通用提示和当前盘面图，没有任何“上一个关卡长什么样”的对照。如果某类游戏的新关卡与旧关卡同构（只是布局变），模型要重新推导；这正是 `ARC3_LEVEL_TRANSFER_GUIDANCE` 想补的，但**跨关 inventory 是关掉的**。这是一个“确定性信息缺失”点（不是拦截），可作为候选（打开 `ARC3_LEVEL_INVENTORY=1`），但它每 turn/升级 turn 的 token 成本会上升，且默认关——**不建议在没有离线证据时开**。

---

## 2. 开关面板：cell 4 覆盖 vs 模块默认（真正生效的取值）

`setup_env` 字典在 cell 4 L56–135，随后 `os.environ.update(...)`；L127–135 的 `USE_PRIORITY_SCHEDULING=True` 再追加 7 个调度键。**cell 4 是 import 之前执行的**（cell 2 写 patch、cell 4 apply+set env、cell 8/10 才 import）⇒ 所有 import-time 常量都被它定型。

### 2.1 cell 4 显式设定的键（= 实际生效值）

| 组 | 键 | cell 4 值 | patch 默认 | 作用（代码位置） |
|---|---|---|---|---|
| serving | `LOCAL_ANALYZER_PROVIDER/BASE_URL/MODEL_ID` | vllm / 127.0.0.1:8001 / flashnext | - | 指向 cell 12 起的 SGLang |
| 分析器 | `LOCAL_ANALYZER_TOOL_STEPS` | **`'0'`** | 12 | `0 ⇒ self._tool_steps=None`（part07 L2871）**[推断：None=单个 analyzer turn 内不限工具调用次数]** |
| | `LOCAL_ANALYZER_YIELD_TOKENS` | **2048** | 0(off) | **每 turn 累计生成 ≥2048 就 yield/续写**；只在两次请求之间检查（part07 L5899–5903） |
| | `LOCAL_ANALYZER_YIELD_SECONDS` | 0 | 0.0 | 同上但按墙钟 |
| | `LOCAL_ANALYZER_MAX_OUTPUT` | **12288** | - | 单次请求硬上限（thinking 也含在这 12k 里） |
| | `LOCAL_ANALYZER_TEMPERATURE` | 0.7 | 0.6 | 采样 |
| | `LOCAL_ANALYZER_TOP_P/TOP_K` | 0.95 / 20 | 同 | 采样 |
| | `LOCAL_ANALYZER_ENABLE_THINKING` | `true` | True | 思考开关（**F88/H1**） |
| | `LOCAL_ANALYZER_TOOL_OUTPUT_TOKENS` | **3072** | 1024 | 工具输出给模型的 token 预算（配合中间截断） |
| 上下文 | `LOCAL_ANALYZER_CONTEXT_WINDOW` | 128k | - | 估算用 |
| | `ARC3_CONTEXT_DRAIN_TOKENS` | **58k** | 0 | 触发裁剪后继续丢到 budget−drain；代码再 clamp 到 `budget//2`（part07 L5676–5679） |
| | `ARC3_HISTORY_ASSISTANT_TURNS` | **150** | 30 | assistant 条数上限（在此带宽下基本不 binding） |
| | `ARC3_HISTORY_TURN_DRAIN` | 30 | 0 | 条数上限的滞后 |
| | `ARC3_HISTORY_DRAIN_COALESCE` | `'1'` | False | token 裁剪发生时顺带做条数裁剪（省一次前缀失效） |
| 工具输出 | `ARC3_MIDDLE_TRUNCATION` | `'1'` | False | 超长输出保留“头 2/3 + 尾 1/3”（part07 L4648–4678） |
| | `ARC3_ACTION_ECHO` | `'1'` | 0 | 每次 `action()` 往 snippet stdout 打一行裁决 |
| 提示词 | `ARC3_EXPLAIN_GAMEPLAY_CHANGED` | `'1'` | "" | 解释 `gameplay_changed` 的措辞 |
| | `ARC3_NEW_CHANGED_PROMPTS` | `'1'` | False | 守卫措辞换成 "inside the board area" |
| | `ARC3_LEVEL_TRANSFER_GUIDANCE` | `'1'` | False | 升级时给新关卡的系统+用户提示（part04 L9–31、part07 L4274–4280） |
| | `ARC3_ACTION_INFO` | `'1'` | False | 动作含义表（含 UNDO） |
| | `ARC3_DEDUPE_MULTICALL_LINE` | `'1'` | False | 去掉重复的 multicall 提示 |
| | `ARC3_FRAME_DIFF_HINT` | `'1'` | False | `frame_diff()` 用法提示 |
| 视觉 | `MULTIMODAL_CONTEXT` | `current_grid` | - | 每 turn 附当前盘面图 |
| | `MULTIMODAL_UPSCALE` | 10 | - | 64×64 → 640×640（≈402 vision tokens/张） |
| | `ARC3_DIFF_IMAGE` | `'1'` | False | 再附一张“前后差异图” |
| | `ARC3_GAMEOVER_DIFF_IMAGE` | `'1'` | False | 死亡 turn 的差异图 |
| | `ARC3_ANIMATION` | `'1'` | False | 动画中间帧（可查 `last_animation_frames/timeline`） |
| 守卫 | `ARC3_GUARDS_FROM_LEVEL` | 2 | 1 | 第 1 关不做 per-action 拦截（只观察）；影响 repeat/stale 两类 |
| | `ARC3_BATCH_NOOP_BLOCK` | `'1'` | 0 | 批内“边框 4 格以外无变化”的动作执行后截断批 |
| | `ARC3_STALE_STATE_BLOCK` | `'1'` | 0 | no-op 之后拒绝下一个动作（见 §3） |
| 世界模型 | `ARC3_MEMORY_SECTIONS` | `'off'` | "" | 关掉 world-model 区块（并改写相应 prompt） |
| 持久函数 | `ARC3_PERSISTENT_FUNCTIONS` | `'1'` | False | 跨 snippet 保留函数定义 |
| | `..._SCOPE` | `game` | - | 保留到整局结束 |
| | `..._IMPORTS` | `'1'` | False | 允许保留 import |
| 控制 | `EXPOSE_UNDO` | `on` | tufa | 把 ACTION7 作为 **UNDO** 广告且执行 |
| 调度 | `ARC3_MAX_ACTIVE_STREAMS` | **10** | 0(off) | 准入槽数（§6） |
| | `ARC3_PRIORITY_REFRESH_QUEUE` | `'1'` | False | 每次释放槽时重算等待者优先级 |
| | `ARC3_PRIORITY_PACE` | `'0'` | False | 关闭“进度配速”折扣 |
| | `ARC3_PRIORITY_TAIL_FADE` | `'1'` | False | 最后 20% 墙钟淡出“未来关卡”价值 |
| | `ARC3_PRIORITY_TAIL_FADE_FRACTION` | `'0.2'` | "" | = 0.2×532min ≈ 最后 **106 分钟** |
| | `ARC3_PRIORITY_TAIL_LOOKUP` | `remaining` | "" | 用 8/7/5/0 的启发式 tail 表（part03 L39–41） |
| | `ARC3_PRIORITY_SCORE_NORMALIZATION` | `'1'` | False | 把“当前关价值”归一到 10 关参考（part03 L110–113） |

cell 4 里还有 4 个**不走 setup_env、直接写 os.environ** 的键：`ARC3_WARMUP_ACTION_GAMES=1`（第一个开跑的游戏在 analyzer 就绪前先发一次 RESET，保 15 分钟动作窗口）、`ARC3_HTTP_RETRY_INITIAL_SECONDS=900`（首个请求的宽限）、`TAAF_RUN_AS_SUBMISSION`、`TAAF_MINIMAL_DIAGNOSTICS`、`MPLBACKEND=Agg`、`ONLY_RESET_LEVELS=true`（见 §1.5）。

### 2.2 默认关闭、cell 4 也没开 ⇒ 本轮**完全无效**的机制（重要）

| 键 | 默认 | 失效证据 |
|---|---|---|
| `ARC3_NOOP_REPEAT_GUARD` | False | `self._noop_repeat_guard=None`（part07 L2933–2940）；`_action_guard_hook` 第一句 `if guard is None: return None`（L4745–4747） |
| `ARC3_DEATH_REPEAT_GUARD` | False | 同上；`_noop_guard_deaths_enabled=False` |
| `ARC3_DEATH_GUARD_LOOKAHEAD` | False | 只在死亡守卫开时有用 |
| `ARC3_DEATH_LEDGER` | False | `_death_ledger_observe` 在两者都关时**早退不记录**（L3511–3524） |
| `ARC3_REPEAT_STATE_GUARD` | False | L4836–4862 |
| `ARC3_SUMMARY_INTERVAL_TOKENS` | 0 | rolling summary 全程不触发（`_maybe_append_rolling_summary` 首行 interval<=0 return） |
| `ARC3_AUTO_FRAME_DIFF` / `ARC3_GAMEOVER_DIFF` / `ARC3_PRUNE_*` / `ARC3_RESUME_*` | 全 False/默认 | 与 cell 4 无关，均不生效 |
| `ARC3_MEMORY_SECTIONS` 之外的 world-model 子开关（`WM_REVISE_NUDGES` 等） | False | 因为 memory sections 是 off |
| `EXPOSE_RESET` | off | 模型看不到也执行不了 RESET（§1.5） |

⇒ **F89 的“5 个守卫”实际只有 3 个在跑**；REPEAT/DEATH 那一族是可用但未启用的工具。

### 2.3 其他关键非 env 配置（cell 16 / cell 12）

- `bm.n_passes = 4`（离线）；`TRUE_SUBMISSION` 强制 **`n_passes=1`**，`concurrency=120`，`max_runtime_s_per_game=532*60=31920s`（cell 16 L12–21）。`bm.solver.max_actions_per_game=None` ⇒ **没有动作数上限**，只有墙钟（和可选 token 上限，未设）。
- `bm.solver.analyzer_timeout=900`；`ARC3_MAX_ANALYZER_FAILURES`（默认 10）+ `ANALYZER_RETRY_BACKOFF_SECONDS`（patch 从 1.0 改成 **10.0**）⇒ 端点挂了会放弃该局而不是空转（part10 L57–83、L483–508）。
- SGLang（cell 12 L12–35、L275–316）：`CTX=(116+12+8)*1024=139264`、`--max-running-requests 10`、`--cuda-graph-max-bs-decode 10`、`--page-size 64`、`--chunked-prefill-size 8192`、`--max-prefill-tokens 16384`、KV `fp8_e4m3`、`NEXTN` 投机（draft steps 3）、`--reasoning-parser qwen3`、`--tool-call-parser qwen3_coder`、`--default-chat-template-kwargs '{"preserve_thinking":true}'`。
  ⇒ **服务端真正的并发生成数是 10**，这个数字和 harness 的 `ARC3_MAX_ACTIVE_STREAMS=10` 数值相同但含义不同（§6）。

---

## 3. 守卫：哪些真的会拦、拦什么、成本是 turn 还是 action

### 3.1 三个真正生效的守卫

**(A) `ARC3_GUARDS_FROM_LEVEL=2`（`_guards_active`）**
只决定“per-action 拦截从第几关开始”。cell 4=2 ⇒ **第 1 关不拦、只观察**（part07 L4748–4758：第 1 关仍然 `note_level` + 算 hash，只是不拒绝）。第 2 关起 (B)/(C) 的 no-op 判定才可能拒绝动作；**`BATCH_NOOP_BLOCK` 不受它控制**（solver 里注释明确：“The batch no-op stop is deliberately NOT covered ... a wrong movement model is exactly as expensive on level 1 as anywhere”，part10 L124–142）。

**(B) `ARC3_BATCH_NOOP_BLOCK=1`（批内 no-op 截断）**
- 判定：`_interior_gameplay_changed(prev, new, border=4)`（part10 L254–279）——**只看离边框 4 格以外的格子**；只有边框内（HUD/计时条）变 ⇒ `gameplay_changed=False`。
- 行为（part10 L631–638）：**`batch_size >= 2`** 且某个已执行动作 `gameplay_changed=False` ⇒ `stop_reason="no_op_action"`，**该动作已经执行、已经计 1 个动作**，只是批里后续动作不再执行。
- 会不会拦合法动作：**不拒绝任何动作**，只会把“本来想接着做”的后半批变成 `SKIPPED`。风险是**误判**：如果某游戏的合法效果恰好只落在边框 4 格内（或只在中间动画帧里），就会被当成 no-op ⇒ 批被截断。代价 = 一次额外的 tool/turn 往返；**不消耗额外引擎动作**。
- 附带信息：payload 里有 `no_op_action_index`、`action_trace`、`stop_detail`（part10 L690–716），模型能看到“只有前 N−1 个动作改变了盘面”。

**(C) `ARC3_STALE_STATE_BLOCK=1`（no-op 之后拒绝下一个动作）**
- 触发链：sandbox 里 `action()` 收到 `gameplay_changed is False` 且 `executed` ⇒ 记 `_stale_state=[动作名]`（part05 L307–324）；**下一次同一 snippet 里的 `action()`** 把 `stale_after` 传给 host（part05 L250–257）；`solver.step_env` 在**第 1 个动作**上判定（part10 L546–623）：
  - 如果新动作 == 刚才 no-op 的那个动作 ⇒ 先走 stale 分支（更具体的提示）；
  - 否则先过 guard_hook（此处没开⇒None），然后**仍然走 `if stale_after and batch_index == 1:` 分支并拒绝**。
  ⇒ **拒绝的是“该 snippet 内 no-op 之后的第一个动作”，不论它是不是重复动作、是否合法。** 抛 `StaleStateActionError`（**可捕获的普通 Exception**，part05 L198–204）。
- 为什么会“自愈不了”：`_stale_state` 只在 ① 新的 snippet 执行（closure 重建，part05 L210–212）或 ② 某次 `gameplay_changed=True` 时清空。**在同一个 snippet 里 catch 之后重发还是被拒**（stale_after 依旧随每次 `action()` 发送）。⇒ 实际效果 = **每个落到 no-op 的动作，强制把该 snippet 结束在下一个动作之前**；模型必须换一个 snippet（同一个 analyzer turn 里可以再调工具，所以成本是 1 次 tool 往返，而不是必然 1 个 turn）。
- 会不会拦合法动作：**会**（不同动作也会被拒一次），但只要换新 snippet 就能执行；**不消耗引擎动作**（拒绝不执行、不计分）。代价是生成/往返。
- 第 1 关（`GUARDS_FROM_LEVEL=2`）不受影响。

### 3.2 已实现但**关闭**的守卫（可作为确定性提分候选，见 §8）

- `NoopRepeatGuard`（part01 全文）：按 `(level, 整帧 hash, 动作签名)` 记录“已证明不改变盘面内”的 `(state, action)`，**执行前拒绝** ⇒ **不花引擎动作**；可“立刻重发同一动作”覆盖一次（防自锁死），第三次再拦。已知缺陷（docstring 自述）：动作效果若只出现在**中间动画帧**（被拒绝的点击、回弹）就看不出来，会被误记；整帧 hash 包含 HUD 已经降低误判。
- `DeathRepeatGuard` + death ledger（part07 L3410–3524、L4696–4865）：记录每次 GAME_OVER 的 `actions[]` 与**每个动作执行前的整帧 hash**，用 `(hash, action)` 反查；再从同一 hash 重放**同一条致命前缀**时，**在执行第一个动作前就拒绝整批**（`ARC3_DEATH_GUARD_LOOKAHEAD` 打开时）；不落 lookahead 时只拦 offset 0。逻辑建立在“环境确定性”上（补丁注释自己引用了官方文档），因此**误拦的概率理论上极低**（要同整帧 hash + 同动作 + 这次却不死）；节省 = 致命动作 1 个 + 自动 RESET 1 个 = **2 个引擎动作**，还避免重开一关。
- `RepeatedActionInStateError`（part05 L195–196 / part07 L4836–4862）：snippet 内“从同一盘面再跑同一动作”拒绝，直接针对死循环类代码（“20–30 个白给动作”）。属于 `ARC3_REPEAT_STATE_GUARD`，默认 False。

### 3.3 什么时候“丢关键信息”而不是“拦动作”

- `gameplay_changed=False` 但 `board_changed=True` 时：守卫认为“只有边框变”，而 `_action_verdict` 会给出 NO-OP；模型可能据此放弃一条正确路线（幻觉性否定）。cell 4 开了 `ARC3_NEW_CHANGED_PROMPTS/EXPLAIN_GAMEPLAY_CHANGED` 正是为了把措辞改准确（“no change inside the board area”）。
- `BATCH_NOOP_BLOCK` 只在 `batch_size>=2` 生效 ⇒ 单动作探测永远不受影响；模型把“探测”拆成单动作即可绕开（prompt 里没有教这件事，除了 stop_detail 的说明）。

---

## 4. 动作批处理与“一个动作算几次”

- 一个 batch 在 `step_env` 里**逐个**执行（part10 L545–638）：每个执行的动作 → 1 次引擎 `step` → scorecard `take_action` +1（RESET 走 `reset` +1）。
- **refuse 的动作（known_noop/known_death/stale_state/repeated/invalid）0 次**：不执行、不计分、不计动作，**也不增加 harness 的 `action_count`**（`action_count` 只在真正执行的路径上递增；refuse 在 `step_env` 里直接 `return`，不经过该路径）。
- 批内提前停的三种原因：`should_stop()`（预算/run 结束/WIN）、`level_completed`、`BATCH_NOOP_BLOCK` 的 no-op。停在 level/win 时不执行后续动作。
- `_execute_auto_reset`（GAME_OVER 后）是**额外** 1 个动作，带 `automatic=True` 标记；它不会被当成模型动作，但**会记进 scorecard 的 actions 和 resets**（§1.2）。
- `action echo`（`ARC3_ACTION_ECHO=1`）只是把一行裁决打到 snippet stdout；`action_trace`/`gameplay_changed_per_action` 只在 batch>1 或死亡/被拒时生成（part10 L667–680）。**都不重复计分。**
- `LOCAL_ANALYZER_TOOL_STEPS=0` ⇒ 一个 analyzer turn 内可以连续多次 `action()`（受 `YIELD_TOKENS=2048` 累计生成量约束），每次 `action()` 的每个执行动作各计 1。

---

## 5. 上下文裁剪 / yield：什么时候丢有用信息

### 5.1 裁剪的锯齿带

- 估算器：`_estimate_tokens` 用字符/`chars_per_token`（默认 3，**会用服务端 `usage.prompt_tokens` 在线标定**，clamp 在 1.0–3.3，part07 L2651–2708、L5184+）。图片按真实 vision token 计：`ceil(w/32)*ceil(h/32)+2` ⇒ 640×640 → **402 token/张**（part07 L2645–2764）。
- 触发：`estimated > budget`；`drain = min(ARC3_CONTEXT_DRAIN_TOKENS, budget//2)`，`target = budget - drain`（part07 L5674–5680）。
  cell 4：window 128k、max_output 12k ⇒ budget≈116k（[推断：`_context_budget_tokens` 在未打补丁的原函数里，看不到）；drain 请求 58k 被 clamp 到 ≈58k ⇒ **一次裁剪从 ~116k 直接砍到 ~58k**。
- 顺序：`_persistent_history_messages`（part07 L5520–5557）：控制消息剪枝 → 图片窗口 → token 裁剪 → assistant 条数上限（150 / drain 30 / coalesce）→ 保证 history 以 user 开头。
- 后果：**首剪约在 30–50 turn**（gate 注释自己测量的，part07 L2002–2003），此后大约每 **12–15 turn** 再剪一次（每 turn 约 4–5k token）。被剪掉的是**最早的整块历史**；如果关键发现只写在早先的 assistant 文本里、没有进 world model（`MEMORY_SECTIONS=off`！）⇒ **永久丢失**。`MEMORY_SECTIONS=off` + `summary` 关闭 ⇒ **这个 harness 没有任何长期记忆补偿**，全靠 prompt 里的“重新观察”和持久函数（只保留函数定义，不保留数据）。
- `ARC3_HISTORY_ASSISTANT_TURNS=150` 在 116k 预算下几乎不可能先触发（≈25 turn × ≤3 assistant 消息 < 150）**[推断]**；真正 binding 的是 token 带。
- `ARC3_MIDDLE_TRUNCATION=1`：**工具输出**（stdout/error/result）超过 `tool_output_chars`（由 `TOOL_OUTPUT_TOKENS=3072` 决定）时保留头 2/3 + 尾 1/3；`error` 的尾部（`SomeError: 解释`）和 stdout 尾部的“行动后状态”因此保住，但**中段（通常是逐条检查的列表）会被丢**。若模型把关键证据打印在输出中段，会看不到——这是“合法信息丢失”而不是拦截。

### 5.2 yield / 单请求成本

- `YIELD_TOKENS=2048`：**每 turn 累计生成 ≥2048 token 就 yield**（`control_yield_reason`，part07 L5894–5904），下一请求以 resume prompt 继续（`ARC3_YIELD_RESUME_PROMPT/TONE` 默认 `""` ⇒ 标准措辞）。这是“turn 的切块大小”。
- **`MAX_OUTPUT=12288` 是单次请求的硬上限**：yield 检查发生在**请求之间**，不能截断一次请求内部的思考。因此单次动作的最坏生成成本是 12k token（thinking 全算在里面）。这是“每动作成本”的唯一天花板开关。
- 每 turn 的固定 prefill 增量：opener（状态行+action trace+提示）≈1–2k 文本 token + 1–2 张图（402–804）+ tool 定义（在 system 里，前缀缓存命中）；历史越长 prefill 越贵，但有 paged prefix cache（page 64、chunked prefill 8192）。
- 每动作真正的墙钟成本 ≈（单请求生成 token / 有效 decode 速度）+（新 prefill token / prefill 速度）。10 条流共享一块 GPU ⇒ 有效 decode 速度 ≈ 单流 1/10 左右（F88 的 ~890 token/动作是在“预算被共享”的前提下反推的）。

---

## 6. 调度：那两个“10”不是同一个 10

### 6.1 harness 侧 `_PriorityGate`（part07 L1856–2026；solver part10 L419–459；handover 在 part07 L5579–5624）

- `ARC3_MAX_ACTIVE_STREAMS=10` ⇒ 进程级 `_PriorityGate(10)`：**同时最多 10 个 game session 持有“槽”**。槽在 `play()` 开始时 `gate.acquire(_PRIORITY_UNTRIMMED_BASE - game_index*100 - pass_index)`。
- **槽只在“该游戏第一次上下文裁剪”时移交**：`_maybe_handover()` 由 `_note_history_evicted()` 置位的 `_context_was_trimmed` 触发（part07 L5579–5624、L5514–5518），然后 `gate.handover(estimate, snapshot)` = 释放并**立刻重新竞争**（可能马上赢回来）。
- 优先级数值：未裁剪游戏 `_PRIORITY_UNTRIMMED_BASE - queue_position` = **≈2,000,000 − (game_index*100+pass_index)**；裁剪后的游戏 `priority_value()` 量级只有 **~10²–10³**（part03 L86–140，`max(1, int(value))`，value≈(a+b)·c·100）。中间还有一个 `_PRIORITY_BAND=1,000,000` 用于“本次请求付了 prefill ⇒ 掉到底带”。
  ⇒ **未裁剪游戏永远优先于已裁剪游戏 ⇒ 首段严格按 `game_index` 顺序（FIFO）**；每个游戏先拿到一段“首跑”（到首剪为止），全部轮过之后才进入按优先级竞争的第二阶段。
- 首段长度 ≈ 30–50 turn（补丁自己的测量），110 个游戏 / 10 槽 ≈ 11 波；若每段 ~5–8 分钟，**~1–1.5 小时把所有游戏喂一遍**（数量级推断，不是测量）。
- 第二阶段：`priority_value` = 深度优先（a = level×efficiency，b = 未来关卡价值，c = 动作/ token 衰减），带 **`TAIL_FADE`：最后 0.2×总墙钟 ≈ 106 分钟**把 b 淡出 ⇒ 末期只看“再通这一关值多少”。
- `ARC3_PRIORITY_PACE=0`（关）、`ARC3_PRIORITY_TAIL_LOOKUP=remaining`（8/7/5/0 启发式表）、`SCORE_NORMALIZATION=1`（按 10 关归一）。
- ⇒ F89/F88 的“某些游戏 0 动作/缺关”机制上更像：**所有游戏都会拿到首段，然后“卡在浅层 + 动作多”的游戏在第二阶段优先级最低，被饿死**；而不是“从头就没轮到”。（F88 里 `[13,94,0,0,…]` 也符合“同局后段被预算切断”。）**[推断；需要 request log/调度模拟器验证]**

### 6.2 服务端侧 `--max-running-requests 10`（cell 12）

- SGLang 同一时刻最多 **10 条生成请求**；`--chunked-prefill-size 8192`/`--max-prefill-tokens 16384` 决定 prefill 分块。
- gate 的 10 个“槽”是**游戏级**的：一个持槽游戏在 Python sandbox 里跑代码时**不占 GPU**，但会把槽占着。⇒ gate=10 时，服务端**平均并发请求数 < 10**（取决于 sandbox 占比）；把 gate 放宽到 20–25 不会超过服务端 10 条并发生成，但能让服务端队列里始终有就绪请求、**把“游戏侧的空转”填掉**，同时让第 11 名之后的游戏更早拿到首段。
- 这也解释了为什么“10 vs 25”是一个**独立理由充分但方向未知**的实验：它改变的是 GPU 占空比与调度顺序，不是模型能力。

---

## 7. 建议改动（按“机制确定性 × 风险”排序；最多 5 条可上手）

> 统一约束：**都只改 cell 4 `setup_env` 里的一个值，不新增 cell、不改代码** ⇒ 代码路径崩溃风险≈0（F92 那次 0.00 来自新增一个 monkeypatch cell，不是 env 值）。但 **Save 跑通仍然不能证明比赛重跑跑通**（F92），每条都保留“方向风险”。

### R1（推荐第一枪）`ARC3_DEATH_REPEAT_GUARD=1`（可再加 `ARC3_DEATH_GUARD_LOOKAHEAD=1`）

- 机制：开死亡守卫 ⇒ `_NoopRepeatGuard` 被创建（part07 L2933–2940）⇒ `_death_ledger_observe` 开始记录（L3511–3524）⇒ `_action_guard_hook` 在**每个动作执行前**用 `(整帧 hash, 动作签名)` 查“这个动作是否在完全相同的盘面上杀死过我们”（L4735–4865）。命中 ⇒ **整批动作在执行前被拒绝**（lookahead 开时连“致命前缀”一起拦），**不消耗引擎动作**，并给模型一条明确提示；模型“立刻重发同一动作”可覆盖。
- 默认/现状：默认 `False`；cell 4 **没有**设置 ⇒ 目前 death ledger 连记录都不做（§2.2）。
- 预期方向：每拦一次省 **2 个引擎动作**（致命动作 + 自动 RESET）并避免重开一关；直接影响“每关动作数”和“能否在预算内推进”。**若线上用 RHAE，这是直接乘进 `(baseline/actions)^2` 的；若用 levels 口径，是省预算** ⇒ 两种口径都不吃亏。
- 误拦条件（理论上）：同一整帧 hash + 同一动作 + 这次却不死 ⇒ 需要环境不确定（官方说是确定性的）或整帧相同但隐藏状态不同。补丁默认用**整帧**（`ARC3_STATE_IDENTITY_BORDER=0`）而不是裁边 hash，正是为了避免 HUD 差异被当成“同状态”**[这点很重要，别去开 STATE_IDENTITY_BORDER]**。
- 线上风险：**崩溃 LOW**（env-only + 补丁内部已把 `KnownDeathActionError` 显式放进 sandbox 的 except 列表，part05 L468–482）；**方向 LOW–MED**（真的会改变模型行为；但逻辑上只会拦“已证死”的动作）。
- 离线可验证：**可以**（公开 25 个游戏里死亡是常态）。但注意 §1.5：离线 `ONLY_RESET_LEVELS=true`，线上不一定 ⇒ Save 只能证明“不崩 + 动作数变化方向”。
- 备注：`ARC3_GUARDS_FROM_LEVEL=2` ⇒ **第 1 关不受死亡守卫保护**（第 1 关死亡最便宜，作者的选择是合理的）；如果想从第 1 关就保护，把它设为 1（但同一天也会让 no-op 类守卫在第 1 关生效，副作用变大）。`ARC3_DEATH_GUARD_LOOKAHEAD` 打开会把“致命前缀”整批拦下（省更多动作，但如果模型故意想走前缀再变道，会被劝退一次）。

### R2 `ARC3_MAX_ACTIVE_STREAMS` 10 → 20/25（已有现成 kernel：`arc-exp-streams25`，与基线**只差这一行**）

- 机制：见 §6。10 个 gate 槽对应 SGLang 的 10 条并发上限，但槽被 sandbox 阶段空占；放宽 ⇒ 服务端请求队列常年饱和 + 后段游戏更早开始。
- 默认/现状：patch 默认 0=关闭 gate；cell 4=10。
- 预期方向：**更多总动作数**（→ 更多关卡）。但可能：前缀缓存抖动、每个游戏更浅、调度顺序改变后“该深的没深”。
- 风险：**崩溃 LOW**；**方向 MED**（这是纯吞吐假设，不是逻辑必然）。
- 离线可验证：**可以但弱**（离线 25 游戏×4 轮，本身就有 100 条流，gate=10 的影响与线上 110 条流不同——F91 已指出这一点）。

### R3 `LOCAL_ANALYZER_MAX_OUTPUT` 12288 → 4096（现成 kernel：`arc-exp-out2048` 是 2048）

- 机制：**单请求**硬上限；yield 只在请求之间检查，所以 12k 的最坏思考成本只能由它压。按 F88 的预算模型，降上限 ⇒ 同样墙钟内更多动作。
- 默认/现状：模块默认（F88 记录 12×1024）；cell 4=12288。
- 预期方向：动作数 ↑；但 `finish_reason=length` 会丢掉一次工具调用/一条计划 ⇒ 关卡数可能 ↓。
- 风险：**崩溃 LOW**；**方向 MED–HIGH**（直接压模型棋力）。
- 离线可验证：**可以**（看同一批游戏的动作数/通关数变化），但方向不能外推。

### R4 `ARC3_STALE_STATE_BLOCK` 1 → 0（或 `ARC3_GUARDS_FROM_LEVEL` 2 → 3/4）

- 机制：见 §3.1(C)。它**不省任何引擎动作**，只把“no-op 之后的第一个动作”变成一次 tool 往返 + 一次重读；若某游戏因“只改边框”被频繁判成 no-op，则每个动作都被迫换 snippet，吞吐明显下降。`GUARDS_FROM_LEVEL` 提高则把这种开销推迟到更深的关卡。
- 默认/现状：patch 默认 0；cell 4 = 1（2/3 都是 notebook 作者的选择，作者是 34.30 的作者，**改动等于否定他的调参**）。
- 预期方向：减少确定性开销 ⇒ 动作数 ↑；代价是模型可能基于错误位移继续行动 ⇒ 浪费动作。
- 风险：**崩溃 LOW**；**方向 MED**（对称的不确定）。
- 离线可验证：**可以**（计数 `stop_reason=stale_state` 的次数与动作数）。

### R5 `ARC3_NOOP_REPEAT_GUARD=1`（与 R1 共享 store；建议**先 R1 加了、观察到死亡守卫稳定后再加这个**）

- 机制：已证明 no-op 的 `(整帧, 动作)` **执行前拒绝**，不花动作，可重发覆盖。
- 预期方向：省掉“重复探测同一个死动作”的动作（RHAE 口径直接涨效率；levels 口径省预算）。
- 风险：**崩溃 LOW**；**方向 MED–HIGH**——补丁 docstring 自己写了已知缺陷：效果只在中间动画帧出现的动作会看不出变化 ⇒ 被误记；而 cell 4 的 `ARC3_ANIMATION=1` 反而**帮助**模型看到中间帧，但**不帮助守卫**（守卫只看首尾帧）。所以第 1、2 个踩坑的可能是“合法的隐藏状态动作”。
- 离线可验证：**可以**（记录 `stop_reason=known_noop` 与随后是否被“重发覆盖”）。

### 不要做（有明确机制/证据反对）

| 想法 | 反对理由 |
|---|---|
| 打开 `EXPOSE_RESET` | 模型可发 RESET；若线上 `ONLY_RESET_LEVELS=false` 则“关卡起始 RESET”会 full_reset 丢光已通关卡（§1.5/§1.6）。且手动 RESET 只花动作不回血。 |
| 提高 `ARC3_STATE_IDENTITY_BORDER` | 会把 HUD 不同的盘面当同一状态，让死亡/no-op 守卫**误拦**（part07 L286–302 的注释就是为了这个默认 0）。 |
| 依赖 `ONLY_RESET_LEVELS` 做任何线上结论 | 它在 gateway 进程读，notebook 设置无效（§1.5）；而且它会让离线本地 scorecard 变成空账（§1.6）。 |
| 再写 “优先级公式” cell（dprime/ours 类） | 已实测 0.00（F92）；且它改的正是 25 vs 110 游戏生命周期这一维度。若真要动调度，**只用 env 值**（R2/R4）比换公式安全一个量级。 |
| 打开 `ARC3_MEMORY_SECTIONS` / summary | 每动作 token 成本上升，与 F88 的“预算而非智力”结论相冲；且默认关。 |
| 提交时改 `n_passes` | cell 16 在 `TRUE_SUBMISSION` 分支**强制 1**；要改就得改代码，且每 game 的 play 语义/预算会变。 |

---

## 8. 对既有 findings 的修正 / 待验证

1. **F89 的“完整可调面板”应加一列“是否真的生效”**：`NOOP_REPEAT_GUARD`/`DEATH_REPEAT_GUARD`/`DEATH_LEDGER`/`REPEAT_STATE_GUARD` 四个在 cell 4 里**不存在** ⇒ 默认 False ⇒ 死代码路径。F89 把“守卫 2/1/1”当成三个都活着，实际上只有 3 个非 repeat 守卫活着，而 repeat 家族是**还没试过的工具**（这反而是新信息）。
2. **F88 的“预算而非智力”在机制上更精确的版本**：每动作成本 ≈（单请求生成 token / 有效 decode 速度）；两个真正能压成本的旋钮是 `LOCAL_ANALYZER_MAX_OUTPUT`（单请求天花板）和 `LOCAL_ANALYZER_ENABLE_THINKING`（乘数）；`YIELD_TOKENS=2048` 不是成本开关而是**切块**（切太细 = 更多 resume 往返，切太粗 = 一个 turn 占着模型更久）。F88 的 H2（2048）方向对，但它没指出“yield 在请求之间检查”这个关键约束。
3. **F91 “调度优先级是杠杆”**：机制存在（§6），但 **dfranzen 的公式本身就是深度优先**；如果公榜口径是“关卡比例”（每关等权），**深度优先可能不是最优，breadth-first（优先把只过了 0–1 关的游戏推到第 1–2 关）在分数上更划算**——因为 level 1 最便宜而每关等值。这条**没有被任何已试改动覆盖**（dprime 也是深度族），值得交给调度模拟器（task-3）验证，而不是再花一次抽样。
4. **F92 的新机制补充**：除了“Save ≠ 重跑”的并发/游戏数维度，本文给出第二条 **确定性**差异：`ONLY_RESET_LEVELS` 只在 notebook 进程（离线）生效，线上由 gateway 决定；因此所有“死亡/重置后关卡保留”相关的离线观察都不能直接外推。
4b. **已验证**：同一 flag 还让本地 `arc_agi` scorecard 变成空账（§1.6 实验 2）⇒ 用 notebook 环境跑“官方计分器”离线标定会**静默得到 0**。如果谁要做分数向的离线 A/B，要么用 `tools/score_local.py`（不加载 notebook env），要么在探针里把 `ONLY_RESET_LEVELS` 去掉；**不要混用 benchmark.json 的关卡数与 scorecard 的 RHAE 分**（两套账）。
5. 待验证（缺 taaf 源码）：`just_won_level` 的精确语义；taaf 是否在 WIN 后再发 RESET（影响 §1.2 的单 play 归零风险）；`bm.run` 的 soft deadline 在线上是否为 None（影响 `TAIL_FADE` 的 deadline 计算）；`LOCAL_ANALYZER_TOOL_STEPS=0` ⇒ `None` 的语义（推断=不限，但原 turn loop 在未打补丁的代码里，看不到）。

---

## 9. 复现命令

```powershell
# 1) 拆 cell / 拆 patch（已生成到 arc/internals/_work）
python D:\kaggle\arc\internals\_work\cells.py
python D:\kaggle\arc\internals\_work\split.py
python D:\kaggle\arc\internals\_work\knobs.py             # 116 个 ARC3_*/LOCAL_*/EXPOSE_* 常量
python D:\kaggle\arc\internals\_work\table.py             # cell4 vs 模块默认 对照表（→ knobtable.txt）
# 2) 行级阅读（每个结论的引用都在这些文件里）
#    _work/patch_parts/07__*tool_agent.py   ← 守卫/调度/裁剪/提示词
#    _work/patch_parts/10__*solver.py       ← level_completed / batch / auto-reset / gate
#    _work/patch_parts/{00,01,03,05}.py     ← action 名/守卫实现/优先级公式/sandbox 异常
# 3) 引擎与计分器（只读 site-packages）
python -c "import arcengine, arc_agi, inspect; print(arcengine.__file__); print(arc_agi.__file__)"
# 4) 两个本机验证探针（§1.6；只写 _work/ 下的 recordings）
$py = 'D:\kaggle\arc\starter\.venv\Scripts\python.exe'
& $py D:\kaggle\arc\internals\_work\engine_probe.py  true     # RESET 语义
& $py D:\kaggle\arc\internals\_work\engine_probe.py  false
& $py D:\kaggle\arc\internals\_work\offline_probe.py true     # 本地 scorecard 是否记账（true ⇒ 空账）
& $py D:\kaggle\arc\internals\_work\offline_probe.py false
```

> 边界：本文没有修改、也没有提交任何东西；没有读/写 `arc-agi-3-ledger/` 与 `rsna-knee/` 的内容（只读取了 `arc-agi-3-ledger/findings/` 的既有结论用于交叉核对）。
