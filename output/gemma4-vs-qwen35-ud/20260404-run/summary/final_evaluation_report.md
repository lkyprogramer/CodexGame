# Gemma4 vs Qwen35 UD Final Evaluation

直接结论：
- **Executor**：`Qwen3.5-35B-A3B-UD-Q4_K_XL` 明显优于 `gemma-4-26B-A4B-it-UD-Q4_K_XL`。
- **Agentic**：两边都不合格，Gemma 更差。
- **Analyst**：这轮无法得出模型质量高低结论，因为 `128K` profile 本身失效。

关键结果：
- Executor coding
  - Gemma：`200=7/22`，其余 `503`
  - Qwen：`200=22/26`，其余 `400/503` 主要集中在 extreme 长上下文压力题
- Executor agentic
  - Gemma：`16/16` 全 `503`
  - Qwen：`2/16` 得到 `200`，但也没有产出可解析 JSON
- Manual rubric
  - Coding：Qwen `302` vs Gemma `82`
  - Analyst：两边都 `0`，因为无可评分正文

最终评价：
1. Gemma 这次最大的正面信号，只是它在前 7 个经典 Java review 题上能给出方向正确的回答。
2. 但它的输出契约污染明显，稳定性远差于 Qwen35 UD，一进长一点或跨文件任务就迅速退化。
3. Qwen35 UD 也没有强到可以接替 27B UD 做 executor；尤其 agentic 几乎不可用。
4. 因此这轮真正能下的决策不是“Gemma 还是 Qwen35 UD 谁当主力”，而是：**两者都不该替换现有 27B UD executor**。
5. 如果只在这两个里选一个做工程型单模型，仍然是 `Qwen35 UD`；但这是相对更好，不是已经足够好。

建议：
- 保持现有 `27B UD` 作为 executor 主力。
- `Qwen35 UD` 只适合做高质量 review / coding explanation 的候选，不适合 agentic 默认后端。
- Gemma4 UD 暂时只建议保留为实验模型；若要继续研究，先解决 `gemma4` 输出模板污染和 serving 稳定性，再谈能力对比。
