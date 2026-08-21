# 签名用规范化查询串

你正在维护一个仅使用 JDK 标准库的 Java 17+ 小型工程。请在仓库内完成修复或实现。

## 任务

实现 `CanonicalQuery.canonicalize(Map<String, List<String>> params)`：

- 每个 key 可对应多个 value，null 列表、null key 或 null value 非法。
- 对 key/value 分别按 UTF-8 RFC 3986 percent-encoding；未保留字符仅 `A-Z a-z 0-9 - . _ ~`，空格必须编码为 `%20`，十六进制大写。
- 先按编码后的 key，再按编码后的 value 排序；重复项保留。
- 输出 `k=v&k=v`；空 map 返回空串。不得修改输入。

## 约束

- 不引入第三方依赖。
- 保持现有公开类名和方法签名，除非题面明确允许调整。
- 处理边界条件、异常语义和并发要求。
- 只修改必要文件；不要读取或猜测隐藏测试。
- 可用工具时先检查 `src/` 下的源码，完成后运行公开测试（若存在）。
- 最终修改必须留在工作区；非工具模式下输出统一 diff。
