# strict_json

- status: `PASS`
- started: `2026-08-16T23:17:12-0400`
- model: `/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf`
- llama.cpp commit: `4df29be4f4c3673f428170fda944a5b19f743bb8`
- lane: `qwen38_smoke_n2_ctx32_reasoning_on_failure`
- context: `32768`
- cold/warm: `n/a`

## Metrics

- prompt_tokens: `93`
- completion_tokens: `47`
- prompt_ms: `194.356`
- predicted_ms: `551.027`
- prompt_tokens_per_s: `478.5033649591471`
- decode_tokens_per_s: `85.29527591206964`
- effective_tokens_per_s: `62.499817145502824`
- draft_n: `31`
- draft_n_accepted: `30`
- draft_acceptance_rate: `0.967741935483871`
- cache_n: `53`
- empty_output: `False`
- think_leak: `False`
- markdown_fence: `False`
- json_valid: `True`
- contains_ok: `None`
- exact_ok: `None`
- finish_reason: `stop`

## GPU

- peak memory MiB: `18576.0`
- max utilization: `95.0`
- max power W: `141.3`
- max temperature C: `51.0`

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
{"name":"health","method":"GET","path":"/health"}
```
