# OpenClaw MTP=4 单请求最终结论

这次已按单一并发场景重测：`concurrency=1 / -np 1`。

结论：当前 4090 上 MTP=4 的稳定单请求长上下文上限是 128k，不是 256k。

128k 最强通过点：

```text
-c 131072 -np 1
prompt_tokens: 130406
exact_match: true
cold latency: 105.84s
warm latency: 1.23s
cache_n: 130402 / 130406
prompt cache speedup: 85.89x
```

128k 最近失败点：

```text
prompt_tokens: 131866
n_ctx: 131072
result: HTTP 400 exceed_context_size_error
```

256k 结论：

```text
-c 262144 -np 1
约 240k/255k prompt 的请求会在 prompt processing 中触发 CUDA OOM abort
即使用 -b 512 -ub 128 --ctx-checkpoints 4 --cache-ram 2048 仍失败
```

OpenClaw 当前建议：

```text
单请求长上下文 lane 使用 -c 131072 -np 1
输入预算建议 <= 120k tokens
开启 --cache-prompt --cache-reuse 256
屏蔽 256k lane，除非后续修复 llama.cpp/MTP/CUDA FA 内存问题
```

完整报告：

```text
/Users/luo/Documents/github/CodexGame/output/qwen36-4090-openclaw-mtp4-c1-cache-20260514/reports/openclaw-mtp4-single-concurrency-cache-report.md
```

测试后已恢复默认服务：

```text
qwen35-35b-a3b-uncensored.service: active
nginx: active
```

