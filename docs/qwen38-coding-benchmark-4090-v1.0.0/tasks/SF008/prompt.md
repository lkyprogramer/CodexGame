# 线程安全 LRU+TTL 缓存

你正在维护一个只依赖 Python 3.11+ 标准库的工程。请在仓库内完成修复或实现。

## 任务

完成 `LruTtlCache`：构造器 `LruTtlCache(max_size, ttl_seconds, clock=time.monotonic)`；公开方法为 `put(key, value)`、`get(key, default=None)`、`__len__()`。

每次 put 都从当前时刻重新计算 TTL；get 命中时更新 LRU；过期条目表现为未命中并被删除；容量超限时淘汰最久未访问的未过期条目。`max_size` 和 `ttl_seconds` 必须大于 0。所有公开操作线程安全，禁止在调用 `clock` 时持有可能导致用户回调重入死锁的不可重入锁。

## 约束

- 不引入第三方依赖。
- 保持现有公开 API，除非题面明确允许调整。
- 考虑输入校验、边界条件和确定性行为。
- 只修改必要文件；不要读取或猜测隐藏测试。
- 可用工具时先检查 仓库中的 Python 源码，完成后运行公开测试（若存在）。
- 最终修改必须留在工作区；非工具模式下输出统一 diff。
