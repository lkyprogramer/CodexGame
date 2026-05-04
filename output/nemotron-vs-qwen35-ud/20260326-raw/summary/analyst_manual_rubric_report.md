# Nemotron vs Qwen35 UD Analyst Manual Rubric Report

## 直接结论

- Analyst 轮我人工复核了 9 题，结论是：
  - `Qwen3.5-35B-A3B-UD-Q4_K_XL` 总分略高
  - 总分：`89 vs 82`
  - `Qwen35 UD` 更好：`6` 题
  - `Nemotron IQ4_XS` 更好：`3` 题
- 这意味着：
  - **如果你要的是更完整、更像资深工程师写出来的分析/规划文稿，Qwen35 UD 更稳**
  - **如果你要的是更快的 bounded root-cause / narrow repair 收敛，Nemotron 更有冲劲**

完整分数在：
- [analyst_manual_rubric_scores.json](/Users/luo/Documents/github/CodexGame/output/nemotron-vs-qwen35-ud/20260326-raw/summary/analyst_manual_rubric_scores.json)

## 评分口径

每题统一按这 5 项人工评分：

- `task_completion`：是否命中题目核心，`0-4`
- `evidence_grounding`：是否真的基于给定快照、日志和代码收敛，`0-4`
- `constraint_adherence`：是否守住最小变更、少发明接口、不过度设计，`0-4`
- `decision_completeness`：方案是否完整、可执行、顺序清楚，`0-4`
- `penalty`：明显跑题、幻觉、协议污染，`0 到 -3`

满分 `16`。

## family 结论

### `longctx`

- `Nemotron`: `29`
- `Qwen35 UD`: `25`

Nemotron 在这组里更好，原因很明确：

- 它更快进入“真正的 bug 是什么”
- 更少把题目扩成泛化架构讨论
- 在 `longctx_metrics_contract` 和 `longctx_java_change_impact` 上，虽然都不完美，但它至少更接近题目主线

Qwen 在这组的主要问题是：

- 容易从具体契约缺口漂到更泛的“成本、token、鲁棒性”分析
- `longctx_metrics_contract` 明显偏题

### `multi_round`

- `Nemotron`: `31`
- `Qwen35 UD`: `29`

这里 Nemotron 仍然略优，但不是碾压。

Nemotron 更好的地方：

- 在 `multi_reconnect_self_repair` 上虽然 patch 面偏大，但至少稳定守住了 `maxReconnectAttempts` 不动
- 在多轮修复里更容易给出一个“能交差”的 final patch

Qwen 更好的地方：

- `multi_restore_self_repair` 比 Nemotron 明显更准，最终收敛到了 `threadIds/threadToAgentId`
- `multi_outbox_self_repair` 的最小边界也更干净

所以这组更像：
- Nemotron 更像快速修 bug 的工程师
- Qwen 更像会多想一步、但有时收敛更慢的 reviewer

### `planning`

- `Nemotron`: `22`
- `Qwen35 UD`: `35`

这是差距最大的一组，也是最终把 analyst 总分拉开的地方。

Qwen35 UD 的优势主要体现在：

- 结构化更稳定
- 更会把方案拆成阶段、前提、失败处理、测试
- 更像“可以直接发给另一个工程师去做”的 implementation plan

Nemotron 的问题是：

- 太容易直接跳进大段伪代码或伪测试
- 会基于不可靠前提展开（例如假设缺 import、假设某方法不存在）
- 计划文稿的可执行性不如 Qwen 稳

## 两个模型在 analyst 角色上的差异

可以把这轮结果概括成一句话：

- **Nemotron 更像快刀型分析员**
- **Qwen35 UD 更像稳健型架构/计划作者**

具体表现：

- Nemotron
  - 更快
  - 更敢下判断
  - 在 bounded 问题上更容易直接给结论
  - 但在复杂规划题里更容易用“像代码、像测试”的表面具体性掩盖不可靠前提

- Qwen35 UD
  - 明显更慢
  - 但 planning 类文稿更成熟
  - 更能把协议、runtime、client、tests 这些层次讲顺
  - 更适合真正的设计评审与实施规划

## 最终 analyst 建议

- 如果是 **长上下文 root-cause / bounded repair 分析**：
  - `Nemotron IQ4_XS` 值得保留

- 如果是 **复杂规划 / 方案设计 / 实施文稿**：
  - `Qwen3.5-35B-A3B-UD-Q4_K_XL` 更适合当默认 analyst

- 如果只能选一个更稳妥的 analyst：
  - 我会偏向 `Qwen35 UD`

原因不是它全面更强，而是：
- 在真正需要“写出一个能交付给工程师落地的 plan”时，它更可靠
