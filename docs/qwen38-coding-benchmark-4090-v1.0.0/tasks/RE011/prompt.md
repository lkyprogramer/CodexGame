# 确定性百分比灰度发布

你正在维护一个只依赖 Python 3.11+ 标准库的工程。请在仓库内完成修复或实现。

## 任务

完成 `is_enabled(user_id, config, overrides=None)`。config 含 `name`、`salt`、`basis_points`（0..10000）；override 中用户 id 的 bool 值优先。其余用户用 SHA-256 对 `salt:name:user_id` UTF-8 字节哈希，取前 8 字节无符号大端整数 `% 10000`，小于 basis_points 时启用。相同输入跨进程必须稳定；禁止使用 Python `hash()`。严格校验输入，不修改 config/overrides。

## 约束

- 不引入第三方依赖。
- 保持现有公开 API，除非题面明确允许调整。
- 考虑输入校验、边界条件和确定性行为。
- 只修改必要文件；不要读取或猜测隐藏测试。
- 可用工具时先检查 `flags/model.py` 与 `flags/evaluator.py`，完成后运行公开测试（若存在）。
- 最终修改必须留在工作区；非工具模式下输出统一 diff。
