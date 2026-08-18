# long_generation_2048_57671

- status: `PASS`
- started: `2026-08-16T23:04:08-0400`
- model: `/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf`
- llama.cpp commit: `4df29be4f4c3673f428170fda944a5b19f743bb8`
- lane: `qwen38_mtp_n2_p075_ctx65536`
- context: `65536`
- cold/warm: `n/a`

## Metrics

- prompt_tokens: `40083`
- completion_tokens: `25`
- prompt_ms: `553.086`
- predicted_ms: `315.786`
- prompt_tokens_per_s: `72471.55053644461`
- decode_tokens_per_s: `79.16753750957928`
- effective_tokens_per_s: `23.107024642349387`
- draft_n: `16`
- draft_n_accepted: `16`
- draft_acceptance_rate: `1.0`
- cache_n: `39562`
- empty_output: `False`
- think_leak: `False`
- markdown_fence: `False`
- json_valid: `None`
- contains_ok: `True`
- exact_ok: `None`
- finish_reason: `stop`

## GPU

- peak memory MiB: `20600.0`
- max utilization: `100.0`
- max power W: `443.64`
- max temperature C: `76.0`

## Manual review

- format score (1-5): `4`
- quality score (1-5): `4`
- reviewer notes: `核心 marker/修复内容正确，长输出可读；未对全部细节做语义基准。`

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
