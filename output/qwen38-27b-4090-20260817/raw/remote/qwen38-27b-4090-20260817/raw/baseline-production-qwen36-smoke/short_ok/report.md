# short_ok

- status: `PASS`
- started: `2026-08-16T22:43:14-0400`
- model: `openclaw/Qwen3.6-27B-MTP-Q4XL`
- llama.cpp commit: `ebe4fca`
- lane: `baseline-production-qwen36-smoke`
- context: `131072`
- cold/warm: `n/a`

## Metrics

- prompt_tokens: `44`
- completion_tokens: `6`
- prompt_ms: `90.443`
- predicted_ms: `49.591`
- prompt_tokens_per_s: `486.4942560507723`
- decode_tokens_per_s: `120.98969571091529`
- effective_tokens_per_s: `20.35712403825523`
- draft_n: `4`
- draft_n_accepted: `4`
- draft_acceptance_rate: `1.0`
- cache_n: `0`
- empty_output: `False`
- think_leak: `False`
- markdown_fence: `False`
- json_valid: `None`
- contains_ok: `None`
- exact_ok: `True`
- finish_reason: `stop`

## GPU

- peak memory MiB: `22686.0`
- max utilization: `21.0`
- max power W: `31.25`
- max temperature C: `41.0`

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
OK
```
