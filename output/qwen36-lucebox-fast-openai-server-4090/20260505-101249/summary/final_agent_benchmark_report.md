# Qwen3.6 Lucebox Fast OpenAI Server 32K/64K/128K Agent Benchmark

主指标是每一次完整 OpenAI-compatible API 调用的端到端输出速度：`visible output tokens / wall elapsed seconds`。它包含压缩、cache lookup、GPU snapshot restore、target prefill、DFlash decode、HTTP/JSON 与 Python 调度开销。`daemon decode TPS` 只作为内部解码阶段参考。

## Final Config

- target: `/data/models/qwen/Qwen3.6-27B-Q4_K_M.gguf`
- draft: `/data/models/qwen/dflash-draft-qwen36-q8/dflash-draft-3.6-q8_0.gguf`
- prefill_drafter: `/data/models/qwen/Qwen3-0.6B-BF16.gguf`
- server: `/home/hhtele/lucebox-hub-main-maxperf-qwen36/dflash/scripts/server_fast.py`
- port: `18349 for 32K/64K, 18350 for optimized 128K rerun`
- kv: `TQ3_0`
- fa_window: `2048`
- ddtree_budget: `26`
- pflash_keep_ratio: `0.05`
- stream_chunk_tokens: `4`
- max_tokens_per_turn: `128`
- source_max_ctx: `131072`
- target_max_ctx_32k_64k: `16384`
- target_max_ctx_128k_final: `8192`

## Final Summary

| context | source tokens | compressed target tokens | cold complete TPS | warm median complete TPS | cold latency | warm median latency | compression cache | GPU snapshot restores | daemon decode median |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 32K | 32278 | 1601 | 10.52 | 38.06 | 12.16s | 3.37s | 4/1 | 4/4 warm | 54.89 |
| 64K | 65274 | 3255 | 10.66 | 39.02 | 12.00s | 3.30s | 4/1 | 4/4 warm | 53.65 |
| 128K | 127243 | 6333 | 7.15 | 33.03 | 17.91s | 3.88s | 4/1 | 4/4 warm | 51.93 |

## Per-Turn Complete Inference Speed

| context | turn | wall latency | visible tokens | complete TPS | source tokens | compressed target tokens | target ctx | compression hit/miss | GPU restore | daemon prefill | daemon decode TPS | output valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---|
| 32K | 1 | 12.16s | 128 | 10.52 | 32278 | 1601 | 16384 | 0/1 | False | 4.168s | 62.88 | True |
| 32K | 2 | 3.67s | 128 | 34.88 | 32280 | 1603 | 16384 | 1/0 | True | 0.122s | 47.62 | True |
| 32K | 3 | 3.49s | 128 | 36.67 | 32275 | 1598 | 16384 | 1/0 | True | 0.092s | 49.98 | True |
| 32K | 4 | 3.24s | 128 | 39.45 | 32273 | 1596 | 16384 | 1/0 | True | 0.091s | 54.89 | True |
| 32K | 5 | 2.93s | 128 | 43.69 | 32273 | 1596 | 16384 | 1/0 | True | 0.092s | 65.03 | True |
| 64K | 1 | 12.00s | 128 | 10.66 | 65274 | 3255 | 16384 | 0/1 | False | 2.230s | 53.65 | True |
| 64K | 2 | 2.94s | 128 | 43.56 | 65276 | 3257 | 16384 | 1/0 | True | 0.050s | 70.21 | True |
| 64K | 3 | 3.59s | 128 | 35.70 | 65271 | 3252 | 16384 | 1/0 | True | 0.048s | 52.71 | True |
| 64K | 4 | 3.53s | 128 | 36.28 | 65269 | 3250 | 16384 | 1/0 | True | 0.047s | 53.22 | True |
| 64K | 5 | 3.07s | 128 | 41.76 | 65269 | 3250 | 16384 | 1/0 | True | 0.047s | 62.20 | True |
| 128K | 1 | 17.91s | 128 | 7.15 | 127243 | 6333 | 8192 | 0/1 | False | 4.038s | 48.67 | True |
| 128K | 2 | 3.79s | 128 | 33.80 | 127245 | 6335 | 8192 | 1/0 | True | 0.054s | 55.64 | True |
| 128K | 3 | 3.97s | 128 | 32.26 | 127240 | 6330 | 8192 | 1/0 | True | 0.056s | 51.93 | True |
| 128K | 4 | 4.05s | 128 | 31.61 | 127238 | 6328 | 8192 | 1/0 | True | 0.055s | 50.44 | True |
| 128K | 5 | 3.61s | 128 | 35.44 | 127238 | 6328 | 8192 | 1/0 | True | 0.052s | 62.07 | True |

## 128K Optimization Note

- 初始 128K 使用 `target_max_ctx=16384` 时，压缩后 target prompt 约 `6333` tokens，但 stable prefix snapshot 分配仍需要约 `573.63 MiB`，4090 上连续失败，warm turns 只能命中 CPU compression cache，warm median complete TPS 约 `15.75`。
- 重新把 128K target ctx 降到 `8192` 后，同一 128K agent 任务 4 个 warm turns 全部 GPU snapshot restore 命中，warm median complete TPS 提升到 `33.03`，warm median latency 从 `8.13s` 降到 `3.88s`。
- 这说明长上下文 agent 场景的关键不是单纯打开 PFlash，而是按压缩后的 target prompt 动态收缩 target KV ctx，让 snapshot 在 24GB 4090 上实际可分配。

## Validation

- 32K/64K/128K 每档各 5 个 agent/coding turns，全部生成非空正文。
- 三档均未出现 `<think>` / thinking leakage。
- 32K、64K、128K final profile 的 4 个 warm turns 均命中 compression cache 和 GPU stable compressed-prefix snapshot。
- benchmark 脚本结束后已恢复 `qwen35-35b-a3b-uncensored`，两轮 `default_service_restored=true`。

## Raw Artifacts

- `agent-final/raw/qwen36_fast_agent_bench_final/agent_benchmark.json`: 32K/64K plus original 128K diagnostic run.
- `agent-final/raw/qwen36_fast_agent_bench_128k_ctx8192/agent_benchmark.json`: optimized 128K final run.
- `summary/agent_benchmark_final.json`: merged final result used by this report.
