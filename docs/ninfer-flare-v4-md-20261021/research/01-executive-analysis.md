# 当前工程判断

优先目标是纯Chat推理性能。以已有P4可构建及最小功能证据开工，不等完整上游/全平台资格。先最小归因，挑一个热点或草稿收益假设，做一次定向验收；完整生产发布仍独立。

Flare可借鉴GDN correction、SM89小形状调优、按GPU生命周期复用workspace；现有NInfer已有紧凑记录、all-layer fold、gated norm融合和small-T路由，不能重复声称新增这些能力。更多记录store/空间可能抵消correction收益，必须比完整round。

W8/W16、DFlash2、检索和utility均有推理性能可能，应保留可选实验；接受率、宽度或理论并行不能替代包含draft/verify/搬运/资源成本的服务净收益。[实验机制](../plans/11-optional-performance-experiments.md)。

上游的缓存/编码/异步导出/small-T/midrise部分已在P1—P4吸收，不能把“剩余P5功能无直接收益”泛化为“上游没有价值”。余量U28—U34源码主要在决策/媒体/UI，完整合并保留条件对照但当前不优先。[上游评估](06-upstream-performance-assessment.md)。

Baseline的冷prefill与warm decode各有瓶颈，97fc7be6是context_capacity直接证据而非已证OOM；Gson缺selector日志、RE003夹具不一致，原成绩不改。当前所有性能百分比是条件目标，不是实测。
