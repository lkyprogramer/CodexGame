# Qwen3.6 Lucebox Fast OpenAI Server Agent Benchmark

Main metric is complete end-to-end output speed per API call: `visible output tokens / wall elapsed seconds`. Daemon decode TPS is reported separately.

## Config

- target: `/data/models/qwen/Qwen3.6-27B-Q4_K_M.gguf`
- draft: `/data/models/qwen/dflash-draft-qwen36-q8/dflash-draft-3.6-q8_0.gguf`
- drafter: `/data/models/qwen/Qwen3-0.6B-BF16.gguf`
- kv: `tq3_0`
- fa_window: `2048`
- budget: `26`
- keep_ratio: `0.05`
- target_max_ctx: `16384`
- max_tokens: `128`
- turns_per_context: `5`

## Summary By Context

| context | source tokens | target tokens | cold full TPS | warm median full TPS | cold latency | warm median latency | cache hits/misses | GPU restores | daemon decode median |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 32K | 32278 | 1601 | 10.52 | 38.06 | 12.16s | 3.37s | 4/1 | 4 | 54.89 |
| 64K | 65274 | 3255 | 10.66 | 39.02 | 12.00s | 3.30s | 4/1 | 4 | 53.65 |
| 128K | 127243 | 6333 | 6.99 | 15.75 | 18.31s | 8.13s | 4/1 | 0 | 52.18 |

## Per-Turn Complete Inference Speed

| context | turn | wall latency | visible tokens | full output TPS | source tokens | target tokens | compression hit/miss | GPU restore | daemon prefill | daemon decode TPS | empty | thinking leak |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---|---|
| 32K | 1 | 12.16s | 128 | 10.52 | 32278 | 1601 | 0/1 | False | 4.168s | 62.88 | False | False |
| 32K | 2 | 3.67s | 128 | 34.88 | 32280 | 1603 | 1/0 | True | 0.122s | 47.62 | False | False |
| 32K | 3 | 3.49s | 128 | 36.67 | 32275 | 1598 | 1/0 | True | 0.092s | 49.98 | False | False |
| 32K | 4 | 3.24s | 128 | 39.45 | 32273 | 1596 | 1/0 | True | 0.091s | 54.89 | False | False |
| 32K | 5 | 2.93s | 128 | 43.69 | 32273 | 1596 | 1/0 | True | 0.092s | 65.03 | False | False |
| 64K | 1 | 12.00s | 128 | 10.66 | 65274 | 3255 | 0/1 | False | 2.230s | 53.65 | False | False |
| 64K | 2 | 2.94s | 128 | 43.56 | 65276 | 3257 | 1/0 | True | 0.050s | 70.21 | False | False |
| 64K | 3 | 3.59s | 128 | 35.70 | 65271 | 3252 | 1/0 | True | 0.048s | 52.71 | False | False |
| 64K | 4 | 3.53s | 128 | 36.28 | 65269 | 3250 | 1/0 | True | 0.047s | 53.22 | False | False |
| 64K | 5 | 3.07s | 128 | 41.76 | 65269 | 3250 | 1/0 | True | 0.047s | 62.20 | False | False |
| 128K | 1 | 18.31s | 128 | 6.99 | 127243 | 6333 | 0/1 | False | 4.311s | 49.81 | False | False |
| 128K | 2 | 7.51s | 128 | 17.05 | 127245 | 6335 | 1/0 | False | 4.355s | 69.15 | False | False |
| 128K | 3 | 8.21s | 128 | 15.58 | 127240 | 6330 | 1/0 | False | 4.307s | 48.74 | False | False |
| 128K | 4 | 8.25s | 128 | 15.52 | 127238 | 6328 | 1/0 | False | 4.353s | 52.18 | False | False |
| 128K | 5 | 8.04s | 128 | 15.92 | 127238 | 6328 | 1/0 | False | 4.403s | 57.68 | False | False |

## Notes

- `full output TPS` includes compression/cache lookup, GPU snapshot restore, target prefill, decode, HTTP/JSON overhead, and Python scheduling.
- `daemon decode TPS` is only the inner DFlash decode phase and is not the headline service metric.
- Cold turn includes first compression for the stable long context. Warm turns should hit disk compression cache and stable compressed-prefix GPU snapshot.
- Default service restored: `True`
