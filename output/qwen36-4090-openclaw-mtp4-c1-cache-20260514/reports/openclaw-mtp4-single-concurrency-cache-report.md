# OpenClaw MTP=4 单请求上下文极限与 Prompt Cache 测试报告

测试时间：2026-05-14  
测试机器：RTX 4090，`192.168.10.29`  
测试目标：只测试一个并发场景，即 `concurrency=1 / -np 1`。重点验证 128k、256k 上下文极限，以及同 prompt 二次请求的 prompt cache 效果。  
原始记录目录：`/Users/luo/Documents/github/CodexGame/output/qwen36-4090-openclaw-mtp4-c1-cache-20260514`

## 1. 最终结论

结论：当前 4090 + Qwen3.6-27B-MTP-Q4XL + llama.cpp MTP=4 的可用单请求上限是 128k 档。`-c 131072 -np 1` 可以稳定处理接近 128k 的长上下文，并且 prompt cache 对重复请求有巨大收益；`-c 262144 -np 1` 在当前实现下不可用，长 prompt processing 过程中会触发 CUDA OOM abort。

128k 最强通过点：

```text
-c 131072 -np 1
concurrency: 1
prompt_tokens: 130406
exact_match: true
cold latency: 105.84s
warm latency: 1.23s
cache_n: 130402 / 130406
prompt cache speedup: 85.89x
think_leak_count: 0
```

128k 最近失败点：

```text
-c 131072 -np 1
prompt_tokens: 131866
n_ctx: 131072
result: HTTP 400 exceed_context_size_error
```

256k 结论：

```text
-c 262144 -np 1
prompt_tokens target: ~240k / ~255k
result: llama-server abort during prompt processing
root error: CUDA error: out of memory
observed progress before abort: about 53248 processed tokens
```

补充尝试：

```text
-c 262144 -np 1 -b 512 -ub 128 --ctx-checkpoints 4 --cache-ram 2048
result: still aborts with CUDA OOM around the same progress
```

所以当前建议：OpenClaw 的 MTP=4 单请求长上下文 lane 先按 128k 上限设计，不要把 256k 放入可用路由。

## 2. 测试配置

基础启动参数：

```bash
llama-server \
  -m /data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf \
  --alias openclaw/Qwen3.6-27B-MTP-Q4XL \
  -ngl 99 \
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
  --cache-reuse 256
```

128k 使用：

```text
-c 131072
```

256k 默认尝试：

```text
-c 262144
```

256k 保守尝试：

```text
-c 262144 -b 512 -ub 128 --ctx-checkpoints 4 --cache-ram 2048
```

测试脚本：

```text
/Users/luo/Documents/github/CodexGame/scripts/qwen4090_openclaw_fixed_concurrency_cache.py
```

远端脚本：

```text
/home/hhtele/qwen4090_openclaw_fixed_concurrency_cache.py
```

## 3. 128k 测试结果

| lane | prompt tokens | cold latency | cold prompt tok/s | warm latency | cache_n | cache ratio | speedup | result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `c131072_np1_w1650_c1_cache` | 120551 | 95.50s | 1276.17 | 1.24s | 120547 | 99.997% | 76.91x | exact |
| `c131072_np1_w1785_c1_cache` | 130406 | 105.84s | 1244.77 | 1.23s | 130402 | 99.997% | 85.89x | exact |
| `c131072_np1_w1805_c1_boundary` | 131866 requested | N/A | N/A | N/A | N/A | N/A | N/A | HTTP 400 |

128k 结论：

- `130406 tokens` 是本轮测到的最高有效点。
- `131866 tokens` 被服务端按 `n_ctx=131072` 正常拒绝。
- prompt cache 对相同 prompt 几乎全量命中，`cache_n` 只比 `prompt_tokens` 少 4 tokens。
- cold 的主要成本是 prompt prefill；warm 后端到端延迟降到约 `1.2s`。

## 4. 256k 测试结果

| lane | target | outcome | 关键错误 |
| --- | --- | --- | --- |
| `c262144_np1_b512_ub128_w3300_c1_cache` | 约 240k prompt tokens | server abort | `RemoteDisconnected`，日志显示 CUDA OOM |
| `c262144_np1_b512_ub128_w3500_c1_cache` | 约 255k prompt tokens | server abort | `RemoteDisconnected`，日志显示 CUDA OOM |
| `c262144_np1_b512_ub128_w3600_c1_boundary` | 262909 tokens | HTTP 400 | `request (262909 tokens) exceeds ... 262144` |
| `c262144_np1_ctxcp4_cache2048_w3300_c1_cache` | 约 240k prompt tokens | server abort | 降低 checkpoints/cache 后仍 CUDA OOM |

关键日志证据：

```text
llama_context: n_ctx = 262144
llama_context: n_batch = 512
llama_context: n_ubatch = 128
srv load_model: prompt cache is enabled
slot update_slots: prompt processing progress, n_tokens = 53248
CUDA error: out of memory
```

256k 判断：

- 不是模型找不到 marker。
- 不是输入超过 `n_ctx`，因为 `w3300/w3500` 在服务端处理过程中 abort，没有返回超上下文 HTTP 400。
- 根因是当前 4090 + MTP context + CUDA flash attention + prompt cache/checkpoint 组合在长 prompt prefill 时显存/虚拟内存分配失败。
- `w3600` 是正常边界失败，用于确认 256k 服务确实按 `n_ctx=262144` 做 hard limit。

## 5. Prompt Cache 效果

Prompt cache 在 128k 单请求场景非常有效：

```text
120551-token prompt:
cold batch elapsed: 95.51s
warm batch elapsed: 1.24s
speedup: 76.91x
cache_n: 120547

130406-token prompt:
cold batch elapsed: 105.85s
warm batch elapsed: 1.23s
speedup: 85.89x
cache_n: 130402
```

对 OpenClaw 的含义：

- 如果同一个 repo context / policy / tool schema 会重复请求，prompt cache 能把 128k 级别的重复上下文从分钟级降到约 1 秒级。
- cache 对“完全相同 prompt”的收益极高；对仅尾部变化的真实 OpenClaw prompt，还需要后续用真实 trace 测 partial reuse。
- 256k 下 cache 暂时不能作为可用能力，因为服务端会在 cold prefill 阶段先 OOM。

## 6. OpenClaw 建议

推荐单请求长上下文 lane：

```bash
-c 131072 -np 1 \
--spec-type mtp --spec-draft-n-max 4 \
-ctk q4_0 -ctv q4_0 \
--cache-prompt --cache-reuse 256 \
-fa on -rea off
```

路由预算：

```text
硬上限：131072 tokens
建议输入预算：<= 120000 tokens
极限可用点：130406 tokens
超过 131k：会 HTTP 400
```

暂不推荐：

```text
-c 262144 -np 1
```

原因：当前实测在约 53k processed tokens 处 CUDA OOM abort，不能作为稳定 OpenClaw lane。

## 7. 人工评分

| 维度 | 分数 | 依据 |
| --- | ---: | --- |
| 128k exact retrieval | 5.0 / 5 | 120k、130k prompt 均精确返回 marker |
| 128k prompt cache | 5.0 / 5 | warm latency 约 1.2s，最高 85.89x speedup |
| MTP 格式稳定性 | 5.0 / 5 | 有效请求 `think_leak_count=0` |
| 128k 边界可解释性 | 5.0 / 5 | 超限返回明确 HTTP 400 |
| 256k 可用性 | 1.5 / 5 | 能启动并识别 hard limit，但长 prompt prefill OOM abort |
| OpenClaw 生产适配 | 4.0 / 5 | 128k 可用，256k 需屏蔽或继续底层修复 |

综合评分：`4.25 / 5`

## 8. 下一步

1. 用真实 OpenClaw trace 测 128k prompt cache partial reuse：固定 repo context，只改变尾部任务。
2. 256k 如果继续攻关，优先从 llama.cpp/MTP/CUDA FA 内存路径入手，而不是继续换 prompt。
3. 对 256k 可尝试单独编译/运行禁用 MTP 或禁用 FA 的对照组，用于确认 OOM 是 MTP-specific、FA-specific，还是模型结构在 256k 下的通用限制。

