# 直接交给执行 AI 的总提示词

你负责在我现有 `tensorninja/ninfer-4090@44a2c6c3392c9d51e76a895ed97bf1867530d252` 的独立实验副本上实现本计划的 CED / Late-State Prefill。

先读取本包 `00-START-HERE.md`、`AGENTS.md`、`docs/01-baseline-and-corrections.md`、`docs/03-contracts.md`、`docs/07-operations.md`、`docs/10-execution.md` 与当前Phase全文，再读取目标仓库的AGENTS。不要从聊天摘要猜接口。运行本包validate_package确认包完整。

从P0开始，按`manifests/plan.json`依赖执行。每个Task先写具体反例与局部测试，开发后做必要的编译/单测；**等当前Phase所有开发Task完成并合并到同一提交，再统一执行完整Phase验收**。GPU工作全部串行独占，不给每个subagent各开27B实例。

仅限本包范围：原base模型权重不变、CUDA13.2开发容器、sm_89、原262144 native容量、MTP3与rk4v4-e8作为现网对照；先48/16，不直接做32/32。P4先no-spec；P5才完整接MTP与缓存来源。保留conv history、MTP prefix hidden/KV、frontier与approx provenance。

生产unit、原镜像tag、模型文件、NGINX、兼容层和端口不可修改。没有明确维护授权不得暂停生产；缺GPU/权限/数据/依赖时输出BLOCKED与已完成工作，不擅自停机、不后台等待、不用模拟结果冒充实测。P0 guard必须先用mock做故障测试。

Teacher-state injection只证明接入合同，不证明Predictor质量；实际candidate不能读Teacher标签/答案。训练按repo/session分组，数据和训练预算有上限；不能全量dump百万token所有层状态。所有新脚本与--late-state参数是需要你实现的交付，不是当前repo已有功能。

Gate必须有非空case、raw日志、当前SHA、实际prompt长度、完整开销与恢复证据。SKIP、exit77、无GPU、0个测试或统计不足不能写PASS。质量和速度要用同一配置同时通过；未通过最多两轮针对明确根因的修复，之后给出NO-GO或范围限制。

P6通过后先形成可交付的CED16。P7为可选扩展；只有配置明确启用时运行，而且40/24统一Gate通过才进入32/32。P8可直接从P6交付，功能默认off，不自动替换生产服务。

每个Phase结束交付一份统一phase-report.md和gate.json，说明真实通过项、失败项、限制、原生恢复结果以及下一允许阶段。不要重复创建其他总体规划。没有实测就不要写预期速度已实现，也不要把private_opt_in资格说成已证明无损。
