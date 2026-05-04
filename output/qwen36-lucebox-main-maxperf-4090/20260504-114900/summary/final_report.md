# Lucebox Main Qwen3.6-27B 4090 Max Performance Report

## 结论

- **short decode winner**: DFlash + DDTree + fast rollback, budget `26`, `n_gen=256`，HumanEval 10 prompts 全部成功，mean `152.73 tok/s`，AL `8.06`，accept `50.35%`。相对旧 Qwen3.6 + Qwen3.5 draft `72.95 tok/s`，约 `2.09x`。
- **long/agent winner**: 本轮不建议给出可上线 agent winner。TQ3 证明了 128K 容量可跑通，但该长 prompt 只生成 1 token，不能当作长上下文 decode 吞吐；server/cache agent loop 5 轮全是空内容，且短问答存在 thinking leakage。
- **PFlash/BSA**: `test_flashprefill_kernels` 通过，补装 CPU torch 后 PFlash 压缩阶段可用，32K/64K/128K 分别压到约 3.5K/3.5K/2.8K tokens；但生成阶段因 GGUF spec draft 恢复路径报 `safetensors: bad header length`，NIAH 未完成，不能作为 winner。
- **服务恢复**: 最终 `qwen35-35b-a3b-uncensored` 已恢复 active，`/v1/models` 回到 `hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M`。`openclaw-executor` 评测前就是 inactive，本轮结束仍为 inactive。

## 环境与构建

- 源码: `Luce-Org/lucebox-hub` archive commit `69ebfb9983c31bc28089fa493e8d791c4284bb9f`
- 部署目录: `/home/hhtele/lucebox-hub-main-maxperf-qwen36`
- target: `/data/models/qwen/Qwen3.6-27B-Q4_K_M.gguf`
- matched draft: `/data/models/qwen/dflash-draft-qwen36-q8/dflash-draft-3.6-q8_0.gguf`
- PFlash drafter: `/data/models/qwen/Qwen3-0.6B-BF16.gguf`
- CMake: `Release`, `CMAKE_CUDA_ARCHITECTURES=89`, `DFLASH27B_ENABLE_BSA=ON`, `DFLASH27B_FA_ALL_QUANTS=ON`
- GPU: RTX 4090, driver `545.23.08`, CUDA `12.3`, VRAM `24564 MiB`

## 关键兼容性补丁

最新版源码直接加载 public Qwen3.6 GGUF draft 会失败。部署副本中只改了 `dflash/src/gguf_draft_loader.cpp`，未改本地项目和 `/opt/llama.cpp`。补丁内容保存在 `patches/gguf_draft_loader.diff`。

- 接受 `general.architecture = dflash-draft`，不只接受 `qwen35-dflash-draft`。
- metadata prefix 改为读取实际 architecture，并在缺少 `dflash.n_target_layers` 时 fallback 到 `DFLASH27B_DRAFT_N_TARGET_LAYERS`。
- 增加 tensor alias: `dflash_fc.weight`, `dflash_hidden_norm.weight`, `post_attention_norm.weight`。

## Smoke

- `test_flashprefill_kernels`: returncode `0`, e2e S=8192 `[fp-test] e2e flash_prefill_forward_bf16 at S=8192: 2.7 ms / iter (avg of 5)`
- `scripts/run.py --kv-tq3 --fa-window 2048`: returncode `0`, elapsed `8.04s`，正文非空，但默认输出包含 thinking process。

## Decode Sweep

| budget | n_gen | success | mean tok/s | AL | accept % |
| --- | --- | --- | --- | --- | --- |
| 16 | 128 | 10/10 | 110.779 | 5.63 | 35.2 |
| 18 | 128 | 10/10 | 112.875 | 5.751 | 35.94 |
| 20 | 128 | 10/10 | 124.935 | 6.341 | 39.62 |
| 22 | 128 | 10/10 | 123.217 | 6.361 | 39.76 |
| 24 | 128 | 10/10 | 129.378 | 6.722 | 42.0 |
| 26 | 128 | 10/10 | 130.79 | 6.85 | 42.81 |
| 26 | 256 | 10/10 | 152.729 | 8.056 | 50.35 |
| 24 | 256 | 10/10 | 149.946 | 7.851 | 49.07 |

winner 是 `budget=26, n_gen=256`。单 prompt 波动较大，最高 `sum_product` 到 `237.42 tok/s`，最低 `below_zero` 约 `95.06 tok/s`；因此报告采用 10 prompt mean，不用单样本峰值。

## Long Context

| KV | ctx target | returncode | elapsed s | prefill tokens | prefill s | generated | decode tok/s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| tq3 | 32768 | 0 | 34.038 | 32789 | 27.45 | 1 | None |
| tq3 | 65536 | 0 | 77.173 | 65566 | 70.47 | 1 | None |
| tq3 | 131072 | 0 | 219.231 | 131120 | 212.17 | 1 | None |
| q4 | 32768 | 0 | 27.385 | 32789 | 20.44 | 64 | 276.61 |

TQ3 的结论是容量可用，不是长 decode winner：32K/64K/128K 都完成 prefill，但测试 prompt 在第一个 token 后结束。Q4 32K 能生成 64 token 且 `276.61 tok/s`，更像短 continuation 上限，不代表复杂长任务质量。

## PFlash / BSA

| ctx | keep | returncode | compressed | ratio | score s | needle hit | failure |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 32768 | 0.1 | 1 | 3466 | 10.1 | 4.8 | None | unpark draft safetensors bad header / BrokenPipe |
| 65536 | 0.05 | 1 | 3473 | 20.1 | 6.1 | None | unpark draft safetensors bad header / BrokenPipe |
| 131072 | 0.02 | 1 | 2755 | 50.8 | 11.3 | None | unpark draft safetensors bad header / BrokenPipe |

第一次 PFlash NIAH 因 venv 缺 PyTorch 在 tokenizer tensor 转换处失败。补装 CPU torch 后，压缩阶段已经跑通，说明 BSA/PFlash scorer 可执行；但生成阶段恢复 spec draft 时按 safetensors 路径读取 GGUF draft，导致 daemon 退出。这个问题应在 Lucebox 的 `DflashClient`/daemon park-unpark 逻辑里修，而不是继续调 keep ratio。

## Server / Cache

| check | status | elapsed/content |
| --- | --- | --- |
| GET /v1/models | 200 | 0.025s |
| non-stream chat | 200 | 1.428s, thinking_leakage=True |
| SSE stream chat | 200 | 1.200s, thinking_leakage=True |
| 5-turn agent loop | 200 each | content_len=[0, 0, 0, 0, 0] |

cache log counts: `{'prefix_hit': 0, 'full_cache_hit': 0, 'pflash': 2}`。server 证明 API wrapper 能启动并流式返回 token，但当前参数下不适合作为 agent profile：5 轮长 prompt completion 都是 0 token，prefix/full cache 没有命中，且 no-thinking 控制未生效。

## 建议

1. 短任务最大吞吐用 `test_dflash`/CLI 路径，`budget=26` 是当前 winner；如果要更保守可用 `budget=24`，mean `149.95 tok/s`，接近 winner。
2. 长上下文优先继续打磨 TQ3 容量 profile，但需要换不会立即 EOS 的 64K/128K coding prompt 重新测 decode，不要把本轮 1-token long 结果当质量结论。
3. PFlash 要先修 GGUF spec draft 的 park/unpark 兼容性，再重跑 NIAH；当前压缩速度有价值，但没有 needle 命中结果。
4. server/cache 暂不建议接入线上 agent。需要先解决 no-thinking、空 completion、cache hit，以及 PFlash + GGUF draft 兼容性。

## 产物

- `summary/derived_findings.json`
- `summary/maxperf_summary.json`
- `bench/decode_budget_sweep.json`
- `bench/tq3_long_context.json`
- `bench/pflash_niah.json` and `bench/pflash_niah_rerun_torch.json`
- `api/server_cache_agent_loop.json`
- `patches/gguf_draft_loader.diff`
- `summary/final_service_check_after_pflash_rerun.json`
