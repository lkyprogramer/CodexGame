# Lucebox Fast OpenAI Server 4090 Implementation Report

## Result

Implemented a new OpenAI-only fast server and daemon request protocol for Qwen3.6-27B DFlash. This validates the important path: dynamic small target context, parseable daemon perf, SSE chunking, and message-level PFlash compression cache.

This is not yet a full 32K/64K/128K agent benchmark. The smoke tests prove the server architecture works and that compressed-message cache survives GPU snapshot limitations.

## Code Changes

- `dflash/scripts/server_fast.py`: new OpenAI Chat Completions server for `/v1/models` and `/v1/chat/completions` only.
- `dflash/test/test_dflash.cpp`: added `REQ` daemon command, request-level `max_ctx` cache rebuild, request `budget/fa_window`, inline snapshot status, and `[perf]` JSON line.
- Existing legacy daemon commands are preserved for `scripts/run.py`, `bench_he.py`, and old `server.py`.

## 4090 Validation

- Remote build: `test_dflash` built successfully.
- Remote build: `test_flashprefill_kernels` built successfully.
- OpenAI `/v1/models`: passed on port `18345`.
- OpenAI non-streaming chat: passed.
- OpenAI SSE streaming chat: passed with 4-token chunking.
- Default service restored: `hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M`.

## Short API Smoke

- route: `short_direct`
- target max ctx: `256`
- wall visible TPS: `16.13` tok/s
- daemon decode TPS: `189.88` tok/s
- daemon decode time: `0.337` s

The daemon-side decode speed is now visible separately from API wall time. The first non-stream request includes startup/cache rebuild overhead, so wall TPS is not the steady-state short prompt metric.

## PFlash Cache Smoke

Turn 1:
- elapsed: `7.81` s
- source prompt: `1580` tokens
- compressed target prompt: `76` tokens
- compression hits/misses: `0` / `1`
- daemon decode TPS: `49.37` tok/s
- snapshot ok: `True`

Turn 2:
- elapsed: `1.33` s
- compression hits/misses: `1` / `0`
- daemon decode TPS: `51.73` tok/s
- snapshot restore hit: `False`

The key result is that turn 2 skips PFlash recompression via disk compressed-message cache. GPU full snapshot did not restore in this smoke because the rendered full prompt changed per turn; that is expected for the current full-prompt snapshot key.

## Artifacts

- `summary/perf_breakdown.json`
- `api/qwen36_fast_server_smoke/`
- `api/qwen36_fast_pflash_smoke/`
- `build/qwen36_fast_build.log`
- `build/qwen36_fast_cmake.log`

## Remaining Work

- Run the full 32K/64K/128K PFlash + agent loop benchmark with stable long context split into separate messages.
- Add a message-prefix GPU snapshot strategy if we want GPU restore hits across changing agent turns; disk compressed-message cache already works.
- Move FastAPI lifecycle from deprecated `on_event` to lifespan when cleaning up API warnings.
