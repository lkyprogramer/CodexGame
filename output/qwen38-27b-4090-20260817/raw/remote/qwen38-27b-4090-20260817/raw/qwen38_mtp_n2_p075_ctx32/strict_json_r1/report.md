# strict_json_r1

- status: `PASS`
- started: `2026-08-16T22:52:09-0400`
- model: `/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf`
- llama.cpp commit: `4df29be4f4c3673f428170fda944a5b19f743bb8`
- lane: `qwen38_mtp_n2_p075_ctx32`
- context: `32768`
- cold/warm: `n/a`

## Metrics

- prompt_tokens: `69`
- completion_tokens: `28`
- prompt_ms: `193.502`
- predicted_ms: `285.837`
- prompt_tokens_per_s: `356.5854616489752`
- decode_tokens_per_s: `97.9579270703233`
- effective_tokens_per_s: `41.861469702577594`
- draft_n: `18`
- draft_n_accepted: `18`
- draft_acceptance_rate: `1.0`
- cache_n: `27`
- empty_output: `False`
- think_leak: `False`
- markdown_fence: `False`
- json_valid: `True`
- contains_ok: `None`
- exact_ok: `None`
- finish_reason: `stop`

## GPU

- peak memory MiB: `18580.0`
- max utilization: `96.0`
- max power W: `415.91`
- max temperature C: `80.0`

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
  "name": "health",
  "method": "GET",
  "path": "/health"
}
```
