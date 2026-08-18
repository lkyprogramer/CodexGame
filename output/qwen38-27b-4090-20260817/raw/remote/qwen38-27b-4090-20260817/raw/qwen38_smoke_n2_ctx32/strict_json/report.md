# strict_json

- status: `PASS`
- started: `2026-08-16T22:44:39-0400`
- model: `/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf`
- llama.cpp commit: `4df29be4f4c3673f428170fda944a5b19f743bb8`
- lane: `qwen38_smoke_n2_ctx32`
- context: `32768`
- cold/warm: `n/a`

## Metrics

- prompt_tokens: `69`
- completion_tokens: `28`
- prompt_ms: `192.782`
- predicted_ms: `286.348`
- prompt_tokens_per_s: `357.91723293668497`
- decode_tokens_per_s: `97.78311704639111`
- effective_tokens_per_s: `57.696727215401886`
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

- peak memory MiB: `18568.0`
- max utilization: `97.0`
- max power W: `130.78`
- max temperature C: `52.0`

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
