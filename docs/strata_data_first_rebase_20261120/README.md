# Strata 4090 数据优先重基线与后续探索包

日期：2026-11-20（北京时间）  
状态：**研究与实施规格已交付；采集器改造、Strata 构建、4090 测试及部署均未在本轮执行。**  
补遗：上游发布 v0.2.17 后的新锁定点、4090 实测回填和评估方法修正见 [26 补遗](docs/26_V0217_REBASE_ADDENDUM.md)；正文保持 v0.2.16 快照原样。

本包依据用户仓库 [4090-report / c5f05b46](https://github.com/lkyprogramer/CodexGame/tree/c5f05b46c5fc895f7d7a74979cf526f8c4f3dc8b) 的最新归档，研究 Strata **App/Terminal 0.2.16、Control/Engine 0.1.62**。它是可独立阅读、可交给 AI 执行的完整计划，整合而非覆盖两个旧包：

- `strata_foundation_kernel_evidence_addendum_20261110`：保留归因、数值、构建与反例门；修正“计划等于已实现”的误读。
- `ninfer_strata_source_delta_exploration_20261115`：保留 D1/H2/K-PAIR/M0 的原始状态；不再次以新名称启动旧实验。

## 结论先读

**值得继续，但首先做观测适配和最小采集补洞，不是立即修改推理算法。**

新版 Strata 已有 `/metrics`、`/v1/telemetry`、Terminal monitor、请求摘要、批次与 native diagnostics；没有必要再建一套监控平台。但它们还不能充分回答：

1. 这条真实 agent 任务慢在哪里：外层等待、HTTP/服务排队、engine admission、恢复/重算、GPU/CPU/DMA、SSE 发布？
2. `reused` 是否真的来自 GPU ready 状态，还是 RAM/SSD 恢复；空闲父会话是否被挤掉？
3. 哪个实际 dispatch/shape/物理工作量处于完成路径，消掉它是否真的缩短任务？
4. 监控本身有没有改执行路径、增加同步或丢事件？

**本轮进入候选资格队列的只有两项：** C01 同会话 suffix 碰撞恢复的离线反事实；C02 实际 MoE 行填充 census。两者目前都是“要数据验证的假说”，不是已证明的新提速路线。其他项目主要贡献指标语义、失败案例和适用边界。

## 阅读路径

| 角色/问题 | 阅读顺序 |
|---|---|
| 快速做决定 | [00 结论](docs/00_EXECUTIVE_DECISION.md) → [18 候选](docs/18_CANDIDATES_AND_STOP_RULES.md) |
| 核实历史、避免重测 | [01 最新历史](docs/01_BASELINE_AND_HISTORY.md) → [02 禁重台账](docs/02_NO_REPEAT_LEDGER.md) → [03 复用与迁移](docs/03_EXISTING_ASSETS_AND_REBASE.md) |
| 先把数据做对 | [04 metrics 审计](docs/04_STRATA_METRICS_AUDIT.md) → [05 数据模型](docs/05_DATA_MODEL_AND_MEASUREMENT.md) → [06 最小挂点](docs/06_MINIMAL_INSTRUMENTATION.md) → [07 采集链](docs/07_COLLECTOR_AND_REPORT_PIPELINE.md) |
| 控制观测代价 | [08 开销与 Ada profiling](docs/08_OBSERVER_BUDGET_AND_ADA_PROFILING.md) |
| 真正评估收益 | [09 工作负载](docs/09_WORKLOAD_AND_CORRECTNESS.md) → [10 统计门](docs/10_EVALUATION_AND_STATS.md) |
| 深入六个来源 | [11 综合](docs/11_SOURCE_SYNTHESIS.md)；[12 QuixiInfer](docs/12_DONOR_QUIXI.md)、[13 Kinetic](docs/13_DONOR_KINETIC.md)、[14 Speedy](docs/14_DONOR_SPEEDY.md)、[15 FlashInfer](docs/15_DONOR_FLASHINFER.md)、[16 Blink](docs/16_PAPER_BLINK.md)、[17 PolyStrata](docs/17_DONOR_POLYSTRATA.md) |
| 交给执行 AI | [AGENTS](AGENTS.md) → [19 Phase/Task](docs/19_PHASE_TASK_PLAN.md) → [20 验收用例](docs/20_ACCEPTANCE_TEST_MATRIX.md) → [21 Runbook](docs/21_RUNBOOK_AND_HANDOFF.md) |
| 落入现有监控与预算 | [22 面板](docs/22_MONITOR_DASHBOARD_SPEC.md) → [23 决策/预算](docs/23_DECISION_AND_BUDGET.md) |
| 核来源与交付验收 | [24 来源目录](docs/24_SOURCE_CATALOG.md) → [25 静态验证](docs/25_PACKAGE_VERIFICATION.md) |
| v0.2.17 之后从哪里接着做 | [26 补遗](docs/26_V0217_REBASE_ADDENDUM.md) |

## 包内交付物与边界

- `docs/`：事实审计、最小设计、分阶段执行计划、测试与停测条件。
- `schemas/`：新事件附件的 JSON Schema；只定义外部数据边界，不取代旧 REQUESTS/WINDOWS/DEPENDENCIES。
- `templates/`：待绑定/不可执行的合同、证据、决策与预算模板，以及 AI 启动说明。
- `evidence/`：固定来源锁、历史状态与本轮静态验证回执。
- `MANIFEST.sha256`：包内文件校验；它不证明上游二进制或 GPU 实测。

执行起点见[AI_START_HERE](templates/AI_START_HERE.md)，结构与语义边界见[Schema说明](schemas/README.md)。先P2.0审现成L0证据，确有决策字段缺口才补相应hook；L0足够不改engine。

**没有提供假装能直接跑的采集器。** 文中的新模块和新接口均标为 PROPOSED；只有 [03](docs/03_EXISTING_ASSETS_AND_REBASE.md) / [21](docs/21_RUNBOOK_AND_HANDOFF.md) 指定的已存在命令可当现有工具。默认 GPU/模型请求预算为 **0**；本包不是停服、升级、下载权重或运行 128K 压测的授权。

## 新旧基线关系

此次固定的上游 release tag commit 为 `64524fb9fc82222ddce554c0643b64f056ec8366`，main 为 `58ee3227720629ff2e41d640165ebe89c880dfef`。二者相关 engine/telemetry 文件经 diff 未变；**实际 Linux 发布引擎 build/source 仍待现场绑定**，release 包 digest 不是解压后的 binary digest。

用户旧 Strata 档案确认的是 Flash-Next **GSQ-RCO IQ3_XXS 两分片**、Xeon Silver 4216 / PCIe Gen3×16 等历史配置；不是简单从记忆填入 IQ3_S。新测的模型、主机与生效配置必须再绑定，不自动搬用旧值。11/18 最新 130K 多会话记录属于 Dense 27B NInfer/HyperQwen；借它的观测教训，不借它的性能结论。

推荐导入位置：`CodexGame/docs/strata_data_first_rebase_20261120/`。原报告、raw、gold、旧合同原位保留。本轮未提交到 GitHub。

