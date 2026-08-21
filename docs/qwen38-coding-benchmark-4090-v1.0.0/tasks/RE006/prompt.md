# 插件依赖解析与确定性启动

你正在维护一个只依赖 Python 3.11+ 标准库的工程。请在仓库内完成修复或实现。

## 任务

修复 `PluginRegistry`。`register(name, factory, dependencies=())` 注册唯一非空名称；依赖名称需在 `start_all` 前全部存在。`resolve_order()` 返回确定性的拓扑顺序：同一可启动层按名称排序。存在缺失依赖或环时抛出 `ValueError`，环错误需包含被阻塞名称。`start_all()` 按顺序各调用 factory 一次，并返回 `{name: instance}`；任一 factory 失败后停止，失败及未启动插件不得缓存，下一次可重试。

## 约束

- 不引入第三方依赖。
- 保持现有公开 API，除非题面明确允许调整。
- 考虑输入校验、边界条件和确定性行为。
- 只修改必要文件；不要读取或猜测隐藏测试。
- 可用工具时先检查 `plugin.py` 与 `registry.py`，完成后运行公开测试（若存在）。
- 最终修改必须留在工作区；非工具模式下输出统一 diff。
