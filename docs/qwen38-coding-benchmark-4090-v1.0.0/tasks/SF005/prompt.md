# 溢出安全的重试退避策略

你正在维护一个仅使用 JDK 标准库的 Java 17+ 小型工程。请在仓库内完成修复或实现。

## 任务

实现 `RetryPolicy.delayMillis(int attempt, long retryAfterMillis)`：

- `attempt` 从 1 开始，非法值抛出 `IllegalArgumentException`。
- 指数退避为 `baseDelayMillis * 2^(attempt-1)`，但必须溢出安全并封顶到 `maxDelayMillis`。
- `retryAfterMillis == -1` 表示服务端没有建议；其他负数非法。
- 有服务端建议时取“指数退避与 retry-after 的较大者”，最后仍封顶到 max。
- 构造参数 `baseDelayMillis > 0`、`maxDelayMillis >= baseDelayMillis`。

## 约束

- 不引入第三方依赖。
- 保持现有公开类名和方法签名，除非题面明确允许调整。
- 处理边界条件、异常语义和并发要求。
- 只修改必要文件；不要读取或猜测隐藏测试。
- 可用工具时先检查 `src/` 下的源码，完成后运行公开测试（若存在）。
- 最终修改必须留在工作区；非工具模式下输出统一 diff。
