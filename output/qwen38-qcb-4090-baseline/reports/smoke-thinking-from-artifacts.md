# Smoke 思考量事后拆分（不是 API Reasoning Token）

来源：4090 `raw-responses.json` 的 `message.reasoning_content`。  
llama.cpp **没有**填 `usage.reasoning_tokens`。下表禁止解读成「少了 N% reasoning tokens」。

度量：

- **completion token**：API end-to-end，含思考 + 工具 JSON + 可见回答。
- **thinking chars**：`reasoning_content` 字符。同一 Qwen3.8 词表上可横向比。
- **calls**：每题 LLM 轮次。

| 候选 | n | 轮次 P50 | completion token P50 | thinking chars P50 | 可见回答 chars P50 | think 字符占比 |
|---|---:|---:|---:|---:|---:|---:|
| Sharp | 12 | 12 | 9329 | 18984 | 2120 | 91.8% |
| Grug | 12 | **39** | 8774 | **2849** | 343 | 86.1% |
| Fable | 12 | 14 | 6552 | 14528 | 1556 | 92.5% |
| Salience | 12 | 10 | **5372** | 10523 | 2148 | 89.4% |
| Cold Fusion | 12 | 10 | 6306 | 14840 | 2742 | 84.9% |
| WORK core 混合物 | 108 | 12 | 9180 | 17209 | 2555 | 91.7% |

要点：

1. **Grug 的卖点成立，但只在思考正文上。** thinking chars 大约是 Sharp 的 15%（2849 vs 18984）。completion token 几乎没少，因为轮次从 12 打到 39（空转）。
2. 若不拆 `reasoning_content`，会误判「Grug 没少思考」。这正是反馈说的盲区。
3. Salience 是 smoke 里 **completion token 最省** 的（P50 5372），思考量中等，Hard 最高。
4. Cold Fusion 思考字符只略低于 Sharp，没有作者宣称的 1/5–1/2 那么夸张（至少在这 12 题上）。
5. WORK core 108 含 12 条 smoke，只能当量级，不能当冻结对照。正式对照等 core 用新 runner 再记。

core 起跑必须用已改 QCB：`token_breakdown.llm_calls[]` 每轮 prompt/completion/thinking chars/answer chars。
