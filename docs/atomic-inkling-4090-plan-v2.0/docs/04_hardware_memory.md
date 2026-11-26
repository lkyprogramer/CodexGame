# 04 · 4090资源预算与容量决策

## 1. 首先消除不必要的分层

26.4B参数模型经GGUF量化后有机会在24GB中同时容纳权重、KV和草稿器；是否做到取决于实际tensor布局与上下文，而不是模型参数量一个数字。优先测全驻留路径，避免把原本可留在GPU的数据变成PCIe Gen3流量。Atomic循环优先驻留的主要价值在预算不足时；全部物理权重已经驻留时，它不会再凭空省下三遍计算或三倍显存带宽。[S01/S02]

## 2. 统一预算口径

所有记录使用bytes，展示用GiB（2^30）；厂商GB单独注明。`nvidia-smi`总显存是实际起点，不把“24GB”当精确可分配bytes。

GPU峰值合同：

`resident_weights + expert_cache + target_KV + conv_and_loop_state + draft_weights + draft_KV + verify_or_tree_scratch + graph_pools + staging_device + allocator_padding + runtime_untracked <= measured_total - reserve`

Host峰值合同：

`anonymous_model_copies + pageable_expert_cache + pinned_staging + host_state_cache + process_scratch + runtime + measured_OS_working_set + OS_file_cache_residency <= physical_RAM`

同一物理allocation只计一次。文件mmap、页缓存、匿名副本和pinned副本必须区分；不能把它们既相加后又宣称是不同预算内的同一数据。Atomic ledger不覆盖所有driver池和OS缓存，因此同时采集ledger、NVML与RSS/PSS。[S01]

初始策略值：GPU额外保留 `max(1.5 GiB, 实测外部峰值+0.5 GiB)`；host至少为OS与代理保留8GiB，进一步按实际业务峰值提高。它们是起始安全余量，不是已证实的最优值。不以持续swap满足预算。

## 3. KV按逻辑访问计算

正式Mini为24物理层/48逻辑访问；per-loop KV和conv分别持有。相同权重指针不意味着KV可共用。模型有global与sliding-window两类attention，不能把48个访问都按全上下文估算，也不能误按24层估算。[S01/S02]

对每个逻辑访问j：

`KV_j = allocated_positions_j × (encoded_K_row_bytes_j + encoded_V_row_bytes_j)`

global的positions由真实capacity决定；SWA由窗口、batch、sequence和padding决定。Atomic当前 `llama-kv-cache-iswa.cpp` 的SWA规则包含窗口×sequence与microbatch，并按256对齐；`swa_full`会改变这条预算。**最终以实际buffer分配日志为准**。

### 有条件的算术示例

若读出的资产确为8个global逻辑访问、8个KV头、每头128维，context=131072，且只计算global K+V：

| 类型 | 每32标量编码bytes | global KV估算 |
|---|---:|---:|
| F16/BF16 | 64 | 4.000 GiB |
| GGML Q8_0 | 34 | 2.125 GiB |
| GGML Q4_0 | 18 | 1.125 GiB |

示例没有包括40个SWA访问、conv、草稿器、workspace、对齐和元数据，也没有证明运行峰值。squid自定义Q4的group/scale布局与GGML Q4_0不同，不能沿用其bytes/token。未知格式用实际块大小与tensor stride计算。

## 4. 阶梯测量表

T04首轮只测target-only/spec off，保持已记录的串行graph模式。至少填写下表，原始数据不可只留在这张摘要中。原生DSpark行在T06资格后补测，新增固定图/workspace组合在T08后补测；不能要求T04先跑尚未实现的特性。

| 模型/量化 | P输入tokens | 输出预留 | KV格式 | target weights | target KV | draft总量 | scratch/graph峰值 | NVML峰值 | host PSS峰值 | 结论 |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| 正式Mini候选 | 4096 | 512 | Q8或已注明F16 | 未测 | 未测 | 关闭 | 未测 | 未测 | 未测 | NOT_RUN |
| 同资产 | 16384 | 512 | 同上 | 未测 | 未测 | 关闭 | 未测 | 未测 | 未测 | NOT_RUN |
| 同资产 | 65536 | 1024 | 同上 | 未测 | 未测 | 关闭 | 未测 | 未测 | 未测 | NOT_RUN |
| 同资产 | 131072 | 1024 | 同上 | 未测 | 未测 | 关闭 | 未测 | 未测 | 未测 | NOT_RUN |

测试中的P是应用模板后的实际输入token数。生产服务总context=131072与“输入131072再生成1024”不同，见09/14。

T04是容量诊断任务：记录每个profile的FIT / DOES_NOT_FIT / UNSUPPORTED、原始原因和下一步后，可以完成诊断任务；DOES_NOT_FIT绝不能把该能力的G4标PASS。每次加入draft、改变k/B、ubatch、graph或量化后重做完整组合的容量准入。T09的skip证据绑定完整profile指纹，不能用serial的峰值永久豁免spec组合。

## 5. 当全驻留不够时

按以下顺序建立单变量实验：

1. 清理重复物理权重分配、失效图池、过大保留workspace等实现问题。
2. 限定microbatch与verify/tree workspace，不改变目标模型。
3. T10可对**停用会话**做精确状态换出/恢复，测PCIe代价。活跃请求期间的KV分页/host spill涉及attention读取路径，首版标DEFERRED；若要实现须另立任务，不能默认为T10已经包含。
4. 使用CUDA loop-aware专家缓存，先保留计算复用频繁的core，剩余留RAM；SSD优先用于持久资产和冷加载。
5. 量化KV、提高权重量化压缩、last-loop共享分别走质量研究门。

不默认把CPU专家计算当救命路径。Xeon/DDR4/PCIe Gen3下必须比较“CPU计算+传hidden”与“传packed expert+GPU算”的真实代价和可重叠部分。

## 6. 驻留策略与测量指标

只有T09由容量证据触发后，才比较全驻留对照、静态core优先、全层均分、纯LRU。静态core优先按共享权重的访问频率提出，不伪称学习得到的热点。进一步动态策略只有在命中率、搬运bytes与wall time均有收益时才引入。

指标：per-physical-layer hit/miss、packed/dequant bytes、H2D/D2H bytes、blocked I/O时间、GPU idle、每个loop的stall、lease等待、cache churn、CUDA graph重建次数。统计实际SSD block I/O与逻辑read各自单列；48GB机器页缓存中的读取不能充当小内存机器SSD证据。

## 7. 不进行的环境操作

现场调查不修改power limit、不升级驱动、不关闭现有服务、不清空系统page cache。需要独占GPU或冷盘测试时使用已授权隔离环境；无法做到则标注混杂因素并停止性能结论，不用侵入式操作补齐数据。

## v2统一预算补充

以[37](37_unified_resource_policy.md)的allocation×阶段并集计算峰值：增加record map、codebook、raw open、raw sealed pending、encoded新页、overflow、prefill解码workspace、旧新arena/graph并存与inflight store/restore。Tier只减少host/SSD存储，不能计GPU KV节省；Pool真正释放的字节只允许在context、专家驻留、draft/workspace或headroom中分配一次。恢复和fallback也必须先准入。原Q8/F16算术示例与reserve保持，不拿BF16 0.71覆盖Q8实测。

## v2.0 · 物理内存账与驻留权利

Magnitude的ledger机制补入统一预算：一个physical_store内同一allocation只计一次；claim/reservation是尚可使用的权利，allocated是实际物理块，retiring仍被设备引用，必须继续占容量。pool内部granule转owner不能伪装成释放物理内存。采用同一个BudgetSnapshot(sample_id, ledger_epoch)与自身分配日志做准入，不能拼接不同时间的OS余量。GPU和RAM是分离容量，不搬用统一内存机器的grant公式。细节及MGX01–03见[41](41_magnitude_source_audit.md)、[42](42_magnitude_integration.md)。
