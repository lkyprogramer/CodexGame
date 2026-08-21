# 修复 UTF-8 流式解码

你正在维护一个只依赖 Python 3.11+ 标准库的工程。请在仓库内完成修复或实现。

## 任务

修复 `Utf8ChunkDecoder`。`feed(data, final=False)` 接收 bytes-like 分片并返回本次可解码文本；跨分片的多字节字符必须正确缓冲。`final=True` 时必须检测残缺序列，之后任何 feed 都抛出 `RuntimeError`。非法 UTF-8 使用严格模式抛出 `UnicodeDecodeError`；非 bytes-like 输入抛出 `TypeError`。

## 约束

- 不引入第三方依赖。
- 保持现有公开 API，除非题面明确允许调整。
- 考虑输入校验、边界条件和确定性行为。
- 只修改必要文件；不要读取或猜测隐藏测试。
- 可用工具时先检查 仓库中的 Python 源码，完成后运行公开测试（若存在）。
- 最终修改必须留在工作区；非工具模式下输出统一 diff。
