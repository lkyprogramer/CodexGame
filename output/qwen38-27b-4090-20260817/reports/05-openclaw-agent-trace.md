# Case 05: OpenClaw Agent Trace

## 结果

同一进程内完成真实三轮链路：首轮请求工具、服务返回 `tool_calls=1`；第二轮回灌工具结果并要求 JSON 诊断；第三轮追加 unified diff 并要求 patch review JSON。

| turn | tool_calls | JSON | completion | decode tok/s | format | quality |
|---|---:|---|---:|---:|---:|---:|
| `trace_patch_review_round3` | 0 | True | 202 | 61.53 | 5 | 5 |
| `trace_tool_round1` | 1 | None | 31 | 90.94 | 5 | 5 |
| `trace_tool_round2_json` | 0 | True | 199 | 58.59 | 5 | 5 |

首轮工具调用、工具结果、assistant 历史和后续请求均保存在每个 case 的 `request.json`、`response.json` 与 `trace.json`。第三轮没有 thinking 文本污染，JSON 可解析。

## 人工结论

该 lane 对 OpenClaw 最关键的多轮形状是可用的：工具调用结构正确，工具结果能被后续轮次使用，patch review 能指出 45s 降为 5s 的风险并给出安全修复建议。仍需在生产客户端使用 JSON schema/response format 防止 matrix 类 prompt 偶发 fence。

## 证据

- raw lane：`raw/remote/qwen38-27b-4090-20260817/raw/qwen38_agent_n2_ctx64`
- console：`raw/remote/qwen38-27b-4090-20260817/logs/case05-agent-console.log`
