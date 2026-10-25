# 完整任务范围审计

本轮逐项处置原144节点（113任务/31门禁）、373原断言及115份当前层文档。原断言不是删掉后宣称通过：全部ID/原文/状态保存在修订前403成员快照及[保全记录](../evidence/03-revision-provenance.md)所指JSON中。

新执行库18任务、4门禁。可选实验包含DFlash2、全局检索、W8/W16、utility、draft head、有限投影与上游选择/完整合并。去掉其强制串行依赖、重复全量验收与无关功能；没有因尚无实测就排除有性能机制的实验。新断言使用CHATPERF前缀，不偷换旧ID的含义。

| 原节点 | 原目标 | 处置 | 当前归属 | 理由 |
|---|---|---|---|---|
| P0-T01 | 冻结完整源码与实际合并冲突 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | K0-T01 | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P0-T02 | 核对生产三件套、代理配置与显存账本 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | K0-T01 | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P0-T03 | 冻结真实资源、旧 oracle 和 G1 素材 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P0-T04 | 建立 PROD/O 配对基线与冻结质量门槛 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P1-T01 | 串行合入上游里程碑（U01—U10） | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P1-T02 | 统一 B0 扫描、分段前缀与 B1 memo | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P1-T03 | 隔离 legacy DTO 并建立独立差分 oracle | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P1-T04 | 恢复 prepare_detail 与三协议请求体观测 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P1-T05 | 验证 typed alias 与新缓存边界语义 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P1-T06 | 验证 repetition guard、轮级故障与进度事件 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P1-DEVELOPMENT-READY | P2隔离开发准入（复用P1，不授予完整验收资格） | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P2-T01 | 串行合入上游里程碑（U11） | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P2-T02 | 补齐异步 export 的 fence 与生命周期回归 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P2-T03 | 对齐异步阶段耗时和导出指标 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P2-T04 | 实机混合热冷流量与导出压力验收 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P2-DEVELOPMENT-READY | P3隔离开发准入（复用P2，不授予完整验收资格） | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P3-T01 | 串行合入上游里程碑（U12—U17） | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P3-T02 | 整体验证 small-T MMA 与算子路由 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P3-T03 | 贯通三协议增量工具调用与历史存储 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P3-T04 | 固定测试注册与 skip77 策略 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P3-T05 | 验证 small-T 与工具流的端到端收益 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P3-DEVELOPMENT-READY | P4隔离开发准入（复用P3，不授予完整验收资格） | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P4-T01 | 串行合入上游里程碑（U18—U27） | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P4-T02 | 迁移 KV codec、序列化版本与缓存隔离 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P4-T03 | 整合决策 runtime、LoRA 和分支隔离 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P4-T04 | 迁移 schema22、无饥饿遥测和双系统观测 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P4-T05 | 隔离输出 UTF-8 修复与输入严格校验 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P4-T06 | 4090 上验证新 KV 质量、容量与性能 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P5-T01 | 串行合入上游里程碑（U28—U34） | OPTIONAL_UPSTREAM_OR_SHARED_QUALIFICATION | UP-T01 | 上游选择/完整合并进UP可选对照，必要共享验收合并到K4；不统一阻塞开工。 |
| P5-T02 | 验证双决策协议、模型发现与错误契约 | EXCLUDED_FEATURE_WORK | — | 决策接口/图像能力/playground不属于当前纯Chat性能验收。 |
| P5-T03 | 合入图像预处理身份、MRoPE 与媒体容量 | EXCLUDED_FEATURE_WORK | — | 决策接口/图像能力/playground不属于当前纯Chat性能验收。 |
| P5-T04 | 验收 playground 与历史日志显示 | EXCLUDED_FEATURE_WORK | — | 决策接口/图像能力/playground不属于当前纯Chat性能验收。 |
| P5-T05 | 统一验收最终 API 与多模态状态 | OPTIONAL_UPSTREAM_OR_SHARED_QUALIFICATION | UP-T01 | 上游选择/完整合并进UP可选对照，必要共享验收合并到K4；不统一阻塞开工。 |
| P6-T01 | 完成全量 ancestry 与定制保留审查 | OPTIONAL_UPSTREAM_OR_SHARED_QUALIFICATION | UP-T01 | 上游选择/完整合并进UP可选对照，必要共享验收合并到K4；不统一阻塞开工。 |
| P6-T02 | 最终 128K—248K Java Agent 配对验收 | OPTIONAL_UPSTREAM_OR_SHARED_QUALIFICATION | — | 上游选择/完整合并进UP可选对照，必要共享验收合并到K4；不统一阻塞开工。 |
| P6-T03 | 构建不可变镜像并演练启动与排空 | OPTIONAL_UPSTREAM_OR_SHARED_QUALIFICATION | — | 上游选择/完整合并进UP可选对照，必要共享验收合并到K4；不统一阻塞开工。 |
| P6-T04 | 在批准窗口执行生产试运行 | OPTIONAL_UPSTREAM_OR_SHARED_QUALIFICATION | — | 上游选择/完整合并进UP可选对照，必要共享验收合并到K4；不统一阻塞开工。 |
| P6-T05 | 实际回滚演练与最终交付 | OPTIONAL_UPSTREAM_OR_SHARED_QUALIFICATION | — | 上游选择/完整合并进UP可选对照，必要共享验收合并到K4；不统一阻塞开工。 |
| P0-DEVELOPMENT-READY | 隔离开发准入（不授予候选或生产资格） | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P0-GATE | 统一代码 review 与集成测试门禁 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P1-GATE | 统一代码 review 与集成测试门禁 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P2-GATE | 统一代码 review 与集成测试门禁 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P3-GATE | 统一代码 review 与集成测试门禁 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P4-GATE | 统一代码 review 与集成测试门禁 | REUSE_EXISTING_EVIDENCE_WITH_GAPS | PERF-READY | 已完成范围及原失败/缺口复用；改变路径才补证，不据旧门禁重跑。 |
| P5-GATE | 统一代码 review 与集成测试门禁 | OPTIONAL_UPSTREAM_OR_SHARED_QUALIFICATION | K4-QUALIFIED, K4-GATE | 上游选择/完整合并进UP可选对照，必要共享验收合并到K4；不统一阻塞开工。 |
| P6-GATE | 统一代码 review 与集成测试门禁 | OPTIONAL_UPSTREAM_OR_SHARED_QUALIFICATION | K4-QUALIFIED, K4-GATE | 上游选择/完整合并进UP可选对照，必要共享验收合并到K4；不统一阻塞开工。 |
| H0-T01 | 冻结实际P6基线、源码与shape目录 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K0-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H0-T02 | 冻结语料、请求矩阵与配对benchmark驱动 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K0-T02 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H0-T03 | 新增非侵入式round与路由观测 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K0-T02 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H0-T04 | 实现显存、host与Graph资源账本 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K0-T02 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H0-T05 | 建立逐层与整轮数值对照协议 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K0-T02 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H0-T06 | 实现fail-closed阶段证据检查 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K0-T02 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H0-GATE | P6基线、语料、观测、资源与证据统一评审验收 | SHARED_GATE_REPLACES_SERIAL_GATE | K4-QUALIFIED | 适用验证合并至K0-GATE/K4-QUALIFIED，实际发布另K4-GATE；旧门禁不伪PASS。 |
| H1-T01 | 落盘hybrid契约与显式能力准入 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H1-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H1-T02 | 实现request-local有界Lookup索引 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H1-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H1-T03 | 实现连续前缀的head/tail融合 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H1-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H1-T04 | 接入共同verify与完整MTP对齐 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H1-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H1-T05 | 补齐多lane、取消和continuation回归 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H1-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H1-T06 | 建立低宽度MTP/Lookup资格候选 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H1-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H1-T07 | 资格确定性草稿与Target sampling验收 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H1-T07 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H1-GATE | 现有W≤6的MTP＋Lookup统一评审验收 | SHARED_GATE_REPLACES_SERIAL_GATE | K4-QUALIFIED | 适用验证合并至K0-GATE/K4-QUALIFIED，实际发布另K4-GATE；旧门禁不伪PASS。 |
| H2-T01 | 校准中文/Java/工具调用草稿ID候选 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H2-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H2-T02 | 离线生成只读proposal-head companion | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H2-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H2-T03 | 绑定closed head profile与Graph身份 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H2-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H2-T04 | 验证proposal映射、完整输出与质量 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H2-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H2-T05 | 用整轮成本选择词表而非coverage最大值 | OPTIONAL_PERFORMANCE_EXPERIMENT | H2-T01 | 有性能可能，归入同路线代表任务；不是后续必做或仅参考。 |
| H2-GATE | 中文/Java草稿词表与head companion统一评审验收 | OPTIONAL_PERFORMANCE_EXPERIMENT | H2-T01 | 有性能可能，归入同路线代表任务；不是后续必做或仅参考。 |
| H3-T01 | 冻结W8 frame及物理容量契约 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H3-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H3-T02 | 扩展W8完整KV Attention | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H3-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H3-T03 | 扩展W8 GDN记录、许可与回放 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H3-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H3-T04 | W8 MTP alignment与next-round闭环 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H3-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H3-T05 | W8 Graph闭合与同构batch调度 | OPTIONAL_PERFORMANCE_EXPERIMENT | H3-T01 | 有性能可能，归入同路线代表任务；不是后续必做或仅参考。 |
| H3-T06 | W8真实长上下文与业务资格 | OPTIONAL_PERFORMANCE_EXPERIMENT | H3-T01 | 有性能可能，归入同路线代表任务；不是后续必做或仅参考。 |
| H3-GATE | W8完整链与Graph资格统一评审验收 | OPTIONAL_PERFORMANCE_EXPERIMENT | H3-T01 | 有性能可能，归入同路线代表任务；不是后续必做或仅参考。 |
| H4-T01 | 冻结W16预算、frame与准入闭合 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H4-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H4-T02 | W16完整Attention与投影shape资格 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H4-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H4-T03 | W16 ReplaySSM和MTP alignment状态资格 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H4-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H4-T04 | 实现每lane复制策略及安全反馈 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H4-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H4-T05 | 接入双宽度Graph及proposal-skip | OPTIONAL_PERFORMANCE_EXPERIMENT | H4-T01 | 有性能可能，归入同路线代表任务；不是后续必做或仅参考。 |
| H4-T06 | 验证动态长块的实际适用边界 | OPTIONAL_PERFORMANCE_EXPERIMENT | H4-T01 | 有性能可能，归入同路线代表任务；不是后续必做或仅参考。 |
| H4-GATE | W16、每lane策略与proposal-skip统一评审验收 | OPTIONAL_PERFORMANCE_EXPERIMENT | H4-T01 | 有性能可能，归入同路线代表任务；不是后续必做或仅参考。 |
| H5-T01 | 低成本组合代码与数值最终审查 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K4-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H5-T02 | 完整Java Agent和长上下文A/B/A | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K4-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H5-T03 | 发布不可变低成本profile并受控试运行 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K4-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H5-T04 | 实际回滚与低成本路线封版 | CONSOLIDATED_SHARED_VALIDATION | K4-T01 | 归并选中路线的定向合同及一次K4共同资格，不重复建工具/跑矩阵。 |
| H5-GATE | 低成本路线独立发布/回滚统一评审验收 | SHARED_GATE_REPLACES_SERIAL_GATE | K4-QUALIFIED | 适用验证合并至K0-GATE/K4-QUALIFIED，实际发布另K4-GATE；旧门禁不伪PASS。 |
| H6-T01 | 冻结DFlash2资产并实现离线typed绑定 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H6-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H6-T02 | 建立DFlash2逐层独立参考 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H6-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H6-T03 | 实现DFlash2动态卷积与selector算子 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H6-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H6-T04 | 实现feature捕获、ring和状态事务 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H6-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H6-T05 | DFlash2进入统一fusion/verify/故障边界 | OPTIONAL_PERFORMANCE_EXPERIMENT | H6-T01 | 有性能可能，归入同路线代表任务；不是后续必做或仅参考。 |
| H6-T06 | 草稿Graph、head与共驻资源消融 | OPTIONAL_PERFORMANCE_EXPERIMENT | H6-T01 | 有性能可能，归入同路线代表任务；不是后续必做或仅参考。 |
| H6-T07 | ring-only DFlash2资格与止损 | OPTIONAL_PERFORMANCE_EXPERIMENT | H6-T01 | 有性能可能，归入同路线代表任务；不是后续必做或仅参考。 |
| H6-GATE | 原生27B DFlash2 bounded ring统一评审验收 | OPTIONAL_PERFORMANCE_EXPERIMENT | H6-T01 | 有性能可能，归入同路线代表任务；不是后续必做或仅参考。 |
| H7-T01 | 实现独立ProjectedG host archive | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H7-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H7-T02 | 实现全局页摘要与两级检索oracle | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H7-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H7-T03 | GPU检索、DraftKV重建与位置映射 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H7-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H7-T04 | 异步refresh、双staging与事件隔离 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | H7-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H7-T05 | 串接L1/L2/L3、重写及slot生命周期 | OPTIONAL_PERFORMANCE_EXPERIMENT | H7-T01 | 有性能可能，归入同路线代表任务；不是后续必做或仅参考。 |
| H7-T06 | 将检索与恢复成本纳入后端选择 | OPTIONAL_PERFORMANCE_EXPERIMENT | H7-T01 | 有性能可能，归入同路线代表任务；不是后续必做或仅参考。 |
| H7-T07 | 全局检索长上下文端到端资格 | OPTIONAL_PERFORMANCE_EXPERIMENT | H7-T01 | 有性能可能，归入同路线代表任务；不是后续必做或仅参考。 |
| H7-GATE | 独立archive与全局selective drafting统一评审验收 | OPTIONAL_PERFORMANCE_EXPERIMENT | H7-T01 | 有性能可能，归入同路线代表任务；不是后续必做或仅参考。 |
| H8-T01 | 全融合所有权、来源与定制保留审查 | CONSOLIDATED_SHARED_VALIDATION | K4-T01 | 归并选中路线的定向合同及一次K4共同资格，不重复建工具/跑矩阵。 |
| H8-T02 | 最终组合数值、协议和状态矩阵 | CONSOLIDATED_SHARED_VALIDATION | K4-T01 | 归并选中路线的定向合同及一次K4共同资格，不重复建工具/跑矩阵。 |
| H8-T03 | 最终性能、容量与采用profile选择 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K4-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H8-T04 | 完整候选受控试运行及实机回滚 | CONSOLIDATED_SHARED_VALIDATION | K4-T01 | 归并选中路线的定向合同及一次K4共同资格，不重复建工具/跑矩阵。 |
| H8-T05 | 证据封版与完成/阻断清单交付 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K4-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| H8-GATE | 最终组合资格和受控发布统一评审验收 | SHARED_GATE_REPLACES_SERIAL_GATE | K4-QUALIFIED | 适用验证合并至K0-GATE/K4-QUALIFIED，实际发布另K4-GATE；旧门禁不伪PASS。 |
| K0-T01 | 固定donor调用链与实际P6 kernel地图 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K0-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| K0-T02 | 扩展既有观测为Op/整轮/服务三层配对基线 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K0-T02 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| K0-T03 | 建立raw与correction的独立数值、许可参考 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K1-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| K0-T04 | 冻结有限调优、资源身份与采用合同 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K0-T04 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| K1-T01 | 新增带类型的FP32 correction记录布局 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K1-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| K1-T02 | 从原GDN计算点输出correction records | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K1-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| K1-T03 | 实现同序correction all-layer fold及conv提交 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K1-T02 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| K1-T04 | 将correction接入许可、Graph身份和fallback | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K1-T02 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| K1-T05 | 完成correction整轮数值及净收益实验 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K1-T02 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| K2-T01 | 调优已有D128 gated RMSNorm的CTA映射 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K2-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| K2-T02 | 对Qwen GDN验证尝试有限窗口预载 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K2-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| K2-T03 | 按热点验证现有Q4/Q5 small-T计划 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K2-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| K2-T04 | 冻结组合调优表并校验Graph与cost身份 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K2-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| K3-T01 | 生成actual GraphCatalog与GPU生命周期账本 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K3-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| K3-T02 | 压缩有证明的scratch并刷新固定views | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K3-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| K3-T03 | 验证一个受限MTP投影fork/join候选 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K3-T02 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| K3-T04 | 压力验证Graph指针、escape与poison边界 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K3-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| K4-T01 | 完成kernel-only整体验收与采用选择 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K4-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| K4-T02 | 对接H1—H8宽度与cost合同，避免重复实现 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | K4-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| K4-T03 | kernel-only受控试运行与实际回滚 | CONSOLIDATED_SHARED_VALIDATION | K4-T01 | 归并选中路线的定向合同及一次K4共同资格，不重复建工具/跑矩阵。 |
| S0-T01 | 建立共享execution cost book与shadow观测 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | S0-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| S0-T02 | 实现受限utility执行选择与公平保护 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | S0-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| S0-T03 | 校准eligible缓存候选的restore成本 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | S0-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| S0-T04 | 验证runtime策略隔离净收益与候选回退 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | S0-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| K0-GATE | 证据、原始算术与有限调优合同统一review与集成验收 | SHARED_GATE_REPLACES_SERIAL_GATE | K4-QUALIFIED | 适用验证合并至K0-GATE/K4-QUALIFIED，实际发布另K4-GATE；旧门禁不伪PASS。 |
| K1-GATE | GDN correction记录与许可提交统一review与集成验收 | SHARED_GATE_REPLACES_SERIAL_GATE | K4-QUALIFIED | 适用验证合并至K0-GATE/K4-QUALIFIED，实际发布另K4-GATE；旧门禁不伪PASS。 |
| K2-GATE | SM89有限小kernel与投影计划统一review与集成验收 | SHARED_GATE_REPLACES_SERIAL_GATE | K4-QUALIFIED | 适用验证合并至K0-GATE/K4-QUALIFIED，实际发布另K4-GATE；旧门禁不伪PASS。 |
| K3-GATE | Scratch生命周期与可选Graph overlap统一review与集成验收 | SHARED_GATE_REPLACES_SERIAL_GATE | K4-QUALIFIED | 适用验证合并至K0-GATE/K4-QUALIFIED，实际发布另K4-GATE；旧门禁不伪PASS。 |
| K4-GATE | kernel-only资格、发布与回滚统一review与集成验收 | SHARED_GATE_REPLACES_SERIAL_GATE | K4-QUALIFIED | 适用验证合并至K0-GATE/K4-QUALIFIED，实际发布另K4-GATE；旧门禁不伪PASS。 |
| S0-GATE | 可选utility与恢复成本统一review与集成验收 | OPTIONAL_PERFORMANCE_EXPERIMENT | S0-T01 | 有性能可能，归入同路线代表任务；不是后续必做或仅参考。 |
| P6-QUALIFIED | 迁移候选隔离资格（不包含生产发布） | OPTIONAL_UPSTREAM_OR_SHARED_QUALIFICATION | K4-QUALIFIED, K4-GATE | 上游选择/完整合并进UP可选对照，必要共享验收合并到K4；不统一阻塞开工。 |
| K4-QUALIFIED | kernel候选资格（不包含生产发布） | SHARED_GATE_REPLACES_SERIAL_GATE | K4-QUALIFIED | 适用验证合并至K0-GATE/K4-QUALIFIED，实际发布另K4-GATE；旧门禁不伪PASS。 |
| H5-QUALIFIED | 低成本组合候选资格（不包含生产发布） | SHARED_GATE_REPLACES_SERIAL_GATE | K4-QUALIFIED | 适用验证合并至K0-GATE/K4-QUALIFIED，实际发布另K4-GATE；旧门禁不伪PASS。 |
| H8-QUALIFIED | 完整组合候选证据封版（不包含生产发布） | SHARED_GATE_REPLACES_SERIAL_GATE | K4-QUALIFIED | 适用验证合并至K0-GATE/K4-QUALIFIED，实际发布另K4-GATE；旧门禁不伪PASS。 |
| S0-T05 | runtime策略受控生产试运行与实际回滚 | CONSOLIDATED_PERFORMANCE_EXPERIMENT | S0-T01 | 直接性能工作保留，合并重复实现/验证并使用单候选预算。 |
| S0-QUALIFIED | runtime策略隔离候选资格（不包含生产发布） | OPTIONAL_PERFORMANCE_EXPERIMENT | S0-T01 | 有性能可能，归入同路线代表任务；不是后续必做或仅参考。 |

保留范围：数值/状态/采样/缓存身份/异步生命周期/容量与故障合同是性能改造正确性的必要条件。只验证选中改动影响的路径，不为纯Chat要求决策API、视觉、UI、多协议、35B/NVFP4或全面上游资格。

P5未完成导入已停止并单独保留，不能丢弃后假装没有成本，也不能拿未评审树继续性能研发。
