# cache_04_similarity

- status: `PASS`
- started: `2026-08-16T23:03:12-0400`
- model: `/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf`
- llama.cpp commit: `4df29be4f4c3673f428170fda944a5b19f743bb8`
- lane: `qwen38_cache_n2_ctx64`
- context: `65536`
- cold/warm: `similarity`

## Metrics

- prompt_tokens: `5640`
- completion_tokens: `55`
- prompt_ms: `363.375`
- predicted_ms: `729.936`
- prompt_tokens_per_s: `15521.155830753354`
- decode_tokens_per_s: `75.34907169943666`
- effective_tokens_per_s: `48.63138841790522`
- draft_n: `34`
- draft_n_accepted: `33`
- draft_acceptance_rate: `0.9705882352941176`
- cache_n: `5134`
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
  "next_step": "Acknowledge marker and await further instructions."
}
```
```
