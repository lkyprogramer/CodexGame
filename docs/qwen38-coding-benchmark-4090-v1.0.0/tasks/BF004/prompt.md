# 修复重试异常语义

你正在维护一个只依赖 Python 3.11+ 标准库的工程。请在仓库内完成修复或实现。

## 任务

修复 `retry(action, retries, retry_on, sleep, base_delay=0.1)`：`retries` 表示首次调用后的额外重试次数；只重试 `retry_on` 指定的异常类型；采用 `base_delay * 2**retry_index`（第一次重试为 base_delay）；成功立即返回；耗尽后原样抛出最后一个异常。不得捕获 `KeyboardInterrupt`、`SystemExit` 等 `BaseException`。参数非法时抛出 `ValueError`。

## 约束

- 不引入第三方依赖。
- 保持现有公开 API，除非题面明确允许调整。
- 考虑输入校验、边界条件和确定性行为。
- 只修改必要文件；不要读取或猜测隐藏测试。
- 可用工具时先检查 仓库中的 Python 源码，完成后运行公开测试（若存在）。
- 最终修改必须留在工作区；非工具模式下输出统一 diff。
