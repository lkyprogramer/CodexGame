# NInfer Extreme v2 Implementation Plan

> 给执行AI：按任务DAG逐项执行；可使用已有的subagent-driven-development或executing-plans流程。没有这些插件也必须遵守同样的读合同→失败测试→最小实现→独立复核顺序。不要以工具缺失为由跳过验证。

**Goal:** 在不降低现网能力的前提下，验证并交付对真实4090/Java/Pi有可测收益的NInfer增量优化。

**Architecture:** 单一target验证与状态事务，Suffix链延长+现有MTP（v1零bridge）为首条路线，T07 W8路径门前置的DFlash2独立迁移（含会话持久化新功能），W16与d256 kernel按证据推进。主模型和生产服务保持冻结。

**Tech Stack:** C++20/CUDA13.2、SM89、现有NInfer、Mac Pi/JDK17、Python标准库工具。

**Spec:** `03-architecture-and-state.md` + 各分路线文档 + `22-machine-verified-facts-and-revisions.md`（事实基线，冲突时优先）。

## Global Constraints

候选受保护容量**200192**（用户2026-09-09决策；生产回滚点仍是262144，不改生产）；原artifact只读；Mac跑Pi；GPU串行；原23文件Java题保留；medium采样；完整state/q；no silent truncation；无密码进日志；生产切流人工批准；性能门≥8配对+A/A噪声底≤3%；rk8与DFlash2不同时占200192预算。

## 执行与并行

T00→T01→T02→T03是事实与测量地基（T00含显存账，T03输出rk8/DFlash2二选一）。T04/T05可并行CPU开发，然后T06完成Suffix链延长v1。**T07在T01后即可开跑**，它是DFlash2链的收益门：`Δ_w8`不过门则T08–T10降为可行性研究；过门后T08→T09→T10（T10含会话持久化新功能）。T12依赖T07+T06，不依赖DFlash2完成。T15可提前在控制端准备。T11只在T06进入v2时需要；T13需热点证据（先nsys测attention占比f）；T14默认关闭；T17/T18只在实际miss/head热点触发。

工期尺度（推断，`22 §4.8`）：T00–T03 1–2周；Suffix v1 2–4周；DFlash2链6–10周；W16 2–4周；d256 4–8周。串行约4–7个月一人；每阶段以产物验收界定完成，不是承诺。

T16不是“全任务都必须做完”节点，而是对**选定候选分支**完成验收。optional路线未做不算当前候选失败，但不能宣称它已实现。`configs/tasks.json`只记录计划，运行状态放独立`results/tasks-state.json`，不修改原计划来掩盖跳步。

子代理CPU工作可并行，修改共享sampling/runtime文件时由一个owner集成；所有GPU命令统一通过lease。独立reviewer必须读diff与证据，而不只读实现者总结。每个task完成commit，固定tag后才测；任何修复都会使受影响旧evidence过期。

## 任务目录

- [T00 冻结实际环境、源码、制品与构建输入](../tasks/T00.md) — deps: none; foundation
- [T01 Mac控制器、GPU lease与真实验证adapter](../tasks/T01.md) — deps: T00; foundation
- [T02 扩展每轮round计数（复用已有request/metrics账本）与20轨迹账本](../tasks/T02.md) — deps: T01; foundation
- [T03 有界控制实验：rk8与现成DFlash2机会测量](../tasks/T03.md) — deps: T02; foundation
- [T04 扩展现有精确采样器：ProposalBatch合同与Sparse16 q](../tasks/T04.md) — deps: T02; algorithm
- [T05 会话内有界SuffixIndex](../tasks/T05.md) — deps: T02; suffix
- [T06 Suffix链延长 + 现有MTP（v1零bridge；v2条件启动）](../tasks/T06.md) — deps: T04, T05; suffix
- [T07 W8合法验证路径、资源完整性与DFlash2收益前置门](../tasks/T07.md) — deps: T01; dflash
- [T08 DFlash2 companion转换与不可变artifact绑定](../tasks/T08.md) — deps: T00, T03; dflash
- [T09 DFlash2动态卷积、conditioning与selector算子](../tasks/T09.md) — deps: T04, T07, T08; dflash
- [T10 DFlash2状态事务、采样、Graph、恢复与会话持久化（新功能）](../tasks/T10.md) — deps: T09; dflash
- [T11 成本路由与窄/宽profile选择](../tasks/T11.md) — deps: T06; routing
- [T12 W16 packed4 decode优化](../tasks/T12.md) — deps: T07, T06; kernel
- [T13 d256 prefill Attention低风险与FP8研究](../tasks/T13.md) — deps: T02, T15; prefill
- [T14 A4 IMMA独立可行性尖峰](../tasks/T14.md) — deps: T13; high-risk
- [T15 复用Java/长上下文与真实轨迹资格集](../tasks/T15.md) — deps: T01, T02; quality
- [T16 最终配对、定向soak与发布证据](../tasks/T16.md) — deps: T03, T15; release
- [T17 按真实miss触发的近史anchors](../tasks/T17.md) — deps: T02; conditional-cache
- [T18 有证据时做draft-head Ada MMA小补丁](../tasks/T18.md) — deps: T02; conditional-kernel

## 自主推进边界

在明确授权的预算与维护窗口内，AI可依据decision.json启用研究分支并执行迭代，不必为每个小patch提问。触及生产切流、系统权限扩大、购买云算力、上传私有轨迹、超频、修改模型能力边界时必须停止并请求授权。无GPU/权限时先做CPU资产，不冒充完成。

## 任务实现公共附录

- [实际q、状态测试向量、d256 oracle与宽度审计合同](20-developer-contracts-and-test-vectors.md)
- [阶段退出点、显存分账与收益计算](21-experiment-priorities-and-memory-ledger.md)

执行T04/T07/T09/T10/T12/T13前必须阅读对应附录，不得只依据任务标题实现。
