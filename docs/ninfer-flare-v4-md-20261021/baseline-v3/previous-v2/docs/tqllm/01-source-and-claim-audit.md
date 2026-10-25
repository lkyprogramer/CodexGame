> V2 参考快照：P7—P12 不再是执行权威；按根目录 `plans/00-master-plan.md` 和 `plans/01-v2-migration-map.md` 执行。本文保留历史设计与来源，不表示实现完成。

# 对附带分析的逐项核实

不是否定附件的总体方向；把它从研究建议变成生产开发计划，需要补齐checkpoint、状态、数值、容量和真实基准的前置条件。来源编号见[证据目录](09-source-evidence.md)。

| 编号 | 分析中的主张 | 核实结论 | 依据 | 落地修正 | 责任task |
|---|---|---|---|---|---|
| A01 | 附件56—82：检索候选最多65536远端tokens | VERIFIED | T06 | 保留判断；这是候选覆盖上限，不是drafter总窗口，也不是所有上下文硬上限。 | P11-T02 |
| A02 | 附件84—109：完整DraftKV256K约5GiB | CONDITIONAL_GEOMETRY | T03/T04/T08 | 20KiB/token算例成立，但实际layer/head/stride以模型manifest与显存测量为准，文件大小不等于设备大小。 | P7-T04 |
| A03 | 附件111—129：检索关闭部分CUDA Graph/batchfast path | VERIFIED | T03/T05 | 限定常规draft快速路径，不声称所有Target graph同时关闭。 | P11-T04 |
| A04 | 附件175—185：全局页索引保持查询常数 | CORRECTION | T06/R01 | GPU工作集可有界；主机archive仍O(N)，扫描页摘要O(N/page)，不能宣称整个算法O(1)。 | P11-T02 |
| A05 | 附件222：直接从NInfer L2调入远端DraftKV | CORRECTION | T04/N04 | L2 Target状态没有所需Draft投影；建立独立有界DraftArchive，复用传输设施而非强转payload。 | P11-T01 |
| A06 | 附件240：随机采样只需真实draftq | QUALIFY | T07/N05 | ratio方法需要条件q和residual；lattice分数不是q。先greedy，采样走原合格后端；target-sample-match是独立后续方案。 | P8-T01 |
| A07 | 附件313—317：K4/5适配5/6列验证 | PARTLY_VERIFIED | N01/N07 | Attention列数相容；还须核对整个schedule、GDN、projection、graph及sampling契约。 | P8-T02 |
| A08 | 附件363—367：现有27B直接对比MTP和DFlash2 | CORRECTION | N01/N03 | 27B没有DFlash2产品路径；P10是前置，不能把它放进尚未实现的P8基准。 | P10-T01 |
| A09 | 附件动态MTP/DFlash切换 | NEW_DESIGN_NOT_DONOR_FEATURE | T08/N06 | tqLLM mtp-from是prompt阈值；NInfer新增能力掩码/校准策略，先请求边界选择。 | P8-T01 |
| A10 | 附件340—346：accepted_per_round用于有效吞吐 | CORRECTION | N05 | 用实际committed，包括修正/bonus，分母用关键路径wall time；重叠阶段不求和。 | P7-T03 |
| A11 | 附件419：保留262KE8KV | SUPERSEDED_BASELINE | 原包P4 | 基于上游整合后的rk4v4；不可把旧E8别名/缓存读回。 | P7-T01 |
| A12 | 附件社区长上下文倍数 | UNVERIFIED_AS_CONTROLLED_AB | 用户附件 | 附件有异上下文3090比较和第三方运行；未取得其完整配置/原日志，不用于本机收益承诺。 | P7-T02 |
| A13 | DFlash2 draft-max降低必然减少draft计算 | NEW_CAUTION | T05/T08 | 物理block B取训练配置，want可能只截断返回候选；分别记录physicaldraftrows与verifywidth。 | P10-T06 |
| A14 | Largecontext参数即长上下文测试通过 | CORRECTION | T09/T10 | 现有exactfixture截12000字符，retrievalfixture pos6000；新增真实128K/248K输入。 | P12-T02 |
| A15 | NInfer源码kNativeContext=1M意味着4090可服务1M | UNSUPPORTED_INFERENCE | N01 | 源码上限不等于已测容量；本轮仍冻结262144pool与输出余量。 | P7-T04 |


## 检索范围的可复算边界

`tqLLM: F=pos-recent; nc=floor(F/16); n=min(nc,4096); first=nc-n`。因此当pos=262144、recent=1536时，完整远端有16288个chunk，而原型只评分最后4096个。全局索引测试必须在第0页植入唯一相关片段，证明其进入候选域；不能只测Top-K对已经被截断的候选排序正确。[T06]

## 公平的比较分层

算法迁移只比较同一NInfer Target artifact、codec、模板和真实token输入。tqLLM作为外部产品比较时另列Target量化、模板、MTP/DFlash资产和显存布局，最多作为方向依据，不能用于证明本轮单因素改造的收益。[T01/T08]

LongSpec与SpecExtend原始出版页支持有界draft状态和跨模型检索的研究方向；本扩展的projected-feature archive、页摘要、异步staging是针对NInfer提出的设计，不冒充论文或tqLLM已实现的功能。Dustin仅列为后续稀疏验证研究，不作为完整Target语义的证明。[R01/R02/R03]
