# NInfer 44a2c6c 前端 tokenization 优化 · v2 AI 开发与验证包

**版本：2.0.0 · 2026-09-25 · 状态：设计/执行资料已交付，产品实现与生产验收未执行。**

锁定 `tensorninja/ninfer-4090@44a2c6c3392c9d51e76a895ed97bf1867530d252`。本包是 v1 的完整替代执行入口，不是补丁说明。将目录放在仓库的 `docs/ninfer-44a2c6c-frontend-optimization-v2/`，不要覆盖仓库根 `AGENTS.md`，不要直接运行旧 v1 的 T06–T08。

## 结论与实施边界

首期只实施 **B0：保持最左起点/同位最小 ID 的单遍 added-token 扫描**，以及 **B1：一次主编码 + 基于实际扫描重启点的局部边界验证**。两者共同消除“重复编码长前缀 × 每次编码又反复搜索剩余全文”的工作放大。完整 render、NFC/BPE、工具提示、模型权重、MTP3、E8 KV、262K 和 GPU continuation 都保持不变。

**B2 跨请求 token 缓存明确推迟。** 在 B0+B1 的真实发布后，若匹配生产形态的 120K+ 热请求 tokenize p90 持续超过 1 秒，才重新评估；单次阈值超限不是自动开工许可。长会话 full_reset 是另一条同样重要但独立的调查线，不在 tokenizer PR 内同时调整 L1/L2/TTL/客户端路由。

## 为什么修订

Claude 附带的 CPU 基准保留了一条生产形态合成输入：legacy **101.564 s**、B1 **4.480 s**、B0+B1 **0.443 s**。这是候选原型在评审主机的记录，**不是本包作者重跑，不是生产二进制，不是 HTTP TTFT**。该输入实际 **273,012 tokens**，超过 262,144，只能作为 CPU 压力输入。B0 的约 10 秒结果只有评审正文说明，没有对应的保留原始行。

本包采纳双根因与收缩范围，同时补齐审查发现的证据限制：评审的 clone oracle 少了原版 uint32 溢出检查；可选 B0 基准分支未完整保留边界断言；原始资源、诊断 overlay diff、真实请求正文和生成器依赖的 raw 语料没有随包提供。不能把这些缺失默认为已验证。

## 导航

| 用途 | 入口 |
|---|---|
| AI 首次接手 | [AI_START_HERE.md](AI_START_HERE.md) |
| 范围、证据等级与基线 | [00](docs/00_SCOPE_BASELINE_EVIDENCE.md) / [01](docs/01_PINNED_SOURCE_AUDIT.md) |
| 架构与语义证明 | [02](docs/02_DESIGN_AND_ADRS.md) / [03](docs/03_BOUNDARY_CORRECTNESS_SPEC.md) / [04](docs/04_B0_SCANNER_AND_B1_ALGORITHM.md) |
| 文件与接口、观测字段 | [05](docs/05_CODE_CHANGE_MAP_AND_INTERFACES.md) / [06](docs/06_OBSERVABILITY_SCHEMA.md) |
| 开发顺序与任务卡 | [07](docs/07_AI_EXECUTION_PLAN.md) / [任务索引](tasks/index.json) |
| 正确性与性能验收 | [08](docs/08_TEST_STRATEGY_AND_GATES.md) / [09](docs/09_BENCHMARK_AND_PRODUCTION_REPLAY.md) |
| 构建、部署、回滚 | [10](docs/10_BUILD_DEPLOY_ROLLBACK.md) / [11](docs/11_REVIEW_AND_FAILURE_PLAYBOOK.md) |
| 决策与延期边界 | [12](docs/12_ROADMAP_AND_DECISION_RULES.md) / [B2](deferred/B2_DESIGN.md) |
| 来源、数据和工具格式 | [13](docs/13_SOURCE_REFERENCES.md) / [14](docs/14_FIXTURE_FORMAT_AND_HELPERS.md) |
| 逐项评审处置与二次审计 | [15](docs/15_REVIEW_DISPOSITION.md) / [16](docs/16_ASSET_AUDIT_AND_LIMITS.md) |
| 独立 full_reset 项目 | [17](docs/17_FULL_RESET_SEPARATE_PROJECT.md) |
| artifact 与 overlay 身份 | [18](docs/18_RESOURCE_OVERLAY_PROVENANCE.md) |
| 所有产品门初始状态 | [gate-report.json](templates/gate-report.json) |

## 使用与限制

Python 辅助工具只验证文档、有限词法模型、数据和归一化结果；没有包含已经完成的 NInfer 产品补丁。`evidence/review-assets/` 是用户附件的原样复制，不能直接作为可上线代码。`data/generated_sessions/` 是可复现合成请求，token 数未校准，默认禁止直接用于 HTTP。

执行 `bash tools/self_check.sh` 可自检本包。不需要 GPU，不访问生产。产品源码编译、真实 artifact 前端差分、节点 29 CPU 性能和 4090 HTTP 验证必须由执行者在受控环境完成。任何缺少资源的测试记为 `NOT_RUN` 或 `BLOCKED`，不得用 mock/跳过替代通过。
