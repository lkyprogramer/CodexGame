# 42 · Magnitude 机制融入 Atomic：M00–M03 执行合同

**设计日期：2026-11-26，Asia/Shanghai。当前四个任务与 MGX01–MGX16 全部 NOT_RUN。本文交付工程计划，没有实现服务代码、运行 GPU 或安装 Magnitude。**

## 1. 目标、来源与不变条件

在 Atomic 内完善资源、传输、决策证据和服务观测。正式 Inkling-2-Mini 固定 R=3；RTX 4090 24 GB、64 GB RAM；原支持范围内继续使用 Q8 KV；生产 Vision Off；同一物理 GPU 同时最多一个活跃生成或独占性能 worker。Atomic 保有 CUDA context、stream、allocator、graph、状态事务与采样所有权。

来源固定为 Magnitude `3aba40fda19fdaacc345c91c5e711a3bca2f9ee3`。阅读顺序为 [41 来源审计](41_magnitude_source_audit.md)、[34 状态与寿命](34_cache_state_contracts.md)、[35 Tier](35_tier_cache_design.md)、[36 Pool](36_compressed_pool_sm89.md)、[37 统一预算](37_unified_resource_policy.md)。精确源码及分支见 [magnitude-source-pins.json](../manifests/magnitude-source-pins.json)，带行范围的发现和原始测试提案见 [magnitude-source-audit.json](../manifests/magnitude-source-audit.json)。本篇将 MGX 提案收束到 Atomic 内的四个任务，具体执行范围以本篇和当前机器 DAG 为准。

不实现第二个 Magnitude/Seismic 后端，不构建其 Inkling runner，不改为 AffineK8V4/RotatedK4V4，不启用视觉模型，不复制其数值 α 门槛或产品速度宣称。Magnitude 的专家权重 SSD 分层与 L03 的完整会话 SSD checkpoint 分别登记；它们可以共用传输合同，但没有相互授予资格的关系。

## 2. 依赖如何生效

固定前置保证共享基础已经可用；条件前置只约束被选中的执行阶段。文档/CPU 合同可以先完成，缺少某个实际 provider 时，对应 GPU 能力保持 BLOCKED。不能把未实现的 bank、跳过的测试或全驻留豁免当作 streaming 已实现。

| 任务 | 固定依赖 | 选中后才需要的能力 | 必做 MGX | 条件 MGX |
|---|---|---|---|---|
| M00 来源、表示与共享账本 | T01 | 实际 state consumer 接入时消费 T05/L01 已登记成员；不全局依赖 L 任务 | 01、02、03、15、16 | 无 |
| M01 传输、staging、回放 | M00、T05 | 真实模型研究/性能结论需 T04；专家 tiering 需 T09；增强 G01 路径需 G01；Tier consumer 需 L03；完整 Pool consumer 需 L05 | 04、05、06、07 | 开启 prefetch 必须 08 |
| M02 CostEpoch 与资格绑定 | M00 | DSpark 决策需 T06；动态宽度/图选择需 T08；所选专家路径需 T09/G01；KernelLab 合同接入需 K01，候选运行需 K05 | 09、11 | 改变 spec control 必须 10 |
| M03 可选观测与组合资格 | M00、T11 | 所选 M01/M02 变化需要其证据；缓存交互需 L06，缓存服务候选需 L07；新 KernelLab provider 服务候选需 K06 | 14 | 开启观测必须 12、13 |

表中数字均指 MGX 编号。MGX07 的基础因果回放 CPU 测试必做；只有声称实际专家策略价值时才增加真实 R3 route 回放。MGX15 是固定源码的拒绝证据检查，不是构建 Magnitude 模型运行器的任务。

**不新增统一的 T12 → M00/M01/M02/M03 依赖。** T12 只消费最终 profile 实际启用功能的资格。未选功能保持 NOT_RUN/DEFERRED，关闭有据的无收益优化可记 NO_BENEFIT；不应为了使整个图变绿而运行不相关分支。同 profile、同 artifact 和完整覆盖的 T11/L07/K06 证据可被 M03 引用，避免无理由重跑。

## 3. M00 与 L01 只实现一份共享基础

共享组件 ID 固定为 `atomic.resource-ledger.v1`。其范围是物理 allocation 身份、同一版本预算快照、claim/reserve、已分配/退休中核算及 release 条件；L01 继续拥有完整 StateInventory、checkpoint 目录和状态发布事务。M00 不另建 `magnitude-ledger`、allocator、cache registry 或状态 owner。

首个被选中执行的 M00/L01 任务按以下协议实现，后执行者补充幂等增量：

1. 先读 `profiles/shared-core-delivery.json` 和实际 checkout。没有此记录时登记唯一实现路径、接口版本、负责该次变更的任务和预期文件 hash；两个代理不能同时修改同一组件。
2. 组件已存在时先核对实现 commit、ABI、schema、StateSizingProvider 合同与测试覆盖。完全匹配则消费原始证据；不得复制类、重复计费或用另一个对象模拟同一 allocation。
3. 缺少字段/行为时提交最小 delta，记录 `base_component_digest → result_component_digest`、新增字段、迁移方式和受影响消费者。第二次应用同一 delta 必须 no-op 或明确报告 already applied；不可重复注册 owner、charge、event callback。
4. 发生接口不兼容时提升组件 revision，并使受影响的 M/L/G/K profile 资格失效。不能“向后兼容”地忽略未知字段或绕过预算 guard。
5. 证据按组件 hash、测试 scope、allocator/平台合同绑定。只增加文档或消费别名不重跑未受影响的 GPU 实验；变更寿命/预算语义必须补相应回归。
6. 共享核心通过不等于 M00、L01 全部完成。L01 仍需完整状态、typed subrecord、恢复和 LX 测试；M00 仍需来源/表示边界及自己的 MGX 证据。

`StateSizingProvider` 是大小计算的唯一接入点：M00 的 CPU 参考可用明确标记的 synthetic shape；真实 Inkling 成员大小由 T05/L01 的真实 inventory 提供。没有实际 loop/conv/SWA/verify 成员覆盖时，不得给完整模型或缓存准入资格。结构化 JSON/Markdown 检查只能标 `evidence_kind=document_check`，不能替代未来实现的 MGX01–MGX03 语义测试。

### 3.1 共享数据与 API 合同

以下都是 **NEW/PLANNED 接口**，名称用于工程分工，不表示本包或上游已经提供这些函数。实现可采用 Atomic 现有类型；合并前须给出字段与调用点映射。

| 数据/API | 必填输入或字段 | 必须成立的结果 |
|---|---|---|
| BudgetSnapshot | physical_store_id、sample_id、monotonic_time、ledger_epoch、driver/topology 指纹、capacity/grant、reserved、allocated、retiring、unknown/untracked | 一次决定使用同一快照及 epoch；分立 VRAM/RAM 分账；未知值不是 0 |
| AllocationIdentity | physical_store_id、allocation_id、allocation_generation、medium；resource_id/view_generation映射range；arena_id/arena_generation独立 | 物理key只计一次；子view重用须新view_generation，不能用arena generation替代 |
| reserve(snapshot, demand) | demand_id、component bytes、alignment、临时峰值、required reserve | 返回 Reservation 或明确 Short/Stale/Overflow；失败不分配、不 launch、不发布 |
| extend(reservation, next_extent) | 旧 revision、下一步 rows/loop/verify 上界及 StateSizingProvider 输出 | checked 加乘；只在安全边界原子扩大；失败保留旧 reservation |
| retire(allocation, dependencies) | last reader/writer events、graph leases、generation | 提交释放不减去仍在途字节；确认最后使用完成后才归还可分配容量 |
| shared component receipt | component_id、schema/ABI、commit、file hashes、delta ID、tests、consumer bindings | 只读引用旧证据或实施一次可审查增量；不反向授予其他任务全部资格 |

准入计算使用容量的保守上界与真实同时存活峰值，不依赖平均压缩比、预计预取命中率或未来可能释放的地址。[37](37_unified_resource_policy.md) 的资源余量和“节省只能分配一次”继续适用。

## 4. M00 · 来源、表示与共享 ledger / reserve

**状态：NOT_RUN。类型：optional_mechanism_contract。固定依赖：T01。产出 G0/G2 的限定证据。**

### 4.1 进入条件与文件

T01 的 manifest、capability 查询、证据角色和退出码已实现；固定 Atomic checkout 和 Magnitude 来源；读取所选文件许可证；建立 shared component receipt。M00 的来源分析不运行 Magnitude。

| 操作 | 将来 Atomic 隔离 checkout 中的路径 | 职责 |
|---|---|---|
| NEW，已有则 MODIFY 同一组件 | `common/atomic-resource-ledger.h/.cpp` | 共享账本、snapshot、reserve 与退休核算 |
| NEW，已有则补缺失案例 | `tests/test-atomic-resource-ledger.cpp` | MGX01–MGX03 的实际 CPU 语义测试 |
| NEW | `tools/inkling-lab/magnitude_profiles.py` | 固定来源、表示、选中机制与拒绝原因校验 |
| NEW/MODIFY 单一 receipt | `profiles/shared-core-delivery.json` | M00/L01 实现与证据的幂等交接 |
| MODIFY，T01 计划创建 | `tools/inkling-lab/manifest.py`、`capabilities.py` | 接入机制开关、拒绝状态和 scope；不放松原门槛 |

### 4.2 执行步骤

1. 把 sources、blob SHA、许可证、所选机制与目标能力写入运行 manifest；固定 `formal R=3`、GPU active=1、VisionOff 和 K/V 各自 representation。来源变化不自动升级代码。
2. 完成 MGX15：核对 pinned family registry 和未知 architecture 拒绝路径，记录“无已验证正式 Mini adapter”。该证据仅用于禁止替代后端假设，不下载、转换或运行模型。
3. 完成 MGX16 的表示边界实现：Q8_0 codes/scales、BF16、FP8、自有 affine/rotated 使用不同 identity；相同 shape 不能绕过拒绝。无损包装保存已初始化的原始字节；增加量化路线不属于 M00。
4. 在共享核心实现前写 MGX01–MGX03 反例：alias 双记、claim 尚未 allocation、release 尚未 completion、过期 OS sample、generation 冲突、差 1 byte 的扩展、乘加溢出、reserved row 外写入。
5. 实现单一 ledger/sizing 接口，分别保留 held、allocated、retiring 量；将自身 allocation journal 与快照版本关联。CPU 参考检查资源守恒，模拟器记录明确的 evidence kind。
6. 对照 L01 已有交付，只补缺失合同和案例；验证同 delta 再应用不新增条目/回调/charge。
7. 注册原始日志、实际 case 数、拒绝原因和 receipt。空测试、缺实现或只有文档检查不能给语义测试 PASS。

### 4.3 退出与证据

必做 MGX01、02、03、15、16。退出交付为来源/表示支持矩阵、可执行共享核心 CPU 测试、receipt 及不支持列表。MGX15 可以使用静态源码检查；MGX01–03 必须运行未来实现，不能把此次 JSON 自检改名为语义验证。

没有实际 allocator/state consumer 映射时，允许交付 source/CPU component scope，但 GPU/完整状态能力仍 BLOCKED；不能宣布完整 L01 通过。这个基础任务不要求先证明速度提升，任何账目不守恒、越界或未知状态被接受都属于 FAIL。

参考：MGF03–MGF07、MGF16，详见 [41](41_magnitude_source_audit.md) 和 [来源发现](../manifests/magnitude-source-audit.json)。

## 5. M01 · 传输寿命、需求 staging、离线回放与条件预取

**状态：NOT_RUN。类型：conditional_resource_optimization。固定依赖：M00、T05。基础必做 MGX04–MGX07。**

### 5.1 进入条件、路径与接口

T05 的已接受/未提交状态、取消和恢复边界明确；M00 的 reservation 与 generation 可用。基础 DMA 资格可使用 Atomic 自己的 allocator/stream 上的有界 fixture，不需要先启用专家分层或缓存。实际专家增强只有在 T04 表明真实搬运瓶颈、T09/G01 提供对应实现后进入；实际 Tier/Pool consumer 分别消费 L03/L05 证据。

| 操作 | 计划路径 | 条件 |
|---|---|---|
| NEW | `common/atomic-transfer-ticket.h/.cpp`、`tests/test-atomic-transfer-ticket.cpp` | 复用共享核心和 Atomic 的事件拥有权 |
| NEW | `tools/inkling-lab/expert_route_replay.py`、`tests/inkling_lab/test_expert_route_replay.py` | 纯 CPU 因果回放，不启动另一个模型 |
| NEW | `profiles/expert-transfer-policy.json` | 明确需求保留、队列/bytes 上限、优先级及 prefetch 默认关闭 |
| MODIFY，G01 计划创建 | `src/llama-inkling-residency.h/.cpp` | 仅增强实际选中的专家策略 |
| MODIFY，T09 计划创建 | `src/llama-inkling-cuda-banks.h` | 仅选中分立 CUDA bank；缺失不当已实现 |
| MODIFY，L03 计划创建 | `common/atomic-cache-tier.cpp` | 仅选中完整 checkpoint Tier 传输 |

TransferTicket 至少包含 `ticket_id, request_id, operation_kind, source/destination physical key + resource_id/view_generation + arena_generation, byte_span, queue_state, issued_event, completed_event, readers, graph_leases, cancellation_requested, quarantine_reason`。操作接口为 `enqueue_reserved_transfer`、`attach_reader`、`cancel_unissued`、`observe_completion`、`retire_reader`、`can_reuse`；每次操作均验证 generation。不同消费者共享 ticket 合同，不共享未经声明的逻辑状态。

Queued 可在未发出且无消费者时撤销；Issued 后取消只停止后续工作，继续持有资源到真实 completion。Completed 仍可能有读者；只有最后读者、graph lease、元数据读者结束才可 Retired。Faulted 进入隔离路径，不能用 error/timeout/句柄 drop 冒充 completion。metadata 更新沿用 [34](34_cache_state_contracts.md) 的 `last_reader → update_complete → next_replay_wait`。

### 5.2 执行步骤

1. 写 MGX04–06 失败案例，再实现最薄 Atomic ticket 接入。注入延迟 DMA、两读者、取消、event 乱序/迟到、stale generation、设备错误和重复释放。CPU 状态机通过后，运行 Atomic-owned CUDA fixture；无 GPU 时该动态范围 BLOCKED。
2. 先固定 demand floor，再允许 hint 取剩余记录。上限同时覆盖 device staging、pinned、队列条目、bytes、句柄与 in-flight；不同 pool 的索引上限不得混用。上限不足返回背压或拒绝，不临时无界扩容。
3. 把优先级表写进 policy 并测试：当前关键路径的数据及为其释放容量的必要依赖优先；当前请求恢复次之；后台 store/promotion 与预测工作按明确规则排队。沿用 [35](35_tier_cache_design.md) 的干扰与背压原则。不得照抄存在注释/实现差异的上游顺序。
4. 完成 MGX07 基础 CPU 回放：固定记录顺序、重复/越界拒绝、LRU/frequency/候选因果策略与 NextRead/Bélády 未来知情的 miss 对照。上游 replay 返回 misses 和 held experts，不返回 stall、可隐藏延迟或预取速度上界。只允许 oracle 读取未来；未来信息不得进入候选。
5. 实际专家路线选中时从 Atomic R3 采集 trace：`request, token, logical_loop, logical_visit, physical_expert, target_or_draft, prediction_time, actual_route_time, tier, bytes, wait, state_epoch`。物理权重只计一次，逻辑访问分别记录；采集不得用未来 token 反填预测。
6. 分开判断替换策略与预取。相同容量/约束下与 NextRead 的 miss 差距很小，可以停止改进 eviction/residency ranking；它不能单独停止预取，因为 compulsory miss 仍可能提前搬运。预取立项/停止必须同时检查真实 demand stall、预测在需求之前可得的 causal lead time、实测 DMA 与 compute 重叠、有效带宽及排队干扰。全驻留且无真实 demand stall、缺乏因果提前量或不存在可用重叠窗口时，才按对应证据停止该预取假设；不能把 miss 数换算成虚构时间。
7. 有明确瓶颈才开启一个预注册的预取策略，保持 weights/KV/loop/输出/graph 和总预算不变，进行 MGX08。覆盖 all-resident、可预测、随机 route，区分 compulsory/eviction miss、真实 SSD 冷读与 OS page cache 热读，记录每次预测提前量、传输与计算时间线、未使用预取和前台干扰，以完整 E2E 结果决定是否保留。
8. 和 Cache Tier 共用资源时仍分别报告对象类别与流量；仅对选中的交互进入 L06，不要求启用 Pool 或全部 G 路线。

### 5.3 退出、停止与证据

基础交付需要 MGX04–07；MGX07 CPU fixture 不能授予实际模型路由或性能结论。启用 prefetch 必须额外完成 MGX08、相同 profile 的 G2/G4 及所宣称的 G3 收益证据。记录 raw timings、H2D/D2H/SSD bytes、miss stall、pinned/device peak、队列高水位、unused prefetch、故障与回退。

错误释放、越界、坏状态发布或模型不可解释差异立即 FAIL；缺对应 bank/Tier/Pool provider 为 BLOCKED。正确但无端到端收益可 NO_BENEFIT 并保持 prefetch=false；最多两轮有 profiler 证据的修正，不因 miss rate 改善而扩大范围。

参考：MGF08–MGF12；[34](34_cache_state_contracts.md)、[35](35_tier_cache_design.md)、[37](37_unified_resource_policy.md)。

## 6. M02 · CostEpoch、投机成本与 kernel 证据

**状态：NOT_RUN。类型：conditional_policy_optimization。固定依赖：M00。基础必做 MGX09、MGX11。**

### 6.1 进入条件、文件与数据合同

基础部分只实现 CPU 可测的 epoch/资格绑定；不要求先实现新的 KernelLab provider。实际 DSpark 决策需 T06 已资格固定宽度，动态宽度/图切换另需 T08。观察 tiering 的实际影响时消费 T09/G01 对应能力。选中 KernelLab 时复用 K01 合同和 K05 动态资格，不能重新建立另一套 registry。

| 操作 | 计划路径 | 用途 |
|---|---|---|
| NEW | `common/atomic-cost-epoch.h/.cpp`、`tests/test-atomic-cost-epoch.cpp` | 有界成本表、失效原因、safe-boundary 切换 |
| NEW | `profiles/cost-epochs.json` | 表容量、context classes、过期条件、已资格宽度、离线策略 |
| NEW | `tests/inkling_lab/test_artifact_evidence_binding.py` | 来源/产物/资格错配的语义负例 |
| MODIFY | `common/speculative.cpp` | 仅接入选中的 T06/T08 控制点，不改 acceptance/sampling 数学 |
| MODIFY，T01 计划创建 | `tools/inkling-lab/capabilities.py` | 记录角色、未知测量及完整 capability key |
| MODIFY，K01 计划创建 | `tools/inkling-lab/kernel_contracts.py` | 仅当 KernelLab 被选中；复用而非复制合同 |

CostEpochKey 包含 `target/draft fingerprints, source representation, R/visit layout, residency policy+generation, tier/pool mode, budget envelope, graph/arena generation, context class, sequence count, verify shape, provider/artifact, device/toolchain`。改变任一影响成本或数值的项，产生新 epoch；保留历史仅供审计，不作为当前 measured cost。

CostObservation 区分 `measured / prior / unknown`；保存 sample scope、原始 wall time、draft/verify/entry/switch/restore/stall、committed tokens、acceptance prefix 与采集时的 epoch。unknown 用缺失值和原因表达，不用 0。表数量/容量必须预先有界；不能因长上下文增长无限保留 bucket。

ArtifactIdentity 绑定源码、编译参数、ABI、dtype/layout、SM89、工具链和二进制 hash。QualificationBinding 另外绑定模型、数据/holdout、scope、预算、oracle、原始证据及结论。命中 compilation cache 只说明有匹配 artifact，不能合成 PASS、复用不匹配 timing 或授予额外搜索预算。

### 6.2 执行步骤

1. 写 MGX09：改变 KV 表示、驻留比例、graph generation、context class、verify width，确认旧成本失效；过期 plain 参考不能永久锁死决策；未测 shape 不得被当免费。
2. 写 MGX11：同名不同二进制、改 driver/toolchain、改 target/draft、缺 artifact、覆盖不完整、旧结果伪装当前 epoch。拒绝应发生在候选被选入执行之前。
3. 把观测接入已经资格的 plain/固定宽度路径，先记录完整成本，不改变决策。将真实采样和 synthetic fixtures 分开；包含 prefill、feature catch-up、切换、拒绝和资源迁移开销。
4. 用冻结 trace 离线比较 plain 与已资格宽度。不得将 Magnitude 的 acceptance prior 常数当本机测量，也不能把 verify 理想成本直接设为一次 plain decode。
5. 确有收益假设时，按 T06/T08 的现有控制边界实施一个候选，执行 MGX10。在线探测初始关闭；若后续选择，需要独立声明时间/轮数/内存上限、plain 刷新规则和退出条件，不能由 source 代码存在而默认打开。
6. KernelLab 被选中时把已有候选与 K01/K05 证据映射到同一 Binding；原生 Atomic C++ 路径也可以使用合同，不强制引入 Rust、Seismic、编译器或新 CUDA context。
7. 只在无未决 proposal 的安全边界切换策略/epoch；保持 T05 的完整状态与 RNG 账本。模型质量或状态条件不满足时不能靠“更保守宽度”继续污染的 context。

### 6.3 退出、停止与证据

基础合同交付需要 MGX09、MGX11。启用改变后的 spec control 必须追加 MGX10，以及 T06/T08、原 G2/G3/G5 的相应资格。输出 `epoch-transition.jsonl`、每种测量角色、过期/拒绝原因、artifact/qualification 关联与配对 E2E 原始记录。

只有 kernel 变快、接受率变高或成本模型拟合更好，不能宣布请求收益。控制器正确但不优于最佳已资格固定宽度，可 NO_BENEFIT，生产保留原策略。保留 [13](13_correctness_quality.md)、[14](14_benchmarks.md) 的全部质量和统计门；上游数值验收开放问题不构成降低本包门槛的理由。

参考：MGF13–MGF16；[37 预算协同](37_unified_resource_policy.md)、[31 Kernel 任务](31_kernel_tasks.md)。

## 7. M03 · 可选 Pi / Java8 观测与选中组合资格

**状态：NOT_RUN。类型：optional_service_qualification。固定依赖：M00、T11。基础必做 MGX14；观测开启时必做 MGX12、MGX13。**

### 7.1 进入条件与计划文件

T11 已有请求身份、有界队列、工具解析、取消和终态权威来源。M03 不接管工具执行或 CUDA；只对最终 profile 选中的 M01/M02/L/K 功能聚合资格。未选缓存或 KernelLab 时，不等待 L06/L07/K06。

| 操作 | 计划路径 | 条件 |
|---|---|---|
| NEW | `common/atomic-inference-observation.h/.cpp` | 可选事件与快照，不持有生成提交权 |
| MODIFY | `tools/server/server-context.cpp` | 仅显式 opt-in 的观测输出；默认 token/tool 协议保持 |
| NEW | `tests/inkling_lab/test_atomic_observations.py` | SSE、重试、取消、慢消费者及副作用隔离 |
| NEW | `integrations/pi/atomic-observation.ts` | Pi 观测被选中且现场版本验证后；不安装 Magnitude 扩展 |
| NEW | `integrations/java8/AtomicSseObservation.java` | Java8 客户端被选中；不要求 Bun/Effect |
| NEW | `profiles/magnitude-mechanisms-release.json` | 实际选中机制、精确资格与禁用回退 |
| MODIFY，T01 计划创建 | `tools/inkling-lab/qualification.py` | 按条件检查必需证据，不产生全局 M 依赖 |

客户端若已有归属明确的 adapter，应修改该适配点并在任务 receipt 登记实际路径，不创建第二套并行 provider。表中 NEW 是计划的默认文件位置，不表示当前仓库存在客户端项目。

### 7.2 观测合同

InferenceObservation 包含 `schema_version, request_id, attempt_id, event_seq, phase, monotonic_time, model/profile fingerprint, prompt/cached/processed tokens, generated/committed tokens, optional timings, terminal_observation`。phase 只报告实际发生的阶段；未知时间或不可得指标保留缺失原因，不补零。只有 T11 的权威 request terminal 能决定成功、工具提交和正式 usage。

首版优先 `trace_only` JSONL；如选 `sse_extension_v1`，必须显式协商版本及 opt-in，在 MGX12 验证客户端容忍额外事件。此处字段/协议名称均为提案，不是 Atomic 现有 CLI 或服务 API。默认客户端不被迫安装扩展。

观测可以失败或被丢弃，不能破坏原 token/tool body；observer 自身的队列、buffer 和生命周期有界。EOF、[DONE] 缺失、timings 已到、HTTP 断开均不能单独推成成功。重试按 request+attempt 去重，只累计权威接受的 attempt；不自动重试有外部副作用的工具。图和传输资源仍按 M00/M01 的完成条件释放。

### 7.3 执行步骤

1. 验证 MGX14：T01 的独占实验 lease 与 T11 的 service active=1 分别有证据。第二个生成、调优或对照 worker 必须排队/拒绝；CPU 文档/解析工作可并行。parent 等待 child 时不得持有 GPU slot 形成死锁。
2. 观测开关默认为 false。选择 Pi/Java8 时先实现 MGX12 fixtures：UTF-8 拆包、CRLF、多个 data 行、未知字段、坏 progress JSON、非 2xx、无终结帧。观察支路不得改变正式 token/tool/usage 字节或解析结果。
3. 实现 MGX13：abort、timeout、observer 卡住、慢消费者、重复/乱序事件、重试以及设备工作晚完成。服务应结束可观察状态，但不能提前释放 in-flight 地址或重复提交工具。
4. 比较观测开/关的请求时延、CPU、buffer 与日志开销；开销不从计时中扣除。敏感提示词不因观测而整段记录。只报告真实可观察指标。
5. 冻结最终组合。若包含 M01/M02 变化，先检查对应任务及条件测试；缓存组合进入 L06，缓存服务使用 L07，新 provider 使用 K06。原始证据完整且 fingerprint 相同可复用，缺覆盖只补受影响 scope。
6. 完成原 G2–G6 的所选能力确认、150 Java 任务/300 工具案例、原长上下文矩阵和至少 8 小时且 200 请求 soak。副作用使用 fixture/replay 隔离；单卡对照按计划顺序运行。
7. 输出 T12 可审查候选、功能禁用方式、失败隔离和回退演练；不自动进入 G7，不切生产流量。

### 7.4 退出与停止

性能优化仍要求单项请求中位数至少改善 5%、迁移真实任务至少改善 10%、配对 95% CI 支持正收益，关键分层 p95 退化不超过 5%。基础正确性和观测功能本身不伪装为速度晋级；其成本单列，最终候选仍满足原质量、容量与服务要求。

观测扩展不兼容或开销过高，可停用并保留 trace-only/既有协议，记录 DEFERRED 或 NO_BENEFIT；实际 token/tool 错乱、重复副作用、跨 epoch 状态或 premature free 为 FAIL。没有该选中组合的硬件/模型证据为 BLOCKED。M03 完成不代表所有未选 M/L/G/K 能力通过。

参考：MGF17–MGF20；[20 服务验收](20_acceptance.md)、[34 状态寿命](34_cache_state_contracts.md)、[37 完整组合](37_unified_resource_policy.md)。

## 8. MGX01–MGX16 的唯一主要归属

其他任务可以引用同一测试证据，不复制测试 ID、不把 source test 的存在算成已执行，也不把 CPU 模拟或文档校验换名为 GPU PASS。所有行初始 NOT_RUN。

| ID | 主要任务 | 最小实际证据 / 场景 | 条件与通过边界 |
|---|---|---|---|
| MGX01 | M00 | 实现后的 CPU ledger：alias、pool 转移、claim、retiring | 物理块单计费；需语义测试，非 JSON 检查 |
| MGX02 | M00 | OS sample / allocation journal 交错、stale epoch、分立两域 | 决策读同一版本，自己变化不成为 others |
| MGX03 | M00 | reserve/extend 差 1 byte、整数溢出、越界 rows | 失败不提交；CPU sizing fixture 不授真实模型容量 |
| MGX04 | M01 | 延迟 DMA、两个读者、取消、晚 event、fault | GPU 寿命声明需要 Atomic-owned 实际 CUDA fixture |
| MGX05 | M01 | 空 staging、跨 pool 索引、hint 占满后 demand | 需求保留、索引和所有队列/bytes 上限成立 |
| MGX06 | M01 | 显式排序、reprice、queued/issuing/in-flight 取消 | 实现与 policy 一致；无需求饥饿或提前回收 |
| MGX07 | M01 | 因果回放 CPU fixtures；选中专家路线再加真实 R3 trace | NextRead 只给 miss/held 对照；不推出 stall 或预取速度上界 |
| MGX08 | M01 | demand-only / prefetch 配对；实际 stall、因果提前量、DMA/compute 时间线、SSD 冷热 | prefetch.enabled 时必做；小 Bélády gap 不能单独否定预取，最终按 E2E 与原 G3 |
| MGX09 | M02 | residency/context/graph/representation/verify 变化与成本过期 | 旧 epoch 不适用；unknown 非 0；安全边界切换 |
| MGX10 | M02 | plain / 最佳固定宽度 / 候选控制的完整请求配对 | spec_control.enabled 时必做，沿原 5%/10% 与质量门 |
| MGX11 | M02 | artifact、来源、ABI、scope、预算与资格记录错配 | compilation hit 不授模型/GPU/性能资格 |
| MGX12 | M03 | Pi/Java8 SSE 分片、坏观测、终态缺失、未知字段 | observability.enabled 时必做；原生成协议不被改写 |
| MGX13 | M03 | abort、慢消费者、重试、observer 卡住、晚 DMA | observability.enabled 时必做；无提前释放/重复副作用 |
| MGX14 | M03 | T01 GPU 实验 lease 与 T11 活跃请求准入 | 必做；单物理 GPU active=1，不能只测服务计数器 |
| MGX15 | M00 | 固定源码 registry/recognize 的静态拒绝证据及 pin | **只做 STATIC_SOURCE_CHECK**；不建设 Magnitude runner |
| MGX16 | M00 | 表示 identity / byte-preservation / 不兼容拒绝的 CPU fixtures | 不引入新 KV 量化；新表示的模型资格另立任务 |

无测试适用范围时必须记录 selected=false 或明确 skip reason，不生成空集合 PASS。任务交付状态与 capability gate 分离：例如 M00 CPU 组件可以交付，但未测实际 allocator 的 GPU 范围保持 BLOCKED；M01 的预取可 NO_BENEFIT，而公共寿命测试仍须有结果。

## 9. 未来 runner 与证据目录

继续使用 **T01 将来创建的** `tools/inkling-lab/lab.py` 的 validate/run/qualify/compare，不新增 Magnitude 服务 runner。M00–M03 向同一 runner 注册 case 与 profile；实际 C++、Java8/Pi 测试目标及 argv 由相应任务实现后写入 manifest。本文不提供假装现在可运行的 Magnitude/Atomic 安装或服务命令。

计划命令形状如下，全部标记 **PLANNED_AFTER_T01_AND_SELECTED_TASK_IMPLEMENTATION**；相关文件或 suite 不存在时必须退出 2，输入不合法退出 3，执行失败退出 1。文档包检查不能替代这些调用。

~~~text
python3 tools/inkling-lab/lab.py validate --manifest runs/M00-cpu.json
python3 tools/inkling-lab/lab.py run --manifest runs/M01-transfer.json --out evidence/M01
python3 tools/inkling-lab/lab.py qualify --suite G2 --manifest runs/M02-selected.json --out evidence/M02
python3 tools/inkling-lab/lab.py compare --baseline evidence/base --candidate evidence/candidate --out evidence/paired
~~~

每个任务至少保存运行 manifest、source/component/representation/capability fingerprints、实际命令、原始 stdout/stderr、case 数与执行/跳过理由、artifact hash、失败案例、结论和受影响能力。M01 增加传输及 route JSONL；M02 增加 epoch transition 与 artifact/evidence 关联；M03 增加 request/attempt/terminal 和完整组合引用。存在 private prompt/tool 数据时按既有工程权限处理，不为分享证据额外上传。

当前仅为实施输入：后续工程代理先检查实际授权、共享组件 receipt 与选中能力，再执行对应阶段。不能因为本篇定义了路径和函数就声称代码已经存在，也不能借此启用第二后端、改变正式 R3、重新量化 KV 或扩大 GPU 并发。


## 10. 规范profile入口与后续审查约束

执行run只通过`config.mechanism_profile_ref`引用完整机制profile及SHA256；初始形状见[mechanism-profile-example](../manifests/mechanism-profile-example.json)。`profile.prefetch.enabled`、`profile.spec_control.enabled`、`profile.observability.enabled`是条件测试的唯一开关路径，来自被引用文件，不从任务标题或自然语言猜测。T01/M00语义验证器必须解析引用、核对执行capability及已选policy和硬上限；null不是无限预算，false不表示已经验证关闭/回退行为。

M00/L01共享物理key与view/arena映射以[34§9](34_cache_state_contracts.md)为规范。物理allocation generation、子view generation与arena generation独立；同arena内复用不能让旧ticket退休新对象。完整会话与缓存transfer还需continuation_binding/权威提交水位，机制profile不能授权跨请求克隆私有状态。

MGX07回放输出只含miss/held；即使未来oracle与因果策略的miss数接近，也不能据此断言预取没有速度空间。替换命中改善和提前搬运分别做决定，MGX08由真实关键路径与完整E2E证据裁决。
