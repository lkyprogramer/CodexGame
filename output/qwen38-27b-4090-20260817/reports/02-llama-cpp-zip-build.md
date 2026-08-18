# Case 02: llama.cpp ZIP 构建

## 结果

- 本机固定 master commit：`4df29be4f4c3673f428170fda944a5b19f743bb8`
- ZIP SHA256：`2aa0ee8c4b4577a9ce74435f7267443587c0943a61f542fbfa0ca155a2339150`
- 远端源码：`/home/hhtele/llama.cpp-qwen38-20260817`
- CUDA compiler：CUDA 12.3，`nvcc`；CMake 3.25.1
- 构建：Release、CUDA FA、CUDA graphs、架构 89、静态库
- `llama-server`、`llama-cli`、`llama-bench`：均构建成功
- UI：使用 `LLAMA_BUILD_UI=OFF`、`LLAMA_USE_PREBUILT_UI=OFF`，未依赖 GitHub/HF UI 资产

ZIP、commit、校验文件保留在：`raw/remote/qwen38-27b-4090-20260817/source`。

## Binary 证据

```text
timestamp=2026-08-16T22:42:25-04:00
commit=4df29be4f4c3673f428170fda944a5b19f743bb8
nvcc=Build cuda_12.3.r12.3/compiler.33567101_0
cmake=cmake version 3.25.1
3d1195068639ff043805af6b95b400e5484aaf2bcf95a95c5ca846cd8af91ed8  /home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server
fc6e2fb5f79d8a2166f65ee9c8fdb42c339859adccacf5cbd4a42dc4c6ae2b64  /home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-cli
50bab8d39682e8c5c876cf3cab3206cb2eb108c372ab631fee45c47543ca77bd  /home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-bench
--- version ---
--- help ---
-sm,   --split-mode {none,layer,row,tensor}
-mg,   --main-gpu INDEX                 the GPU to use for the model (with split-mode = none), or for
                                        intermediate results and KV (with split-mode = row) (default: 0)
--spec-draft-type-k, -ctkd, --cache-type-k-draft TYPE
--spec-draft-type-v, -ctvd, --cache-type-v-draft TYPE
--spec-draft-hf, -hfd, -hfrd, --hf-repo-draft <user>/<model>[:quant]
--spec-draft-threads, -td, --threads-draft N
--spec-draft-threads-batch, -tbd, --threads-batch-draft N
--spec-draft-cpu-mask, -Cd, --cpu-mask-draft M
--spec-draft-cpu-range, -Crd, --cpu-range-draft lo-hi
--spec-draft-cpu-strict, --cpu-strict-draft <0|1>
--spec-draft-prio, --prio-draft N       set draft process/thread priority : 0-normal, 1-medium, 2-high,
--spec-draft-poll, --poll-draft <0|1>   Use polling to wait for draft model work (default: same as --poll)
--spec-draft-cpu-mask-batch, -Cbd, --cpu-mask-batch-draft M
--spec-draft-cpu-strict-batch, --cpu-strict-batch-draft <0|1>
--spec-draft-prio-batch, --prio-batch-draft N
--spec-draft-poll-batch, --poll-batch-draft <0|1>
--spec-draft-override-tensor, -otd, --override-tensor-draft <tensor name pattern>=<buffer type>,...
--spec-draft-cpu-moe, -cmoed, --cpu-moe-draft
--spec-draft-n-cpu-moe, --spec-draft-ncmoe, -ncmoed, --n-cpu-moe-draft N
--spec-draft-n-max N                    number of tokens to draft for speculative decoding (default: 3)
--spec-draft-n-min N                    minimum number of draft tokens to use for speculative decoding
--spec-draft-p-split, --draft-p-split P
--spec-draft-p-min, --draft-p-min P     minimum speculative decoding probability (greedy) (default: 0.00)
--spec-draft-backend-sampling, --no-spec-draft-backend-sampling
--spec-draft-device, -devd, --device-draft <dev1,dev2,..>
--spec-draft-ngl, -ngld, --gpu-layers-draft, --n-gpu-layers-draft N
--spec-draft-model, -md, --model-draft FNAME
--spec-type none,draft-simple,draft-eagle3,draft-mtp,draft-dflash,draft-dspark,ngram-simple,ngram-map-k,ngram-map-k4v,ngram-mod,ngram-cache
--draft, --draft-n, --draft-max N       the argument has been removed. use --spec-draft-n-max or
--draft-min, --draft-n-min N            the argument has been removed. use --spec-draft-n-min or
-cram, --cache-ram N                    set the maximum cache size in MiB (default: 8192, -1 - no limit, 0 -
                                        using unified KV (default: enabled, requires cache-ram)
--chat-template-kwargs STRING           sets additional params for the json template parser, must be a valid
--cache-prompt, --no-cache-prompt       whether to enable prompt caching (default: enabled)
--cache-reuse N                         min chunk size to attempt reusing from the cache via KV shifting,
--metrics                               enable prometheus compatible metrics endpoint (default: disabled)
--reasoning-format FORMAT               controls whether thought tags are allowed and/or extracted from the
                                        - deepseek: puts thoughts in `message.reasoning_content`
                                        also populating `message.reasoning_content`
-rea,  --reasoning [on|off|auto]        Use reasoning/thinking in the chat ('on', 'off', or 'auto', default:
--reasoning-effort LEVEL                reasoning effort level given to the chat template: 'default' to keep
--reasoning-budget N                    token budget for thinking: -1 for unrestricted, 0 for immediate end,
--reasoning-budget-message MESSAGE      message injected before the end-of-thinking tag when reasoning budget
--reasoning-preserve, --no-reasoning-preserve
                                        preserve reasoning trace in the full history, not just the last
                                        compatible with certain templates having 'supports_preserve_reasoning'
                                        reasoning and/or tool calls (default: disabled)

```

注意：ZIP 没有 `.git` 元数据，因此 binary version 显示 `commit unknown`；源码身份以 ZIP 内保存的 `4df29be4f4c3673f428170fda944a5b19f743bb8` 和本机 ZIP SHA256 为准。
