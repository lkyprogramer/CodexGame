> V2 参考快照：P7—P12 不再是执行权威；按根目录 `plans/00-master-plan.md` 和 `plans/01-v2-migration-map.md` 执行。本文保留历史设计与来源，不表示实现完成。

# 决策记录、依赖与未采纳路线

| ADR | 决定 | 原因 / 推翻条件 |
|---|---|---|
| TQ-01 | 语义迁移而非全引擎合并 | `.ninfer`与现有Target/缓存/接口契约优先；用户明确改变产品方向才重开 |
| TQ-02 | 保留上游rk4v4，不恢复E8 lattice | 原包P4已处理格式变更；附件旧建议失效 |
| TQ-03 | 第一批先MTP/Lookup | 27B暂无DFlash2；减少不必要新模型/内存前置 [N01] |
| TQ-04 | chain K<=5先于tree | 保留1—6列体系与单前缀ReplaySSM；tree需新siblings屏蔽、conv/GDN分支状态、概率路径 [N07] |
| TQ-05 | 完整TargetKV与词表验证 | Draft近似不能变成Target近似；Target稀疏只另案 [R03] |
| TQ-06 | ProjectedG独立archive | TargetL2不足以重建drafterfeatures [T04]；若G不充分则BLOCKED，改另一个有证据方案 |
| TQ-07 | fixedring/阶段刷新，host在图外 | 固定指针/shape；不虚构GPUgraph覆盖CPUarchive操作 [T05] |
| TQ-08 | 不做生产自动memory-fit降质 | 既定Target/context不能被改变；不足返回NO_GO [T08] |
| TQ-09 | 新路径greedy优先 | lattice分数不是真实q；概率守恒另有独立方法与验证 |
| TQ-10 | 预算和性能均可否决高级阶段 | 4090部署目标高于技术堆砌；之前合格优化可单独保留 |

## 可研究但不进入本轮task依赖

**Target-guided retrieval。** SpecExtend提供基于Target attention的context重要性方向，但其信息不是DraftKV。只有P11证明基于Draft页代表的接受损失显著，且抓取少量FA层页级分数可控制在round关键路径2%之内时，才增加一个feature-gated实验。不能把GDN状态叫attention matrix，不能每轮把全矩阵传回CPU。[R02]

**Token tree。** 只有链式在高接受短上下文明显受候选不足限制，且预算还有空间，才独立设计tree parent/depth/mask、逐branch conv/GDN及accepted-path commit。tqLLM已有路径可参考，但NInfer决策segmented attention共享prefix分支不等同于可任意树形验证。[T02/T07/N05]

**Target TQ量化或新TCQ KV。** 可能释放给drafter的显存，但改变Target代表值和质量，是独立模型格式项目；不能在本次“同Target性能优化”中悄悄切入。[T01/T08]

**长上下文drafter训练。** 只有ring与global检索都正确、计算成本已优化且仍有明显接受率问题，才用冻结长上下文数据实验；需要新模型、数据/训练预算和单独验证，本包不自动授权训练。LongSpec是专门模型/位置方案，不能宣称不训练照搬即可得相同收益。[R01]

## 尚未关闭的外部依赖

真实P6 merged SHA、当前生产配置/driver、完整drafter revision/tensors/license、转换后device bytes、真实Java冻结语料与4090测量。每项都有P7或P10责任task；缺失时对应功能保持BLOCKED，不用TODO代码或猜测值替代。
