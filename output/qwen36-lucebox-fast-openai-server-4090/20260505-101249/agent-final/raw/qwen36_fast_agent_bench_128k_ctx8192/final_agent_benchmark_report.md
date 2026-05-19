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
- target_max_ctx: `8192`
- max_tokens: `128`
- turns_per_context: `5`

## Summary By Context

| context | source tokens | target tokens | cold full TPS | warm median full TPS | cold latency | warm median latency | cache hits/misses | GPU restores | daemon decode median |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 128K | 127243 | 6333 | 7.15 | 33.03 | 17.91s | 3.88s | 4/1 | 4 | 51.93 |

## Per-Turn Complete Inference Speed

| context | turn | wall latency | visible tokens | full output TPS | source tokens | target tokens | compression hit/miss | GPU restore | daemon prefill | daemon decode TPS | empty | thinking leak |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---|---|
| 128K | 1 | 17.91s | 128 | 7.15 | 127243 | 6333 | 0/1 | False | 4.038s | 48.67 | False | False |
| 128K | 2 | 3.79s | 128 | 33.80 | 127245 | 6335 | 1/0 | True | 0.054s | 55.64 | False | False |
| 128K | 3 | 3.97s | 128 | 32.26 | 127240 | 6330 | 1/0 | True | 0.056s | 51.93 | False | False |
| 128K | 4 | 4.05s | 128 | 31.61 | 127238 | 6328 | 1/0 | True | 0.055s | 50.44 | False | False |
| 128K | 5 | 3.61s | 128 | 35.44 | 127238 | 6328 | 1/0 | True | 0.052s | 62.07 | False | False |

## Notes

- `full output TPS` includes compression/cache lookup, GPU snapshot restore, target prefill, decode, HTTP/JSON overhead, and Python scheduling.
- `daemon decode TPS` is only the inner DFlash decode phase and is not the headline service metric.
- Cold turn includes first compression for the stable long context. Warm turns should hit disk compression cache and stable compressed-prefix GPU snapshot.
- Default service restored: `True`
