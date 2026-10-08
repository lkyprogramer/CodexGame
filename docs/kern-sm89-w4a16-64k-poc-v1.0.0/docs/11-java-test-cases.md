# Java / Pi实际题目

三个夹具均仅用JDK标准库，目标Java8。controller使用较新JDK时通过`--release 8`编译；JDK8用source/target8。无Maven下载时间污染。

| 题目 | 真实业务合同 | 主要风险 |
|---|---|---|
| java-01-idempotency | 成功幂等、并发同key、失败不缓存、不同key不全局串行 | check-then-act与粗锁 |
| java-02-retry | maxAttempts含首次、只重试IOException、保留中断、传播terminal exception | off-by-one与吞异常 |
| java-03-reconnect | 秒→毫秒、到期边界、clock rollback、旧连接清理不能删新连接 | 单位错误和ABA式状态覆盖 |

运行：

```bash
python3 -m poc_tools.java_runner --base-url http://127.0.0.1:18041/v1 \
  --model qwen3.8-27b-kern-sm89-p0 --out-dir results/pi-run-001
```

每题原始状态必须FAIL，Pi修复后controller复制原始测试与候选src/main到新临时目录再次编译。修改src/test、verify.sh、TASK.md、AGENTS.md即FAIL。仅输出建议、没有真实src/main修改也FAIL。

三个题在本交付生成环境已检查“初始失败/临时参考修复成功”；**这不代表任何模型已经通过它们**。参考修复没有复制进测试Agent的工作目录。

计量累加每条assistant message_end usage，不能只取最后一次响应。tool_execution_start按id去重；不识别的事件保留到原始JSONL，不用零调用补齐。记录总工具次数、失败重试、编译次数、墙钟、TTFT与新算输入量。

3/3是发布smoke门槛，不是“模型能力≥原版99%”的统计证据。后续可用用户真实Java迁移任务扩展，但本阶段避免把题量做大掩盖移植问题。
