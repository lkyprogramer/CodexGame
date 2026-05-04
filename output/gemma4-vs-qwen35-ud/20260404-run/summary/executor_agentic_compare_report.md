# Executor Agentic Compare

直接结论：两边在当前 64K executor profile 下都不适合作为 agentic JSON 交付模型，但 Gemma 更差。

自动结果：
- Gemma：16/16 全部 `503`，`json_parse_success=0`，`validation_success=0`
- Qwen：16 次里 `200=2`、`503=14`，但两次 `200` 也都 `json_parse_success=0`，最终 `validation_success=0`

判断：
- 这轮已经足以说明 `Qwen35 UD` 和 `Gemma4 UD` 都不应替代现有 27B UD executor。
- Gemma 的问题是直接不可用；Qwen35 UD 的问题是偶尔出正文，但协议稳定性仍然不够。
