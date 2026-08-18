# cache_08_repeat_4

- status: `PASS`
- started: `2026-08-16T23:03:16-0400`
- model: `/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf`
- llama.cpp commit: `4df29be4f4c3673f428170fda944a5b19f743bb8`
- lane: `qwen38_cache_n2_ctx64`
- context: `65536`
- cold/warm: `repeat_4`

## Metrics

- prompt_tokens: `5639`
- completion_tokens: `53`
- prompt_ms: `113.625`
- predicted_ms: `618.24`
- prompt_tokens_per_s: `49628.16281628163`
- decode_tokens_per_s: `85.72722567287785`
- effective_tokens_per_s: `69.16463994401774`
- draft_n: `34`
- draft_n_accepted: `34`
- draft_acceptance_rate: `1.0`
- cache_n: `5635`
- empty_output: `False`
- think_leak: `False`
- markdown_fence: `True`
- json_valid: `False`
- contains_ok: `None`
- exact_ok: `None`
- finish_reason: `stop`

## GPU

- peak memory MiB: `20600.0`
- max utilization: `100.0`
- max power W: `438.35`
- max temperature C: `76.0`

## Manual review

- format score (1-5): `3`
- quality score (1-5): `3`
- reviewer notes: `内容主体可读，但格式合同泄漏 markdown fence。`

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
```json
{
  "marker": "QWEN38_OPENCLAW_NEEDLE_4090_20260817",
  "action": "Return only the exact critical marker."
}
```
```
