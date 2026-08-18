# reasoning_thinking_false

- status: `PASS`
- started: `2026-08-16T23:03:46-0400`
- model: `/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf`
- llama.cpp commit: `4df29be4f4c3673f428170fda944a5b19f743bb8`
- lane: `qwen38_reasoning_n2_ctx64`
- context: `65536`
- cold/warm: `thinking_false`

## Metrics

- prompt_tokens: `57`
- completion_tokens: `22`
- prompt_ms: `236.452`
- predicted_ms: `292.517`
- prompt_tokens_per_s: `241.06372540727082`
- decode_tokens_per_s: `75.20930407463499`
- effective_tokens_per_s: `41.130242149129835`
- draft_n: `15`
- draft_n_accepted: `15`
- draft_acceptance_rate: `1.0`
- cache_n: `0`
- empty_output: `False`
- think_leak: `False`
- markdown_fence: `False`
- json_valid: `True`
- contains_ok: `None`
- exact_ok: `None`
- finish_reason: `stop`

## GPU

- peak memory MiB: `20596.0`
- max utilization: `97.0`
- max power W: `288.01`
- max temperature C: `66.0`

## Manual review

- format score (1-5): `5`
- quality score (1-5): `5`
- reviewer notes: `满足 case 的精确值或 JSON 字段约束，内容简洁可解析。`

## Raw evidence

- `request.json`
- `response.json`
- `result.json`
- `server.stdout.log`
- `server.stderr.log`
- `gpu.csv`
- `trace.json` (when this is a multi-turn trace)

## Output

```text
{
  "answer": 4,
  "reasoning_mode": "direct"
}
```
