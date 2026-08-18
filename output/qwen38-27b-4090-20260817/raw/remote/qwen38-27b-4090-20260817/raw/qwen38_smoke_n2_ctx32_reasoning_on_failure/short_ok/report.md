# short_ok

- status: `PASS`
- started: `2026-08-16T23:17:12-0400`
- model: `/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf`
- llama.cpp commit: `4df29be4f4c3673f428170fda944a5b19f743bb8`
- lane: `qwen38_smoke_n2_ctx32_reasoning_on_failure`
- context: `32768`
- cold/warm: `n/a`

## Metrics

- prompt_tokens: `68`
- completion_tokens: `16`
- prompt_ms: `243.923`
- predicted_ms: `222.211`
- prompt_tokens_per_s: `278.77649914112243`
- decode_tokens_per_s: `72.00363618362726`
- effective_tokens_per_s: `33.843508042561176`
- draft_n: `11`
- draft_n_accepted: `9`
- draft_acceptance_rate: `0.8181818181818182`
- cache_n: `0`
- empty_output: `True`
- think_leak: `False`
- markdown_fence: `False`
- json_valid: `None`
- contains_ok: `None`
- exact_ok: `False`
- finish_reason: `length`

## GPU

- peak memory MiB: `18576.0`
- max utilization: `95.0`
- max power W: `141.3`
- max temperature C: `51.0`

## Manual review

- format score (1-5): `1`
- quality score (1-5): `1`
- reviewer notes: `请求失败、空输出或服务错误。`

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
The user is asking me to reply with "OK" only. This is a
```
