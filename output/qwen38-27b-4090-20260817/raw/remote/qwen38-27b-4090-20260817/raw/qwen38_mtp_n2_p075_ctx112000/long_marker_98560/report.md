# long_marker_98560

- status: `PASS`
- started: `2026-08-16T23:05:19-0400`
- model: `/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf`
- llama.cpp commit: `4df29be4f4c3673f428170fda944a5b19f743bb8`
- lane: `qwen38_mtp_n2_p075_ctx112000`
- context: `112000`
- cold/warm: `n/a`

## Metrics

- prompt_tokens: `68391`
- completion_tokens: `25`
- prompt_ms: `34125.345`
- predicted_ms: `386.212`
- prompt_tokens_per_s: `2004.1116067837554`
- decode_tokens_per_s: `64.73128747941546`
- effective_tokens_per_s: `0.716934122302995`
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

- peak memory MiB: `22698.0`
- max utilization: `100.0`
- max power W: `443.27`
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
