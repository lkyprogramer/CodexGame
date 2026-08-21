# 并发幂等订单创建

你正在维护一个仅使用 JDK 标准库的 Java 17+ 小型工程。请在仓库内完成修复或实现。

## 任务

修复 `OrderService.create(commandId, orderId, amount)` 的进程内幂等语义。

同一 commandId 的并发或重复请求必须返回同一个订单结果，只允许调用一次 `PaymentGateway.charge` 和一次 `OrderRepository.save`。不同 commandId 可并行。gateway 或 repository 失败时，失败不得被永久缓存，后续相同 commandId 可重新尝试。参数非法时抛出 `IllegalArgumentException`，gateway 返回 null 非法。不得更改已有接口。

## 约束

- 不引入第三方依赖。
- 保持现有公开类名和方法签名，除非题面明确允许调整。
- 处理边界条件、异常语义和并发要求。
- 只修改必要文件；不要读取或猜测隐藏测试。
- 可用工具时先检查 整个 `src/` 仓库，完成后运行公开测试（若存在）。
- 最终修改必须留在工作区；非工具模式下输出统一 diff。
