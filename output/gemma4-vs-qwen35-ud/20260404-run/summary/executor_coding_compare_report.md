# Executor Coding Compare

直接结论：`Qwen3.5-35B-A3B-UD-Q4_K_XL` 明显优于 `gemma-4-26B-A4B-it-UD-Q4_K_XL`。

自动结果：
- Gemma：22 题里 `200=7`，`503=15`，成功题平均时延 `12729.3` ms，平均 `130.9` tok/s
- Qwen：26 题里 `200=22`，`400=2`，`503=2`，成功题平均时延 `28473.07` ms，平均 `133.83` tok/s

人工 rubric：
- Qwen 总分：`302`
- Gemma 总分：`82`
- Qwen 更好：`22` 题
- Gemma 更好：`0` 题
- 持平：`4` 题

关键观察：
- Gemma 前 7 个 Java review 题能给出方向正确的分析，但输出带明显模板污染，例如 `<|channel>thought`。
- Gemma 一旦进入更长的 TS / script 任务就快速退化为 `503`。
- Qwen 虽然更慢，但在普通 64K coding 题上覆盖更完整，且协议污染比 Gemma 轻。
- 两边都无法在这套 64K profile 下处理 extreme 长上下文题；这部分不应被解释成模型质量分差，而是 profile 不匹配。
