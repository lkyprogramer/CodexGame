# 多来源配置优先级与类型校验

你正在维护一个只依赖 Python 3.11+ 标准库的工程。请在仓库内完成修复或实现。

## 任务

完成 `load_config(path, env, cli)`。配置键仅允许 `host:str`、`port:int(1..65535)`、`debug:bool`、`workers:int(1..128)`、`tags:list[str]`。优先级为 CLI > 环境变量 `APP_*` > JSON 文件 > defaults。环境变量和 CLI 可传字符串，bool 仅接受 true/false/1/0/yes/no，tags 字符串按逗号切分并去空白。未知键、类型错误、文件非对象或无效范围均抛出 `ValueError`。返回新 dict，不修改输入。

## 约束

- 不引入第三方依赖。
- 保持现有公开 API，除非题面明确允许调整。
- 考虑输入校验、边界条件和确定性行为。
- 只修改必要文件；不要读取或猜测隐藏测试。
- 可用工具时先检查 `defaults.py` 与 `config_loader.py`，完成后运行公开测试（若存在）。
- 最终修改必须留在工作区；非工具模式下输出统一 diff。
