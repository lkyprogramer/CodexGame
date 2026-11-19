# RTX 4090：NInfer / Strata 源码差量探索增补包

日期：2026-11-15（Asia/Shanghai）｜状态：**研究与执行规格完成；引擎改造、硬件资格与收益验证均未执行**。

## 结论

本轮没有发现足以承诺“4090 再提升几十个百分点”的通用补丁，也不建议迁移生产引擎。值得推进的是**一个有条件的机制差量、一个旧计划的源码细化**。另外保留一个源码缺口核查卡和一个上游正确性维护卡，不能把它们包装成四条新优化。

| ID | 本轮定位 | 当前结论 | 下一步到哪里为止 |
|---|---|---|---|
| D1 | OSAKANA 来源锚定、编辑断点恢复、命中后避免无用神经草稿 | `NEW_MECHANISM_CONDITIONAL` | 先证明旧 H1/H7 之外的差量；同 W 离线机会与成本门，不过即停 |
| H2 | YASAKANI 的低秩筛选＋候选重打分，应用于草稿头 | `PLANNED_NOT_RUN_SOURCE_REFINED` | 旧 H2 的具体实现参考；先绑定当前 head 独占成本、资产和显存 |
| K-PAIR | TensorFold 共输入多投影分段 dispatch | `SOURCE_BOUND_PAIR_P3_DELTA_UNBOUND` | 只核对 P3 / 当前运行分派；尚不是 GPU 候选 |
| M0 | Strata CUDA 终止窗口边界与下一请求 continuation | `UPSTREAM_IMPLEMENTED_DEPLOYMENT_UNBOUND` | 上游已有；查部署身份并补精确回归证据，不重写修复 |

**对你的实际优先级：**先消除“当前生产到底是哪棵树、哪些旧实验已经包含”的身份缺口；若你经常让 Agent 输出整份文件并作小改，D1 才值得继续。普通 Java 推理占主导、复制比例低时，D1 很可能应在离线门关闭。H2 只有在当前草稿头仍占可观关键路径、且不挤压长上下文时才值得做。Strata Flash-Next 主线本轮没有获得合格的新性能候选。

## 与旧包的关系

本包是非覆盖式增补，继承：

- `strata_observability_specpilot_foundation_20261106.zip`：完成路径归因、观测资格、SpecPilot 式证据控制。
- `strata_foundation_kernel_evidence_addendum_20261110.zip`：samir-vllm / Nabo 的 kernel 证据与数值审计。
- `strata_foundation_hyperkernel_service_addendum_20261110.zip`：服务生命周期、cache 工作量、异步所有权。

不复制第二套控制器，不重建 telemetry / dashboard，不解除任何旧 STOP。旧包身份和 SHA256 见 [LINEAGE](evidence/LINEAGE.md)。可将整个目录放入原工程 `docs/strata_4090_128k_lab/addenda/`；不要直接覆盖旧文件。NInfer 实验产物必须独立 engine family / artifact 身份，不能套 Strata 已有资格。

## 推荐阅读顺序

1. [决策与适用场景](docs/00_DECISION_SUMMARY.md) → [历史去重](docs/01_HISTORY_AND_NO_REPEAT.md)。
2. [底层架构比较](docs/03_DONOR_ARCHITECTURE.md) → [4090 可迁移边界](docs/04_PORTABILITY_AND_EXCLUSIONS.md)。
3. [D1](docs/06_D1_SOURCE_ANCHORED_COPY.md)、[H2](docs/07_H2_DRAFT_HEAD_REFINEMENT.md)、[源码核查与维护卡](docs/08_K_PAIR_AND_M0.md)。
4. [AI 执行入口](START_HERE_AI.md) → [Phase / Task DAG](docs/11_PHASES_TASKS_DAG.md) → `phases/`。
5. [测试与门槛](docs/10_TEST_PROTOCOL_AND_GATES.md)、[事件合同](docs/09_EVENT_AND_ARTIFACT_CONTRACT.md)、[成本与停止](docs/12_COST_AND_STOP_RULES.md)。
6. [与之前关注项目的合并去重](docs/14_PREVIOUS_DONORS_AND_REOPEN_RULES.md)。

## 本包交付了什么，没做什么

交付固定源码研究、不可重复台账、候选接口与消融规格、串行 Phase / 可并行 Task、最小测试、独立审阅/验证门、预算模板及失败交接。`templates/*.json` 是**有意不完整、默认拒绝执行**的模板，不是运行结果。文中未来 CLI 标为“待实现接口”，本包不提供或声称已实现这些工具。

本轮未 SSH、未启动引擎、未下载模型、未构建 donor、未运行 4090、未发送生成请求、未提交远程改动。作者数据是作者数据；历史报告是历史报告；文件校验不等于 GPU 通过。不存在本轮新增 tok/s 实测值。

所有来源、版本歧义和没有证据的地方见 [证据地图](docs/02_EVIDENCE_AND_SOURCE_MAP.md)、[source_lock.json](evidence/source_lock.json)。交付质量检查见 [VERIFICATION](evidence/VERIFICATION.md)。
