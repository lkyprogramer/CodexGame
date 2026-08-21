# 不可变货币值对象

你正在维护一个仅使用 JDK 标准库的 Java 17+ 小型工程。请在仓库内完成修复或实现。

## 任务

完成不可变 `Money` 值对象：

- `Money.of(String amount, String currency)` 使用 `BigDecimal` 解析，货币代码必须是三位 ASCII 字母并规范为大写。
- 金额统一按小数点后 2 位、`RoundingMode.HALF_EVEN` 规范化。
- 提供 `add`、`subtract`、`multiply(BigDecimal factor)`、`amount()`、`currency()`。
- 加减仅允许同币种；null 参数和非法数字应转为 `IllegalArgumentException`。
- `equals/hashCode/toString` 必须基于规范化金额和币种；toString 格式为 `USD 12.34`。

## 约束

- 不引入第三方依赖。
- 保持现有公开类名和方法签名，除非题面明确允许调整。
- 处理边界条件、异常语义和并发要求。
- 只修改必要文件；不要读取或猜测隐藏测试。
- 可用工具时先检查 `src/` 下的源码，完成后运行公开测试（若存在）。
- 最终修改必须留在工作区；非工具模式下输出统一 diff。
