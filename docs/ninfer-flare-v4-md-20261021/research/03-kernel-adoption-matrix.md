# 采用矩阵：性能机制与适用前提

| 机制 | 当前已有 | 新增实验 | 不做的重复工作 |
|---|---|---|---|
| GDN replay | raw紧凑记录、全层fold | 原计算点correction与完整round对照 | 消除不存在的全state快照或48次launch |
| gated norm | RMSNorm+SiLU融合 | D128 gated CTA分组 | 再实现融合 |
| small-T | P3已集成Q4/Q5路由 | 真实热点的有限SM89配置 | 重做已过数值矩阵 |
| workspace | 现有planner/Graph | 按最后consumer复用 | 新allocator框架 |
| 投影并行 | 已有部分融合 | 独立窄分支fork/join | 拆开已融合GDN |
| Lookup/扩宽 | 原MTP/Target接受器 | 实际前缀融合与W8/W16 | 第二套采样器、全路线必做 |
| DFlash2/检索 | 需精确资产/身份核验 | 按准入选一个有界实验 | 35B资格套27B、通用向量平台 |
| utility | 现有调度/恢复权威 | 合格路线的有限成本规则 | 通用QoS/多租户平台 |
| 上游合并 | U01—U27已吸收 | 有益共享改动或完整U34对照 | 为历史完整性重做P1—P4 |

细节以[注册表](../plans/02-task-registry.md)及[预算](../plans/08-validation-budget-and-estimate.md)为准。未选择的路线不执行、不占本次预算，也不造PASS。
