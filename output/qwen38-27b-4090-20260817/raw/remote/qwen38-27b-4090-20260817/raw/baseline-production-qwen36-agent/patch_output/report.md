# patch_output

- status: `PASS`
- started: `2026-08-16T22:43:19-0400`
- model: `openclaw/Qwen3.6-27B-MTP-Q4XL`
- llama.cpp commit: `ebe4fca`
- lane: `baseline-production-qwen36-agent`
- context: `131072`
- cold/warm: `n/a`

## Metrics

- prompt_tokens: `84`
- completion_tokens: `70`
- prompt_ms: `121.794`
- predicted_ms: `784.161`
- prompt_tokens_per_s: `689.6891472486329`
- decode_tokens_per_s: `89.26738259107505`
- effective_tokens_per_s: `62.54025992959216`
- draft_n: `53`
- draft_n_accepted: `52`
- draft_acceptance_rate: `0.9811320754716981`
- cache_n: `0`
- empty_output: `False`
- think_leak: `False`
- markdown_fence: `True`
- json_valid: `None`
- contains_ok: `True`
- exact_ok: `None`
- finish_reason: `stop`

## GPU

- peak memory MiB: `22686.0`
- max utilization: `74.0`
- max power W: `277.78`
- max temperature C: `50.0`

## Manual review

- format score (1-5): `3`
- quality score (1-5): `4`
- reviewer notes: `核心内容正确，但仍有 markdown fence，不能直接作为严格 JSON/patch 协议载荷。`

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
```diff
--- a/executor/rank.py
+++ b/executor/rank.py
@@ -1,3 +1,3 @@
 def top_k(items, k):
-    items.sort(reverse=True)
-    return items[:k]
+    return sorted(items, reverse=True)[:k]
```
```
