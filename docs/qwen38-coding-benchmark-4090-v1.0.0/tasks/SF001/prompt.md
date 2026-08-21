# 线程安全滑动窗口限流器

你正在维护一个仅使用 JDK 标准库的 Java 17+ 小型工程。请在仓库内完成修复或实现。

## 任务

实现 `RateLimiter`：

- 构造参数为 `maxRequests` 与 `windowMillis`，两者都必须大于 0。
- `allow(String key, long nowMillis)` 对每个 key 独立执行精确滑动窗口限流。
- 时间区间定义为 `(nowMillis - windowMillis, nowMillis]`；恰好位于左边界的旧请求应过期。
- 同一 key 的时间戳必须单调不减，倒退时抛出 `IllegalArgumentException`。
- 方法需要线程安全；并发调用不能突破配额。
- key 为 null 或空字符串时抛出 `IllegalArgumentException`。

## 约束

- 不引入第三方依赖。
- 保持现有公开类名和方法签名，除非题面明确允许调整。
- 处理边界条件、异常语义和并发要求。
- 只修改必要文件；不要读取或猜测隐藏测试。
- 可用工具时先检查 `src/` 下的源码，完成后运行公开测试（若存在）。
- 最终修改必须留在工作区；非工具模式下输出统一 diff。
