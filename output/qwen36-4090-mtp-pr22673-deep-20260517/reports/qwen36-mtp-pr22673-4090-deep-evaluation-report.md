# Qwen3.6 27B MTP / PR #22673 4090 深度测试评估报告

测试日期：2026-05-17  
测试机器：RTX 4090 24GB，Driver 545.23.08，CUDA Toolkit 12.3.107  
测试目标：验证 llama.cpp PR #22673 merge 后的 `draft-mtp` 参数，对 OpenClaw 单并发、128k、prompt cache、MTP4 基础模型场景的性能与质量影响。  
测试结论状态：已完成测试；原 `openclaw-qwen36-mtp4-128k.service` 已恢复并验证 active/enabled。

## 1. 直接结论

1. PR #22673 已进入 llama.cpp master，本轮成功编译并实测新参数 `--spec-type draft-mtp`、`--spec-draft-p-min`、`--spec-draft-n-max`。
2. 对 OpenClaw 的 128k 单并发服务，`--spec-draft-n-max 4` 仍可作为 MTP4 基础 profile 使用：8/8 case 成功，128k profile 峰值显存 21,746 MiB，长上下文 exact prompt cache 二次请求从 38.89s 降到 1.16s，约 33.39x 加速。
3. 但如果目标是长输出持续 decode 吞吐，`n-max=2` 更稳：`long_generation_1024` 为 67.51 tok/s，`n-max=4` 为 62.44 tok/s，`n-max=6` 退回 50.48 tok/s。
4. `--spec-draft-p-min 0.75` 在本轮 4090 + Q4_K_XL 任务集上没有带来可见收益：`n=4,p=0.75` 与 `n=4,p=0.0` 基本相同。
5. `ngram-mod,draft-mtp` 可以启动且质量正常，但吞吐低于纯 `draft-mtp n=2/n=4`，暂不建议进入 OpenClaw 默认链路。
6. `q8_0` KV 没有带来质量或吞吐优势，但显存更高；128k 24GB 4090 上继续使用 `q4_0` KV。
7. 256k 不建议作为当前主线。本轮没有重复跑 256k OOM，因为上一轮已有证据显示 `-c 262144 -np 1` 在 prompt processing 约 53k processed tokens 附近 CUDA OOM；本轮 128k MTP4 已经峰值 21.7GB，显存余量不足以让 256k 成为可靠服务 profile。

## 2. 测试环境与版本

### 2.1 远端服务状态

测试前：

```text
openclaw-qwen36-mtp4-128k.service: active
openclaw-qwen36-mtp4-128k.service: enabled
GPU before: 22058 MiB used / 24564 MiB total
```

测试后恢复验证：

```text
openclaw-qwen36-mtp4-128k.service: active
openclaw-qwen36-mtp4-128k.service: enabled
18343 /v1/models: OK
28343 /v1/models with token: OK
28343 /v1/models without token: 401 Unauthorized
GPU after restore: 21866 MiB used / 24564 MiB total
```

当前恢复后的生产服务仍是原服务：

```bash
/home/hhtele/llama.cpp-mtp-unsloth-20260513/build/bin/llama-server \
  -m /data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf \
  --alias openclaw/Qwen3.6-27B-MTP-Q4XL \
  -ngl 99 \
  -c 131072 \
  -np 1 \
  -fa on \
  -ctk q4_0 \
  -ctv q4_0 \
  --spec-type mtp \
  --spec-draft-n-max 4 \
  -rea off \
  --temp 0 \
  --top-p 1 \
  --cache-prompt \
  --cache-reuse 256 \
  --cache-ram 2048 \
  --slot-prompt-similarity 0.10 \
  --host 0.0.0.0 \
  --port 18343
```

### 2.2 新 llama.cpp 构建

新构建目录：

```text
/home/hhtele/llama.cpp-master-pr22673-20260517
```

构建版本：

```text
llama-server version: 1 (4f13cb7)
ggml commit: 4f13cb7
CUDA Toolkit: 12.3.107
CMAKE_CUDA_ARCHITECTURES=89
```

关键构建参数：

```bash
cmake -S . -B build \
  -DBUILD_SHARED_LIBS=OFF \
  -DLLAMA_BUILD_UI=OFF \
  -DLLAMA_BUILD_WEBUI=OFF \
  -DGGML_CUDA=ON \
  -DGGML_CUDA_FA=ON \
  -DGGML_CUDA_GRAPHS=ON \
  -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc \
  -DCMAKE_CUDA_ARCHITECTURES=89 \
  -DCMAKE_BUILD_TYPE=Release
```

新二进制 help 已确认：

```text
--spec-type none,draft-simple,draft-eagle3,draft-mtp,ngram-simple,ngram-map-k,ngram-map-k4v,ngram-mod,ngram-cache
--spec-draft-p-min default: 0.75
--cache-ram default: 8192 MiB
--no-mmproj supported
```

## 3. 测试方法

所有性能测试均为单并发 `-np 1`，端口 `127.0.0.1:19343`，测试前停止原 18343 systemd 服务，测试结束后自动恢复。

基础启动参数：

```bash
llama-server \
  -m /data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf \
  -ngl 99 \
  -np 1 \
  -fa on \
  -rea off \
  --temp 0 \
  --top-p 1 \
  --cache-prompt \
  --cache-ram 2048 \
  --host 127.0.0.1 \
  --port 19343
```

测试 case：

| case | 目的 | 人工评分重点 |
|---|---|---|
| `stream_ttft_ok` | 首字响应 / TTFT | 是否快速返回 `OK` |
| `short_ok` | 短响应 | 格式是否严格 |
| `json_tool` | JSON 工具调用 | 是否 JSON-only，可解析，字段完整 |
| `patch_unified_diff` | 代码 patch | 是否 unified diff，是否有无关说明 |
| `code_review_cn` | 中文代码审查 | 是否指出异步并发、错误传播、一致性问题 |
| `long_generation_1024` | 长输出持续 decode | 连贯性、重复度、是否跑偏 |
| `long_context_marker` | 长上下文定位与 prompt cache | marker 是否准确、cache 是否命中 |

评分标准：

| 分数 | 含义 |
|---:|---|
| 5.0 | 完全满足格式与任务要求 |
| 4.5 | 满足核心要求，有轻微冗余或不够精炼 |
| 4.0 | 可用但内容泛化、重复或信息密度不足 |
| <4.0 | 结构或质量明显影响 OpenClaw 使用 |

## 4. 总体结果

| 配置 | ctx | KV | spec | 成功 | 持续 decode tok/s | 平均 decode tok/s | max decode | accept | 质量 | 格式 | 峰值显存 MiB | cache 加速 |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `old_mtp_n4_q4_ctx32` | 32768 | q4_0 | `--spec-type mtp --spec-draft-n-max 4` | 6/6 | 50.44 | 88.09 | 136.06 | 0.988 | 4.67 | 4.83 | 20222 |  |
| `new_draft_n2_p075_q4_ctx32` | 32768 | q4_0 | `--spec-type draft-mtp --spec-draft-p-min 0.75 --spec-draft-n-max 2` | 6/6 | 67.97 | 72.25 | 87.86 | 0.845 | 4.67 | 4.83 | 19128 |  |
| `new_draft_n3_p075_q4_ctx32` | 32768 | q4_0 | `--spec-type draft-mtp --spec-draft-p-min 0.75 --spec-draft-n-max 3` | 6/6 | 66.71 | 73.61 | 103.07 | 0.755 | 4.67 | 4.83 | 19290 |  |
| `new_draft_n4_p075_q4_ctx32` | 32768 | q4_0 | `--spec-type draft-mtp --spec-draft-p-min 0.75 --spec-draft-n-max 4` | 6/6 | 62.79 | 71.96 | 99.67 | 0.710 | 4.67 | 4.83 | 19448 |  |
| `new_draft_n4_p000_q4_ctx32` | 32768 | q4_0 | `--spec-type draft-mtp --spec-draft-p-min 0.0 --spec-draft-n-max 4` | 6/6 | 62.75 | 71.98 | 99.82 | 0.710 | 4.67 | 4.83 | 19448 |  |
| `new_draft_n6_p075_q4_ctx32` | 32768 | q4_0 | `--spec-type draft-mtp --spec-draft-p-min 0.75 --spec-draft-n-max 6` | 6/6 | 50.77 | 64.02 | 95.04 | 0.577 | 4.67 | 4.83 | 19758 |  |
| `new_ngram_draft_n2_p075_q4_ctx32` | 32768 | q4_0 | `--spec-type ngram-mod,draft-mtp --spec-draft-p-min 0.75 --spec-draft-n-max 2 --spec-ngram-mod-n-match 24 --spec-ngram-mod-n-min 48 --spec-ngram-mod-n-max 64` | 6/6 | 58.09 | 68.83 | 90.71 | 0.959 | 4.67 | 4.83 | 18966 |  |
| `new_draft_n2_p075_q8_ctx32` | 32768 | q8_0 | `--spec-type draft-mtp --spec-draft-p-min 0.75 --spec-draft-n-max 2` | 6/6 | 66.43 | 73.03 | 90.20 | 0.856 | 4.67 | 4.83 | 19672 |  |
| `new_draft_n2_p075_q4_ctx64` | 65536 | q4_0 | `--spec-type draft-mtp --spec-draft-p-min 0.75 --spec-draft-n-max 2` | 6/6 | 67.88 | 72.13 | 86.96 | 0.845 | 4.67 | 4.83 | 19740 |  |
| `new_draft_n2_p075_q8_ctx64` | 65536 | q8_0 | `--spec-type draft-mtp --spec-draft-p-min 0.75 --spec-draft-n-max 2` | 6/6 | 66.28 | 72.88 | 89.94 | 0.856 | 4.67 | 4.83 | 20828 |  |
| `new_draft_n2_p075_q4_ctx128_cache` | 131072 | q4_0 | `--spec-type draft-mtp --spec-draft-p-min 0.75 --spec-draft-n-max 2` | 8/8 | 67.51 | 68.78 | 86.77 | 0.889 | 4.75 | 4.88 | 21422 | 30.42x |
| `new_draft_n4_p075_q4_ctx128_cache` | 131072 | q4_0 | `--spec-type draft-mtp --spec-draft-p-min 0.75 --spec-draft-n-max 4` | 8/8 | 62.44 | 72.11 | 99.13 | 0.793 | 4.75 | 4.88 | 21746 | 33.39x |
| `new_draft_n6_p075_q4_ctx128_probe` | 131072 | q4_0 | `--spec-type draft-mtp --spec-draft-p-min 0.75 --spec-draft-n-max 6` | 7/7 | 50.48 | 68.52 | 94.14 | 0.636 | 4.71 | 4.86 | 21828 |  |

说明：

- `持续 decode tok/s` 取 `long_generation_1024`，更接近 OpenClaw 长输出生成能力。
- `平均 decode tok/s` 会被短输出和 JSON case 拉高或拉低，不应单独作为容量判断。
- 长上下文 prompt cache case 的 `平均 prompt tok/s` 会因为 warm cache 命中而异常高，应单独看第 5 节。

## 5. 长上下文与 prompt cache

本轮 128k profile 使用约 57,411 prompt tokens 的长上下文 marker 测试做 cold/warm 两次 exact-repeat。

| 配置 | rep | prompt tokens | cache_n | elapsed s | prompt tok/s | decode tok/s | response tok/s | prompt_ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `n2_ctx128_cache` | 1 | 57411 | 0 | 38.89 | 1509 | 64.58 | 0.80 | 38040.7 |
| `n2_ctx128_cache` | 2 | 57411 | 57407 | 1.28 | 335560 | 56.70 | 24.25 | 171.1 |
| `n4_ctx128_cache` | 1 | 57411 | 0 | 38.89 | 1507 | 74.43 | 0.80 | 38104.9 |
| `n4_ctx128_cache` | 2 | 57411 | 57407 | 1.16 | 326605 | 72.32 | 26.62 | 175.8 |
| `n6_ctx128_probe` | 1 | 28745 | 0 | 18.11 | 1640 | 92.87 | 1.66 | 17530.1 |

结论：

1. `--cache-prompt` exact-repeat 确认有效。`n4` warm cache 从 38.89s 降到 1.16s，cache 命中 `57407/57411` tokens。
2. 该 cache 主要节省 prompt processing，而不是直接提升长输出 decode。长输出持续 decode 仍由 `long_generation_1024` 更能代表。
3. `n4` 在长上下文 marker 的 warm decode/response 上优于 `n2`，但在 1024 长输出持续生成上低于 `n2`。
4. 128k MTP4 已接近显存边界：峰值 21.75GB，测试后恢复服务常驻约 21.87GB used，留给 256k、q8 KV 或并发的空间很小。

## 6. 各参数结论

### 6.1 `draft-mtp` vs 旧 `mtp`

PR #22673 merge 后的 master 要使用：

```bash
--spec-type draft-mtp
```

旧 20260513 分支仍使用：

```bash
--spec-type mtp
```

在本轮任务集上，旧 `mtp n=4` 的平均 decode 被短响应拉高到 88.09 tok/s，但长输出持续 decode 只有 50.44 tok/s。新 `draft-mtp n=2/n=3/n=4` 的长输出持续 decode 分别为 67.97 / 66.71 / 62.79 tok/s，实际更适合长输出。

### 6.2 `--spec-draft-n-max`

| n-max | ctx32 long_generation_1024 | ctx128 long_generation_1024 | 结论 |
|---:|---:|---:|---|
| 2 | 67.97 tok/s | 67.51 tok/s | 长输出最佳，显存最低，推荐保守默认 |
| 3 | 66.71 tok/s | 未跑 128k | 与 n2 接近，可作为备选 |
| 4 | 62.79 tok/s | 62.44 tok/s | OpenClaw MTP4 可用，长上下文 cache 表现最好 |
| 6 | 50.77 tok/s | 50.48 tok/s | draft 过多导致 accept 下降，暂不推荐 |

`n=6` 的 accept 在长输出 case 只有 0.274，吞吐退回旧水平；不要为了追求“更多 draft token”直接上 6。

### 6.3 `--spec-draft-p-min`

本轮对 `n=4` 做了 `p-min=0.75` 和 `p-min=0.0` 对比：

| 参数 | 平均 decode | long_generation_1024 | accept |
|---|---:|---:|---:|
| `p-min=0.75` | 71.96 | 62.79 | 0.710 |
| `p-min=0.0` | 71.98 | 62.75 | 0.710 |

结论：4090 + Q4_K_XL + 当前任务集上，`p-min=0.75` 没有明显收益，也没有负收益。保持默认 `0.75` 即可，不建议把它作为主要调参方向。

### 6.4 `ngram-mod,draft-mtp`

组合参数能启动：

```bash
--spec-type ngram-mod,draft-mtp \
--spec-draft-p-min 0.75 \
--spec-draft-n-max 2 \
--spec-ngram-mod-n-match 24 \
--spec-ngram-mod-n-min 48 \
--spec-ngram-mod-n-max 64
```

但结果不适合当前 CUDA 4090 默认服务：

```text
long_generation_1024: 58.09 tok/s
avg decode: 68.83 tok/s
quality/format: 与其他 profile 基本一致
```

虽然 accept 高达 0.959，但 wall/decode 没有转化成收益。建议仅作为后续专项实验，不进入 OpenClaw 默认。

### 6.5 KV cache 类型

| 配置 | ctx | KV | long_generation_1024 | 峰值显存 |
|---|---:|---|---:|---:|
| `n2_q4_ctx32` | 32k | q4_0 | 67.97 | 19128 MiB |
| `n2_q8_ctx32` | 32k | q8_0 | 66.43 | 19672 MiB |
| `n2_q4_ctx64` | 64k | q4_0 | 67.88 | 19740 MiB |
| `n2_q8_ctx64` | 64k | q8_0 | 66.28 | 20828 MiB |

结论：q8 KV 没有质量提升，也没有吞吐收益，显存更高。128k 主线应继续 `-ctk q4_0 -ctv q4_0`。

## 7. 质量评估

人工复核重点：

1. JSON 输出：所有被抽查配置均为严格 JSON，无 markdown 包裹，可解析，字段完整，5.0/5.0。
2. unified diff：输出是标准 diff，变更点正确；轻微问题是 patch 偏短、没有更完整上下文，质量 4.5，格式 5.0。
3. 中文 code review：能稳定指出 `forEach + async` 不等待、错误静默、并发写入一致性/连接池风险；有时会附带较长示例，格式 4.5，质量 4.5。
4. 长输出：能连续输出 1024 token，但内容偏泛化、信息密度下降，质量 4.0，格式 4.5。这类任务是最能拉开持续 decode 差距的 case。
5. 长上下文 marker：n2/n4 的 cold/warm 两次均准确返回 marker，质量和格式均 5.0。
6. 未发现 `<think>` 泄露：`think_leak_count=0`。

OpenClaw 风险判断：

- 对 JSON-only / tool-call / patch 类短结构化输出，MTP 参数变化未造成格式风险。
- 对长文本计划/报告类输出，MTP 不会明显破坏质量，但 `n=6` accept 下降后吞吐变差，没有质量收益。
- 质量差异小于性能差异，因此 profile 选择应主要依据吞吐、显存和 prompt cache 行为。

## 8. 推荐配置

### 8.1 OpenClaw MTP4 128k 主 profile

如果坚持以 MTP4 作为 OpenClaw 基础模型，建议使用新 master 的如下配置做下一版候选服务：

```bash
/home/hhtele/llama.cpp-master-pr22673-20260517/build/bin/llama-server \
  -m /data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf \
  --alias openclaw/Qwen3.6-27B-MTP-Q4XL \
  -ngl 99 \
  -c 131072 \
  -np 1 \
  -fa on \
  -ctk q4_0 \
  -ctv q4_0 \
  -rea off \
  --temp 0 \
  --top-p 1 \
  --cache-prompt \
  --cache-ram 2048 \
  --spec-type draft-mtp \
  --spec-draft-p-min 0.75 \
  --spec-draft-n-max 4 \
  --host 0.0.0.0 \
  --port 18343
```

该配置适合：

- 128k 单并发长上下文；
- OpenClaw 重复前缀明显、prompt cache 能命中的 agent 循环；
- 短结构化输出、patch、code review、marker retrieval；
- 接受约 21.7GB 峰值显存占用。

### 8.2 更稳的长输出 profile

如果 OpenClaw 的下一阶段更偏长报告、长代码生成、长解释，建议改为：

```bash
--spec-type draft-mtp \
--spec-draft-p-min 0.75 \
--spec-draft-n-max 2
```

理由：

- 128k 长输出持续 decode：67.51 tok/s，高于 n4 的 62.44 tok/s。
- 峰值显存：21,422 MiB，低于 n4 的 21,746 MiB。
- 质量评分不低于 n4。

### 8.3 不推荐项

```text
--spec-draft-n-max 6
```

不推荐作为常驻服务。accept 下降明显，长输出吞吐退回 50 tok/s 量级。

```text
-ctk q8_0 -ctv q8_0
```

不推荐用于 128k 24GB 4090。显存增加，质量与吞吐未改善。

```text
--spec-type ngram-mod,draft-mtp
```

当前不推荐默认启用。可以专项测试代码补丁大量重复上下文，但本轮没有收益。

## 9. 128k / 256k 边界

128k 当前可以稳定作为主线，但应控制以下边界：

1. 单并发：继续 `-np 1`。
2. KV：继续 q4_0。
3. prompt cache：保留 `--cache-prompt --cache-ram 2048`。
4. 128k prompt 不等于可以塞满 131072 tokens 后再要求大量输出。上一轮已经出现 `prompt_tokens=131866 > n_ctx=131072` 的 HTTP 400。
5. 256k 暂不进主线。已有失败形态：

```text
-c 262144 -np 1
约 240k / 255k prompt
prompt processing 阶段 CUDA OOM abort
约 53248 processed tokens 附近失败
即使用 -b 512 -ub 128 --ctx-checkpoints 4 --cache-ram 2048 仍失败
```

本轮新 128k MTP4 峰值 21,746 MiB，剩余显存不足以支撑 256k 稳定服务。若要继续攻关 256k，应作为单独底层实验，先切更小模型量化或更激进 KV/attention 策略，而不是替换 OpenClaw 默认。

## 10. 为什么这次和之前 50 tok/s 平均值不矛盾

之前看到的 50 tok/s 多数接近长输出/整体 wall TPS 口径；本轮如果只看旧 `mtp n4` 的短输出平均，甚至能得到 88 tok/s，但这不是长期可持续吞吐。

更合理的对比是：

| 配置 | 短 JSON decode | 代码审查 decode | 1024 长输出 decode |
|---|---:|---:|---:|
| 旧 `mtp n4` | 120.77 | 53.66 | 50.44 |
| 新 `draft-mtp n2` | 87.86 | 74.40 | 67.97 |
| 新 `draft-mtp n4` | 99.67 | 70.96 | 62.79 |
| 新 `draft-mtp n6` | 95.04 | 53.29 | 50.77 |

因此，短响应可以看到 90-130 tok/s，但 OpenClaw 真正需要关注的是长上下文 prefill + 中长输出 decode + cache 命中后的 wall time。

## 11. 最终建议

1. 短期不替换生产服务，先保留当前已恢复的 18343 systemd 服务。
2. 新建一个候选 systemd profile，使用新 master `draft-mtp n4`，端口仍可用测试端口或维护窗口短切。
3. OpenClaw 默认路由建议先用 MTP4 128k cache profile，但监控两类指标：
   - `draft_accept_rate < 0.65` 持续出现时，自动切到 n2 profile；
   - 长输出超过 1024 tokens 的任务，优先 n2 profile。
4. 不继续投入 `n=6`、q8 KV、ngram 组合，除非后续 llama.cpp 对 multi-seq / recurrent state / ngram compatibility 有新的明确性能修复。
5. 256k 不作为 OpenClaw 当前默认目标。128k + prompt cache 是这张 4090 上最现实的性能/稳定性平衡点。

## 12. 原始数据与复现材料

本机结果目录：

```text
/Users/luo/Documents/github/CodexGame/output/qwen36-4090-mtp-pr22673-deep-20260517
```

关键文件：

```text
raw/remote-copy/results/summary.json
raw/remote-copy/results/*.json
raw/remote-copy/results/server_logs/*.log
raw/remote-copy/logs/build.log
raw/remote-copy/logs/eval-wrapper.log
raw/remote-copy/logs/pre-eval-status.log
raw/remote-copy/logs/restore-status.log
remote/qwen4090_pr22673_deep_eval.py
remote/run_pr22673_eval_wrapper.sh
```

外部参考：

- llama.cpp PR #22673: https://github.com/ggml-org/llama.cpp/pull/22673
- llama.cpp speculative docs: https://github.com/ggml-org/llama.cpp/blob/master/docs/speculative.md
- Unsloth Qwen3.6 MTP guide: https://unsloth.ai/docs/models/qwen3.6#mtp-guide

