# S1 协议门禁

Lane：`s1_work_balanced`，64K q8 + MTP n=2 + medium + budget 16384  
峰值显存：20600 MiB，最高温度 83°C

| case | pass | 关键观察 |
|---|---|---|
| `s1_models` | True | `/v1/models` 200 |
| `s1_think_sentinel` | True | `chat_template_kwargs.reasoning_effort=banana` → HTTP 500。顶层/非法值不会静默当 xhigh |
| `s1_medium_not_empty` | True | 1.24s，思考约 44 token，正文 `323 is the product...`，`finish=stop` |
| `s1_budget_cut_no_redo` | True | xhigh 诱导长思考：reasoning ≈ 14761，墙钟 235s，正文有分类，未重做 |
| `s1_json_schema` | True | `response_format` 得到 name/method/path |
| `s1_tool_round1` | True | 调用 `read_file` |
| `s1_tool_roundtrip` | True | 回灌后 JSON：tick_ms=200，turn_timeout_ms=45000 |
| `s1_no_think_short` | True | 请求级 thinking off，精确 `OK` |

S1 自动分：**8/8**。

硬结论：

- 08-17 的“必须全局关思考”不成立。medium + 足够 `max_tokens` 时短问答稳定。
- 预算切断有效：思考被切在约 16k，正文仍可用。
- 客户端 `max_tokens` 必须大于思考预算，否则会重现 S4 的空正文（见 S4）。
