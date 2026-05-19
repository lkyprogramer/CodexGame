# OpenClaw MTP=4 最终结论

`Qwen3.6-27B-MTP-Q4XL` 在 4090 上使用 `--spec-draft-n-max 4` 可以进入 OpenClaw 基础模型候选，推荐先作为高吞吐 executor 后端接入。

推荐默认配置：

```bash
-ngl 99 -c 32768 -np 1 -fa on \
-ctk q4_0 -ctv q4_0 \
--spec-type mtp --spec-draft-n-max 4 \
-rea off --temp 0 --top-p 1
```

关键结论：

- `-np 1` 主测试 6/6 通过，平均 47.08 tokens/s，中位 49.56 tokens/s。
- 短任务吞吐约 44-70 tokens/s；tool call、JSON、中文运维推理均通过。
- 所有完成请求 `think_leak_count=0`，MTP 格式问题在当前启动参数下已解决。
- 19k prompt tokens 长上下文精确检索通过；45.6k tokens 在 `-c 32768` 下会被服务端拒绝。
- `-np 2` 并发短任务 2/2 通过，batch 约 76.62 tokens/s，但单请求上下文下降到 16k 档。
- 人工综合评分 `4.56/5`。主要扣分点是 patch-only 输出仍带 markdown fence，安全解释在短 token budget 下被截断。

接入 OpenClaw 前必须补齐：

- 上下文预算器：`-c 32768` 档建议输入控制在 24k tokens 以内。
- Patch fence stripping：只移除首尾 markdown fence，不改 diff 内容。
- 格式失败 retry：JSON、tool call、patch 各做一次带错误原因的重试。
- 执行层安全 gate：不要依赖模型自觉拒绝 destructive command。

测试结束后已恢复原 systemd 服务：

```text
qwen35-35b-a3b-uncensored.service: active
/v1/models: hauhaucs/Qwen3.5-35B-A3B-Uncensored-Aggressive-Q4_K_M
```

完整报告：`/Users/luo/Documents/github/CodexGame/output/qwen36-4090-openclaw-mtp4-20260513/reports/openclaw-mtp4-evaluation-report.md`

