# strict_json

- status: `PASS`
- started: `2026-08-16T22:43:15-0400`
- model: `openclaw/Qwen3.6-27B-MTP-Q4XL`
- llama.cpp commit: `ebe4fca`
- lane: `baseline-production-qwen36-smoke`
- context: `131072`
- cold/warm: `n/a`

## Metrics

- prompt_tokens: `69`
- completion_tokens: `31`
- prompt_ms: `129.747`
- predicted_ms: `259.599`
- prompt_tokens_per_s: `531.8042035654004`
- decode_tokens_per_s: `119.414943817195`
- effective_tokens_per_s: `70.78148492766111`
- draft_n: `24`
- draft_n_accepted: `24`
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

- peak memory MiB: `22686.0`
- max utilization: `71.0`
- max power W: `94.25`
- max temperature C: `44.0`

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
