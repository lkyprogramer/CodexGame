# 候选卡索引

**十二项均未获得本机新的warm长会话性能资格。它们不是自动实现队列。**

2026-10-31[Astra复核后本轮收口](../reports/ASTRA_REASSESSMENT_20261031.md)：当前NO_QUALIFIED_CANDIDATE，F02保留DEFERRED_NEW_EVIDENCE；F03本轮快照审计已关闭。下表保留方向卡类别，不意味着继续诊断或实现。

| ID | 方向 | 当前状态 | 数值等级 |
|---|---|---|---|
| [F01](F01_KV_SELECTED_REUSE.md) | 现有selected-KV路径：只查尚未解释的读取/失效 | `COVERED_DIAGNOSTIC_ONLY` | E0 |
| [F02](F02_EXACT_LOAD_LAYOUT.md) | 保留既有融合与算术的载入布局改造 | `DEFERRED_NEW_EVIDENCE` | E0 |
| [F03](F03_LIVE_MEMORY_LIFETIME.md) | 活跃内存压力与不必要驻留的生命周期诊断 | `DIAGNOSTIC_ONLY` | E0 |
| [F04](F04_EXACT_QSA_SELECTION.md) | QSA长索引与精确选择的条件分支 | `DEFERRED_NEW_EVIDENCE` | E0 |
| [F05](F05_MOE_GROUP_SCRATCH.md) | 保留全Dm的MoE中间行窗复用 | `HYPOTHESIS_UNQUALIFIED` | E0 |
| [F06](F06_STABLE_INTEGER_GROUPING.md) | 非fused路径的稳定整数count/rank/scatter | `HYPOTHESIS_UNQUALIFIED` | E0 |
| [F07](F07_MMQ_POOL_EPOCH.md) | MMQ尺寸分级与有代际的scratch借还 | `HYPOTHESIS_UNQUALIFIED` | E0 |
| [F08](F08_DEADLINE_PLACEMENT.md) | 按row成本和未完成复制债务决定CPU/GPU归属 | `DEFERRED_QUALITY` | E1 |
| [F09](F09_NUMERICAL_GPU_KERNELS.md) | SM89 tensor/attention/GDN数值路径重写 | `DEFERRED_QUALITY` | E1 |
| [F10](F10_TARGET_FIXED_DRAFT.md) | 改变草稿成本结构，保持完整target验证 | `DEFERRED_SOURCE_AND_QUALITY` | E1 |
| [F11](F11_QUALITY_SPEED_FRONTIER.md) | 改变目标计算的质量—速度前沿 | `OUT_OF_MAINLINE` | Q |
| [F12](F12_ORCHESTRATION_GAPS.md) | 已具graph/doorbell/overlap的供给缺口诊断 | `COVERED_DIAGNOSTIC_ONLY` | E0 |
