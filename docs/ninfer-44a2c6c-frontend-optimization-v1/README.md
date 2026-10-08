# NInfer 4090：前端 tokenization 修复与增量续写实施包 v1.0

**基线：`tensorninja/ninfer-4090@44a2c6c3392c9d51e76a895ed97bf1867530d252`**  
**编制日期：2026-09-24｜交付类型：设计、实施、测试、验收文档及辅助资料；不是已完成的 NInfer 补丁。**

## 先读结论

线上诊断把几十秒的热续写等待定位到 `tokenize`。本次按指定提交审阅后，又找到一层此前方案没有准确覆盖的源码原因：`encode_rendered_chat()` 不只编码完整文本一次，还会为 stable/turn/user 边界及每个 `checkpoint_hint` **重新从文本开头编码前缀**。

因此本包采用两项分别可交付的改动：

1. **单请求一次主编码 + 有界局部边界验证**：消除检查点造成的重复前缀 BPE，保留原来的边界合法性、错误行为和全部检查点。
2. **前端跨请求 token 前缀复用**：在第一项通过后，保留全量 render，以真实字节前缀及安全 lexer 重启点复用旧 tokens，只编码变化后缀；GPU 仍独立决定自己的复用路径。

不能直接把上一轮提到的新上游 `exact_frontier/stable_frontier` API 当成 `44a2c6c` 已有接口；也不能在 tokenize 前读取尚未产生的 `append_frontier` 决策。完整更正在 [源码审计](docs/01_PINNED_SOURCE_AUDIT.md)。

## 使用顺序

先把 [AI 执行入口](AI_START_HERE.md) 交给开发 AI；设计入口是 [02_DESIGN_AND_ADRS.md](docs/02_DESIGN_AND_ADRS.md)，逐任务执行入口是 [07_AI_EXECUTION_PLAN.md](docs/07_AI_EXECUTION_PLAN.md)。**本包根目录的 AGENTS.md 只约束本包使用，不替换原仓 AGENTS.md。**

| 资料 | 用途 |
|---|---|
| [基线与证据](docs/00_SCOPE_BASELINE_EVIDENCE.md) | 线上观测、固定参数、未知项、统计限制 |
| [锁定源码审计](docs/01_PINNED_SOURCE_AUDIT.md) | 真实路径、复杂度、根因与前述方案纠偏 |
| [架构与决策](docs/02_DESIGN_AND_ADRS.md) | 两阶段方案、替代方案、作用域 |
| [边界正确性](docs/03_BOUNDARY_CORRECTNESS_SPEC.md) | 一次编码、局部前缀 oracle、NFC/BPE/added-token 证明义务 |
| [跨请求缓存](docs/04_INCREMENTAL_CACHE_SPEC.md) | 安全切点、资源隔离、生命周期、并发与退化 |
| [接口和修改地图](docs/05_CODE_CHANGE_MAP_AND_INTERFACES.md) | 实际文件、拟新增接口、配置与测试接入 |
| [指标契约](docs/06_OBSERVABILITY_SCHEMA.md) | schema19/20 共存、工作放大量、时间闭合 |
| [任务 DAG](docs/07_AI_EXECUTION_PLAN.md) | T00–T13，逐任务红绿测试与交付要求 |
| [测试与 Gate](docs/08_TEST_STRATEGY_AND_GATES.md) | 数据集、独立 oracle、边界/协议/生命周期/性能门 |
| [基准与回放](docs/09_BENCHMARK_AND_PRODUCTION_REPLAY.md) | legacy/single-pass/incremental 同机对照及污染控制 |
| [构建部署回滚](docs/10_BUILD_DEPLOY_ROLLBACK.md) | CUDA 构建、单 GPU 互斥、诊断镜像保护 |
| [Review/故障处理](docs/11_REVIEW_AND_FAILURE_PLAYBOOK.md) | 禁止走捷径、根因复核、失配处理 |
| [后续路线](docs/12_ROADMAP_AND_DECISION_RULES.md) | 单请求修复达标后是否还需要跨请求缓存 |
| [测试输入与工具](docs/14_FIXTURE_FORMAT_AND_HELPERS.md) | 86例fixture格式、8组生成器、版本/配对分析工具 |
| [固定来源](docs/13_SOURCE_REFERENCES.md) | 提交固定 URL、Git blob 身份 |

`data/` 是合成输入和用户报告的结构化摘要，不是用户的原始请求正文；`tools/` 是文档/数据/基准记录辅助工具，不是推理引擎。`evidence/` 区分本包自检结果与尚未执行的 NInfer/CUDA/4090 验收。

## 本包能证明什么

能证明已提供的资料结构、输入数据、辅助脚本及其自检情况。**不能证明 NInfer 已编译、token 边界实现已正确、4090 已加速或生产已切流。** 当前诊断补丁源码、原始 1617 条 JSONL 和真实请求正文没有在本次交付中获得；执行者须按 T00/T01 取证，不得把汇总表伪造为逐请求回放。
