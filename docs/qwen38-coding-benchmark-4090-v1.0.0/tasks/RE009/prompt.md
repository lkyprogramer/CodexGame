# 并发 Webhook 去重与失败重试

你正在维护一个只依赖 Python 3.11+ 标准库的工程。请在仓库内完成修复或实现。

## 任务

修复 `WebhookProcessor.handle(event_id, payload, handler)`。同一 event_id 的并发调用只执行一次 handler；首个成功调用返回 `processed`，等待者与后续重复调用返回 `duplicate`。handler 失败时不能把事件标记为已处理，所有当批等待者收到同一个异常，后续调用可重试。不同 event_id 可以并行。event_id 非空字符串、handler 可调用，否则 `ValueError`。

## 约束

- 不引入第三方依赖。
- 保持现有公开 API，除非题面明确允许调整。
- 考虑输入校验、边界条件和确定性行为。
- 只修改必要文件；不要读取或猜测隐藏测试。
- 可用工具时先检查 `store.py` 与 `processor.py`，完成后运行公开测试（若存在）。
- 最终修改必须留在工作区；非工具模式下输出统一 diff。
