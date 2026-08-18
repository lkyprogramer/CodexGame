# Case 03: Qwen3.8 32K smoke

## 结论

最终正式 smoke 通过：模型加载、OpenAI `/v1/models`、短响应和严格 JSON 均通过，无 CUDA OOM。lane 峰值显存 `18568.0 MiB`。

首轮 smoke 曾观察到 `--reasoning auto` 在 `max_tokens=16` 下把预算消耗在 `reasoning_content`、正文为空；该轮未作为正式结果保留，随后将默认 chat template kwargs 固定为 `enable_thinking=false` 后重跑并通过。此行为是部署配置门禁，不能忽略。

## 指标

| case | result | prompt | completion | decode tok/s | acceptance | format | quality |
|---|---|---:|---:|---:|---:|---:|---:|
| `short_ok` | PASS | 44 | 2 | 36.10 | 1.00 | 5 | 5 |
| `strict_json` | PASS | 69 | 28 | 97.78 | 1.00 | 5 | 5 |

## 证据

- raw lane：`raw/remote/qwen38-27b-4090-20260817/raw/qwen38_smoke_n2_ctx32`
- 首轮 console：`raw/remote/qwen38-27b-4090-20260817/logs/case03-smoke-console.log`
- 正式重跑 console：`raw/remote/qwen38-27b-4090-20260817/logs/case03-smoke-console-rerun.log`
