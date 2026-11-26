# 05 · 目标架构与不可破坏的不变量

## 1. 模块边界

~~~mermaid
flowchart TD
  A["请求与工具协议"] --> B["能力选择与队列"]
  B --> C["版本化会话状态"]
  C --> D["固定目标执行器"]
  C --> E["投机事务协调器"]
  E --> D
  D --> F["物理权重与专家驻留"]
  D --> G["逻辑KV与循环状态"]
  F --> H["SM89算子与CUDA图"]
  G --> H
  I["预算与lease账本"] --> F
  I --> G
  J["证据与性能记录"] --> B
  J --> E
  J --> H
~~~

Atomic现有模型解析、GGUF、ggml/CUDA、server和预算设施继续作为基础，不重写全套运行时。拟新增的能力选择、状态事务和测量接口首先隔离在模型相关代码与lab工具中，再决定哪些值得通用化。

## 2. 三种编号必须显式存在

| 编号 | 定义 | 可共享内容 |
|---|---|---|
| physical_layer_id | checkpoint中的实际参数层 | 权重tensor与只读packed expert |
| logical_cache_slot | 某次循环/层拥有的历史状态 | 默认不跨loop共享KV或conv |
| execution_visit_id | 本次forward的真实访问顺序 | DSpark特征索引、trace，不替代cache slot |

以6+12×3+6为例，必须产生48个visit并映射到24个physical layer；还要匹配Atomic现有slot重排，不自行假设slot等于visit。`src/models/inkling2-loop.cpp` 已区分这些概念，新增功能沿用其真实映射。[S01]

## 3. 循环执行语义

不能把Inkling简化成 `h = core(h)` 连续执行三次。当前实现保留prelude表示，每个后续pass由其重新建立当前输入，再通过上一pass bank以及query/down/gain/forget等控制产生消息，分别影响Q/K/V/FFN。coda执行一次。融合、早退、特征抽取都必须保留同样的边界和norm位置。

**不变量INV01：** 同一physical参数集合只按所需布局计费；重用权重不重用未定义可共享的运行状态。  
**INV02：** committed prefix中每个token的所有必要loop/conv/KV状态相互一致。  
**INV03：** 目标与草稿使用的feature visit列表通过资产指纹校验。  
**INV04：** 非法组合加载前失败，不在运行中悄悄切换算法。  
**INV05：** 任何显存地址被CUDA工作或graph引用时，不可释放或挪用。

## 4. 能力协商

拟新增 `CapabilityKey`：backend/device_arch、model_family/model_epoch、loop_mode、kv_mode/format、spec_mode、max_verified_context、max_verified_verify_width、batch/sequence上限、graph_mode、budget_mode、state_format_version。

`query_capability(key)` 返回 `SUPPORTED / UNSUPPORTED / UNQUALIFIED`、原因与通过的测试ID。`SUPPORTED`必须可追到能力行的证据。上游guard是现有能力声明的一部分，扩展时新增狭窄模型分支，不能全局删检查。

能力身份与实验可比性是两件事。AR与DSpark、不同verify宽度或graph模式的完整CapabilityKey应当不同。gate顶层key只对应被资格化的candidate；baseline/reference记录各自key。G3依据冻结的comparison contract核对目标、数据、采样、硬件、P/N等固定因素以及允许改动，不以完整key相等判断可比性，也不能为了比较删除key维度。

首版这是lab/profile层的逻辑接口，归属T01的 `tools/inkling-lab/capabilities.py` 与 `profiles/capabilities.json`，不要求立即新增通用C++ registry。T02负责核对真实backend/模型支持，T09负责核心代码中的预算硬guard扩展，T11启动器消费已审查的能力记录。profile验证绝不能覆盖或绕过引擎硬guard。

初始明确拒绝：正式Mini动态loop、原生草稿器搭配不匹配visit、2DSD资产冒充原生、未知KV codec、PDL/TMA硬件路径、未资格认证的预算+spec组合。

## 5. 投机状态事务

拟新增C++逻辑接口（名称为设计接口，不代表上游现存）：

~~~cpp
using TxnId = uint64_t;
struct PrefixCursor { uint64_t committed_tokens; uint64_t model_epoch; };
struct SpecCheckpoint;  // opaque; validates epoch and capability fingerprint
SpecCheckpoint begin_speculation(PrefixCursor prefix, uint32_t max_candidates);
void commit_verified_prefix(SpecCheckpoint&, uint32_t accepted_count);
void discard_uncommitted_suffix(SpecCheckpoint&);
void cancel_request_and_release(SpecCheckpoint&);
~~~

`accepted_count`是本轮已验证可提交的候选前缀数量；correction/bonus token由协调器在正确目标状态上推进，不能偷算进已验证候选数量。协议要明确定义KV是否包含最后emit token，以及下一forward从何位置开始。

checkpoint内容：所有global/SWA页映射、有效长度、conv状态、跨步存活的loop/controller状态、DSpark特征/Markov状态、positions、停止条件、采样器处理状态、RNG事件账本。纯forward scratch可重算，但必须证明重算足以还原语义。页写入采用copy-on-write或预留scratch；不能用“把n_tokens改小”替代回滚已经覆盖的滑窗conv。

## 6. RNG合同

greedy和随机采样单独资格。采样使用独立的proposal / acceptance / residual / target流，推荐counter-based RNG键为request、step、branch、role、draw_index。已经消费的接受/恢复随机数不因候选拒绝而重用；撤销候选模型状态与撤销随机事件不是同一操作。

同逻辑session/request的续接应序列化完整采样状态，并校验continuation binding和外部提交水位；跨请求model-prefix reuse只能共享获准模型状态，新建私有采样/协议状态。对相同完整执行序列可以要求重现；不同spec策略即便数学等分布，也不强制同seed逐token相同。统计检验不能替代算法证明，见07/13。

## 7. 权重lease与预算

resident bank、streaming tile和graph引用都持有lease。lease只在相关CUDA event完成之后释放；取消与异常也要drain或正确延期释放。requested/applied budget分开；减小预算不能evict active lease或半发布tensor。仅在已证明状态未被污染的准入失败/投机降级边界，才允许原位回到可用串行路径。

固定Atomic源码的expert executor错误是sticky，相关context会被视为不可继续使用。[S01] expert execution/CUDA错误后必须drain并退役旧context；若CUDA device context也失效，重启隔离worker。恢复只能在**同一有效预算与已资格profile**内新建context，从已commit前缀重建；不能原位续跑失效context，也不能悄悄移除预算重载普通CUDA。无法恢复时显式失败。工具副作用根据已记录call ID处理，重建不重做已完成工具。

Host和device有独立账本，pinned staging按host计费，device copy按device计费。图池属于显存预算；形状、地址、capacity或kernel版本变化要更新或失效图。

## 8. 前缀/会话缓存键

至少包含03统一的target_fingerprint（model_fingerprint仅是同义旧名）、draft_fingerprint（如存草稿状态）、KV codec、loop策略、LoopCD参数、template hash、token ids、位置策略、grammar/采样器状态和format版本。last-loop的固定prefill分区与块内语义也属于target身份。缓存必须对精确token前缀验证，不能仅靠文本hash/近似hash命中；CRC或校验和用于数据完整性。

权重、KV或策略改变时新epoch原子发布，旧请求继续持有旧epoch直到完成；不能让同一请求前半用旧图后半用新缓存。首版服务可使用排空后切换，避免过早实现热更新。

## 9. Ghost候选的身份与状态补充

[24迁移设计](24_ghost_transfer_design.md)和[25任务](25_ghost_tasks.md)沿用本篇不变量。完整capability key新增`residency_policy`、`runtime_layout_sha256`、`prefill_grouping`、`relay_mode`、`snapshot_policy`及各实现revision。字段必须对应实际执行路径；纯布局/调度可保持数学目标，但算术量化、归约、KV或guidance改变必须依03重建相应target_fingerprint。

A/B的capability key可以不同，G3比较合同冻结共同因素与允许差异。完整会话快照继承所有loop、KV/conv、controller、draft、RNG、grammar/stop及commit状态，不能以通用Ghost KV快照替代。relay采用epoch/ticket和提交前sticky错误检查；图地址稳定不免除资源拥有权、event/lease与退役责任。

## v1.2：局部kernel provider与身份扩展

新路径是[28](28_custom_backend_architecture.md)定义的局部provider，默认在原ggml-cuda分派、context、stream、budget、graph和事务内工作。kernel只产生受控输出，不自行提交token/tool或改变R3状态。独立backend为K07条件原型，非默认迁移。

已启用候选的完整capability key新增：provider/frontend revision、kernel source/template/参数、KernelContract/ABI hash、cubin/PTX与toolchain/driver/JIT身份、实际shape/dtype/alias范围、layout指纹、registry generation、proof policy/范围（若请求）、graph/arena地址generation。前端不改变数学目标时不必捏造新模型target；若算术/量化等改变目标定义，则按03/13更新对应身份与N/Q合同。能力key与target key不可混用。

未来原run的可扩展config通过`kernel_candidate`记录候选artifact路径/hash、provider、ABI/registry/shape/layout身份；原始execution/oracle/measurements只引用实际收集的build/proof/dynamic/timing记录。kernel-candidate-contract定义候选事实，不把字段塞进封闭engine/hardware/model。K01实现跨文件语义验证与一致性约束；仅合法JSON不授资格。

graph cache同时持有module与全部buffer leases。预提交NoMatch可走原合法实现；提交后故障要停止commit、drain/隔离并恢复committed前缀，不能在污染context上立即重跑baseline。请求取消与host对象释放不代表GPU已结束。原05的所有INV继续约束新路径。

## v2：模型执行、状态缓存、资源策略与局部后端统一

[00](00_integrated_master_plan.md)给出整体架构，[34](34_cache_state_contracts.md)定义EncodedRecord、完整Checkpoint与RuntimeLeaseSet三种合同，[35/36](35_tier_cache_design.md)分别定义Tier与Pool，[37](37_unified_resource_policy.md)定义预算与交互实验。Atomic继续拥有context/stream/allocator和提交；Codec不提交token，资源策略不改router/目标，provider不绕过能力guard。

缓存身份分为target、logical prefix、record representation、capability。纯无损包装不改变target；新Attention算术需N资格。首版完整快照仅同session续接，跨请求只共享获准模型状态并重建私有RNG/协议。新增typed subrecords目录、末token/next-logit协议、raw sealed到encoded发布的保留、有界overflow失败和metadata的reader→update→replay事件链。上述规则是原INV的具体化，不允许与原状态协议并行生成两个游标或两个资源账本。

## v2.0 · 资源调度的具体边界

在Atomic既有所有权内增加BudgetSnapshot、AdvanceReservation和TransferTicket，复用L01的ResourceLedger，不另建第二套账本。每次target/verify/recurrent advance前先为全部实际状态预留；失败不部分launch或commit。TransferTicket绑定source/destination generation、DMA完成和所有读者退休，取消已发出的工作不等于释放。RouteTraceRecord区分physical expert与loop/visit；CostEpoch使旧驻留条件下的投机成本失效；InferenceObservation只观测，不提交token或工具。来源、接口与M00–M03见[41](41_magnitude_source_audit.md)、[42](42_magnitude_integration.md)。
