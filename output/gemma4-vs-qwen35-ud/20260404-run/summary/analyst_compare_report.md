# Analyst Compare

直接结论：这轮 `128K` analyst profile 没有产出有效模型质量对比，因为两边都是基础设施级失败。

自动结果：
- Gemma：9/9 全部 `503`
- Qwen35 UD：9/9 全部 `503`

解释：
- 这说明当前 `131072 + q4_0 KV + 单槽 + 4090` 的 serving 组合对这组 analyst 任务不稳。
- 因此 analyst 轮不能据此判定“Gemma 比 Qwen 差”或反过来，只能判定“这套 profile 不可用”。
