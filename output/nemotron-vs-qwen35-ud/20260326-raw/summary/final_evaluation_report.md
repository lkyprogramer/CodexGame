# Nemotron IQ4_XS vs Qwen35B-A3B-UD Final Evaluation

## 直接结论

- **Executor 口径**：不建议用 `Nemotron-Cascade-2-30B-A3B-IQ4_XS` 替换 `Qwen3.5-35B-A3B-UD-Q4_K_XL`
- **Analyst 口径**：如果目标是复杂规划和高质量实施文稿，`Qwen35 UD` 也更稳
- **Nemotron 的真实优势**：极快，而且在 bounded root-cause / narrow repair 分析上有竞争力

也就是说，这轮不是 Nemotron “不行”，而是：

- 对 executor 主力角色，它输在 first-pass agentic 稳定性
- 对 analyst 主力角色，它输在复杂规划文稿的可靠性

## 现网状态

这轮 benchmark 已经完整收口，当前公网服务已恢复：

- `GET /v1/models` 返回：
  - `hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M`

关键恢复验证：
- [smoke_results.json](/Users/luo/Documents/github/CodexGame/output/nemotron-vs-qwen35-ud/20260326-raw/summary/smoke_results.json)

## Executor 结论

基础自动报告：

- [executor_coding_compare_report.md](/Users/luo/Documents/github/CodexGame/output/nemotron-vs-qwen35-ud/20260326-raw/summary/executor_coding_compare_report.md)
- [executor_agentic_compare_report.md](/Users/luo/Documents/github/CodexGame/output/nemotron-vs-qwen35-ud/20260326-raw/summary/executor_agentic_compare_report.md)

关键结果：

- Coding 22 题：
  - 两边都是 `22/22`
  - Nemotron 更快：
    - `6241.97 ms` vs `9008.55 ms`
    - `209.68 tok/s` vs `135.94 tok/s`

- Agentic 4 题 x 2 repeat：
  - Nemotron 首轮 JSON：`6/8`
  - Nemotron 首轮 validation：`5/8`
  - Qwen 首轮 JSON：`7/8`
  - Qwen 首轮 validation：`6/8`
  - Nemotron `best-of-2` 仍然只有 `5/8`
  - Qwen `best-of-2` 到 `7/8`

这已经足够下 executor 结论：

- **Nemotron 不适合替换 Qwen35 UD 作为默认 executor**
- 原因不是它慢或答案差，而是：
  - **结构化交付和补丁验证成功率更低**
  - 这是 executor 最关键的门槛

## Analyst 结论

分析轮自动汇总：
- [analyst_compare_report.md](/Users/luo/Documents/github/CodexGame/output/nemotron-vs-qwen35-ud/20260326-raw/summary/analyst_compare_report.md)

人工 rubric：
- [analyst_manual_rubric_report.md](/Users/luo/Documents/github/CodexGame/output/nemotron-vs-qwen35-ud/20260326-raw/summary/analyst_manual_rubric_report.md)
- [analyst_manual_rubric_scores.json](/Users/luo/Documents/github/CodexGame/output/nemotron-vs-qwen35-ud/20260326-raw/summary/analyst_manual_rubric_scores.json)

关键结果：

- 自动指标：
  - 两边都是 `9/9`
  - Nemotron 明显更快：
    - `22948.69 ms` vs `33879.56 ms`
  - Nemotron 也略长：
    - `5256` vs `4930`

- 人工 rubric：
  - Nemotron：`82`
  - Qwen35 UD：`89`
  - Nemotron 胜：`3`
  - Qwen35 UD 胜：`6`

family 结论：

- `longctx`
  - Nemotron 更好
- `multi_round`
  - Nemotron 略好
- `planning`
  - Qwen35 UD 明显更好

所以 analyst 口径的更准确结论不是“谁全赢”，而是：

- Nemotron 更适合：
  - 快速问题定位
  - 较窄边界的修复分析

- Qwen35 UD 更适合：
  - 实施规划
  - 复杂方案拆解
  - 更像正式设计文档的输出

如果只能选一个更稳妥的默认 analyst，我会选 **Qwen35 UD**。

## 最终推荐

如果你的目标是只保留一个最稳的工程型 35B：

- **默认 executor**：`Qwen3.5-35B-A3B-UD-Q4_K_XL`
- **默认 analyst**：`Qwen3.5-35B-A3B-UD-Q4_K_XL`

如果你允许双模型分工，这轮最有价值的组合是：

- `Qwen35 UD`
  - 主 executor
  - 主 planning / design analyst

- `Nemotron IQ4_XS`
  - 快速 review
  - 快速 bounded root-cause
  - guardrail 包裹下的辅助分析模型

一句话总结：

- **Qwen35 UD 更稳**
- **Nemotron 更快**
- 但在你这轮定义的工程口径里，**稳比快更重要**
