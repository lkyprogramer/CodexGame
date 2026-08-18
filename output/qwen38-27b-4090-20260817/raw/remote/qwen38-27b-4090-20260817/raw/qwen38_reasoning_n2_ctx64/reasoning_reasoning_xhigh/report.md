# reasoning_reasoning_xhigh

- status: `PASS`
- started: `2026-08-16T23:03:50-0400`
- model: `/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf`
- llama.cpp commit: `4df29be4f4c3673f428170fda944a5b19f743bb8`
- lane: `qwen38_reasoning_n2_ctx64`
- context: `65536`
- cold/warm: `reasoning_xhigh`

## Metrics

- prompt_tokens: `93`
- completion_tokens: `121`
- prompt_ms: `210.423`
- predicted_ms: `1802.704`
- prompt_tokens_per_s: `441.96689525384585`
- decode_tokens_per_s: `67.12139097710995`
- effective_tokens_per_s: `56.195334350621145`
- draft_n: `72`
- draft_n_accepted: `64`
- draft_acceptance_rate: `0.8888888888888888`
- cache_n: `0`
- empty_output: `False`
- think_leak: `False`
- markdown_fence: `False`
- json_valid: `True`
- contains_ok: `None`
- exact_ok: `None`
- finish_reason: `stop`

## GPU

- peak memory MiB: `20596.0`
- max utilization: `97.0`
- max power W: `288.01`
- max temperature C: `66.0`

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
  "answer": "4",
  "reasoning_mode": "direct"
}
```
