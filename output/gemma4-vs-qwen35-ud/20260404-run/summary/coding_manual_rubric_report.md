# Coding Manual Rubric

评分规则：`task_completion / evidence_grounding / constraint_adherence / decision_completeness / penalty`。

总分：
- Qwen35 UD：`302`
- Gemma4 UD：`82`

说明：
- 对 HTTP `503/400` 或未形成可读正文的题，直接记 `0`。
- Gemma 前 7 题虽然方向基本对，但统一扣除了输出模板污染和收敛不足的分。
- Qwen 在大部分成功题上能给出更完整的根因、约束和修复方向，因此总分明显更高。
