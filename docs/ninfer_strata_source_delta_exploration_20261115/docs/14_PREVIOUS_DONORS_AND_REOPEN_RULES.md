# 与之前关注项目的合并去重

这是**机制级接续表**，不是对以下所有仓库最新版本的再次完整审计。当前重新固定源码的项目见source_lock；其他项目沿旧foundation/A1/A2和历史台账，只在出现真正差量时重新打开。

| 先前项目 / 主题 | 与本轮的关系 | 已有证据约束 | 本轮动作 |
|---|---|---|---|
| HyperQwen、lookup-augmented DFlash2、16-token verification | 同属proposal成本/宽verify/高复制负载效用 | NInfer H1/W6已测；W8/W16/H7已计划；64并发总吞吐不等于单流 | 仅D1的anchor/edit和真实skip差量进入前置门，不重跑一般lookup/宽度扫描 |
| TensorFold旧Python、当前native DFlash2 | 当前代码与旧0.6.6不同；head/state/dispatch可能影响净成本 | Strata DF2已通过但不采用；NInfer27B DF2旧计划/支持边界不可混 | 读取native1.2.9并拆机制；不新增泛DF2路线 |
| tqLLM、flare、samir-vllm、Nabo kernel-primer | kernel组织、profile、低层学习的参考 | A1已规定same-codec、数值oracle、SASS/资源与whole-task gate；NInfer已有INT8prefill、旧layout/prefetch关闭 | K-PAIR只做实际pair/P3绑定；不把“Tensor Core/融合”再当新建议 |
| Basalt、adaptive-tail、prefill→decode内存复用 | 与草稿/状态workspace生命周期有关，但不是本轮head或planner机制 | Strata P24少传字节无净益；旧A2强调last-consumer；P24不代表所有未来phase-aware策略都已否决 | 本轮无新可回收区间/热点专家证据，不追加缓存调参；若重提需独立真实lifetime和关键路径证据 |
| Hyperkernel、服务调度/cache-work、ring/lease | 本轮需要可靠完成/commit/下一请求证据 | A2已有指标来源、缓存重算量、owner和服务门；不能由常驻kernel宣传推导Graph尾隙收益 | 复用A2，不开发第二个平台/通信环或并发引擎 |
| RustingStrata、tokenspeed及其他Strata forks | 需实际patch→当前上游/用户分支差量 | 版本号/函数名不证明未有功能；旧SpecCost/HC/pool关闭 | 不自动再评所有fork，更不组合旧负结果；先commit/symbol映射 |
| Infernix及旧评估中的sm120a专用实现 | 硬件ISA边界与YASAKANI PDL同类 | 5090/GB10专用指令与4090兼容路径不能等同 | 保留硬件门；新版本若有sm89实现需重新固定源码，不据旧限定作永久结论 |
| DSpine / 新drafter或新量化模型 | 改proposal或权重资产可能改变接受率/质量合同 | 不等于本轮保持既有target/head的H2；不能借DF2曾PASS赋予资格 | 单独模型/adapter研究，不夹入此次单因素C |
| Edge0、project-maya | 不符合用户当前选择范围 | 用户明确不采用相关迁移路线 | 本包不安排部署/移植 |

## 不应漏掉的既有未完成窗口

NInfer export/publication解耦已经CPU实现，并有冻结但未执行的实机prep。它是已识别的服务路径问题，不应被新kernel项目遮蔽，也不能算本轮新路线。若用户后续优先解决真实queue/TTFT，先评估这个既有窗口是否值得另获授权，而不是再从零搭调度器。本包不自动执行或续用其额度。

## 未来重开最低证据

要从上表任一项再立候选，提交：旧路线ID与范围、donor固定commit/symbol、用户当前目标树中的缺口、当前关键路径/资源证据、保持或明确改变的模型/采样/容量合同、最小反证用例、独立预算。只提供作者速度或“新架构”名称不够。

若用户目标改为更换模型/量化而非优化现引擎，可以另开模型质量-速度-内存的三方评测；不能把那种探索结论写入本包的same-target净益栏。
