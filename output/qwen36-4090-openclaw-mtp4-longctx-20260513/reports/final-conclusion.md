# OpenClaw MTP=4 长上下文并发最终结论

本轮重点测了 MTP=4 作为 OpenClaw 基础模型时的长上下文并发极限。

最终结论：可用，但必须做 per-slot 上下文预算。`llama.cpp` 的有效请求上限近似是 `total_ctx / np`，不是总 `-c`。只要请求低于 slot 上限，本轮所有长上下文并发请求都精确返回 marker；超过上限会直接 HTTP 400，不是模型答错。

最强通过点：

```text
-c 98304 -np 2
concurrency: 2
per request prompt_tokens: 49013
exact_match: 2/2
think_leak_count: 0
max latency: 62.52s
batch prompt ingest: 1567.72 tokens/s
```

最近失败点：

```text
-c 98304 -np 2
concurrency: 2
per request prompt_tokens: 49349
n_ctx per slot: 49152
result: HTTP 400 exceed_context_size_error
```

推荐 OpenClaw 路由：

```text
<= 12k tokens: -c 65536 -np 4
12k-24k tokens: -c 65536 -np 2
24k-43k tokens: -c 98304 -np 2
> 43k tokens: 先裁剪 / 摘要 / 分块
```

综合人工评分：`4.75/5`。扣分主要来自长上下文并发尾延迟高，`49k * 2` 的极限档最大延迟约 62.5s，不适合交互式低延迟任务，但适合后台 repo scan / 大日志 / 大 diff 审查 lane。

完整报告：

```text
/Users/luo/Documents/github/CodexGame/output/qwen36-4090-openclaw-mtp4-longctx-20260513/reports/openclaw-mtp4-long-context-concurrency-report.md
```

测试后已恢复默认服务：

```text
qwen35-35b-a3b-uncensored.service: active
/v1/models: hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M
```

