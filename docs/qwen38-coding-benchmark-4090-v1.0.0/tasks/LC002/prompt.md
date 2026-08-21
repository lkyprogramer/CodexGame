# 长仓库事件规范序列化

你正在维护一个只依赖 Python 3.11+ 标准库的工程。请在仓库内完成修复或实现。

## 任务

定位事件序列化实现并修复。输出必须是确定性的 UTF-8 JSON bytes：key 排序、紧凑分隔、保留 Unicode；不得修改输入。支持嵌套 dict/list、有限数字、bool/null、timezone-aware datetime（转 UTC 毫秒 `Z`）、date、bytes-like（表示为 `{"$bytes":"base64"}`）。拒绝非字符串 key、NaN/Infinity、naive datetime、循环引用和不支持类型。

## 约束

- 不引入第三方依赖。
- 保持现有公开 API，除非题面明确允许调整。
- 考虑输入校验、边界条件和确定性行为。
- 只修改必要文件；不要读取或猜测隐藏测试。
- 可用工具时先检查 大型 `platform/` 仓库，使用 search 定位 serialization/event，完成后运行公开测试（若存在）。
- 最终修改必须留在工作区；非工具模式下输出统一 diff。
