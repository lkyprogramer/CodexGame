# 递归审计日志脱敏

你正在维护一个仅使用 JDK 标准库的 Java 17+ 小型工程。请在仓库内完成修复或实现。

## 任务

完成 `AuditRedactor.redact(Object value)`，递归复制由 Map、List、基础不可变值组成的数据。Map key 转字符串后若大小写不敏感地包含 `password`、`secret`、`token` 或 `authorization`，其 value 替换为字符串 `***`，不再递归。其他 Map/List 必须深拷贝且返回不可修改集合；原对象不能被修改。支持 null、String、Number、Boolean。遇到其他类型或循环引用抛出 `IllegalArgumentException`。

## 约束

- 不引入第三方依赖。
- 保持现有公开类名和方法签名，除非题面明确允许调整。
- 处理边界条件、异常语义和并发要求。
- 只修改必要文件；不要读取或猜测隐藏测试。
- 可用工具时先检查 `src/AuditRedactor.java` 与示例调用，完成后运行公开测试（若存在）。
- 最终修改必须留在工作区；非工具模式下输出统一 diff。
