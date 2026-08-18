# Case 08: Reasoning profile

| profile | JSON | content | reasoning_content | completion | decode tok/s | format | quality |
|---|---|---|---|---:|---:|---:|---:|
| `reasoning_low` | True | True | True | 56 | 84.13 | 5 | 5 |
| `reasoning_xhigh` | True | True | True | 121 | 67.12 | 5 | 5 |
| `thinking_false` | True | True | False | 22 | 75.21 | 5 | 5 |

## 结论

- 默认 OpenClaw 候选必须使用 `enable_thinking=false`，否则短输出可能把预算消耗在 reasoning_content。
- `reasoning_low` 与 `reasoning_xhigh` 均能区分 `content` 与 `reasoning_content`，JSON 解析通过；xhigh 代价是 completion 和 decode 更慢。
- reasoning profile 不应通过全局默认值隐式打开，应用层需显式选择。

证据：`raw/remote/qwen38-27b-4090-20260817/raw/qwen38_reasoning_n2_ctx64`。
