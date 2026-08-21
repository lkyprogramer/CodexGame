# Release Verification Evidence

本目录保存发布包的可复查证据：

- `release-summary.json`：环境、题库和验证汇总；
- `reference-validation.json`：48 个参考实现和 48 个故障基线的逐题结果；
- `quick-release-verification.log`：编译、27 项单元/端到端测试、目录/泄漏审计、CLI、结果审计和合成报告管线的原始日志。

发布自检不包含真实 Qwen 模型推理；`examples/` 中所有结果均为合成管线夹具，不能用于评价模型能力。
