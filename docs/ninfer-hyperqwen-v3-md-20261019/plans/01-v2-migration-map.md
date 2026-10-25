# V2 → V3任务迁移与权威优先级

P0—P6的35个实施任务及门禁继续有效，保留在previous-v2。旧P7—P12的32个任务全部被下表承接；旧文档和JSON只是参考快照，不再调度执行，避免重复开发。

如果用户已经实现旧任务，不重做：按映射在H0核对实际commit/diff/tests，对新接口变化做delta验证，已有独立证据可登记为继承，但新的组合gate仍重测。没有执行证据时保持PENDING。

| 旧任务 | 原目标 | 新责任任务 | 处置 |
|---|---|---|---|
| P7-T01 | 冻结P6基线、tqLLM来源与drafter资产契约 | [H0-T01](tasks/H0-T01.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P7-T02 | 冻结实际长上下文与Java业务A/B语料 | [H0-T02](tasks/H0-T02.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P7-T03 | 增加采样式GPU阶段观测和稳定日志扩展 | [H0-T03](tasks/H0-T03.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P7-T04 | 建立实测资源账本和阶段采用门槛 | [H0-T04](tasks/H0-T04.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P8-T01 | 冻结策略、能力集合与新backend枚举 | [H1-T01](tasks/H1-T01.md) | 改掉Lookup=backend的建模；神经backend与每token source分开 |
| P8-T02 | MTP3/4/5完整shape与状态资格 | [H1-T04](tasks/H1-T04.md) | 原MTP3/4/5保留；W8/W16另列H3/H4，不把MTPmax扩大成15 |
| P8-T03 | 实现有界Prompt Lookup提案索引 | [H1-T02](tasks/H1-T02.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P8-T04 | 外部提案共同验收与同构batch集成 | [H1-T04](tasks/H1-T04.md)、[H1-T05](tasks/H1-T05.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P8-T05 | 低成本策略整体验证和E1候选 | [H1-T06](tasks/H1-T06.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P9-T01 | 固定完整验证数值oracle与优化点 | [H0-T05](tasks/H0-T05.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P9-T02 | 优化选定full-KV kernel或保持现状 | [H3-T02](tasks/H3-T02.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P9-T03 | 冻结verify图包络和资源生命周期 | [H3-T01](tasks/H3-T01.md)、[H3-T05](tasks/H3-T05.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P9-T04 | 完整验证优化的长上下文资格 | [H3-T06](tasks/H3-T06.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P10-T01 | 实现离线companion转换、typed绑定与只读模型view | [H6-T01](tasks/H6-T01.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P10-T02 | 建立独立DFlash2逐层reference和固定golden | [H6-T02](tasks/H6-T02.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P10-T03 | 实现DFlash2 dynamic-conv、selector和chain算子 | [H6-T03](tasks/H6-T03.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P10-T04 | feature捕获、ring、workspace与事务状态 | [H6-T04](tasks/H6-T04.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P10-T05 | DFlash2单链进入共同验证、采样路由与故障边界 | [H6-T05](tasks/H6-T05.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P10-T06 | 固定ring图、草稿词表与head内存消融 | [H2-T03](tasks/H2-T03.md)、[H6-T06](tasks/H6-T06.md) | 公共词表治理提前H2；DFlash2自身head/graph仍在H6 |
| P10-T07 | 固定ring DFlash2全量资格与24GB止损 | [H6-T07](tasks/H6-T07.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P11-T01 | 独立ProjectedG host archive和版本化identity | [H7-T01](tasks/H7-T01.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P11-T02 | 全局页代表索引与两级CPU oracle | [H7-T02](tasks/H7-T02.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P11-T03 | GPU coarse/refine选择、按headstage与Draft位置映射 | [H7-T03](tasks/H7-T03.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P11-T04 | 图外异步刷新、双stage和迟到任务隔离 | [H7-T04](tasks/H7-T04.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P11-T05 | 连接continuation、重写、slot与adapter生命周期 | [H7-T05](tasks/H7-T05.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P11-T06 | 检索成本进入后端策略与观测 | [H7-T06](tasks/H7-T06.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P11-T07 | 全局检索128K/248K远端依赖与端到端资格 | [H7-T07](tasks/H7-T07.md) | 保留功能并适配统一C10—C21；原任务PENDING不转为完成 |
| P12-T01 | 最终来源、架构与原定制保留审查 | [H5-T01](tasks/H5-T01.md)、[H8-T01](tasks/H8-T01.md) | 拆成H5低成本独立发布与H8完整融合发布，不再被高级资产拖住 |
| P12-T02 | 最终组合版本完整数值、业务与性能验收 | [H5-T02](tasks/H5-T02.md)、[H8-T02](tasks/H8-T02.md)、[H8-T03](tasks/H8-T03.md) | 拆成H5低成本独立发布与H8完整融合发布，不再被高级资产拖住 |
| P12-T03 | 生成只读artifact与部署ready profile | [H5-T03](tasks/H5-T03.md)、[H8-T03](tasks/H8-T03.md) | 拆成H5低成本独立发布与H8完整融合发布，不再被高级资产拖住 |
| P12-T04 | 获授权后的单卡试运行及实际回滚演练 | [H5-T03](tasks/H5-T03.md)、[H5-T04](tasks/H5-T04.md)、[H8-T04](tasks/H8-T04.md) | 拆成H5低成本独立发布与H8完整融合发布，不再被高级资产拖住 |
| P12-T05 | 封版、机器门禁与开发/生产资格分离 | [H5-T04](tasks/H5-T04.md)、[H8-T05](tasks/H8-T05.md) | 拆成H5低成本独立发布与H8完整融合发布，不再被高级资产拖住 |

## 新增而不是重复的工作

H1-T03条件融合，H2整套中文/Java词表治理，H3 W8完整形状，H4 W16/复制状态机/安全反馈/proposal-skip是本次主要新增。旧P9“优化热点”仍由H3/H4微基准验证，需要收益才采用；不再独立追加一套Attention实现。

## 冲突时的文档顺序

用户明确约束 → 根AI_EXECUTION_PROMPT → V3 design/C10—C21 → V3 master/task/phase → 继承P0—P6文档 → 旧tqLLM设计参考 → donor/附件说明。

这个顺序不授权放宽固定Target、gate或数据；发现规范冲突要在decision record中修订并重审，不能任选容易实现的一份。旧v2 scripts/phase_gate仅验证P0—P6；V3新checker读取本版注册表。

## 本次审查修订与继承优先级

previous-v2全部历史围栏/原文保持原字节；P0—P6目标、任务数与DAG仍继承。当前B29 baseline按 [plans/05](05-baseline-29-execution.md)先兑现P0生产测量；这不豁免其余P0或P6资格。旧统计helper不支持p95且未知规则静默忽略的行为由现行design/07、design/09明确禁止，不能把“原件保留”解释为允许照旧门禁。新14档/两采样轨/实际cache/Pi两层与正式统计规则覆盖原较窄执行举例，不让历史7档例子缩小本次范围。

## 2026-10-21继承限制更新

previous-v2/inputs仍保持所有原字节；其中“20×3通用下限”、greedy-only新路径描述和旧测试展开由现行plans/06、design/11替代。新增H1-T07承担确定草稿/Target sampling的实际概率与状态资格，原accept/processor/RNG复用，不新增整个phase或sampler。旧断言仍保留其历史出处，当前执行以registry/现行具名矩阵为准；不能将新计划写成已有GPU通过。
