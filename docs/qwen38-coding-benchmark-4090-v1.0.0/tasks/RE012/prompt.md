# 缓存仓储读写一致性

你正在维护一个仅使用 JDK 标准库的 Java 17+ 小型工程。请在仓库内完成修复或实现。

## 任务

修复 `CachedUserRepository`：`find(id)` 先查 cache，未命中读 store 并缓存 Optional（包括不存在的负缓存）；`save(user)` 必须先成功写 store，再更新 cache；`delete(id)` 必须先成功删 store，再驱逐 cache。store 操作失败时不能提前污染/删除 cache。id/user/dependency 非法时抛出 `IllegalArgumentException`。不得吞掉 store 异常。

## 约束

- 不引入第三方依赖。
- 保持现有公开类名和方法签名，除非题面明确允许调整。
- 处理边界条件、异常语义和并发要求。
- 只修改必要文件；不要读取或猜测隐藏测试。
- 可用工具时先检查 `src/` 中 store、cache 和 repository，完成后运行公开测试（若存在）。
- 最终修改必须留在工作区；非工具模式下输出统一 diff。
