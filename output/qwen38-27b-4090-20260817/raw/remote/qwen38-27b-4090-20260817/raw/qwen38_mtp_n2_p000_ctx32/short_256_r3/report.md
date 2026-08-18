# short_256_r3

- status: `PASS`
- started: `2026-08-16T23:00:07-0400`
- model: `/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf`
- llama.cpp commit: `4df29be4f4c3673f428170fda944a5b19f743bb8`
- lane: `qwen38_mtp_n2_p000_ctx32`
- context: `32768`
- cold/warm: `n/a`

## Metrics

- prompt_tokens: `72`
- completion_tokens: `256`
- prompt_ms: `193.393`
- predicted_ms: `3552.535`
- prompt_tokens_per_s: `372.29889396203583`
- decode_tokens_per_s: `72.06121825682224`
- effective_tokens_per_s: `64.99517102253206`
- draft_n: `240`
- draft_n_accepted: `135`
- draft_acceptance_rate: `0.5625`
- cache_n: `27`
- empty_output: `False`
- think_leak: `False`
- markdown_fence: `False`
- json_valid: `None`
- contains_ok: `True`
- exact_ok: `None`
- finish_reason: `length`

## GPU

- peak memory MiB: `18580.0`
- max utilization: `100.0`
- max power W: `442.77`
- max temperature C: `84.0`

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
1. Establishing a baseline is the foundational step in any maintenance workflow. Before applying any changes, you must capture the current state of the system. This includes recording CPU usage, memory allocation, disk I/O, and network latency. Without this snapshot, you have no reference point to compare against later. If the system is already degraded, you need to know that immediately. It prevents you from misattributing pre-existing issues to the new patch. This step ensures that you are starting from a known, stable state.

2. Verifying service availability is critical to ensure that all dependent components are functioning correctly. A read-only check confirms that critical services are up and responding to health probes. If a service is down or unresponsive before the patch, applying changes could mask the root cause or complicate troubleshooting. You need to confirm that the application layer is healthy. This includes checking API endpoints, database connections, and message queues. Ensuring these are operational guarantees that the patch will be applied to a live, functioning system rather than a broken one.

3. Checking for pending updates or conflicts is essential to avoid version mismatches. The health check should verify that the current software version matches the expected version. It should also look for any unapplied configuration changes or pending
```
