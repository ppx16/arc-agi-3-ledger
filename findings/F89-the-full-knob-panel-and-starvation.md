# F89 — 完整可调面板（`setup_env`），以及"为什么有的游戏一个动作都没做"的最可能答案

写于 2026-10-22。来源：`ppxl16/arc-agi-3-m2-franzen-verbatim` 的 **cell 4**，一个显式的 `setup_env` 字典。
之前我以为这些是散落的 `os.environ[...]` 或模块默认值 —— **不是**：**cell 4 的字典就是总开关**，模块默认值大多被它覆盖
（例如温度模块默认 0.6，这里设成 **0.7**）。

## 1. 面板（原样，未改动）

| 组 | 键 | 值 |
|---|---|---|
| serving | `LOCAL_ANALYZER_MODEL_ID` / `_PROVIDER` | 本机 vLLM，端口 8001 |
| 分析器 | `LOCAL_ANALYZER_ENABLE_THINKING` | **true** |
| | `LOCAL_ANALYZER_TOOL_STEPS` | **0** |
| | `LOCAL_ANALYZER_YIELD_TOKENS` | 2048 |
| | `LOCAL_ANALYZER_TEMPERATURE` / `TOP_P` / `TOP_K` | **0.7** / 0.95 / 20 |
| 上下文 | `LOCAL_ANALYZER_CONTEXT_WINDOW` | 128k |
| | `LOCAL_ANALYZER_MAX_OUTPUT` | **12 288** |
| | `ARC3_CONTEXT_DRAIN_TOKENS` | 58k |
| | `ARC3_HISTORY_ASSISTANT_TURNS` / `_DRAIN` | 150 / 30 |
| 工具输出 | `LOCAL_ANALYZER_TOOL_OUTPUT_TOKENS` | **3072** |
| 提示词 | `ARC3_NEW_CHANGED_PROMPTS` / `_LEVEL_TRANSFER_GUIDANCE` / `_FRAME_DIFF_HINT` / `_EXPLAIN_GAMEPLAY_CHANGED` | 全开 |
| 视觉 | `MULTIMODAL_CONTEXT` / `MULTIMODAL_UPSCALE` / `ARC3_DIFF_IMAGE` / `ARC3_ANIMATION` | `current_grid` / 10 / 1 / 1 |
| 守卫 | `ARC3_GUARDS_FROM_LEVEL` / `_BATCH_NOOP_BLOCK` / `_STALE_STATE_BLOCK` | 2 / 1 / 1 |
| 世界模型 | `ARC3_MEMORY_SECTIONS` | **off** |
| 持久函数 | `ARC3_PERSISTENT_FUNCTIONS` / `_SCOPE` / `_IMPORTS` | 1 / game / 1 |
| 控制 | `EXPOSE_UNDO` | on |
| **调度（优先级开时追加）** | **`ARC3_MAX_ACTIVE_STREAMS`** | **10** |
| | `ARC3_PRIORITY_REFRESH_QUEUE` / `_PACE` / `_TAIL_FADE` / `_TAIL_FADE_FRACTION` / `_TAIL_LOOKUP` | 1 / 0 / 1 / **0.2** / remaining |

## 2. ⭐ 这解释了 F88 里那四个"零动作"的游戏

- 线上 `concurrency = 120`，注释写 *"game count should be 110"* ⇒ **110 个游戏**。
- 但队列层限制 **`ARC3_MAX_ACTIVE_STREAMS = 10`** ⇒ **同时只有 10 个游戏真正在推进**，其余排队，
  靠 `PRIORITY_*` 轮转与尾部淡出（最后 20% 预算淡出）。
- **⇒ "某个游戏一个动作都没做"不是它太难,而是它没轮到/被淡出。** 这与 `actions_per_level` 里那些 **0** 完全吻合。

## 3. 于是候选实验按"独立理由的强度"排序

| # | 改动 | 独立理由 | 风险 |
|---|---|---|---|
| **E1** | `ARC3_MAX_ACTIVE_STREAMS` 10 → **20~25** | 直接针对"被饿死"这个已观测现象（F88 的零动作） | 活跃流翻倍会摊薄每条流的吞吐，可能让所有游戏都变浅 |
| **E2** | `LOCAL_ANALYZER_ENABLE_THINKING` → false | 把每动作 token 成本降一个量级（F88） | 棋力可能崩 |
| **E3** | `LOCAL_ANALYZER_MAX_OUTPUT` 12288 → **2048** | 温和版 E2,保留思考但限长 | 长思考被截断 → 决策变差 |
| E4 | `ARC3_MEMORY_SECTIONS` off → on | "世界模型"是 ARC 的核心能力 | 每动作 token 成本上升 ⇒ 动作数变少（与 F88 相反） |

**⇒ E1 的独立理由最强**：它不是猜"更多并行更好"，而是**针对一个被观测到的失效模式**（有些游戏零动作）。

## 4. 但必须先把"标尺"和"相关性"分开谈（F87 的延续）

- **标尺精度**：基线复现（v2，进行中）给。
- **相关性**：离线 58.46 ↔ 线上 23.51/26.41 **只有一对**。要建立相关性需要多对，每对**花一次抽样**。
- ⇒ **11 次抽样里拿出 4–6 次去验证标尺是不划算的。**

**⇒ 因此本轮的策略是**：
1. 用离线只测 **1–2 个有独立理由的改动**（E1 优先），不放宽判据；
2. **最多花 1–2 次抽样**去线上验证看起来最好的那个；
3. **其余抽样照旧每天交当前最好版本** —— 因为"每天抽一次"本身就有 ~2%/次 的独立概率，不能为了做实验把它停掉。
