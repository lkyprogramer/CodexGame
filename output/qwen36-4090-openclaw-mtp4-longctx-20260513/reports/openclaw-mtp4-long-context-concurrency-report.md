# OpenClaw MTP=4 长上下文并发极限测试报告

测试时间：2026-05-13  
测试机器：RTX 4090，`192.168.10.29`  
测试目标：按上一轮 `openclaw-mtp4-evaluation-report.md` 的建议，重点验证 `Qwen3.6-27B-MTP-Q4XL` 在 MTP=4 下作为 OpenClaw 基础模型时的长上下文并发极限。  
原始记录目录：`/Users/luo/Documents/github/CodexGame/output/qwen36-4090-openclaw-mtp4-longctx-20260513`

## 1. 最终结论

结论：MTP=4 在 4090 上可以支撑 OpenClaw 的并发长上下文检索，但必须按 `ctx / np` 做严格 per-slot 上下文预算。它的行为非常接近理论分槽边界：只要请求 token 数低于当前 slot 的 `n_ctx`，长上下文 marker 检索稳定；一旦超过，llama.cpp 会直接 400 拒绝，而不是模型质量退化。

最强通过点：

```text
-c 98304 -np 2
concurrency: 2
per request prompt_tokens: 49013
per slot n_ctx: 49152
exact_match: 2/2
think_leak_count: 0
max latency: 62.52s
batch prompt ingest: 1567.72 tokens/s
```

极限失败点：

```text
-c 98304 -np 2
concurrency: 2
per request prompt_tokens: 49349
per slot n_ctx: 49152
result: HTTP 400 exceed_context_size_error
```

这说明本轮测到的并发长上下文极限是：`-c 98304 -np 2` 下每个并发请求约 `49k prompt tokens`，再往上需要增加总 context 或降低 `np`。

## 2. 测试方法

### 2.1 启动参数

所有 lane 都使用同一个 MTP 启动基线，只改变 `-c` 与 `-np`：

```bash
llama-server \
  -m /data/models/qwen/mtp/Qwen3.6-27B-UD-Q4_K_XL.gguf \
  --alias openclaw/Qwen3.6-27B-MTP-Q4XL \
  -ngl 99 \
  -fa on \
  -ctk q4_0 \
  -ctv q4_0 \
  --spec-type mtp \
  --spec-draft-n-max 4 \
  -rea off \
  --temp 0 \
  --top-p 1
```

仍然不使用 `--reasoning-format none`。

### 2.2 测试脚本

本地脚本：

```text
/Users/luo/Documents/github/CodexGame/scripts/qwen4090_openclaw_long_context_concurrency.py
```

远端脚本：

```text
/home/hhtele/qwen4090_openclaw_long_context_concurrency.py
```

每个 worker 构造独立 marker：

```text
OPENCLAW_LONG_CTX_CONCURRENCY_4090_MTP4_<lane>_W<worker>_WORDS<words>
```

验收规则：

- 响应必须只返回该 worker 的 exact marker。
- 记录 `prompt_tokens`、`completion_tokens`、端到端耗时、prompt ingest、decode speed、draft accept rate。
- 记录 HTTP 400 的 `n_prompt_tokens` 与 `n_ctx`，用于确认边界是 context slot 限制。
- 人工评分按 OpenClaw 真实使用风险评估，不把服务端合理拒绝误判为模型质量错误。

### 2.3 服务恢复

测试期间停止默认服务，测试后已恢复并验证：

```text
qwen35-35b-a3b-uncensored.service: active
/v1/models: hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M
GPU after restore: 21870 MiB used, 2347 MiB free
```

## 3. 完整结果矩阵

| lane | ctx | np | concurrency | per request prompt tokens | result | max latency | batch prompt tok/s | 人工分 |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| `c32768_np1_w220_c1` | 32768 | 1 | 1 | 14843 | 1/1 exact | 9.17s | 1618.16 | 5.0 |
| `c32768_np1_w360_c1` | 32768 | 1 | 1 | 24223 | 1/1 exact | 14.76s | 1640.45 | 5.0 |
| `c32768_np1_w460_c1` | 32768 | 1 | 1 | 30923 | 1/1 exact | 19.08s | 1620.02 | 5.0 |
| `c32768_np1_w650_c1` | 32768 | 1 | 1 | 43653 requested | 400 exceed ctx | N/A | N/A | 4.0 |
| `c32768_np2_w180_c2` | 32768 | 2 | 2 | 12163 | 2/2 exact | 14.63s | 1662.33 | 5.0 |
| `c32768_np2_w230_c2` | 32768 | 2 | 2 | 15513 | 2/2 exact | 18.50s | 1676.59 | 5.0 |
| `c32768_np2_w250_c2` | 32768 | 2 | 2 | 16853 requested | 400 exceed ctx | N/A | N/A | 4.0 |
| `c65536_np2_w360_c2` | 65536 | 2 | 2 | 24223 | 2/2 exact | 28.73s | 1685.79 | 5.0 |
| `c65536_np2_w460_c2` | 65536 | 2 | 2 | 30923 | 2/2 exact | 37.18s | 1663.08 | 5.0 |
| `c65536_np2_w650_c2` | 65536 | 2 | 2 | 43653 requested | 400 exceed ctx | N/A | N/A | 4.0 |
| `c65536_np4_w180_c4` | 65536 | 4 | 4 | 12163 | 4/4 exact | 28.69s | 1695.60 | 5.0 |
| `c65536_np4_w230_c4` | 65536 | 4 | 4 | 15513 | 4/4 exact | 36.10s | 1718.46 | 5.0 |
| `c65536_np4_w300_c4` | 65536 | 4 | 4 | 20203 requested | 400 exceed ctx | N/A | N/A | 4.0 |
| `c98304_np2_w650_c2` | 98304 | 2 | 2 | 43653 | 2/2 exact | 54.63s | 1597.98 | 5.0 |
| `c98304_np2_w730_c2` | 98304 | 2 | 2 | 49013 | 2/2 exact | 62.52s | 1567.72 | 5.0 |
| `c98304_np2_w735_c2_boundary` | 98304 | 2 | 2 | 49349 requested | 400 exceed ctx | N/A | N/A | 5.0 |

说明：失败 lane 的人工分不是模型回答质量分，而是系统行为评价分。HTTP 400 且明确返回 `n_prompt_tokens > n_ctx` 是可预期、可治理的边界行为；`c98304_np2_w735_c2_boundary` 因为精确证明了边界，给 5.0。

## 4. 分槽边界

llama.cpp server 在并发 slot 下的有效上下文近似为：

```text
per_slot_n_ctx = total_ctx / np
```

本轮实测：

| total ctx | np | per-slot n_ctx | 最高通过 prompt tokens | 最近失败 prompt tokens | 结论 |
| ---: | ---: | ---: | ---: | ---: | --- |
| 32768 | 1 | 32768 | 30923 | 43653 | 单路 32k 档可用输入预算约 30k |
| 32768 | 2 | 16384 | 15513 | 16853 | 双路 32k 档每 worker 极限约 15.5k |
| 65536 | 2 | 32768 | 30923 | 43653 | 双路 64k 档每 worker 可接近 31k |
| 65536 | 4 | 16384 | 15513 | 20203 | 四路 64k 档每 worker 极限约 15.5k |
| 98304 | 2 | 49152 | 49013 | 49349 | 双路 96k 档每 worker 极限约 49k |

关键判断：OpenClaw 的并发策略必须按 slot 预算，不是只看 `-c` 总值。比如 `-c 65536 -np 4` 看起来是 64k context，但每个并发请求只有 16k 左右。

## 5. 性能观察

### 5.1 Prompt ingest

有效 lane 的 batch prompt ingest 基本稳定在 `1567-1718 tokens/s`：

```text
c32768_np1_w460_c1: 1620.02 batch prompt tok/s
c32768_np2_w230_c2: 1676.59 batch prompt tok/s
c65536_np2_w460_c2: 1663.08 batch prompt tok/s
c65536_np4_w230_c4: 1718.46 batch prompt tok/s
c98304_np2_w730_c2: 1567.72 batch prompt tok/s
```

并发增加后，总 prefill 吞吐没有线性增长，主要表现为单请求等待时间变长。OpenClaw 如果把长上下文任务并发排队，吞吐稳定，但尾延迟会明显上升。

### 5.2 Latency

相同 per request token 下，并发越高，端到端延迟越高：

```text
12.1k tokens:
-c32768 -np2 -c2: max 14.63s
-c65536 -np4 -c4: max 28.69s

15.5k tokens:
-c32768 -np2 -c2: max 18.50s
-c65536 -np4 -c4: max 36.10s

30.9k tokens:
-c32768 -np1 -c1: max 19.08s
-c65536 -np2 -c2: max 37.18s
```

这符合长上下文 prefill 的资源竞争特征。对 OpenClaw 来说，并发长上下文更适合后台/批处理，不适合交互式低延迟链路。

### 5.3 MTP draft accept

所有有效 lane 的 `avg_draft_accept_rate = 1.0`。这类 marker retrieval 输出极短、确定性强，MTP draft 接受率非常高；但由于输出只有几十 token，整体耗时仍由 prompt prefill 决定。

## 6. OpenClaw 推荐配置

### 6.1 默认交互档

用于常规 executor、短/中上下文 patch、tool call、CI triage：

```bash
-c 32768 -np 1 \
--spec-type mtp --spec-draft-n-max 4 \
-ctk q4_0 -ctv q4_0 -fa on -rea off
```

预算：

```text
输入硬上限：< 32768 tokens
建议 OpenClaw 输入预算：<= 24000 tokens
本轮 30923 tokens 仍通过，但生产不建议压到 slot 顶部
```

### 6.2 双并发长上下文档

用于两个 agent / 两个 repo scan / 两个长日志 triage 同时跑：

```bash
-c 65536 -np 2 \
--spec-type mtp --spec-draft-n-max 4 \
-ctk q4_0 -ctv q4_0 -fa on -rea off
```

预算：

```text
每 worker 硬上限：32768 tokens
建议每 worker 输入预算：<= 24000 tokens
实测 30923 tokens 仍 2/2 exact，但 max latency 37.18s
```

### 6.3 四并发中长上下文档

用于多个较小任务并发，不适合超长 repo context：

```bash
-c 65536 -np 4
```

预算：

```text
每 worker 硬上限：16384 tokens
建议每 worker 输入预算：<= 12000 tokens
实测 15513 tokens 仍 4/4 exact，但 max latency 36.10s
```

### 6.4 极限双并发档

用于专门压榨长上下文并发，不建议作为默认交互服务：

```bash
-c 98304 -np 2
```

预算：

```text
每 worker 硬上限：49152 tokens
建议每 worker 输入预算：<= 43000 tokens
实测 49013 tokens 仍 2/2 exact
49349 tokens 被 400 拒绝
```

这个档位适合 OpenClaw 的“长仓库摘要 / 大日志 / 大 diff 审查”专用 lane。它的质量表现很好，但尾延迟已经超过 60s。

## 7. 人工评分

| 维度 | 分数 | 依据 |
| --- | ---: | --- |
| 长上下文 exact retrieval | 5.0 / 5 | 所有未超 context 的 lane 都精确返回 worker marker |
| 并发稳定性 | 5.0 / 5 | `c2` 与 `c4` 有效 lane 均无错配、无串 worker marker |
| MTP 格式稳定性 | 5.0 / 5 | 有效 lane `think_leak_count=0` |
| context 边界可解释性 | 5.0 / 5 | 失败均为明确 `exceed_context_size_error`，包含 `n_prompt_tokens` 和 `n_ctx` |
| 极限吞吐 | 4.5 / 5 | batch prefill 稳定在 1.5k-1.7k tok/s，但高并发长上下文尾延迟高 |
| OpenClaw 生产适配 | 4.0 / 5 | 必须实现 per-slot budget、队列分流和长任务 timeout 管控 |

综合评分：`4.75 / 5`

## 8. 对 OpenClaw 的实现要求

1. 上下文预算必须按 lane 计算：

```text
usable_input_tokens = floor(total_ctx / np) - reserved_completion_tokens - reserved_tool_result_tokens - safety_margin
```

2. 推荐 safety margin：

```text
普通任务：2048 tokens
长上下文任务：4096 tokens
工具链多轮任务：至少 8192 tokens
```

3. 路由建议：

```text
<= 12k tokens: 可进 -c65536 -np4 lane
12k-24k tokens: 进 -c65536 -np2 lane
24k-43k tokens: 进 -c98304 -np2 lane
> 43k tokens: 先裁剪 / 摘要 / 分块，不直接请求
```

4. 并发策略：

- 短任务可以用 `np=2/4` 提高吞吐。
- 长上下文任务不应无限并发；建议最多 2 路。
- 极长上下文应独占或半独占队列，避免拖慢交互任务。

5. 失败治理：

- `exceed_context_size_error` 不做模型重试，直接触发上下文裁剪。
- exact marker / JSON / patch 协议失败才做一次模型重试。
- 超过 60s 的长上下文任务应归类为后台任务，不要占交互式 executor SLA。

## 9. 后续建议

下一轮不要再只测 synthetic marker。建议接真实 OpenClaw trace：

1. 两个并发 repo scan，各自包含真实文件树、关键源码片段和工具 schema。
2. 两个并发 CI failure triage，各自包含 10k-30k tokens 日志。
3. 大 diff patch review，验证模型不仅能找 marker，还能在 30k-50k context 中定位具体问题。
4. 开启 prompt cache，测试相同 repo context 的第二轮延迟下降。
5. 加 executor routing mock，验证 `ctx/np` budget 超限时能自动选择 lane 或裁剪上下文。

