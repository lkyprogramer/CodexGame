# 09 · 解释边界与限制

- 48 题样本仍然有限；1–2 道题可能显著影响小类别比例；
- 公开发布后存在训练污染风险；
- Java/Python 比重与用户真实 Java/Spring 仓库并不完全相同；
- 受限工具避免任意 shell 风险，但比 Claude Code/Codex 的完整工具环境更窄；
- 自动验证偏向可执行 contract，架构美感和可维护性仍需人工 patch review；
- 代码审查题使用只读工具和关键词组 Rubric 测高信号问题召回，可能被表述方式影响，不等同于真实安全审计；
- OpenAI-compatible 后端的 token/reasoning usage 语义可能不一致；
- GPU 指标是采样值，不能替代服务器级 profile；
- GGUF、template、MTP 和 server 版本交互很强，结果不能无条件外推。

因此报告结论应是“在给定环境和任务分布下的相对证据”，不是模型本体的永恒排名。

- 标准 Runner 使用非流式 API，TTFT 必须另从 server telemetry 获取；
- `context_size` 是实验声明，实际限制由 server 启动参数决定；
- 工具环境是安全受限的共同子集，不完全复制 Claude Code、Codex 或 OpenCode 的 shell 能力。
