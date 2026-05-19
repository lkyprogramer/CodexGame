# TurboQuant PR #146 / Qwen3.6 MTP4 4090 测试评估报告

测试日期：2026-05-18  
4090 访问路径：`direct-192.168.10.29`  
测试机器：RTX 4090 24GB，Driver 545.23.08，CUDA Toolkit 12.3.107  
模型：`/data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf`  
目标：验证 TurboQuant PR #146 的 CUDA 构建能否作为 OpenClaw Qwen3.6 MTP4 的下一轮 128k/196k/262k 优化路线。

## 1. 结论

本轮 **不建议继续测试 TurboQuant PR #146 的 Turbo KV lane，也不建议替换当前生产服务**。

原因很明确：Phase 0 control 已失败。即使不用 Turbo KV，只使用 PR #146 binary 的 `q4_0/q4_0 + draft-mtp n=4 + ctx32`，输出已经退化为连续 `/`，draft accept 为 `0.0`，平均 decode 只有 `26.16 tok/s`。这不是 TurboQuant KV 参数好坏的问题，而是 PR #146 当前 CUDA 构建在这个 Qwen3.6 MTP GGUF 上基础生成不可用。

为了排除 speculative/MTP 本身导致的问题，我补跑了同一个 PR #146 binary 的 no-spec 诊断：关闭 `--spec-type draft-mtp` 后，`short_ok` 和 `json_tool` 仍然输出连续 `/`。因此判断为 **PR #146 当前分支与该 Qwen3.6 GGUF / CUDA 推理路径存在基础兼容性问题**，不具备继续跑 128k/196k/262k 的前提。

生产服务已恢复并二次验证：

```text
openclaw-qwen36-mtp4-128k.service: active
openclaw-qwen36-mtp4-128k.service: enabled
127.0.0.1:18343/v1/models: OK
192.168.10.29:28343/v1/models with token: OK
192.168.10.29:28343/v1/models without token: 401
GPU after restore: 21866 MiB used / 24564 MiB total
```

## 2. 构建结果

构建目录：

```text
/home/hhtele/llama.cpp-turboquant-pr146-20260518
```

测试目录：

```text
/home/hhtele/qwen36-turboquant-pr146-20260518
```

构建 commit：

```text
COMMIT eef2db439
version: 9409 (eef2db439)
ggml commit: eef2db439
CUDA Toolkit: 12.3.107
CMAKE_CUDA_ARCHITECTURES=89
```

构建能力检查通过：

```text
HELP_CHECK_DRAFT_MTP=1
HELP_CHECK_TURBO2=4
HELP_CHECK_TURBO3=4
HELP_CHECK_TURBO4=4
```

这说明 PR #146 分支本身可以在 4090 上完成 CUDA 构建，并且 CLI 层面具备 `draft-mtp` 和 `turbo2/turbo3/turbo4` 参数能力。失败发生在实际推理输出质量和 draft accept，而不是构建阶段。

## 3. Phase 0 Control 结果

启动参数：

```bash
/home/hhtele/llama.cpp-turboquant-pr146-20260518/build/bin/llama-server \
  -m /data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf \
  --alias openclaw/tq146_q4q4_n4_ctx32 \
  -ngl 99 \
  -c 32768 \
  -np 1 \
  -fa on \
  -ctk q4_0 \
  -ctv q4_0 \
  -rea off \
  --temp 0 \
  --top-p 1 \
  --cache-prompt \
  --cache-ram 2048 \
  --host 127.0.0.1 \
  --port 19343 \
  --spec-type draft-mtp \
  --spec-draft-p-min 0.75 \
  --spec-draft-n-max 4
```

汇总：

| 指标 | 结果 |
|---|---:|
| case 成功率 | 6/6 HTTP 成功 |
| 平均 decode | 26.16 tok/s |
| max decode | 28.11 tok/s |
| draft accept | 0.000 |
| 平均格式分 | 2.33 |
| 平均质量分 | 2.33 |
| think leak | 0 |
| 峰值显存 | 19432 MiB |
| 峰值功耗 | 433.39 W |
| GPU 峰值利用率 | 96% |

逐 case：

| case | HTTP | decode tok/s | accept | 格式 | 质量 | 输出摘要 |
|---|---:|---:|---:|---:|---:|---|
| `stream_ttft_ok` | OK | N/A | N/A | 2.0 | 2.0 | `////////` |
| `short_ok` | OK | 28.11 | 0.0 | 1.0 | 1.0 | `////////` |
| `json_tool` | OK | 25.89 | 0.0 | 1.0 | 2.0 | 连续 `/`，不是 JSON |
| `patch_unified_diff` | OK | 25.69 | 0.0 | 1.0 | 2.5 | 连续 `/`，不是 diff |
| `code_review_cn` | OK | 25.64 | 0.0 | 4.5 | 2.5 | 连续 `/`，无有效 review |
| `long_generation_1024` | OK | 25.49 | 0.0 | 4.5 | 4.0 | 连续 `/`，无有效内容 |

与上一轮 upstream baseline 对比：

| 配置 | ctx | KV | MTP | 平均 decode | long output | draft accept | 质量 |
|---|---:|---|---|---:|---:|---:|---:|
| upstream `4f13cb7` | 32768 | `q4_0/q4_0` | `draft-mtp n=4` | 71.96 | 62.79 | 0.710 | 4.67 |
| TurboQuant PR #146 `eef2db439` | 32768 | `q4_0/q4_0` | `draft-mtp n=4` | 26.16 | 25.49 | 0.000 | 2.33 |

该 control 未达到继续测试门槛：

```text
required: quality >= 4.5, no severe output corruption
actual: quality = 2.33, output = repeated slash tokens
```

因此 Phase 1/2/3 按计划停止，未继续跑 Turbo KV / 128k / 196k / 262k，避免浪费测试时间并避免长时间占用生产服务。

## 4. No-spec 诊断

为确认问题是否只来自 `draft-mtp`，补跑同一 PR #146 binary，不带 speculative 参数：

```bash
/home/hhtele/llama.cpp-turboquant-pr146-20260518/build/bin/llama-server \
  -m /data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf \
  --alias openclaw/tq146_no_spec_diag \
  -ngl 99 \
  -c 32768 \
  -np 1 \
  -fa on \
  -ctk q4_0 \
  -ctv q4_0 \
  -rea off \
  --temp 0 \
  --top-p 1 \
  --cache-prompt \
  --cache-ram 2048 \
  --host 127.0.0.1 \
  --port 19343
```

结果：

| case | 输出 |
|---|---|
| `short_ok` | `////////` |
| `json_tool` | `////////////////////////////////////////////////////////////////////////////////` |

结论：关闭 speculative 后仍然输出连续 `/`，说明问题不是 `draft-mtp` 接受率本身，而是 PR #146 当前构建在该模型上的基础解码路径已经不可用。

## 5. 判断与建议

### 5.1 当前不应继续跑 Turbo KV 矩阵

原计划中的 TurboQuant KV lane：

```text
q4_0/turbo4
q4_0/turbo3
q4_0/turbo2 + TURBO_LAYER_ADAPTIVE=7
q8_0/turbo4
```

都依赖 Phase 0 control 先证明 PR #146 binary 对 `q4_0/q4_0` 基础推理无回归。现在 control 已失败，继续跑 Turbo KV 无法区分是 Turbo KV 的效果，还是 PR 分支基础生成已损坏。

### 5.2 不建议替换现有 OpenClaw 服务

当前生产服务仍然是更稳的旧 MTP 分支：

```text
/home/hhtele/llama.cpp-mtp-unsloth-20260513/build/bin/llama-server
--spec-type mtp
--spec-draft-n-max 4
-c 131072
-ctk q4_0
-ctv q4_0
```

该服务已恢复，且上一轮 128k 测试可用。PR #146 当前不具备替换条件。

### 5.3 后续如果继续攻关 TurboQuant，应先做源码级兼容性定位

下一轮不应直接继续性能测试，而应先定位 PR #146 的基础输出退化问题：

1. 对比 upstream `4f13cb7` 与 TQ PR `eef2db439` 的 Qwen3.5/Qwen3.6 模型加载路径。
2. 检查 Qwen3.6 MTP GGUF 的 tokenizer / chat template / output head / draft head 是否在 TQ 分支被错误解释。
3. 用 `llama-cli` 而不是 server 做最小 prompt 复现，排除 server chat wrapper。
4. 用非 MTP Qwen GGUF 或小模型做 sanity，判断是 Qwen3.6 MTP 专属问题还是 TQ CUDA 全局问题。
5. 如果 `llama-cli` 也连续输出 `/`，再查 logits、token id、sampling 和 quantized matmul 路径。

只有当 `q4_0/q4_0` no-spec 和 `draft-mtp` control 都恢复正常后，才值得回到 Turbo KV 128k/196k/262k 性能测试。

## 6. 产物

本机目录：

```text
/Users/luo/Documents/github/CodexGame/output/qwen36-4090-turboquant-pr146-20260518
```

关键文件：

```text
remote/build_turboquant_pr146.sh
remote/qwen4090_turboquant_pr146_eval.py
remote/run_turboquant_pr146_eval_wrapper.sh
raw/remote-copy/logs/build.log
raw/remote-copy/logs/eval-wrapper.log
raw/remote-copy/logs/pre-eval-status.log
raw/remote-copy/logs/restore-status.log
raw/remote-copy/results/summary.json
raw/remote-copy/results/tq146_q4q4_n4_ctx32.json
raw/remote-copy/results/no_spec_diag.json
raw/remote-copy/results/server_logs/*.log
```

注意：`restore-status.log` 中第一次恢复验证过早，18343 尚未完成启动，出现了一次 502/connection refused；随后已补做二次 live 验证，确认生产服务正常。

