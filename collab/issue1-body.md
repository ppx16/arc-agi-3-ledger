# 请求审查：ARC-AGI-3 最后 8 次提交该做什么

## 处境（事实）

- 比赛：Kaggle **ARC Prize 2026 — ARC-AGI-3**，截止 **2026-11-02 23:59Z**。
- 我们：**rank 868 / 29.34**（20 次提交）。铜线上涨至 **30.88（rank 473）**，银线 32.20。
- **每天只能交 1 次，还剩 8 次。** 分数取**所有提交的最大值**。
- 全部提交：`https://raw.githubusercontent.com/ppx16/arc-agi-3-ledger/main/state/global_watch.txt`
- 完整事实台账（F88–F96）：`https://github.com/ppx16/arc-agi-3-ledger/tree/main/findings`

## 我现在相信的两条结论（请重点攻击）

**主张 1 — 我们那两次 0.00 分源于"模式判定"失败，不是比赛打得差。**
依据：内核判断"是否比赛重跑"只用了一行裸读环境变量
`TRUE_SUBMISSION = os.environ.get("KAGGLE_IS_COMPETITION_RERUN","")...`。
若评分重跑时该变量读不到，notebook 会静默走**离线演练分支**、提交占位文件 ⇒ 官方记 0.00。
外部佐证：另一支队的公开笔记本注释记录了 **2026-10-22 同一天**同一失效模式与修复
（改为"环境变量为真 **OR** 比赛网关可达"）。
证据：
- `https://raw.githubusercontent.com/ppx16/arc-agi-3-ledger/main/findings/F94-mode-detection-was-the-zero.md`
- `https://raw.githubusercontent.com/ppx16/arc-agi-3-ledger/main/findings/F92-save-run-is-not-a-crash-check.md`

**主张 2 — 公榜分数是 RHAE = `(人类动作数 / AI动作数)²`，因此"省动作"是直接提分。**
据此我把一个**默认关闭、公开面无人启用**的机制选为下一枪：`ARC3_DEATH_REPEAT_GUARD`
——在同一盘面重放已知致死的动作**执行前就拦住**，不消耗引擎动作。每次拦截省 2 个动作
（致命动作 + 自动 RESET）。
证据：
- `https://raw.githubusercontent.com/ppx16/arc-agi-3-ledger/main/findings/F95-the-score-is-rhae-not-levels.md`
- `https://raw.githubusercontent.com/ppx16/arc-agi-3-ledger/main/team/INTERNALS.md`

## 已经排除的方向（有证据，请不要再建议）

1. **换更大的模型（27B）** —— 公开榜 33.55 / 33.22 / 32.59 三本笔记挂的模型与我们**完全相同**。
   `team/RECON.md` §1
2. **换更好的 harness 补丁** —— 27 本 ≥30 分笔记里 20 本的 498KB 补丁在排版归一化后**与我们 sha 相同**。
   `team/RECON.md` §2
3. **调度优先级（dprime 公式）** —— 已实测线上 **0.00**（提交 57579559，33 分钟出分）；
   且不含量模型的模拟器显示它**期望更差**：线上 −18.5%、离线 −11.8%、8 个敏感性场景全负、
   41/110 个游戏一次都没轮到。`findings/F96-...md`、`team/sched_sim.py`
4. **持久世界模型记忆（`ARC3_MEMORY_SECTIONS`）** —— 0/27 本公开笔记开启，
   且 harness 自己的 docstring 记录了 25 局实测的分区写入频次 ⇒ 作者是**试过并主动关掉**的。

## 明天的计划（请审这个决定本身）

把**两处改动合并**进一个内核，交明天那一次抽样：
1. **模式判定兜底**：`TRUE_SUBMISSION = 环境变量为真 OR http://gateway:8001/ 可达`（超时 180 秒）。
2. **`ARC3_DEATH_REPEAT_GUARD=1` + `ARC3_DEATH_GUARD_LOOKAHEAD=1`**。

理由：前者是**单向防御**（只可能把本该 0.00 的救回来，不改任何游戏逻辑），后者**只改两个环境变量的值**、
不插入代码；两者互不作用。

## 请回答这四件事

1. **事实错误**：上面两段事实陈述里，哪一条与证据不符？（请指明具体文件）
2. **推理跳跃**：从证据到"明天应该合并提交这两个改动"，哪一步不成立？
3. **遗漏**：这四条已排除方向之外，有没有**我们没看过的、公开可得的**证据或机制？
   （特别是：ARC-AGI-3 的官方评分规则细节——RHAE 的**具体公式、封顶、是否按关卡平均**，
   以及 RESET / 死亡是否会额外扣动作。如果你能给出官方出处，比我们的二手笔记更有价值。）
4. **更好的下一步**：在"只剩 8 次提交、每次 1 个改动"的约束下，你会把下一枪投给什么？为什么？

## 输出格式（请照这个来）

- 每条结论标注 **[事实] / [推断] / [不确定]**；
- 给链接或出处；
- 如果你认为我们的方案是对的，也请**明确说出你的置信度**，并指出最可能导致它失败的一种情形。
