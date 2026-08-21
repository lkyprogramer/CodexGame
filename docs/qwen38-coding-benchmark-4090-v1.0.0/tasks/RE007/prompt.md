# 稳定游标分页

你正在维护一个仅使用 JDK 标准库的 Java 17+ 小型工程。请在仓库内完成修复或实现。

## 任务

实现 `Paginator.page(items, cursor, limit)`。结果按 `score` 降序、`id` 升序排序；limit 为 1..100。cursor 为上一页最后一项的不可读 Base64 URL 编码，必须同时包含 score 与完整 id。下一页只返回排序位置严格在 cursor 之后的项，即使列表前部插入新项也不重复。返回 `Page(items,nextCursor)`，仅当仍有后续项时提供 nextCursor。非法/不存在的 cursor 抛出 `IllegalArgumentException`；不得修改输入。

## 约束

- 不引入第三方依赖。
- 保持现有公开类名和方法签名，除非题面明确允许调整。
- 处理边界条件、异常语义和并发要求。
- 只修改必要文件；不要读取或猜测隐藏测试。
- 可用工具时先检查 `src/` 下的分页模型，完成后运行公开测试（若存在）。
- 最终修改必须留在工作区；非工具模式下输出统一 diff。
