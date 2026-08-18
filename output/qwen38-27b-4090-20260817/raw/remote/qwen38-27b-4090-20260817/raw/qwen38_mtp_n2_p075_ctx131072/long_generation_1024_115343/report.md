# long_generation_1024_115343

- status: `PASS`
- started: `2026-08-16T23:06:04-0400`
- model: `/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf`
- llama.cpp commit: `4df29be4f4c3673f428170fda944a5b19f743bb8`
- lane: `qwen38_mtp_n2_p075_ctx131072`
- context: `131072`
- cold/warm: `n/a`

## Metrics

- prompt_tokens: `80050`
- completion_tokens: `25`
- prompt_ms: `749.358`
- predicted_ms: `385.131`
- prompt_tokens_per_s: `106824.77534102526`
- decode_tokens_per_s: `64.91297766214613`
- effective_tokens_per_s: `16.203412228974727`
- draft_n: `16`
- draft_n_accepted: `16`
- draft_acceptance_rate: `1.0`
- cache_n: `79503`
- empty_output: `False`
- think_leak: `False`
- markdown_fence: `False`
- json_valid: `None`
- contains_ok: `True`
- exact_ok: `None`
- finish_reason: `stop`

## GPU

- peak memory MiB: `23552.0`
- max utilization: `100.0`
- max power W: `445.68`
- max temperature C: `83.0`

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
