# 00 · v2.0 总体改造计划：从独立优化转向完整请求的资源协同

**设计日期：2026-11-26，Asia/Shanghai。交付为设计与执行合同，目标机执行未开始。**

## 1. 本次重新决策

Atomic 仍是唯一主底座；正式 Inkling-2-Mini 固定 R=3 仍是产品主线；RTX 4090 24GB、64GB RAM 与一次一个活跃 GPU 生成请求仍是约束。改变的是组织方式：不再按项目依次移植，而是按一次 Agent 请求的关键路径、完整状态和资源竞争来选机制。

新版包含全部既有专题、来源与测试合同，并重写主入口、架构、预算、缓存及任务编排；原有 T/R/G/K 任务 ID 保留，新增 L00–L07 与 M00–M03。旧测试 ID 不重用。来源更新会明确撤销过时判断，不能把历史缺码状态延续成现在的事实。

本轮最重要的新结论：

1. LoomKV 的 Tier 与 Pool 应分别立项：Tier 保留原 GPU 表示，压缩 RAM/SSD；Pool 改变 GPU 缓存布局与 Attention。二者不能共用一个“无损所以正确”的验收结论。[论文 §III、VI、VIII-G](https://arxiv.org/html/2611.32954v1)
2. 先分析 Atomic 实际持有的 Q8_0/F16/BF16 数据和状态，不预设 BF16 的压缩率适用于所有 KV。压缩资格绑定 representation，而不是只绑定模型名称。
3. 完整会话恢复必须覆盖 KV、SWA 元数据、逐循环 conv、跨步存活的控制状态及选中投机路径的状态。KV 命中不能单独授权跳过整个前缀计算。
4. `2DSD/feat/inkling-dspark@962874f…` 已有公开 Inkling 参考/批量/静态 runner；撤销 v1.2 的“公开 runner 缺失”阻塞。研究版有对应 drafter，正式 Mini 在该分支 registry 中尚无默认匹配的 2DSD drafter；它也不是标准 vLLM Inkling 服务实现。[分支 registry](https://github.com/SqueezeAILab/2DSD/blob/962874f303c3142406ab3eecfae2bb51567815c9/configs/models.json)
5. 无损缓存、专家驻留、DSpark 与 Kernel 可以产生协同，也会争夺显存、PCIe、SM 和图池。采用完整组合的实验结果，禁止相乘论文倍率或重复分配同一份节省。

## 2. 三条可行路线的取舍

| 路线 | 优点 | 代价 | v2 决策 |
|---|---|---|---|
| 在 Atomic 内逐步增加状态、缓存和局部 SM89 provider | 可沿用 GGUF、模型执行、服务、CUDA 所有权；每步有回退 | 必须把原接口边界讲清，不能靠删除 guard | 主线 |
| 从第一天编写全新 Rust/CUDA 后端与统一调度器 | 架构自由度高 | 同时承担模型、数值、图、寿命、采样、服务和性能资格，难以归因 | K07 条件研究，初始 DEFERRED |
| 直接换用 Loom/vLLM/GAAC/Ghost 的完整运行时 | 可快速观察某些机制 | 不是用户选择的底座，模型格式、缓存和硬件前提不同 | 仅用作隔离参考与 oracle |

这不是先实现全部抽象再调优。第一版统一的是**资源账目、状态身份和能力证据**；并不强制重写 Atomic allocator 或引入独立缓存服务进程。

## 3. 共同架构

~~~mermaid
flowchart TD
  Q["请求队列与能力准入"] --> X["Atomic 执行与事务"]
  X --> W["权重与专家驻留"]
  X --> S["完整状态与缓存对象"]
  S --> T["RAM / SSD 精确存储"]
  S --> P["可选压缩 GPU Pool"]
  X --> K["局部 SM89 provider"]
  P --> K
  B["统一预算与事件寿命"] --> W
  B --> S
  B --> K
  E["测量与资格记录"] --> Q
~~~

Atomic 持有 CUDA context、stream、图、allocator、预算和请求状态。CacheManager 负责对象格式及事务；Codec 只负责有界字节变换；AttentionProvider 负责规定表示上的算术；BudgetPolicy 只在安全边界调配已核算资源；KernelLab 离线生成候选，生产只加载冻结产物。

## 4. 每个项目只承担能证明的职责

| 来源 | 纳入主线的精华 | 条件/研究部分 | 禁止推导 |
|---|---|---|---|
| Atomic | 模型/visit/slot、GGUF、预算 lease、原生 DSpark 接入基础 | Inkling 离散 CUDA budget 扩展 | Mac 可跑就等于 4090 可跑 |
| Inkling 正式模型 | 固定 R3、共享物理权重、独立逻辑状态 | 研究 checkpoint 与深度变化 | 重用权重等于少算两轮 |
| Ghost | 循环感知驻留、准确 runtime 格式、prefill 分组 | mapped-memory relay、通用快照迁移 | 通用服务能力等于 Inkling 专用预览能力 |
| squid5090 | 小批量热点、状态管理、减少 launch 的方法 | 重新设计 SM89 kernel | 搬来 Blackwell 指令即可受益 |
| 原生 DSpark | 同目标 token 投机与验证 | 动态 k、confidence/lookup | 草稿接受率等于请求收益 |
| 2DSD 新分支 | 明确的 loop plane、树节点状态、串行参考与静态图对照 | varloop 的二维投机、匹配 drafter 与采样验证 | 自动适用于正式 Mini 或压缩 Pool |
| PR51161 | last-loop 的容量思路；SWA static mask 回归案例 | 改变历史读取语义的研究目标 | 49% KV 减少等于 49% 速度提升 |
| LoopCD / ARLoop | 循环中间表示与 readout 的研究方法 | 改变目标的质量/计算权衡 | 与固定 R3 原目标无损等价 |
| LoomKV | 端到端缓存生命周期、直接分页恢复、可变记录与同步移出关键路径 | SM89 Pool 融合解码、实际压缩容量 | H800 goodput 倍率等于本机 decode 倍率 |
| GAAC / SplitZip / ZipFusion / ZipServ | 格式/查表/escape/融合/传输参考 | 以各自真实 dtype、硬件、许可证为门 | 各论文实现可互换或全部已有可用代码 |
| Magnitude | 一份物理账本、需求保留的预取、DMA/读者退休、route replay、CostEpoch、被动观测 | 对实际专家搬运与合法投机策略做有界自适应 | 有GGUF/递归状态就等于已有Inkling adapter；专家SSD就等于完整会话SSD |
| CUDA Rust / 证明文章 | 受限安全证明、失败关闭、候选绑定和反例 | Rust SIMT/Tile 前端与独立 backend | 证明了完整模型、数值或速度 |

逐项事实与固定 SHA 见 [22 融合矩阵](22_integration_matrix.md)、[33 无损缓存来源](33_lossless_source_audit.md)、[40 上游更新](40_upstream_refresh.md)、[41 Magnitude审计](41_magnitude_source_audit.md) 与 [42 融合任务](42_magnitude_integration.md)。

## 5. 重排后的实施阶段

| 阶段 | 交付 | 任务 | 放行依据 |
|---|---|---|---|
| A：可用且可比较 | 真实机器清单、正式 Mini 串行 oracle、质量/容量基线 | T00–T04 | G0/G1；容量诊断可失败，但必须真实 |
| B：可恢复且可计费 | 完整状态事务、StateInventory、逐 allocation 预算 | T05、L00/L01；M00共用合同 | G2；每个持久成员有处理方式 |
| C：先取得低风险收益 | 原生 DSpark；实测热点的 ggml-cuda 优化；缓存格式采样 | T06–T08、K00–K06、L02 | 每个选中能力独立正确性、质量和收益 |
| D：减少跨轮重复计算 | 闲置会话/前缀的精确 Tier 缓存、增量恢复 | T10、L03；按需 G05 | 相同表示恢复、状态完整、TTFT/容量净收益 |
| E：解除真实 GPU 瓶颈 | 条件专家驻留，或 SM89 压缩 Pool | T09/G01；L04/L05；按需M01 | 真实瓶颈；净容量、完整 Attention 与状态资格 |
| F：系统协同 | 缓存 × 驻留 × DSpark 的有界交互实验 | L06、M02；选中研究的 R05 | 同一完整 profile 的资源与 E2E 收益 |
| G：服务候选 | 长上下文、Pi 工具、恢复、soak 与回退演练 | T11/T12、L07；可选M03 | 原 G3–G6；生产切换另需 G7 |

阶段 C 内可并行读代码、写 CPU 参考，**同一张 GPU 的性能实验串行**。阶段 D 不要求先实现 Pool。阶段 E 不以“容量测试未通过”为前置通过条件，容量缺口是其输入。未选 L/M/K/G/R 特性不阻断普通 CUDA 主线。

## 6. 根据瓶颈选择下一项

- 质量未过：先处理资产、模板与正确性，不进入性能搜索。
- 大部分时间花在权重搬运：优先全驻留/专家 residency；只有 Pool 真正释放可分配 GPU 字节才讨论联动。
- 多轮 TTFT 被重复 prefill 主导且旧前缀可复用：优先完整状态快照 + Tier；同时保留 raw Tier 对照，区分“有缓存”与“压缩缓存”的增益。
- 长上下文 decode 被 KV 读取主导且表示可压缩：进入 Pool；必须比较本机最佳合法 raw Attention。
- launch/小矩阵/路由控制占主导：用局部 KernelProvider、图与分组，缓存压缩不预设有直接收益。
- 稳态已经全驻留、前缀命中充分且 SLO 满足：可以不启用压缩；NO_BENEFIT 是完成的研究结论。

## 7. 证明层级与发布口径

`字节往返一致 → 状态恢复一致 → Attention 数值合格 → 模型/采样合格 → 业务非劣 → 服务收益`，每一步都需要独立证据。形式证明只覆盖声明的程序性质，不替代这条链。

保留原门槛：单项请求中位数减少至少 5%，迁移真实任务中位数减少至少 10%，配对 95% CI 支持正收益；关键分层 p95 退化不超过 5%；150 Java 任务、300 工具案例的预注册非劣；至少 8 小时且 200 请求 soak。容量晋级可作为独立目标，但不能改称速度晋级。详见 [validation-policy.json](../manifests/validation-policy.json)。

## 8. 文档与命令的执行地位

包内 `tools/preflight.py`、`tools/paired_stats.py` 和 `tests/test_tools.py` 可立即运行。`tools/inkling-lab/lab.py`、CacheManager、SM89 Pool 与文中 NEW 路径是将来由对应任务实现的工程接口。没有这些实现时，实验状态保持 NOT_RUN/BLOCKED；不得复制伪命令生成 PASS。

每次工程代理开始任务，读取 README、AGENTS、本篇、任务所属专题及机器 DAG。以当前版本合同约束行动，保存原始证据；不修改生产、不安装新 GPU 工具链来“验证文档”。

## 9. v2.1 修订

阶段A增加mainline b12751跨引擎oracle与上游修复回移植；T04后写D-BASE底座复核记录（是否继续Atomic由用户决定）；128K容量以indexed bias（#33063）为关键路径；T07/K系列先验证上游CUDA融合（#33060）再自研；T06新增DFlash2扩展。4090现场事实、停服窗口W0–W4及命令见[43](43_upstream_llamacpp_4090_site.md)。任务ID、DAG、148项测试与全部门槛不变。
