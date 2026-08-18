# long_marker_180000

- status: `PASS`
- started: `2026-08-16T23:08:13-0400`
- model: `/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf`
- llama.cpp commit: `4df29be4f4c3673f428170fda944a5b19f743bb8`
- lane: `qwen38_mtp_n2_p075_ctx131072_exact`
- context: `131072`
- cold/warm: `n/a`

## Metrics

- prompt_tokens: `124831`
- completion_tokens: `25`
- prompt_ms: `75069.473`
- predicted_ms: `479.433`
- prompt_tokens_per_s: `1662.8730029848484`
- decode_tokens_per_s: `52.14492953134223`
- effective_tokens_per_s: `0.3284586722310133`
- draft_n: `16`
- draft_n_accepted: `16`
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

- peak memory MiB: `23552.0`
- max utilization: `100.0`
- max power W: `442.16`
- max temperature C: `82.0`

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
QWEN38_OPENCLAW_NEEDLE_4090_20260817
```
