# 22 · 全项目融合矩阵与采用决策

本矩阵按能力与瓶颈组织。所有“采用”均表示进入实施计划；是否启用取决于具体profile的证据。固定来源见[02](02_evidence_register.md)与[source-lock](../manifests/source-lock.json)，总体顺序见[00](00_integrated_master_plan.md)。

## 1. 来源 → 机制 → 任务 → 验证

| 来源 | 吸收机制 | 工程落点 | 需要观察的收益 | 限制 |
|---|---|---|---|---|
| Atomic Engine | GGUF、模型图、physical bank、expert lease、预算与服务 | T02/T05/T09/T11 | 正确运行、容量、可靠性、完整任务时间 | 固定CUDA budget guard尚不覆盖Inkling；不能直接复用Mac命令 |
| 正式Inkling / 原生DSpark | 固定R3、共享物理权重、独立逐visit状态、原生草稿特征 | T02/T03/T05/T06 | 同目标投机的请求收益 | 不减少正式模型loop；草稿资产与feature必须匹配 |
| squid5090 | arena、固定图、小批量/分组专家、lookup | T07/T08/K系列 | 真实热点和launch开销下降 | SM120a/Blackwell、TMA/PDL等不搬到SM89 |
| Ghost Infer | 循环感知驻留、runtime code/scale布局、prefill专家分组、闲置保留 | G00–G05 | H2D与stall、RAM代价、prefill/恢复 | 专用Inkling CLI不等于通用服务；G04 relay后置 |
| 2DSD | token×depth、node/plane、真实proposal、参考/批量/静态runner | R03/R05，UX01–03 | 相对最佳合法native DSpark的增量 | S44实验分支已有runner；正式Mini默认drafter仍缺，不是现成Atomic实现 |
| PR51161 | last-loop容量与只读历史视图、conv分离、static mask反例 | R01 | 实际allocated KV、容量与请求时间 | 改历史语义；dynamic速度原报告不变、static反而慢 |
| LoopCD / ARLoop | 同prefix早/末loop readout、guidance、小模型状态验证方法 | R02/R04/R05 | 质量与计算成本的可验证取舍 | 新target；不是正式R3原分布的免费加速 |
| LoomKV Tier / TileStream | exact-length存储、延后长度回读、直接scatter恢复 | L00–L03 | 完整前缀恢复TTFT、RAM/SSD容量、PCIe | 不释放活动GPU KV；本地typed subrecord格式须重新定义 |
| LoomKV Pool / FragPack | compressed-page管理、寄存器解码融合Attention | L04/L05 | 净GPU容量与完整请求速度 | H800 TMA实现不可照搬；E codec与N Attention分开资格 |
| GAAC | BF16 high-byte码本、escape、融合decode | L02/L04的一个参考 | 在真实数据上的ratio与成本 | BF16/head/scale/SWA/spec限制；side-pool静态风险先修合同 |
| SplitZip | BF16/FP8 codec、分流编码 | L02/L03对照 | 总record/allocated成本与恢复路径 | stateful码本、同步回读、FP8尾部、最坏扩张都要补齐 |
| ZipFusion | block局部编码与融合解码Attention | L04设计参考 | 本机新kernel相对最佳raw路径 | 官方代码未确认；论文decode计时不能充当端到端 |
| ZipServ | BF16权重CPU编码/GPU解码GEMM | T09/G02的条件研究 | 真正权重传输与GEMM成本 | 不是KV系统；不自动优于现有GGUF低比特权重 |
| CUDA Rust / proof文章 | scoped安全证明、候选hash绑定、失败关闭与反例 | K00–K06、UX04 | 可审查安全范围与合格kernel收益 | 不能证明整模型/浮点/FFI/编译链；K07完整后端后置 |
| Magnitude | 物理ledger、reserve-before-advance、DMA/读者退休、需求保留预取 | M00/M01与L01/G01共用 | 峰值可解释、减少真实demand stall | 不另建allocator；当前无Inkling family；SSD专家≠会话checkpoint |
| Magnitude | causal route replay、residency CostEpoch、证据与artifact分离、Pi观测 | M01–M03与T/K/L共用 | 预测空间、合法draft净收益、可定位的请求成本 | Bélády是未来上界；unknown≠0；观察器不提交token/tool |
| NInfer/Strata历史 | Agent续接、分层缓存、已知失败与回退经验 | T10–T12、L03/L07 | 同业务语料的完整任务比较 | 未审计本轮私有代码；旧参数/速度不是Atomic能力 |

## 2. 初始候选与条件开关

| 能力 | 初始状态 | 启用依据 |
|---|---|---|
| 正式Mini固定R3、per-loop | 产品主线待资格 | G1/G5与资产/模板固定 |
| Q8 KV | 首选待验证表示 | 真实backend支持；不支持则显式F16等profile，不静默换格式 |
| 全驻留CUDA | 首选 | T04峰值与余量；CPU/PCIe实际状态T00确定 |
| 原生DSpark固定宽度 | 关闭 | T05/T06状态与同目标资格、G3净收益 |
| 局部SM89 kernel / 图 | 按热点选择 | 原C++动态资格或可选Rust/Tile完整证据 |
| 闲置完整状态raw Tier | 关闭 | T10/G05完整续接，same-policy对照 |
| 无损Tier codec | 关闭 | L02/L03真实表示压缩、净资源和恢复收益 |
| GPU压缩Pool | 关闭 | L04/L05几何、数值、prefill、SWA、graph、spec全profile资格 |
| 专家tiering / 预测预取 | 关闭 | 真实容量或搬运瓶颈；T09/G01/M01选择性资格 |
| 动态draft成本控制 | 关闭 | 最佳固定策略先建立；M02有界、独立确认 |
| Pi额外进度 | 可选关闭 | M03协议/取消/背压不改变业务流 |
| last-loop / 2DSD / LoopCD / varloop | 研究关闭 | 独立target与R系列资格 |
| 独立Rust/Seismic/Magnitude后端 | DEFERRED | 新目标、adapter与关键路径证据另立项，不阻塞Atomic主线 |

## 3. 组合关系必须逐项证明

| 组合 | 分类 | 关键要求 |
|---|---|---|
| Tier + 原有raw GPU Attention | 同表示存储E | 完整StateInventory、zero-suffix next logits、请求私有状态隔离 |
| Pool + 原target | codec E + Attention N | 累加顺序、prefill临时区、raw tail、page overflow、接受率与质量 |
| Pool + 更多专家驻留 | 条件协同 | 实测净可分配字节；仅有专家搬运时有意义；同一节省不能再全给KV |
| Tier restore + 专家prefetch | 资源竞争 | 同PCIe/SM与staging预算；TransferTicket最后reader后释放 |
| Cache/驻留变化 + DSpark | 成本变化 | 新CostEpoch；重测plain、draft、verify、catch-up与回滚 |
| Graph + 压缩map/预算变化 | 寿命条件 | reader→update→replay，或独立generation表；旧图引用不能移动 |
| 2DSD + last-loop | 语义未证明 | B>1节点的own-loop历史与单步final-loop历史不同；lagged另设target |
| LoopCD + spec | 目标变化 | verifier使用guided p，actual q正确，coda和随机消费完整 |
| 低比特KV + lossless包装 | 表示绑定 | 无损的是原codes+scales字节；不外推BF16/FP8比例 |
| Pi观测 + 服务取消 | 协议条件 | EOF不当成功、未提交tool不执行、已发DMA不早回收 |

## 4. 瓶颈决定顺序，避免重建所有项目

先有正式模型串行oracle、可接受质量和完整状态。随后按trace选择：搬运主导做驻留，重复prefill主导做Tier，KV带宽或容量主导才做Pool，小矩阵/launch主导做kernel。Magnitude的统一账本和证据身份属于这些路径共用的基础；预测预取、动态draft和额外观测是可选能力，不必同时实现。

两因素只做已资格机制的00/10/01/11消融，按[37](37_unified_resource_policy.md)区分同工作负载与同硬预算。作者倍率、单kernel加速、压缩ratio与完整任务收益不能相乘。任何机制都允许NO_BENEFIT；不因新项目出现重新打开无新trace的旧DFlash2、CPU pool或launch overlap结论。

## 5. 推荐第一条交付线

Atomic固定fork + 质量合格GGUF + 正式R3 + 合法per-loop Q8表示 + 尽量全驻留CUDA + 已资格的原生DSpark固定宽度 + 少数profiler证实的SM89优化 + 可恢复完整状态 + 单GPU生成队列。

在此基础上，先验证raw Tier，再加入无损codec；专家预取和Pool分别按瓶颈进入。完整发布profile冻结所有target、格式、状态、图、kernel、预算、草稿与数据集身份。这里描述候选交付线，目标4090性能与质量仍为NOT_RUN。
