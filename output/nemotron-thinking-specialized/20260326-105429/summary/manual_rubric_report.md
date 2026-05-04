# Nemotron Thinking Manual Rubric Report

## 直接结论

- 我人工复核了 9 组专项题输出，结论和自动指标一致：
  - `thinking=true` 的答案通常更长，但**总质量没有更高**
  - 总分：`94 vs 85`
  - `thinking=false` 更好：`5` 题
  - `thinking=true` 更好：`3` 题
  - 持平：`1` 题
- 所以“长答案是不是其实更好”这件事，在这轮数据上结论是否定的：
  - **更长不等于更好**
  - 在 Nemotron 这组任务里，更长更常见地意味着“内部分析过程被显性化了”，而不是“最终决策质量明显提升”

## 评分口径

每题都按同一套人工 rubric 打分：

- `task_completion`：是否命中题目的核心问题与目标，`0-4`
- `evidence_grounding`：是否真的基于给定快照和日志收敛，而不是泛化推测，`0-4`
- `constraint_adherence`：是否遵守“最小变更 / 不发明接口 / 不漂移主线”等约束，`0-4`
- `decision_completeness`：最终方案是否足够可执行、顺序清楚、验证点完整，`0-4`
- `penalty`：幻觉、明显跑题、协议污染等，`0 到 -3`

满分 `16`。

完整明细在：
- [manual_rubric_scores.json](/Users/luo/Documents/github/CodexGame/output/nemotron-thinking-specialized/20260326-105429/summary/manual_rubric_scores.json)

## 结果拆解

### 1. `longctx`

- `thinking=false`：`33`
- `thinking=true`：`28`

这是差距最清楚的一组。

- `longctx_restore_bootstrap`
  - `thinking=false` 更好
  - 原因：直接命中 `phase=running` 早于 thread bootstrap 的错序，方案收敛快
- `longctx_metrics_contract`
  - `thinking=false` 更好
  - 原因：虽然也有过度推断，但至少给出了明确 contract gap；`thinking=true` 更像边看边想，收敛更差
- `longctx_java_change_impact`
  - 持平
  - 两边都只命中了一半：都看到了 side-effect 风险，但一个方案偏大，一个方案偏错位

结论：
- 在长上下文分析里，`thinking=true` 主要增加了篇幅
- 它没有把问题识别得更准，也没有把修复边界收得更好

### 2. `multi_round`

- `thinking=false`：`28`
- `thinking=true`：`23`

这一组最能说明“多轮输出更长，不代表更会自我修正”。

- `multi_restore_self_repair`
  - `thinking=true` 更好
  - 原因：它最终至少回到 `threadIds/threadToAgentId` 这个 restore 主线上
- `multi_outbox_self_repair`
  - `thinking=false` 更好
  - 两边都不理想，但 `thinking=true` 最终没有收敛成一个可执行的最小 patch
- `multi_reconnect_self_repair`
  - `thinking=false` 明显更好
  - `thinking=false` 直接收敛到“successful reconnect 后 reset reconnectAttempts”
  - `thinking=true` 则漂到 `pendingTurns` / stale state，偏离题目主线

结论：
- 多轮修复并没有因为 `thinking=true` 而展现更好的“自我修正能力”
- 更常见的是它把中间分析过程说了出来，但最后 patch plan 反而更散

### 3. `planning`

- `thinking=false`：`33`
- `thinking=true`：`34`

这是唯一一个 `thinking=true` 没吃亏的 family，而且略有优势。

- `plan_boot_restore_gap`
  - `thinking=true` 略好
  - 原因：对 failure handling、thread recreation、pending state 的覆盖更完整
- `plan_metrics_exposure`
  - `thinking=false` 略好
  - 原因：结构更干净，完全按 protocol -> runtime -> client -> tests 展开
- `plan_reconnect_fault_injection`
  - `thinking=true` 略好
  - 原因：harness / injector / observability 三段式更贴题

结论：
- `thinking=true` 的价值主要体现在**规划型任务**
- 但这个优势非常有限，只有 `+1`
- 它远不足以抵消在 `longctx` 和 `multi_round` 上的损失

## 为什么“更长”没有变成“更好”

这轮人工复核后，模式很稳定：

- `thinking=true` 更常做的是：
  - 把中间分析过程写出来
  - 把不确定性也显式说出来
  - 在进入最终 patch / final plan 之前先走一段 narrative

- 但真正决定质量的几个点并没有同步提升：
  - 是否命中题目真正的 hidden focus
  - 是否保持最小变更
  - 是否不发明额外接口/文件/约束
  - 是否在最终答案里真正收敛

所以这里的问题不是“输出短，所以差”；而是：
- `thinking=true` 增加的新增 token，大部分没有转化成更高密度的有效决策

## 与 `--reasoning-format none` 的关系

这个变量**有影响**，但不是这轮主结论的根因。

影响在于：

- 当保留 `--reasoning-format none` 时，`thinking=true` 会更容易把内部草稿污染到 `content`
- 这会让表面观感和输出契约变差

但我这轮人工 rubric 看的不是 raw `content` 污染本身，而是抽取后的最终答案质量。  
即便把这个因素剥开看，结论仍然成立：

- `thinking=true` 的主要增益只在少数 planning 题上出现
- 在大多数题上，它仍然只是更长，不是更强

所以更准确的判断是：

- `--reasoning-format none` 会让 `thinking=true` **看起来更差**
- 但即使不把这个因素算进去，`thinking=true` 也**没有证明自己默认值得开启**

## 最终建议

- Nemotron 当前默认配置继续保持：
  - `enable_thinking=false`

- 如果要继续研究 `thinking`，只建议放在：
  - `parser enabled`
  - `analyst / planning profile`

- 不建议把 `thinking=true` 作为这台 4090 上 Nemotron 的默认执行配置，原因很简单：
  - 自动指标没有显示明显收益
  - 人工 rubric 也没有证明“长答案其实更好”
  - 反而更容易带来输出膨胀和收敛变差
