# F94 — 更正 F86：那次 0.00 **不是 agent 失败，是模式判定失败**；修它比提分更值

写于 2026-10-24。这条同时**撤回我自己的一个归因**，并给出剩余 8 次抽样的**保护措施**。

## 1. 我们的模式判定只有一行裸读

`cell 4`（我们的内核）：

```python
TRUE_SUBMISSION = os.environ.get("KAGGLE_IS_COMPETITION_RERUN", "").strip().lower() in {"1", "true"}
```

⇒ **评分重跑时若这个环境变量没被读到，`TRUE_SUBMISSION=False`** ⇒ notebook 走**离线演练分支**：
打捆绑的环境、写出一份"演练用"的提交 ⇒ **官方计 0.00**。
而且还伴随 `TAAF_MINIMAL_DIAGNOSTICS=0`、`target.is_competition_rerun=False` 等一连串后果。

## 2. 独立证据：另一支队在同一天踩了同一个坑

`weitaoguo/affectify-arc-dfranzen-form-d1`（**32.61**）的 cell 5 里有一段中文注释，逐字：

> *"2026-10-22 的评分 rerun 里 `KAGGLE_IS_COMPETITION_RERUN` 没被读到，笔记本走了离线演练分支，
> 只跑 1 个环境并提交'一行占位 parquet' -> 官方 0.00。判据改为：环境变量为真 OR 比赛网关可达。"*

**⇒ 而我们的 `57502063` 正是 2026-10-22 00:09 提交、**未改动任何东西的原版内核**、得 0.00。**
**⇒ 同一天、同一失效模式、同一份 harness。**

**⚠️ 因此 F86 里我写的归因（"最可能是模型服务在启动阶段失败"）应当撤回** —— 那只是我的推测，
而现在有一条更强的解释，且它附带**修复方案**。

## 3. 修复（他们的做法，我采纳）

```python
_ENV_FLAG = os.environ.get("KAGGLE_IS_COMPETITION_RERUN", "").strip().lower() in {"1", "true"}
_GW = False if _ENV_FLAG else _arc_gateway_reachable("http://gateway:8001/", total_timeout=180, step=15)
TRUE_SUBMISSION = _ENV_FLAG or _GW
print(f"[arc3-mode] env_flag={_ENV_FLAG} gateway={_GW} -> TRUE_SUBMISSION={TRUE_SUBMISSION}")
```

`_arc_gateway_reachable` 用 `urlopen` 轮询：**成功或 HTTPError 都算"可达"**（HTTPError 也证明有服务在应答）；
只有连不上才继续重试，超时则返回 False。

**为什么它安全（单向）**：
- 真·评分重跑里 gateway 一定在 ⇒ 即使 env 变量读不到，也会被判成 True ⇒ **救回一次 0.00**;
- Save&Run / 手动 push 里没有 gateway ⇒ 照旧走演练分支 ⇒ **我们自己的实验行为不变**;
- **它不改任何游戏逻辑、prompt、模型**。

**为什么超时取 180 秒而不是他们的 900 秒**：900 秒会让每次 Save 运行白白多等 15 分钟；
而评分重跑的 gateway 通常立刻就在。180 秒足够覆盖冷启动，又不毁掉实验节奏。

## 4. 它值多少（算一下）

- 观测到的 0.00 率：**2 / 20 = 10%**（`57502063` 10-22、`57579559` 10-24）。
- 其中 10-22 那次**很可能是模式判定**（本次更正），10-24 那次是 pri-dprime 的补丁崩溃（F92，另一种原因）。
- **⇒ 剩下 8 次里，模式判定失败这一类可以被这次修复消掉。**
  按 1/20 的此类失效率算，期望挽回 **0.4 次抽样**;若 10-22 那种失效在某些时段更频繁，挽回更多。
- 对比：任何"提分"改动的最好情况是把 2%/次 抬到 3%/次（+0.08 次期望）。
  **⇒ 防 0.00 的期望收益比提分高一个数量级。**

## 5. 判据（预先写下）

这次改动的验证**不靠分数**，靠日志：
- 提交后看日志里有没有 `[arc3-mode] env_flag=... gateway=... -> TRUE_SUBMISSION=...`;
- **若某次提交的 `TRUE_SUBMISSION=True`，而按旧逻辑它本该是 False ⇒ 修复当场生效**（并救回一次 0.00）;
- 若所有提交都是 `env_flag=True`（即原本就没坏）⇒ **这次修复无害，但也没证明什么** —— 要如实这么写。

⚠️ 与 F92 的关系：**任何内核改动都有 0.00 风险**（pri-dprime 就是插入代码后死的）。
本次改动**只改 cell 4 里的几行**，不插入新 cell、不动 patch，风险低于 pri-dprime，但仍非零。
**⇒ 这一抽的取舍是：拿一次抽样去换"后续 7 次的模式判定保护"。**
